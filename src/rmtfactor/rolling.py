"""Rolling eigen-analysis: find the birth of a factor, and prove it persists.

Three things this module does that a single-window analysis cannot:

1. **Match eigenvectors across windows** with the Hungarian algorithm on absolute
   cosine overlap. Without matching, "the second eigenvalue grew" may be two
   different factors swapping rank.
2. **Track persistence**, not one window. A factor that exists in one 250-day
   window is noise; one that exists in 60% of windows with the same composition
   is a candidate.
3. **Change-point test** on the eigenvalue series, so "it appeared" has a date and
   a statistic rather than a visual impression.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


@dataclass
class TrackedFactor:
    """One eigenvector followed through time."""

    track_id: int
    windows: list[pd.Timestamp] = field(default_factory=list)
    eigenvalues: list[float] = field(default_factory=list)
    vectors: list[np.ndarray] = field(default_factory=list)
    basket_cos: list[float] = field(default_factory=list)
    ipr: list[float] = field(default_factory=list)

    def add(self, ts, lam, vec, cos, ipr) -> None:
        self.windows.append(ts)
        self.eigenvalues.append(float(lam))
        self.vectors.append(np.asarray(vec, dtype=float))
        self.basket_cos.append(float(cos))
        self.ipr.append(float(ipr))

    def as_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ts": self.windows,
                "eigenvalue": self.eigenvalues,
                "basket_cos": self.basket_cos,
                "ipr": self.ipr,
            }
        )


def match_vectors(prev: np.ndarray, cur: np.ndarray) -> list[tuple[int, int, float]]:
    """Hungarian assignment maximising total |cos| between two eigenvector sets.

    ``prev``, ``cur``: (k, N) matrices of eigenvectors (rows). Returns
    (prev_idx, cur_idx, cos) triples, sign-agnostic because an eigenvector is
    defined up to a sign.
    """
    overlap = np.abs(prev @ cur.T)
    rows, cols = linear_sum_assignment(-overlap)
    return [(int(r), int(c), float(overlap[r, c])) for r, c in zip(rows, cols)]


def rolling_eigen(
    returns: pd.DataFrame,
    window: int = 250,
    step: int = 10,
    n_track: int = 4,
    min_overlap: float = 0.5,
) -> dict[int, TrackedFactor]:
    """Track the top ``n_track`` eigenvectors through rolling windows.

    A track continues only while the cosine overlap with the previous window
    exceeds ``min_overlap``; otherwise a new track starts. That rule is what makes
    "the factor persisted" mean something specific.
    """
    from .factors import correlation
    from .mp import inverse_participation_ratio

    tracks: dict[int, TrackedFactor] = {}
    next_id = 0
    prev_vecs: np.ndarray | None = None
    prev_ids: list[int] = []

    for start in range(0, len(returns) - window + 1, step):
        sub = returns.iloc[start : start + window]
        c = correlation(sub)
        eigs, vecs = np.linalg.eigh(c)
        order = np.argsort(eigs)[::-1][:n_track]
        cur_vecs = vecs[:, order].T
        cur_eigs = eigs[order]
        ts = sub.index[-1]

        if prev_vecs is None:
            ids = []
            for k in range(len(order)):
                tracks[next_id] = TrackedFactor(next_id)
                tracks[next_id].add(ts, cur_eigs[k], cur_vecs[k], np.nan, inverse_participation_ratio(cur_vecs[k]))
                ids.append(next_id)
                next_id += 1
        else:
            ids = [None] * len(order)
            for pi, ci, cos in match_vectors(prev_vecs, cur_vecs):
                if cos >= min_overlap:
                    ids[ci] = prev_ids[pi]
            for k, tid in enumerate(ids):
                if tid is None:
                    tracks[next_id] = TrackedFactor(next_id)
                    ids[k] = next_id
                    next_id += 1
                tracks[ids[k]].add(
                    ts, cur_eigs[k], cur_vecs[k], np.nan, inverse_participation_ratio(cur_vecs[k])
                )
        prev_vecs, prev_ids = cur_vecs, ids
    return tracks


def score_against_basket(tracks: dict[int, TrackedFactor], basket_vec: np.ndarray) -> None:
    """Fill each track's basket cosine in place (kept separate for clarity)."""
    for track in tracks.values():
        track.basket_cos = [abs(float(v @ basket_vec)) for v in track.vectors]


def persistence(track: TrackedFactor, threshold: float = 0.5, after: str | None = None) -> dict[str, float]:
    """Share of windows where the composition matches the basket."""
    df = track.as_frame()
    if after:
        df = df[df["ts"] >= pd.Timestamp(after, tz="UTC")]
    if df.empty:
        return {"n_windows": 0.0, "share_matching": 0.0, "mean_cos": 0.0}
    cos = df["basket_cos"].dropna()
    return {
        "n_windows": float(len(df)),
        "share_matching": float((cos > threshold).mean()) if len(cos) else 0.0,
        "mean_cos": float(cos.mean()) if len(cos) else 0.0,
        "mean_ipr": float(df["ipr"].mean()),
    }


def change_point(series: np.ndarray, min_frac: float = 0.15) -> dict[str, float]:
    """Single-break test: maximise a normalised mean-shift statistic.

        S(tau) = |mean(x[:tau]) - mean(x[tau:])| / sd(x)

    This is the Andrews-Plobert-Andrews style sup statistic in its simplest
    form. The p-value is obtained by a permutation of the series order, which is
    valid because under the null the series has no temporal structure. Report the
    statistic and the permutation p; do not quote an asymptotic critical value for
    a series of 60 windows.
    """
    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 10:
        return {"stat": float("nan"), "break_index": float("nan"), "p_value": float("nan")}
    lo, hi = int(n * min_frac), int(n * (1 - min_frac))
    if hi <= lo:
        return {"stat": float("nan"), "break_index": float("nan"), "p_value": float("nan")}

    def sup_stat(v: np.ndarray) -> tuple[float, int]:
        sd = v.std(ddof=1) or 1e-12
        best, idx = 0.0, lo
        for tau in range(lo, hi):
            s = abs(v[:tau].mean() - v[tau:].mean()) / sd
            if s > best:
                best, idx = s, tau
        return best, idx

    stat, idx = sup_stat(x)
    rng = np.random.default_rng(7)
    null = np.array([sup_stat(rng.permutation(x))[0] for _ in range(1000)])
    return {
        "stat": float(stat),
        "break_index": float(idx),
        "p_value": float((null >= stat).mean()),
    }
