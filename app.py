"""WEMA Study analytics dashboard (Streamlit).

Run locally:   streamlit run app.py
Configuration: .streamlit/secrets.toml or environment variables (see README).
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

from wema import charts as CH, codebook, config as C, demo, derive, export, ingest, report as R, tables as T

st.set_page_config(page_title="WEMA Study dashboard", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
  .block-container {padding-top: 3.5rem; width: 100%; max-width: 1280px; box-sizing: border-box;}
  div[data-testid="stPlotlyChart"] {width: 100%; min-width: 0;}
  .kpi {border: 1px solid #e7e6e2; border-radius: 10px; padding: 14px 16px; background: #fff; height: 100%;}
  .kpi .v {font-size: 1.9rem; font-weight: 650; color: #0b0b0b; line-height: 1.1;}
  .kpi .l {font-size: .86rem; color: #52514e; margin-top: 4px;}
  .kpi .c {font-size: .78rem; color: #8a8984; margin-top: 2px;}
  .statement {border-left: 3px solid #2a78d6; background: #f3f7fd; padding: 8px 12px; border-radius: 4px;
              color: #1f2f46; margin: 4px 0 14px 0; font-size: .95rem;}
  .demo {background: #fff4e5; border: 1px solid #fab219; padding: 8px 12px; border-radius: 6px;
         color: #5c3b00; font-weight: 600; line-height: 1.5; margin-bottom: 10px;}
  .legendnote {color: #8a8984; font-size: .8rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# configuration & access control
# ---------------------------------------------------------------------------
def secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:  # no secrets file
        pass
    return os.environ.get(name, default)


def password_gate() -> None:
    pw = secret("APP_PASSWORD")
    if not pw or st.session_state.get("auth_ok"):
        return
    st.title("WEMA Study dashboard")
    st.caption("This dashboard contains confidential study data. Please sign in.")
    entered = st.text_input("Password", type="password")
    if entered:
        if hmac.compare_digest(entered, pw):
            st.session_state["auth_ok"] = True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()


password_gate()


# ---------------------------------------------------------------------------
# pages are registered first so deep links (e.g. /t4) survive the data step;
# the page functions are defined further down and looked up when NAV.run() fires
# ---------------------------------------------------------------------------
def _p(name):
    return lambda: globals()[name]()


def _shell(key):
    return lambda: shell_page(key)


pages = {
    "Summary": [st.Page(_p("page_overview"), title="Overview", icon="🏠", default=True)],
    "Table shells": [
        st.Page(_shell("T1"), title="T1 Sample", url_path="t1"),
        st.Page(_shell("T2"), title="T2 Symptom burden", url_path="t2"),
        st.Page(_shell("T3"), title="T3 Awareness", url_path="t3"),
        st.Page(_shell("T4"), title="T4 Care-seeking", url_path="t4"),
        st.Page(_p("page_t5"), title="T5 Diagnosis", url_path="t5"),
        st.Page(_shell("T6"), title="T6 Stigma & psychosocial", url_path="t6"),
        st.Page(_shell("T7"), title="T7 Economic burden", url_path="t7"),
        st.Page(_shell("T8"), title="T8 Insurance", url_path="t8"),
        st.Page(_shell("T9"), title="T9 Coping & needs", url_path="t9"),
        st.Page(_shell("T10"), title="T10 Data & digital", url_path="t10"),
    ],
    "Analysis": [
        st.Page(_p("page_comparisons"), title="Comparisons", url_path="comparisons"),
        st.Page(_p("page_models"), title="Adjusted models", url_path="models"),
        st.Page(_p("page_behaviour"), title="Behavioural baseline", url_path="behaviour"),
    ],
    "About the data": [
        st.Page(_p("page_quality"), title="Data quality", url_path="quality"),
        st.Page(_p("page_methods"), title="Methods & limitations", url_path="methods"),
        st.Page(_p("page_export"), title="Export", url_path="export"),
    ],
}
NAV = st.navigation(pages)

# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner="Downloading responses from KoboToolbox…")
def load_kobo(token: str, server: str, uid: str) -> tuple[pd.DataFrame, str]:
    df = ingest.fetch_kobo(token, server, uid)
    return df, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@st.cache_data(show_spinner="Reading file…")
def load_file(data: bytes, name: str) -> pd.DataFrame:
    return ingest.read_export(data, name)


@st.cache_data(show_spinner="Generating synthetic demo data…")
def load_demo(n: int) -> pd.DataFrame:
    return demo.generate(n)


@st.cache_data(show_spinner="Deriving indicators…")
def derived(df: pd.DataFrame) -> pd.DataFrame:
    return derive.derive(df)


token = secret("KOBO_TOKEN")
server = secret("KOBO_SERVER", C.KOBO_SERVER)
uid = secret("KOBO_ASSET_UID", C.KOBO_ASSET_UID)

with st.sidebar:
    st.markdown("### WEMA Study")
    sources = (["KoboToolbox (live)"] if token else []) + ["Upload a Kobo export", "Demo (synthetic data)"]
    source = st.radio("Data source", sources, index=0,
                      help="Live data needs KOBO_TOKEN in the app secrets. Uploads: in Kobo choose "
                           "Downloads → XLS, 'XML values and headers'.")
    raw, stamp, is_demo = None, "", False
    if source == "KoboToolbox (live)":
        try:
            raw, stamp = load_kobo(token, server, uid)
        except Exception as e:  # show a clear message rather than a traceback
            st.error(f"Could not load from Kobo: {e}")
        if st.button("Refresh data", use_container_width=True):
            load_kobo.clear()
            st.rerun()
    elif source == "Upload a Kobo export":
        up = st.file_uploader("Kobo export (.xlsx, .csv or .json)", type=["xlsx", "xls", "csv", "json"])
        if up is not None:
            raw = load_file(up.getvalue(), up.name)
            stamp = f"file {up.name}"
    else:
        raw, stamp, is_demo = load_demo(320), "synthetic", True

if raw is None or raw.empty:
    st.title("WEMA Study dashboard")
    st.info("Choose a data source in the sidebar. With no Kobo token configured you can upload an export, "
            "or explore the dashboard with synthetic demo data.")
    st.stop()

D = derived(raw)

with st.sidebar:
    st.caption(f"{len(D):,} submissions · {stamp}")
    st.markdown("---")
    st.markdown("**Analysis population**")
    keep_none = st.toggle("Include 'no condition' comparison group", value=True,
                          help="Decision B1. When off, analyses are restricted to women who know or "
                               "suspect they have at least one condition.")
    with st.expander("Filters", expanded=False):
        counties = R.BREAKDOWNS["County / town"][1]
        f_county = st.multiselect("County / town", counties, default=[])
        f_age = st.multiselect("Age group", C.AGE_LABELS, default=[])
        f_dates = None
        if "_submission_time" in D and D["_submission_time"].notna().any():
            dmin = D["_submission_time"].min().date()
            dmax = D["_submission_time"].max().date()
            if dmin < dmax:
                f_dates = st.slider("Submission date", min_value=dmin, max_value=dmax, value=(dmin, dmax))
        f_valid = False
        if "_validation_status" in D and D["_validation_status"].notna().any():
            f_valid = st.checkbox("Exclude submissions marked 'Not approved' in Kobo", value=True)

A = derive.analytic(D, keep_none)
if f_county:
    A = A[A["county"].isin(f_county)]
if f_age:
    A = A[A["age_group"].isin(f_age)]
if f_dates:
    t = A["_submission_time"].dt.date
    A = A[(t >= f_dates[0]) & (t <= f_dates[1])]
if f_valid:
    A = A[~A["_validation_status"].fillna("").str.contains("Not approved", case=False)]
FILTERED = bool(f_county or f_age or (f_dates and f_dates != (dmin, dmax)))


# ---------------------------------------------------------------------------
# rendering helpers
# ---------------------------------------------------------------------------
def banner():
    if is_demo:
        st.markdown('<div class="demo">⚠ DEMO MODE – synthetic data. Numbers on this page are made up '
                    'and must not be quoted.</div>', unsafe_allow_html=True)
    if FILTERED:
        st.caption(f"Filters applied: n = {len(A)} women in view.")


def header(title: str, statement: str = "", sub: str = ""):
    banner()
    st.title(title)
    if sub:
        st.caption(sub)
    if statement:
        st.markdown(f'<div class="statement"><b>Statement it supports:</b> {statement}</div>',
                    unsafe_allow_html=True)


def kpi(col, value: str, label: str, ci: str = ""):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div>'
                 f'<div class="c">{ci}</div></div>', unsafe_allow_html=True)


def kpi_ind(col, ind: str, label: str | None = None, data: pd.DataFrame | None = None):
    p = T.S.proportion((A if data is None else data)[ind])
    v = f"{100 * p['p']:.0f}%" if p["n"] else "–"
    ci = f"95% CI {100 * p['lo']:.0f}–{100 * p['hi']:.0f} · n={p['n']}" if p["n"] else "no data"
    if p["n"] and p["n"] < C.SMALL_N:
        ci += " · descriptive only"
    kpi(col, v, label or derive.IND[ind].label, ci)


def table_view(df: pd.DataFrame, key: str, caption: str = ""):
    with st.expander("Table view & download", expanded=False):
        if caption:
            st.caption(caption)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download CSV", df.to_csv().encode("utf-8"), file_name=f"{key}.csv",
                           mime="text/csv", key=f"dl_{key}")


SMALL_NOTE = ("Dots show % with 95% CI. **Hollow dots** = fewer than 40 respondents (descriptive only). "
              "† in tables marks the same.")


def render_block(b: R.Block, breakdown: str, key: str):
    t = b.compute(A, breakdown)
    st.subheader(b.title)
    if b.note:
        st.caption(b.note)
    if t.empty or (("n" in t) and t["n"].max() == 0):
        st.info("No responses for this item in the current selection.")
        return
    by, levels = R.BREAKDOWNS[breakdown]
    groups = ["All"] + [g for g in levels if g in set(t["Group"])] if by else ["All"]
    if b.kind == "ind":
        st.plotly_chart(CH.dot_ci(t, "Indicator", groups), use_container_width=True, key=f"c_{key}")
    elif b.kind in ("dist", "cat"):
        multi = bool(t["multi"].iloc[0]) if "multi" in t else False
        show = t if len(groups) <= 4 else t[t["Group"].isin(groups[:4])]
        st.plotly_chart(CH.bars(show, "Option", groups[:4], sort=b.kind == "dist" and multi),
                        use_container_width=True, key=f"c_{key}")
        if multi:
            st.caption("Select-all-that-apply: percentages do not sum to 100%.")
    elif b.kind == "ord":
        labels = {v: codebook.short(lab, 48) for v, lab in codebook.choices(b.field)}
        st.plotly_chart(CH.stacked(t, b.order, labels, groups), use_container_width=True, key=f"c_{key}")
    if b.kind == "num":
        st.dataframe(b.display(t), use_container_width=True)
    else:
        table_view(b.display(t), key, "Cells: % (95% CI) [n = denominator]. † = n < 40.")


def shell_page(shell_key: str):
    sh = R.SHELL[shell_key]
    header(f"{sh.key} · {sh.title}", sh.statement, sh.objective)
    breakdown = st.selectbox("Break down by", sh.breakdowns, key=f"bd_{shell_key}")
    st.caption(SMALL_NOTE)
    for i, b in enumerate(sh.blocks):
        render_block(b, breakdown, f"{shell_key}_{i}")
        st.markdown("")


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
def page_overview():
    header("WEMA Study – overview",
           sub="Women's Experiences of Menstrual Disorders Assessment · Kenya")
    n_dx = int((A["group"] == C.GRP_DX).sum())
    n_s = int((A["group"] == C.GRP_SUSP).sum())
    n_n = int((A["group"] == C.GRP_NONE).sum())
    c = st.columns(4)
    kpi(c[0], f"{len(A):,}", "Women in the analysis", f"of {len(D):,} submissions")
    kpi(c[1], f"{n_dx:,}", "Diagnosed with ≥1 condition", "Section 4 gate = Yes")
    kpi(c[2], f"{n_s:,}", "Suspect a condition, not diagnosed", "Q29 ticked, gate = No")
    kpi(c[3], f"{n_n:,}", "No condition (comparison)", "Q29 none" if keep_none else "excluded (B1)")
    st.markdown("")
    c = st.columns(4)
    period = A[A["period12"] == 1]
    kpi_ind(c[0], "hmb", "Heavy menstrual bleeding (proxy)", period)
    kpi_ind(c[1], "sev_pain", "Severe period pain", period)
    kpi_ind(c[2], "delay_long_any", "Waited ≥3 years for diagnosis")
    kpi_ind(c[3], "hardship", "Financial hardship")
    st.markdown("")
    c = st.columns(4)
    kpi_ind(c[0], "care_any", "Sought care (symptoms of concern)")
    kpi_ind(c[1], "days_work3", "Lose ≥3 work/school days a month")
    kpi_ind(c[2], "stigma", "Experienced stigma or disbelief")
    kpi_ind(c[3], "ins_any", "Have any health insurance")

    st.subheader("Key findings")
    for line in T.key_findings(A):
        st.markdown(f"- {line}")
    st.caption("Percentages with 95% confidence intervals. Findings describe the women who took part "
               "(a convenience sample recruited largely through advocacy groups), not all Kenyan women.")
    st.subheader("Burden and access by group")
    t = pd.concat([T.ind_table(A[A["period12"] == 1], ["hmb", "sev_pain", "marker_sx"], "group", C.GROUP_ORDER),
                   T.ind_table(A, ["care_any", "hardship", "days_work3", "stigma"], "group", C.GROUP_ORDER)])
    st.plotly_chart(CH.dot_ci(t, "Indicator", ["All"] + C.GROUP_ORDER), use_container_width=True)
    st.caption(SMALL_NOTE + " Bleeding and pain items: women with a period in the past 12 months.")

    st.subheader("Sample flow")
    steps = derive.sample_flow(D, keep_none)
    st.plotly_chart(CH.flow(steps), use_container_width=True)
    st.caption("Women in menopause are routed past Sections 3–7 by the form, so they appear in T1 counts "
               "but cannot enter condition-based analyses.")


def page_t5():
    header("T5 · Diagnosis, per condition", "Diagnostic capacity and referral gaps (ultrasound, laparoscopy).",
           "Objective 2")
    s = T.diagnosis_summary(A)
    st.subheader("Diagnosis and delay by condition")
    t = pd.DataFrame({"Indicator": s["Condition"], "Group": "Diagnosed", "p": s["Delay ≥3 y"], "lo": s["Delay lo"],
                      "hi": s["Delay hi"], "n": s["Delay n"],
                      "k": (s["Delay ≥3 y"] * s["Delay n"]).round(), "small": s["Delay n"] < C.SMALL_N})
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Diagnostic delay of 3 years or more** (diagnosed women)")
        st.plotly_chart(CH.dot_ci(t, "Indicator", ["Diagnosed"], "% with delay ≥3 years (95% CI)"),
                        use_container_width=True)
    with c2:
        show = s[["Condition", "Know or suspect (Q29)", "Diagnosed", "Suspected only",
                  "Median age at diagnosis"]].set_index("Condition")
        st.markdown("**Counts**")
        st.dataframe(show, use_container_width=True)
    st.caption(SMALL_NOTE)
    key = st.radio("Condition", list(C.CONDITIONS), format_func=lambda k: C.CONDITIONS[k]["label"],
                   horizontal=True)
    n = int((A[f"dx_{key}"] == 1).sum())
    st.markdown(f"**{C.CONDITIONS[key]['label']}: {n} diagnosed women.**"
                + (" Fewer than 40 – describe, do not compare." if n < C.SMALL_N else ""))
    if n == 0:
        return
    for i, (title, tab) in enumerate(T.condition_items(A, key).items()):
        st.subheader(title)
        if title.startswith("Time"):
            labels = {v: v for v in C.DELAY_ORDER}
            st.plotly_chart(CH.stacked(tab, C.DELAY_ORDER, labels), use_container_width=True, key=f"t5_{i}")
            tab = tab.assign(Option=tab["Option"].astype(str))
        else:
            st.plotly_chart(CH.bars(tab, "Option", ["All"]), use_container_width=True, key=f"t5_{i}")
        table_view(T.display(tab, "Option"), f"T5_{key}_{i}")


def page_comparisons():
    header("Pre-specified comparisons",
           sub="Effect sizes with 95% CIs. p-values are reported for completeness, not for screening.")
    name = st.selectbox("Comparison", list(T.COMPARISONS))
    spec = T.COMPARISONS[name]
    na = int((A[spec["gcol"]] == spec["a"]).sum())
    nb = int((A[spec["gcol"]] == spec["b"]).sum())
    st.markdown(f"**{spec['a']}** (n={na}) vs **{spec['b']}** (n={nb})")
    if min(na, nb) < C.SMALL_N:
        st.warning("At least one group has fewer than 40 women: treat results as descriptive only.")
    res = T.comparison(A, name)
    st.markdown("**Proportions** – difference = first group minus second, in percentage points")
    st.plotly_chart(CH.effect_forest(res, "Difference (pp)"), use_container_width=True)
    if (res["Effect measure"] == "Rank-biserial r").any():
        st.markdown("**Ordered bands** – rank-biserial r (> 0: first group tends to higher bands)")
        st.plotly_chart(CH.effect_forest(res, "Rank-biserial r"), use_container_width=True)
    show = res.copy()
    show["Effect (95% CI)"] = [
        (f"{100 * e:+.1f} pp ({100 * lo:+.1f} to {100 * hi:+.1f})" if m.startswith("Diff")
         else f"{e:+.2f} ({lo:+.2f} to {hi:+.2f})") if pd.notna(e) else "–"
        for e, lo, hi, m in zip(show["Effect"], show["Effect low"], show["Effect high"], show["Effect measure"])]
    show["p"] = show["p"].map(lambda p: "–" if pd.isna(p) else ("<0.001" if p < 0.001 else f"{p:.3f}"))
    st.dataframe(show[["Outcome", spec["a"], spec["b"], "Effect (95% CI)", "Test", "p"]].set_index("Outcome"),
                 use_container_width=True)
    if name == "Lowest vs highest income band":
        st.subheader("All income bands")
        st.dataframe(T.trend_across(A, "income", C.INCOME_ORDER,
                                    ["spend_prod_500", "hardship", "hard_cannot", "care_any"]).set_index("Outcome"),
                     use_container_width=True)
    st.caption("Tests: chi-square; Fisher's exact (2×2) or Monte Carlo exact chi-square when an expected count "
               "is below 5; Mann–Whitney U for ordered bands. CIs: Newcombe (differences), bootstrap "
               "(rank-biserial).")


def page_models():
    header("Adjusted models (Firth logistic regression)",
           sub="Pre-specified outcomes and covariates. At most one covariate per ~10 events.")
    st.markdown("Covariates are added in the pre-specified order **age → insurance → income → education** "
                "until the events-per-variable budget is used up. Odds ratios with profile "
                "penalised-likelihood 95% CIs; complete-case analysis.")
    for lab, outcome in T.MODELS.items():
        st.subheader(lab)
        m = T.model(A, outcome)
        st.caption(f"Events: {m['events']} · non-events: {m['nonevents']} · parameter budget: {m['budget']}"
                   + (f" · not included (budget): {', '.join(m['dropped'])}" if m["dropped"] else ""))
        r = m["result"]
        if r is None:
            st.info("Too few events for an adjusted model; report the unadjusted proportions instead.")
            continue
        c1, c2 = st.columns([1.1, 1])
        with c1:
            st.plotly_chart(CH.or_forest(r.table()), use_container_width=True, key=f"m_{outcome}")
        with c2:
            tab = r.table()
            tab["OR (95% CI)"] = [f"{o:.2f} ({l:.2f}–{h:.2f})" for o, l, h in
                                  zip(tab["OR"], tab["OR low"], tab["OR high"])]
            st.dataframe(tab[["Term", "OR (95% CI)"]].set_index("Term"), use_container_width=True)
            st.caption(f"n = {r.n} complete cases. " + "; ".join(r.notes))


def page_behaviour():
    header("Behavioural baseline (Q24–26, Q86–87)",
           "Baseline care-seeking, prompt and importance – descriptive only.")
    st.info("These items describe care-seeking behaviour, what prompted it and how important women think it is. "
            "They are **not** a test of the Fogg Behaviour Model. The formal test – a motivation × ability × "
            "prompt map, the action line, segments needing a signal, facilitator or spark, and the treatment "
            "cascade – belongs in the follow-on survey with validated motivation and ability scales.")
    breakdown = st.selectbox("Break down by", ["Population group", "Insured vs uninsured", "Household income"])
    blocks = [
        R.Block("ind", "Care sought in the past 12 months (Q24)", cols=["care_any", "care_trained", "care_easy"]),
        R.Block("dist", "Care sought (Q24) – all answers", field="seek_care_period_related_symptoms"),
        R.Block("dist", "Reasons for not speaking to a provider (Q26) – barriers to ability",
                field="reasons_not_spoken_HCP"),
        R.Block("dist", "Something or someone prompted care-seeking (Q86)", field="sth_someone_remind_seek_care"),
        R.Block("ord", "Importance of seeking care (Q87) – motivation proxy", field="how_important_seeking_care",
                order=[v for v, _ in codebook.choices("how_important_seeking_care")]),
    ]
    for i, b in enumerate(blocks):
        render_block(b, breakdown, f"beh_{i}")
    st.subheader("Prompt × care sought")
    sub = A[A["care_any"].notna() & A["sth_someone_remind_seek_care"].notna()]
    if len(sub):
        lab = codebook.value_labels("sth_someone_remind_seek_care")
        tab = pd.crosstab(sub["sth_someone_remind_seek_care"].map(lab),
                          sub["care_any"].map({1.0: "Sought care", 0.0: "Did not"}), margins=True)
        st.dataframe(tab, use_container_width=True)
        st.caption("Cross-sectional: shows co-occurrence, not that prompts cause care-seeking.")


def page_quality():
    header("Data quality", sub="Item non-response is measured among women who were actually shown each "
                                "question (the form's skip logic is applied).")
    mm = T.missingness(D)
    sec = T.missing_by_section(mm)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.plotly_chart(CH.missing_bars(sec), use_container_width=True)
        st.caption("Red line: 10% flag threshold.")
    with c2:
        st.dataframe(sec.assign(**{"% missing": sec["% missing"].map(lambda p: f"{p:.1%}" if pd.notna(p) else "–")})
                     .set_index("Section"), use_container_width=True)
    flagged = mm[mm["Flag >10%"]]
    st.subheader(f"Items with more than 10% missing ({len(flagged)})")
    if flagged.empty:
        st.success("No item exceeds 10% non-response.")
    else:
        st.dataframe(flagged.assign(**{"% missing": flagged["% missing"].map("{:.1%}".format)}),
                     use_container_width=True, hide_index=True)
    st.subheader("Consistency checks")
    st.caption("Patterns the form currently allows. Complete-case analysis is used; these respondents are "
               "kept, and the derived indicators already apply the correct denominators.")
    st.dataframe(T.consistency(D), use_container_width=True, hide_index=True)
    with st.expander("All items"):
        st.dataframe(mm, use_container_width=True, hide_index=True)


def page_methods():
    header("Methods and limitations")
    st.markdown(open(os.path.join(os.path.dirname(__file__), "docs", "METHODS.md"), encoding="utf-8").read())
    st.subheader("Indicator definitions")
    st.dataframe(pd.DataFrame([vars(i) for i in derive.INDICATORS]).rename(
        columns={"col": "Variable", "label": "Indicator", "items": "Items", "denominator": "Denominator"}),
        use_container_width=True, hide_index=True)


def page_export():
    header("Export")
    st.markdown("Download every table (T1–T10), the comparisons, models and data-quality report as one Excel "
                "workbook, using the current population and filters. Each table uses its first listed "
                "breakdown.")
    if st.button("Build Excel workbook"):
        with st.spinner("Building…"):
            data = export.workbook(D, A, demo=is_demo)
        st.download_button("Download WEMA_tables.xlsx", data, file_name="WEMA_tables.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("---")
    st.markdown("**Analysis dataset** (derived indicators, no free text or phone numbers)")
    cols = ["_id", "_submission_time", "group", "age", "age_group", "education", "income", "county",
            "insurance_type", "period12"] + [i.col for i in derive.INDICATORS]
    cols = [c for c in cols if c in A]
    st.download_button("Download indicators CSV", A[cols].to_csv(index=False).encode("utf-8"),
                       file_name="WEMA_indicators.csv", mime="text/csv")


NAV.run()
