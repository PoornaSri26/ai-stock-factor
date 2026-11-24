# APP_FLOW — Secret AI Stock Finder

No UI. Stages in order, with two gates that refuse to continue.

## 1. Stage list

| Stage | Command | Writes |
|---|---|---|
| 0. Register | `make stamp` | `PREREGISTRATION.sha256` |
| 1. Factors | `python scripts/fetch_ff.py` | `data/raw/ff/*.zip` |
| 2. Prices | `python scripts/fetch_prices.py --tickers tickers.txt` | `data/raw/prices/*.csv` |
| 3. Membership (optional) | manual download | `data/raw/universe/sp500_history.csv` |
| 4. Study | `make study` | `outputs/study.json`, `cov_comparison.csv`, `dm_tests.csv` |
| 5. Tests | `make test` | — |

## 2. Main journey

```
stamp → ff → prices → [membership] → study → write-up
```

## 3. Per-stage detail

### Stage 1 — Factors
- **Sees:** one line per zip, sizes, then a citation reminder.
- **Failure:** HTTP error → prints the manual URL and exits 1.

### Stage 2 — Prices
- **Sees:** one line per ticker.
- **Delisted state:** `FAIL <T> ... unexpected payload (delisted or wrong suffix?)`
  — expected for a historical universe; the note says so and the return code is 1
  so the caller notices.
- **Idempotent:** existing files skipped, so a partial run resumes.

### Stage 3 — Membership (manual)
- **Absent:** `data.load_membership()` returns `None`; the study still runs and
  the README must say "survivorship-biased".

### Stage 4 — Study
- **Gate 1:** fewer than 20 series → exit 1.
- **Gate 2:** Ken French files missing → exit 1 with `Refusing to call anything
  'AI' without industry controls`.
- **Sees, in order:** universe shape and `Q`, raw spectrum, nulls, residuals,
  rolling tracks, covariance table, DM tests, bootstrap CI.
- **Degenerate state:** no evaluation periods → a message naming
  `EST_WINDOW`/`FORWARD_DAYS` against the sample length.
- **Per-estimator failure:** caught, printed with the date, and the run continues
  — one bad estimator must not destroy the comparison.

## 4. States

| State | Meaning | Where |
|---|---|---|
| Prepared | returns built, `Q` printed | study stdout |
| Fit | `sigma^2` and edge computed | `study.json` |
| Tracked | rolling factors with persistence | `study.json.tracks` |
| Compared | per-period losses | `cov_comparison.csv` |
| Refused | missing factors / too few names | stderr + exit 1 |

## 5. Edge cases

| Case | Behaviour |
|---|---|
| Stock listed mid-sample | kept; NaNs stay; `min_coverage` is measured over its live span |
| Ticker delisted | fetch fails loudly; note it, do not silently drop |
| `T/N` very small | a printed note; conclusions are conditional on the sample |
| Constant column | dropped by `standardise` |
| All-zero industry column | `lstsq` handles it; the beta is ~0 and reported |
| Estimator produces non-finite matrix | skipped for that period with a message |
| Fewer than 12 periods | DM and bootstrap return NaN rather than a fake p-value |

## 6. Access rules

| Artefact | Access |
|---|---|
| `data/raw/` | any stage; written by fetch scripts only |
| `outputs/` | written by the study script only |
| `tickers.txt` | human-curated; the universe is a research decision |
