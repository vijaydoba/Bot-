"""Bar-by-bar backtester with realistic trading costs.

Design goals (all aimed at NOT lying to yourself):

  * No look-ahead: a signal generated on bar t is executed at the OPEN of bar
    t+1. Indicators only use data up to the bar they are computed on.
  * Spread: every entry/exit pays half the spread on each side (modelled as the
    bid/ask gap around the mid price).
  * Slippage: a configurable number of pips is added against you on fills.
  * One position at a time (no pyramiding) - simple and honest.
  * Intrabar exits: stop-loss and take-profit are checked against each bar's
    high/low. When both could trigger in the same bar we assume the WORSE case
    (stop first) - a conservative assumption so results are not rosy.
  * Position sizing comes from the risk module (fixed fractional risk).

Returns a BacktestResult with the equity curve and a per-trade log.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import metrics as metrics_mod
from .risk import RiskParams, position_size
from .strategy import StrategyParams, generate_signals


@dataclass
class CostModel:
    spread_pips: float = 1.0       # typical EURUSD spread
    slippage_pips: float = 0.5     # extra adverse fill per side
    commission_per_trade: float = 0.0  # account-currency commission per fill
    pip: float = 0.0001


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: metrics_mod.Metrics
    data_source: str = "unknown"

    def summary(self) -> str:
        return self.metrics.pretty()


def _infer_bars_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 3:
        return 252.0
    # Use pandas Timedelta so we are independent of the index's datetime
    # resolution (pandas 3.0 indexes can be us/ns/ms - don't assume ns).
    deltas = index.to_series().diff().dropna()
    median = deltas.median()
    seconds = median.total_seconds()
    if seconds <= 0:
        return 252.0
    bars_per_day = (24 * 3600) / seconds
    # Forex trades ~5 days/week.
    return bars_per_day * 5 * 52


def run(
    df: pd.DataFrame,
    sp: StrategyParams | None = None,
    rp: RiskParams | None = None,
    cost: CostModel | None = None,
    initial_equity: float = 10_000.0,
) -> BacktestResult:
    sp = sp or StrategyParams()
    rp = rp or RiskParams()
    cost = cost or CostModel()

    d = generate_signals(df, sp)
    closes = d["close"].to_numpy()
    opens = d["open"].to_numpy()
    highs = d["high"].to_numpy()
    lows = d["low"].to_numpy()
    atr = d["atr"].to_numpy()
    signal = d["signal"].to_numpy()
    index = d.index

    half_spread = (cost.spread_pips / 2.0) * cost.pip
    slip = cost.slippage_pips * cost.pip

    equity = initial_equity
    equity_curve = np.empty(len(d))
    trades: list[dict] = []

    pos = 0          # +1 long, -1 short, 0 flat
    units = 0.0
    entry_px = 0.0
    stop = 0.0
    take = 0.0
    entry_i = 0

    for i in range(len(d)):
        # ---- Manage an open position against THIS bar's range ----
        if pos != 0:
            hi, lo = highs[i], lows[i]
            exit_px = None
            reason = None
            if pos == 1:
                hit_stop = lo <= stop
                hit_take = hi >= take
                if hit_stop:  # conservative: assume stop first if both
                    exit_px, reason = stop, "stop"
                elif hit_take:
                    exit_px, reason = take, "take_profit"
            else:  # short
                hit_stop = hi >= stop
                hit_take = lo <= take
                if hit_stop:
                    exit_px, reason = stop, "stop"
                elif hit_take:
                    exit_px, reason = take, "take_profit"

            if exit_px is not None:
                # Apply adverse slippage + spread on the exit fill.
                fill = exit_px - (half_spread + slip) * pos
                pnl = (fill - entry_px) * pos * units - cost.commission_per_trade
                equity += pnl
                trades.append(
                    {
                        "entry_time": index[entry_i],
                        "exit_time": index[i],
                        "direction": pos,
                        "entry": entry_px,
                        "exit": fill,
                        "units": units,
                        "pnl": pnl,
                        "reason": reason,
                        "bars_held": i - entry_i,
                    }
                )
                pos, units = 0, 0.0

        # ---- Open a new position at THIS bar's open from the PREVIOUS signal ----
        # signal[i-1] was generated using data through bar i-1; we act at open i.
        if pos == 0 and i > 0 and signal[i - 1] != 0 and not np.isnan(atr[i - 1]):
            direction = int(signal[i - 1])
            raw = opens[i]
            # Pay half-spread + slippage adversely on entry.
            entry_px = raw + (half_spread + slip) * direction
            stop_dist = sp.atr_stop_mult * atr[i - 1]
            if stop_dist > 0:
                if direction == 1:
                    stop = entry_px - stop_dist
                    take = entry_px + sp.reward_risk * stop_dist
                else:
                    stop = entry_px + stop_dist
                    take = entry_px - sp.reward_risk * stop_dist
                units = position_size(equity, entry_px, stop, rp)
                if units > 0:
                    equity -= cost.commission_per_trade
                    pos = direction
                    entry_i = i

        equity_curve[i] = equity

    # Close any position still open at the final bar (mark to last close).
    if pos != 0:
        fill = closes[-1] - (half_spread + slip) * pos
        pnl = (fill - entry_px) * pos * units - cost.commission_per_trade
        equity += pnl
        trades.append(
            {
                "entry_time": index[entry_i],
                "exit_time": index[-1],
                "direction": pos,
                "entry": entry_px,
                "exit": fill,
                "units": units,
                "pnl": pnl,
                "reason": "eod_close",
                "bars_held": len(d) - 1 - entry_i,
            }
        )
        equity_curve[-1] = equity

    eq = pd.Series(equity_curve, index=index, name="equity")
    trades_df = pd.DataFrame(trades)
    bars_per_year = _infer_bars_per_year(index)
    m = metrics_mod.compute(trades_df, eq, bars_per_year)
    return BacktestResult(
        equity_curve=eq,
        trades=trades_df,
        metrics=m,
        data_source=str(df.attrs.get("source", "unknown")),
    )
