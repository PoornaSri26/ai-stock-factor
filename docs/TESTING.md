# TESTING — Secret AI Stock Finder

## 1. Overview

| Type | Checks | Tool |
|---|---|---|
| Unit | MP density integrates to 1; bounds ordered | pytest + scipy.integrate |
| Unit | `sigma^2` recovers ~1 on pure noise | pytest |
| Unit | TW threshold sits above the MP edge and shrinks with T | pytest |
| Unit | a planted factor is detected, pure noise is not | pytest |
| Unit | shuffle destroys correlation, keeps marginals | pytest |
| Unit | min-variance weights are long-only and sum to 1 | pytest |
| Unit | QLIKE minimised at a perfect forecast | pytest |
| Unit | DM detects an ordering, not noise | pytest |
| Unit | residualisation removes a known beta | pytest |
| Unit | change-point finds a planted break, not noise | pytest |

## 2. Goals

1. An edge threshold set too low fails a test (noise must not look like a factor).
2. A broken residualisation fails a test (a known beta must survive).
3. A min-variance solver returning shorts or weights ≠ 1 fails a test.
4. A DM implementation that reports significance on noise fails a test.

## 3. Test cases

| ID | Scenario | Expected | Status |
|---|---|---|---|
| TC-01 | MP bounds for `sigma^2=1, q=0.25` | (0.25, 2.25) | Pass |
| TC-02 | MP pdf integrates over (0, 10) | 1.0 ± 0.02 | Pass |
| TC-03 | `fit_sigma2` on 2000×50 noise | 0.8 < σ² < 1.25, KS < 0.10 | Pass |
| TC-04 | TW > MP edge for three (T, N) pairs | true | Pass |
| TC-05 | TW decreases as T grows | true | Pass |
| TC-06 | count above edge on 2000×50 noise | ≤ 2 | Pass |
| TC-07 | planted single factor | ≥ 1 above edge | Pass |
| TC-08 | IPR: spread < concentrated; concentrated = 1 | true | Pass |
| TC-09 | independent shuffle | off-diagonal \|ρ\| < 0.2, marginals identical | Pass |
| TC-10 | block shuffle | same shape, no NaN | Pass |
| TC-11 | min-variance weights | ≥ 0, sum = 1 | Pass |
| TC-12 | QLIKE at a perfect forecast | 0 | Pass |
| TC-13 | DM on a clear ordering | < −1.96, significant | Pass |
| TC-14 | DM on noise | \|DM\| < 3 | Pass |
| TC-15 | residualise with beta 2.0 | recovers 2.0 ± 0.05, residual sd < 0.01 | Pass |
| TC-16 | Hungarian matching with sign flips | cos = 1 for both pairs | Pass |
| TC-17 | change-point planted at 40 | index in [30, 50], p < 0.01 | Pass |
| TC-18 | change-point on noise | p > 0.01 | Pass |
| TC-19 | basket vector | L2 = 1; no overlap raises | Pass |
| TC-20 | `walk_forward` end-to-end on synthetic data | 4 estimators × periods, Ledoit-Wolf best on noise | Verified manually |
| TC-21 | `run_study.py` without FF files | exit 1 with "refusing" message | **Pending** |

## 4. Running

```bash
make test
PYTHONPATH=src python -m pytest -q tests -k "mp or tw"
PYTHONPATH=src python -m pytest -q tests -k cov
```

## 5. Checklist

- [ ] Tests need no network and no data files.
- [ ] Every statistic has a closed-form or planted-signal case.
- [ ] The noise test would fail if `sigma^2` were fixed at 1.
- [ ] The DM test would fail if HAC were replaced by an iid variance on
      autocorrelated losses.
- [ ] Synthetic end-to-end run finishes in under a minute.

## 6. What is not tested

- **Data provider availability.** Terms and endpoints change; `TRD.md` §6 is the
  dated record.
- **Whether AI is really a factor.** No test can answer that; the pre-registered
  bar and the walk-forward comparison can.
- **The choice of basket.** A judgement, declared in advance, not verifiable.
- **Min-variance optimality** against a QP solver. The projected gradient is
  checked for feasibility, not for exact optimality; a cross-check is listed as
  follow-up.
