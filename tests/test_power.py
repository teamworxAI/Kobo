import numpy as np
import pytest

from wema import demo, derive, power as P


def test_analytic_rules_of_thumb():
    # the plan's guide: ±7 at 200, ±10 at 100, ±15 at 40; ~100 per group detects ~20 points
    assert round(100 * P.half_width(200)) == 7
    assert round(100 * P.half_width(100)) == 10
    assert round(100 * P.half_width(40)) == 15
    assert 0.18 < P.mdd(100, 100) < 0.21
    assert P.n_per_group(0.20) == pytest.approx(93, abs=2)
    assert P.total_n_needed(0.5, 0.5, 0.20) == pytest.approx(2 * P.n_per_group(0.20), rel=0.02)
    assert P.design_effect(31, 0.02) == pytest.approx(1.6)
    assert P.epv_budget(55, 145) == 5


def test_simulation_calibrated_and_monotone():
    r = P.run_comparisons(200, "Planned targets", 0.0, deltas=(0.0, 0.2), reps=400, seed=11)
    null = r[r["delta"] == 0]
    assert null["power"].between(0.01, 0.10).all()          # type I error near 5%
    assert r["coverage"].between(0.90, 0.99).all()          # CI coverage near 95%
    r4 = P.run_comparisons(400, "Planned targets", 0.0, deltas=(0.2,), reps=400, seed=12)
    a = r[r["delta"] == 0.2].set_index("comparison")["power"]
    b = r4.set_index("comparison")["power"]
    assert (b >= a - 0.03).all()                             # more women, more power


def test_simulation_matches_analytic():
    # equal groups of ~100 (HMB vs none at n=200): analytic power for 20 points ~ 0.8
    r = P.run_comparisons(200, "Planned targets", 0.0, deltas=(0.2,), reps=800, seed=13)
    p = r.set_index("comparison").loc["hmb_vs_none", "power"]
    assert 0.72 < p < 0.92


def test_clustering_hurts_whole_sample_ci():
    ok = P.run_prevalence_coverage(200, 0.0, reps=800, seed=14)
    bad = P.run_prevalence_coverage(200, 0.05, reps=800, seed=14)
    assert ok["coverage"] > 0.92 and bad["coverage"] < ok["coverage"] - 0.04


def test_interaction_needs_bigger_sample():
    it = P.run_interaction(200, 0.0, 0.2, reps=400, seed=15)
    assert it["power_interaction"] < it["power_main_effect_same_size"] - 0.3


def test_firth_budget():
    f = P.run_firth(200, "delay_long", reps=30, seed=16)
    assert f["median_budget"] < 5


def test_current_data_checks():
    a = derive.analytic(derive.derive(demo.generate(150, seed=21)))
    cc = P.comparison_capacity(a, 0.02, P.mean_cluster_size(a["hear_about_this_survey"]))
    assert len(cc) >= 6 and cc["Verdict"].notna().all()
    assert (cc.loc[cc[["n A", "n B"]].min(axis=1) < 40, "Verdict"].str.startswith("Descriptive")).all()
    rt = P.recruitment_vs_targets(a)
    assert list(rt["Target"]) == [100, 60, 40]
    inf = P.informativeness(a, ["hmb", "care_trad_only"], 200)
    assert set(inf["Kind"]) == {"Indicator", "Band distribution"}
    assert P.model_capacity(a)["Parameter budget (EPV 10)"].ge(0).all()


def test_cached_results_present_and_brief():
    res = P.load()
    assert res is not None, "run python tools/run_power_sim.py"
    assert len(P.brief(res)) >= 5
    assert np.isfinite(P.needed_table(res["comparisons"])["Total n for 20 pp"]).all()
