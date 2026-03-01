import pandas as pd
from strategies.base import Strategy


class EMACrossover(Strategy):
    def __init__(self, fast=9, slow=21, timeframe="5m"):
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

        # Bullish crossover
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return 1

        # Bearish crossover (exit)
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return -1

        return 0