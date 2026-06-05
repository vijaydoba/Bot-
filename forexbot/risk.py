"""Risk management and position sizing.

The golden rule: risk a fixed small fraction of equity per trade. The position
size is derived from the stop distance so that, IF the stop is hit, the loss is
exactly that fraction. This is what keeps an account alive across losing streaks.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskParams:
    risk_per_trade: float = 0.01   # 1% of equity risked per trade
    max_position_units: float = 1_000_000  # broker/leverage cap (safety)
    pip_value: float = 0.0001      # for EURUSD-style pairs


def position_size(
    equity: float,
    entry: float,
    stop: float,
    rp: RiskParams,
) -> float:
    """Units of the base currency to trade.

    loss_if_stopped = units * |entry - stop|  ==  equity * risk_per_trade
    => units = equity * risk_per_trade / |entry - stop|
    """
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return 0.0
    units = (equity * rp.risk_per_trade) / stop_dist
    return float(min(units, rp.max_position_units))
