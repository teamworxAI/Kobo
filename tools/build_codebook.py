"""Rebuild wema/codebook.json from the live KoboToolbox (Enketo) form.

Usage:
    python tools/build_codebook.py [ENKETO_ID] [OUTPUT]

The Enketo "transform" endpoint is public (the same definition any respondent's
browser downloads), so no API token is needed. Re-run this whenever the form is
redeployed so value codes and labels stay in sync with the dashboard.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from lxml import etree

ENKETO_ID = "XkauKNnq"
TRANSFORM_URL = "https://ee.kobotoolbox.org/transform/xform/{id}"

# Protocol question numbers (the numbering used in the analysis plan), mapped to
# Kobo field names. The form's own on-screen numbers also count "other, specify"
# boxes, so they drift from the protocol numbering; this table is the bridge.
PROTOCOL_Q = {
    # Numbering follows the 11 Oct 2026 questionnaire revision used by the analysis plan.
    # Items added to the live form after that revision (ever_tried_get_pregnant,
    # had_menses, have_anaemia_low_iron, hear_about_this_survey) have no number.
    1: "how_old_are_you", 2: "residence", 3: "highest_level_education",
    4: "main_source_income", 5: "marital_status", 6: "children_have",
    7: "like_have_children", 8: "avg_monthly_household_income", 9: "describe_body_size",
    10: "facility_usually_visited", 11: "age_at_menarche", 12: "period_12months",
    13: "age_entered_menopause", 14: "currently_using_HMC",
    15: "HMC_currently_using", 16: "long_using_HMC", 17: "main_reason_using_HMC",
    18: "avg_often_period_come", 19: "days_bleed_per_cycle",
    20: "describe_mestrual_heaviest_days", 21: "experience_pain_before_during_period",
    22: "where_feel_pain_or_discomfort", 23: "experienced_period_related_symptoms",
    24: "seek_care_period_related_symptoms", 25: "obtain_period_related_symptoms",
    26: "reasons_not_spoken_HCP", 27: "familiar_with_these_conditions",
    28: "condition_make_sense", 29: "supect_following_conditions",
    30: "first_degree_female_relative_have_conditions",
    31: "which_conditions_applied_to_them",
    # Section 4 - one block of seven items per condition
    32: "diagnose_HCP_adenomyosis", 33: "how_diagnosed_adenomyosis",
    34: "age_diagnosed_adenomyosis", 35: "describe_diagnosis_came_about",
    36: "long_first_noticed_receiving_diagnosis",
    37: "biggest_challenge_faced_get_diagnosis", 38: "received_treatment_any_condition",
    39: "diagnose_HCP_endometriosis", 40: "how_diagnosed_endometriosis",
    41: "age_diagnosed_endometriosis", 42: "describe_endometriosis_came_about",
    43: "long_first_noticed_endometriosis", 44: "biggest_challenge_faced_get_endometriosis",
    45: "received_treatment_endometriosis",
    46: "diagnosed_HCP_uterine_fibroids", 47: "how_diagnosed_uterine_fibroids",
    48: "age_diagnosed_uterine_fibroids", 49: "describe_uterine_fibroids_came_about",
    50: "long_first_noticed_uterine_fibroids",
    51: "biggest_challenge_faced_get_uterine_fibroids", 52: "received_treatment_uterine_fibroids",
    53: "diagnosed_HCP_pmos", 54: "how_diagnosed_pmos", 55: "age_diagnosed_pmos",
    56: "describe_pmos_came_about", 57: "long_first_noticed_pmos",
    58: "biggest_challenge_faced_get_pmos", 59: "received_treatment_pmos",
    60: "diagnosed_HCP_pmdd", 61: "how_diagnosed_pmdd", 62: "age_diagnosed_pmdd",
    63: "describe_pmdd_came_about", 64: "long_first_noticed_pmdd",
    65: "biggest_challenge_faced_get_pmdd", 66: "received_treatment_pmdd",
    67: "often_menstrual_affect_mood", 68: "symptoms_affected_relationships",
    69: "feel_supported_people_around_you", 70: "ever_experiencedStigma_disbelief",
    71: "have_someone_talk_to", 72: "spend_manage_menstrual_condition",
    73: "spend_pain_doctor_visit", 74: "borrow_sell_pay_health",
    75: "postpone_important_expenses", 76: "burden_condition_places",
    77: "days_missed_each_month", 78: "days_hh_duties_missed",
    79: "do_when_cannot_afford_treatment", 80: "Have_any_Health_insurance",
    81: "health_insurance_cover_diag_treat", 82: "payout_of_pocket",
    83: "ever_denied_claim", 84: "manage_period_related_symptoms",
    85: "ever_seek_emergency_medical_care", 86: "sth_someone_remind_seek_care",
    87: "how_important_seeking_care", 88: "urgent_need_manage_condition",
    89: "use_health_app_device", 90: "data_privacy_mean",
    91: "share_health_info_privacy_protected", 92: "comments",
}

SKIP_NOTES = {"wema_study", "_span_style_color_re_data_submission_span",
              "data_submission_span", "survey_questionnaire", "def", "adenomyosis",
              "Thank_you_very_much_he_end_of_the_survey"}


def _clean_label(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"^\d+(\.\d+)?\s*\.?\s*", "", text)  # drop the form's own number


def build(enketo_id: str = ENKETO_ID) -> dict:
    resp = requests.post(TRANSFORM_URL.format(id=enketo_id), timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    model = etree.fromstring(payload["model"].encode())
    soup = BeautifulSoup(payload["form"], "lxml")

    # itemset instances: itextId -> stored value
    lists: dict[str, dict[str, str]] = {}
    root_tag = None
    for inst in model.iter("{*}instance"):
        iid = inst.get("id")
        if not iid:
            primary = next(iter(inst), None)
            if primary is not None:
                root_tag = etree.QName(primary).localname
            continue
        lists[iid] = {}
        for item in inst.iter():
            if etree.QName(item).localname != "item":
                continue
            vals = {etree.QName(c).localname: (c.text or "") for c in item}
            lists[iid][vals.get("itextId", "")] = vals.get("name", "")

    groups = {}
    for el in soup.find_all(["section", "fieldset"]):
        if el.get("name"):
            groups[el["name"].split("/")[-1]] = (el.get("data-relevant") or "").strip() or None

    q_by_name = {v: k for k, v in PROTOCOL_Q.items()}
    fields = {}
    seen = set()
    for el in soup.find_all(["label", "fieldset"]):
        if "question" not in (el.get("class") or []):
            continue
        inp = el.find(["input", "select", "textarea"])
        if inp is None or not inp.get("name") or inp["name"] in seen:
            continue
        path = inp["name"]
        seen.add(path)
        name = path.split("/")[-1]
        if name in SKIP_NOTES:
            continue
        parts = path.strip("/").split("/")
        group = parts[1] if len(parts) > 2 else None
        lab = el.find(class_="question-label")
        ftype = {"radio": "select_one", "checkbox": "select_multiple"}.get(
            inp.get("type"), inp.get("data-type-xml") or "string")
        choices = []
        tmpl = el.find(class_="itemset-template")
        if tmpl is not None:
            list_id = re.search(r"instance\('([^']+)'\)", tmpl.get("data-items-path", "")).group(1)
            labels = el.find(class_="itemset-labels")
            for sp in labels.find_all("span"):
                if "active" not in (sp.get("class") or []):
                    continue
                itext = sp.get("data-itext-id")
                choices.append({"value": lists[list_id][itext], "label": sp.get_text(" ", strip=True)})
        fields[name] = {
            "q": q_by_name.get(name),
            "label": _clean_label(lab.get_text(" ", strip=True)) if lab else name,
            "type": ftype,
            "group": group,
            "relevant": (inp.get("data-relevant") or "").strip() or None,
            "required": bool(inp.get("data-required")),
            "choices": choices,
        }
    return {"form_uid": root_tag, "enketo_id": enketo_id, "groups": groups, "fields": fields}


if __name__ == "__main__":
    enketo = sys.argv[1] if len(sys.argv) > 1 else ENKETO_ID
    out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parents[1] / "wema" / "codebook.json")
    cb = build(enketo)
    missing = [n for n in PROTOCOL_Q.values() if n not in cb["fields"]]
    if missing:
        print("WARNING: protocol items not found in form:", missing, file=sys.stderr)
    out.write_text(json.dumps(cb, indent=1, ensure_ascii=False))
    print(f"Wrote {out} - {len(cb['fields'])} fields, form uid {cb['form_uid']}")
