#!/usr/bin/env python
"""The study: spectrum, nulls, industry controls, rolling birth, forecast test.

Prints its sample size at every step. Refuses to compute the factor claim if the
industry controls are missing, because that is the difference between "a new
factor" and "the semiconductor sector".
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from rmtfactor import config, cov, data, evaluate, factors, mp, nulls, preprocess, rolling


def spectrum_block(returns: pd.DataFrame) -> dict:
    t, n = returns.shape
    q = n / t
    if q > config.Q_LIMIT_WARN:
        print(f"  NOTE: T/N = {t/n:.1f} (Q = {q:.3f}); the noise band is wide")
    c = factors.correlation(returns.dropna(axis=1, how="any"))
    eigs = np.linalg.eigvalsh(c)
    fit = mp.fit_sigma2(eigs, q, trim_frac=config.BULK_TRIM)
    thr = mp.tw_threshold(t, n, fit.sigma2, level=config.EDGE_LEVEL)
    spec = mp.spectrum(eigs, thr)
    spec.update({"sigma2": fit.sigma2, "edge": thr, "ks": fit.ks, "q": q, "T": t, "N": n})
    return spec


def main() -> int:
    config.ensure_dirs()
    print("loading prices ...")
    panel = data.price_panel()
    rets = preprocess.prepare(panel)
    rets = rets.loc[rets.index >= config.START]
    if rets.shape[1] < 20:
        print(f"only {rets.shape[1]} series; need at least 20", file=sys.stderr)
        return 1

    out: dict = {"universe": list(rets.columns), "shape": list(rets.shape)}

    # 1. raw spectrum
    print("\n[1] raw spectrum")
    raw_spec = spectrum_block(rets)
    out["raw_spectrum"] = raw_spec
    print(f"  lambda1={raw_spec['lambda1']:.2f} (share {raw_spec['lambda1_share']:.2%}), "
          f"edge={raw_spec['edge']:.3f}, above edge: {raw_spec['n_above_edge']}")

    # 2. nulls
    print("\n[2] null worlds")
    null_out = {}
    for family in ("independent", "block"):
        info = nulls.null_edge_counts(rets, family, nulls.NullSpec(n_paths=min(config.NULL_PATHS, 100), block=config.NULL_BLOCK))
        null_out[family] = info
        print(f"  {family}: mean {info['count_mean']:.2f}, p95 {info['count_p95']:.0f}, "
              f"lambda1 p95 {info['lambda1_p95']:.2f}")
    out["nulls"] = null_out
    out["excess_over_null"] = nulls.excess_count(raw_spec["n_above_edge"], null_out["block"])

    # 3. industry controls
    print("\n[3] stripping known factors")
    try:
        ff, ind = data.load_ff()
    except FileNotFoundError:
        print("  no factor files. Run scripts/fetch_ff.py. "
              "Refusing to call anything 'AI' without industry controls.", file=sys.stderr)
        return 1
    design = factors.build_design(ff, ind)
    resid, betas = factors.residualise(rets, design)
    print(f"  residuals: {resid.shape[1]} series x {resid.shape[0]} days")
    resid_spec = spectrum_block(resid)
    out["residual_spectrum"] = resid_spec
    print(f"  after controls: lambda1={resid_spec['lambda1']:.2f}, above edge: {resid_spec['n_above_edge']}")

    # 4. rolling birth + basket match
    print("\n[4] rolling eigen-tracking")
    tracks = rolling.rolling_eigen(
        resid, window=config.ROLL_WINDOW, step=config.ROLL_STEP,
        n_track=config.N_TRACK, min_overlap=config.MATCH_MIN_OVERLAP,
    )
    basket = factors.basket_vector(list(resid.columns), factors.ai_basket([]))
    rolling.score_against_basket(tracks, basket)
    scored = []
    for tid, tr in tracks.items():
        p = rolling.persistence(tr, after=config.BREAK_AFTER)
        if p["n_windows"] < 5:
            continue
        cp = rolling.change_point(np.asarray(tr.eigenvalues))
        scored.append({"track_id": tid, "mean_cos": p["mean_cos"], "share_matching": p["share_matching"],
                       "mean_ipr": p["mean_ipr"], "n_windows": p["n_windows"],
                       "break_p": cp["p_value"], "break_index": cp["break_index"]})
    tbl = pd.DataFrame(scored).sort_values("mean_cos", ascending=False) if scored else pd.DataFrame()
    out["tracks"] = tbl.to_dict(orient="records") if not tbl.empty else []
    if not tbl.empty:
        print(tbl.head(5).to_string(index=False))
        best = tbl.iloc[0]
        out["persistence_share"] = float(best["share_matching"])

    # 5. does it help risk forecasts?
    print("\n[5] walk-forward covariance comparison")
    results = evaluate.walk_forward(rets, est_window=config.EST_WINDOW,
                                    forward=config.FORWARD_DAYS, step=config.REBALANCE_DAYS)
    if results.empty:
        print("  no evaluation periods; check EST_WINDOW/FORWARD_DAYS against the sample", file=sys.stderr)
    else:
        table = evaluate.summarise(results, bar=config.BAR_ESTIMATOR)
        dm = evaluate.significance(results, bar=config.BAR_ESTIMATOR)
        boot = evaluate.bootstrap_improvement(results, "factor_2", bar=config.BAR_ESTIMATOR)
        print(table.to_string())
        if not dm.empty:
            print("\n" + dm.to_string(index=False))
        print(f"\nfactor_2 vs {config.BAR_ESTIMATOR}: {boot}")
        out["covariance"] = {
            "table": table.reset_index().to_dict(orient="records"),
            "dm": dm.to_dict(orient="records") if not dm.empty else [],
            "bootstrap": boot,
        }
        table.to_csv(config.OUT / "cov_comparison.csv")
        if not dm.empty:
            dm.to_csv(config.OUT / "dm_tests.csv", index=False)

    if "residual_spectrum" in out:
        betas.to_csv(config.OUT / "industry_betas.csv")
    (config.OUT / "study.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {config.OUT / 'study.json'}")
    print("The factor claim and the forecast claim are separate. Report them separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
