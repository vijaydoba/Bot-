"""Historical price data loading.

Priority order:
    1. Local CSV cache (data/<symbol>_<interval>.csv)
    2. yfinance download (real data - works wherever Yahoo is reachable)
    3. Synthetic generator (deterministic, offline fallback for testing)

Returned DataFrames always have lower-case columns:
    open, high, low, close, volume   indexed by a tz-aware DatetimeIndex.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_DIR = Path(os.environ.get("FOREXBOT_CACHE", "data"))


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case columns, keep OHLCV, drop NaN rows."""
    df = df.copy()
    # yfinance can return a MultiIndex column frame for a single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    rename = {"adj close": "adj_close"}
    df = df.rename(columns=rename)
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df.dropna(subset=["open", "high", "low", "close"])


def from_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLCV from a CSV with a datetime index in the first column."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return _normalize(df)


def from_yfinance(
    symbol: str = "EURUSD=X",
    period: str = "2y",
    interval: str = "1h",
    cache: bool = True,
) -> pd.DataFrame:
    """Download real data via yfinance. Raises if no data comes back."""
    import yfinance as yf  # imported lazily so offline use does not require it

    df = yf.download(
        symbol, period=period, interval=interval, progress=False, auto_adjust=False
    )
    if df is None or len(df) == 0:
        raise RuntimeError(
            f"yfinance returned no data for {symbol} "
            f"(period={period}, interval={interval}). "
            "Network may be blocked, or the symbol/interval is invalid."
        )
    df = _normalize(df)
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe = symbol.replace("=", "").replace("/", "")
        df.to_csv(CACHE_DIR / f"{safe}_{interval}.csv")
    return df


def synthetic(
    n: int = 6000,
    interval_minutes: int = 60,
    start_price: float = 1.10,
    seed: int = 42,
    annual_vol: float = 0.08,
    trend_strength: float = 0.28,
    trend_prob: float = 0.40,
) -> pd.DataFrame:
    """Generate deterministic synthetic OHLCV that *looks* like a forex pair.

    Uses a regime-switching geometric random walk so there are real trends
    (which a trend strategy can exploit) interleaved with choppy ranges
    (which it cannot). This is NOT real data - it exists so the backtester
    and tests run with zero network access. Do not draw real conclusions from
    synthetic results; use yfinance/CSV data for that.
    """
    rng = np.random.default_rng(seed)
    minutes_per_year = 365 * 24 * 60
    bar_vol = annual_vol * np.sqrt(interval_minutes / minutes_per_year)

    # Regime-switching drift: alternate trending and ranging blocks.
    drift = np.zeros(n)
    i = 0
    while i < n:
        block = rng.integers(120, 400)
        if rng.random() < trend_prob:  # trending block
            direction = rng.choice([-1.0, 1.0])
            drift[i : i + block] = direction * trend_strength * bar_vol
        # else ranging block -> drift stays 0
        i += block

    shocks = rng.normal(0.0, bar_vol, n)
    log_ret = drift + shocks
    close = start_price * np.exp(np.cumsum(log_ret))

    open_ = np.empty(n)
    open_[0] = start_price
    open_[1:] = close[:-1]
    wick = np.abs(rng.normal(0.0, bar_vol, n)) * close
    high = np.maximum(open_, close) + wick * rng.random(n)
    low = np.minimum(open_, close) - wick * rng.random(n)
    volume = rng.integers(500, 5000, n).astype(float)

    idx = pd.date_range("2021-01-01", periods=n, freq=f"{interval_minutes}min", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def load(
    symbol: str = "EURUSD=X",
    period: str = "2y",
    interval: str = "1h",
    allow_synthetic: bool = True,
) -> pd.DataFrame:
    """Best-effort loader: cache -> yfinance -> synthetic.

    Returns (df). The caller can inspect df.attrs['source'] to know the origin.
    """
    safe = symbol.replace("=", "").replace("/", "")
    cache_path = CACHE_DIR / f"{safe}_{interval}.csv"
    if cache_path.exists():
        df = from_csv(cache_path)
        df.attrs["source"] = f"cache:{cache_path}"
        return df

    try:
        df = from_yfinance(symbol, period=period, interval=interval)
        df.attrs["source"] = "yfinance"
        return df
    except Exception as exc:  # network blocked, bad symbol, yfinance missing...
        if not allow_synthetic:
            raise
        print(
            f"[data] yfinance unavailable ({exc.__class__.__name__}: {exc}).\n"
            f"[data] Falling back to SYNTHETIC data - results are illustrative only."
        )
        df = synthetic()
        df.attrs["source"] = "synthetic"
        return df
