#!/usr/bin/env python3
"""Run a backtest from the command line.

Examples:
    python run_backtest.py                          # EURUSD 1h, real data if reachable
    python run_backtest.py --symbol GBPUSD=X --interval 1h --period 2y
    python run_backtest.py --plot equity.png        # save an equity-curve chart
    python run_backtest.py --synthetic              # force offline synthetic data
"""
from __future__ import annotations

import argparse

from forexbot import data as data_mod
from forexbot.backtest import CostModel, run
from forexbot.risk import RiskParams
from forexbot.strategy import StrategyParams


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest the trend-pullback strategy.")
    ap.add_argument("--symbol", default="EURUSD=X")
    ap.add_argument("--interval", default="1h")
    ap.add_argument("--period", default="2y")
    ap.add_argument("--csv", default=None, help="Load OHLCV from a CSV instead.")
    ap.add_argument("--synthetic", action="store_true",
                    help="Force synthetic offline data (no network).")
    ap.add_argument("--equity", type=float, default=10_000.0)
    ap.add_argument("--risk", type=float, default=0.01, help="Risk per trade (fraction).")
    ap.add_argument("--rr", type=float, default=1.8, help="Reward:risk ratio.")
    ap.add_argument("--spread", type=float, default=1.0, help="Spread in pips.")
    ap.add_argument("--plot", default=None, help="Path to save equity-curve PNG.")
    args = ap.parse_args()

    if args.csv:
        df = data_mod.from_csv(args.csv)
        df.attrs["source"] = f"csv:{args.csv}"
    elif args.synthetic:
        df = data_mod.synthetic()
        df.attrs["source"] = "synthetic(forced)"
    else:
        df = data_mod.load(args.symbol, period=args.period, interval=args.interval)

    sp = StrategyParams(reward_risk=args.rr)
    rp = RiskParams(risk_per_trade=args.risk)
    cost = CostModel(spread_pips=args.spread)

    result = run(df, sp=sp, rp=rp, cost=cost, initial_equity=args.equity)

    print("=" * 56)
    print(f"Symbol:     {args.symbol}")
    print(f"Bars:       {len(df)}")
    print(f"Data source:{result.data_source}")
    print("-" * 56)
    print(result.summary())
    print("=" * 56)
    if result.data_source.startswith("synthetic"):
        print("NOTE: results are on SYNTHETIC data - illustrative only. "
              "Re-run with real yfinance/CSV data for meaningful numbers.")

    if args.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(11, 5))
            result.equity_curve.plot(ax=ax)
            ax.set_title(f"Equity curve - {args.symbol} ({result.data_source})")
            ax.set_ylabel("Equity")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            fig.savefig(args.plot, dpi=120)
            print(f"Saved equity curve to {args.plot}")
        except ImportError:
            print("matplotlib not installed; skipping --plot. pip install matplotlib")


if __name__ == "__main__":
    main()
