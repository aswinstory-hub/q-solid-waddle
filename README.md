# Quant — Python Backtesting Framework

A clean, extensible backtesting system for Indian equity markets (NSE), built with Python, DuckDB, and Matplotlib.

---

## Project Structure

```
Quant/
├── run.py                  # Entry point — runs the full backtest interactively
├── data_loader.py          # Downloads and updates price data into DuckDB
├── utils.py                # Shared helpers: DB_PATH, load_tickers, ask_symbol
├── tickers.txt             # NSE ticker symbols (one per line, without .NS)
├── prices.db               # DuckDB database storing all OHLCV price data
│
├── strategies/
│   ├── __init__.py         # STRATEGY_REGISTRY — register new strategies here
│   ├── base.py             # Abstract base class all strategies must inherit
│   ├── ema_crossover.py    # EMA Crossover strategy (built-in)
│   └── my_strategy.py      # Template — copy this to build your own strategy
│
└── engines/
    ├── __init__.py         # Package exports
    ├── s_backtest.py       # Backtest class — bar-by-bar simulation engine
    ├── broker.py           # Broker class — simulates order execution
    ├── risk_manager.py     # RiskManager — position sizing, stop-loss, target
    └── metrics.py          # Performance metrics (Sharpe, Sortino, CAGR, etc.)
```

---

## Quickstart

### 1. Update price data
```bash
python data_loader.py
```
Downloads the latest OHLCV data for all tickers in `tickers.txt` and stores them in `prices.db`.

### 2. Run a backtest
```bash
python run.py
```
You will be prompted to:
- Select a strategy
- Configure strategy parameters (e.g. EMA fast/slow periods)
- Set capital, position size, stop-loss, and max risk per trade
- Pick a symbol from the available tickers

The backtest then runs and prints a full metrics summary. You can optionally view the trade log. Three separate chart windows open when done.

---

## How the System Works

### Bar-by-bar simulation
The `Backtest` class walks through price data one bar at a time. On each bar:
1. **Stop-loss check** — if price fell below entry × (1 - stop_loss_pct), sell immediately
2. **Target check** — if price rose above entry × (1 + target_pct), sell immediately
3. **Strategy signal** — call `strategy.generate_signal(data_so_far)` and act on the result

Only **one position** can be open at a time. The `Broker` hard-blocks a second buy if a position is already open.

### Components

| Class | File | Responsibility |
|---|---|---|
| `Backtest` | `engines/s_backtest.py` | Bar loop, coordinates all components |
| `Broker` | `engines/broker.py` | Cash management, order execution, trade log |
| `RiskManager` | `engines/risk_manager.py` | Position sizing, stop-loss, profit target |
| `Strategy` | `strategies/base.py` | Abstract base all strategies subclass |

---

## Performance Metrics

After each backtest the following metrics are computed:

| Metric | Description |
|---|---|
| **CAGR** | Compound Annual Growth Rate |
| **Sharpe Ratio** | Risk-adjusted return (vs 6.5% risk-free rate) |
| **Sortino Ratio** | Like Sharpe, but only penalises downside volatility |
| **Calmar Ratio** | CAGR divided by Max Drawdown |
| **Max Drawdown** | Largest peak-to-trough % drop |
| **Max DD Duration** | Longest time (bars) spent below previous equity high |
| **Volatility** | Annualised standard deviation of daily returns |
| **Profit Factor** | Gross profit ÷ gross loss |
| **Avg Win / Avg Loss** | Average P&L of winning and losing trades |
| **Expectancy** | Weighted average P&L per trade |

---

## Adding a New Strategy

### Step 1 — Copy the template
```bash
cp strategies/my_strategy.py strategies/rsi_strategy.py
```

### Step 2 — Fill in the class
Open `strategies/rsi_strategy.py` and:

```python
class RSIStrategy(Strategy):

    # Declare parameters (shown as prompts in run.py automatically)
    PARAMS = {
        "period": {"label": "RSI Period", "type": int, "default": 14},
        "oversold":   {"label": "Oversold Level",   "type": float, "default": 30.0},
        "overbought": {"label": "Overbought Level",  "type": float, "default": 70.0},
    }

    # Risk parameters (specific to this strategy)
    position_size_pct: float = 0.10
    stop_loss_pct:     float = 0.03   # 3% stop-loss
    target_pct:        float = 0.08   # 8% profit target

    def __init__(self, period=14, oversold=30.0, overbought=70.0, timeframe="1d"):
        super().__init__(name="RSI_Strategy", timeframe=timeframe)
        self.period     = period
        self.oversold   = oversold
        self.overbought = overbought

    def required_bars(self) -> int:
        return self.period + 5

    def generate_signal(self, data: pd.DataFrame) -> int:
        # ... your logic here ...
        return 0
```

### Step 3 — Register it

In `strategies/__init__.py`, add two lines:
```python
from .rsi_strategy import RSIStrategy

STRATEGY_REGISTRY["RSI Strategy"] = RSIStrategy
```

That's it. `run.py` will show it in the strategy menu and automatically prompt for its `PARAMS`.

---

## Risk Parameters (defined per strategy)

Each strategy file sets three class-level attributes:

| Attribute | Default | Description |
|---|---|---|
| `position_size_pct` | `0.10` | Fraction of capital allocated per trade |
| `stop_loss_pct` | `0.02` | Exit if price drops this % from entry |
| `target_pct` | `0.05` | Exit if price rises this % from entry. Set `None` to disable. |

These are read by `RiskManager` automatically — no changes needed anywhere else.

---

## Data Management

Price data is stored in `prices.db` (DuckDB). The `prices` table has columns:

```
symbol | date | open | high | low | close | volume
```

Run `data_loader.py` regularly to keep prices up to date. It only downloads data newer than what's already in the database (incremental update).

---

## Dependencies

```
duckdb
pandas
yfinance
matplotlib
```

Install with:
```bash
pip install duckdb pandas yfinance matplotlib
```
