"""Preprocessing: log returns, winsorising, volatility normalisation.

The volatility choice changes the null, so it is a config constant and it is
stated in the README:

* **raw log returns** — fat tails and clustering leak into the correlation
  matrix, and the MP band no longer describes noise.
* **EWMA-normalised** (default) — divide each stock by its own EWMA volatility.
  Removes most of the clustering with two parameters, and keeps the cross-section
  comparable.
* **GARCH(1,1)-normalised** — better, slower, and it changes the effective sample
  (one fitted volatility per stock). Optional.

After normalisation the matrix is standardised so the diagonal is exactly 1; the
correlation matrix, not the covariance, is what the eigenvalue analysis uses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import EWMA_LAMBDA, WINSOR_SD


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns, with the first row dropped rather than zero-filled."""
    px = prices.astype(float).where(prices > 0)
    r = np.log(px).diff()
    return r.iloc[1:]


def winsorise(returns: pd.DataFrame, sd: float = WINSOR_SD) -> pd.DataFrame:
    """Clip each column at ±``sd`` cross-sectional standard deviations.

    Per column, computed on the *expanding* history available at the time, so a
    later regime change cannot retroactively clip an early observation. The
    expanding version is the default because the alternative leaks.
    """
    out = returns.copy()
    for col in returns.columns:
        s = returns[col]
        mean = s.expanding(min_periods=60).mean()
        std = s.expanding(min_periods=60).std()
        out[col] = s.clip(mean - sd * std, mean + sd * std)
    return out


def ewma_vol(returns: pd.Series, lam: float = EWMA_LAMBDA) -> pd.Series:
    """RiskMetrics-style EWMA volatility (zero mean, variance recursion)."""
    var = returns.pow(2).ewm(alpha=1 - lam, adjust=False, min_periods=20).mean()
    return np.sqrt(var)


def volatility_normalise(returns: pd.DataFrame, lam: float = EWMA_LAMBDA) -> pd.DataFrame:
    """Divide each stock by its own lagged EWMA volatility.

    The lag matters: using the contemporaneous volatility would put the day's own
    move in the denominator and mechanically dampen exactly the large moves the
    analysis is about.
    """
    out = {}
    for col in returns.columns:
        vol = ewma_vol(returns[col], lam=lam).shift(1)
        out[col] = returns[col] / vol.replace(0, np.nan)
    return pd.DataFrame(out).replace([np.inf, -np.inf], np.nan)


def standardise(returns: pd.DataFrame, min_obs: int = 250) -> pd.DataFrame:
    """Full-sample standardisation, for the correlation matrix only.

    This is intentionally *not* the normalisation used for the null panels: a
    full-sample z-score would leak the future into the eigenvalues. It is fine
    here because the correlation matrix is a unit-free summary, but the rolling
    analysis in `rolling.py` recomputes it inside each window.
    """
    z = (returns - returns.mean()) / returns.std(ddof=0).replace(0, np.nan)
    return z.loc[:, returns.notna().sum() >= min_obs].replace([np.inf, -np.inf], np.nan)


def prepare(prices: pd.DataFrame, winsor: bool = True, vol_normalise: bool = True) -> pd.DataFrame:
    """The one pipeline: prices -> analysis-ready returns."""
    r = log_returns(prices)
    if winsor:
        r = winsorise(r)
    if vol_normalise:
        r = volatility_normalise(r)
    r = r.dropna(axis=1, how="all")
    print(
        f"  prepared {r.shape[1]} series x {r.shape[0]} days "
        f"({r.index.min().date()} -> {r.index.max().date()}); "
        f"Q = T/N = {r.shape[0] / max(r.shape[1], 1):.1f}"
    )
    return r


def realised_cov(returns: pd.DataFrame, window: int = 21) -> np.ndarray:
    """Realised covariance over the next ``window`` days — the evaluation target."""
    sub = returns.tail(window).dropna(axis=1, how="any")
    return np.cov(sub.to_numpy(dtype=float), rowvar=False, ddof=1)
