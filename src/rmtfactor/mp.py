r"""Random-matrix tools: Marchenko-Pastur bulk, Tracy-Widom edge, null counts.

Setting. With ``T`` observations of ``N`` standardised series, the sample
correlation matrix has eigenvalues that, for pure noise, live in the
Marchenko-Pastur band

    a = sigma^2 (1 - sqrt(q))^2 ,  b = sigma^2 (1 + sqrt(q))^2 ,  q = N/T <= 1

**Fit sigma^2 to the bulk, not to 1.** The market mode inflates the largest
eigenvalue by a factor of ten or more; forcing sigma^2 = 1 pushes the whole band
up and hides real structure. `fit_sigma2` matches the *bulk* CDF by minimising a
Kolmogorov-Smirnov distance, which uses the middle of the spectrum where the MP
law actually holds.

**The edge is an asymptotic statement.** At T = 250 and N = 100 the sharp
threshold is not sharp, so significance is judged with Tracy-Widom fluctuations
of the largest eigenvalue (Johnstone 2001, real case):

    (lambda_1 / sigma^2 - mu) / sd  ->  TW_1
    mu = (sqrt(T-1) + sqrt(N))^2
    sd = (sqrt(T-1) + sqrt(N)) * (1/sqrt(T-1) + 1/sqrt(N))^(1/3)

with lambda_1 of the *unscaled* T x T-normalised covariance. `tw_threshold`
returns the 95% point in the same units as the eigenvalues of `S = X'X / T`.

Quantiles of TW_1 used here: 0.4501 (90%), 0.9793 (95%), 2.0234 (99%). They are
constants from the literature, not fitted here — and 2.02 at 99% is only ~2 sd
above the mean, which is why "significant at the edge" needs care at small T.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import integrate, optimize

TW_QUANTILES = {0.90: 0.4501, 0.95: 0.9793, 0.99: 2.0234}


def mp_bounds(sigma2: float, q: float) -> tuple[float, float]:
    r = np.sqrt(min(q, 1.0))
    return sigma2 * (1 - r) ** 2, sigma2 * (1 + r) ** 2


def mp_pdf(x: np.ndarray, sigma2: float, q: float) -> np.ndarray:
    """MP density for the eigenvalues of a covariance matrix (q = N/T <= 1)."""
    x = np.asarray(x, dtype=float)
    a, b = mp_bounds(sigma2, q)
    out = np.zeros_like(x)
    inside = (x > a) & (x < b)
    out[inside] = np.sqrt((b - x[inside]) * (x[inside] - a)) / (
        2 * np.pi * q * sigma2 * x[inside]
    )
    return out


def mp_cdf(x: np.ndarray, sigma2: float, q: float) -> np.ndarray:
    """Numerical CDF (the closed form is a messy arc-tangent expression)."""
    a, _ = mp_bounds(sigma2, q)
    xs = np.atleast_1d(np.asarray(x, dtype=float))
    out = np.empty_like(xs)
    for i, v in enumerate(xs):
        lo, hi = max(a, 1e-12), v
        if hi <= lo:
            out[i] = 0.0
        else:
            out[i] = integrate.quad(lambda t: float(mp_pdf(np.array([t]), sigma2, q)[0]), lo, hi, limit=100)[0]
    return out


@dataclass(frozen=True)
class BulkFit:
    sigma2: float
    q: float
    ks: float
    n_bulk: int

    @property
    def edge(self) -> float:
        return mp_bounds(self.sigma2, self.q)[1]


def fit_sigma2(eigs: np.ndarray, q: float, trim_frac: float = 0.10) -> BulkFit:
    """Fit sigma^2 so the MP CDF matches the trimmed empirical bulk.

    The top ``trim_frac`` of eigenvalues are excluded from the fit: those are the
    candidate signal (market mode + factors), and including them biases sigma^2
    upward — which is exactly the mistake that makes a real factor look like noise.
    """
    e = np.sort(np.asarray(eigs, dtype=float))
    keep = e[: max(int(len(e) * (1 - trim_frac)), 5)]
    emp_cdf = (np.arange(1, keep.size + 1) - 0.5) / keep.size

    def ks(s2: float) -> float:
        return float(np.max(np.abs(mp_cdf(keep, s2, q) - emp_cdf)))

    lo = max(keep.mean() * 0.1, 1e-6)
    hi = keep.mean() * 3.0
    res = optimize.minimize_scalar(lambda s: ks(s), bounds=(lo, hi), method="bounded")
    return BulkFit(sigma2=float(res.x), q=float(q), ks=float(res.fun), n_bulk=int(keep.size))


def tw_threshold(T: int, N: int, sigma2: float, level: float = 0.95) -> float:
    """Tracy-Widom-corrected upper edge, in units of eigenvalues of S = X'X/T."""
    tw = TW_QUANTILES.get(level, TW_QUANTILES[0.95])
    st, sn = np.sqrt(T - 1), np.sqrt(N)
    mu = (st + sn) ** 2
    sd = (st + sn) * (1 / st + 1 / sn) ** (1 / 3)
    return float(sigma2 / T * (mu + tw * sd))


def count_above(eigs: np.ndarray, threshold: float) -> int:
    return int(np.sum(np.asarray(eigs) > threshold))


def spectrum(eigs: np.ndarray, threshold: float) -> dict[str, float]:
    e = np.sort(np.asarray(eigs, dtype=float))[::-1]
    total = e.sum()
    return {
        "lambda1": float(e[0]),
        "lambda1_share": float(e[0] / total),
        "n_above_edge": count_above(e, threshold),
        "top5_share": float(e[:5].sum() / total),
        "spacing_1_2": float(e[0] - e[1]),
    }


def inverse_participation_ratio(vector: np.ndarray) -> float:
    """sum(v^4) for a unit vector: 1/N when spread evenly, ~1 when concentrated.

    This is the *inverse* of the usual participation ratio, so a larger number
    means fewer names drive the factor. Say which convention you quote.
    """
    v = np.asarray(vector, dtype=float)
    v = v / (np.linalg.norm(v) + 1e-12)
    return float(np.sum(v**4))
