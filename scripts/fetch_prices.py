#!/usr/bin/env python
"""Download daily prices for a ticker list from Stooq (no key, one CSV per name).

Stooq's CSV endpoint:
    https://stooq.com/q/d/l/?s=<ticker>.us&i=d

Rate: be polite. This script sleeps between requests and skips files it already
has. Run it once for the universe; do not put it in a loop in CI.

Usage:
    python scripts/fetch_prices.py --tickers tickers.txt
    python scripts/fetch_prices.py --tickers NVDA MSFT TSM
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
URL = "https://stooq.com/q/d/l/?s={ticker}.us&i=d"


def fetch(ticker: str, dest: Path, sleep: float = 1.0) -> bool:
    if dest.exists() and dest.stat().st_size > 200:
        print(f"  have {ticker}")
        return True
    try:
        req = urllib.request.Request(URL.format(ticker=ticker.lower()), headers={"User-Agent": "rmtfactor/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
        if b"Date,Open" not in body[:100]:
            print(f"  FAIL {ticker}: unexpected payload (delisted or wrong suffix?)", file=sys.stderr)
            return False
        dest.write_bytes(body)
        print(f"  ok   {ticker}  {len(body) / 1024:.0f} KB")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {ticker}: {exc}", file=sys.stderr)
        return False
    finally:
        time.sleep(sleep)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", required=True, help="a file of tickers or tickers directly")
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    out = DATA / "raw" / "prices"
    out.mkdir(parents=True, exist_ok=True)

    if len(args.tickers) == 1 and Path(args.tickers[0]).exists():
        tickers = [t.strip().upper() for t in Path(args.tickers[0]).read_text().split() if t.strip()]
    else:
        tickers = [t.upper() for t in args.tickers]

    print(f"fetching {len(tickers)} tickers into {out}")
    ok = sum(fetch(t, out / f"{t}.csv", args.sleep) for t in tickers)
    print(f"\n{ok}/{len(tickers)} present")
    if ok < len(tickers):
        print("Delisted names are expected in a historical universe; note them, do not drop silently.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
