"""Guard against a redeployed form silently changing what the stored codes mean."""
from wema import codebook as cb, config as C


def lab(field, value):
    return cb.value_labels(field)[value]


def test_condition_codes():
    for c in C.CONDITIONS.values():
        assert lab("supect_following_conditions", c["q29"]).lower().startswith(c["label"].split()[0].lower()[:4]) \
            or c["label"].startswith("PMOS")
        assert c["gate"] in cb.fields() and c["delay"] in cb.fields()
    assert lab("supect_following_conditions", C.Q29_KNOW_NONE).startswith("I know")
    assert lab("supect_following_conditions", C.Q29_SUSPECT_NONE).startswith("I don't suspect")


def test_section2_codes():
    assert lab("period_12months", C.PERIOD_YES) == "Yes"
    assert "menopause" in lab("period_12months", C.PERIOD_MENOPAUSE)
    assert "less than 24" in lab("avg_often_period_come", C.CYCLE_SHORT)
    assert "more than 38" in lab("avg_often_period_come", C.CYCLE_LONG)
    assert "dyspareunia" in lab("experienced_period_related_symptoms", C.SX_DYSPAREUNIA)
    assert "bowel" in lab("experienced_period_related_symptoms", C.SX_DYSCHEZIA)
    assert "urination" in lab("experienced_period_related_symptoms", C.SX_DYSURIA)
    assert "Fatigue" in lab("experienced_period_related_symptoms", C.SX_FATIGUE)
    assert "Dizziness" in lab("experienced_period_related_symptoms", C.SX_DIZZY)
    assert "doctor or nurse" in lab("seek_care_period_related_symptoms", C.CARE_TRAINED_ONLY)
    assert "both" in lab("seek_care_period_related_symptoms", C.CARE_BOTH)
    assert "Traditional" in lab("seek_care_period_related_symptoms", C.CARE_TRAD_ONLY)
    assert "worried" in lab("seek_care_period_related_symptoms", C.CARE_NO_WORRY)


def test_text_valued_choices_exist():
    checks = {"days_bleed_per_cycle": C.BLEED_VALID, "describe_mestrual_heaviest_days": C.FLOW_HEAVY,
              "experience_pain_before_during_period": set(C.PAIN_ORDER),
              "long_first_noticed_receiving_diagnosis": set(C.DELAY_ORDER),
              "condition_make_sense": set(C.UNDERSTAND_ORDER),
              "spend_manage_menstrual_condition": set(C.PRODUCT_BANDS),
              "spend_pain_doctor_visit": set(C.CARE_BANDS),
              "days_missed_each_month": set(C.DAYS_ORDER), "burden_condition_places": set(C.BURDEN_ORDER),
              "health_insurance_cover_diag_treat": C.COVER_YES | {C.COVER_DK},
              "borrow_sell_pay_health": C.BORROW_YES | {C.BORROW_CANNOT_AFFORD},
              "feel_supported_people_around_you": set(C.SUPPORT_ORDER),
              "have_someone_talk_to": C.CONFIDANT_YES | {C.CONFIDANT_NO}}
    for field, vals in checks.items():
        assert vals <= set(cb.value_labels(field)), field


def test_insurance_and_afford_codes():
    for v in C.INS_SHA:
        assert "SHA" in lab("Have_any_Health_insurance", v)
    for v in C.INS_PRIVATE_ONLY:
        assert "private" in lab("Have_any_Health_insurance", v) and "SHA" not in lab("Have_any_Health_insurance", v)
    assert "do not have" in lab("Have_any_Health_insurance", C.INS_NONE)
    assert "friends or family" in lab("do_when_cannot_afford_treatment", C.AFFORD_HELP)
    assert "hasn't" in lab("do_when_cannot_afford_treatment", C.AFFORD_NOT_HAPPENED)
    assert {lab("do_when_cannot_afford_treatment", v) for v in C.AFFORD_WITHOUT} == \
        {"Delay or skip treatment", "Go without care"}


def test_method_codes():
    assert "Laparoscopy" in lab("how_diagnosed_endometriosis", "6")
    assert "ultrasound" in lab("how_diagnosed_endometriosis", "2").lower()
    assert "Laparoscopy" in lab("how_diagnosed_adenomyosis", "3")
    assert "Ultrasound" in lab("how_diagnosed_uterine_fibroids", "2")


def test_protocol_numbering_complete():
    qs = sorted(f["q"] for f in cb.fields().values() if f.get("q"))
    assert qs == list(range(1, 94))
