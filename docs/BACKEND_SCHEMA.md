# BACKEND_SCHEMA — Secret AI Stock Finder

No database. On-disk contract.

## 1. `data/raw/prices/<TICKER>.csv`

Stooq daily CSV, kept verbatim:

| Column | Type |
|---|---|
| `Date` | YYYY-MM-DD |
| `Open`, `High`, `Low`, `Close` | float |
| `Volume` | float |

**Key:** `Date`. **Note:** Stooq's `Close` is split-adjusted; it is *not* a total
return. Dividend adjustment is not applied, and that is stated — a price-only
return understates total return by roughly the dividend yield, evenly across names,
which matters for levels but not for a correlation study.

## 2. `data/raw/ff/*.zip`

Ken French zips, read with `skiprows=3`, values in **percent** (divided by 100 in
`data.load_ff`), footer rows dropped.

| File | Columns |
|---|---|
| `F-F_Research_Data_Factors_daily_CSV.zip` | `Mkt-RF, SMB, HML, RF` |
| `F-F_Momentum_Factor_daily_CSV.zip` | `MOM` (first column renamed) |
| `49_Industry_Portfolios_daily_CSV.zip` | 49 industry returns |

## 3. `data/raw/universe/sp500_history.csv` (optional)

| Column | Type | Meaning |
|---|---|---|
| `date` | date | effective date of a change |
| `tickers` | string | comma-separated membership **after** the change |

`data.members_on(history, when)` returns the most recent set at or before `when`.

## 4. In-memory contract: normalised returns frame

Index: trading days. Columns: tickers. Values: log return / lagged EWMA vol,
winsorised. Every downstream module assumes:

- no `inf` (replaced with NaN),
- `NaN` only where the stock did not trade,
- columns sorted, unique.

`preprocess.prepare` guarantees these; nothing else may construct the frame.

## 5. `outputs/study.json`

| Field | Meaning |
|---|---|
| `universe`, `shape` | tickers and (T, N) |
| `raw_spectrum` | `lambda1`, `lambda1_share`, `n_above_edge`, `sigma2`, `edge`, `ks`, `q`, `T`, `N`, `top5_share`, `spacing_1_2` |
| `nulls.{independent,block}` | `count_mean`, `count_p95`, `count_max`, `lambda1_mean`, `lambda1_p95` |
| `excess_over_null` | `observed_above_edge − null.count_p95` |
| `residual_spectrum` | same fields after industry controls |
| `tracks` | per-track `mean_cos`, `share_matching`, `mean_ipr`, `n_windows`, `break_p`, `break_index` |
| `persistence_share` | `share_matching` for the best-matching track |
| `covariance.table` | per-estimator QLIKE, realised var, Frobenius, improvements |
| `covariance.dm` | DM statistics vs the bar |
| `covariance.bootstrap` | `improvement_pct`, `ci_lo`, `ci_hi`, `n` |

**Invariant:** `excess_over_null` is never reported without `nulls.block.count_p95`
in the same document.

## 6. `outputs/cov_comparison.csv`

`estimator, qlike, realised_var, frobenius, max_weight, n_periods,
qlike_improvement_pct, frob_improvement_pct`. Sorted by QLIKE.

## 7. `outputs/dm_tests.csv`

`estimator, vs, dm_stat, mean_qlike_diff, n, significant, better`. A negative
`dm_stat` means the estimator has the lower loss.

## 8. `outputs/industry_betas.csv`

Per-stock `alpha` plus the factor/industry betas from `residualise`. Useful for the
sanity check "is the high-loading name just a semiconductor?".

## 9. Access rules

| Path | Read | Write |
|---|---|---|
| `data/raw/prices/` | any stage | `fetch_prices.py` |
| `data/raw/ff/` | any stage | `fetch_ff.py` |
| `data/raw/universe/` | any stage | human |
| `outputs/` | anyone | `run_study.py` |
