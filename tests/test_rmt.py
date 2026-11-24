"""Checks on the random-matrix machinery and the covariance comparison.

These are the tests that catch the two ways this project goes wrong: an edge
threshold that is silently too low (so noise looks like a factor), and a
min-variance solver that returns garbage weights.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from rmtfactor import cov, factors, mp, nulls, rolling


def _noise_matrix(t=500, n=40, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(t, n))


def test_mp_bounds_are_ordered_and_contain_the_median():
    a, b = mp.mp_bounds(1.0, 0.25)
    assert 0 < a < 1 < b
    assert a == pytest.approx(0.25)
    assert b == pytest.approx(2.25)


def test_mp_pdf_integrates_to_one():
    from scipy import integrate

    val = integrate.quad(lambda x: float(mp.mp_pdf(np.array([x]), 1.0, 0.3)[0]), 1e-6, 10, limit=200)[0]
    assert val == pytest.approx(1.0, abs=0.02)


def test_fit_sigma2_recovers_the_truth_on_pure_noise():
    x = _noise_matrix(t=2000, n=50, seed=1)
    c = np.corrcoef(x, rowvar=False)
    eigs = np.linalg.eigvalsh(c)
    fit = mp.fit_sigma2(eigs, q=50 / 2000)
    assert 0.8 < fit.sigma2 < 1.25
    assert fit.ks < 0.10


def test_tw_threshold_is_above_the_mp_edge():
    for t, n in ((500, 20), (250, 100), (2500, 500)):
        s2 = 1.0
        a, b = mp.mp_bounds(s2, n / t)
        assert mp.tw_threshold(t, n, s2) > b * 0.95


def test_tw_threshold_decreases_with_more_data():
    assert mp.tw_threshold(2500, 100, 1.0) < mp.tw_threshold(500, 100, 1.0)


def test_count_above_on_pure_noise_is_small():
    x = _noise_matrix(t=2000, n=50, seed=2)
    eigs = np.linalg.eigvalsh(np.corrcoef(x, rowvar=False))
    thr = mp.tw_threshold(2000, 50, 1.0)
    assert mp.count_above(eigs, thr) <= 2


def test_a_planted_factor_is_found():
    rng = np.random.default_rng(3)
    t, n = 1000, 40
    f = rng.normal(size=(t, 1))
    x = rng.normal(size=(t, n)) * 0.5 + f * 1.0
    eigs = np.linalg.eigvalsh(np.corrcoef(x, rowvar=False))
    thr = mp.tw_threshold(t, n, 1.0)
    assert mp.count_above(eigs, thr) >= 1


def test_inverse_participation_ratio_extremes():
    n = 20
    spread = np.ones(n) / np.sqrt(n)
    concentrated = np.eye(n)[0]
    assert mp.inverse_participation_ratio(spread) < mp.inverse_participation_ratio(concentrated)
    assert mp.inverse_participation_ratio(concentrated) == pytest.approx(1.0)


def test_independent_shuffle_destroys_correlation_but_keeps_marginals():
    rng = np.random.default_rng(4)
    base = pd.DataFrame(rng.normal(size=(400, 6)), columns=list("abcdef"))
    base["b"] = base["a"] * 0.9 + base["b"] * 0.1
    sh = nulls.shuffle_independent(base, rng)
    c = np.corrcoef(sh.to_numpy(), rowvar=False)
    off = c[~np.eye(6, dtype=bool)]
    assert np.abs(off).max() < 0.2
    assert np.allclose(np.sort(sh["a"]), np.sort(base["a"]))


def test_block_shuffle_preserves_length():
    rng = np.random.default_rng(5)
    base = pd.DataFrame(rng.normal(size=(103, 4)), columns=list("abcd"))
    out = nulls.block_shuffle(base, rng, block=20)
    assert out.shape == base.shape
    assert not out.isna().any().any()


def test_min_variance_weights_are_long_only_and_sum_to_one():
    rng = np.random.default_rng(6)
    x = rng.normal(size=(500, 10))
    w = cov.min_variance_weights(cov.sample_cov(x))
    assert (w >= -1e-12).all()
    assert w.sum() == pytest.approx(1.0)


def test_qlike_is_minimised_at_a_perfect_forecast():
    perfect = cov.qlike(0.04, 0.04)
    assert perfect == pytest.approx(0.0, abs=1e-9)
    assert cov.qlike(0.01, 0.04) > perfect
    assert cov.qlike(0.16, 0.04) > perfect


def test_diebold_mariano_detects_a_clear_ordering():
    rng = np.random.default_rng(7)
    a = rng.normal(0.10, 0.02, 300)
    b = rng.normal(0.12, 0.02, 300)
    out = cov.diebold_mariano(a, b, h=1)
    assert out["dm"] < -1.96 and out["significant"]


def test_diebold_mariano_is_not_significant_on_noise():
    rng = np.random.default_rng(8)
    a = rng.normal(0.10, 0.05, 300)
    b = rng.normal(0.10, 0.05, 300)
    assert abs(cov.diebold_mariano(a, b, h=1)["dm"]) < 3.0


def test_residualise_removes_a_constant_beta_exposure():
    rng = np.random.default_rng(9)
    t = 400
    idx = pd.date_range("2020-01-01", periods=t, freq="B")
    mkt = rng.normal(0, 0.01, t)
    ff = pd.DataFrame(
        {"Mkt-RF": mkt * 100, "SMB": 0.0, "HML": 0.0, "MOM": 0.0}, index=idx
    )
    ind = pd.DataFrame({f"ind{i}": np.zeros(t) for i in range(3)}, index=idx)
    rets = pd.DataFrame({"AAA": 2.0 * mkt + rng.normal(0, 1e-4, t)}, index=idx)
    resid, betas = factors.residualise(rets, factors.build_design(ff, ind), min_obs=100)
    assert abs(betas.loc["AAA", "Mkt-RF"] - 2.0) < 0.05
    assert resid["AAA"].std() < 0.01


def test_match_vectors_is_sign_agnostic():
    v = np.array([[1.0, 0.0], [0.0, 1.0]])
    flipped = np.array([[-1.0, 0.0], [0.0, -1.0]])
    pairs = rolling.match_vectors(v, flipped)
    assert len(pairs) == 2
    assert all(abs(cos - 1.0) < 1e-9 for _, _, cos in pairs)


def test_change_point_finds_a_planted_break():
    x = np.concatenate([np.ones(40), np.ones(40) * 3.0]) + np.random.default_rng(10).normal(0, 0.05, 80)
    out = rolling.change_point(x)
    assert 30 <= out["break_index"] <= 50
    assert out["p_value"] < 0.01


def test_change_point_is_null_on_noise():
    x = np.random.default_rng(11).normal(size=100)
    assert rolling.change_point(x)["p_value"] > 0.01


def test_basket_vector_is_normalised_and_rejects_no_overlap():
    v = factors.basket_vector(["NVDA", "MSFT", "XOM"], factors.ai_basket([]))
    assert v.sum() > 0
    assert np.linalg.norm(v) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        factors.basket_vector(["XOM"], factors.ai_basket([]))
