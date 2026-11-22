"""SYNTHETIC demonstration data.

Generates fake submissions that follow the form's skip logic so the dashboard can
be tried out and tested before (or without) real data. Every number produced from
this data is made up; the app shows a banner whenever it is in use.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import codebook, config, relevance
from .ingest import normalise


def _pick(rng, values, p=None):
    if p is not None:
        p = np.asarray(p, float)
        p = p / p.sum()
    return values[rng.choice(len(values), p=p)]


def _multi(rng, values, p, exclusive=()):
    chosen = [v for v, q in zip(values, p) if rng.random() < q and v not in exclusive]
    if not chosen and exclusive:
        return exclusive[0]
    return " ".join(chosen) if chosen else values[0]


def generate(n: int = 320, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cb = codebook.fields()
    vals = {k: [c["value"] for c in f["choices"]] for k, f in cb.items()}
    rows = []
    start = pd.Timestamp("2026-09-01", tz="UTC")
    for i in range(n):
        r: dict = {}
        r["consent"] = "Yes" if rng.random() > 0.02 else "No"
        r["how_old_are_you"] = int(np.clip(rng.normal(31, 8), 16, 60))
        r["residence"] = _pick(rng, vals["residence"], [45, 10, 8, 7, 5, 25])
        if r["residence"] == "Other":
            r["current_residence_other"] = _pick(rng, ["Kiambu, urban", "Machakos, rural",
                                                     "Kakamega rural", "Nyeri town"])
        r["highest_level_education"] = _pick(rng, vals["highest_level_education"],
                                             [1, 4, 18, 25, 35, 14, 3])
        r["main_source_income"] = _pick(rng, vals["main_source_income"], [12, 14, 22, 12, 22, 10, 6, 2])
        r["marital_status"] = _pick(rng, vals["marital_status"], [45, 42, 8, 2, 3])
        r["children_have"] = _pick(rng, vals["children_have"], [18, 17, 10, 6, 49])
        r["like_have_children"] = _pick(rng, vals["like_have_children"], [4, 66, 2, 8, 20])
        r["ever_tried_get_pregnant"] = _pick(rng, vals["ever_tried_get_pregnant"], [18, 30, 48, 4])
        r["avg_monthly_household_income"] = _pick(rng, vals["avg_monthly_household_income"],
                                                  [38, 24, 14, 9, 5, 10])
        r["describe_body_size"] = _pick(rng, vals["describe_body_size"], [8, 52, 28, 8, 4])
        r["facility_usually_visited"] = _pick(rng, vals["facility_usually_visited"],
                                              [35, 40, 10, 6, 1, 5, 1, 2])
        r["had_menses"] = "Yes" if rng.random() > 0.01 else "No"
        r["age_at_menarche"] = int(np.clip(rng.normal(13, 1.4), 9, 18))
        r["period_12months"] = _pick(rng, vals["period_12months"], [84, 6, 1, 3, 2, 1, 2, 1])
        if r["period_12months"] == "7":
            r["age_entered_menopause"] = int(rng.integers(45, 55))
        # latent severity drives condition status and symptoms together
        sev = rng.random()
        conds = [c["q29"] for c in config.CONDITIONS.values()]
        cond_p = np.array([0.30, 0.10, 0.32, 0.18, 0.08]) * (0.4 + 1.6 * sev)
        chosen = [c for c, p in zip(conds, cond_p) if rng.random() < p]
        r["supect_following_conditions"] = " ".join(chosen) if chosen else (
            config.Q29_SUSPECT_NONE if rng.random() < 0.6 else config.Q29_KNOW_NONE)
        dx = {c: (c in chosen and rng.random() < 0.35 + 0.4 * sev) for c in conds}
        r["currently_using_HMC"] = _pick(rng, vals["currently_using_HMC"], [28, 66, 4, 2])
        r["HMC_currently_using"] = _pick(rng, vals["HMC_currently_using"], [20, 6, 30, 22, 10, 2, 2, 5, 3])
        r["long_using_HMC"] = _pick(rng, vals["long_using_HMC"], [15, 18, 25, 22, 10, 6, 4])
        r["main_reason_using_HMC"] = _pick(rng, vals["main_reason_using_HMC"],
                                           [10, 12, 8, 14, 40, 2, 3, 1, 3, 4, 3])
        r["avg_often_period_come"] = _pick(rng, vals["avg_often_period_come"],
                                           [8 + 10 * sev, 62, 10 + 8 * sev, 1, 3, 2, 6])
        r["days_bleed_per_cycle"] = _pick(rng, vals["days_bleed_per_cycle"],
                                          [5, 48, 30, 8 + 14 * sev, 2, 3])
        r["describe_mestrual_heaviest_days"] = _pick(rng, vals["describe_mestrual_heaviest_days"],
                                                     [14, 40, 22 + 12 * sev, 8 + 20 * sev, 2])
        r["have_anaemia_low_iron"] = _pick(rng, vals["have_anaemia_low_iron"], [10 + 20 * sev, 60, 12, 3])
        r["experience_pain_before_during_period"] = _pick(
            rng, vals["experience_pain_before_during_period"], [6, 20, 38, 22 + 20 * sev, 4 + 14 * sev])
        r["where_feel_pain_or_discomfort"] = _multi(rng, vals["where_feel_pain_or_discomfort"],
                                                    [0.85, 0.6, 0.35, 0.3, 0.3, 0.2, 0.03])
        sxp = [0.5, 0.45 + 0.2 * sev, 0.2 + 0.2 * sev, 0.3, 0.25, 0.5, 0.25,
               0.1 + 0.3 * sev, 0.1 + 0.25 * sev, 0.08 + 0.15 * sev, 0.15, 0]
        r["experienced_period_related_symptoms"] = _multi(rng, vals["experienced_period_related_symptoms"],
                                                          sxp, exclusive=())
        seek = _pick(rng, vals["seek_care_period_related_symptoms"], [30 + 25 * sev, 4, 5, 30, 18 - 10 * sev])
        r["seek_care_period_related_symptoms"] = seek
        r["obtain_period_related_symptoms"] = _pick(rng, vals["obtain_period_related_symptoms"],
                                                    [15, 28, 30, 18, 9])
        r["reasons_not_spoken_HCP"] = _multi(rng, vals["reasons_not_spoken_HCP"], [0.5, 0.35, 0.2, 0.18, 0.05])
        fam = [0.6, 0.12, 0.85, 0.35, 0.1, 0.02, 0]
        r["familiar_with_these_conditions"] = _multi(rng, vals["familiar_with_these_conditions"], fam,
                                                     exclusive=("7",))
        r["condition_make_sense"] = _pick(rng, vals["condition_make_sense"], [12, 35, 35, 18])
        r["first_degree_female_relative_have_conditions"] = _multi(
            rng, vals["first_degree_female_relative_have_conditions"], [0.25, 0.15, 0.02, 0.5, 0.15])
        r["which_conditions_applied_to_them"] = _multi(rng, vals["which_conditions_applied_to_them"],
                                                       [0.2, 0.05, 0.6, 0.15, 0.03, 0.05])
        for key, c in config.CONDITIONS.items():
            r[c["gate"]] = "Yes" if dx[c["q29"]] else "No"
            r[c["method"]] = _multi(rng, vals[c["method"]], [0.6, 0.15, 0.25, 0.2, 0.1, 0.05][: len(vals[c["method"]])])
            r[c["age"]] = int(np.clip(r["how_old_are_you"] - rng.integers(0, 10), 14, r["how_old_are_you"]))
            r[c["pathway"]] = _multi(rng, vals[c["pathway"]], [0.7, 0.3, 0.35, 0.12, 0.15, 0.2, 0.03])
            delay_p = [22, 25, 25, 12, 6, 6, 4] if key in ("endo", "adeno") else [40, 28, 16, 6, 3, 3, 4]
            r[c["delay"]] = _pick(rng, vals[c["delay"]], delay_p)
            r[c["challenge"]] = _multi(rng, vals[c["challenge"]], [0.55, 0.3, 0.35, 0.25, 0.15, 0.1, 0.12, 0.1, 0.03])
            r[c["treatment"]] = _multi(rng, vals[c["treatment"]], [0.45, 0.2, 0.6, 0.08, 0.12, 0.03, 0.25, 0.25, 0.03, 0.08])
        r["often_menstrual_affect_mood"] = _pick(rng, vals["often_menstrual_affect_mood"], [12, 35, 30, 23])
        r["symptoms_affected_relationships"] = _pick(rng, vals["symptoms_affected_relationships"], [20, 35, 25, 20])
        r["feel_supported_people_around_you"] = _pick(rng, vals["feel_supported_people_around_you"], [30, 40, 18, 12])
        r["ever_experiencedStigma_disbelief"] = _pick(rng, vals["ever_experiencedStigma_disbelief"],
                                                      [12 + 15 * sev, 30, 45, 8])
        r["have_someone_talk_to"] = _pick(rng, vals["have_someone_talk_to"], [25, 40, 4, 8, 18, 5])
        r["spend_manage_menstrual_condition"] = _pick(rng, vals["spend_manage_menstrual_condition"],
                                                      [25, 35, 20, 12 + 8 * sev, 8])
        r["spend_pain_doctor_visit"] = _pick(rng, vals["spend_pain_doctor_visit"],
                                             [20, 22, 14, 12, 7, 8 + 6 * sev, 3, 2, 8])
        r["borrow_sell_pay_health"] = _pick(rng, vals["borrow_sell_pay_health"], [20, 6, 60, 14])
        r["postpone_important_expenses"] = _pick(rng, vals["postpone_important_expenses"], [30 + 15 * sev, 60])
        r["burden_condition_places"] = _pick(rng, vals["burden_condition_places"], [18, 32, 30, 20])
        r["days_missed_each_month"] = _pick(rng, vals["days_missed_each_month"], [30, 40, 18 + 10 * sev, 8 + 10 * sev])
        r["days_hh_duties_missed"] = _pick(rng, vals["days_hh_duties_missed"], [30, 42, 18, 10])
        r["do_when_cannot_afford_treatment"] = "8" if rng.random() < 0.4 else _multi(
            rng, vals["do_when_cannot_afford_treatment"], [0.4, 0.3, 0.08, 0.02, 0.3, 0.18, 0, 0.02])
        r["Have_any_Health_insurance"] = _pick(rng, vals["Have_any_Health_insurance"], [35, 6, 6, 8, 12, 33])
        r["health_insurance_cover_diag_treat"] = _pick(rng, vals["health_insurance_cover_diag_treat"], [15, 30, 10, 45])
        r["payout_of_pocket"] = _pick(rng, vals["payout_of_pocket"], [25, 30, 25, 20])
        r["ever_denied_claim"] = _pick(rng, vals["ever_denied_claim"], [12, 48, 40])
        r["manage_period_related_symptoms"] = _multi(rng, vals["manage_period_related_symptoms"],
                                                     [0.8, 0.2, 0.55, 0.15, 0.2, 0.2, 0.15, 0.25, 0.05, 0.03])
        r["ever_seek_emergency_medical_care"] = _pick(rng, vals["ever_seek_emergency_medical_care"],
                                                      [10, 6 + 6 * sev, 3, 2, 70])
        r["sth_someone_remind_seek_care"] = _pick(rng, vals["sth_someone_remind_seek_care"], [10, 25, 15, 15, 33, 2])
        r["how_important_seeking_care"] = _pick(rng, vals["how_important_seeking_care"], [4, 5, 12, 30, 49])
        r["urgent_need_manage_condition"] = _pick(rng, vals["urgent_need_manage_condition"],
                                                  [32, 6, 12, 14, 16, 6, 6, 5, 3])
        r["use_health_app_device"] = _multi(rng, vals["use_health_app_device"],
                                            [0.35, 0.2, 0.45, 0.12, 0.06, 0.01, 0.02])
        r["data_privacy_mean"] = _multi(rng, vals["data_privacy_mean"], [0.7, 0.45, 0.55, 0.4, 0.45, 0.06])
        r["share_health_info_privacy_protected"] = _pick(rng, vals["share_health_info_privacy_protected"],
                                                         [55, 10, 33, 2])
        r["hear_about_this_survey"] = _pick(rng, vals["hear_about_this_survey"], [30, 15, 8, 3, 25, 12, 5, 2])
        # sprinkle realistic item non-response
        for k in ("avg_monthly_household_income", "spend_pain_doctor_visit", "age_at_menarche",
                  "health_insurance_cover_diag_treat"):
            if rng.random() < 0.06:
                r[k] = None
        r["_uuid"] = f"demo-{i:05d}"
        r["_id"] = i + 1
        r["_submission_time"] = (start + pd.Timedelta(minutes=int(rng.integers(0, 60 * 24 * 80)))).isoformat()
        rows.append(r)

    df = pd.DataFrame(rows)
    # enforce the form's skip logic in field order, as Enketo would
    for name in cb:
        if name not in df:
            df[name] = None
        shown = relevance.applicable(df, name)
        df.loc[~shown, name] = None
    # emulate API keys with group prefixes, then normalise like real data
    prefixed = {name: (f"{f['group']}/{name}" if f.get("group") else name) for name, f in cb.items()}
    return normalise(df.rename(columns=prefixed))
