# AGENTS.md — Secret AI Stock Finder

## Project

Test whether a distinct AI factor appeared after 2023 in US equities, and whether
including it improves out-of-sample covariance forecasts. Python 3.11+, free data
only, no trading, no API keys.

## Commands

```bash
pip install -r requirements.txt
make stamp     # freeze + hash PREREGISTRATION.md
make data      # Ken French zips; then: python scripts/fetch_prices.py --tickers tickers.txt
make study     # spectrum -> nulls -> industry controls -> rolling -> cov comparison
make test
```

Windows without `make`: `bash reproduce.sh`.

## Documentation map

| Question | File |
|---|---|
| Scope, bar, priorities | `docs/PRD.md` |
| Data sources, Q, assumptions | `docs/TRD.md` |
| Stage order and gates | `docs/APP_FLOW.md` |
| Module boundaries, decisions | `docs/ARCHITECTURE.md` |
| File schemas, `study.json` fields | `docs/BACKEND_SCHEMA.md` |
| Spectrum/rolling/QLIKE figures | `docs/DESIGN_SYSTEM.md` |
| Naming, formula docstrings | `docs/CODE_STYLE.md` |
| Two-week plan | `docs/IMPLEMENTATION_PLAN.md` |
| Data terms, bias disclosures | `docs/SECURITY.md` |
| 21 test cases | `docs/TESTING.md` |
| **The frozen bar and basket** | `PREREGISTRATION.md` |

## Rules — Always

1. Read `docs/` first, starting with `PRD.md` and `ARCHITECTURE.md`.
2. Fit `sigma^2` to the bulk; never fix it at 1.
3. Report `observed − null p95`, never `observed − 0`.
4. Residualise on 4 factors + 49 industries before saying "AI".
5. Report all four estimators, with `n_periods`, sorted by QLIKE.
6. Any QLIKE claim comes with a Diebold-Mariano statistic.
7. `make test` passes before you say done.

## Rules — Ask first

- Changing the AI basket, the universe (`tickers.txt`), or the bar.
- Changing `EST_WINDOW`, `FORWARD_DAYS`, `ROLL_WINDOW`, or the volatility model.
- Adding a dependency or a data vendor.
- Adding an estimator to `cov.ESTIMATORS` (it changes the comparison).

## Rules — Never

- Use raw-return eigenvalues as evidence for a factor.
- Drop the industry control to get a significant result.
- Report the best window, estimator or objective only.
- Quote a QLIKE improvement without DM and `n_periods`.
- Use paid data, or a vendor whose terms forbid the use.
- Hide survivorship bias — say the words if the PIT file is absent.
- Call a `Pending` row in `docs/TESTING.md` passing.

## Definition of done

Tests pass, `study.json` contains the null distribution, the residual spectrum, the
persistence share, the change-point p and the covariance comparison with DM and
CIs — and the README states the two claims separately, including the case where
the factor exists and does not help.
