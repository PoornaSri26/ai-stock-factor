# CODE_STYLE — Secret AI Stock Finder

## 1. Naming

| Thing | Convention | Example |
|---|---|---|
| Modules | `snake_case` | `mp.py`, `nulls.py` |
| Functions | `snake_case` verb | `fit_sigma2`, `walk_forward` |
| Classes | `PascalCase` | `BulkFit`, `TrackedFactor`, `ForecastScore` |
| Constants | `UPPER_SNAKE_CASE` | `EST_WINDOW`, `WINSOR_SD` |
| Statistical symbols | as published | `sigma2`, `lambda1`, `q`, `ipr` |

Use `sigma2` and `lambda1` rather than `s2`/`l1`: they are what the formulas say,
and a reader matching code to a paper needs them.

## 2. Formatting

- `ruff format` (100 cols), `ruff check`.
- `from __future__ import annotations` everywhere.
- `sklearn` imported inside `cov.ledoit_wolf` so the rest of the package imports
  without it (the tests that matter do not need shrinkage).
- No module-level I/O.

## 3. Types

- Annotated public signatures. `np.ndarray` for matrices, `pd.DataFrame` for
  panels.
- Frozen dataclasses for records: `BulkFit`, `ForecastScore`, `NullSpec`.
- Mutable accumulator only where it must be: `TrackedFactor` (it grows).

## 4. Structure

- `mp.py` has no window logic; `rolling.py` has no eigenvalue formula. The
  spectrum maths lives in one file so it can be checked against a paper in one
  sitting.
- `preprocess.py` is the only place that touches price → return transformation.
- `scripts/run_study.py` prints and writes only.
- Functions ≤ 40 lines; `walk_forward` is the longest and is a linear loop.

## 5. Docstrings: the formula rule

Every statistic states its equation, symbols and units:

```python
def fit_sigma2(eigs, q, trim_frac=0.10):
    """Fit sigma^2 so the MP CDF matches the trimmed empirical bulk.

    Excludes the top `trim_frac` eigenvalues: those are the candidate signal, and
    including them biases sigma^2 upward -- the mistake that makes a real factor
    look like noise.
    """
```

The `glft`-style caveat applies here too: if a constant comes from the literature
rather than from the code (TW quantiles), say so and cite where it came from.

## 6. Errors

- A missing control is a hard gate: `run_study.py` exits 1 without Ken French.
- A single estimator failing is caught and printed with the date; it does not
  abort the comparison.
- Too few periods → NaN and a message, never a p-value from 5 observations.

## 7. Honesty conventions

- `excess_over_null` is computed as `observed − null p95`, not `observed − 0`.
- `None` means "not available"; never coerce to 0.
- `bootstrap_improvement` returns NaN with the period count when `n < 12`.

## 8. Randomness

`np.random.default_rng((SEED, path, family))` for nulls; `default_rng(7)` for the
bootstrap and the change-point permutation.

## 9. Git

`feat:` `fix:` `docs:` `test:` `data:` `chore:`.
Changing `tickers.txt` is a `data:` commit with a reason in the body — the
universe is part of the experiment.
`Freeze pre-registration` precedes the first `src/` commit.
