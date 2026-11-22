"""Access to the form definition (wema/codebook.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CODEBOOK_PATH = Path(__file__).with_name("codebook.json")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(CODEBOOK_PATH.read_text())


def fields() -> dict:
    return load()["fields"]


def field(name: str) -> dict:
    return fields()[name]


def choices(name: str) -> list[tuple[str, str]]:
    return [(c["value"], c["label"]) for c in fields()[name]["choices"]]


def value_labels(name: str) -> dict[str, str]:
    return dict(choices(name))


def short(label: str, n: int = 60) -> str:
    """Trim long option labels for charts ("Endometriosis - a condition ..." -> "Endometriosis")."""
    for sep in (" - ", " (", ": "):
        if sep in label and label.index(sep) > 3:
            label = label[: label.index(sep)]
            break
    label = label.strip().rstrip(":").strip()
    return label if len(label) <= n else label[: n - 1] + "…"


def qlabel(name: str) -> str:
    f = fields()[name]
    return f"Q{f['q']}. {f['label']}" if f.get("q") else f["label"]


def by_q(q: int) -> str:
    for name, f in fields().items():
        if f.get("q") == q:
            return name
    raise KeyError(q)
