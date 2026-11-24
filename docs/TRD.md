# TRD — Secret AI Stock Finder

## 1. Project overview

| Item | Value |
|---|---|
| Package | `rmtfactor` |
| Language | Python 3.11+ |
| Core | numpy, pandas, scipy, scikit-learn |
| Data | Stooq CSVs, Ken French zips, optional PIT membership CSV |
| Storage | CSV (prices), parquet-free (frames), JSON + CSV (outputs) |
| Compute | CPU; the whole study is minutes at 500 names × 2000 days |

## 2. Technical objectives

- **No leakage in the spectrum.** Volatility normalisation uses lagged EWMA;
  rolling windows recompute the correlation inside the window.
- **A null, not a threshold.** Two simulated nulls with eigenvalue counts.
- **A reproducible comparison.** Fixed windows, fixed seeds, DM with HAC errors.
- **No paid data.** Everything free and scriptable.

## 3. Functional requirements

| ID | Requirement |
|---|---|
| F1 | Read Stooq CSVs and Ken French zips (header/footer handling) |
| F2 | Point-in-time membership, with an explicit `None` when absent |
| F3 | Log returns; expanding winsorise; lagged EWMA normalisation |
| F4 | MP density, CDF, bulk `sigma^2` fit by KS distance |
| F5 | Tracy-Widom threshold for `lambda_1` |
| F6 | Independent-shuffle and block-shuffle nulls with edge counts |
| F7 | Residualise on 4 factors + industry dummies |
| F8 | Rolling eigen-tracking with Hungarian matching; persistence; change-point |
| F9 | Four covariance estimators; long-only min-variance |
| F10 | QLIKE, Frobenius, realised variance; DM with HAC errors; bootstrap CI |

## 4. Non-functional requirements

| Requirement | Target |
|---|---|
| Full study runtime | < 10 min at 500 names, 2000 days |
| Memory | < 4 GB |
| Determinism | identical outputs for the same seeds and inputs |
| Dependencies | 6 direct, all free |
| Failure mode | missing factors → exit 1 with the fetch command |

## 5. Stack and responsibility

| Layer | Technology | Responsibility |
|---|---|---|
| Ingest | pandas | CSVs and zips |
| Linear algebra | numpy | eigen, lstsq, cov |
| Optimisation | scipy | `minimize_scalar` (KS fit), `linear_sum_assignment` |
| Shrinkage | scikit-learn | Ledoit-Wolf (the bar) |
| Statistics | scipy | normal quantiles |
| Outputs | CSV + JSON | comparison tables |

**Rejected:** `statsmodels` (a HAC covariance and a DM test are 20 lines, and
hand-rolling them keeps the formula visible in the repo), `Riskfolio-Lib`
(hides the estimator being tested), any paid vendor.

## 6. Integrations

| Source | Endpoint | Auth | Note |
|---|---|---|---|
| Stooq | `stooq.com/q/d/l/?s=<t>.us&i=d` | none | 1 req/s; some delisted names 404 |
| Ken French | `mba.tuck.dartmouth.edu/.../ftp/*.zip` | none | cite the library |
| fja05680/sp500 | GitHub raw CSV | none | community-maintained; check the last change date |

## 7. Constraints and assumptions

- **Q = T/N is small.** 500 names and 2500 days gives Q ≈ 5; 100 names and 250
  days gives Q ≈ 2.5. The noise band is wide and every conclusion is conditional
  on the sample length. The number is printed.
- **Volatility normalisation changes the null.** EWMA with λ = 0.94 is the
  default; a GARCH alternative is listed as follow-up, not claimed.
- **The AI basket is a judgement**, declared in the pre-registration. A different
  basket is a different study.
- **The industry control may absorb the factor.** That is the point: if AI is a
  sector bet, it should not survive.
- **Min-variance is one objective.** Covariance improvements need not show up in
  min-variance; that limitation is stated rather than hidden by trying objectives
  until one works.
