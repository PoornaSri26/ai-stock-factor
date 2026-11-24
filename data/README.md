# data/

gitignored except this file.

```
data/raw/prices/<TICKER>.csv      Stooq daily OHLCV, one file per name
data/raw/ff/*.zip                 Ken French factor + 49-industry zips
data/raw/universe/sp500_history.csv   point-in-time membership (fja05680/sp500)
```

## Sources and terms

| Source | Access | Note |
|---|---|---|
| Stooq | `stooq.com/q/d/l/?s=<t>.us&i=d` | free, no key; be polite (1 req/s) |
| Ken French library | direct zips from Dartmouth | free for research; cite it |
| `fja05680/sp500` | GitHub CSV | community-maintained; verify the last change date |
| yfinance | fallback only | read its terms before a bulk pull |
| Tiingo | not used by default | free tier has a symbol cap — check it before relying on it |

## Why `universe/` matters

Without point-in-time membership, the universe is today's index projected
backwards: every stock that survived. That biases cross-sectional dispersion down
and can manufacture (or destroy) a factor. `data.load_membership()` returns `None`
when the file is absent, and the README must then contain the words
"survivorship-biased".

## Size

500 names × 8 years of daily CSVs ≈ 60 MB. Ken French zips ≈ 5 MB.
