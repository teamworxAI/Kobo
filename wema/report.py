"""The ten table shells (T1-T10) declared once, used by the dashboard and the export.

Each shell lists blocks. A block is computed for a chosen breakdown and returns a
tidy table (for charts) that tables.display() turns into the published layout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from . import codebook, config as C, tables as T

# breakdown key -> (column, level order)
BREAKDOWNS: dict[str, tuple[str, list[str]]] = {
    "Population group": ("group", C.GROUP_ORDER),
    "Diagnosed vs suspected": ("group", [C.GRP_DX, C.GRP_SUSP]),
    "Age group": ("age_group", C.AGE_LABELS),
    "Education": ("education", C.EDU_ORDER),
    "Household income": ("income", C.INCOME_ORDER),
    "Insured vs uninsured": ("insured", ["Insured", "Uninsured"]),
    "Insurance type": ("insurance_type", ["SHA only", "SHA + private", "Private only", "Uninsured"]),
    "Nairobi vs other counties": ("nairobi", ["Nairobi", "Other counties"]),
    "County / town": ("county", ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Other county"]),
    "HMB proxy": ("hmb_group", ["HMB proxy", "No HMB"]),
    "Period in past 12 months": ("period12_lab", ["Period in past 12 months", "No period in past 12 months"]),
    "None (all respondents)": (None, []),
}

Mask = Callable[[pd.DataFrame], pd.Series]


@dataclass
class Block:
    kind: str                      # ind | dist | ord | cat | num
    title: str
    cols: list[str] = field(default_factory=list)   # ind
    field: str | None = None       # dist / ord / cat / num
    order: list[str] | None = None  # ord / cat
    mask: Mask | None = None
    note: str = ""
    drop_values: set | None = None
    chart: str = "auto"

    def compute(self, a: pd.DataFrame, breakdown: str) -> pd.DataFrame:
        by, levels = BREAKDOWNS[breakdown]
        if self.mask is not None:
            a = a[self.mask(a).fillna(False).astype(bool)]
        if self.kind == "ind":
            return T.ind_table(a, self.cols, by, levels or None)
        if self.kind == "dist":
            return T.dist_table(a, self.field, by, levels or None, drop_values=self.drop_values)
        if self.kind == "ord":
            return T.ordinal_table(a, self.field, self.order, by, levels or None)
        if self.kind == "cat":
            return T.cat_table(a, self.field, self.order, by, levels or None, self.title)
        if self.kind == "num":
            return T.numeric_summary(a, self.field, by, levels or None)
        raise ValueError(self.kind)

    def display(self, t: pd.DataFrame) -> pd.DataFrame:
        if self.kind == "num":
            return t.set_index("Group").round(1)
        if self.kind == "ord":
            t = t.copy()
            t["Option"] = t["Option"].astype(str)
        return T.display(t, "Indicator" if self.kind == "ind" else "Option")


@dataclass
class Shell:
    key: str
    title: str
    objective: str
    statement: str
    breakdowns: list[str]
    blocks: list[Block]


def _period(a):
    return a["period12"] == 1


def _no_period(a):
    return a["period12"] == 0


def _sought(a):
    return a["care_any"] == 1


def _insured(a):
    return a["ins_any"] == 1


SHELLS: list[Shell] = [
    Shell("T1", "Sample", "Context",
          "Who the findings describe (and who they do not).",
          ["Population group", "None (all respondents)", "Nairobi vs other counties"],
          [Block("num", "Age (years)", field="age"),
           Block("cat", "Age group", field="age_group", order=C.AGE_LABELS),
           Block("cat", "County / town of residence (Q2)", field="county",
                 order=BREAKDOWNS["County / town"][1]),
           Block("cat", "Education (Q3, grouped)", field="education", order=C.EDU_ORDER),
           Block("cat", "Monthly household income (Q9, grouped)", field="income", order=C.INCOME_ORDER,
                 note="'Prefer not to say' excluded from the denominator."),
           Block("dist", "Occupation (Q4)", field="main_source_income"),
           Block("cat", "Health insurance (Q80)", field="insurance_type",
                 order=BREAKDOWNS["Insurance type"][1]),
           Block("dist", "Recruitment route (Q92)", field="hear_about_this_survey",
                 note="Most women reached through support groups means the sample leans towards "
                      "women already engaged with these conditions."),
           Block("dist", "Menstrual status: period in the past 12 months (Q12)", field="period_12months"),
           Block("dist", "Current hormonal contraception (Q14)", field="currently_using_HMC")]),
    Shell("T2", "Symptom burden", "Scale of need",
          "Scale of need; heavy menstrual bleeding as a public-health issue.",
          ["Population group", "Age group", "Nairobi vs other counties", "Household income"],
          [Block("ind", "Cycle and symptom indicators – women with a period in the past 12 months",
                 cols=["hmb", "hmb_flow", "hmb_long", "sev_pain", "marker_sx", "irregular",
                       "fatigue_dizzy", "anaemia"], mask=_period),
           Block("ord", "Period pain severity (Q21) – women with a period in the past 12 months",
                 field="experience_pain_before_during_period", order=C.PAIN_ORDER, mask=_period),
           Block("dist", "Period-related symptoms (Q23)", field="experienced_period_related_symptoms",
                 mask=_period),
           Block("ind", "Same indicators – women with NO period in the past 12 months (reported separately)",
                 cols=["hmb", "sev_pain", "marker_sx", "irregular"], mask=_no_period,
                 note="Mostly women on hormonal contraception, pregnant or breastfeeding; their answers "
                      "describe usual or past periods and are not pooled with the main estimates."),
           Block("ind", "Emergency care for period symptoms (Q85) – all women",
                 cols=["emergency"])]),
    Shell("T3", "Awareness", "Objective 1",
          "Content and audience for information.",
          ["Education", "Nairobi vs other counties", "County / town", "Age group", "Population group"],
          [Block("ind", "Awareness indicators", cols=["aware_any", "understand_good"]),
           Block("dist", "Conditions familiar before today (Q27)", field="familiar_with_these_conditions"),
           Block("ord", "How well the condition names made sense (Q28)", field="condition_make_sense",
                 order=C.UNDERSTAND_ORDER),
           Block("dist", "Most urgent need (Q88) – top unmet need", field="urgent_need_manage_condition")]),
    Shell("T4", "Care-seeking", "Objective 2",
          "Where women go first, and what stops them.",
          ["Insured vs uninsured", "Household income", "Insurance type", "Population group",
           "Nairobi vs other counties"],
          [Block("ind", "Care sought in the past 12 months – women with symptoms of concern",
                 cols=["care_any", "care_trained", "care_trad_only", "care_easy"],
                 note="Denominator excludes women who said they had no symptoms that worried them."),
           Block("dist", "Care sought for period symptoms (Q24) – all answers",
                 field="seek_care_period_related_symptoms"),
           Block("ord", "Ease of obtaining care (Q25) – women who sought care",
                 field="obtain_period_related_symptoms",
                 order=[v for v, _ in codebook.choices("obtain_period_related_symptoms")], mask=_sought,
                 note="The form also shows Q25 to women who did not seek care; those answers are excluded."),
           Block("dist", "Reasons for not speaking to a provider (Q26)", field="reasons_not_spoken_HCP"),
           Block("dist", "Facility usually visited (Q11)", field="facility_usually_visited")]),
    # T5 is condition-specific and is rendered by a dedicated page / export routine
    Shell("T6", "Stigma and psychosocial", "Objectives 3 and 5",
          "Support services and messaging.",
          ["Diagnosed vs suspected", "Population group", "Age group"],
          [Block("ind", "Psychosocial indicators",
                 cols=["stigma", "supported", "confidant", "mood_often", "rel_affected"]),
           Block("ord", "Periods affect mood (Q67)", field="often_menstrual_affect_mood", order=C.MOOD_ORDER),
           Block("ord", "Symptoms affected relationships (Q68)", field="symptoms_affected_relationships",
                 order=C.REL_ORDER),
           Block("ord", "Feels supported by people around (Q69)", field="feel_supported_people_around_you",
                 order=C.SUPPORT_ORDER),
           Block("ord", "Experienced stigma or disbelief (Q70)", field="ever_experiencedStigma_disbelief",
                 order=["No", "Sometimes", "Yes, many times"]),
           Block("dist", "Someone to talk to (Q71)", field="have_someone_talk_to")]),
    Shell("T7", "Economic burden", "Objective 4",
          "SHA brief: out-of-pocket burden and lost productivity.",
          ["Insured vs uninsured", "Household income", "HMB proxy", "Population group"],
          [Block("ind", "Economic indicators",
                 cols=["spend_prod_500", "spend_care_5k", "hardship", "hard_borrow", "hard_cannot",
                       "hard_forwent", "burden_mod_sev", "days_work3", "days_hh3"]),
           Block("ord", "Spend on menstrual products / management, past 30 days (Q72)",
                 field="spend_manage_menstrual_condition", order=C.PRODUCT_BANDS,
                 note="Band distribution is the primary result; 'Not sure' excluded."),
           Block("ord", "Spend on medication, visits, transport or alternative care, past 12 months (Q73)",
                 field="spend_pain_doctor_visit", order=C.CARE_BANDS),
           Block("num", "Sensitivity only: care spend using band midpoints (KES, past 12 months)",
                 field="spend_care_mid",
                 note="Midpoints are assumptions (open top band = 1.5× its lower bound). Use for "
                      "sensitivity, not as the headline estimate."),
           Block("dist", "How care was paid for (Q74)", field="borrow_sell_pay_health"),
           Block("dist", "When treatment is unaffordable (Q79)", field="do_when_cannot_afford_treatment"),
           Block("ord", "Financial burden (Q76)", field="burden_condition_places", order=C.BURDEN_ORDER),
           Block("ord", "Days of work or school lost a month (Q77)", field="days_missed_each_month",
                 order=C.DAYS_ORDER),
           Block("ord", "Days of household duties lost a month (Q78)", field="days_hh_duties_missed",
                 order=C.DAYS_ORDER)]),
    Shell("T8", "Insurance", "Objective 4",
          "SHA brief: coverage gaps in the benefit package.",
          ["Insurance type", "Household income", "Population group"],
          [Block("ind", "Insurance indicators", cols=["ins_any", "ins_sha"]),
           Block("ind", "Among insured women", cols=["ins_covered", "ins_cover_dk", "ins_upfront", "ins_denied"],
                 mask=_insured,
                 note="Q81–83 are shown to uninsured women too; only insured women are analysed."),
           Block("dist", "Type of insurance (Q80)", field="Have_any_Health_insurance"),
           Block("dist", "Perceived coverage of these conditions (Q81) – insured",
                 field="health_insurance_cover_diag_treat", mask=_insured),
           Block("dist", "Paid upfront and claimed back (Q82) – insured", field="payout_of_pocket", mask=_insured),
           Block("dist", "Claim denied (Q83) – insured", field="ever_denied_claim", mask=_insured)]),
    Shell("T9", "Coping and needs", "Objectives 5 and 6",
          "Priorities for services and research.",
          ["Diagnosed vs suspected", "Population group", "Household income"],
          [Block("ind", "Traditional care", cols=["trad_any", "care_trad_only"]),
           Block("dist", "How symptoms are managed (Q84)", field="manage_period_related_symptoms"),
           Block("dist", "Most urgent need (Q88)", field="urgent_need_manage_condition")]),
    Shell("T10", "Data and digital", "Objective 6",
          "Design of the Awodee research platform.",
          ["Age group", "Education", "Population group"],
          [Block("ind", "Digital indicators", cols=["uses_tracker", "share_yes"]),
           Block("dist", "Apps or devices used to track health (Q89)", field="use_health_app_device"),
           Block("dist", "What 'data privacy' means (Q90)", field="data_privacy_mean"),
           Block("dist", "Willing to share anonymised data for research (Q91)",
                 field="share_health_info_privacy_protected")]),
]
SHELL = {s.key: s for s in SHELLS}


def _shell_builder(shell: Shell):
    def build(a: pd.DataFrame):
        out = []
        for b in shell.blocks:
            t = b.compute(a, shell.breakdowns[0])
            out.append((b.title, b.display(t)))
        return out
    return build


def _t5(a: pd.DataFrame):
    out = [("Diagnosis summary by condition", T.diagnosis_summary(a).set_index("Condition"))]
    for key, c in C.CONDITIONS.items():
        for title, t in T.condition_items(a, key).items():
            lab = "Option"
            out.append((f"{c['label']} – {title}", T.display(t.assign(Option=t["Option"].astype(str)), lab)))
    return out


TABLE_SPECS = {f"{s.key} {s.title}"[:31]: _shell_builder(s) for s in SHELLS}
TABLE_SPECS = dict(sorted({**TABLE_SPECS, "T5 Diagnosis": _t5}.items(), key=lambda kv: int(kv[0].split()[0][1:])))
