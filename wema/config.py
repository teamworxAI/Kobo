"""Study constants: Kobo connection defaults, value codes and analysis settings.

Value codes are the *stored* values in Kobo (what the API and "XML values"
exports return), taken from wema/codebook.json. tests/test_codes.py checks that
every code below still points at the label we expect, so a redeployed form that
reorders choices fails loudly instead of silently mis-classifying women.
"""
from __future__ import annotations

import os

# --- Kobo connection -------------------------------------------------------
# ee.kobotoolbox.org is the Enketo front end of the global server.
KOBO_SERVER = os.environ.get("KOBO_SERVER", "https://kf.kobotoolbox.org")
KOBO_ASSET_UID = os.environ.get("KOBO_ASSET_UID", "aLWbr2Y7epAUXji3GkuABi")
ENKETO_ID = "XkauKNnq"

# Fields that identify a person. Dropped at ingest, never stored or shown.
PII_FIELDS = {"mpesa_phone_number"}
# Free text that can contain identifying details; kept out of the dashboard.
FREE_TEXT_HIDDEN = {"comments"}

# --- Conditions (order used everywhere) -----------------------------------
CONDITIONS = {
    # key: (label, Q29 code, Section-4 gate field, delay field, method field,
    #       age field, pathway field, challenge field, treatment field)
    "endo": dict(label="Endometriosis", q29="1", gate="diagnose_HCP_endometriosis",
                 delay="long_first_noticed_endometriosis", method="how_diagnosed_endometriosis",
                 age="age_diagnosed_endometriosis", pathway="describe_endometriosis_came_about",
                 challenge="biggest_challenge_faced_get_endometriosis",
                 treatment="received_treatment_endometriosis"),
    "adeno": dict(label="Adenomyosis", q29="2", gate="diagnose_HCP_adenomyosis",
                  delay="long_first_noticed_receiving_diagnosis", method="how_diagnosed_adenomyosis",
                  age="age_diagnosed_adenomyosis", pathway="describe_diagnosis_came_about",
                  challenge="biggest_challenge_faced_get_diagnosis",
                  treatment="received_treatment_any_condition"),
    "fibroids": dict(label="Uterine fibroids", q29="3", gate="diagnosed_HCP_uterine_fibroids",
                     delay="long_first_noticed_uterine_fibroids", method="how_diagnosed_uterine_fibroids",
                     age="age_diagnosed_uterine_fibroids", pathway="describe_uterine_fibroids_came_about",
                     challenge="biggest_challenge_faced_get_uterine_fibroids",
                     treatment="received_treatment_uterine_fibroids"),
    "pmos": dict(label="PMOS / PCOS", q29="4", gate="diagnosed_HCP_pmos",
                 delay="long_first_noticed_pmos", method="how_diagnosed_pmos",
                 age="age_diagnosed_pmos", pathway="describe_pmos_came_about",
                 challenge="biggest_challenge_faced_get_pmos", treatment="received_treatment_pmos"),
    "pmdd": dict(label="PMDD", q29="5", gate="diagnosed_HCP_pmdd",
                 delay="long_first_noticed_pmdd", method="how_diagnosed_pmdd",
                 age="age_diagnosed_pmdd", pathway="describe_pmdd_came_about",
                 challenge="biggest_challenge_faced_get_pmdd", treatment="received_treatment_pmdd"),
}
Q29_KNOW_NONE = "6"      # "I know that I don't have any of these conditions"
Q29_SUSPECT_NONE = "7"   # "I don't suspect that I have any of these conditions"
Q27_CONDITION_CODES = ["1", "2", "3", "4", "5"]
Q27_NONE = "7"

# --- Population groups -----------------------------------------------------
GRP_DX, GRP_SUSP, GRP_NONE, GRP_UNCL = "Diagnosed", "Suspected only", "No condition", "Unclassified"
GROUP_ORDER = [GRP_DX, GRP_SUSP, GRP_NONE]

