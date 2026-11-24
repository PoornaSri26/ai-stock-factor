# Secret AI Stock Finder

**Question.** Did a distinct AI factor appear after 2023 — and does knowing about
it improve out-of-sample risk forecasts?

**Bar.** The factor claim needs basket cosine > 0.5 in ≥ 60% of post-2023 rolling
windows, survival of 49-industry controls, and a change-point at 5%. The forecast
claim needs a Diebold-Mariano statistic beyond ±1.96 against Ledoit-Wolf on
QLIKE. Frozen in `PREREGISTRATION.md`.

**Result.** _Not yet run._

---

## The order of business

"The new eigenvalue" is the least novel part of this project: raw returns on US
equities produce a market mode, a sector mode, and a semiconductor mode, and an
AI-labelled basket will correlate with the third of those. So the sequence is

1. spectrum with a proper null,
2. **strip** market/size/value/momentum + 49 industries,
3. only then look for a new factor,
4. and spend most of the effort on whether any of it improves a covariance
   forecast.

Step 4 is the contribution. A factor that exists and does not improve forecasts
is a legitimate result, and this repo is built to report it.

## Why the null has to be empirical

At T = 250 and N = 100, `Q = T/N = 2.5`, and the Marchenko-Pastur band is wide.
Noise alone routinely produces 1-3 eigenvalues above the sharp edge, so
`observed − 0` is not evidence. `rmtfactor.nulls` simulates two null worlds
(independent shuffle; block shuffle of vol-normalised returns) and the honest
number is `observed − null p95`.

The edge itself is judged with **Tracy-Widom** fluctuations, not the asymptotic
MP threshold, because at a few hundred days the threshold is not sharp.

## Survivorship bias, stated up front

Point-in-time membership comes from `fja05680/sp500`. If that file is absent,
`data.load_membership()` returns `None`, the universe is today's index backward,
and the README must say **"survivorship-biased"**. It is not silently ignored.

## Layout

```
docs/                  the 12 project documents
AGENTS.md  README.md  PREREGISTRATION.md (+ .sha256)
data/raw/{prices,ff,universe}/          gitignored
src/rmtfactor/
  data.py       Stooq CSVs, Ken French zips, point-in-time membership
  preprocess.py log returns, expanding winsorise, EWMA normalisation
  mp.py         MP density/CDF, sigma^2 fit to the bulk, Tracy-Widom edge, IPR
  nulls.py      independent and block-shuffle null worlds
  factors.py    4-factor + industry residualisation, AI basket, loadings
  rolling.py    eigen-tracking (Hungarian), persistence, change-point test
  cov.py        4 estimators, min-variance, QLIKE/Frobenius, Diebold-Mariano
  evaluate.py   walk-forward protocol, bootstrap CI on the improvement
scripts/  fetch_prices.py  fetch_ff.py  run_study.py  stamp_prereg.py
```

## Reproduce

```bash
pip install -r requirements.txt
make stamp
make data             # Stooq prices + Ken French factors (no keys)
make study            # spectrum, nulls, controls, rolling birth, cov comparison
make test
```

Windows without `make`: `bash reproduce.sh`.

## Estimators under test

| Estimator | Idea |
|---|---|
| `sample` | the naive one, kept so its failure is visible |
| `ledoit_wolf` | shrinkage — **the bar** |
| `rmt_clip` | replace eigenvalues inside the MP band by their mean |
| `factor_2` | market + second factor explicitly, diagonal residuals (POET-style) |

Min-variance is long-only and solved by projected gradient, because the
unconstrained closed form shorts the noisy directions and looks like a strategy.

## What I'd do next

- Add a fourth estimator that uses the *identified* AI factor rather than
  "second eigenvector". If `factor_2` loses to shrinkage, forcing two factors is
  the problem, not the idea.
- Re-run with GARCH-normalised returns: if the factor survives a different
  volatility null, it is not an artefact of the EWMA.
- Sector-neutralise the AI basket and see whether the residual factor still
  matches it — that is the sharpest version of "not just semis".

## Attribution

Scaffold generated with an AI coding agent. Every statistic carries its formula in
the docstring above the implementation (`mp.py`, `cov.py`, `rolling.py`) so it can
be re-derived by hand.
