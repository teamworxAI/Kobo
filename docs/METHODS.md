#### Analysis populations

| Population | Definition |
|---|---|
| **Eligible (B1)** | Consented, aged 18 or over, has ever menstruated. Women in menopause are counted in the sample flow but the form routes them past Sections 3–7, so they cannot enter condition-based analyses. |
| **Know or suspect a condition** | Q29 names any of the five conditions, or any Section 4 gate = Yes. |
| **Diagnosed** (per condition) | Section 4 gate (Q32 / 39 / 46 / 53 / 60) = Yes. *Diagnosed* overall = any gate Yes. |
| **Suspected only** | Q29 names a condition and no gate = Yes. |
| **No condition** | Q29 = "I know I don't have…" or "I don't suspect…", no gate = Yes. Kept as a comparison group unless switched off (B1 toggle). |
| **No period in the past 12 months** | Q12 ≠ Yes. Cycle and symptom items (Q18–23) for these women are shown separately and not pooled. |

Groups are mutually exclusive in the order Diagnosed → Suspected only → No condition.

#### Estimates
Proportions with **Wilson 95% confidence intervals**. The half-width is about ±7 points at n = 200, ±10 at n = 100
and ±15 at n = 40. **Groups under 40 are descriptive only**: hollow dots in charts, † in tables.
Each indicator has its own denominator (see the definitions table): "don't know", "not sure", "prefer not to say"
and "not applicable" are excluded rather than counted as "no".

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

#### Money
Spending is reported as **band distributions**. Band midpoints are used only as a sensitivity analysis. The open top
band is set to 1.5 × its lower bound.

#### Missing data
Item non-response is reported by section. It is measured among women who were actually shown each item, because the
form's skip logic is re-applied to every response. Analysis is complete-case. Items with more than 10% missing are
flagged on the Data quality page.

#### Limitations
* **Convenience sample** recruited mainly through advocacy and support groups. It probably over-represents women who
  are already diagnosed, urban, educated and engaged with these conditions.
* **Self-reported diagnosis** and **recall bias**, especially for diagnostic delay and spending over 12 months.
* Cross-sectional: associations are not causal.
* **Findings describe this group of women, not all Kenyan women.**
