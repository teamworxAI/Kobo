# Issues found in the live form (version 12, 22 Nov 2026)

I found these by reading the deployed form definition (skip logic and choice codes) and checking
it against the survey design: the 11 Oct 2026 revision, its survey-flow diagram and the draft
analysis plan. Question numbers follow the 11 Oct revision.
The dashboard **works around every one of them in the analysis**. Where the problem is in
data collection, though, only a form change fixes it. The most important ones come first.

**Fixes from the 11 Oct review, as they stand in the live form**

* **A1** (no-condition respondents continue to family history and Section 5): **partly in place.** Section 5
  (Q67–79) is shown to everyone, so the "as printed" skip to Q75 is gone. But women who answer "I know I don't
  have any" (code 6) still skip family history Q30–31 (see #8).
* **A3** (Q25 ease only for women who sought care): **not in place** (see #4).
* **A4** (Q86 "no prompt" answer): **in place.** "No, nothing or no one prompted me" exists. Q86 is still single
  choice and still placed after Q85.

| # | Item | Problem | Effect on analysis | Fix in the form (XLSForm) |
|---|------|---------|--------------------|---------------------------|
| 1 | **M-Pesa phone number** (end of form) | The phone number for the airtime refund is saved in the *same record* as the health answers, but the survey is described as anonymous. | Re-identification risk. The dashboard drops this field when it loads the data and never shows or exports it. | Collect refund numbers in a separate Kobo form, linked only by a random code (or not linked at all). |
| 2 | **Section 4 gates (Q32/39/46/53/60)** | The section's skip rule is `supect_following_conditions != '6'`. Q29 is select-multiple, so this only hides Section 4 from women who ticked *only* "I know I don't have any". Women who "don't suspect" (code 7) and women who ticked one condition still get all five diagnosis blocks. The design flow sends only "any condition" respondents into Section 4. | Diagnosis is still taken from the gates, as planned. Diagnoses not ticked at Q29 are flagged on the Data quality page. Respondent burden is higher than needed. | Give each condition block its own rule: `selected(${supect_following_conditions}, '1')` for endometriosis, and so on. |
| 3 | **Q29** | A woman can tick a condition *and* "I know I don't have any" / "I don't suspect…". | The group is set by the condition. Contradictions are counted on the Data quality page. | Add a constraint: `not((selected(., '6') or selected(., '7')) and count-selected(.) > 1)`. |
| 4 | **Q25 ease of obtaining care** (A3) | The rule is `seek_care != '5'`, so women who answered "No, I have not discussed my symptoms with a provider" (code 4) are asked how easy it was to get care. | Q25 is analysed only for women who sought care (Q24 = 1, 2 or 3). | Rule: `selected(${seek_care_period_related_symptoms}, '1') or … '2' or … '3'`. |
| 5 | **Q81–83 insurance details** | These have no skip rule, so uninsured women are asked about coverage, upfront payment and denied claims. | Analysed among insured women only. | Rule: `${Have_any_Health_insurance} != '4'`. |
| 6 | **Women in menopause** (Q12 = code 7) | **The form contradicts the design.** In the 11 Oct flow they answer Q13, then the whole survey, recalling Q18–23 at age 20–30. The live form skips Sections 3–7 for them: awareness, diagnosis, stigma, costs, insurance and needs. | They stay in the population, as designed (sidebar toggle), and in the separate "no period in 12 months" block. Their condition status is "Unclassified", so they count in "All" but not in group comparisons. | Drop `period_12months != '7'` from the Section 3–7 group rules. Add a recall note ("think of when you were 20–30") to Q18–23 when Q12 = menopause. |
| 7 | **Urban / rural** | No urban/rural item. Q2 lists 5 cities plus "Other – county and urban/rural, please specify" as free text. | The urban/rural comparison is replaced by **Nairobi vs other counties**. Free text containing "rural" or "urban" is flagged but not used. | Add `select_one urban_rural` after Q2, and a county list (all 47) instead of free text. |
| 8 | **Q30–31 family history** (A1) | Shown on the rule `Q29 != '6'`. The A1 correction sends *all* no-condition respondents to Q30. | Family history is not used in the current tables. | Show to everyone. |
| 9 | **Q72 product spend** | Bands start at "KES 1–200". There is no "nothing / KES 0" option. | Zero spend is forced into the lowest band or left blank. | Add "KES 0 (nothing)". |
| 10 | **Q73 care spend** | Bands overlap ("KES 10,001–15,000" and "KES 15,000–50,000"). | Minor. The bands are kept as asked. | "KES 15,001–50,000". |
| 11 | **Q36/43/50/57/64 delay**, Q16 duration | "1–2 years" is followed by "3–5 years", so 2–3 years has no band. | The ≥3-year cut-off is unaffected, but a 2.5-year delay has no correct answer. | "Less than 1 year / 1 to <3 years / 3 to <6 years…". |
| 12 | **Q74** "borrow_sell_pay_health" | The planned hardship definition includes *sold belongings*, but Q74 has no "sold" option. | Hardship = borrowed / received help, could not afford, or gave up essentials. Selling belongings can't be measured. | Add "Yes, I sold belongings or assets". |
| 13 | **Q79** | "No, this hasn't happened" can be ticked together with other options. | Treated as "not happened" only when ticked on its own. | Make it exclusive (constraint as in #3). |
| 14 | **Q12** wording | The label says "(multiple check boxes)" but it is single choice. | None. | Fix the label. Or make it select-multiple if women can be, for example, both breastfeeding and on contraception. |
| 15 | **Q18 "Other, specify"** | The free-text box only appears if the woman uses hormonal contraception. | None. | Remove `currently_using_HMC` from that rule. |
| 16 | **Under-18s** | After consent, under-18s see an empty form instead of an exit message. | Excluded by the eligibility rule. | Add an end-of-survey note shown when age < 18. |
| 17 | **Completion-time metadata** | The form has no `start` or `end` metadata. The plan says Kobo's start/end timestamps will replace the design time estimates (16–36 min by path). | Completion time can't be measured. The Data quality page shows a warning, and fills in path-by-path times once the fields exist. | Add `start` and `end` rows (type `start`, `end`) to the XLSForm survey sheet. |
| 18 | **Stated duration** | The consent and recruitment message say 30–45 minutes. The design estimate is about 16–30 minutes for most paths. | None. | Restate after the timed pilot (needs #17). Overstating burden may reduce uptake. |
| 19 | **Question numbering** | Items added after the 11 Oct revision have no protocol number: had menses, tried to get pregnant, anaemia, how you heard about the survey. The form's on-screen numbers also count "specify" boxes. | The codebook uses the 11 Oct numbering, so Q-numbers match the analysis plan. | Renumber the on-screen labels to the protocol numbering before the next deployment. |
