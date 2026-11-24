# PRD — Secret AI Stock Finder

## 1. Overview

Test whether a distinguishable AI factor appeared in US equities after 2023, and
— the part that matters — whether including it improves out-of-sample covariance
forecasts for a minimum-variance portfolio.

## 2. Problem statement

Two weak claims circulate:

- "AI created a new factor." Usually shown as a second eigenvalue growing in raw
  returns, with no industry control, no empirical null, and no test that it
  persists.
- "Factor models don't help risk forecasting." Usually asserted by someone who
  never compared a factor-structured estimator with Ledoit-Wolf out of sample.

This project sets both up so either can be falsified: a proper noise null, industry
residualisation, a persistence test, and a monthly walk-forward QLIKE comparison
with Diebold-Mariano.

## 3. Goals (measurable)

| # | Goal | Measure |
|---|---|---|
| G1 | A null that reflects the sample | MP `sigma^2` fitted to the bulk; Tracy-Widom edge; two simulated nulls |
| G2 | Not just semis | result computed on residuals after 4 factors + 49 industries |
| G3 | A date, not an impression | single-break test on the eigenvalue series with a permutation p |
| G4 | Persistence, not one window | cosine with the pre-declared basket in ≥ 60% of post-2023 windows |
| G5 | The contribution | walk-forward QLIKE, realised variance, Frobenius, DM tests |
| G6 | Honest bias statement | survivorship bias stated if point-in-time membership is absent |

## 4. Target users

- The author, as a quant-risk portfolio project.
- A reader who wants a template for "is this eigenvalue real" that is not
  hand-waving.

## 5. Features and priorities

| Priority | Feature |
|---|---|
| Must | Free data: Stooq prices, Ken French factors, optional PIT membership |
| Must | Log returns, expanding winsorise, EWMA volatility normalisation |
| Must | MP density/CDF, bulk `sigma^2` fit, Tracy-Widom threshold |
| Must | Two empirical nulls with eigenvalue counts above the edge |
| Must | Industry residualisation before any factor claim |
| Must | Rolling eigen-tracking with Hungarian matching, persistence, change-point |
| Must | Four covariance estimators and a walk-forward DM comparison |
| Should | Bootstrap CI on the QLIKE improvement, resampling periods |
| Could | Long-only vs unconstrained min-variance as a side-note |
| Won't | Signals, alpha, backtesting a trading strategy |
| Won't | Claims about the article's 2024-2025 window showing a birth |
| Won't | Any paid data vendor |

## 6. User stories

**US-1** — *As a reviewer, I want the noise level at this T and N.*
Acceptance: `study.json` contains `nulls.block.count_p95` and
`excess_over_null`; the README quotes both.

**US-2** — *As a sceptic, I want the industry control to be mandatory.*
Acceptance: `run_study.py` exits 1 if the Ken French files are missing, rather
than skipping the residualisation.

**US-3** — *As a risk manager, I want to know if this improves forecasts.*
Acceptance: `outputs/cov_comparison.csv` and `dm_tests.csv` exist before any
factor claim is written.

**US-4** — *As a reader, I want to know if the universe is survivorship-biased.*
Acceptance: the README states it in one sentence, either way.

## 7. Success metrics

- Factor claim supported or rejected, with the three conditions each marked.
- Forecast claim supported or rejected, with DM statistic and CI.
- Either way: "a factor was born; it did not help" is an acceptable headline.

## 8. Out of scope

Alpha signals, transaction costs, portfolio construction beyond min-variance,
intraday data, options, and any statement about individual company prospects.
