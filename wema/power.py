"""What can a sample of a given size and composition show?

Two parts:

1. **Analytic planning tools** (instant): CI half-widths, minimum detectable
   difference (MDD) for two groups, sample size per group, design effect for
   clustered recruitment, events-per-variable budget, and an informativeness
   check that runs on any dataset (real or synthetic).

2. **Monte Carlo simulation** (tools/run_power_sim.py, results cached in
   wema/data/): generate many datasets at several sample sizes, condition mixes
   and amounts of clustering by recruitment channel, plant effects of known
   size, run the planned analyses, and record how often they recover the effect
   (power), how often they report an effect that is not there (type I error), and
   whether the 95% CIs contain the truth (coverage).

The simulator works at the level of the analysis variables, not the full
questionnaire, so that thousands of datasets can be generated quickly. Every
input is an assumption, listed in DEFAULTS and written to the results metadata.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats as sps

from . import config as C
from . import stats as S

DATA_DIR = Path(__file__).with_name("data")
Z = sps.norm.ppf(0.975)
Z80 = sps.norm.ppf(0.80)

# Recruitment targets from the study plan (know or suspect each condition)
TARGETS = {"Fibroids": 100, "Endometriosis or adenomyosis": 60, "PMOS / PCOS": 40}
TARGET_N = 200


# ===========================================================================
# 1. Analytic tools
# ===========================================================================
def half_width(n: float, p: float = 0.5) -> float:
    """95% CI half-width (normal approximation) for a proportion."""
    return Z * math.sqrt(p * (1 - p) / n) if n > 0 else float("nan")


def design_effect(mean_cluster_size: float, icc: float) -> float:
    return 1 + max(mean_cluster_size - 1, 0) * icc


def mdd(n1: float, n2: float, p_ref: float = 0.5, power: float = 0.8, alpha: float = 0.05,
        deff: float = 1.0) -> float:
    """Smallest difference in proportions (absolute) detectable with the given power,
    two-sided test, unequal groups. Solved on the exact normal-approximation formula."""
    if min(n1, n2) <= 1:
        return float("nan")
    za, zb = sps.norm.ppf(1 - alpha / 2), sps.norm.ppf(power)
    n1e, n2e = n1 / deff, n2 / deff

    def f(d):
        p1 = min(p_ref + d, 0.999)
        pbar = (n1e * p1 + n2e * p_ref) / (n1e + n2e)
        se0 = math.sqrt(pbar * (1 - pbar) * (1 / n1e + 1 / n2e))
        se1 = math.sqrt(p1 * (1 - p1) / n1e + p_ref * (1 - p_ref) / n2e)
        return d - (za * se0 + zb * se1)

    hi = 0.999 - p_ref
    if f(hi) < 0:
        return float("nan")
    return optimize.brentq(f, 1e-6, hi)


def n_per_group(delta: float, p_ref: float = 0.5, power: float = 0.8, alpha: float = 0.05,
                deff: float = 1.0) -> int:
    """Women needed in EACH of two equal groups to detect `delta` (absolute)."""
    za, zb = sps.norm.ppf(1 - alpha / 2), sps.norm.ppf(power)
    p1 = min(p_ref + delta, 0.999)
    pbar = (p1 + p_ref) / 2
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p_ref * (1 - p_ref))) ** 2
    return int(math.ceil(n / delta ** 2 * deff))


def epv_budget(events: int, nonevents: int, per: int = 10) -> int:
    return min(events, nonevents) // per


def mean_cluster_size(channel: pd.Series) -> float:
    """Average recruitment-channel size experienced by a respondent (size-weighted),
    which is what drives the design effect."""
    c = channel.dropna().value_counts()
    if c.sum() == 0:
        return 1.0
    return float((c ** 2).sum() / c.sum())


# ---------------------------------------------------------------------------
# informativeness of each indicator / band item in the data at hand
# ---------------------------------------------------------------------------
BAND_ITEMS = {
    "spend_manage_menstrual_condition": ("Product spend, past 30 days (Q72)", C.PRODUCT_BANDS),
    "spend_pain_doctor_visit": ("Care spend, past 12 months (Q73)", C.CARE_BANDS),
    "days_missed_each_month": ("Days of work/school lost (Q77)", C.DAYS_ORDER),
    "days_hh_duties_missed": ("Days of household duties lost (Q78)", C.DAYS_ORDER),
    "burden_condition_places": ("Financial burden (Q76)", C.BURDEN_ORDER),
    "experience_pain_before_during_period": ("Pain severity (Q21)", C.PAIN_ORDER),
}


def informativeness(a: pd.DataFrame, indicators: list[str], target_n: int | None = None) -> pd.DataFrame:
    """Flags indicators that are too rare (or too common) to report or model, and
    answer scales that put almost everyone in one category. With `target_n`, counts are
    projected to that sample size at the observed proportions."""
    from .derive import IND
    rows = []
    scale = (target_n / len(a)) if (target_n and len(a)) else 1.0
    for col in indicators:
        if col not in a:
            continue
        s = pd.to_numeric(a[col], errors="coerce").dropna()
        n, k = len(s), int(s.sum())
        nn, kk = n * scale, k * scale
        minority = min(kk, nn - kk)
        if n == 0:
            verdict = "No data"
        elif minority < 10:
            verdict = "Too rare / too common to model (fewer than 10 in one category)"
        elif minority < 20:
            verdict = "Report with caution (small minority category)"
        else:
            verdict = "OK"
        rows.append({"Indicator": IND[col].label if col in IND else col, "Kind": "Indicator",
                     "n": round(nn), "Events": round(kk), "%": k / n if n else np.nan,
                     "Smallest category": round(minority), "Verdict": verdict})
    for field_, (label, order) in BAND_ITEMS.items():
        if field_ not in a:
            continue
        s = a[field_].dropna()
        s = s[s.isin(order)]
        n = len(s)
        if n == 0:
            continue
        counts = s.value_counts().reindex(order, fill_value=0) * scale
        top = counts.max() / counts.sum()
        thin = int((counts < 5).sum())
        if top > 0.8:
            verdict = "Little spread: over 80% in one band"
        elif thin > len(order) / 2:
            verdict = "Most bands nearly empty: collapse bands"
        elif thin:
            verdict = f"{thin} band(s) with fewer than 5: consider collapsing"
        else:
            verdict = "OK"
        rows.append({"Indicator": label, "Kind": "Band distribution", "n": round(n * scale), "Events": None,
                     "%": top, "Smallest category": round(counts.min()), "Verdict": verdict})
    return pd.DataFrame(rows)


# ===========================================================================
# 2. Monte Carlo simulation
# ===========================================================================
MIXES = {
    # probability that a respondent knows or suspects each condition (independent, so
    # some women report several); "Planned targets" reproduces 100 / 60 / 40 of 200
    "Planned targets": {"fibroids": 0.50, "endo_adeno": 0.30, "pmos": 0.20, "pmdd": 0.05},
    "Fibroid-heavy": {"fibroids": 0.65, "endo_adeno": 0.18, "pmos": 0.10, "pmdd": 0.03},
    "Endometriosis-heavy": {"fibroids": 0.30, "endo_adeno": 0.50, "pmos": 0.15, "pmdd": 0.08},
}


@dataclass
class Assumptions:
    p_diagnosed_given_condition: float = 0.55
    p_need_care: float = 0.85            # Q24 symptoms of concern (care-seeking denominator)
    p_insured: float = 0.60
    p_hmb: float = 0.40                  # plus 0.15 if fibroids
    p_nairobi: float = 0.50
    income_probs: tuple = (0.40, 0.25, 0.15, 0.20)
    support_group_share: float = 0.60    # recruited through advocacy / support groups
    n_support_groups: int = 6            # those split unevenly across this many groups
    other_channels: tuple = (0.45, 0.30, 0.15, 0.10)  # social media, friends, health worker, other
    # reference-group outcome rates for each planned comparison
    base: dict = field(default_factory=lambda: {
        "care_any": 0.50, "hardship": 0.45, "days_work3": 0.25, "delay_long": 0.40})


# (key, label, grouping, outcome, reference level is the 0-group)
COMPARISONS = [
    ("dx_vs_susp", "Diagnosed vs suspected only: care sought", "diagnosed", "care_any"),
    ("ins_vs_unins", "Insured vs uninsured: financial hardship", "insured", "hardship"),
    ("hmb_vs_none", "HMB proxy vs none: 3+ days lost", "hmb", "days_work3"),
    ("income_low_high", "Lowest vs highest income band: hardship", "income_low", "hardship"),
    ("nairobi_care", "Nairobi vs other: care sought", "nairobi", "care_any"),
    ("nairobi_delay", "Nairobi vs other: delay ≥3 years (diagnosed)", "nairobi", "delay_long"),
]


def _channels(rng, A: Assumptions):
    sg = rng.dirichlet(np.full(A.n_support_groups, 2.0)) * A.support_group_share
    other = np.asarray(A.other_channels) / np.sum(A.other_channels) * (1 - A.support_group_share)
    return np.concatenate([sg, other])


def _clustered_bernoulli(rng, p, chan, n_chan, icc):
    """Bernoulli with a channel-level shift on the probability scale (ICC on that scale)."""
    if icc <= 0:
        return rng.random(p.shape) < p
    p0 = np.clip(np.mean(p), 0.02, 0.98)
    tau = math.sqrt(icc * p0 * (1 - p0))
    shift = rng.normal(0, tau, size=(p.shape[0], n_chan))
    shift -= shift.mean(axis=1, keepdims=True)
    pp = np.clip(p + np.take_along_axis(shift, chan, axis=1), 0.001, 0.999)
    return rng.random(p.shape) < pp


def simulate_population(rng, n: int, reps: int, mix: dict, icc: float, A: Assumptions) -> dict:
    """Arrays of shape (reps, n): grouping variables, with recruitment-channel clustering."""
    probs = _channels(rng, A)
    n_chan = len(probs)
    chan = rng.choice(n_chan, size=(reps, n), p=probs)
    full = lambda p: np.full((reps, n), p)  # noqa: E731
    cb = lambda p: _clustered_bernoulli(rng, p, chan, n_chan, icc)  # noqa: E731
    fib = cb(full(mix["fibroids"]))
    endo = cb(full(mix["endo_adeno"]))
    pmos = cb(full(mix["pmos"]))
    pmdd = cb(full(mix["pmdd"]))
    anycond = fib | endo | pmos | pmdd
    dx = anycond & cb(full(A.p_diagnosed_given_condition))
    inc_u = rng.random((reps, n))
    cum = np.cumsum(A.income_probs)
    income = np.searchsorted(cum, inc_u)
    return {
        "chan": chan, "n_chan": n_chan, "fib": fib, "endo": endo, "pmos": pmos, "pmdd": pmdd,
        "anycond": anycond, "diagnosed": dx, "suspected": anycond & ~dx,
        "insured": cb(full(A.p_insured)), "hmb": cb(np.where(fib, A.p_hmb + 0.15, A.p_hmb)),
        "nairobi": cb(full(A.p_nairobi)), "income": income,
        "need": rng.random((reps, n)) < A.p_need_care,
        "dx_fib": fib & dx, "dx_endo": endo & dx, "dx_pmos": pmos & dx,
    }


def _wilson_vec(k, n):
    n = np.maximum(n, 1)
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return c - h, c + h


def _analyse(y, g1, g0):
    """Vectorised 2x2 analysis over reps: RD, Newcombe CI, chi-square/Fisher p."""
    n1, n0 = g1.sum(1), g0.sum(1)
    k1, k0 = (y & g1).sum(1), (y & g0).sum(1)
    p1, p0 = k1 / np.maximum(n1, 1), k0 / np.maximum(n0, 1)
    l1, u1 = _wilson_vec(k1, n1)
    l0, u0 = _wilson_vec(k0, n0)
    d = p1 - p0
    lo = d - np.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    hi = d + np.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    # Pearson chi-square, Fisher where an expected count < 5 (as in the dashboard)
    N = n1 + n0
    K = k1 + k0
    with np.errstate(divide="ignore", invalid="ignore"):
        e = np.stack([n1 * K / N, n1 * (N - K) / N, n0 * K / N, n0 * (N - K) / N])
        o = np.stack([k1, n1 - k1, k0, n0 - k0])
        chi = np.nansum((o - e) ** 2 / np.where(e > 0, e, np.nan), axis=0)
    p = sps.chi2.sf(chi, 1)
    small = (e.min(axis=0) < 5) & (N > 0)
    for i in np.where(small)[0]:
        p[i] = sps.fisher_exact([[k1[i], n1[i] - k1[i]], [k0[i], n0[i] - k0[i]]])[1]
    p[(n1 == 0) | (n0 == 0) | (K == 0) | (K == N)] = 1.0
    return d, lo, hi, p, n1, n0


def run_comparisons(n: int, mix_name: str, icc: float, deltas=(0, .10, .15, .20, .25), reps: int = 1000,
                    seed: int = 1, A: Assumptions | None = None) -> pd.DataFrame:
    A = A or Assumptions()
    rng = np.random.default_rng(seed)
    pop = simulate_population(rng, n, reps, MIXES[mix_name], icc, A)
    out = []
    for key, label, gvar, outcome in COMPARISONS:
        if gvar == "diagnosed":
            g1, g0 = pop["diagnosed"], pop["suspected"]
        elif gvar == "income_low":
            g1, g0 = pop["income"] == 0, pop["income"] == 3
        else:
            g1, g0 = pop[gvar], ~pop[gvar]
        mask = np.ones_like(g1)
        if outcome == "care_any":
            mask = pop["need"]
        if outcome == "delay_long":
            mask = pop["diagnosed"]
        g1, g0 = g1 & mask, g0 & mask
        base = A.base[outcome]
        for delta in deltas:
            p = np.where(g1, base + delta, base)
            y = _clustered_bernoulli(rng, p, pop["chan"], pop["n_chan"], icc)
            d, lo, hi, pv, n1, n0 = _analyse(y, g1, g0)
            ok = (n1 > 0) & (n0 > 0)
            out.append({
                "n": n, "mix": mix_name, "icc": icc, "comparison": key, "label": label, "delta": delta,
                "power": float(np.mean((pv[ok] < 0.05) & (np.sign(d[ok]) == np.sign(delta) if delta else True))),
                "coverage": float(np.mean((lo[ok] <= delta) & (hi[ok] >= delta))),
                "mean_est": float(np.mean(d[ok])),
                "n_group1": float(np.mean(n1)), "n_group0": float(np.mean(n0)),
                "p_small_group": float(np.mean(np.minimum(n1, n0) < C.SMALL_N)),
                "reps": int(reps),
            })
    return pd.DataFrame(out)


def run_composition(n: int, mix_name: str, icc: float, reps: int = 1000, seed: int = 2,
                    A: Assumptions | None = None) -> pd.DataFrame:
    """Group sizes each design produces, and how often each condition is reportable."""
    A = A or Assumptions()
    rng = np.random.default_rng(seed)
    pop = simulate_population(rng, n, reps, MIXES[mix_name], icc, A)
    rows = []
    items = [("Know or suspect fibroids", pop["fib"]), ("Know or suspect endometriosis / adenomyosis", pop["endo"]),
             ("Know or suspect PMOS / PCOS", pop["pmos"]), ("Diagnosed (any)", pop["diagnosed"]),
             ("Suspected only", pop["suspected"]), ("No condition", ~pop["anycond"]),
             ("Diagnosed fibroids", pop["dx_fib"]), ("Diagnosed endometriosis / adenomyosis", pop["dx_endo"]),
             ("Diagnosed PMOS / PCOS", pop["dx_pmos"]), ("Insured", pop["insured"]), ("Uninsured", ~pop["insured"]),
             ("HMB proxy", pop["hmb"]), ("Nairobi", pop["nairobi"]),
             ("Lowest income band", pop["income"] == 0), ("Highest income band", pop["income"] == 3),
             ("Nairobi, diagnosed", pop["nairobi"] & pop["diagnosed"]),
             ("Other counties, diagnosed", ~pop["nairobi"] & pop["diagnosed"])]
    for label, arr in items:
        c = arr.sum(1)
        rows.append({"n": n, "mix": mix_name, "icc": icc, "Group": label, "Median n": float(np.median(c)),
                     "5th pct": float(np.percentile(c, 5)), "95th pct": float(np.percentile(c, 95)),
                     "P(n ≥ 40)": float(np.mean(c >= C.SMALL_N)), "P(n ≥ 100)": float(np.mean(c >= 100)),
                     "Half-width at median (pp)": 100 * half_width(max(np.median(c), 1))})
    return pd.DataFrame(rows)


def run_prevalence_coverage(n: int, icc: float, reps: int = 2000, seed: int = 3, p: float = 0.4,
                            A: Assumptions | None = None) -> dict:
    """Does a 95% Wilson CI for a whole-sample prevalence still cover 95% under clustering?"""
    A = A or Assumptions()
    rng = np.random.default_rng(seed)
    probs = _channels(rng, A)
    chan = rng.choice(len(probs), size=(reps, n), p=probs)
    y = _clustered_bernoulli(rng, np.full((reps, n), p), chan, len(probs), icc)
    k = y.sum(1)
    lo, hi = _wilson_vec(k, np.full(reps, n))
    m = float(np.mean([mean_cluster_size(pd.Series(c)) for c in chan[:50]]))
    return {"n": n, "icc": icc, "coverage": float(np.mean((lo <= p) & (hi >= p))),
            "mean_cluster_size": m, "design_effect": design_effect(m, icc),
            "nominal_half_width_pp": 100 * half_width(n, p),
            "actual_half_width_pp": 100 * half_width(n, p) * math.sqrt(design_effect(m, icc))}


def run_interaction(n: int, icc: float, delta: float = 0.20, reps: int = 1000, seed: int = 4,
                    A: Assumptions | None = None) -> dict:
    """Power for a difference-in-differences (HMB x insurance on hardship) of size
    `delta`, against power for a main effect of the same size."""
    A = A or Assumptions()
    rng = np.random.default_rng(seed)
    pop = simulate_population(rng, n, reps, MIXES["Planned targets"], icc, A)
    h, i = pop["hmb"], pop["insured"]
    base = A.base["hardship"]
    p = base + np.where(h & ~i, delta, 0.0)      # HMB raises hardship only among the uninsured
    y = _clustered_bernoulli(rng, p, pop["chan"], pop["n_chan"], icc)

    def cell(m):
        nn = m.sum(1)
        return (y & m).sum(1) / np.maximum(nn, 1), np.maximum(nn, 1)

    pa, na = cell(h & ~i)
    pb, nb = cell(~h & ~i)
    pc, nc = cell(h & i)
    pd_, nd = cell(~h & i)
    did = (pa - pb) - (pc - pd_)
    se = np.sqrt(sum(pp * (1 - pp) / nn for pp, nn in ((pa, na), (pb, nb), (pc, nc), (pd_, nd))))
    z = did / np.where(se > 0, se, np.nan)
    power_int = float(np.nanmean(np.abs(z) > Z))
    # the same-sized effect as a whole-sample main effect (HMB vs none, everyone)
    y2 = _clustered_bernoulli(rng, base + np.where(h, delta, 0.0), pop["chan"], pop["n_chan"], icc)
    _, _, _, pv, *_ = _analyse(y2, h, ~h)
    return {"n": n, "icc": icc, "delta": delta, "power_interaction": power_int,
            "power_main_effect_same_size": float(np.mean(pv < 0.05))}


def run_firth(n: int, outcome: str, or_exposure: float = 2.0, reps: int = 200, seed: int = 5,
              A: Assumptions | None = None) -> dict:
    """Events-per-variable budget and power of the pre-specified Firth model to recover
    an odds ratio for insurance, adjusting for the covariates the budget allows."""
    A = A or Assumptions()
    rng = np.random.default_rng(seed)
    base = {"care_any": 0.55, "hardship": 0.45, "delay_long": 0.42}[outcome]
    frac = {"care_any": A.p_need_care, "hardship": 1.0,
            "delay_long": 0.85 * A.p_diagnosed_given_condition}[outcome]
    detected, budgets, n_covs, events_l = [], [], [], []
    for _ in range(reps):
        m = int(rng.binomial(n, frac))
        age = rng.normal(31, 8, m)
        ins = (rng.random(m) < A.p_insured).astype(float)
        inc = np.searchsorted(np.cumsum(A.income_probs), rng.random(m)).astype(float)
        edu = rng.choice(3, m, p=[.25, .3, .45])
        lp = math.log(base / (1 - base)) + math.log(or_exposure) * (ins - ins.mean()) - 0.1 * (inc - inc.mean())
        y = (rng.random(m) < 1 / (1 + np.exp(-lp))).astype(float)
        ev = int(y.sum())
        budget = min(ev, m - ev) // 10
        cols = [np.ones(m), age, ins, inc, (edu == 1).astype(float), (edu == 2).astype(float)]
        k = 1 + min(budget, 5)  # intercept + allowed parameters in priority order
        if budget < 2:           # cannot carry insurance alongside age
            detected.append(False)
            budgets.append(budget)
            n_covs.append(0)
            events_l.append(ev)
            continue
        X = np.column_stack(cols[:k])
        beta, ll, _ = S._firth_fit(X, y)
        _, l0, _ = S._firth_fit(X, y, fixed={2: 0.0})
        p = sps.chi2.sf(max(0.0, 2 * (ll - l0)), 1)
        detected.append(p < 0.05 and beta[2] > 0)
        budgets.append(budget)
        n_covs.append(k - 1)
        events_l.append(ev)
    return {"n": n, "outcome": outcome, "or": or_exposure, "power": float(np.mean(detected)),
            "median_events": float(np.median(events_l)), "median_budget": float(np.median(budgets)),
            "p_all_4_covariates": float(np.mean(np.array(budgets) >= 5)),
            "median_parameters_used": float(np.median(n_covs))}


# ===========================================================================
# grid runner and cached results
# ===========================================================================
GRID = dict(ns=(200, 400, 800), mixes=tuple(MIXES), iccs=(0.0, 0.02, 0.05, 0.10),
            deltas=(0.0, 0.10, 0.15, 0.20, 0.25))


def run_all(reps: int = 1000, firth_reps: int = 200, progress=print) -> dict[str, pd.DataFrame]:
    A = Assumptions()
    comp, compo, cov, inter, firth = [], [], [], [], []
    seed = 100
    for n in GRID["ns"]:
        for mix in GRID["mixes"]:
            for icc in GRID["iccs"]:
                seed += 1
                comp.append(run_comparisons(n, mix, icc, GRID["deltas"], reps, seed, A))
                compo.append(run_composition(n, mix, icc, reps, seed + 5000, A))
        for icc in GRID["iccs"]:
            cov.append(run_prevalence_coverage(n, icc, 2000, seed + 9000, A=A))
            inter.append(run_interaction(n, icc, 0.20, reps, seed + 7000, A))
        for outcome in ("care_any", "hardship", "delay_long"):
            firth.append(run_firth(n, outcome, 2.0, firth_reps, seed + 8000, A))
        progress(f"n={n} done")
    return {"comparisons": pd.concat(comp, ignore_index=True),
            "composition": pd.concat(compo, ignore_index=True),
            "prevalence_coverage": pd.DataFrame(cov), "interaction": pd.DataFrame(inter),
            "firth": pd.DataFrame(firth),
            "_meta": {"reps": reps, "firth_reps": firth_reps, "grid": GRID, "assumptions": asdict(A),
                      "mixes": MIXES, "comparisons": COMPARISONS}}


def save(results: dict, folder: Path = DATA_DIR) -> None:
    folder.mkdir(exist_ok=True)
    for k, v in results.items():
        if k == "_meta":
            (folder / "power_meta.json").write_text(json.dumps(v, indent=1, default=list))
        else:
            v.to_csv(folder / f"power_{k}.csv", index=False)


def load(folder: Path = DATA_DIR) -> dict | None:
    if not (folder / "power_meta.json").exists():
        return None
    out = {k: pd.read_csv(folder / f"power_{k}.csv") for k in
           ("comparisons", "composition", "prevalence_coverage", "interaction", "firth")}
    out["_meta"] = json.loads((folder / "power_meta.json").read_text())
    return out


def min_n_for_power(comp: pd.DataFrame, target: float = 0.8) -> pd.DataFrame:
    """Smallest simulated total n reaching the target power, per comparison, effect, mix, ICC."""
    d = comp[comp["delta"] > 0]
    rows = []
    for (key, label, mix, icc, delta), g in d.groupby(["comparison", "label", "mix", "icc", "delta"]):
        ok = g[g["power"] >= target].sort_values("n")
        if len(ok):
            r = ok.iloc[0]
            rows.append({"comparison": key, "label": label, "mix": mix, "icc": icc, "delta": delta,
                         "min_total_n": int(r["n"]), "smaller_group_n": int(round(min(r["n_group1"], r["n_group0"])))})
        else:
            rows.append({"comparison": key, "label": label, "mix": mix, "icc": icc, "delta": delta,
                         "min_total_n": None, "smaller_group_n": None})
    return pd.DataFrame(rows)


# ===========================================================================
# 3. Applying it: current data and planning summaries
# ===========================================================================
PRIMARY_OUTCOME = {
    "Diagnosed vs suspected only": "care_any",
    "Insured vs uninsured": "hardship",
    "HMB proxy vs none": "days_work3",
    "Lowest vs highest income band": "hardship",
    "Nairobi vs other counties": "care_any",
    "Sensitivity: support-group recruits vs other routes": "care_any",
}


def comparison_capacity(a: pd.DataFrame, icc: float = 0.0, m: float = 1.0) -> pd.DataFrame:
    """For each pre-specified comparison in the data at hand: group sizes, margins of
    error (also allowing for clustering by recruitment channel), and the smallest
    difference detectable with 80% power. The simulation shows that clustering inflates
    single-group margins of error but barely affects between-group comparisons (both
    groups come from the same channels), so the design effect is applied to the margins
    only."""
    from .tables import COMPARISONS as SPECS
    from .derive import IND
    deff = design_effect(m, icc)
    rows = []
    extra = [("Nairobi vs other counties", "delay_long_any")]
    items = [(k, PRIMARY_OUTCOME.get(k, "care_any")) for k in SPECS] + extra
    for name, outcome in items:
        spec = SPECS[name]
        g = a[spec["gcol"]]
        y = pd.to_numeric(a[outcome], errors="coerce")
        n1 = int(((g == spec["a"]) & y.notna()).sum())
        n0 = int(((g == spec["b"]) & y.notna()).sum())
        ref = y[(g == spec["b"])].mean()
        p_ref = float(ref) if pd.notna(ref) and 0.05 < ref < 0.95 else 0.5
        p_ref = min(p_ref, 0.75)
        d0 = mdd(n1, n0, p_ref) if min(n1, n0) > 1 else np.nan
        d1 = d0
        small = min(n1, n0)
        if small < C.SMALL_N:
            verdict = "Descriptive only (a group under 40)"
        elif np.isnan(d1) or d1 > 0.25:
            verdict = "Only very large differences (>25 points) detectable"
        elif d1 > 0.15:
            verdict = f"Large differences only (≥{100 * d1:.0f} points)"
        else:
            verdict = f"Moderate differences detectable (≥{100 * d1:.0f} points)"
        rows.append({"Comparison": name, "Outcome": IND[outcome].label if outcome in IND else outcome,
                     f"n {spec['a'][:18]}": n1, "n other group": n0, "Group A": spec["a"], "Group B": spec["b"],
                     "n A": n1, "n B": n0,
                     "± A (pp)": 100 * half_width(n1) if n1 else np.nan,
                     "± B (pp)": 100 * half_width(n0) if n0 else np.nan,
                     "± A with clustering": 100 * half_width(n1) * math.sqrt(deff) if n1 else np.nan,
                     "± B with clustering": 100 * half_width(n0) * math.sqrt(deff) if n0 else np.nan,
                     "Detectable difference (pp)": 100 * d0 if pd.notna(d0) else np.nan,
                     "Verdict": verdict})
    return pd.DataFrame(rows)[["Comparison", "Outcome", "Group A", "n A", "Group B", "n B", "± A (pp)", "± B (pp)",
                               "± A with clustering", "± B with clustering", "Detectable difference (pp)", "Verdict"]]


def recruitment_vs_targets(a: pd.DataFrame) -> pd.DataFrame:
    """Know-or-suspect and diagnosed counts against the plan's recruitment targets."""
    sets = {"Fibroids": ["fibroids"], "Endometriosis or adenomyosis": ["endo", "adeno"], "PMOS / PCOS": ["pmos"]}
    rows = []
    for label, keys in sets.items():
        ks = pd.concat([a[f"q29_{k}"] == 1 for k in keys] + [a[f"dx_{k}"] == 1 for k in keys], axis=1).any(axis=1)
        dx = pd.concat([a[f"dx_{k}"] == 1 for k in keys], axis=1).any(axis=1)
        rows.append({"Condition": label, "Target": TARGETS[label], "Know or suspect": int(ks.sum()),
                     "Diagnosed": int(dx.sum()), "% of target": ks.sum() / TARGETS[label],
                     "Diagnosed reportable (≥40)": bool(dx.sum() >= C.SMALL_N)})
    return pd.DataFrame(rows)


