#!/usr/bin/env python
"""Download the Ken French factor files (four factors, momentum, 49 industries).

Direct, unauthenticated zips from Dartmouth's library. No key, no terms problem
for research use — but cite the library in the README.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"

FILES = (
    "F-F_Research_Data_Factors_daily_CSV.zip",
    "F-F_Momentum_Factor_daily_CSV.zip",
    "49_Industry_Portfolios_daily_CSV.zip",
)


def main() -> int:
    out = DATA / "raw" / "ff"
    out.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name in FILES:
        dest = out / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  have {name}")
            ok += 1
            continue
        try:
            url = f"{BASE}/{name}"
            with urllib.request.urlopen(url, timeout=60) as r:
                dest.write_bytes(r.read())
            print(f"  ok   {name}  {dest.stat().st_size / 1024:.0f} KB")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {name}: {exc}\n  manual URL: {BASE}/{name}", file=sys.stderr)

    print(f"\n{ok}/{len(FILES)} factor files in {out}")
    if ok < len(FILES):
        print("The library occasionally moves files; download by hand and re-run.", file=sys.stderr)
        return 1
    print("cite: Kenneth R. French - Data Library")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
