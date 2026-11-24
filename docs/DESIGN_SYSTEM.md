# DESIGN_SYSTEM — Secret AI Stock Finder

Deliverables: an **eigenvalue spectrum with the null band and the edge**, a
**rolling eigenvalue + basket-cosine panel**, and a **QLIKE comparison bar chart
with CIs**.

## 1. Colour tokens (`src/rmtfactor/style.py`)

| Token | Hex | Use |
|---|---|---|
| `ink` | `#111318` | text, axes |
| `grid` | `#D6DAE1` | gridlines |
| `bulk` | `#9AA3B2` | eigenvalues inside the noise band |
| `edge` | `#B3261E` | the Tracy-Widom threshold (dashed rule) |
| `signal` | `#3B6EA5` | eigenvalues above the edge |
| `basket` | `#8A5A00` | basket cosine series |
| `muted` | `#6B7280` | annotations, `n` counts |

Rules:
- The MP band is a **shaded grey region**, not two lines: it is an interval, and
  shading communicates that instantly.
- The edge is a **red dashed rule** with its value. Only one threshold per panel.
- Above-edge eigenvalues are the only blue points. Everything else is grey.
- Never colour by "sector" — the industry control is a statistical step, not a
  palette.

## 2. Figure geometry

| Figure | Size (in) | Notes |
|---|---|---|
| spectrum | 6.8 × 4.2 | x = eigenvalue rank, y = eigenvalue (log optional) |
| rolling panel | 6.8 × 5.0 | two stacked axes: eigenvalue, then cosine |
| QLIKE bars | 6.8 × 4.2 | error bars = bootstrap CI, bar at the shrinkage estimator |

DPI 160. 9 pt ticks. 11 pt bold title. Top/right spines off.

## 3. Axis conventions

- **Spectrum:** rank on x (1..N), eigenvalue on y; log-y is usually better
  because `lambda_1` is 20× `lambda_20`. Label which scale is used.
- **Rolling:** x = window end date; vertical rule at `2023-01-01` (the declared
  "after" date) and a second at the detected break, labelled distinctly.
- **QLIKE:** lower is better, so invert nothing — state "lower is better" in the
  subtitle and sort ascending.

## 4. Required annotations

1. `T`, `N`, `Q` in every spectrum panel — the result is conditional on them;
2. `sigma^2` and the edge value on the spectrum;
3. the null's 95th percentile count as a dashed horizontal rule on any
   "how many factors" chart.

## 5. Tables

- Estimator table order: `sample`, `ledoit_wolf`, `rmt_clip`, `factor_2` — the bar
  sits in the middle so an improvement or a regression is visible either way.
- Always print `n_periods`; a QLIKE difference over 8 months is not a result.
- DM rows carry `significant` as words ("yes"/"no"), not colour.

## 6. Accessibility

- [ ] Greyscale: shading + dash + marker carry the distinctions.
- [ ] Log axes labelled as log.
- [ ] Contrast ≥ 7:1.
- [ ] Alt text: conclusion plus T, N, Q.