def model_capacity(a: pd.DataFrame) -> pd.DataFrame:
    labels = {"care_any": "Care sought", "hardship": "Financial hardship", "delay_long_any": "Delay ≥3 years"}
    rows = []
    for col, lab in labels.items():
        y = pd.to_numeric(a[col], errors="coerce").dropna()
        ev, ne = int(y.sum()), int((y == 0).sum())
        b = epv_budget(ev, ne)
        cov = []
        used = 0
        for name, df_ in (("age", 1), ("insurance", 1), ("income", 1), ("education", 2)):
            if used + df_ <= b:
                cov.append(name)
                used += df_
        rows.append({"Outcome": lab, "n": len(y), "Events": ev, "Non-events": ne, "Parameter budget (EPV 10)": b,
                     "Covariates the model can carry": ", ".join(cov) if cov else "none – report unadjusted",
                     "Events needed for all four (5 parameters)": max(0, 50 - min(ev, ne))})
    return pd.DataFrame(rows)


def total_n_needed(share_a: float, share_b: float, delta: float, p_ref: float = 0.5, deff: float = 1.0) -> float:
    """Total sample at which a comparison between groups making up `share_a` and
    `share_b` of the sample reaches 80% power for `delta` (analytic)."""
    def f(n):
        d = mdd(n * share_a, n * share_b, p_ref, deff=deff)
        return (1.0 if not np.isfinite(d) else d) - delta

    lo, hi = 10.0, 200000.0
    if f(hi) > 0:
        return float("nan")
    if f(lo) < 0:
        return lo
    return float(optimize.brentq(f, lo, hi))


