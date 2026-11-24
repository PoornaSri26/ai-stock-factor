"""Covariance estimators, and the out-of-sample comparison that is the point.

Estimators
----------
1. **sample** — the naive one. Included so its failure is visible.
2. **Ledoit-Wolf** — shrinkage toward a scaled identity (sklearn). This is the
   bar; beating it is the only claim worth making.
3. **RMT clipping** — replace eigenvalues inside the MP band by their average,
   keep the ones above the edge. Preserves the market mode, removes noise.
4. **factor-structured** — market factor + the AI factor explicitly + diagonal
   residuals (a POET-style estimator). This is where "knowing about the AI
   factor" is supposed to help, so it is the estimator under test.

Why min-variance blows up in sample: with N comparable to T, the sample
covariance has N-T+1 near-zero eigenvalues; inverting them amplifies estimation
error, so the "optimal" portfolio puts huge weights on accidental low-variance
directions. Shrinkage and clipping both work by refusing to believe those
directions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def sample_cov(x: np.ndarray) -> np.ndarray:
    return np.cov(x, rowvar=False, ddof=1)


def ledoit_wolf(x: np.ndarray) -> np.ndarray:
    from sklearn.covariance import ledoit_wolf as lw

    cov, _ = lw(x, assume_centered=False)
    return cov


def rmt_clip(x: np.ndarray, sigma2: float | None = None, q: float | None = None) -> np.ndarray:
    """Eigenvalue clipping at the MP edge (Laloux-Cizeau-Bouchaud).

    Inside the band: replace by the mean of the band (so the trace is preserved).
    Above the edge: keep. This is not a shrinking of the whole matrix; it is a
    statement that the band contains no information.
    """
    t, n = x.shape
    q = q if q is not None else n / t
    c = sample_cov(x)
    eigs, vecs = np.linalg.eigh(c)
    from .mp import mp_bounds

    a, b = mp_bounds(sigma2 if sigma2 is not None else float(np.median(eigs)), q)
    inside = (eigs >= a) & (eigs <= b)
    eigs_clipped = eigs.copy()
    if inside.any():
        eigs_clipped[inside] = eigs[inside].mean()
    out = vecs @ np.diag(eigs_clipped) @ vecs.T
    return 0.5 * (out + out.T)


def factor_structured(x: np.ndarray, n_factors: int = 2) -> np.ndarray:
    """Market + k factors from the top eigenvectors, diagonal residuals.

    ``n_factors=2`` includes the market mode and the next eigenvector — which,
    if the AI factor is real, is the AI factor. The point of the estimator is
    that it *names* it rather than leaving it inside a clipped bulk.
    """
    t, n = x.shape
    c = sample_cov(x)
    eigs, vecs = np.linalg.eigh(c)
    order = np.argsort(eigs)[::-1][:n_factors]
    v = vecs[:, order]
    lam = eigs[order]
    systematic = v @ np.diag(lam) @ v.T
    diag_resid = np.diag(np.clip(np.diag(c) - np.diag(systematic), 1e-10, None))
    out = systematic + diag_resid
    return 0.5 * (out + out.T)


ESTIMATORS = {
    "sample": sample_cov,
    "ledoit_wolf": ledoit_wolf,
    "rmt_clip": rmt_clip,
    "factor_2": factor_structured,
}


def min_variance_weights(cov: np.ndarray, long_only: bool = True) -> np.ndarray:
    """Minimum-variance weights, long-only by projected gradient.

    The closed form 1'Σ⁻¹/(1'Σ⁻¹1) is unconstrained and produces large short
    positions in a noisy Σ. Long-only is the honest version of what a fund would
    actually run, and it is solved here by a simple projected gradient so the
    code does not depend on a QP solver.
    """
    n = cov.shape[0]
    w = np.full(n, 1.0 / n)
    lr = 1.0 / (np.linalg.eigvalsh(cov).max() + 1e-12)
    for _ in range(500):
        grad = 2 * cov @ w
        w = w - lr * grad
        w = np.clip(w, 0.0, None)
        s = w.sum()
        if s <= 0:
            w = np.full(n, 1.0 / n)
            break
        w = w / s
        if np.linalg.norm(grad) < 1e-8:
            break
    return w


@dataclass(frozen=True)
class ForecastScore:
    estimator: str
    realised_var: float
    qlike: float
    frobenius: float
    n_periods: int

    def as_row(self) -> dict:
        return {
            "estimator": self.estimator,
            "realised_var": self.realised_var,
            "qlike": self.qlike,
            "frobenius": self.frobenius,
            "n_periods": self.n_periods,
        }


def realised_variance(w: np.ndarray, forward_returns: np.ndarray) -> float:
    """Variance actually realised by the weights over the next period."""
    pnl = forward_returns @ w
    return float(np.var(pnl, ddof=1)) if pnl.size > 1 else float(pnl**2)


def qlike(forecast: float, realised: float, eps: float = 1e-12) -> float:
    """QLIKE loss: realised/forecast - log(realised/forecast) - 1.

    Preferred over MSE for variance forecasts: it penalises under-prediction more,
    which is the asymmetry that actually hurts a risk manager.
    """
    f = max(forecast, eps)
    r = max(realised, eps)
    return float(r / f - np.log(r / f) - 1.0)


def frobenius(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b, ord="fro") / (np.linalg.norm(b, ord="fro") + 1e-12))


def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray, h: int = 1) -> dict[str, float]:
    """Diebold-Mariano test on the loss differential d = a - b, with HAC variance.

        DM = mean(d) / sqrt(HAC_var(d)/n)

    A negative DM means model a has the lower loss. HAC (Bartlett, h-1 lags)
    because forecast losses are serially correlated when periods overlap.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    d = d[np.isfinite(d)]
    n = d.size
    if n < 10:
        return {"dm": float("nan"), "mean_diff": float("nan"), "n": float(n)}
    mean = d.mean()
    gamma0 = np.var(d, ddof=0)
    var = gamma0
    for lag in range(1, max(h, 1)):
        if lag >= n:
            break
        w = 1.0 - lag / h
        g = np.cov(d[lag:], d[:-lag], ddof=0)[0, 1]
        var += 2 * w * g
    se = np.sqrt(max(var, 1e-16) / n)
    dm = float(mean / se)
    return {"dm": dm, "mean_diff": float(mean), "n": float(n), "significant": bool(abs(dm) > 1.96)}
