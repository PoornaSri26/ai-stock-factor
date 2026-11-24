"""Walk-forward covariance comparison — the actual contribution of the project.

Protocol
--------
* Re-estimate monthly on a trailing window of ``EST_WINDOW`` days.
* Form long-only minimum-variance weights from each estimator.
* Hold for the next month and measure:

    - **realised variance** of the resulting portfolio (annualised),
    - **QLIKE** of the predicted portfolio variance against the realised one,
    - **Frobenius** distance to the realised covariance.

* Compare against **Ledoit-Wolf**, which is the bar, using Diebold-Mariano on the
  per-period loss differentials with HAC errors.

Why this is the contribution and the factor is not: an eigenvalue appearing is a
statement about a sample. A covariance estimator that forecasts better out of
sample is a statement about the world, and it is falsifiable on data the
estimation never saw.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import cov as covmod
from .config import EST_WINDOW, FORWARD_DAYS, REBALANCE_DAYS


@dataclass
class PeriodResult:
    ts: pd.Timestamp
    estimator: str
    predicted_var: float
    realised_var: float
    qlike: float
    frobenius: float
    n_assets: int
    max_weight: float


def _predicted_var(c: np.ndarray, w: np.ndarray) -> float:
    return float(w @ c @ w)


def walk_forward(
    returns: pd.DataFrame,
    estimators: dict[str, callable] | None = None,
    est_window: int = EST_WINDOW,
    forward: int = FORWARD_DAYS,
    step: int = REBALANCE_DAYS,
) -> pd.DataFrame:
    """One row per (period, estimator). The input to every downstream claim."""
    estimators = estimators or covmod.ESTIMATORS
    rows: list[PeriodResult] = []

    for start in range(0, len(returns) - est_window - forward + 1, step):
        train = returns.iloc[start : start + est_window]
        test = returns.iloc[start + est_window : start + est_window + forward]
        # only names quoted throughout both blocks can be compared fairly
        common = train.columns.intersection(test.columns)
        train = train[common].dropna(axis=1, how="any")
        test = test[train.columns].dropna(axis=1, how="any")
        cols = train.columns.intersection(test.columns)
        if len(cols) < 10:
            continue
        x = train[cols].to_numpy(dtype=float)
        fwd = test[cols].to_numpy(dtype=float)
        realised_c = np.cov(fwd, rowvar=False, ddof=1)
        ts = test.index[-1]

        for name, fn in estimators.items():
            try:
                c = fn(x)
            except Exception as exc:  # noqa: BLE001 - one estimator must not kill the run
                print(f"  {name} failed at {ts.date()}: {exc}")
                continue
            if not np.all(np.isfinite(c)):
                continue
            w = covmod.min_variance_weights(c)
            pv = _predicted_var(c, w)
            rv = float(np.var(fwd @ w, ddof=1))
            rows.append(
                PeriodResult(
                    ts=ts,
                    estimator=name,
                    predicted_var=pv,
                    realised_var=rv,
                    qlike=covmod.qlike(pv, rv),
                    frobenius=covmod.frobenius(c, realised_c),
                    n_assets=len(cols),
                    max_weight=float(w.max()),
                )
            )
    return pd.DataFrame([r.__dict__ for r in rows])


def summarise(results: pd.DataFrame, bar: str = "ledoit_wolf") -> pd.DataFrame:
    """Mean losses per estimator, plus a percentage improvement over the bar."""
    if results.empty:
        return pd.DataFrame()
    g = results.groupby("estimator", observed=True)
    table = pd.DataFrame(
        {
            "qlike": g["qlike"].mean(),
            "realised_var": g["realised_var"].mean(),
            "frobenius": g["frobenius"].mean(),
            "max_weight": g["max_weight"].mean(),
            "n_periods": g.size(),
        }
    )
    if bar in table.index:
        table["qlike_improvement_pct"] = (1 - table["qlike"] / table.loc[bar, "qlike"]) * 100
        table["frob_improvement_pct"] = (1 - table["frobenius"] / table.loc[bar, "frobenius"]) * 100
    return table.sort_values("qlike")


def significance(results: pd.DataFrame, bar: str = "ledoit_wolf") -> pd.DataFrame:
    """Diebold-Mariano of each estimator's QLIKE loss against the bar."""
    if results.empty:
        return pd.DataFrame()
    pivot = results.pivot_table(index="ts", columns="estimator", values="qlike")
    if bar not in pivot.columns:
        return pd.DataFrame()
    rows = []
    for name in pivot.columns:
        if name == bar:
            continue
        pair = pivot[[name, bar]].dropna()
        if len(pair) < 12:
            continue
        dm = covmod.diebold_mariano(pair[name].to_numpy(), pair[bar].to_numpy(), h=1)
        rows.append(
            {
                "estimator": name,
                "vs": bar,
                "dm_stat": dm["dm"],
                "mean_qlike_diff": dm["mean_diff"],
                "n": dm["n"],
                "significant": dm.get("significant", False),
                "better": bool(dm["mean_diff"] < 0),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_improvement(
    results: pd.DataFrame, estimator: str, bar: str = "ledoit_wolf", n_boot: int = 2000, seed: int = 7
) -> dict[str, float]:
    """CI on the percentage QLIKE improvement, resampling periods.

    Periods, not assets: the months are the independent units, and resampling
    assets would treat a 100-name cross-section as 100 pieces of evidence.
    """
    pivot = results.pivot_table(index="ts", columns="estimator", values="qlike")
    if estimator not in pivot.columns or bar not in pivot.columns:
        return {"improvement_pct": float("nan")}
    pair = pivot[[estimator, bar]].dropna()
    if len(pair) < 12:
        return {"improvement_pct": float("nan"), "n": float(len(pair))}
    base = float((1 - pair[estimator].mean() / pair[bar].mean()) * 100)
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, len(pair), len(pair))
        s = pair.iloc[idx]
        vals[i] = (1 - s[estimator].mean() / s[bar].mean()) * 100
    return {
        "improvement_pct": base,
        "ci_lo": float(np.quantile(vals, 0.025)),
        "ci_hi": float(np.quantile(vals, 0.975)),
        "n": float(len(pair)),
    }
