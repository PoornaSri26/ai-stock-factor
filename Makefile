PY ?= python

.PHONY: help stamp data study test clean

help:
	@echo "make stamp  freeze + hash the pre-registration"
	@echo "make data   Stooq prices + Ken French factors (no API keys)"
	@echo "make study  spectrum -> nulls -> controls -> rolling -> cov comparison"
	@echo "make test   random-matrix and estimator checks"

stamp:
	$(PY) scripts/stamp_prereg.py

data:
	$(PY) scripts/fetch_ff.py
	@echo "prices: python scripts/fetch_prices.py --tickers tickers.txt"

study:
	PYTHONPATH=src $(PY) scripts/run_study.py

test:
	PYTHONPATH=src $(PY) -m pytest -q tests

clean:
	rm -rf outputs .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
