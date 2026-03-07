from .ema_crossover import EMACrossover
from .my_strategy   import MyStrategy

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
# Add every new strategy here.
# run.py reads this dict to show the strategy selection menu automatically.
#
# Format:
#   "Display Name": StrategyClass
#
# Example — after you build an RSI strategy:
#   from .rsi_strategy import RSIStrategy
#   STRATEGY_REGISTRY["RSI Strategy"] = RSIStrategy
# ─────────────────────────────────────────────────────────────────────────────

STRATEGY_REGISTRY: dict = {
    "EMA Crossover": EMACrossover,
    # "My Strategy":  MyStrategy,   ← uncomment when you're ready to test yours
}

__all__ = [
    "EMACrossover",
    "MyStrategy",
    "STRATEGY_REGISTRY",
]
