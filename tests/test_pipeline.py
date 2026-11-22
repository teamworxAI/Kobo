import io

import numpy as np
import pandas as pd

from wema import config as C, demo, derive, export, ingest, relevance, tables as T


def test_relevance_semantics():
    e = "/f/consent = 'Yes' and /f/S/period_12months != '7'"
    assert relevance.evaluate(e, {"consent": "Yes", "period_12months": "1"})
    assert not relevance.evaluate(e, {"consent": "Yes", "period_12months": "7"})
    assert relevance.evaluate(e, {"consent": "Yes"})            # blank != '7'
    assert not relevance.evaluate("/f/S/how_old_are_you >= 18", {})
    assert relevance.evaluate("selected( /f/S/x , '3')", {"x": "1 3"})


def row(**kw):
    base = dict(consent="Yes", how_old_are_you=30, had_menses="Yes", period_12months="1")
    base.update(kw)
    return base


def test_groups_and_indicators():
    raw = pd.DataFrame([
        row(supect_following_conditions="1", diagnose_HCP_endometriosis="Yes",
            long_first_noticed_endometriosis="6-8 years",
            describe_mestrual_heaviest_days="Moderate flow (need to change protection every 3-4 hours)",
            days_bleed_per_cycle="More than 7 days", seek_care_period_related_symptoms="4"),
        row(supect_following_conditions="3", diagnosed_HCP_uterine_fibroids="No",
            seek_care_period_related_symptoms="5", obtain_period_related_symptoms="Easy"),
        row(supect_following_conditions="7", seek_care_period_related_symptoms="2"),
        row(period_12months="7"),
        row(how_old_are_you=17),
    ])
    d = derive.derive(ingest.normalise(raw))
    assert list(d["group"][:3]) == [C.GRP_DX, C.GRP_SUSP, C.GRP_NONE]
    # design eligibility: menopause stays in (row 3); under-18 exits (row 4)
    assert list(d["analytic"]) == [True, True, True, True, False]
    assert d.loc[3, "group"] == C.GRP_UNCL
    assert len(derive.analytic(d, keep_menopause=False)) == 3
    assert d.loc[0, "hmb"] == 1 and d.loc[0, "hmb_flow"] == 0 and d.loc[0, "hmb_long"] == 1
    assert d.loc[0, "delay_long_endo"] == 1 and d.loc[0, "delay_long_any"] == 1
    assert d.loc[0, "care_any"] == 0
    assert np.isnan(d.loc[1, "care_any"])            # no worrying symptoms -> not in denominator
    assert np.isnan(d.loc[1, "care_easy"])           # Q25 answered without seeking care -> ignored
    assert d.loc[2, "care_trad_only"] == 1 and d.loc[2, "care_trained"] == 0
    a = derive.analytic(d, keep_no_condition=False)
    assert set(a["group"]) == {C.GRP_DX, C.GRP_SUSP}


def test_ingest_labels_none_answer_and_pii():
    raw = pd.DataFrame({
        "pei/burden_condition_places": ["None", "Severe burden"],
        "Section2/experience_pain_before_during_period": ["No pain", None],
        "Health_insurance/Have_any_Health_insurance": ["I do not have health insurance", "1"],  # label export
        "mpesa_phone_number": ["0712345678", "0700000000"],
        "Section2/experienced_period_related_symptoms/8": ["1", "0"],
        "Section2/experienced_period_related_symptoms/2": ["1", "1"],
    })
    df = ingest.normalise(raw)
    assert df.loc[0, "burden_condition_places"] == "None"      # a real answer, not blank
    assert "mpesa_phone_number" not in df.columns
    assert list(df["Have_any_Health_insurance"]) == ["4", "1"]
    assert df.loc[0, "experienced_period_related_symptoms"] == "2 8"
    assert df.loc[1, "experienced_period_related_symptoms"] == "2"


def test_csv_roundtrip_and_full_build():
    raw = demo.generate(150, seed=3)
    buf = io.StringIO()
    raw.to_csv(buf, index=False)
    again = ingest.read_export(buf.getvalue().encode(), "x.csv")
    d = derive.derive(again)
    a = derive.analytic(d)
    assert len(a) > 100
    for name in T.COMPARISONS:
        assert not T.comparison(a, name).empty
    assert T.missingness(d)["Shown to"].sum() > 0
    xlsx = export.workbook(d, a, demo=True)
    assert len(pd.ExcelFile(io.BytesIO(xlsx)).sheet_names) >= 15


def test_baseline_and_service_indicators():
    raw = pd.DataFrame([
        row(sth_someone_remind_seek_care="No, nothing or no one prompted me.",
            how_important_seeking_care="Very important", currently_using_HMC="Yes", main_reason_using_HMC="2",
            supect_following_conditions="1", diagnose_HCP_endometriosis="Yes",
            biggest_challenge_faced_get_endometriosis="3 1", describe_endometriosis_came_about="2",
            received_treatment_endometriosis="1 3", hear_about_this_survey="Fibroid support group",
            facility_usually_visited="Pharmacy or chemist"),
        row(sth_someone_remind_seek_care="I don't remember.", currently_using_HMC="Yes",
            main_reason_using_HMC="5", supect_following_conditions="3", diagnosed_HCP_uterine_fibroids="Yes",
            received_treatment_uterine_fibroids="10", hear_about_this_survey="Social media"),
    ])
    d = derive.derive(ingest.normalise(raw))
    assert d.loc[0, "prompt_any"] == 0 and np.isnan(d.loc[1, "prompt_any"])
    assert d.loc[0, "importance_high"] == 1
    assert d.loc[0, "hmc_therapeutic"] == 1 and d.loc[1, "hmc_therapeutic"] == 0
    assert d.loc[0, "dx_dismissed"] == 1 and d.loc[0, "dx_cost_barrier"] == 1 and d.loc[0, "dx_no_equipment"] == 0
    assert d.loc[0, "dx_misdiagnosed"] == 1
    assert d.loc[0, "treatments_any"] == "1 3" and d.loc[0, "treated_any"] == 1
    assert d.loc[1, "treated_any"] == 0                      # "No treatment received"
    assert list(d["recruit_group"]) == ["Support / advocacy group", "Other route"]
    assert d.loc[0, "facility_type"] == "Pharmacy"
    assert len(derive.analytic(d, exclude_support_groups=True)) == 1


def test_durations_only_when_metadata_present():
    d = derive.derive(demo.generate(60, seed=5))
    assert T.durations(d) is None
    raw = demo.generate(60, seed=5)
    raw["_start"] = pd.Timestamp("2026-10-01T10:00Z")
    raw["_end"] = raw["_start"] + pd.Timedelta(minutes=22)
    out = T.durations(derive.derive(raw))
    assert out.iloc[-1]["Median (min)"] == 22
