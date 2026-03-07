"""
Backtest — walks forward bar-by-bar, orchestrating strategy signals,
risk management, and broker order execution.
"""

from __future__ import annotations
import pandas as pd

from strategies.base import Strategy
from engines.broker import Broker
from engines.risk_manager import RiskManager


class Backtest:
    """
    Event-driven backtest engine.

    Parameters
    ----------
    df           : pd.DataFrame  — OHLCV data indexed by date
    strategy     : Strategy      — any subclass of Strategy
    broker       : Broker        — handles order execution & cash
    risk_manager : RiskManager   — handles position sizing & stop-loss
    symbol       : str           — ticker symbol (informational)
    """

    def __init__(
        self,
        df:           pd.DataFrame,
        strategy:     Strategy,
        broker:       Broker,
        risk_manager: RiskManager,
        symbol:       str = "UNKNOWN",
    ):
        self.df           = df.copy()
        self.strategy     = strategy
        self.broker       = broker
        self.risk_manager = risk_manager
        self.symbol       = symbol

        # Equity curve — one value per bar
        self.equity_curve: list[float] = []

    # ──────────────────────────────────────────
    # Run
    # ──────────────────────────────────────────

    def run(self) -> dict:
        """
        Execute the backtest.

        Returns a results dict with:
            equity_curve, dates, trade_log, and broker summary stats.
        """
        required = self.strategy.required_bars()
        df       = self.df

        for i in range(len(df)):
            price = df["close"].iloc[i]
            date  = df.index[i]

            # ── Stop-loss check (before signal) ──
            if self.broker.is_in_position():
                entry = self.broker.position.entry_price
                if self.risk_manager.is_stop_loss_hit(entry, price):
                    self.broker.sell(self.symbol, price, date, reason="STOP-LOSS")
                elif self.risk_manager.is_target_hit(entry, price):
                    self.broker.sell(self.symbol, price, date, reason="TARGET")

            # ── Strategy signal ──────────────────
            if i >= required:
                window = df.iloc[: i + 1]
                signal = self.strategy.generate_signal(window)

                if signal == 1 and not self.broker.is_in_position():
                    capital = self.broker.portfolio_value(price)
                    shares  = self.risk_manager.calculate_shares(capital, price)
                    self.broker.buy(self.symbol, shares, price, date)

                elif signal == -1 and self.broker.is_in_position():
                    self.broker.sell(self.symbol, price, date, reason="SELL")

            # ── Record equity at this bar ────────
            self.equity_curve.append(self.broker.portfolio_value(price))

        # ── Close any open position at last bar ──
        if self.broker.is_in_position():
            last_price = df["close"].iloc[-1]
            last_date  = df.index[-1]
            self.broker.sell(self.symbol, last_price, last_date, reason="SELL (close)")

        # ── Build results ────────────────────────
        summary = self.broker.summary()
        summary.update({
            "symbol":       self.symbol,
            "strategy":     self.strategy.name,
            "initial_cap":  self.broker.initial_capital,
            "final_value":  round(self.broker.portfolio_value(), 2),
            "return_pct":   round(
                (self.broker.portfolio_value() - self.broker.initial_capital)
                / self.broker.initial_capital * 100, 2
            ),
            "equity_curve": self.equity_curve,
            "dates":        list(df.index),
            "trade_log":    self.broker.trade_log,
        })
        return summary
