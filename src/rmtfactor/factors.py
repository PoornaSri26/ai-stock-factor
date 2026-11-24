"""Strip the known factors before calling anything "new".

Without this step, "a new AI factor" is very often the semiconductor sector. The
controls are the Fama-French factors plus industry portfolios, and the test is
whether the candidate eigenvector survives in the *residual* correlation matrix.

Procedure
---------
For each stock i, regress its excess return on

    [1, MKT, SMB, HML, MOM, industry dummies]

and keep the residual. Then rebuild the correlation matrix from residuals and
re-run the eigenvalue analysis. Anything that disappears was a known factor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_design(
    ff: pd.DataFrame, industries: pd.DataFrame, columns_ind: list[str] | None = None
) -> pd.DataFrame:
    """Design matrix of known factors, aligned on the date index.

    ``ff`` needs Mkt-RF, SMB, HML, MOM (all in percent — divide by 100).
    ``industries`` is Ken French's 49-industry daily returns.
    """
    cols = columns_ind or list(industries.columns)
    x = pd.concat([ff[["Mkt-RF", "SMB", "HML", "MOM"]], industries[cols]], axis=1)
    x = x / 100.0 if x["Mkt-RF"].abs().max() > 1.0 else x
    return x.dropna()


def residualise(
    returns: pd.DataFrame,
    design: pd.DataFrame,
    industry_of: dict[str, str] | None = None,
    min_obs: int = 250,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Residual returns after known factors; plus each stock's industry loadings.

    If ``industry_of`` is given, each stock is regressed on the four factors plus
    its *own* industry dummy column (a stock's industry does not change daily).
    Otherwise all industry columns are used, which is a stricter but noisier
    control.
    """
    idx = returns.index.intersection(design.index)
    r = returns.loc[idx]
    x_all = design.loc[idx]
    resid = pd.DataFrame(index=idx, columns=r.columns, dtype=float)
    betas = {}

    for col in r.columns:
        y = r[col]
        ok = y.notna()
        if ok.sum() < min_obs:
            continue
        if industry_of and col in industry_of and industry_of[col] in x_all.columns:
            use = ["Mkt-RF", "SMB", "HML", "MOM", industry_of[col]]
        else:
            use = list(x_all.columns)
        x = np.column_stack([np.ones(ok.sum()), x_all.loc[ok, use].to_numpy(dtype=float)])
        yy = y[ok].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(x, yy, rcond=None)
        resid.loc[ok, col] = yy - x @ beta
        betas[col] = dict(zip(["alpha", *use], beta))

    return resid.dropna(axis=1, how="any"), pd.DataFrame(betas).T


def correlation(returns: pd.DataFrame) -> np.ndarray:
    c = np.corrcoef(returns.to_numpy(dtype=float), rowvar=False)
    c = np.nan_to_num(c, nan=0.0)
    np.fill_diagonal(c, 1.0)
    return np.clip(c, -1.0, 1.0)


def ai_basket(tickers: list[str], groups: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    """A hand-built AI basket, declared before looking at any eigenvector.

    Declared in the pre-registration, which is the only thing that stops the
    basket being reverse-engineered from the result.
    """
    return groups or {
        "gpu": ["NVDA", "AMD", "AVGO", "MU"],
        "foundry": ["TSM", "ASML", "AMAT", "LRCX", "KLAC"],
        "hyperscaler": ["MSFT", "GOOGL", "AMZN", "META"],
        "power_dc": ["VRT", "ETN", "CEG", "NEE", "SMCI", "ANET"],
    }


def basket_vector(tickers: list[str], basket: dict[str, list[str]]) -> np.ndarray:
    """Equal-weight +1 for basket members, 0 otherwise, L2-normalised."""
    members = {t for group in basket.values() for t in group}
    v = np.array([1.0 if t in members else 0.0 for t in tickers])
    if v.sum() == 0:
        raise ValueError("basket has no overlap with the universe; check tickers")
    return v / np.linalg.norm(v)


def cosine_overlap(v1: np.ndarray, v2: np.ndarray) -> float:
    a, b = np.asarray(v1, float), np.asarray(v2, float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(abs(a @ b) / denom) if denom > 0 else 0.0


def top_loadings(tickers: list[str], vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
    """Highest absolute loadings — including the *unlabelled* names.

    The unlabelled high-loading stocks are the "hidden AI stock" result, and are
    also the claim that most needs a sanity check (see `rolling.persistence`).
    """
    order = np.argsort(-np.abs(vector))[:k]
    return [(tickers[i], float(vector[i])) for i in order]
