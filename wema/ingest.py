"""Get responses into one tidy DataFrame: one row per submission, one column per
form field (bare field name, stored Kobo values), plus submission metadata.

Sources:
  * KoboToolbox API v2 (token)                     -> fetch_kobo()
  * a Kobo export file (.xlsx / .csv / .json)      -> read_export()
Both go through normalise(), which strips group prefixes, converts label-style
exports back to stored values, drops identifying fields and de-duplicates.
"""
from __future__ import annotations

import io
import json
from typing import Iterable

import pandas as pd
import requests

from . import codebook, config

META_KEEP = {"_id": "_id", "_uuid": "_uuid", "_submission_time": "_submission_time",
             "_validation_status": "_validation_status", "start": "_start", "end": "_end",
             "__version__": "_form_version", "meta/instanceID": "_instance_id"}


class KoboError(RuntimeError):
    pass


def fetch_kobo(token: str, server: str = config.KOBO_SERVER,
               asset_uid: str = config.KOBO_ASSET_UID, page_size: int = 1000,
               timeout: int = 60) -> pd.DataFrame:
    """Download every submission through the Kobo API v2 (paginated)."""
    if not token:
        raise KoboError("No Kobo API token configured.")
    url = f"{server.rstrip('/')}/api/v2/assets/{asset_uid}/data.json"
    params = {"limit": page_size, "start": 0}
    headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
    records: list[dict] = []
    while url:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        if r.status_code in (401, 403):
            raise KoboError("Kobo rejected the token (HTTP %s). Check the token and that the "
                            "account can view submissions for this form." % r.status_code)
        if r.status_code == 404:
            raise KoboError(f"Form {asset_uid} not found on {server}. Check KOBO_SERVER / "
                            "KOBO_ASSET_UID (EU-server accounts use https://eu.kobotoolbox.org).")
        r.raise_for_status()
        payload = r.json()
        records.extend(payload.get("results", []))
        url, params = payload.get("next"), None
    return normalise(pd.DataFrame.from_records(records))


def read_export(data: bytes, filename: str) -> pd.DataFrame:
    """Read a Kobo export. Prefer 'XML values and headers'; label exports are converted."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, dtype=str)
        raw = next(iter(sheets.values()))  # main sheet is first; repeat groups not used
    elif name.endswith(".json"):
        obj = json.loads(data)
        raw = pd.DataFrame.from_records(obj.get("results", obj) if isinstance(obj, dict) else obj)
    else:
        text = data.decode("utf-8-sig")
        sep = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
        raw = pd.read_csv(io.StringIO(text), sep=sep, dtype=str)
    return normalise(raw)


def _bare(col: str) -> str:
    return col.split("/")[-1].strip()


def _rebuild_multi(raw: pd.DataFrame, field: str, values: Iterable[str]) -> pd.Series | None:
    """Kobo exports add one 0/1 column per option ("group/field/value")."""
    cols = {}
    for c in raw.columns:
        parts = c.split("/")
        if len(parts) >= 2 and parts[-2] == field and parts[-1] in values:
            cols[parts[-1]] = c
    if not cols:
        return None
    order = [v for v in values if v in cols]

    def join(row):
        chosen = [v for v in order if str(row[cols[v]]).strip() in ("1", "1.0", "True", "true")]
        return " ".join(chosen) if chosen else None

    return raw.apply(join, axis=1)


def normalise(raw: pd.DataFrame) -> pd.DataFrame:
    fields = codebook.fields()
    if raw.empty:
        return pd.DataFrame(columns=list(fields) + list(META_KEEP.values()))
    cols: dict[str, pd.Series] = {}
    for col, new in META_KEEP.items():
        if col in raw.columns:
            cols[new] = raw[col]
    by_bare: dict[str, str] = {}
    for c in raw.columns:
        b = _bare(c)
        # option columns ("field/value") share a bare name with option values; keep the
        # column whose bare name is a field and which isn't an option sub-column
        if b in fields and b not in by_bare:
            by_bare[b] = c
    for name, f in fields.items():
        if name in config.PII_FIELDS:
            continue
        values = [c["value"] for c in f["choices"]]
        col = by_bare.get(name)
        s = raw[col] if col is not None else pd.Series([None] * len(raw), index=raw.index)
        s = pd.Series([_clean(v) for v in s], index=raw.index, dtype=object)
        if f["type"] == "select_multiple":
            rebuilt = _rebuild_multi(raw, name, values)
            if s.notna().any():
                s = pd.Series([_labels_to_values_multi(v, f) if v is not None else None for v in s],
                              index=raw.index, dtype=object)
            elif rebuilt is not None:
                s = rebuilt
        elif f["type"] == "select_one":
            lab2val = {c["label"]: c["value"] for c in f["choices"]}
            valid = set(values)
            s = s.map(lambda v: v if v is None or v in valid else lab2val.get(v, v)).astype(object)
        elif f["type"] in ("int", "decimal"):
            s = pd.to_numeric(s, errors="coerce")
        cols[name] = s
    out = pd.DataFrame(cols, index=raw.index)
    if "_submission_time" in out:
        out["_submission_time"] = pd.to_datetime(out["_submission_time"], errors="coerce", utc=True)
    if "_validation_status" in out:
        out["_validation_status"] = out["_validation_status"].map(_validation_label)
    key = "_uuid" if "_uuid" in out else ("_instance_id" if "_instance_id" in out else None)
    if key:
        out = out.drop_duplicates(subset=[key], keep="last")
    return out.reset_index(drop=True)


def _clean(v):
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    v = str(v).strip()
    # NB: "None" is a real answer code (Q76 "None" burden), so it is NOT treated as blank
    return None if v in ("", "nan", "NaN") else v


def _labels_to_values_multi(v: str, f: dict) -> str:
    values = {c["value"] for c in f["choices"]}
    toks = v.split()
    if all(t in values for t in toks):
        return v
    # label export: options are separated by spaces too, so match labels greedily
    found = [c["value"] for c in sorted(f["choices"], key=lambda c: -len(c["label"]))
             if c["label"] and c["label"] in v]
    return " ".join(found) if found else v


def _validation_label(v) -> str | None:
    if isinstance(v, dict):
        return v.get("label") or v.get("uid")
    if isinstance(v, str) and v.startswith("{"):
        try:
            d = json.loads(v.replace("'", '"'))
            return d.get("label") or d.get("uid")
        except ValueError:
            return v
    return v if v not in (None, "", "nan") else None
