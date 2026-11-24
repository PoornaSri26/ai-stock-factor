"""Data loading: price panel, Fama-French factors, point-in-time membership.

Sources (all free; check each provider's current terms and limits before a bulk
pull — quotas change):

* **Stooq** bulk CSVs: `https://stooq.com/q/d/l/?s=<ticker>.us&i=d` returns
  `Date,Open,High,Low,Close,Volume`. No key, rate-limited by courtesy.
* **yfinance** fallback: convenient, but read its terms; it is not a data vendor.
* **Ken French library**: zipped CSVs, direct download, no key:
    - `F-F_Research_Data_Factors_daily_CSV.zip`
    - `F-F_Momentum_Factor_daily_CSV.zip`
    - `49_Industry_Portfolios_daily_CSV.zip`
* **Point-in-time membership**: `fja05680/sp500` (a GitHub CSV history of index
  changes). Without it, the universe is survivorship-biased — which is stated in
  the README rather than assumed away.

Nothing here computes a return; that is `preprocess`.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from .config import DATA

RAW = DATA / "raw"
PRICES = RAW / "prices"
FF = RAW / "ff"
UNIV = RAW / "universe"


def read_stooq_csv(path: Path) -> pd.Series:
    """Stooq daily CSV -> adjusted-close series indexed by date."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError(f"{path} is not a Stooq CSV (columns: {list(df.columns)})")
    s = pd.Series(
        pd.to_numeric(df["close"], errors="coerce").to_numpy(),
        index=pd.to_datetime(df["date"], errors="coerce"),
        name=path.stem,
    )
    return s.dropna().sort_index()


def price_panel(tickers: list[str] | None = None, min_coverage: float = 0.9) -> pd.DataFrame:
    """Wide adjusted-close panel from the local Stooq files.

    ``min_coverage`` drops columns with too many missing days *within the span
    where the stock exists*, which is different from dropping them for being
    listed late. A stock that IPO'd in 2021 is kept and its NaNs stay; a stock
    with holes is dropped.
    """
    files = sorted(PRICES.glob("*.csv"))
    if tickers:
        wanted = {t.lower() for t in tickers}
        files = [f for f in files if f.stem.lower() in wanted]
    if not files:
        raise FileNotFoundError(f"no price CSVs in {PRICES}. Run scripts/fetch_prices.py.")

    series = [read_stooq_csv(f) for f in files]
    panel = pd.concat(series, axis=1).sort_index()
    panel = panel.loc[:, ~panel.columns.duplicated()]

    span = panel.notna().sum()
    first_last = panel.apply(lambda s: s.last_valid_index())
    keep = []
    for col in panel.columns:
        s = panel[col]
        live = s.loc[s.first_valid_index() : s.last_valid_index()]
        if live.size == 0:
            continue
        if live.notna().mean() >= min_coverage:
            keep.append(col)
    dropped = sorted(set(panel.columns) - set(keep))
    if dropped:
        print(f"  dropped {len(dropped)} sparse columns, kept {len(keep)}")
    return panel[keep]


def read_ff_zip(path: Path, skip: int = 3) -> pd.DataFrame:
    """Ken French zipped CSV -> DataFrame with a parsed monthly/daily index.

    The files carry a multi-line header and a trailing annual section; ``skip``
    and the trailing filter handle both. Values are in **percent**, and the
    footer rows (``Copyright`` etc.) must be dropped or the whole frame becomes
    object dtype.
    """
    with zipfile.ZipFile(path) as zf:
        inner = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        raw = zf.read(inner).decode("latin-1")
    df = pd.read_csv(io.StringIO(raw), skiprows=skip)
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date")
    df = df.apply(pd.to_numeric, errors="coerce").dropna(how="all")
    return df


def load_ff() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(four factors, 49 industries), daily, in decimal units."""
    f4 = read_ff_zip(FF / "F-F_Research_Data_Factors_daily_CSV.zip")
    mom = read_ff_zip(FF / "F-F_Momentum_Factor_daily_CSV.zip")
    mom = mom.rename(columns={mom.columns[0]: "MOM"})
    ff = f4.join(mom[["MOM"]], how="inner")
    ind = read_ff_zip(FF / "49_Industry_Portfolios_daily_CSV.zip")
    # percent -> decimal, once, here rather than in three places later
    return ff / 100.0, ind / 100.0


def load_membership() -> pd.DataFrame | None:
    """Point-in-time S&P 500 membership, if the history CSV has been downloaded.

    Expected columns: ``date, tickers`` (the fja05680/sp500 format), one row per
    change. Returns None when absent, and the caller must then state the
    survivorship bias in the README.
    """
    p = UNIV / "sp500_history.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    if "tickers" not in df.columns:
        raise ValueError(f"{p} must have columns date,tickers")
    df["members"] = df["tickers"].str.split(",")
    return df.sort_values("date")


def members_on(history: pd.DataFrame, when: pd.Timestamp) -> set[str]:
    """Membership as of a date: the most recent change row at or before it."""
    prior = history[history["date"] <= when]
    if prior.empty:
        return set()
    return set(prior.iloc[-1]["members"])
