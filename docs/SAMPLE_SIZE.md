# What a sample of 200 can show: sample-size simulation

Generated from the planning simulation in `wema/power.py` (1,000 simulated studies per
setting; re-run with `python tools/run_power_sim.py` after changing the assumptions). The dashboard page
**What this sample can show** presents the same results interactively, and also applies the checks to the
data collected so far.

**These are planning results from synthetic data.** They depend on the assumptions listed at the end; replace
them with pilot or early real data and re-run.

## In brief

- **Is 200 enough?** For whole-sample estimates, yes (about ±7 points), and for comparisons between large groups. A 20-point difference is detected about 80% of the time or more only for HMB proxy vs none (3+ days lost, 85%); Insured vs uninsured (financial hardship, 79%); Nairobi vs other (care sought, 76%). It is not enough for smaller, 10–15-point differences, for comparisons that involve a group of under about 60 women, for interactions, or for comparisons within diagnosed subgroups.
- **Weakest comparisons at 200:** Lowest vs highest income band: hardship; Nairobi vs other: delay ≥3 years (diagnosed) – each has a group of about 40–60 women, so only differences of 25 points or more are reliably detected.
- **Condition-specific results:** with the planned mix, a sample of 200 gives a median of 55 diagnosed fibroid, 33 endometriosis/adenomyosis and 22 PMOS women. Only fibroids reliably reaches the 40 needed for anything beyond description. If the targets (100 / 60 / 40) are meant for *diagnosed* women, recruitment must aim at about 182 / 109 / 73 women who know or suspect each condition.
- **Clustering by recruitment channel** matters most for whole-sample percentages. With 60% recruited through six support groups and a modest ICC of 0.02, the real margin of error at n = 200 is about ±9 points, not ±7, and nominal 95% CIs cover the truth only 91% of the time (85% at ICC 0.05). Group comparisons are much less affected, because both groups come from the same channels. Recruiting more widely, rather than more deeply in the same groups, is what fixes this.
- **Interactions** (for example, whether heavy bleeding matters more for uninsured women): a 20-point interaction is detected 30% of the time at n = 200 and 82% at n = 800, against 82% for a main effect of the same size at n = 200 – roughly four times the sample, as expected.
- **Models:** at n = 200 the care-sought and hardship models can carry all four pre-specified covariates (about 92 events). The diagnostic-delay model has about 39 events, enough for 3 parameters, and detects an odds ratio of 2 only 34% of the time; treat it as exploratory below n ≈ 400.

## Total sample needed for each planned comparison

80% power, two-sided 5% test, planned condition mix (100 / 60 / 40 of 200). Calculated exactly for the group
shares the simulation produced, and checked against the simulated power.

| Comparison | Share of sample in each group | Total n for 20 pp | Smaller group for 20 pp | Simulated power at 200/400/800 (20 pp) | Total n for 15 pp | Simulated power at 200/400/800 (15 pp) |
|---|---|---|---|---|---|---|
| Diagnosed vs suspected only: care sought | 34% / 28% | 310 | 85 | 63% / 90% / 99% | 550 | 42% / 67% / 93% |
| Insured vs uninsured: financial hardship | 60% / 40% | 200 | 80 | 78% / 98% / 100% | 360 | 52% / 85% / 99% |
| HMB proxy vs none: 3+ days lost | 48% / 52% | 180 | 84 | 84% / 98% / 100% | 310 | 60% / 90% / 99% |
| Lowest vs highest income band: hardship | 40% / 20% | 360 | 72 | 53% / 84% / 99% | 650 | 34% / 60% / 88% |
| Nairobi vs other: care sought | 42% / 43% | 220 | 93 | 74% / 97% / 100% | 400 | 51% / 81% / 97% |
| Nairobi vs other: delay ≥3 years (diagnosed) | 20% / 20% | 480 | 97 | 47% / 73% / 95% | 860 | 26% / 50% / 78% |

## Group sizes the planned mix produces

Median group size across simulated studies (in brackets: how often the group reaches 40, the minimum for more
than description). Assumes 55% of women who know or suspect a condition have been diagnosed.

