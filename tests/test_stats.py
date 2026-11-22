import numpy as np
import pandas as pd
import pytest

from wema import stats as S


def test_wilson_reference():
    lo, hi = S.wilson(20, 100)
    assert lo == pytest.approx(0.1334, abs=1e-4) and hi == pytest.approx(0.2888, abs=1e-4)
    assert S.wilson(0, 10)[0] == 0


def test_newcombe_reference():
    # Newcombe (1998) example: 56/70 vs 48/80 -> 0.0524 to 0.3339
    d, lo, hi = S.newcombe_diff(56, 70, 48, 80)
    assert d == pytest.approx(0.2)
    assert lo == pytest.approx(0.0524, abs=1e-3) and hi == pytest.approx(0.3339, abs=1e-3)


def test_firth_single_binary_equals_haldane():
    a, b, c, d = 8, 2, 3, 12
    df = pd.DataFrame({"y": [1] * a + [0] * b + [1] * c + [0] * d, "x": [1] * (a + b) + [0] * (c + d)})
    r = S.firth_logit(df, "y", ["x"])
    assert np.exp(r.coef[1]) == pytest.approx(((a + .5) * (d + .5)) / ((b + .5) * (c + .5)), rel=1e-4)
    assert r.ci[1, 0] < r.coef[1] < r.ci[1, 1]


def test_firth_finite_under_separation():
    df = pd.DataFrame({"y": [1] * 6 + [0] * 6, "x": [1] * 6 + [0] * 6})
    r = S.firth_logit(df, "y", ["x"])
    assert np.isfinite(r.coef).all()


def test_categorical_test_switches_to_fisher():
    x = pd.Series([1, 1, 1, 0, 0, 0, 0, 1])
    g = pd.Series(list("aaaabbbb"))
    assert S.categorical_test(x, g).method == "Fisher's exact"
