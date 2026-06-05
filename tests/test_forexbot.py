"""Tests for forexbot: indicators, no-look-ahead, sizing, and the backtester."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forexbot import data as data_mod
from forexbot import indicators as ind
from forexbot.backtest import CostModel, _infer_bars_per_year, run
from forexbot.risk import RiskParams, position_size
from forexbot.strategy import StrategyParams, generate_signals


@pytest.fixture(scope="module")
def df():
    return data_mod.synthetic(n=4000, seed=7)


def test_synthetic_is_deterministic():
    a = data_mod.synthetic(n=500, seed=1)
    b = data_mod.synthetic(n=500, seed=1)
    pd.testing.assert_frame_equal(a, b)


def test_ohlc_invariants(df):
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["low"] <= df["open"]).all()
    assert (df["low"] <= df["close"]).all()


def test_rsi_bounds(df):
    r = ind.rsi(df["close"], 14)
    assert r.min() >= 0.0 and r.max() <= 100.0


def test_atr_positive(df):
    a = ind.atr(df, 14).dropna()
    assert (a > 0).all()


def test_position_size_risks_fixed_fraction():
    rp = RiskParams(risk_per_trade=0.01)
    units = position_size(10_000, entry=1.10, stop=1.09, rp=rp)
    # Loss if stopped = units * |entry-stop| should equal 1% of equity.
    assert units * abs(1.10 - 1.09) == pytest.approx(100.0, rel=1e-9)


def test_position_size_zero_when_no_stop_distance():
    rp = RiskParams()
    assert position_size(10_000, 1.10, 1.10, rp) == 0.0


def test_signals_have_no_lookahead(df):
    """Signal at bar t must not change if future bars are removed."""
    sp = StrategyParams()
    full = generate_signals(df, sp)
    cut = generate_signals(df.iloc[:1500], sp)
    # Compare the overlapping region (allow the tail few bars for EMA warm-up
    # differences to be irrelevant since both share identical history).
    common = full.index.intersection(cut.index)
    assert (full.loc[common, "signal"] == cut.loc[common, "signal"]).all()


def test_backtest_runs_and_is_reproducible(df):
    r1 = run(df, initial_equity=10_000)
    r2 = run(df, initial_equity=10_000)
    assert r1.metrics.n_trades == r2.metrics.n_trades
    assert r1.equity_curve.iloc[-1] == pytest.approx(r2.equity_curve.iloc[-1])


def test_backtest_equity_never_nan(df):
    r = run(df)
    assert not r.equity_curve.isna().any()


def test_costs_reduce_returns(df):
    cheap = run(df, cost=CostModel(spread_pips=0.0, slippage_pips=0.0))
    pricey = run(df, cost=CostModel(spread_pips=3.0, slippage_pips=2.0))
    if cheap.metrics.n_trades > 0:
        # Higher trading costs must not improve the bottom line.
        assert pricey.equity_curve.iloc[-1] <= cheap.equity_curve.iloc[-1]


def test_win_rate_in_valid_range(df):
    r = run(df)
    assert 0.0 <= r.metrics.win_rate <= 1.0


def test_bars_per_year_resolution_independent():
    """Hourly forex index must map to ~6240 bars/year regardless of dtype unit."""
    idx = pd.date_range("2022-01-01", periods=100, freq="60min", tz="UTC")
    assert _infer_bars_per_year(idx) == pytest.approx(6240.0, rel=1e-6)
    daily = pd.date_range("2022-01-01", periods=100, freq="1D", tz="UTC")
    assert _infer_bars_per_year(daily) == pytest.approx(260.0, rel=1e-6)


def test_metrics_no_overflow_on_compounding(df):
    """CAGR must stay finite even when synthetic equity compounds hugely."""
    r = run(df)
    assert np.isfinite(r.metrics.cagr)
    assert np.isfinite(r.metrics.sharpe)


def test_random_walk_is_not_profitable_after_costs():
    """Sanity: no edge on pure noise once spread is charged (no look-ahead)."""
    rng = np.random.default_rng(0)
    n = 6000
    ret = rng.normal(0, 0.0008, n)
    close = 1.10 * np.exp(np.cumsum(ret))
    openp = np.r_[close[0], close[:-1]]
    wick = np.abs(rng.normal(0, 0.0008, n)) * close
    high = np.maximum(openp, close) + wick
    low = np.minimum(openp, close) - wick
    idx = pd.date_range("2022-01-01", periods=n, freq="60min", tz="UTC")
    rw = pd.DataFrame(
        {"open": openp, "high": high, "low": low, "close": close, "volume": 1000},
        index=idx,
    )
    r = run(rw, cost=CostModel(spread_pips=1.0))
    assert r.metrics.total_return < 0.10  # must not magically profit on noise
