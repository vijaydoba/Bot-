"""Broker abstraction.

Two implementations:

  * PaperBroker - simulates fills locally. Use this for forward-testing without
    risking money. ALWAYS start here.
  * OandaBroker - a thin scaffold around OANDA's v20 REST API. It is intentionally
    conservative and will refuse to run live unless you explicitly opt in. Fill
    in your account id + token via environment variables. (OANDA is used as the
    example because it has a clean REST API and a free practice environment.)

The Order/Position dataclasses are broker-agnostic so the live loop does not
care which broker it talks to.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Order:
    symbol: str
    direction: int      # +1 buy, -1 sell
    units: float
    stop: float
    take_profit: float


@dataclass
class Position:
    symbol: str
    direction: int
    units: float
    entry: float


class Broker(Protocol):
    def get_equity(self) -> float: ...
    def get_position(self, symbol: str) -> Position | None: ...
    def market_order(self, order: Order) -> Position: ...
    def close(self, symbol: str) -> None: ...
    def latest_price(self, symbol: str) -> float: ...


class PaperBroker:
    """Local simulation. Fills at the provided price; tracks equity simply."""

    def __init__(self, starting_equity: float = 10_000.0):
        self._equity = starting_equity
        self._positions: dict[str, Position] = {}
        self._last_price: dict[str, float] = {}

    def set_price(self, symbol: str, price: float) -> None:
        self._last_price[symbol] = price

    def latest_price(self, symbol: str) -> float:
        return self._last_price.get(symbol, 0.0)

    def get_equity(self) -> float:
        return self._equity

    def get_position(self, symbol: str) -> Position | None:
        return self._positions.get(symbol)

    def market_order(self, order: Order) -> Position:
        price = self.latest_price(order.symbol)
        pos = Position(order.symbol, order.direction, order.units, price)
        self._positions[order.symbol] = pos
        print(f"[paper] OPEN {order.symbol} dir={order.direction} "
              f"units={order.units:.0f} @ {price:.5f} "
              f"stop={order.stop:.5f} tp={order.take_profit:.5f}")
        return pos

    def close(self, symbol: str) -> None:
        pos = self._positions.pop(symbol, None)
        if pos is None:
            return
        price = self.latest_price(symbol)
        pnl = (price - pos.entry) * pos.direction * pos.units
        self._equity += pnl
        print(f"[paper] CLOSE {symbol} @ {price:.5f} pnl={pnl:.2f} "
              f"equity={self._equity:.2f}")


class OandaBroker:
    """Scaffold for live trading via OANDA v20. Practice by default.

    Requires `pip install oandapyV20` and these environment variables:
        OANDA_TOKEN        your API token
        OANDA_ACCOUNT_ID   your account id
        OANDA_ENV          'practice' (default) or 'live'

    Going live REQUIRES OANDA_ENV=live AND constructing with allow_live=True.
    This double gate exists so you cannot trade real money by accident.
    """

    def __init__(self, allow_live: bool = False):
        self.env = os.environ.get("OANDA_ENV", "practice")
        self.token = os.environ.get("OANDA_TOKEN")
        self.account_id = os.environ.get("OANDA_ACCOUNT_ID")
        if not self.token or not self.account_id:
            raise RuntimeError(
                "Set OANDA_TOKEN and OANDA_ACCOUNT_ID environment variables."
            )
        if self.env == "live" and not allow_live:
            raise RuntimeError(
                "Refusing to connect to a LIVE account. Re-create OandaBroker "
                "with allow_live=True only after you have validated the strategy "
                "in backtest AND on a practice account."
            )
        try:
            import oandapyV20  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "oandapyV20 not installed. Run: pip install oandapyV20"
            ) from exc
        from oandapyV20 import API

        self._api = API(access_token=self.token, environment=self.env)
        print(f"[oanda] connected ({self.env}) account={self.account_id}")

    # The methods below are left as clearly-marked stubs. Implementing them is
    # straightforward with oandapyV20 endpoints, but doing so blindly would be
    # irresponsible - wire them up only when you are ready and have read OANDA's
    # docs. Each raises so nothing silently no-ops.
    def get_equity(self) -> float:
        from oandapyV20.endpoints.accounts import AccountSummary
        r = AccountSummary(self.account_id)
        self._api.request(r)
        return float(r.response["account"]["NAV"])

    def latest_price(self, symbol: str) -> float:
        from oandapyV20.endpoints.pricing import PricingInfo
        r = PricingInfo(self.account_id, params={"instruments": symbol})
        self._api.request(r)
        p = r.response["prices"][0]
        bid = float(p["bids"][0]["price"])
        ask = float(p["asks"][0]["price"])
        return (bid + ask) / 2.0

    def get_position(self, symbol: str) -> Position | None:  # pragma: no cover
        raise NotImplementedError("Wire up OANDA OpenPositions endpoint when ready.")

    def market_order(self, order: Order) -> Position:  # pragma: no cover
        raise NotImplementedError("Wire up OANDA OrderCreate endpoint when ready.")

    def close(self, symbol: str) -> None:  # pragma: no cover
        raise NotImplementedError("Wire up OANDA PositionClose endpoint when ready.")
