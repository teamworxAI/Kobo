"""Estimation and testing used across the dashboard.

* Proportions: Wilson score 95% CI.
* Differences in proportions: Newcombe hybrid score CI (method 10).
* Categorical association: Pearson chi-square; Fisher's exact test for 2x2
  tables with an expected count < 5; for larger sparse tables a Monte Carlo
  permutation version of the chi-square test (10 000 draws).
* Ordinal bands: Mann-Whitney U with the rank-biserial correlation as effect size.
* Models: Firth (bias-reduced) logistic regression, profile penalised-likelihood
  95% CIs, reported as odds ratios.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import optimize, stats

Z = stats.norm.ppf(0.975)


# --------------------------------------------------------------------------
# proportions
# --------------------------------------------------------------------------
def wilson(k: float, n: float, z: float = Z) -> tuple[float, float]:
    if n <= 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    n, k = int(len(s)), int(s.sum())
    lo, hi = wilson(k, n)
    return {"n": n, "k": k, "p": (k / n) if n else np.nan, "lo": lo, "hi": hi}


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """p1 - p2 with Newcombe's hybrid score interval."""
    if min(n1, n2) == 0:
        return (np.nan, np.nan, np.nan)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------
@dataclass
class TestResult:
    method: str
    statistic: float
    p: float
    effect: float = np.nan
    effect_name: str = ""
    note: str = ""

    def as_dict(self):
        return {"Test": self.method, "Statistic": self.statistic, "p": self.p,
                "Effect size": self.effect, "Effect measure": self.effect_name, "Note": self.note}


def _chi2_stat(obs: np.ndarray) -> float:
    exp = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.nansum((obs - exp) ** 2 / np.where(exp == 0, np.nan, exp)))


def categorical_test(x: pd.Series, g: pd.Series, n_perm: int = 10000, seed: int = 1) -> TestResult | None:
    """Association between a categorical outcome x and grouping g."""
    m = x.notna() & g.notna()
    x, g = x[m].astype(str), g[m].astype(str)
    if x.nunique() < 2 or g.nunique() < 2:
        return None
    tab = pd.crosstab(x, g).to_numpy()
    n = tab.sum()
    exp = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / n
    r, c = tab.shape
    v = np.sqrt(_chi2_stat(tab) / (n * (min(r, c) - 1)))
    if (exp < 5).any():
        if tab.shape == (2, 2):
            odds, p = stats.fisher_exact(tab)
            return TestResult("Fisher's exact", odds, p, v, "Cramér's V", "expected count < 5")
        # Monte Carlo permutation of group labels (exact conditional test approximation)
        rng = np.random.default_rng(seed)
        xc = pd.Categorical(x).codes
        gc = pd.Categorical(g).codes
        obs_stat = _chi2_stat(tab)
        ge = 0
        for _ in range(n_perm):
            gp = rng.permutation(gc)
            t = np.zeros((r, c))
            np.add.at(t, (xc, gp), 1)
            ge += _chi2_stat(t) >= obs_stat - 1e-12
        p = (ge + 1) / (n_perm + 1)
        return TestResult("Chi-square (Monte Carlo exact)", obs_stat, p, v, "Cramér's V",
                          "expected count < 5")
    chi2, p, dof, _ = stats.chi2_contingency(tab, correction=False)
    return TestResult(f"Chi-square (df={dof})", chi2, p, v, "Cramér's V")


def mann_whitney(y: pd.Series, g: pd.Series, a: str, b: str) -> TestResult | None:
    """Ordinal outcome y (numeric codes) between groups a and b."""
    ya = pd.to_numeric(y[g == a], errors="coerce").dropna()
    yb = pd.to_numeric(y[g == b], errors="coerce").dropna()
    if len(ya) < 2 or len(yb) < 2:
        return None
    u, p = stats.mannwhitneyu(ya, yb, alternative="two-sided")
    rb = 2 * u / (len(ya) * len(yb)) - 1  # rank-biserial: >0 means a tends higher
    return TestResult("Mann–Whitney U", u, p, rb, "Rank-biserial r")


# --------------------------------------------------------------------------
# Firth logistic regression
# --------------------------------------------------------------------------
@dataclass
class FirthResult:
    names: list[str]
    coef: np.ndarray
    ci: np.ndarray
    p: np.ndarray
    n: int
    events: int
    loglik: float
    converged: bool
    notes: list[str] = field(default_factory=list)

    def table(self) -> pd.DataFrame:
        return pd.DataFrame({
            "Term": self.names, "OR": np.exp(self.coef), "OR low": np.exp(self.ci[:, 0]),
            "OR high": np.exp(self.ci[:, 1]), "p (PLR)": self.p})


