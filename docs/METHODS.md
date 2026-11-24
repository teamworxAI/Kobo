#### Analysis populations

| Population | Definition |
|---|---|
| **Eligible (B1)** | Consented, aged 18 or over, has ever menstruated. These are the exits in the survey design. Women in menopause are included, as designed, with cycle items recalled from age 20–30. The live form still routes them past Sections 3–7, so for now they have no condition status ("Unclassified"). A sidebar switch excludes them while B1 is open. |
| **Know or suspect a condition** | Q29 names any of the five conditions, or any Section 4 gate = Yes. |
| **Diagnosed** (per condition) | Section 4 gate (Q32 / 39 / 46 / 53 / 60) = Yes. *Diagnosed* overall = any gate Yes. |
| **Suspected only** | Q29 names a condition and no gate = Yes. |
| **No condition** | Q29 = "I know I don't have…" or "I don't suspect…", no gate = Yes. Kept as a comparison group unless switched off (B1 toggle). |
| **No period in the past 12 months** | Q12 ≠ Yes. Cycle and symptom items (Q18–23) for these women are shown separately and not pooled. |

Groups are mutually exclusive in the order Diagnosed → Suspected only → No condition. Respondents with no Q29
answer are "Unclassified": they count in "All" estimates but not in group comparisons. When the no-condition group
is switched off, the population becomes "know or suspect a condition" only.

**Strata used throughout:** diagnosed vs suspected only; menstruating vs not in the past 12 months; recruited through
a support or advocacy group vs other routes.

#### Estimates
Proportions with **Wilson 95% confidence intervals**. The half-width is about ±7 points at n = 200, ±10 at n = 100
and ±15 at n = 40. **Groups under 40 are descriptive only**: hollow dots in charts, † in tables.
Each indicator has its own denominator (see the definitions table): "don't know", "not sure", "prefer not to say"
and "not applicable" are excluded rather than counted as "no".

#### Sample size and what can be shown
A planning simulation (see `docs/SAMPLE_SIZE.md` and the dashboard page *What this sample can show*) estimates,
for 200, 400 and 800 women, how large a difference each planned comparison can detect. It also covers how
often each condition reaches 40 diagnosed women, how clustering by recruitment channel widens margins of error,
and how many covariates each model can carry. The same page applies these checks to the data as it comes in.

#### Tests and effect sizes
* Categorical outcomes: Pearson chi-square; Fisher's exact test for 2×2 tables with an expected count below 5;
  for larger sparse tables a Monte Carlo exact chi-square (10,000 permutations).
* Ordered bands (spending, days lost, pain): Mann–Whitney U, with the rank-biserial correlation as effect size.
* Differences in proportions: Newcombe hybrid-score 95% CI.
* Results are reported as effect sizes with CIs. p-values are shown for completeness, not to screen for "significant" findings.

#### Models
Firth (bias-reduced) logistic regression for three outcomes only: care sought, financial hardship and diagnostic
delay of 3 years or more. Covariates are fixed in advance (age, insurance, income, education). They enter in that
order up to about one parameter per 10 events (or non-events, whichever is fewer). Odds ratios use profile
penalised-likelihood 95% CIs.

#### Sensitivity analysis: recruitment route
Most women are reached through support and advocacy groups. A sidebar switch re-runs every page without them. The
comparison "support-group recruits vs other routes" shows how far the two differ on diagnosis, care-seeking, burden
and hardship.

#### Behavioural items (Q24–26, Q86–87)
These are described as a **baseline only**: care-seeking (Q24), ease (Q25, for women who sought care), reasons for
not seeking care (Q26), prompt (Q86) and importance (Q87). The care-seeking denominator leaves out women with "no
symptoms that worried me", which is the closest Wave 1 proxy for an episode group. Care-seeking by prompt and by
importance is shown as an association, not as evidence that one causes the other.

The formal Fogg (B = MAP) test is planned for a follow-on survey and is not attempted here: the episode gate,
six-factor ability, treatment cascade and institutional items are not in Wave 1.

#### Money
Spending is reported as **band distributions**. Band midpoints are used only as a sensitivity analysis. The open top
band is set to 1.5 × its lower bound.

#### Missing data
Completion time by survey path will be compared with the design estimates once the form records Kobo's `start` and
`end` metadata. It does not record them yet.

Item non-response is reported by section. It is measured among women who were actually shown each item, because the
form's skip logic is re-applied to every response. Analysis is complete-case. Items with more than 10% missing are
flagged on the Data quality page.

#### Limitations
* **Convenience sample** recruited mainly through advocacy and support groups. It probably over-represents women who
  are already diagnosed, urban, educated and engaged with these conditions.
* **Self-reported diagnosis** and **recall bias**, especially for diagnostic delay and spending over 12 months.
* Cross-sectional: associations are not causal.
* **Findings describe this group of women, not all Kenyan women.**
