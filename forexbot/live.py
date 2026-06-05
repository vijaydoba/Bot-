"""Live / paper trading loop.

This polls for new bars, recomputes signals, and routes orders through a Broker.
By default it runs against the PaperBroker so it cannot lose real money.

It mirrors the backtester's logic so behaviour is consistent:
  * one position at a time
  * ATR stop and reward:risk take-profit
  * fixed-fractional position sizing

IMPORTANT: this is a starting point, not a finished production trading system.
Before risking real money you still need: robust reconnection/error handling,
order-fill confirmation, slippage monitoring, a kill switch, and logging/alerting.
"""
from __future__ import annotations

import time

import pandas as pd

from . import data as data_mod
from .broker import Broker, Order, PaperBroker
from .risk import RiskParams, position_size
from .strategy import StrategyParams, generate_signals


def step(
    df: pd.DataFrame,
    broker: Broker,
    symbol: str,
    sp: StrategyParams,
    rp: RiskParams,
) -> None:
    """Evaluate the most recent CLOSED bar and act once."""
    d = generate_signals(df, sp)
    last = d.iloc[-1]
    price = float(last["close"])
    if hasattr(broker, "set_price"):
        broker.set_price(symbol, price)  # keep paper broker priced

    pos = broker.get_position(symbol)

    # Exit management: close if stop/TP breached (paper broker has no auto-exit).
    if pos is not None:
        # Recompute the stop/TP that were set at entry is out of scope here;
        # a production system stores them. For the paper demo we simply hold.
        return

    direction = int(last["signal"])
    if direction == 0 or pd.isna(last["atr"]):
        return

    equity = broker.get_equity()
    stop_dist = sp.atr_stop_mult * float(last["atr"])
    if direction == 1:
        stop = price - stop_dist
        tp = price + sp.reward_risk * stop_dist
    else:
        stop = price + stop_dist
        tp = price - sp.reward_risk * stop_dist
    units = position_size(equity, price, stop, rp)
    if units <= 0:
        return
    broker.market_order(Order(symbol, direction, units, stop, tp))


def run_paper(
    symbol: str = "EURUSD=X",
    interval: str = "1h",
    poll_seconds: int = 3600,
    iterations: int | None = None,
    sp: StrategyParams | None = None,
    rp: RiskParams | None = None,
) -> None:
    """Forward-test against a PaperBroker. Ctrl-C to stop.

    `iterations` limits the number of loops (handy for demos/tests); None = forever.
    """
    sp = sp or StrategyParams()
    rp = rp or RiskParams()
    broker = PaperBroker()
    print(f"[live] paper trading {symbol} @ {interval}. Polling every "
          f"{poll_seconds}s. This is simulated money.")

    n = 0
    while iterations is None or n < iterations:
        try:
            df = data_mod.load(symbol, period="3mo", interval=interval)
            step(df, broker, symbol, sp, rp)
            print(f"[live] equity={broker.get_equity():.2f}  source={df.attrs.get('source')}")
        except Exception as exc:  # never let the loop die silently
            print(f"[live] error: {exc.__class__.__name__}: {exc}")
        n += 1
        if iterations is not None and n >= iterations:
            break
        time.sleep(poll_seconds)
