"""Excel export of every table shell (T1-T10), comparisons, models and data quality."""
from __future__ import annotations

import io

import pandas as pd

from . import config as C, derive, tables as T
from .report import TABLE_SPECS


def workbook(d: pd.DataFrame, a: pd.DataFrame, demo: bool = False) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        notes = pd.DataFrame({"Note": [
            "WEMA Study - analysis tables" + (" - SYNTHETIC DEMO DATA, NOT REAL RESULTS" if demo else ""),
            f"Analysis population n = {len(a)} (of {len(d)} submissions)",
            "Cells: % (95% Wilson CI) [n = denominator]. † = fewer than 40 respondents: descriptive only.",
            "Convenience sample recruited largely through advocacy groups; self-reported diagnosis; "
            "findings describe this group of women, not all Kenyan women.",
        ]})
        notes.to_excel(xw, sheet_name="README", index=False)
        pd.DataFrame(derive.sample_flow(d), columns=["Step", "n"]).to_excel(xw, sheet_name="Sample flow", index=False)
        for sheet, builder in TABLE_SPECS.items():
            start = 0
            for title, tab in builder(a):
                pd.DataFrame({title: []}).to_excel(xw, sheet_name=sheet, startrow=start, index=False)
                tab.to_excel(xw, sheet_name=sheet, startrow=start + 1)
                start += len(tab) + 4
        start = 0
        for name in T.COMPARISONS:
            c = T.comparison(a, name)
            pd.DataFrame({name: []}).to_excel(xw, sheet_name="Comparisons", startrow=start, index=False)
            c.to_excel(xw, sheet_name="Comparisons", startrow=start + 1, index=False)
            start += len(c) + 4
        start = 0
        for lab, outcome in T.MODELS.items():
            m = T.model(a, outcome)
            pd.DataFrame({f"{lab}: events={m['events']}, covariates={m['covariates']}": []}).to_excel(
                xw, sheet_name="Models", startrow=start, index=False)
            if m["result"] is not None:
                m["result"].table().to_excel(xw, sheet_name="Models", startrow=start + 1, index=False)
                start += len(m["result"].names) + 4
            else:
                start += 3
        from . import power as PW
        PW.comparison_capacity(a).to_excel(xw, sheet_name="What sample can show", index=False)
        PW.recruitment_vs_targets(a).to_excel(xw, sheet_name="Recruitment vs targets", index=False)
        PW.model_capacity(a).to_excel(xw, sheet_name="Model capacity", index=False)
        mm = T.missingness(d)
        T.missing_by_section(mm).to_excel(xw, sheet_name="Missing data", index=False)
        mm.to_excel(xw, sheet_name="Missing by item", index=False)
        T.consistency(d).to_excel(xw, sheet_name="Consistency checks", index=False)
        pd.DataFrame([vars(i) for i in derive.INDICATORS]).to_excel(xw, sheet_name="Indicator definitions", index=False)
    return buf.getvalue()
