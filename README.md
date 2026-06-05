# forexbot — an honest forex trading bot

A small, well-engineered forex trading bot in Python with a **rigorous,
cost-aware backtester**, a trend-following strategy, fixed-fractional risk
management, and a paper-trading loop. Live trading via OANDA is scaffolded
behind deliberate safety gates.

---

## ⚠️ Read this first: about "80–100% win rate"

You asked for an 80–100% win rate. I have to be straight with you, because it
is your money on the line:

**No forex bot can reliably deliver an 80–100% win rate. Anyone who promises
that is selling something.** Here is the reasoning, not just the assertion:

- **Win rate ≠ profitability.** A bot can win 90% of trades and still blow up
  the account if the losers are large. What matters is *expectancy*
  (`avg_win × win% − avg_loss × loss%`) and risk-adjusted return.
- **High win rates usually hide risk.** The easy way to fake a 90% win rate is
  martingale / grid / no-stop-loss systems: they win small repeatedly, then one
  trade wipes the account. This bot contains **none** of that by design.
- **Backtests lie if you let them.** Overfitting, look-ahead bias, and ignoring
  spread/slippage/commission turn garbage into a "money printer" on paper. This
  backtester is built to *avoid* those traps, so its numbers are realistic
  (and therefore humbler than the fantasy ones).

**Realistic expectation:** good trend-following strategies typically win
**~40–55% of trades** and make money through reward:risk > 1 (winners bigger
than losers). That is the honest target. This repo aims for *durable,
risk-controlled* performance — not a fake win-rate headline.

### Proof this backtester is honest, not rigged

Two self-checks (run as tests):

- On a **pure random walk** (no real edge), the strategy lands near its
  break-even win rate and **loses after spread** — exactly as it should. If it
  "won" on noise, that would prove a look-ahead bug.
- On data with **genuine trends**, it captures them and turns a profit.

So the engine only makes money when real structure exists — it cannot
manufacture an edge from nothing.

---

## What's in here

```
forexbot/
  data.py         Historical data: yfinance → CSV cache → synthetic fallback
  indicators.py   EMA, RSI, ATR, ADX (no look-ahead)
  strategy.py     Trend-following: pullback + Donchian breakout, ATR exits
  risk.py         Fixed-fractional position sizing
  backtest.py     Bar-by-bar backtester w/ spread, slippage, commission
  metrics.py      Win rate, expectancy, profit factor, Sharpe, drawdown, CAGR
  broker.py       PaperBroker (sim) + OandaBroker (gated live scaffold)
  live.py         Paper/live trading loop
run_backtest.py   CLI backtest runner
run_live.py       CLI paper-trading runner
tests/            14 tests incl. no-look-ahead & no-edge-on-noise checks
config.yaml       All tunable knobs in one place
```

## Install

```bash
pip install -r requirements.txt
```

## Quick start

```bash
# Backtest on real EURUSD hourly data (needs Yahoo Finance reachable):
python run_backtest.py --symbol EURUSD=X --interval 1h --period 2y --plot equity.png

# No network? Run the offline engine smoke-test on synthetic data:
python run_backtest.py --synthetic

# Use your own CSV (datetime index + open,high,low,close[,volume]):
python run_backtest.py --csv mydata.csv

# Forward-test with simulated money (PaperBroker — no real funds at risk):
python run_live.py --iterations 5 --poll 2
```

### Example output (synthetic data — illustrative only)

```
Trades:        259
Win rate:      54.1%
Expectancy:    91.54   (per trade; >0 is good)
Profit factor: 2.19    (>1 is profitable)
Total return:  237.1%
Max drawdown:  -15.1%
Sharpe:        5.35    (annualized)
```

> These synthetic numbers exist to validate the *engine*, not to predict
> profit. Real markets are noisier; expect more modest results. **Always
> re-run on real data before drawing conclusions.**

## The strategy (plain English)

1. **Trend filter** — only trade with the trend: fast EMA vs slow EMA, and only
   when ADX confirms the trend is actually strong (avoids chop).
2. **Entry** — either a *pullback re-entry* (price dips to the fast EMA then
   reclaims it) or a *Donchian breakout* (price clears the recent range).
3. **Exit** — stop-loss and take-profit set from ATR, so they adapt to
   volatility. Take-profit is a multiple of the stop (default reward:risk 2.0).
4. **Sizing** — risk a fixed fraction (default **1%**) of equity per trade, so
   no single loss can hurt you much. Position size is derived from the stop
   distance.

Tune everything in `config.yaml` or via CLI flags / dataclass params.

## How costs & realism are modelled

- **Spread:** half the bid/ask spread charged against every entry and exit.
- **Slippage:** configurable adverse pips on each fill.
- **Commission:** optional per-fill cost.
- **No look-ahead:** a signal computed on bar *t* is filled at the **open of
  bar t+1**. Donchian levels are shifted so a bar can't break out of its own range.
- **Conservative intrabar exits:** if both stop and target are touchable in one
  bar, the **stop** is assumed to hit first.

## Data note for this environment

This sandbox's network policy blocks Yahoo Finance (`Host not in allowlist`), so
live `yfinance` pulls fail *here* and the loader falls back to synthetic data.
On **your** machine, `yfinance` works normally — just run the commands above.

## Path to live trading (do this in order — don't skip)

1. **Backtest** on 2+ years of real data across several pairs. Look at
   expectancy, profit factor, drawdown — not just win rate.
2. **Walk-forward / out-of-sample test** — tune on older data, validate on
   newer data you never touched. If it only works on the tuning set, it's
   overfit.
3. **Paper trade** on a broker demo account (`OandaBroker`, `OANDA_ENV=practice`)
   for weeks. Confirm live spreads/slippage match your assumptions.
4. **Go live tiny.** `OandaBroker` requires `OANDA_ENV=live` **and**
   `allow_live=True` — a deliberate double gate so you can't risk real money by
   accident. Start with the smallest size your broker allows.

A production system still needs: reconnection/error handling, fill confirmation,
a kill switch, and logging/alerting. This repo is an honest, solid foundation —
not a turnkey money machine. Trade responsibly; never risk money you can't lose.

## Tests

```bash
pytest -q
```

## Disclaimer

For education and research. Forex/CFD trading carries substantial risk of loss
and is not suitable for everyone. Nothing here is financial advice. Past (or
backtested) performance does not guarantee future results.
