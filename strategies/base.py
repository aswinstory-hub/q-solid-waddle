from abc import ABC, abstractmethod
import pandas as pd


class Strategy(ABC):
    """
    Base class for all trading strategies.
    """

    def __init__(self, name: str, timeframe: str):
        self.name = name
        self.timeframe = timeframe

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> int:
        """
        Parameters:
            data : pd.DataFrame
                Historical OHLCV data up to the current candle.

        Returns:
            1   -> Long / Buy
            -1  -> Exit / Sell
            0   -> Hold / Do nothing
        """
        pass

    def required_bars(self) -> int:
        """
        Minimum bars needed before strategy can act.
        Override if needed.
        """
        return 50