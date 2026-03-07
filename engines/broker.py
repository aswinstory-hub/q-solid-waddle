"""
Broker — simulates order execution.

Tracks cash, open positions, and a full trade log.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Position:
    symbol:      str
    shares:      int
    entry_price: float
    entry_date:  datetime


@dataclass
class Trade:
    date:    datetime
    action:  str        # "BUY" | "SELL" | "STOP-LOSS"
    symbol:  str
    price:   float
    shares:  int
    pnl:     float = 0.0
    cash:    float = 0.0


class Broker:
    """
    Simulates a paper broker.

    Methods
    -------
    buy(symbol, shares, price, date) -> bool
    sell(symbol, price, date, reason) -> bool
    portfolio_value(current_price) -> float
    """

    def __init__(self, initial_capital: float):
        self.initial_capital: float        = initial_capital
        self.cash:            float        = initial_capital
        self.position:        Optional[Position] = None     # single-symbol mode
        self.trade_log:       List[Trade]  = []

    # ──────────────────────────────────────────
    # Orders
    # ──────────────────────────────────────────

    def buy(self, symbol: str, shares: int, price: float, date: datetime) -> bool:
        """Open a long position. Returns False if already in a position or insufficient cash."""
        if self.position is not None:
            print(f"  [Broker] Already in position on {self.position.symbol}. Only one position allowed.")
            return False
        if shares <= 0:
            return False

        cost = shares * price
        if cost > self.cash:
            print(f"  [Broker] Not enough cash (need ₹{cost:,.0f}, have ₹{self.cash:,.0f})")
            return False

        self.cash -= cost
        self.position = Position(
            symbol=symbol,
            shares=shares,
            entry_price=price,
            entry_date=date,
        )
        self.trade_log.append(Trade(
            date=date, action="BUY", symbol=symbol,
            price=price, shares=shares, cash=self.cash,
        ))
        return True

    def sell(
        self,
        symbol: str,
        price: float,
        date: datetime,
        reason: str = "SELL",
    ) -> bool:
        """Close the current position. Returns False if no open position."""
        if self.position is None or self.position.symbol != symbol:
            return False

        pos      = self.position
        proceeds = pos.shares * price
        pnl      = proceeds - (pos.shares * pos.entry_price)
        self.cash   += proceeds
        self.position = None

        self.trade_log.append(Trade(
            date=date, action=reason, symbol=symbol,
            price=price, shares=pos.shares,
            pnl=round(pnl, 2), cash=round(self.cash, 2),
        ))
        return True

    # ──────────────────────────────────────────
    # Portfolio
    # ──────────────────────────────────────────

    def portfolio_value(self, current_price: float = 0.0) -> float:
        """Total value = cash + mark-to-market value of open position."""
        value = self.cash
        if self.position is not None:
            value += self.position.shares * current_price
        return value

    def is_in_position(self) -> bool:
        return self.position is not None

    # ──────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────

    def summary(self) -> dict:
        sells      = [t for t in self.trade_log if t.action in ("SELL", "STOP-LOSS", "TARGET", "SELL (close)")]
        wins       = [t for t in sells if t.pnl > 0]
        total_pnl  = sum(t.pnl for t in sells)
        win_rate   = (len(wins) / len(sells) * 100) if sells else 0.0

        return {
            "total_trades": len(sells),
            "wins":         len(wins),
            "losses":       len(sells) - len(wins),
            "win_rate":     round(win_rate, 1),
            "total_pnl":    round(total_pnl, 2),
            "final_cash":   round(self.cash, 2),
        }
