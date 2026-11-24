# IMPLEMENTATION_PLAN — Secret AI Stock Finder

**Objective:** a defensible answer in two weeks, weighted toward the out-of-sample
covariance comparison.
**Team:** one person.

## Phase 0 — Freeze (day 1)

| Task | Deliverable |
|---|---|
| Bar, basket, nulls, estimators | `PREREGISTRATION.md` |
| Universe decision | `tickers.txt` |
| Skeleton | `make help` |

**Gate:** the AI basket is written down *before* any eigenvector is computed.

## Phase 1 — Data (days 2-3)

| Task | Deliverable |
|---|---|
| Ken French zips | `data/raw/ff/` |
| Stooq prices for the universe | `data/raw/prices/` |
| Optional PIT membership | `data/raw/universe/` |
| Returns pipeline | `preprocess.prepare` prints `Q` |

**Gate:** `Q` is printed, and the README says whether the universe is
survivorship-biased.

## Phase 2 — Spectrum and nulls (days 4-6)

| Task | Deliverable |
|---|---|
| MP density/CDF, bulk fit | `mp.fit_sigma2` |
| Tracy-Widom edge | `mp.tw_threshold` |
| Two null worlds, edge counts | `nulls.null_edge_counts` |

**Gate:** on pure simulated noise the excess count is ≤ 0. If it is not, the edge
is too low and nothing downstream counts.

## Phase 3 — Controls (days 7-8)

| Task | Deliverable |
|---|---|
| 4-factor + industry residualisation | `factors.residualise` |
| Residual spectrum | `study.json.residual_spectrum` |
| Beta table | `outputs/industry_betas.csv` |

**Gate:** the raw-vs-residual eigenvalue counts are both reported. A factor that
exists only in raw returns is a sector, and the report says so.

## Phase 4 — Birth (days 9-10)

| Task | Deliverable |
|---|---|
| Rolling tracking with Hungarian matching | `rolling.rolling_eigen` |
| Basket cosine and persistence | `persistence` |
| Change-point with permutation p | `change_point` |

**Gate:** the three factor conditions are each marked pass/fail with numbers.

## Phase 5 — Does it help? (days 11-13)

| Task | Deliverable |
|---|---|
| Four estimators, long-only min-variance | `cov.py` |
| Monthly walk-forward | `evaluate.walk_forward` |
| DM with HAC, bootstrap CI | `dm_tests.csv`, `study.json` |

**Gate:** `n_periods` ≥ 24 for any claim; otherwise the report says the evaluation
window is too short.

## Phase 6 — Write-up (day 14)

| Task | Deliverable |
|---|---|
| Two claims reported separately | README first screen |
| Spectrum and QLIKE figures | PNGs |
| "A factor was born; it did not help" as an allowed headline | README |

## Risks

| Risk | Mitigation |
|---|---|
| Industry control absorbs the factor | that is a finding; report it as "AI is a sector bet" |
| Few rolling windows | 250-day windows over 8 years gives ~180; state the count |
| Too few evaluation periods | 500-day estimate + 21-day hold, monthly → ~150 periods; check before claiming |
| `factor_2` loses to shrinkage | expected on noise; the honest report says "forcing two factors is the problem" |
| Survivorship bias | state it, or use PIT membership |
