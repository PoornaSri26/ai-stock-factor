# SECURITY — Secret AI Stock Finder

No accounts, no user data, no keys. The security surface is **data-source terms**,
**research integrity**, and **not overclaiming**.

## 1. Secrets

| Secret | Needed | Notes |
|---|---|---|
| any API key | **no** | Stooq, Ken French and the membership CSV are unauthenticated |
| Tiingo key (optional) | if you use Tiingo instead of Stooq | `.env`, gitignored |
| brokerage credentials | **never** | this repo does not trade |

`.gitignore` covers `.env*` with `!.env.example`.

## 2. Data-source terms

| Source | Constraint |
|---|---|
| Stooq | free daily CSVs; 1 req/s; do not redistribute the bulk data |
| Ken French library | free for research; cite it in the README and in captions |
| yfinance (fallback) | read its terms; it is a convenience wrapper, not a licensed feed |
| Tiingo | free tier has a symbol cap — check it before designing around it |
| `fja05680/sp500` | community data; check the last update date and say when it was current |

No scraping of provider UIs. No headless-browser data extraction.

## 3. Integrity controls

| Control | Prevents | Where |
|---|---|---|
| Pre-registration + hash | moving the bar, re-picking the basket | `PREREGISTRATION.md` |
| Basket declared first | reverse-engineering the factor | `factors.ai_basket` |
| Industry control as a gate | calling the semiconductor sector "AI" | exit 1 without FF files |
| Empirical nulls | counting noise as a factor | `nulls.py` |
| Fixed walk-forward | choosing the best window | `config.EST_WINDOW` |
| All four estimators reported | publishing only the winner | `evaluate.summarise` |
| `n_periods` in every table | a 8-month "result" | schema |

## 4. Claim integrity

| Slip | Why it matters | Detection |
|---|---|---|
| Reporting raw-return eigenvalues | that is the market mode plus semis | residual spectrum required |
| `observed − 0` factors | noise produces 1-3 at these sizes | `excess_over_null` |
| Quoting a QLIKE improvement without DM | differences of 1% are noise | `dm_tests.csv` |
| Quoting a DM statistic over 8 periods | powerless | `n < 12` returns NaN |
| Presenting one rolling window as "the factor" | it may be a rank swap | persistence share required |
| Using a paid vendor's data without a licence | legal exposure | only free sources in `requirements`/scripts |

## 5. Bias disclosures that must appear in the README

- survivorship bias (or its absence, if PIT membership is used),
- price-only returns (no dividends),
- the volatility normalisation choice,
- `Q = T/N` and the resulting width of the noise band,
- the estimation/evaluation window lengths and the number of periods.

## 6. Pre-publication checklist

- [ ] `sigma2`, the edge, and `nulls.block.count_p95` are in `study.json`.
- [ ] `outputs/cov_comparison.csv` has `n_periods` for every estimator.
- [ ] Any QLIKE claim is paired with a DM statistic.
- [ ] The three factor conditions are marked pass/fail individually.
- [ ] No `data/` or `outputs/` content in git.
