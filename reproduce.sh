#!/usr/bin/env bash
# Stand-in for `make reproduce` where make is unavailable (Windows).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python}"
stages=("$@")
if [ ${#stages[@]} -eq 0 ]; then stages=(study); fi
for s in "${stages[@]}"; do
  echo "== stage: $s"
  case "$s" in
    ff)    PYTHONPATH=src "$PY" scripts/fetch_ff.py ;;
    prices) PYTHONPATH=src "$PY" scripts/fetch_prices.py --tickers tickers.txt ;;
    study) PYTHONPATH=src "$PY" scripts/run_study.py ;;
    *) echo "unknown stage: $s" >&2; exit 2 ;;
  esac
done
