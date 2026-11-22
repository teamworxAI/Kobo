"""Analysis populations and derived indicators.

Every indicator is coded 1 / 0 / NaN. NaN means "not in the denominator"
(not asked, not applicable, don't know / prefer not to say, or missing), so a
plain mean over non-missing rows gives the proportion with the right denominator.
The denominator rule for each indicator is listed in INDICATORS.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import codebook, config as C


@dataclass(frozen=True)
class Indicator:
    col: str
    label: str
    items: str
    denominator: str


INDICATORS: list[Indicator] = [
    Indicator("hmb", "Heavy menstrual bleeding (HMB) proxy", "Q19, Q20",
              "Answered flow or duration (excl. 'Other' / 'Don't know')"),
    Indicator("hmb_flow", "Heavy or very heavy flow", "Q20", "Answered flow"),
    Indicator("hmb_long", "Bleeding more than 7 days", "Q19", "Answered duration"),
    Indicator("sev_pain", "Severe or extremely severe period pain", "Q21", "Answered Q21"),
    Indicator("marker_sx", "Endometriosis marker symptom (pain with sex, bowel or urination)",
              "Q23", "Answered Q23"),
    Indicator("irregular", "Irregular cycle (<24 or >38 days)", "Q18",
              "Cycle length known (excl. stopped / other / don't know)"),
    Indicator("fatigue_dizzy", "Fatigue, weakness, dizziness or fainting", "Q23", "Answered Q23"),
    Indicator("anaemia", "Ever told anaemia / low iron", "Q12b", "Yes or No"),
    Indicator("emergency", "Emergency care for period symptoms (ever)", "Q85", "Answered Q85"),
    Indicator("care_any", "Care sought, past 12 months (any provider)", "Q24",
              "Had period symptoms of concern (excl. 'no symptoms that worried me')"),
    Indicator("care_trained", "Care from a doctor or nurse (alone or with traditional)", "Q24",
              "As above"),
    Indicator("care_trad_only", "Traditional / complementary provider only", "Q24", "As above"),
    Indicator("care_easy", "Obtaining care was easy or very easy", "Q25",
              "Sought care (Q24 = any provider)"),
    Indicator("trad_any", "Uses traditional / herbal care or remedies", "Q24, Q84",
              "Answered Q24 or Q84"),
    Indicator("aware_any", "Familiar with at least one condition before today", "Q27",
              "Answered Q27"),
    Indicator("understand_good", "Condition names made fairly good / a lot of sense", "Q28",
              "Answered Q28"),
    Indicator("stigma", "Experienced stigma or disbelief (many times or sometimes)", "Q70",
              "Answered Q70 (excl. 'Not sure')"),
    Indicator("supported", "Feels supported always or sometimes", "Q69", "Answered Q69"),
    Indicator("confidant", "Has someone to talk to", "Q71", "Answered Q71 (excl. prefer not to say)"),
    Indicator("mood_often", "Periods affect mood often or every month", "Q67", "Answered Q67"),
    Indicator("rel_affected", "Symptoms affected relationships (somewhat / very much)", "Q68",
              "Answered Q68"),
    Indicator("hardship", "Financial hardship (any of the three components)", "Q74, Q75, Q79",
              "Answered at least one component"),
    Indicator("hard_borrow", "Borrowed or received help to pay", "Q74, Q79", "Answered Q74 or Q79"),
    Indicator("hard_cannot", "Could not afford care", "Q74, Q79", "Answered Q74 or Q79"),
    Indicator("hard_forwent", "Postponed or gave up essentials", "Q75", "Answered Q75"),
    Indicator("spend_prod_500", "Product spend above KES 500 in past 30 days", "Q72",
              "Answered Q72 (excl. not sure)"),
    Indicator("spend_care_5k", "Care spend above KES 5,000 in past 12 months", "Q73",
              "Answered Q73 (excl. not sure)"),
    Indicator("burden_mod_sev", "Moderate or severe financial burden", "Q76", "Answered Q76"),
    Indicator("days_work3", "Lost 3+ days a month of work or school", "Q77", "Answered Q77"),
    Indicator("days_hh3", "Lost 3+ days a month of household duties", "Q78", "Answered Q78"),
    Indicator("ins_any", "Has any health insurance", "Q80", "Answered Q80"),
    Indicator("ins_sha", "Has SHA cover", "Q80", "Answered Q80"),
    Indicator("ins_covered", "Believes insurance covers these conditions (fully / partly)", "Q81",
              "Insured, answered Q81 (excl. don't know)"),
    Indicator("ins_cover_dk", "Does not know whether these conditions are covered", "Q81",
              "Insured, answered Q81"),
    Indicator("ins_upfront", "Paid upfront and claimed back (frequently / occasionally)", "Q82",
              "Insured, excl. not applicable"),
    Indicator("ins_denied", "Had an insurance claim denied", "Q83",
              "Insured and filed a claim (excl. not applicable)"),
    Indicator("dx_any", "Diagnosed with at least one condition", "Q32/39/46/53/60",
              "Answered Section 4"),
    Indicator("delay_long_any", "Diagnostic delay of 3+ years (any condition)", "Q36/43/50/57/64",
              "Diagnosed, delay reported (excl. diagnosed without symptoms)"),
    Indicator("dx_imaging_any", "Diagnosed using ultrasound / MRI / imaging (any condition)",
              "Q33/40/47/54", "Diagnosed with a structural condition, method reported"),
    Indicator("dx_surgical_any", "Diagnosed at laparoscopy or other surgery (any condition)",
              "Q33/40/47", "Diagnosed with endometriosis, adenomyosis or fibroids, method reported"),
    Indicator("uses_tracker", "Uses an app or device to track health", "Q89", "Answered Q89"),
    Indicator("share_yes", "Would share anonymised data for research", "Q91", "Answered Q91"),
]
IND = {i.col: i for i in INDICATORS}


def _has(series: pd.Series, codes) -> pd.Series:
    codes = {codes} if isinstance(codes, str) else set(codes)
    return series.map(lambda v: np.nan if v is None or (isinstance(v, float) and np.isnan(v))
                      else float(bool(codes & set(str(v).split()))))


def _in(series: pd.Series, yes, valid=None, exclude=()) -> pd.Series:
    yes = set(yes)
    exclude = set(exclude)

    def f(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v in exclude:
            return np.nan
        if valid is not None and v not in valid:
            return np.nan
        return float(v in yes)

    return series.map(f)


def _any(*cols: pd.Series) -> pd.Series:
    m = pd.concat(cols, axis=1)
    out = m.max(axis=1, skipna=True)
    return out.where(m.notna().any(axis=1))


def _ordinal(series: pd.Series, order: list[str]) -> pd.Series:
    pos = {v: i for i, v in enumerate(order)}
    return series.map(lambda v: pos.get(v, np.nan)).astype(float)


def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Add population flags and indicators. Returns a new frame (all rows kept)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
        return _derive(df).copy()


def _derive(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    n = len(d)

    def get(c: str) -> pd.Series:
        if c not in d:
            return pd.Series([None] * n, index=d.index, dtype=object)
        s = d[c]
        if s.dtype.kind in "if":
            return s
        return pd.Series([None if v is None or (not isinstance(v, str) and pd.isna(v)) else v
                          for v in s], index=d.index, dtype=object)

    # ---- eligibility (B1) -------------------------------------------------
    age = pd.to_numeric(get("how_old_are_you"), errors="coerce")
    d["age"] = age
    d["consented"] = get("consent").eq("Yes")
    d["adult"] = age.ge(18)
    d["menstruated"] = get("had_menses").eq("Yes")
    d["menopause"] = get("period_12months").eq(C.PERIOD_MENOPAUSE)
    d["eligible_base"] = d["consented"] & d["adult"] & d["menstruated"]
    # The form routes women in menopause past Sections 3-7, so they cannot enter
    # condition-based analyses; they are counted in the sample flow and T1 only.
    d["analytic"] = d["eligible_base"] & ~d["menopause"]
    d["period12"] = get("period_12months").map(
        lambda v: np.nan if v is None else float(v == C.PERIOD_YES))
    d["period12_lab"] = d["period12"].map({1.0: "Period in past 12 months", 0.0: "No period in past 12 months"})
    d["no_period_reason"] = get("period_12months").map(
        lambda v: None if v in (None, C.PERIOD_YES) else codebook.short(
            codebook.value_labels("period_12months").get(v, v), 40))

    # ---- condition status -------------------------------------------------
    q29 = get("supect_following_conditions")
    gates_answered = pd.Series(False, index=d.index)
    for key, c in C.CONDITIONS.items():
        gate = get(c["gate"])
        d[f"dx_{key}"] = gate.map(lambda v: np.nan if v is None else float(v == "Yes"))
        d[f"q29_{key}"] = _has(q29, c["q29"])
        d[f"susp_{key}"] = ((d[f"q29_{key}"] == 1) & (d[f"dx_{key}"] != 1)).astype(float).where(
            q29.notna())
        gates_answered |= gate.notna()
        delay = get(c["delay"])
        d[f"delay_long_{key}"] = _in(delay, C.DELAY_LONG, valid=set(C.DELAY_ORDER)).where(
            d[f"dx_{key}"] == 1)
        d[f"delay_ord_{key}"] = _ordinal(delay, C.DELAY_ORDER).where(d[f"dx_{key}"] == 1)
    for key, c in C.CONDITIONS.items():
        meth = get(c["method"]).where(d[f"dx_{key}"] == 1)
        d[f"dx_imaging_{key}"] = _has(meth, C.METHOD_IMAGING[key]) if C.METHOD_IMAGING[key] else np.nan
        d[f"dx_surgical_{key}"] = _has(meth, C.METHOD_SURGICAL[key]) if C.METHOD_SURGICAL[key] else np.nan
    img = [f"dx_imaging_{k}" for k in C.CONDITIONS if C.METHOD_IMAGING[k]]
    sur = [f"dx_surgical_{k}" for k in C.CONDITIONS if C.METHOD_SURGICAL[k]]
    d["dx_imaging_any"] = d[img].max(axis=1, skipna=True)
    d["dx_surgical_any"] = d[sur].max(axis=1, skipna=True)
    dx_cols = [f"dx_{k}" for k in C.CONDITIONS]
    d["dx_any"] = d[dx_cols].max(axis=1, skipna=True).where(gates_answered)
    d["n_dx"] = d[dx_cols].sum(axis=1, min_count=1)
    d["q29_any"] = _has(q29, [c["q29"] for c in C.CONDITIONS.values()])
    d["q29_none"] = _has(q29, [C.Q29_KNOW_NONE, C.Q29_SUSPECT_NONE])
    d["delay_long_any"] = d[[f"delay_long_{k}" for k in C.CONDITIONS]].max(axis=1, skipna=True)

    def group(row):
        if row["dx_any"] == 1:
            return C.GRP_DX
        if row["q29_any"] == 1:
            return C.GRP_SUSP
        if row["q29_none"] == 1:
            return C.GRP_NONE
        return C.GRP_UNCL

    d["group"] = d.apply(group, axis=1)
    d["know_or_suspect"] = d["group"].isin([C.GRP_DX, C.GRP_SUSP])
    # consistency flags (the form does not enforce these)
    d["flag_q29_contradiction"] = (d["q29_any"] == 1) & (d["q29_none"] == 1)
    d["flag_dx_not_in_q29"] = pd.concat(
        [(d[f"dx_{k}"] == 1) & (d[f"q29_{k}"] == 0) for k in C.CONDITIONS], axis=1).any(axis=1)

    # ---- breakdown variables ----------------------------------------------
    d["age_group"] = pd.cut(age, C.AGE_BINS, right=False, labels=C.AGE_LABELS).astype(object)
    d["education"] = get("highest_level_education").map(C.EDU_MAP)
    d["income"] = get("avg_monthly_household_income").map(C.INCOME_MAP)
    d["income_ord"] = _ordinal(d["income"], C.INCOME_ORDER)
    res = get("residence")
    d["county"] = res.map(lambda v: None if v is None else ("Other county" if v == "Other" else v))
    d["nairobi"] = res.map(lambda v: None if v is None else ("Nairobi" if v == "Nairobi" else "Other counties"))
    other_txt = get("current_residence_other").fillna("").astype(str).str.lower()
    d["rural_reported"] = np.where(other_txt.str.contains("rural"), "Rural (self-reported)",
                                   np.where(other_txt.str.contains("urban|town|city"), "Urban (self-reported)", None))
    ins = get("Have_any_Health_insurance")
    d["insurance_type"] = ins.map(C.INS_TYPE)
    d["ins_any"] = _in(ins, C.INS_SHA | C.INS_PRIVATE_ONLY)
    d["ins_sha"] = _in(ins, C.INS_SHA)
    d["insured"] = d["ins_any"].map({1.0: "Insured", 0.0: "Uninsured"})
    d["recruitment"] = get("hear_about_this_survey").map(
        lambda v: None if v is None else ("Support group" if "support group" in v else v))

    # ---- symptom burden ---------------------------------------------------
    flow = get("describe_mestrual_heaviest_days")
    bleed = get("days_bleed_per_cycle")
    d["hmb_flow"] = _in(flow, C.FLOW_HEAVY, exclude=C.FLOW_VALID_EXCLUDE)
    d["hmb_long"] = _in(bleed, {C.BLEED_GT7}, valid=C.BLEED_VALID)
    d["hmb"] = _any(d["hmb_flow"], d["hmb_long"])
    d["hmb_group"] = d["hmb"].map({1.0: "HMB proxy", 0.0: "No HMB"})
    pain = get("experience_pain_before_during_period")
    d["sev_pain"] = _in(pain, C.PAIN_SEVERE, valid=set(C.PAIN_ORDER))
    d["pain_ord"] = _ordinal(pain, C.PAIN_ORDER)
    sx = get("experienced_period_related_symptoms")
    d["marker_sx"] = _has(sx, [C.SX_DYSPAREUNIA, C.SX_DYSCHEZIA, C.SX_DYSURIA])
    d["fatigue_dizzy"] = _has(sx, [C.SX_FATIGUE, C.SX_DIZZY])
    d["irregular"] = _in(get("avg_often_period_come"), {C.CYCLE_SHORT, C.CYCLE_LONG}, valid=C.CYCLE_VALID)
    d["anaemia"] = _in(get("have_anaemia_low_iron"), {"Yes"}, valid={"Yes", "No"})
    d["emergency"] = _in(get("ever_seek_emergency_medical_care"),
                         set(codebook.value_labels("ever_seek_emergency_medical_care")) - {C.EMERGENCY_NEVER})

    # ---- care-seeking -----------------------------------------------------
    care = get("seek_care_period_related_symptoms")
    need = {C.CARE_TRAINED_ONLY, C.CARE_TRAD_ONLY, C.CARE_BOTH, C.CARE_NOT_DISCUSSED}
    d["care_any"] = _in(care, {C.CARE_TRAINED_ONLY, C.CARE_TRAD_ONLY, C.CARE_BOTH}, valid=need)
    d["care_trained"] = _in(care, {C.CARE_TRAINED_ONLY, C.CARE_BOTH}, valid=need)
    d["care_trad_only"] = _in(care, {C.CARE_TRAD_ONLY}, valid=need)
    # Q25 is shown to everyone except 'no worrying symptoms' (form A3 issue); keep
    # only women who actually sought care.
    ease = get("obtain_period_related_symptoms").where(d["care_any"] == 1)
    d["ease_ord"] = _ordinal(ease, [v for v, _ in codebook.choices("obtain_period_related_symptoms")])
    d["care_easy"] = _in(ease, {"Easy", "Very easy"})

    trad_cope = _has(get("manage_period_related_symptoms"), {"4"})  # herbal / traditional remedies
    d["trad_any"] = _any(_in(care, {C.CARE_TRAD_ONLY, C.CARE_BOTH}, valid=need), trad_cope)

    # ---- awareness --------------------------------------------------------
    fam = get("familiar_with_these_conditions")
    d["aware_n"] = fam.map(lambda v: np.nan if v is None else float(
        len(set(str(v).split()) & set(C.Q27_CONDITION_CODES))))
    d["aware_any"] = (d["aware_n"] > 0).astype(float).where(d["aware_n"].notna())
    for code, lab in codebook.choices("familiar_with_these_conditions"):
        if code in C.Q27_CONDITION_CODES:
            d[f"aware_{code}"] = _has(fam, code)
    und = get("condition_make_sense")
    d["understand_good"] = _in(und, C.UNDERSTAND_GOOD, valid=set(C.UNDERSTAND_ORDER))
    d["understand_ord"] = _ordinal(und, C.UNDERSTAND_ORDER)

    # ---- psychosocial -----------------------------------------------------
    d["stigma"] = _in(get("ever_experiencedStigma_disbelief"), C.STIGMA_YES, exclude={C.STIGMA_NOT_SURE})
    d["supported"] = _in(get("feel_supported_people_around_you"), C.SUPPORT_YES)
    d["confidant"] = _in(get("have_someone_talk_to"), C.CONFIDANT_YES, exclude=C.PREFER_NOT)
    d["mood_often"] = _in(get("often_menstrual_affect_mood"), {"Often", "Every month"})
    d["rel_affected"] = _in(get("symptoms_affected_relationships"), {"Somewhat", "Yes, very much"})

    # ---- economic ---------------------------------------------------------
    prod = get("spend_manage_menstrual_condition")
    carex = get("spend_pain_doctor_visit")
    d["spend_prod_ord"] = _ordinal(prod, C.PRODUCT_BANDS)
    d["spend_care_ord"] = _ordinal(carex, C.CARE_BANDS)
    d["spend_prod_mid"] = prod.map(dict(zip(C.PRODUCT_BANDS, C.PRODUCT_MID))).astype(float)
    d["spend_care_mid"] = carex.map(dict(zip(C.CARE_BANDS, C.CARE_MID))).astype(float)
    d["spend_care_5k"] = (d["spend_care_ord"] >= 3).astype(float).where(d["spend_care_ord"].notna())
    d["spend_prod_500"] = (d["spend_prod_ord"] >= 2).astype(float).where(d["spend_prod_ord"].notna())
    borrow = get("borrow_sell_pay_health")
    afford = get("do_when_cannot_afford_treatment")
    q79_valid = afford.map(lambda v: v is not None and set(str(v).split()) != {C.AFFORD_OTHER})
    a_help = _has(afford, C.AFFORD_HELP).where(q79_valid)
    a_without = _has(afford, C.AFFORD_WITHOUT).where(q79_valid)
    d["hard_borrow"] = _any(_in(borrow, C.BORROW_YES), a_help)
    d["hard_cannot"] = _any(_in(borrow, {C.BORROW_CANNOT_AFFORD}), a_without)
    d["hard_forwent"] = _in(get("postpone_important_expenses"), {"Yes"}, valid={"Yes", "No"})
    d["hardship"] = _any(d["hard_borrow"], d["hard_cannot"], d["hard_forwent"])
    d["burden_mod_sev"] = _in(get("burden_condition_places"), {"Moderate burden", "Severe burden"})
    d["burden_ord"] = _ordinal(get("burden_condition_places"), C.BURDEN_ORDER)
    d["days_work3"] = _in(get("days_missed_each_month"), C.DAYS_3PLUS, valid=set(C.DAYS_ORDER))
    d["days_hh3"] = _in(get("days_hh_duties_missed"), C.DAYS_3PLUS, valid=set(C.DAYS_ORDER))
    d["days_work_ord"] = _ordinal(get("days_missed_each_month"), C.DAYS_ORDER)
    d["days_hh_ord"] = _ordinal(get("days_hh_duties_missed"), C.DAYS_ORDER)

    # ---- insurance (Q81-83 are shown to everyone; analyse the insured) ----
    insured = d["ins_any"] == 1
    cover = get("health_insurance_cover_diag_treat")
    d["ins_covered"] = _in(cover, C.COVER_YES, exclude={C.COVER_DK}).where(insured)
    d["ins_cover_dk"] = _in(cover, {C.COVER_DK}).where(insured)
    d["ins_upfront"] = _in(get("payout_of_pocket"), C.UPFRONT_YES, exclude={C.UPFRONT_NA}).where(insured)
    d["ins_denied"] = _in(get("ever_denied_claim"), {"Yes"}, valid={"Yes", "No"}).where(insured)

    # ---- digital ----------------------------------------------------------
    apps = get("use_health_app_device")  # code "1" = "No, I don't use any device or app"
    d["uses_tracker"] = apps.map(lambda v: np.nan if v is None else float(bool(set(str(v).split()) - {"1"})))
    d["share_yes"] = _in(get("share_health_info_privacy_protected"), {"1"}, exclude={"4"})
    return d


def analytic(d: pd.DataFrame, keep_no_condition: bool = True) -> pd.DataFrame:
    """The B1 analysis population."""
    a = d[d["analytic"]]
    if not keep_no_condition:
        a = a[a["group"] != C.GRP_NONE]
    return a


def sample_flow(d: pd.DataFrame, keep_no_condition: bool = True) -> list[tuple[str, int]]:
    steps = [("Submissions received", len(d))]
    m = d["consented"]
    steps.append(("Gave consent", int(m.sum())))
    m &= d["adult"]
    steps.append(("Aged 18 or over", int(m.sum())))
    m &= d["menstruated"]
    steps.append(("Have ever menstruated", int(m.sum())))
    m &= ~d["menopause"]
    steps.append(("Not in menopause (routed past Sections 3-7 by the form)", int(m.sum())))
    if not keep_no_condition:
        m &= d["group"] != C.GRP_NONE
        steps.append(("Know or suspect a condition (no-condition group dropped)", int(m.sum())))
    return steps