def needed_table(comp: pd.DataFrame, A: Assumptions | None = None, deltas=(0.15, 0.20)) -> pd.DataFrame:
    """Total sample needed per comparison (analytic, using the group shares the
    simulation produced for the planned mix), with the simulated power at 200/400/800
    as a check."""
    A = A or Assumptions()
    base_for = {k: A.base[o] for k, _, _, o in COMPARISONS}
    c = comp[(comp["mix"] == "Planned targets") & (comp["icc"] == 0.0)]
    rows = []
    for key, label, _, _ in COMPARISONS:
        g = c[(c["comparison"] == key) & (c["n"] == 200)].iloc[0]
        sa, sb = g["n_group1"] / 200, g["n_group0"] / 200
        r = {"Comparison": label, "Share of sample in each group": f"{100 * sa:.0f}% / {100 * sb:.0f}%"}
        for d in deltas:
            n = total_n_needed(sa, sb, d, base_for[key])
            r[f"Total n for {100 * d:.0f} pp"] = int(math.ceil(n / 10) * 10) if np.isfinite(n) else None
            r[f"Smaller group for {100 * d:.0f} pp"] = int(math.ceil(n * min(sa, sb))) if np.isfinite(n) else None
            sims = c[(c["comparison"] == key) & (np.isclose(c["delta"], d))].set_index("n")["power"]
            r[f"Simulated power at 200/400/800 ({100 * d:.0f} pp)"] = " / ".join(f"{100 * sims.get(x, np.nan):.0f}%"
                                                                              for x in GRID["ns"])
        rows.append(r)
    return pd.DataFrame(rows)


