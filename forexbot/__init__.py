"""forexbot - an honest, well-engineered forex trading bot.

Modules:
    data        Historical data (yfinance, CSV cache, synthetic fallback)
    indicators  Technical indicators (EMA, RSI, ATR, ...)
    strategy    Signal generation (trend-pullback strategy)
    risk        Position sizing and risk management
    backtest    Realistic bar-by-bar backtester (spread, slippage, costs)
    metrics     Performance metrics (win rate, expectancy, Sharpe, drawdown)
    broker      Broker abstraction (paper broker + OANDA scaffold)
    live        Live/paper trading loop
"""

__version__ = "0.1.0"