| Group | n = 200 | n = 400 | n = 800 |
|---|---|---|---|
| Diagnosed fibroids | 55 (99%) | 110 (100%) | 220 (100%) |
| Diagnosed endometriosis / adenomyosis | 33 (14%) | 66 (100%) | 132 (100%) |
| Diagnosed PMOS / PCOS | 22 (0%) | 44 (75%) | 88 (100%) |
| Diagnosed (any) | 81 (100%) | 161 (100%) | 323 (100%) |
| Suspected only | 66 (100%) | 132 (100%) | 263 (100%) |
| No condition | 53 (98%) | 107 (100%) | 212 (100%) |
| Highest income band | 40 (54%) | 80 (100%) | 161 (100%) |
| Nairobi, diagnosed | 40 (54%) | 80 (100%) | 162 (100%) |
| Other counties, diagnosed | 40 (57%) | 81 (100%) | 161 (100%) |

## Clustering by recruitment channel

60% of women recruited through six support groups of unequal size; the rest through social media, friends,
health workers and other routes. ICC = share of variation between channels.

| n | ICC | Design effect | Real margin of error (points) | Nominal 95% CI covers truth |
|---|---|---|---|---|
| 200 | 0.0 | 1.0 | ±7 | 95% |
| 200 | 0.02 | 1.7 | ±9 | 91% |
| 200 | 0.05 | 2.7 | ±11 | 85% |
| 400 | 0.0 | 1.0 | ±5 | 96% |
| 400 | 0.02 | 2.0 | ±7 | 92% |
| 400 | 0.05 | 3.6 | ±9 | 88% |
| 800 | 0.0 | 1.0 | ±3 | 95% |
| 800 | 0.02 | 3.1 | ±6 | 89% |
| 800 | 0.05 | 6.3 | ±8 | 80% |

Clustering barely changes the planned comparisons (both groups come from the same channels): false positives
stay near 5% up to ICC 0.05 and rise to about 9–16% at ICC 0.10, more in larger samples drawn from the same
channels.

## Recommendations

1. **Whole-sample estimates and large-group comparisons: 200 is enough** for differences of about 20 points
   (HMB vs none, insured vs uninsured, Nairobi vs other for care-seeking). For 15-point differences in these
   comparisons, plan on **about 350–400**.
2. **Diagnosed vs suspected, and income extremes, need about 300–360** for a 20-point difference, because one
   group is small (about 60 suspected-only women and 40 in the highest income band at n = 200).
3. **Condition-specific results (T5):** at 200, only fibroids reliably has 40 diagnosed women. Either
   - set targets for *diagnosed* women (recruit about 180 / 110 / 75 who know or suspect fibroids /
     endometriosis or adenomyosis / PMOS), or
   - present endometriosis/adenomyosis, PMOS and PMDD diagnosis results as descriptive only.
4. **Present as descriptive only at n = 200:** per-condition diagnosis tables other than fibroids;
   Nairobi vs other for diagnostic delay (about 40 diagnosed women per side); anything within the highest
   income band; interactions (they need about four times the sample: a 20-point interaction reaches 80% power
   only at about 800); the diagnostic-delay model (about 39 events, room for 3 parameters).
5. **Recruit wide, not deep.** Clustering is what most threatens whole-sample estimates. Cap the share from any
   single group (for example, no group above about 15% of the sample), and record the *specific* group in the
   form (the current "how did you hear" item only has four support-group types), so the real ICC can be
   estimated and design-effect-adjusted margins reported.
6. **Check spread on the pilot.** The informativeness check on the dashboard flags indicators with fewer than
   10 cases in a category and answer scales with over 80% in one band; run it on the first 30–50 real
   responses before finalising bands (B decisions on spending bands).

## Assumptions

Condition mixes (chance a woman knows or suspects each condition; women can report several):
| Mix | fibroids | endo_adeno | pmos | pmdd |
|---|---|---|---|---|
| Planned targets | 0.5 | 0.3 | 0.2 | 0.05 |
| Fibroid-heavy | 0.65 | 0.18 | 0.1 | 0.03 |
| Endometriosis-heavy | 0.3 | 0.5 | 0.15 | 0.08 |

Other assumptions: `{'p_diagnosed_given_condition': 0.55, 'p_need_care': 0.85, 'p_insured': 0.6, 'p_hmb': 0.4, 'p_nairobi': 0.5, 'income_probs': [0.4, 0.25, 0.15, 0.2], 'support_group_share': 0.6, 'n_support_groups': 6, 'other_channels': [0.45, 0.3, 0.15, 0.1], 'base': {'care_any': 0.5, 'hardship': 0.45, 'days_work3': 0.25, 'delay_long': 0.4}}`

Effects are planted as percentage-point differences from the reference group's rate. Analyses are the
dashboard's own: chi-square (Fisher's exact when counts are small), Newcombe CIs, Firth logistic regression with
covariates in the pre-specified order.
