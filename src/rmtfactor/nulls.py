"""Null worlds for the eigenvalue test.

Two nulls, in increasing strictness:

**N1 — independent shuffle.** Permute each stock's returns independently over
time. This keeps each marginal distribution exactly (so fat tails survive) and
destroys all cross-sectional correlation. It is the right null for "is there any
correlation structure at all".

**N2 — block shuffle of volatility-normalised returns.** Shuffle blocks
(length ~20 days) of the standardised residuals. This keeps volatility clustering
and autocorrelation *within* a stock while destroying cross-stock alignment. It
is the right null for "is the correlation in excess of what serial dependence
alone produces", and it is stricter: it usually raises the count of eigenvalues
above the edge, which is the point.

Counting eigenvalues above the edge in each null path gives a *distribution* for
"how many factors noise produces at this T and N". The real count must be
compared with that distribution, not with zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .mp import count_above, fit_sigma2, tw_threshold


@dataclass(frozen=True)
class NullSpec:
    n_paths: int = 200
    block: int = 20
    seed: int = 7


def shuffle_independent(returns: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    out = np.empty_like(returns.to_numpy(dtype=float))
    for j in range(returns.shape[1]):
        out[:, j] = rng.permutation(returns.iloc[:, j].to_numpy(dtype=float))
    return pd.DataFrame(out, index=returns.index, columns=returns.columns)


def block_shuffle(returns: pd.DataFrame, rng: np.random.Generator, block: int = 20) -> pd.DataFrame:
    """Circular block bootstrap per column: keeps within-column dependence."""
    x = returns.to_numpy(dtype=float)
    t, n = x.shape
    n_blocks = int(np.ceil(t / block))
    out = np.empty_like(x)
    for j in range(n):
        starts = rng.integers(0, t, size=n_blocks)
        col = np.concatenate([np.take(x[:, j], np.arange(s, s + block), mode="wrap") for s in starts])
        out[:, j] = col[:t]
    return pd.DataFrame(out, index=returns.index, columns=returns.columns)


NULLS = {"independent": shuffle_independent, "block": block_shuffle}


def null_edge_counts(
    returns: pd.DataFrame, family: str = "independent", spec: NullSpec | None = None, level: float = 0.95
) -> dict[str, object]:
    """Distribution of (eigenvalues above the TW edge) across null paths."""
    spec = spec or NullSpec()
    fn = NULLS[family]
    t, n = returns.shape
    q = n / t
    counts, lam1 = [], []
    for i in range(spec.n_paths):
        rng = np.random.default_rng((spec.seed, i, 1 if family == "independent" else 2))
        sim = fn(returns, rng, block=spec.block) if family == "block" else fn(returns, rng)
        corr = np.corrcoef(sim.to_numpy(dtype=float), rowvar=False)
        corr = np.nan_to_num(corr, nan=0.0)
        np.fill_diagonal(corr, 1.0)
        eigs = np.linalg.eigvalsh(corr)
        fit = fit_sigma2(eigs, q)
        thr = tw_threshold(t, n, fit.sigma2, level=level)
        counts.append(count_above(eigs, thr))
        lam1.append(float(eigs[-1]))

    c = np.asarray(counts, dtype=float)
    l1 = np.asarray(lam1, dtype=float)
    return {
        "family": family,
        "n_paths": spec.n_paths,
        "count_mean": float(c.mean()),
        "count_p95": float(np.quantile(c, 0.95)),
        "count_max": float(c.max()),
        "lambda1_mean": float(l1.mean()),
        "lambda1_p95": float(np.quantile(l1, 0.95)),
    }


def excess_count(observed: int, null: dict[str, object]) -> float:
    """Observed minus the null's 95th percentile: the honest excess.

    Reporting `observed - 0` overstates by the number of factors noise produces,
    which at T=250, N=100 is routinely 1-3.
    """
    return float(observed - float(null["count_p95"]))
