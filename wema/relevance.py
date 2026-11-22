"""Evaluate the form's own skip logic (XPath `relevant` expressions) on responses.

Only the subset of XPath used by this form is supported: field paths, string and
number literals, = != < <= > >=, and/or/not(), and selected(path, 'v'). This lets
item non-response be measured against the women who were actually *shown* each
question, rather than everyone.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

import pandas as pd

from . import codebook

_PATH = re.compile(r"/[A-Za-z_][\w]*(?:/[A-Za-z_][\w]*)+")


class XV:
    """A node value with XPath comparison semantics (blank = empty string)."""

    __slots__ = ("s",)

    def __init__(self, s):
        self.s = "" if s is None or (isinstance(s, float) and math.isnan(s)) else str(s)

    def _num(self):
        try:
            return float(self.s)
        except ValueError:
            return math.nan

    def _cmp(self, other, op):
        if isinstance(other, (int, float)):
            a, b = self._num(), float(other)
            if math.isnan(a):
                return op == "!="
        else:
            a, b = self.s, str(other)
        return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]

    def __eq__(self, o): return self._cmp(o, "==")
    def __ne__(self, o): return self._cmp(o, "!=")
    def __lt__(self, o): return self._cmp(o, "<")
    def __le__(self, o): return self._cmp(o, "<=")
    def __gt__(self, o): return self._cmp(o, ">")
    def __ge__(self, o): return self._cmp(o, ">=")
    __hash__ = None


def _selected(v: XV, opt) -> bool:
    return str(opt) in v.s.split()


@lru_cache(maxsize=None)
def compile_expr(expr: str):
    if not expr:
        return None
    py = _PATH.sub(lambda m: f"F({m.group(0).split('/')[-1]!r})", expr)
    py = re.sub(r"(?<![!<>=])=(?!=)", "==", py)
    py = re.sub(r"\bnot\s*\(", "(not ", py)
    py = py.replace("selected(", "SEL(")
    return compile(py, "<relevant>", "eval")


def evaluate(expr: str | None, row: dict) -> bool:
    code = compile_expr(expr or "")
    if code is None:
        return True
    env = {"F": lambda name: XV(row.get(name)), "SEL": _selected}
    try:
        return bool(eval(code, {"__builtins__": {}}, env))
    except Exception:  # unsupported construct: treat as shown
        return True


def applicable(df: pd.DataFrame, name: str) -> pd.Series:
    """Boolean Series: was question `name` shown to each respondent?"""
    cb = codebook.load()
    f = cb["fields"][name]
    group_rel = cb["groups"].get(f.get("group")) if f.get("group") else None
    rows = df.to_dict("records")
    out = [evaluate(group_rel, r) and evaluate(f.get("relevant"), r) for r in rows]
    return pd.Series(out, index=df.index, dtype=bool)