def _firth_fit(X, y, offset=None, fixed: dict | None = None, max_iter=100, tol=1e-8):
    """Maximise the Firth-penalised log-likelihood. `fixed` pins some coefficients."""
    n, k = X.shape
    fixed = fixed or {}
    free = [j for j in range(k) if j not in fixed]
    beta = np.zeros(k)
    for j, v in fixed.items():
        beta[j] = v
    off = np.zeros(n) if offset is None else offset

    def pll(b):
        eta = X @ b + off
        p = 1 / (1 + np.exp(-eta))
        w = p * (1 - p)
        info = X.T @ (X * w[:, None])
        sign, logdet = np.linalg.slogdet(info)
        ll = np.sum(y * eta - np.logaddexp(0, eta))
        return ll + 0.5 * logdet, p, w, info

    cur, *_ = pll(beta)
    converged = False
    for _ in range(max_iter):
        val, p, w, info = pll(beta)
        info_inv = np.linalg.pinv(info)
        h = w * np.einsum("ij,jk,ik->i", X, info_inv, X)  # hat diagonal
        score = X.T @ (y - p + h * (0.5 - p))
        Xf = X[:, free]
        info_f = info[np.ix_(free, free)]
        step = np.linalg.solve(info_f + 1e-10 * np.eye(len(free)), score[free])
        step = np.clip(step, -5, 5)
        t = 1.0
        while t > 1e-6:
            nb = beta.copy()
            nb[free] = beta[free] + t * step
            nv, *_ = pll(nb)
            if nv >= val - 1e-12:
                break
            t /= 2
        beta = nb
        if np.max(np.abs(t * step)) < tol:
            converged = True
            break
        del Xf
    val, *_ = pll(beta)
    return beta, val, converged


def firth_logit(df: pd.DataFrame, outcome: str, covariates: list[str]) -> FirthResult | None:
    """Fit outcome ~ covariates (complete cases). Categorical covariates are dummy-coded
    against their first (most common) level."""
    data = df[[outcome] + covariates].dropna()
    if len(data) < 10:
        return None
    y = data[outcome].astype(float).to_numpy()
    parts = [pd.Series(1.0, index=data.index, name="Intercept")]
    notes = []
    for c in covariates:
        col = data[c]
        if col.dtype.kind in "if" and col.nunique() > 2:
            parts.append(col.astype(float).rename(c))
        else:
            if isinstance(col.dtype, pd.CategoricalDtype):
                present = set(col.astype(str))
                levels = [str(x) for x in col.cat.categories if str(x) in present]
                col = col.astype(str)
            else:
                col = col.astype(str)
                levels = col.value_counts().index.tolist()
                if set(levels) <= {"0", "1", "0.0", "1.0"}:
                    levels = sorted(levels)
            ref = levels[0]
            if ref not in ("0", "0.0"):
                notes.append(f"{c}: reference = {ref}")
            for lev in levels[1:]:
                parts.append((col.astype(str) == lev).astype(float).rename(f"{c}: {lev}"))
    X = pd.concat(parts, axis=1)
    names = list(X.columns)
    Xv = X.to_numpy()
    beta, ll, conv = _firth_fit(Xv, y)
    k = len(beta)
    crit = stats.chi2.ppf(0.95, 1) / 2
    ci = np.full((k, 2), np.nan)
    pvals = np.full(k, np.nan)
    for j in range(k):
        def prof(b, j=j):
            _, v, _ = _firth_fit(Xv, y, fixed={j: b})
            return v

        l0 = prof(0.0)
        pvals[j] = stats.chi2.sf(max(0.0, 2 * (ll - l0)), 1)
        f = lambda b: ll - prof(b) - crit  # noqa: E731
        for side, sign in ((0, -1), (1, 1)):
            step = 0.5
            b2 = beta[j] + sign * step
            tries = 0
            while f(b2) < 0 and tries < 30:
                step *= 1.8
                b2 = beta[j] + sign * step
                tries += 1
            if f(b2) >= 0:
                try:
                    ci[j, side] = optimize.brentq(f, beta[j], b2, xtol=1e-5) if sign > 0 else \
                        optimize.brentq(f, b2, beta[j], xtol=1e-5)
                except ValueError:
                    pass
    return FirthResult(names, beta, ci, pvals, int(len(y)), int(y.sum()), ll, conv, notes)