def brief(res: dict) -> list[str]:
    """Plain-language answers drawn from the cached simulation results."""
    c, co, cov, it, fi = (res[k] for k in ("comparisons", "composition", "prevalence_coverage", "interaction", "firth"))
    plan = c[(c["mix"] == "Planned targets") & (c["icc"] == 0.02)]
    p200 = plan[(plan["n"] == 200) & (np.isclose(plan["delta"], 0.20))].set_index("label")["power"]
    ok = [f"{k.replace(': ', ' (')}, {100 * v:.0f}%)" for k, v in p200.sort_values(ascending=False).items() if v >= 0.75]
    weak = [k for k, v in p200.items() if v < 0.6]
    comp200 = co[(co["mix"] == "Planned targets") & (co["icc"] == 0.02) & (co["n"] == 200)].set_index("Group")
    cv = cov.set_index(["n", "icc"])
    i200, i800 = it[(it["n"] == 200) & (it["icc"] == 0.02)].iloc[0], it[(it["n"] == 800) & (it["icc"] == 0.02)].iloc[0]
    f = fi.set_index(["n", "outcome"])
    out = [
        f"**Is 200 enough?** For whole-sample estimates, yes (about ±7 points), and for comparisons between large "
        f"groups. A 20-point difference is detected about 80% of the time or more only for "
        f"{'; '.join(ok)}. It is not enough for smaller, 10–15-point differences, for comparisons that involve a "
        f"group of under about 60 women, for interactions, or for comparisons within diagnosed subgroups.",
        f"**Weakest comparisons at 200:** {'; '.join(weak) if weak else 'none'} – each has a group of about 40–60 "
        f"women, so only differences of 25 points or more are reliably detected.",
        f"**Condition-specific results:** with the planned mix, a sample of 200 gives a median of "
        f"{comp200.loc['Diagnosed fibroids', 'Median n']:.0f} diagnosed fibroid, "
        f"{comp200.loc['Diagnosed endometriosis / adenomyosis', 'Median n']:.0f} endometriosis/adenomyosis and "
        f"{comp200.loc['Diagnosed PMOS / PCOS', 'Median n']:.0f} PMOS women. Only fibroids reliably reaches the "
        f"40 needed for anything beyond description. If the targets (100 / 60 / 40) are meant for *diagnosed* "
        f"women, recruitment must aim at about {100 / 0.55:.0f} / {60 / 0.55:.0f} / {40 / 0.55:.0f} women who "
        f"know or suspect each condition.",
        f"**Clustering by recruitment channel** matters most for whole-sample percentages. With 60% recruited "
        f"through six support groups and a modest ICC of 0.02, the real margin of error at n = 200 is about "
        f"±{cv.loc[(200, 0.02), 'actual_half_width_pp']:.0f} points, not ±7, and nominal 95% CIs cover the truth "
        f"only {100 * cv.loc[(200, 0.02), 'coverage']:.0f}% of the time ({100 * cv.loc[(200, 0.05), 'coverage']:.0f}% "
        f"at ICC 0.05). Group comparisons are much less affected, because both groups come from the same channels. "
        f"Recruiting more widely, rather than more deeply in the same groups, is what fixes this.",
        f"**Interactions** (for example, whether heavy bleeding matters more for uninsured women): a 20-point "
        f"interaction is detected {100 * i200['power_interaction']:.0f}% of the time at n = 200 and "
        f"{100 * i800['power_interaction']:.0f}% at n = 800, against {100 * i200['power_main_effect_same_size']:.0f}% "
        f"for a main effect of the same size at n = 200 – roughly four times the sample, as expected.",
        f"**Models:** at n = 200 the care-sought and hardship models can carry all four pre-specified covariates "
        f"(about {f.loc[(200, 'care_any'), 'median_events']:.0f} events). The diagnostic-delay model has about "
        f"{f.loc[(200, 'delay_long'), 'median_events']:.0f} events, enough for "
        f"{f.loc[(200, 'delay_long'), 'median_budget']:.0f} parameters, and detects an odds ratio of 2 only "
        f"{100 * f.loc[(200, 'delay_long'), 'power']:.0f}% of the time; treat it as exploratory below n ≈ 400.",
    ]
    return out
