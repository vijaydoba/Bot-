"""Performance metrics computed from a trade log and equity curve.

These deliberately report the numbers that actually matter - not just win rate.
A high win rate with negative expectancy is a losing system; expectancy and
risk-adjusted return tell the truth.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Metrics:
    n_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    expectancy: float          # expected profit per trade (account currency)
    profit_factor: float       # gross profit / gross loss
    total_return: float        # fraction, e.g. 0.23 == +23%
    max_drawdown: float        # fraction, negative
    sharpe: float              # annualized, on per-bar equity returns
    cagr: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()

    def pretty(self) -> str:
        return (
            f"Trades:        {self.n_trades}\n"
            f"Win rate:      {self.win_rate * 100:.1f}%\n"
            f"Avg win:       {self.avg_win:.2f}\n"
            f"Avg loss:      {self.avg_loss:.2f}\n"
            f"Expectancy:    {self.expectancy:.2f}  (per trade; >0 is good)\n"
            f"Profit factor: {self.profit_factor:.2f}  (>1 is profitable)\n"
            f"Total return:  {self.total_return * 100:.1f}%\n"
            f"CAGR:          {self.cagr * 100:.1f}%\n"
            f"Max drawdown:  {self.max_drawdown * 100:.1f}%\n"
            f"Sharpe:        {self.sharpe:.2f}  (annualized)"
        )


def compute(
    trades: pd.DataFrame,
    equity_curve: pd.Series,
    bars_per_year: float,
) -> Metrics:
    n = len(trades)
    if n == 0:
        return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    pnl = trades["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    win_rate = len(wins) / n
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0
    expectancy = pnl.mean()
    gross_profit = wins.sum()
    gross_loss = -losses.sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    start_eq = equity_curve.iloc[0]
    end_eq = equity_curve.iloc[-1]
    total_return = end_eq / start_eq - 1.0

    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    max_drawdown = drawdown.min()

    rets = equity_curve.pct_change().dropna()
    if rets.std() > 0:
        sharpe = (rets.mean() / rets.std()) * np.sqrt(bars_per_year)
    else:
        sharpe = 0.0

    n_bars = max(len(equity_curve) - 1, 1)
    years = n_bars / bars_per_year
    # Compute CAGR in log space to avoid overflow on extreme (synthetic) growth,
    # then clamp to a sane display range.
    if years > 0 and end_eq > 0 and start_eq > 0:
        log_growth = np.log(end_eq / start_eq) / years
        cagr = float(np.expm1(min(log_growth, 50.0)))  # cap to avoid inf display
    else:
        cagr = 0.0

    return Metrics(
        n_trades=n,
        win_rate=win_rate,
        avg_win=float(avg_win),
        avg_loss=float(avg_loss),
        expectancy=float(expectancy),
        profit_factor=float(profit_factor),
        total_return=float(total_return),
        max_drawdown=float(max_drawdown),
        sharpe=float(sharpe),
        cagr=float(cagr),
    )
