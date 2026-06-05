#!/usr/bin/env python3
"""Run forward (paper) trading.

By default this trades SIMULATED money via the PaperBroker - it cannot touch a
real account. Live trading through OANDA is gated behind explicit flags inside
forexbot/broker.py and is intentionally not wired up by this script.

Examples:
    python run_live.py                       # paper trade EURUSD 1h forever
    python run_live.py --iterations 3 --poll 2   # short demo run
"""
from __future__ import annotations

import argparse

from forexbot.live import run_paper
from forexbot.risk import RiskParams
from forexbot.strategy import StrategyParams


def main() -> None:
    ap = argparse.ArgumentParser(description="Paper-trade the strategy live.")
    ap.add_argument("--symbol", default="EURUSD=X")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--poll", type=int, default=3600, help="Seconds between polls.")
    ap.add_argument("--iterations", type=int, default=None,
                    help="Stop after N loops (default: run forever).")
    ap.add_argument("--risk", type=float, default=0.01)
    ap.add_argument("--rr", type=float, default=1.8)
    args = ap.parse_args()

    print("*" * 60)
    print("PAPER TRADING (simulated money). No real funds at risk.")
    print("To go live you must explicitly configure OandaBroker in")
    print("forexbot/broker.py - read the warnings there first.")
    print("*" * 60)

    run_paper(
        symbol=args.symbol,
        interval=args.interval,
        poll_seconds=args.poll,
        iterations=args.iterations,
        sp=StrategyParams(reward_risk=args.rr),
        rp=RiskParams(risk_per_trade=args.risk),
    )


if __name__ == "__main__":
    main()
