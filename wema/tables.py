"""Table builders: indicator tables, item distributions, pre-specified comparisons,
models, missing-data report and plain-language key findings.

All outputs are tidy DataFrames so the app can chart them, show them and export them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import codebook, config as C, derive, relevance, stats as S

TOTAL = "All"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _groups(a: pd.DataFrame, by: str | None, order: list[str] | None):
    yield TOTAL, a
    if by is None:
        return
    levels = order or [x for x in a[by].dropna().unique()]
    for lev in levels:
        sub = a[a[by] == lev]
        if len(sub):
            yield lev, sub


def ind_table(a: pd.DataFrame, cols: list[str], by: str | None = None,
              order: list[str] | None = None, include_total: bool = True) -> pd.DataFrame:
    rows = []
    for col in cols:
        meta = derive.IND.get(col)
        for g, sub in _groups(a, by, order):
            if g == TOTAL and not include_total and by is not None:
                continue
            r = S.proportion(sub[col]) if col in sub else {"n": 0, "k": 0, "p": np.nan, "lo": np.nan, "hi": np.nan}
            rows.append({"Indicator": meta.label if meta else col, "col": col,
                         "Items": meta.items if meta else "", "Group": g, **r,
                         "small": r["n"] < C.SMALL_N})
    return pd.DataFrame(rows)


def dist_table(a: pd.DataFrame, field: str, by: str | None = None, order: list[str] | None = None,
               mask: pd.Series | None = None, drop_values: set | None = None,
               short: bool = True, choices_field: str | None = None, title: str = "") -> pd.DataFrame:
    """Distribution of a select_one / select_multiple item (percent of respondents
    who answered; for select_multiple, options do not sum to 100%). `choices_field`
    lets a derived multi-select column (e.g. treatments pooled over conditions) use
    another field's answer list."""
    cf = choices_field or field
    f = codebook.field(cf)
    multi = f["type"] == "select_multiple"
    if mask is not None:
        a = a[mask.reindex(a.index).fillna(False).astype(bool)]
    rows = []
    for g, sub in _groups(a, by, order):
        s = sub[field].dropna() if field in sub else pd.Series(dtype=object)
        s = s[s.astype(str).str.len() > 0]
        if drop_values:
            if multi:
                s = s[s.map(lambda v: not set(str(v).split()) <= drop_values)]
            else:
                s = s[~s.isin(drop_values)]
        n = len(s)
        toks = s.map(lambda v: set(str(v).split())) if multi else None
        for val, lab in codebook.choices(cf):
            if drop_values and val in drop_values:
                continue
            k = int(toks.map(lambda t: val in t).sum()) if multi else int((s == val).sum())
            lo, hi = S.wilson(k, n)
            rows.append({"Item": title or codebook.qlabel(field), "field": field, "Option": codebook.short(lab) if short else lab,
                         "value": val, "Group": g, "n": n, "k": k, "p": k / n if n else np.nan,
                         "lo": lo, "hi": hi, "small": n < C.SMALL_N, "multi": multi})
    return pd.DataFrame(rows)


def ordinal_table(a: pd.DataFrame, field: str, order: list[str], by: str | None = None,
                  group_order: list[str] | None = None, mask: pd.Series | None = None) -> pd.DataFrame:
    t = dist_table(a, field, by, group_order, mask=mask,
                   drop_values=set(codebook.value_labels(field)) - set(order), short=False)
    t["Option"] = pd.Categorical(t["value"], categories=order, ordered=True)
    return t.sort_values(["Group", "Option"])


def numeric_summary(a: pd.DataFrame, col: str, by: str | None = None, order=None) -> pd.DataFrame:
    rows = []
    for g, sub in _groups(a, by, order):
        x = pd.to_numeric(sub[col], errors="coerce").dropna()
        rows.append({"Group": g, "n": len(x), "Median": x.median() if len(x) else np.nan,
                     "Q1": x.quantile(.25) if len(x) else np.nan,
                     "Q3": x.quantile(.75) if len(x) else np.nan,
                     "Mean": x.mean() if len(x) else np.nan})
    return pd.DataFrame(rows)


def fmt_pct(p, lo=None, hi=None, n=None) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "–"
    s = f"{100 * p:.0f}%"
    if lo is not None and not np.isnan(lo):
        s += f" ({100 * lo:.0f}–{100 * hi:.0f})"
    if n is not None:
        s += f", n={n}"
    return s


