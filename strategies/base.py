from abc import ABC, abstractmethod
import pandas as pd


class Strategy(ABC):
    """
    Base class for all trading strategies.

    To create a new strategy:
      1. Create strategies/your_strategy.py
      2. Subclass Strategy
      3. Define PARAMS (your configurable inputs)
      4. Define position_size_pct and stop_loss_pct
      5. Implement generate_signal()
      6. Register in strategies/__init__.py

    See strategies/my_strategy.py for a full template.
    """

    # ── Risk parameters (override in subclass) ────────────────────────────────
    position_size_pct: float = 0.10   # fraction of capital per trade (10%)
    stop_loss_pct:     float = 0.02   # stop-loss trigger (2%)
    target_pct:        float = 0.10   # profit target (10%) — set None to disable

    # ── Parameter declarations (override in subclass) ─────────────────────────
    # Format:
    #   PARAMS = {
    #       "param_name": {
    #           "label":   "Human readable label",
    #           "type":    int | float,
    #           "default": <value>,
    #       },
    #       ...
    #   }
    PARAMS: dict = {}

    def __init__(self, name: str, timeframe: str = "1d"):
        self.name      = name
        self.timeframe = timeframe

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> int:
        """
        Called on every bar with all historical data up to and including
        the current bar.

        Parameters
        ----------
        data : pd.DataFrame
            OHLCV data with columns: open, high, low, close, volume
            Indexed by date (ascending).

        Returns
        -------
        int
             1  → Buy  / Enter long
            -1  → Sell / Exit long
             0  → Hold / No action
        """
        pass

    def required_bars(self) -> int:
        """
        Minimum number of bars needed before the strategy can produce a signal.
        Override this if your strategy needs a warm-up period.
        Default: 50 bars.
        """
        return 50