# ARCHITECTURE — Secret AI Stock Finder

## 1. System overview

```
 Stooq CSVs        Ken French zips        sp500 history (optional)
     |                   |                        |
     v                   v                        v
 rmtfactor.data  (price_panel, load_ff, load_membership)
     |
     v
 rmtfactor.preprocess (log rets -> winsorise -> lagged EWMA normalise)
     |
     +---------------------+----------------------+
     v                     v                      v
 rmtfactor.mp        rmtfactor.nulls        rmtfactor.factors
 (MP, TW, IPR)       (2 null worlds)        (4 factors + 49 industries)
     |                     |                      |
     +----------+----------+----------+-----------+
                v                     v
        rmtfactor.rolling      (residual correlation matrix)
        (tracking, persistence, change-point)
                |
                v
        rmtfactor.cov  (4 estimators, min-variance, QLIKE, DM)
                |
                v
        rmtfactor.evaluate (walk-forward, bootstrap CI)
                |
                v
        outputs/study.json, cov_comparison.csv, dm_tests.csv
```

## 2. Layers and responsibilities

| Layer | Module | Does | Must never |
|---|---|---|---|
| Ingest | `data.py` | CSVs/zips → frames | compute returns |
| Transform | `preprocess.py` | returns, winsorise, normalise | look ahead in the EWMA |
| Spectrum | `mp.py` | MP law, bulk fit, TW edge | decide significance (that is `nulls`) |
| Nulls | `nulls.py` | simulate noise, count edges | touch real cross-correlation |
| Controls | `factors.py` | residualise, basket, loadings | choose the basket after seeing results |
| Dynamics | `rolling.py` | track, persist, break | fit on the evaluation period |
| Estimation | `cov.py` | estimators, weights, losses | select the estimator post hoc |
| Evaluation | `evaluate.py` | walk-forward, DM, bootstrap | recompute a factor claim |
| Orchestration | `scripts/run_study.py` | wire and print | hold formulas |

## 3. Data flow: one decision

1. `preprocess.prepare` produces normalised returns and prints `Q = T/N`.
2. `mp.fit_sigma2` fits the bulk; `tw_threshold` gives the edge in eigenvalue
   units of `S = X'X/T`.
3. `nulls.null_edge_counts` produces the noise distribution of edge counts.
4. `factors.residualise` strips market/size/value/momentum and industries.
5. `rolling.rolling_eigen` tracks the top eigenvectors through 250-day windows
   with Hungarian matching; `score_against_basket` adds the cosine with the
   pre-declared basket.
6. `rolling.persistence` and `change_point` turn "it looks like it appeared" into
   two numbers.
7. `evaluate.walk_forward` re-estimates monthly and records QLIKE, realised
   variance and Frobenius per period.
8. `evaluate.significance` runs DM against Ledoit-Wolf; `bootstrap_improvement`
   gives a CI over periods.

## 4. Folder structure

```
05-ai-stock-factor/
├── docs/                the 12 documents
├── AGENTS.md  README.md  PREREGISTRATION.md (+ .sha256)
├── Makefile  requirements.txt  .gitignore  reproduce.sh/.ps1
├── tickers.txt          the universe (a research decision, committed)
├── data/raw/{prices,ff,universe}/
├── src/rmtfactor/       data preprocess mp nulls factors rolling cov evaluate config style
├── scripts/             fetch_prices fetch_ff run_study stamp_prereg
├── tests/
└── outputs/
```

## 5. Architectural decisions

| Decision | Why | Cost |
|---|---|---|
| `sigma^2` fitted to the bulk, not fixed at 1 | the market mode inflates `lambda_1` 10x and hides structure | one more optimisation |
| Tracy-Widom, not the MP edge | at T=250 the threshold is not sharp | a literature constant to justify |
| Two null worlds | independent shuffle is too easy; block shuffle is honest | 2× simulation time |
| Industry residualisation is a hard gate | otherwise "AI" is "semis" | fewer significant findings |
| Hungarian matching across windows | otherwise ranks swap and "persistence" is meaningless | an assignment per window |
| Pre-declared basket | prevents reverse-engineering the factor | a fixed, possibly wrong, basket |
| Long-only min-variance | the unconstrained solution shorts noise | a projected-gradient solver |
| DM with HAC errors | monthly losses are serially correlated | 20 lines instead of statsmodels |
| Bootstrap over periods | assets are not independent units | wide intervals, which is true |

## 6. Extension points

- **New estimator:** add a function `x -> cov` to `cov.ESTIMATORS`. Do not touch
  `evaluate.py`.
- **New null:** add a `shuffle_*` function to `nulls.NULLS`; it must keep each
  column's marginal.
- **Alternative volatility model:** implement `garch_normalise` in `preprocess`
  and make it a config switch; state which was used in every table caption.
- **Different objective:** add a max-diversification or GMV-with-turnover
  objective in `cov.py`, and report all objectives rather than the best one.
