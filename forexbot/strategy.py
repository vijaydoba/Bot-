"""Trading strategy: trend-following breakout with pullback entries.

The approach (a classic, sensible system - not a magic black box):

  * Establish trend regime with two EMAs AND a trend-strength filter (ADX).
    Only trade WITH the trend; never fight it.
  * Enter on either of two trend-confirming triggers:
      - Pullback re-entry: in an uptrend, price dips to/below the fast EMA and
        then closes back above it (buying a shallow pullback), or
      - Breakout: price closes above the highest high of the last N bars
        (Donchian breakout - momentum resumption).
    Mirror logic for downtrends.
  * Stop-loss and take-profit come from ATR so they adapt to volatility, with a
    take-profit that is a multiple of the stop (positive reward:risk).

This is trend-following: expect a MODERATE win rate (commonly 40-55%) that stays
profitable because winners are larger than losers (reward:risk > 1). That is the
honest trade-off. There is deliberately no martingale / grid / stop-less logic
that would fake a high win rate while hiding catastrophic tail risk.

Signals use only past/current data (no look-ahead). A signal at bar t is acted
on at the OPEN of bar t+1, which is exactly how the backtester consumes it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import indicators as ind


@dataclass
class StrategyParams:
    ema_fast: int = 20
    ema_slow: int = 50
    adx_period: int = 14
    adx_min: float = 18.0          # require some trend strength to trade at all
    breakout_lookback: int = 20    # Donchian channel length for breakouts
    atr_period: int = 14
    atr_stop_mult: float = 2.0     # stop = entry -/+ atr_stop_mult * ATR
    reward_risk: float = 2.0       # take-profit distance = reward_risk * stop distance
    use_pullback: bool = True
    use_breakout: bool = True


@dataclass
class Signal:
    direction: int          # +1 long, -1 short, 0 flat
    stop: float = 0.0
    take_profit: float = 0.0
    meta: dict = field(default_factory=dict)


def compute_indicators(df: pd.DataFrame, p: StrategyParams) -> pd.DataFrame:
    """Attach indicator columns to a copy of df."""
    out = df.copy()
    out["ema_fast"] = ind.ema(out["close"], p.ema_fast)
    out["ema_slow"] = ind.ema(out["close"], p.ema_slow)
    out["adx"] = ind.adx(out, p.adx_period)
    out["atr"] = ind.atr(out, p.atr_period)
    # Donchian channel of the PRIOR n bars (shifted so the current bar's own
    # high/low cannot leak into its own breakout level - prevents look-ahead).
    out["donch_hi"] = out["high"].rolling(p.breakout_lookback).max().shift(1)
    out["donch_lo"] = out["low"].rolling(p.breakout_lookback).min().shift(1)
    return out


def generate_signals(df: pd.DataFrame, p: StrategyParams) -> pd.DataFrame:
    """Return df (with indicators) plus integer 'signal' column in {-1,0,1}.

    A non-zero signal means: open a position in that direction at the next bar.
    """
    d = compute_indicators(df, p)

    uptrend = (d["ema_fast"] > d["ema_slow"]) & (d["adx"] >= p.adx_min)
    downtrend = (d["ema_fast"] < d["ema_slow"]) & (d["adx"] >= p.adx_min)

    close = d["close"]
    prev_close = close.shift(1)
    ema_f = d["ema_fast"]

    # --- Pullback re-entry: dipped to/under fast EMA last bar, reclaimed it now.
    long_pullback = uptrend & (prev_close <= ema_f.shift(1)) & (close > ema_f)
    short_pullback = downtrend & (prev_close >= ema_f.shift(1)) & (close < ema_f)

    # --- Breakout: close pushes beyond the prior Donchian extreme, with trend.
    long_breakout = uptrend & (close > d["donch_hi"]) & (prev_close <= d["donch_hi"])
    short_breakout = downtrend & (close < d["donch_lo"]) & (prev_close >= d["donch_lo"])

    long_entry = pd.Series(False, index=d.index)
    short_entry = pd.Series(False, index=d.index)
    if p.use_pullback:
        long_entry |= long_pullback
        short_entry |= short_pullback
    if p.use_breakout:
        long_entry |= long_breakout
        short_entry |= short_breakout

    signal = pd.Series(0, index=d.index, dtype=int)
    signal[long_entry] = 1
    signal[short_entry & ~long_entry] = -1  # long takes precedence if both (rare)
    d["signal"] = signal
    return d


def signal_at(d: pd.DataFrame, i: int, p: StrategyParams) -> Signal:
    """Build a concrete Signal (with stop/TP) from precomputed row i.

    Used by the live loop; the backtester computes stops inline for speed.
    """
    row = d.iloc[i]
    direction = int(row["signal"])
    if direction == 0 or pd.isna(row["atr"]):
        return Signal(0)
    entry = float(row["close"])
    stop_dist = p.atr_stop_mult * float(row["atr"])
    if direction == 1:
        stop = entry - stop_dist
        tp = entry + p.reward_risk * stop_dist
    else:
        stop = entry + stop_dist
        tp = entry - p.reward_risk * stop_dist
    return Signal(direction, stop=stop, take_profit=tp,
                  meta={"atr": float(row["atr"]), "adx": float(row["adx"])})
