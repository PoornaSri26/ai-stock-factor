# Pre-registration — Secret AI Stock Finder

**Registered at (UTC):** `2026-11-24T16:43:09Z`
**Frozen bar hash:** see `PREREGISTRATION.sha256`

## The question

Did a distinct AI factor appear after 2023, and does knowing about it improve
out-of-sample risk forecasts?

The second half is the contribution. "A new eigenvalue appeared" is the least
novel part of this project and is treated as a hypothesis, not a finding.

## Data (verified Nov 2026)

| Item | Choice | Note |
|---|---|---|
| Window | 2018-01-01 → today | short windows cannot show a factor being *born* |
| Universe | S&P 500 constituents, point-in-time if available | `fja05680/sp500` for membership history |
| Prices | Stooq (free bulk CSV) primary; yfinance fallback | Tiingo's free tier has a symbol cap — check it before relying on it |
| Factors | Ken French daily 4-factor + 49 industry portfolios | free, direct download |
| Returns | adjusted close, log returns, winsorised at 5 sd | state the winsorisation |

**Survivorship bias:** if point-in-time membership is unavailable, the README says
so in one sentence and the result is labelled "survivorship-biased". It is not
silently ignored.

## Frozen quantities

| Quantity | Value |
|---|---|
| Correlation input | volatility-normalised returns (EWMA or GARCH(1,1)) |
| Bulk fit | MP `sigma^2` by KS distance to the empirical bulk |
| Edge test | Marchenko-Pastur edge **and** Tracy-Widom fluctuation on `lambda_1` |
| Nulls | independent column shuffle; block shuffle of vol-normalised returns |
| Known factors | market, size, value, momentum + 49 industry dummies |
| Rolling window | 250 trading days, step 10 |
| Eigenvector matching | Hungarian algorithm on absolute cosine overlap |
| AI basket | NVDA, AVGO, AMD, TSM-linked, MSFT/GOOGL/AMZN/META, power + datacentre names |
| Covariance estimators | sample, Ledoit-Wolf, RMT clipping, factor-structured (market + AI + diagonal) |
| Portfolio | minimum variance, long-only, monthly rebalance |
| Losses | realised variance of the min-var portfolio; QLIKE; Frobenius |
| Significance | Diebold-Mariano with Newey-West HAC errors |

## Pass / fail bar

The AI factor claim is **supported** only if all three hold:

1. **Persistence:** the eigenvector's cosine similarity with the hand-built AI
   basket exceeds **0.5** in at least **60%** of rolling windows after 2023-01,
   and the eigenvalue exceeds the Tracy-Widom 95% threshold in those windows.
2. **Not just semis:** the result survives controlling for the 49 industry
   portfolios — i.e. it appears in the residual correlation matrix, not only in
   raw returns.
3. **A change-point:** a single-break test on the eigenvalue series rejects
   constancy at 5%.

And, separately, the risk-forecast claim is **supported** only if the
factor-structured estimator's QLIKE improvement over Ledoit-Wolf has a
Diebold-Mariano statistic beyond ±1.96, out of sample, with a positive
percentage improvement and a CI.

If the factor exists but does not improve forecasts, the report says exactly that:
"a factor was born; it did not help".

## What would make this fail outright

- Using raw returns without industry controls and calling the result "AI".
- Computing the correlation matrix on the full sample and reporting eigenvalues
  as if they were predictive.
- Any positive result that does not survive the independent-shuffle null.
- Reporting `Q = T/N` as if large: with 500 names and 2500 days, `Q ≈ 5`, and the
  noise band is wide. Say the number.

## Not claimed

That the article's 2024-2025 window shows a factor being born. Two years of a
five-name regime is a sector rotation, and the industry control is what
distinguishes the two.
