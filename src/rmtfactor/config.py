"""Paths, seeds and the frozen constants for the AI-factor study."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
FIG = OUT / "figures"

SEED = 7

# sample
START = "2018-01-01"

# preprocess
WINSOR_SD = 5.0
EWMA_LAMBDA = 0.94

# spectrum
Q_LIMIT_WARN = 5.0          # warn if T/N is this small: the noise band is wide
BULK_TRIM = 0.10            # top share excluded from the sigma^2 fit
EDGE_LEVEL = 0.95
NULL_PATHS = 200
NULL_BLOCK = 20

# rolling analysis
ROLL_WINDOW = 250
ROLL_STEP = 10
N_TRACK = 4
MATCH_MIN_OVERLAP = 0.5
BREAK_AFTER = "2023-01-01"

# covariance comparison
EST_WINDOW = 500
FORWARD_DAYS = 21
REBALANCE_DAYS = 21
BAR_ESTIMATOR = "ledoit_wolf"


def ensure_dirs() -> None:
    for p in (DATA, OUT, FIG):
        p.mkdir(parents=True, exist_ok=True)