# --- Item codes used by derived indicators --------------------------------
PERIOD_YES = "1"
PERIOD_MENOPAUSE = "7"
CYCLE_SHORT, CYCLE_NORMAL, CYCLE_LONG = "1", "2", "3"
CYCLE_VALID = {"1", "2", "3"}   # 4-5 stopped, 6 other, 7 don't know -> not assessable
BLEED_GT7 = "More than 7 days"
BLEED_VALID = {"1-2 days", "3-5 days", "6-7 days", "More than 7 days"}
FLOW_HEAVY = {
    "Heavy flow (need to change protection every 1-2 hours or use double protection)",
    "Very heavy flow (clots, flooding, or changing protection every hour)",
}
FLOW_VALID_EXCLUDE = {"Other"}
PAIN_ORDER = [
    "No pain", "Mild pain (manageable without medication)",
    "Moderate pain (need pain relief but can continue daily activities)",
    "Severe pain (miss school, work, or daily activities)",
    "Extremely severe pain (I need to visit the emergency room or be hospitalized)",
]
PAIN_SEVERE = set(PAIN_ORDER[3:])
SX_DYSPAREUNIA, SX_DYSCHEZIA, SX_DYSURIA = "8", "9", "10"
SX_FATIGUE, SX_DIZZY = "2", "3"
SX_NONE = "12"
CARE_TRAINED_ONLY, CARE_TRAD_ONLY, CARE_BOTH, CARE_NOT_DISCUSSED, CARE_NO_WORRY = "1", "2", "3", "4", "5"
EMERGENCY_NEVER = "No, never"
DELAY_ORDER = ["Less than 12 months", "1-2 years", "3-5 years", "6-8 years", "9-11 years",
               "More than 11 years"]
DELAY_LONG = set(DELAY_ORDER[2:])
DELAY_NO_SYMPTOMS = "I was diagnosed without having symptoms"
UNDERSTAND_ORDER = ["No sense at all", "A little sense", "Fairly good sense", "A lot of sense"]
UNDERSTAND_GOOD = set(UNDERSTAND_ORDER[2:])
STIGMA_YES = {"Yes, many times", "Sometimes"}
STIGMA_NOT_SURE = "Not sure"
SUPPORT_ORDER = ["Always", "Sometimes", "Rarely", "Never"]
SUPPORT_YES = {"Always", "Sometimes"}
CONFIDANT_YES = {"Yes, a partner or spouse", "Yes, a friend or family member",
                 "Yes, a counsellor or therapist", "Yes, a healthcare provider"}
CONFIDANT_NO = "No, I don't have anyone to talk to"
MOOD_ORDER = ["Never", "Occasionally", "Often", "Every month"]
REL_ORDER = ["Not at all", "Not really", "Somewhat", "Yes, very much"]
BURDEN_ORDER = ["None", "Slight burden", "Moderate burden", "Severe burden"]
DAYS_ORDER = ["0 days", "1–2 days", "3–4 days", "5 or more days"]
DAYS_3PLUS = {"3–4 days", "5 or more days"}

# Spending bands (Q72 products, past 30 days; Q73 care, past 12 months).
# Midpoints are an assumption used ONLY as a sensitivity analysis; the open top
# band is set to 1.5x its lower bound.
PRODUCT_BANDS = ["KES 1-200", "KES 201-500", "KES 501-1,000", "More than KES 1,000"]
PRODUCT_MID = [100, 350, 750, 1500]
CARE_BANDS = ["Less than KES 1,000", "KES 1,000–3,000", "KES 3,001–5,000", "KES 5,001–10,000",
              "KES 10,001-15,000", "KES 15,000-50,000", "KES 50,001-100,000",
              "More than KES 100,000"]
CARE_MID = [500, 2000, 4000, 7500, 12500, 32500, 75000, 150000]
SPEND_NOT_SURE = "Not sure"

