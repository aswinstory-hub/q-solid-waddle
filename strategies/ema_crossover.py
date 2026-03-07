import pandas as pd
from .base import Strategy


class EMACrossover(Strategy):
    """
    EMA Crossover Strategy.

    Generates a Buy signal when the fast EMA crosses above the slow EMA,
    and a Sell signal when it crosses below.

    Parameters (configurable via PARAMS)
    -------------------------------------
    fast : int   — fast EMA period  (default 9)
    slow : int   — slow EMA period  (default 21)
    """

    # ── Declare configurable parameters ───────────────────────────────────────
    PARAMS = {
        "fast": {
            "label":   "Fast EMA Period",
            "type":    int,
            "default": 9,
        },
        "slow": {
            "label":   "Slow EMA Period",
            "type":    int,
            "default": 21,
        },
    }

    # ── Risk parameters ────────────────────────────────────────────────────────
    position_size_pct: float = 0.10   # 10% of capital per trade
    stop_loss_pct:     float = 0.02   # exit if price drops 2% from entry
    target_pct:        float = 0.05   # exit if price rises 5% from entry

    def __init__(self, fast: int = 9, slow: int = 21, timeframe: str = "1d"):
        super().__init__(name="EMA_Crossover", timeframe=timeframe)
        self.fast = fast
        self.slow = slow

    def required_bars(self) -> int:
        return max(self.fast, self.slow) + 2

    def generate_signal(self, data: pd.DataFrame) -> int:
        if len(data) < self.required_bars():
            return 0

        df = data.copy()
        df["ema_fast"] = df["close"].ewm(span=self.fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.slow, adjust=False).mean()

        prev_fast = df["ema_fast"].iloc[-2]
        prev_slow = df["ema_slow"].iloc[-2]
        curr_fast = df["ema_fast"].iloc[-1]
        curr_slow = df["ema_slow"].iloc[-1]

        # Bullish crossover → Buy
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return 1

        # Bearish crossover → Sell
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return -1

        return 0