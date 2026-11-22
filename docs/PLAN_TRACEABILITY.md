# Where each part of the analysis plan is implemented

This maps the draft WEMA analysis plan (11 Oct 2026 revision) to the code. The plan itself is not
reproduced here: it is not for circulation until the PIs agree it.

| Plan section | Implementation |
|---|---|
| §1 Analysis populations | `wema/derive.py`: `derive()` (groups, eligibility, period status), `analytic()` (B1 options), `sample_flow()` |
| §2 Derived indicators | `wema/derive.py` `INDICATORS` (definition and denominator for each); codes in `wema/config.py` |
| §3 Table shells T1–T10 | `wema/report.py` `SHELLS` (T1–T4, T6–T10); T5 in `wema/tables.py` `diagnosis_summary()` / `condition_items()` and `app.py` `page_t5()` |
| §4 Pre-specified comparisons | `wema/tables.py` `COMPARISONS` (plus one marked sensitivity comparison: recruitment route) |
| §5 Methods: estimates and tests | `wema/stats.py` (Wilson, Newcombe, chi-square / Fisher / Monte Carlo exact, Mann–Whitney) |
| §5 Methods: models | `wema/tables.py` `model()` and `wema/stats.py` `firth_logit()` (pre-specified covariate order, ~10 events per parameter) |
| §5 Methods: missing data | `wema/tables.py` `missingness()` (form skip logic re-applied by `wema/relevance.py`) |
| §6 Behavioural baseline | `app.py` `page_behaviour()`. The Fogg test is out of scope for Wave 1 |
| Survey-flow diagram: exits, time per path | Eligibility in `derive()`; `tables.durations()` (needs `start` and `end` in the form) |
| Fogg document §3 (existing items mapped to Fogg) | Baseline indicators `prompt_any`, `importance_high`, `hmc_therapeutic`, `treated_any`, `dx_dismissed`, `dx_no_equipment`, `dx_misdiagnosed` |

Differences between the plan or design and the live form are listed in `docs/FORM_ISSUES.md`.
