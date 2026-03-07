"""
RiskManager — enforces position sizing and stop-loss rules.

Reads position_size_pct and stop_loss_pct directly from the strategy object,
so each strategy can define its own risk parameters.
"""

from __future__ import annotations
from strategies.base import Strategy


class RiskManager:
    """
    Calculates position sizes and determines when to trigger a stop-loss.

    Parameters are sourced from the strategy if available, with fallback defaults.

    Attributes
    ----------
    position_size_pct : float
        Fraction of current capital to allocate per trade (e.g. 0.10 = 10%).
    stop_loss_pct : float
        Maximum allowed loss from entry before stop-loss is triggered (e.g. 0.02 = 2%).
    max_risk_per_trade : float
        Hard cap on ₹ amount risked per single trade.
    """

    DEFAULT_POSITION_SIZE = 0.10   # 10%
    DEFAULT_STOP_LOSS     = 0.02   # 2%
    DEFAULT_MAX_RISK      = 10_000 # ₹10,000

    def __init__(
        self,
        strategy:           Strategy,
        max_risk_per_trade: float = DEFAULT_MAX_RISK,
    ):
        # Pull risk params directly from the strategy (with fallbacks)
        self.position_size_pct: float = getattr(
            strategy, "position_size_pct", self.DEFAULT_POSITION_SIZE
        )
        self.stop_loss_pct: float = getattr(
            strategy, "stop_loss_pct", self.DEFAULT_STOP_LOSS
        )
        self.target_pct = getattr(strategy, "target_pct", None)   # None = disabled
        self.max_risk_per_trade: float = max_risk_per_trade

    # ──────────────────────────────────────────
    # Position Sizing
    # ──────────────────────────────────────────

    def calculate_shares(self, capital: float, price: float) -> int:
        """
        Calculate number of shares to buy given current capital and price.

        Uses position_size_pct and caps by max_risk_per_trade.

        Returns 0 if the price is 0 or capital is insufficient.
        """
        if price <= 0 or capital <= 0:
            return 0

        alloc_by_pct    = capital * self.position_size_pct
        alloc_by_risk   = self.max_risk_per_trade / self.stop_loss_pct  # max $$ at risk → position size
        allocation      = min(alloc_by_pct, alloc_by_risk)

        shares = int(allocation // price)
        return shares

    # ──────────────────────────────────────────
    # Stop-Loss
    # ──────────────────────────────────────────

    def is_stop_loss_hit(self, entry_price: float, current_price: float) -> bool:
        """Returns True if current price has fallen stop_loss_pct below entry."""
        if entry_price <= 0:
            return False
        loss_pct = (current_price - entry_price) / entry_price
        return loss_pct <= -self.stop_loss_pct

    def is_target_hit(self, entry_price: float, current_price: float) -> bool:
        """Returns True if current price has risen target_pct above entry. False if target disabled."""
        if self.target_pct is None or entry_price <= 0:
            return False
        gain_pct = (current_price - entry_price) / entry_price
        return gain_pct >= self.target_pct

    # ──────────────────────────────────────────
    # Info
    # ──────────────────────────────────────────

    def __repr__(self) -> str:
        target_str = f"{self.target_pct*100:.0f}%" if self.target_pct else "off"
        return (
            f"RiskManager("
            f"position_size={self.position_size_pct*100:.0f}%, "
            f"stop_loss={self.stop_loss_pct*100:.0f}%, "
            f"target={target_str}, "
            f"max_risk=₹{self.max_risk_per_trade:,.0f})"
        )