def display(t: pd.DataFrame, label_col: str = "Indicator") -> pd.DataFrame:
    """Wide, human-readable table: one row per indicator/option, one column per group."""
    if t.empty:
        return t
    t = t.copy()
    t["cell"] = [fmt_pct(p, lo, hi) + (f"  [n={n}]") + (" †" if sm else "")
                 for p, lo, hi, n, sm in zip(t["p"], t["lo"], t["hi"], t["n"], t["small"])]
    groups = list(dict.fromkeys(t["Group"]))
    labels = list(dict.fromkeys(t[label_col]))
    w = t.pivot_table(index=label_col, columns="Group", values="cell", aggfunc="first")
    return w.reindex(index=labels, columns=groups)


# --------------------------------------------------------------------------
# condition-specific (T5)
# --------------------------------------------------------------------------
def diagnosis_summary(a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, c in C.CONDITIONS.items():
        dx = a[f"dx_{key}"]
        n_dx = int((dx == 1).sum())
        n_q29 = int((a[f"q29_{key}"] == 1).sum())
        sub = a[dx == 1]
        delay = S.proportion(sub[f"delay_long_{key}"])
        age_dx = pd.to_numeric(sub[c["age"]], errors="coerce")
        rows.append({"Condition": c["label"], "key": key, "Know or suspect (Q29)": n_q29,
                     "Diagnosed": n_dx, "Suspected only": int((a[f"susp_{key}"] == 1).sum()),
                     "Median age at diagnosis": age_dx.median(),
                     "Delay ≥3 y": delay["p"], "Delay lo": delay["lo"], "Delay hi": delay["hi"],
                     "Delay n": delay["n"], "small": n_dx < C.SMALL_N})
    return pd.DataFrame(rows)


def condition_items(a: pd.DataFrame, key: str) -> dict[str, pd.DataFrame]:
    c = C.CONDITIONS[key]
    sub = a[a[f"dx_{key}"] == 1]
    return {
        "Diagnostic method": dist_table(sub, c["method"]),
        "How the diagnosis came about": dist_table(sub, c["pathway"]),
        "Time from symptoms to diagnosis": ordinal_table(sub, c["delay"], C.DELAY_ORDER),
        "Challenges getting diagnosed": dist_table(sub, c["challenge"]),
        "Treatments received": dist_table(sub, c["treatment"]),
    }


# --------------------------------------------------------------------------
# comparisons (section 4 of the plan)
# --------------------------------------------------------------------------
def _binary_row(a, outcome, gcol, ga, gb):
    A = S.proportion(a.loc[a[gcol] == ga, outcome])
    B = S.proportion(a.loc[a[gcol] == gb, outcome])
    d, lo, hi = S.newcombe_diff(A["k"], A["n"], B["k"], B["n"])
    m = a[gcol].isin([ga, gb])
    t = S.categorical_test(a.loc[m, outcome], a.loc[m, gcol])
    meta = derive.IND.get(outcome)
    return {"Outcome": meta.label if meta else outcome, "Type": "Proportion",
            ga: fmt_pct(A["p"], n=A["n"]), gb: fmt_pct(B["p"], n=B["n"]),
            "Effect": d, "Effect low": lo, "Effect high": hi, "Effect measure": "Difference (pp)",
            "Test": t.method if t else "–", "p": t.p if t else np.nan,
            "small": min(A["n"], B["n"]) < C.SMALL_N}


def _ordinal_row(a, col, label, gcol, ga, gb, order):
    t = S.mann_whitney(a[col], a[gcol], ga, gb)
    med = lambda g: a.loc[a[gcol] == g, col].dropna()  # noqa: E731
    def mlab(x):
        if not len(x):
            return "–"
        return f"median: {codebook.short(order[int(np.floor(x.median()))], 28)}, n={len(x)}"
    # bootstrap CI for rank-biserial
    lo = hi = np.nan
    xa, xb = med(ga).to_numpy(), med(gb).to_numpy()
    if len(xa) > 1 and len(xb) > 1:
        rng = np.random.default_rng(3)
        bs = []
        for _ in range(500):
            ra, rb = rng.choice(xa, len(xa)), rng.choice(xb, len(xb))
            u = sps.mannwhitneyu(ra, rb).statistic
            bs.append(2 * u / (len(ra) * len(rb)) - 1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"Outcome": label, "Type": "Ordinal", ga: mlab(med(ga)), gb: mlab(med(gb)),
            "Effect": t.effect if t else np.nan, "Effect low": lo, "Effect high": hi,
            "Effect measure": "Rank-biserial r", "Test": t.method if t else "–",
            "p": t.p if t else np.nan, "small": min(len(xa), len(xb)) < C.SMALL_N}


def _multi_rows(a, field, gcol, ga, gb, mask=None):
    sub = a if mask is None else a[mask]
    rows = []
    for val, lab in codebook.choices(field):
        s = sub[field].map(lambda v, val=val: np.nan if v is None or (isinstance(v, float) and np.isnan(v))
                           else float(val in str(v).split()))
        r = _binary_row(pd.DataFrame({"__y": s, gcol: sub[gcol]}), "__y", gcol, ga, gb)
        r["Outcome"] = f"{codebook.qlabel(field).split('.')[0]}: {codebook.short(lab)}"
        rows.append(r)
    return rows


COMPARISONS = {
    "Diagnosed vs suspected only": dict(
        gcol="group", a=C.GRP_DX, b=C.GRP_SUSP,
        binary=["care_any", "care_trained", "care_trad_only", "care_easy", "hmb", "sev_pain",
                "marker_sx", "irregular", "emergency"],
        ordinal=[("pain_ord", "Pain severity (Q21)", C.PAIN_ORDER)],
        multi=[("reasons_not_spoken_HCP", None)]),
    "Insured vs uninsured": dict(
        gcol="insured", a="Insured", b="Uninsured",
        binary=["spend_care_5k", "hardship", "hard_borrow", "hard_cannot", "hard_forwent",
                "care_any", "care_trained"],
        ordinal=[("spend_care_ord", "Care spend band, past 12 months (Q73)", C.CARE_BANDS)],
        multi=[]),
    "HMB proxy vs none": dict(
        gcol="hmb_group", a="HMB proxy", b="No HMB",
        binary=["days_work3", "days_hh3", "fatigue_dizzy", "anaemia", "spend_prod_500"],
        ordinal=[("days_work_ord", "Days of work/school lost a month (Q77)", C.DAYS_ORDER),
                 ("days_hh_ord", "Days of household duties lost a month (Q78)", C.DAYS_ORDER),
                 ("spend_prod_ord", "Product spend band, past 30 days (Q72)", C.PRODUCT_BANDS)],
        multi=[]),
    "Lowest vs highest income band": dict(
        gcol="income", a=C.INCOME_ORDER[0], b=C.INCOME_ORDER[-1],
        binary=["spend_prod_500", "hardship", "hard_cannot", "hard_borrow", "care_any"],
        ordinal=[("spend_prod_ord", "Product spend band (Q72)", C.PRODUCT_BANDS)],
        multi=[("reasons_not_spoken_HCP", None)]),
    "Sensitivity: support-group recruits vs other routes": dict(
        gcol="recruit_group", a="Support / advocacy group", b="Other route",
        binary=["dx_any", "care_any", "hmb", "sev_pain", "delay_long_any", "hardship", "ins_any", "stigma"],
        ordinal=[], multi=[]),
    "Nairobi vs other counties": dict(
        gcol="nairobi", a="Nairobi", b="Other counties",
        binary=["care_any", "care_trained", "dx_imaging_any", "dx_surgical_any", "delay_long_any"],
        ordinal=[], multi=[]),
}


def comparison(a: pd.DataFrame, name: str) -> pd.DataFrame:
    spec = COMPARISONS[name]
    g, ga, gb = spec["gcol"], spec["a"], spec["b"]
    rows = [_binary_row(a, o, g, ga, gb) for o in spec["binary"]]
    rows += [_ordinal_row(a, col, lab, g, ga, gb, order) for col, lab, order in spec["ordinal"]]
    for field, _ in spec["multi"]:
        rows += _multi_rows(a, field, g, ga, gb)
    return pd.DataFrame(rows)


def trend_across(a: pd.DataFrame, gcol: str, order: list[str], outcomes: list[str]) -> pd.DataFrame:
    """All levels of an ordered grouping (e.g. income): % per level + overall test."""
    rows = []
    for o in outcomes:
        m = a[gcol].isin(order)
        t = S.categorical_test(a.loc[m, o], a.loc[m, gcol])
        r = {"Outcome": derive.IND[o].label if o in derive.IND else o}
        for lev in order:
            p = S.proportion(a.loc[a[gcol] == lev, o])
            r[lev] = fmt_pct(p["p"], n=p["n"])
        r["Test"] = t.method if t else "–"
        r["p"] = t.p if t else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# models
# --------------------------------------------------------------------------
COVARIATE_PRIORITY = [("age", "Age (per year)", 1), ("ins_any", "Insured", 1),
                      ("income_ord", "Income band (per step up)", 1), ("education", "Education", 2)]
MODELS = {
    "Care sought (any provider)": "care_any",
    "Financial hardship": "hardship",
    "Diagnostic delay ≥3 years (any condition)": "delay_long_any",
}


def model(a: pd.DataFrame, outcome: str, covariates: list[str] | None = None):
    data = a.copy()
    data["education"] = pd.Categorical(data["education"], categories=C.EDU_ORDER)
    y = pd.to_numeric(data[outcome], errors="coerce")
    events = int(y.sum())
    nonevents = int((y == 0).sum())
    budget = min(events, nonevents) // 10
    chosen, used, dropped = [], 0, []
    for col, lab, df_ in COVARIATE_PRIORITY:
        if covariates is not None and col not in covariates:
            continue
        if used + df_ <= budget:
            chosen.append(col)
            used += df_
        else:
            dropped.append(lab)
    res = S.firth_logit(data, outcome, chosen) if chosen else None
    if res is not None:
        pretty = {"age": "Age (per year)", "income_ord": "Income band (per step up)",
                  "ins_any: 1.0": "Insured (vs uninsured)"}
        res.names = [pretty.get(n, n.replace("education: ", "Education: ")) for n in res.names]
    return {"result": res, "events": events, "nonevents": nonevents, "budget": budget,
            "covariates": chosen, "dropped": dropped}


# --------------------------------------------------------------------------
# missing data
# --------------------------------------------------------------------------
SECTION_NAMES = {None: "Screening", "Section1": "1. Background", "Section2": "2. Menstrual health",
                 "Section3": "3. Awareness", "section4": "4. Diagnosis – adenomyosis",
                 "Endometriosis": "4. Diagnosis – endometriosis",
                 "Uterine_fibroids": "4. Diagnosis – fibroids", "pmos": "4. Diagnosis – PMOS",
                 "pmdd": "4. Diagnosis – PMDD", "pei": "5. Psychosocial & economic",
                 "Health_insurance": "6. Insurance", "self_care": "7. Self-care & needs"}


def missingness(d: pd.DataFrame) -> pd.DataFrame:
    base = d[d["eligible_base"]]
    rows = []
    for name, f in codebook.fields().items():
        if name in C.PII_FIELDS or name in C.FREE_TEXT_HIDDEN or name.endswith(("_other_specify", "_other")) \
                or f["type"] == "string" or name in ("consent", "how_old_are_you", "had_menses"):
            continue
        shown = relevance.applicable(base, name)
        n_app = int(shown.sum())
        miss = int((shown & base[name].isna()).sum()) if name in base else n_app
        rows.append({"Section": SECTION_NAMES.get(f.get("group"), f.get("group")),
                     "Q": f.get("q"), "Field": name, "Question": f["label"][:90],
                     "Shown to": n_app, "Missing": miss,
                     "% missing": miss / n_app if n_app else np.nan,
                     "Flag >10%": bool(n_app and miss / n_app > C.MISSING_FLAG)})
    return pd.DataFrame(rows)


def missing_by_section(m: pd.DataFrame) -> pd.DataFrame:
    g = m.groupby("Section", sort=False).agg(Items=("Field", "count"), Shown=("Shown to", "sum"),
                                             Missing=("Missing", "sum"), Flagged=("Flag >10%", "sum"))
    g["% missing"] = g["Missing"] / g["Shown"].replace(0, np.nan)
    return g.reset_index()


def consistency(d: pd.DataFrame) -> pd.DataFrame:
    a = d[d["analytic"]]
    checks = [
        ("Q29 names a condition AND says 'none'", int(a["flag_q29_contradiction"].sum())),
        ("Diagnosed (Section 4) with a condition not ticked at Q29", int(a["flag_dx_not_in_q29"].sum())),
        ("Q25 (ease of care) answered without having sought care",
         int((a["obtain_period_related_symptoms"].notna() & (a["care_any"] == 0)).sum())),
        ("Insurance detail (Q81–83) answered by uninsured women",
         int((a["health_insurance_cover_diag_treat"].notna() & (a["ins_any"] == 0)).sum())),
        ("No period in 12 months but answered cycle items (Q18–20)",
         int(((a["period12"] == 0) & a["avg_often_period_come"].notna()).sum())),
        ("Age at diagnosis greater than current age",
         int(sum(((pd.to_numeric(a[c["age"]], errors="coerce") > a["age"])).sum()
                 for c in C.CONDITIONS.values()))),
    ]
    return pd.DataFrame(checks, columns=["Check", "Respondents"])


# --------------------------------------------------------------------------
# key findings (plain language)
# --------------------------------------------------------------------------
def key_findings(a: pd.DataFrame) -> list[str]:
    n = len(a)
    if n == 0:
        return []
    out = []

    period = a[a["period12"] == 1]

    def line(col, text):
        p = S.proportion((period if col in ("hmb", "sev_pain") else a)[col])
        if p["n"]:
            out.append(f"{text}: **{fmt_pct(p['p'], p['lo'], p['hi'])}** of {p['n']} women")

    line("hmb", "Met the heavy menstrual bleeding proxy")
    line("sev_pain", "Reported severe or extremely severe period pain")
    line("care_any", "Sought care for period symptoms in the past year (among those with symptoms of concern)")
    line("delay_long_any", "Waited 3 years or more for a diagnosis (diagnosed women)")
    line("hardship", "Experienced financial hardship from their condition")
    line("days_work3", "Lost 3 or more days of work or school each month")
    line("stigma", "Have experienced stigma or disbelief")
    ins = a[a["ins_any"] == 1]
    p = S.proportion(ins["ins_cover_dk"])
    if p["n"]:
        out.append(f"Insured women who do not know whether these conditions are covered: "
                   f"**{fmt_pct(p['p'], p['lo'], p['hi'])}** of {p['n']}")
    return out


def cat_table(a: pd.DataFrame, col: str, order: list[str], by: str | None = None,
              group_order: list[str] | None = None, title: str = "") -> pd.DataFrame:
    """Distribution of a derived categorical column (e.g. age group)."""
    rows = []
    for g, sub in _groups(a, by, group_order):
        s = sub[col].dropna()
        n = len(s)
        for lev in order:
            k = int((s == lev).sum())
            lo, hi = S.wilson(k, n)
            rows.append({"Item": title or col, "field": col, "Option": lev, "value": lev, "Group": g,
                         "n": n, "k": k, "p": k / n if n else np.nan, "lo": lo, "hi": hi,
                         "small": n < C.SMALL_N, "multi": False})
    return pd.DataFrame(rows)


DESIGN_MINUTES = {"No condition known or suspected": "~19", "Suspects a condition, none diagnosed": "~21",
                  "One diagnosed condition": "~24", "Two diagnosed conditions": "~26–27",
                  "Three or more diagnosed conditions": "~29–36"}


def durations(d: pd.DataFrame) -> pd.DataFrame | None:
    """Completion time by survey path, if the form records start/end metadata."""
    if "_start" not in d or "_end" not in d:
        return None
    start = pd.to_datetime(d["_start"], errors="coerce", utc=True)
    end = pd.to_datetime(d["_end"], errors="coerce", utc=True)
    mins = (end - start).dt.total_seconds() / 60
    if mins.notna().sum() == 0:
        return None
    a = d.assign(_mins=mins)[d["analytic"]]

    def path(r):
        if r["group"] == C.GRP_NONE:
            return "No condition known or suspected"
        if r["group"] == C.GRP_SUSP:
            return "Suspects a condition, none diagnosed"
        k = r["n_dx"]
        if k == 1:
            return "One diagnosed condition"
        if k == 2:
            return "Two diagnosed conditions"
        if k >= 3:
            return "Three or more diagnosed conditions"
        return None

    a = a.assign(_path=a.apply(path, axis=1))
    rows = []
    for p, est in DESIGN_MINUTES.items():
        x = a.loc[a["_path"] == p, "_mins"].dropna()
        rows.append({"Path": p, "n": len(x), "Design estimate (min)": est,
                     "Median (min)": round(x.median(), 1) if len(x) else None,
                     "IQR (min)": f"{x.quantile(.25):.0f}–{x.quantile(.75):.0f}" if len(x) else "–",
                     "Under 8 min (possible speeding)": int((x < 8).sum()),
                     "Over 90 min (left open)": int((x > 90).sum())})
    x = a["_mins"].dropna()
    rows.append({"Path": "All", "n": len(x), "Design estimate (min)": "16–36",
                 "Median (min)": round(x.median(), 1), "IQR (min)": f"{x.quantile(.25):.0f}–{x.quantile(.75):.0f}",
                 "Under 8 min (possible speeding)": int((x < 8).sum()), "Over 90 min (left open)": int((x > 90).sum())})
    return pd.DataFrame(rows)
