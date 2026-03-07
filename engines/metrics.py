"""
metrics.py — Computes performance metrics from a backtest equity curve.

Metrics
-------
    CAGR            : Compound Annual Growth Rate
    Sharpe Ratio    : Annualised (risk-free rate = 6.5% for India)
    Sortino Ratio   : Annualised (downside deviation only)
    Max Drawdown    : Peak-to-trough % drop
    Calmar Ratio    : CAGR / |Max Drawdown|
    Volatility      : Annualised standard deviation of daily returns
    Profit Factor   : Gross profit / |Gross loss|
    Avg Win / Loss  : Mean P&L of winning and losing trades
    Expectancy      : Weighted average P&L per trade
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Optional


TRADING_DAYS    = 252
RISK_FREE_RATE  = 0.065   # 6.5% (approximate India RBI repo rate)


def compute_metrics(
    equity_curve:    List[float],
    dates:           list,
    initial_capital: float,
    trade_pnls:      Optional[List[float]] = None,
) -> dict:
    """
    Parameters
    ----------
    equity_curve    : portfolio value at each bar
    dates           : corresponding datetime index
    initial_capital : starting capital in ₹
    trade_pnls      : list of P&L values for each closed trade (optional)

    Returns
    -------
    dict of computed metric values
    """
    eq      = pd.Series(equity_curve, index=pd.to_datetime(dates))
    returns = eq.pct_change().dropna()

    # ── CAGR ─────────────────────────────────────────────────────────────────
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    if years > 0 and initial_capital > 0:
        cagr = ((eq.iloc[-1] / initial_capital) ** (1.0 / years) - 1.0) * 100
    else:
        cagr = 0.0

    # ── Sharpe ───────────────────────────────────────────────────────────────
    rf_daily    = RISK_FREE_RATE / TRADING_DAYS
    excess_ret  = returns - rf_daily
    ann_std     = returns.std() * np.sqrt(TRADING_DAYS)
    sharpe      = (excess_ret.mean() / returns.std() * np.sqrt(TRADING_DAYS)
                   if returns.std() > 0 else 0.0)

    # ── Sortino ──────────────────────────────────────────────────────────────
    neg_returns  = returns[returns < 0]
    downside_std = neg_returns.std() * np.sqrt(TRADING_DAYS) if len(neg_returns) > 1 else 0.0
    sortino      = (excess_ret.mean() * TRADING_DAYS / (downside_std)
                    if downside_std > 0 else 0.0)

    # ── Drawdown ─────────────────────────────────────────────────────────────
    roll_max     = eq.cummax()
    drawdown_ser = (eq - roll_max) / roll_max * 100
    max_dd       = drawdown_ser.min()   # negative value

    # Max drawdown duration (consecutive bars below previous high)
    underwater         = drawdown_ser < 0
    dd_dur             = 0
    max_dd_dur         = 0
    for u in underwater:
        dd_dur = dd_dur + 1 if u else 0
        max_dd_dur = max(max_dd_dur, dd_dur)

    # ── Calmar ───────────────────────────────────────────────────────────────
    calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0.0

    # ── Trade-level metrics ───────────────────────────────────────────────────
    if trade_pnls:
        wins       = [p for p in trade_pnls if p > 0]
        losses     = [p for p in trade_pnls if p < 0]
        gross_win  = sum(wins)
        gross_loss = abs(sum(losses))

        profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")
        avg_win       = float(np.mean(wins))   if wins   else 0.0
        avg_loss      = float(np.mean(losses)) if losses else 0.0
        expectancy    = float(np.mean(trade_pnls))
    else:
        profit_factor = None
        avg_win       = None
        avg_loss      = None
        expectancy    = None

    return {
        "cagr":              round(cagr,          2),
        "sharpe":            round(sharpe,         2),
        "sortino":           round(sortino,        2),
        "volatility_pct":    round(ann_std * 100,  2),
        "max_drawdown_pct":  round(max_dd,         2),
        "max_dd_duration":   max_dd_dur,
        "calmar":            round(calmar,          2),
        "profit_factor":     round(profit_factor, 2) if profit_factor is not None else None,
        "avg_win":           round(avg_win,  2)  if avg_win  is not None else None,
        "avg_loss":          round(avg_loss, 2)  if avg_loss is not None else None,
        "expectancy":        round(expectancy, 2) if expectancy is not None else None,
    }