BORROW_YES = {"Yes, from family or friends", "Yes, from a savings group or loan"}
BORROW_CANNOT_AFFORD = "No, I could not afford to seek care"
AFFORD_HELP = "5"            # Q79 seek help from friends or family
AFFORD_WITHOUT = {"1", "6"}  # Q79 delay or skip treatment; go without care
AFFORD_NOT_HAPPENED = "8"    # Q79 "No, this hasn't happened"
AFFORD_OTHER = "7"

INS_SHA = {"1", "2", "3"}
INS_PRIVATE_ONLY = {"5", "6"}
INS_NONE = "4"
INS_TYPE = {"1": "SHA only", "2": "SHA + private", "3": "SHA + private", "5": "Private only",
            "6": "Private only", "4": "Uninsured"}
COVER_YES = {"Yes, fully covered",
             "Yes, partially covered (e.g. specific treatment, medications excluded)"}
COVER_DK = "I don't know"
UPFRONT_YES = {"Yes, frequently", "Yes, occasionally"}
UPFRONT_NA = "Not applicable"
DENIED_NA = "Not applicable (I have not sought treatment or filed a claim for these conditions)"

INCOME_ORDER = ["Less than KES 30,000", "KES 30,001-60,000", "KES 60,001-100,000",
                "More than KES 100,000"]
INCOME_MAP = {"Less than KES 30,000": INCOME_ORDER[0], "KES 30,001-60,000": INCOME_ORDER[1],
              "KES 60,001-100,000": INCOME_ORDER[2], "KES 100,001-200,000": INCOME_ORDER[3],
              "More than KES 200,000": INCOME_ORDER[3]}
EDU_MAP = {"No formal education": "Secondary or less", "Primary school": "Secondary or less",
           "Secondary school": "Secondary or less",
           "College or technical training": "College / technical",
           "University (undergraduate)": "University", "Postgraduate (Masters)": "University",
           "Postgraduate (PhD)": "University"}
EDU_ORDER = ["Secondary or less", "College / technical", "University"]
AGE_BINS = [18, 25, 35, 45, 200]
AGE_LABELS = ["18–24", "25–34", "35–44", "45+"]
MAJOR_TOWNS = {"Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"}

PREFER_NOT = {"Prefer not to say"}

# --- Methods ---------------------------------------------------------------
SMALL_N = 40            # groups below this are descriptive only
MISSING_FLAG = 0.10     # flag items with >10% item non-response
ALPHA = 0.05

# Diagnostic method codes by condition (Q33/40/47/54/61): imaging and surgical routes
METHOD_IMAGING = {"adeno": {"1", "2"}, "endo": {"2", "3", "5"}, "fibroids": {"2", "3", "5"},
                  "pmos": {"2"}, "pmdd": set()}
METHOD_SURGICAL = {"adeno": {"3"}, "endo": {"6", "4"}, "fibroids": {"4"}, "pmos": set(),
                   "pmdd": set()}

# Q86 prompt and Q87 importance (behavioural baseline)
PROMPT_YES = {"Yes, a media message", "Yes, a family member or friend", "Yes, a health care professional", "Other"}
PROMPT_DK = "I don't remember."
PROMPT_NO = "No, nothing or no one prompted me."
IMPORTANCE_HIGH = {"Very important"}
# Q17 reasons that mean the hormonal method is used to manage symptoms, not only contraception:
# reduce pain, heavy/long periods, regularity, diagnosed condition, hair/acne, mood
HMC_THERAPEUTIC = {"1", "2", "3", "4", "7", "9"}
# Q10 usual facility grouped
FACILITY_GROUP = {"Public hospital or clinic": "Public", "Community health center or dispensary": "Public",
                  "Private hospital or clinic": "Private", "Faith-based (mission) hospital": "Faith-based",
                  "Pharmacy or chemist": "Pharmacy", "Traditional healer/herbalist": "Other / none",
                  "Other": "Other / none", "I do not usually seek care": "Other / none"}
FACILITY_ORDER = ["Public", "Private", "Faith-based", "Pharmacy", "Other / none"]
