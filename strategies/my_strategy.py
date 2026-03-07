"""
my_strategy.py — Template for building a custom strategy.

HOW TO USE THIS TEMPLATE
─────────────────────────
1. Copy this file and rename it: e.g. strategies/rsi_strategy.py
2. Rename the class: e.g. class RSIStrategy(Strategy)
3. Fill in PARAMS, position_size_pct, stop_loss_pct
4. Implement generate_signal()
5. Register it in strategies/__init__.py:
       from .rsi_strategy import RSIStrategy
       STRATEGY_REGISTRY["RSI Strategy"] = RSIStrategy

That's it — run.py will automatically pick it up!
"""

import pandas as pd
from .base import Strategy


class MyStrategy(Strategy):
    """
    [Replace this with a description of your strategy.]

    Strategy Logic:
        - Buy when  : [describe your entry condition]
        - Sell when : [describe your exit condition]
        - Hold when : [describe when you do nothing]
    """

    # ── Step 1: Declare your configurable parameters ───────────────────────────
    #
    # The run.py script reads this dict and automatically prompts the user
    # to enter values for each parameter before running the backtest.
    #
    # Format for each entry:
    #   "param_name": {
    #       "label":   "Human-readable name shown in the prompt",
    #       "type":    int | float,           ← used to cast the user's input
    #       "default": <value>,               ← used if user presses Enter
    #   }
    #
    # Example — uncomment and customise:
    # PARAMS = {
    #     "period": {
    #         "label":   "RSI Period",
    #         "type":    int,
    #         "default": 14,
    #     },
    #     "overbought": {
    #         "label":   "Overbought Level",
    #         "type":    float,
    #         "default": 70.0,
    #     },
    #     "oversold": {
    #         "label":   "Oversold Level",
    #         "type":    float,
    #         "default": 30.0,
    #     },
    # }
    PARAMS: dict = {}

    # ── Step 2: Set risk parameters ────────────────────────────────────────────
    #
    # These are read by RiskManager to size positions and set stop-losses.
    # Adjust to match your strategy's risk tolerance.
    position_size_pct: float = 0.10   # Allocate 10% of capital per trade
    stop_loss_pct:     float = 0.02   # Exit if price drops 2% from entry

    # ── Step 3: Define __init__ ────────────────────────────────────────────────
    #
    # Accept the same parameter names you declared in PARAMS above.
    # Pass a descriptive name and timeframe to super().__init__().
    def __init__(self, timeframe: str = "1d"):
        super().__init__(name="My_Strategy", timeframe=timeframe)

        # Example — store your params as instance attributes:
        # self.period     = period
        # self.overbought = overbought
        # self.oversold   = oversold

    # ── Step 4: Set the warm-up bar count ─────────────────────────────────────
    #
    # Return the minimum number of bars your strategy needs before it can
    # generate a meaningful signal (e.g. your longest indicator period + buffer).
    def required_bars(self) -> int:
        return 50   # ← change this to match your longest indicator

    # ── Step 5: Implement generate_signal ─────────────────────────────────────
    #
    # This is called on every bar during the backtest.
    # `data` contains all historical OHLCV bars up to and including today.
    #
    # Columns available: open, high, low, close, volume
    # Index: datetime (ascending)
    #
    # Return:
    #    1  → Buy  (open a long position)
    #   -1  → Sell (close the long position)
    #    0  → Hold (do nothing)
    def generate_signal(self, data: pd.DataFrame) -> int:
        # Guard: not enough data yet
        if len(data) < self.required_bars():
            return 0

        # Work on a copy — never modify the original DataFrame
        df = data.copy()

        # ── Compute your indicators here ───────────────────────────────────
        #
        # Example (RSI):
        #   delta   = df["close"].diff()
        #   gain    = delta.clip(lower=0)
        #   loss    = (-delta).clip(lower=0)
        #   avg_g   = gain.ewm(span=self.period, adjust=False).mean()
        #   avg_l   = loss.ewm(span=self.period, adjust=False).mean()
        #   rs      = avg_g / avg_l
        #   df["rsi"] = 100 - (100 / (1 + rs))
        #
        # ── Access the latest values ───────────────────────────────────────
        #
        #   current  = df["rsi"].iloc[-1]    ← current bar
        #   previous = df["rsi"].iloc[-2]    ← previous bar
        #
        # ── Return signals ─────────────────────────────────────────────────
        #
        # Example:
        #   if previous >= self.oversold and current < self.oversold:
        #       return 1   # crossed into oversold → Buy
        #
        #   if previous <= self.overbought and current > self.overbought:
        #       return -1  # crossed into overbought → Sell
        #
        #   return 0       # no signal

        # ── Replace this with your actual logic ────────────────────────────
        return 0
