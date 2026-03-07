"""
run.py — Entry point for the backtesting system.

Flow
────
  1. Select a strategy
  2. Configure strategy parameters (read from strategy's PARAMS dict)
  3. Configure general settings (capital, risk)
  4. Pick a symbol
  5. Load OHLCV data from DuckDB
  6. Run backtest (single position, stop-loss + target enforced each bar)
  7. Print metrics summary + optional trade log
  8. Show 3 separate chart windows: Equity, Price+Signals, Drawdown
"""

import sys
import os
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from utils               import DB_PATH, ask_symbol
from strategies          import STRATEGY_REGISTRY
from engines             import Backtest, Broker, RiskManager, compute_metrics


# ─────────────────────────────────────────────────────────────────────────────
# Colours (shared across all charts)
# ─────────────────────────────────────────────────────────────────────────────
BG    = "#0d1117"
PANEL = "#161b22"
GRID  = "#21262d"
TEXT  = "#c9d1d9"
GREEN = "#3fb950"
RED   = "#f85149"
BLUE  = "#58a6ff"
AMBER = "#e3b341"
TEAL  = "#39d353"
MUTED = "#6e7681"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ask_float(prompt: str, default: float) -> float:
    raw = input(f"  {prompt} (default {default}): ").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        print(f"    Invalid. Using default: {default}")
        return default


def _ask_int(prompt: str, default: int) -> int:
    raw = input(f"  {prompt} (default {default}): ").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        print(f"    Invalid. Using default: {default}")
        return default


def _style_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.grid(color=GRID, linewidth=0.4, alpha=0.8)


# ─────────────────────────────────────────────────────────────────────────────
# Strategy selection
# ─────────────────────────────────────────────────────────────────────────────

def ask_strategy():
    names = list(STRATEGY_REGISTRY.keys())
    SEP   = "─" * 48
    print(f"\n{SEP}")
    print("  Select a Strategy")
    print(SEP)
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    print()
    while True:
        raw = input(f"  Enter number (1–{len(names)}): ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(names):
                chosen = names[idx]
                print(f"  → {chosen} selected.\n")
                return STRATEGY_REGISTRY[chosen]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(names)}.")


# ─────────────────────────────────────────────────────────────────────────────
# Strategy parameter prompts (auto-reads PARAMS dict from the strategy)
# ─────────────────────────────────────────────────────────────────────────────

def ask_strategy_params(strategy_cls) -> dict:
    if not strategy_cls.PARAMS:
        return {}
    SEP = "─" * 48
    print(f"{SEP}")
    print(f"  {strategy_cls.__name__} — Strategy Parameters")
    print(SEP)
    print("  Press Enter to keep the default value.\n")
    params = {}
    for key, meta in strategy_cls.PARAMS.items():
        raw = input(f"  {meta['label']} (default {meta['default']}): ").strip()
        try:
            params[key] = meta["type"](raw) if raw else meta["default"]
        except ValueError:
            print(f"    Invalid. Using default: {meta['default']}")
            params[key] = meta["default"]
    print()
    return params


# ─────────────────────────────────────────────────────────────────────────────
# General config
# ─────────────────────────────────────────────────────────────────────────────

def ask_config(strategy_cls) -> dict:
    SEP = "─" * 48
    print(f"{SEP}")
    print("  General Configuration")
    print(SEP)
    print("  Press Enter to keep the default value.\n")

    default_pos = int(getattr(strategy_cls, "position_size_pct", 0.10) * 100)
    default_sl  = int(getattr(strategy_cls, "stop_loss_pct",     0.02) * 100)

    capital  = _ask_float("Initial Capital (₹)",        100_000)
    pos_pct  = _ask_float("Position Size % (e.g. 10)",  default_pos) / 100
    sl_pct   = _ask_float("Stop-Loss % (e.g. 2)",       default_sl)  / 100
    max_risk = _ask_float("Max Risk per Trade (₹)",      10_000)

    print(f"\n{SEP}")
    print(f"  Capital     : ₹{capital:,.0f}")
    print(f"  Position Sz : {pos_pct*100:.0f}%     Stop-Loss : {sl_pct*100:.0f}%")
    print(f"  Max Risk    : ₹{max_risk:,.0f}")
    print(f"{SEP}\n")

    return {
        "capital":           capital,
        "position_size_pct": pos_pct,
        "stop_loss_pct":     sl_pct,
        "max_risk":          max_risk,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data(symbol: str) -> pd.DataFrame:
    con = duckdb.connect(DB_PATH)
    try:
        df = con.execute("""
            SELECT date, open, high, low, close, volume
            FROM prices
            WHERE symbol = ?
            ORDER BY date ASC
        """, [symbol + ".NS"]).fetchdf()
    finally:
        con.close()

    if df.empty:
        raise ValueError(f"No data found for '{symbol}' in the database.")

    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)

    # Drop rows where close is NaN (e.g. stocks listed after DB start date)
    df = df.dropna(subset=["close"])

    if df.empty:
        raise ValueError(f"No valid price data for '{symbol}' after dropping NaN rows.")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Print summary
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: dict, metrics: dict) -> None:
    SEP  = "═" * 52
    SEP2 = "─" * 52

    print(f"\n{SEP}")
    print(f"  {'BACKTEST RESULTS':^50}")
    print(SEP)
    print(f"  Symbol        : {results['symbol']}")
    print(f"  Strategy      : {results['strategy']}")
    print(f"  Initial cap   : ₹{results['initial_cap']:>12,.0f}")
    print(f"  Final value   : ₹{results['final_value']:>12,.2f}")
    print(f"  Total return  : {results['return_pct']:>+12.2f}%")
    print(SEP2)
    print(f"  {'PERFORMANCE METRICS':^50}")
    print(SEP2)
    print(f"  CAGR          : {metrics['cagr']:>+10.2f}%")
    print(f"  Volatility    : {metrics['volatility_pct']:>10.2f}%")
    print(f"  Sharpe Ratio  : {metrics['sharpe']:>10.2f}")
    print(f"  Sortino Ratio : {metrics['sortino']:>10.2f}")
    print(f"  Calmar Ratio  : {metrics['calmar']:>10.2f}")
    print(f"  Max Drawdown  : {metrics['max_drawdown_pct']:>+10.2f}%")
    print(f"  Max DD Dur.   : {metrics['max_dd_duration']:>10} bars")
    print(SEP2)
    print(f"  {'TRADE STATISTICS':^50}")
    print(SEP2)
    print(f"  Total Trades  : {results['total_trades']:>10}")
    print(f"  Wins / Losses : {results['wins']:>4} / {results['losses']:<4}")
    print(f"  Win Rate      : {results['win_rate']:>10.1f}%")
    if metrics["profit_factor"] is not None:
        pf     = metrics["profit_factor"]
        pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"
        print(f"  Profit Factor : {pf_str:>10}")
    if metrics["avg_win"] is not None:
        print(f"  Avg Win       : ₹{metrics['avg_win']:>11,.2f}")
        print(f"  Avg Loss      : ₹{metrics['avg_loss']:>11,.2f}")
        print(f"  Expectancy    : ₹{metrics['expectancy']:>11,.2f}")
    print(SEP)


def print_trade_log(results: dict) -> None:
    if not results["trade_log"]:
        print("  No trades were executed.")
        return
    rows = [
        {
            "Date":   t.date.strftime("%Y-%m-%d"),
            "Action": t.action,
            "Price":  f"₹{t.price:,.2f}",
            "Shares": t.shares,
            "P&L":    f"₹{t.pnl:,.2f}" if t.pnl else "-",
            "Cash":   f"₹{t.cash:,.0f}",
        }
        for t in results["trade_log"]
    ]
    print("\nTrade Log:")
    print(pd.DataFrame(rows).to_string(index=False))


# ─────────────────────────────────────────────────────────────────────────────
# Charts — 3 separate windows
# ─────────────────────────────────────────────────────────────────────────────

def _make_fig(title: str, figsize=(14, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BG)
    _style_ax(ax)
    fig.canvas.manager.set_window_title(title)
    return fig, ax


def plot_equity(df: pd.DataFrame, results: dict, metrics: dict) -> None:
    symbol  = results["symbol"]
    dates   = results["dates"]
    equity  = results["equity_curve"]
    capital = results["initial_cap"]

    first_close = df["close"].dropna().iloc[0]
    bh_shares   = int(capital // first_close)
    bh_leftover = capital - bh_shares * first_close
    buy_hold    = [bh_shares * df["close"].iloc[i] + bh_leftover for i in range(len(df))]
    bh_ret      = round((buy_hold[-1] - capital) / capital * 100, 2)

    fig, ax = _make_fig(f"{symbol} — Equity Curve")

    ax.plot(dates, equity,   color=BLUE,  lw=1.8, label="Strategy",   zorder=3)
    ax.plot(dates, buy_hold, color=AMBER, lw=1.2, linestyle="--",
            label="Buy & Hold", alpha=0.8, zorder=2)
    ax.fill_between(dates, equity, capital, alpha=0.08, color=BLUE)
    ax.axhline(capital, color=MUTED, lw=0.6, linestyle=":")

    ax.set_title(
        f"{symbol} — Equity Curve\n"
        f"CAGR {metrics['cagr']:+.1f}%  |  "
        f"Sharpe {metrics['sharpe']:.2f}  |  "
        f"Sortino {metrics['sortino']:.2f}  |  "
        f"Max DD {metrics['max_drawdown_pct']:.1f}%",
        color=TEXT, fontsize=10, pad=10,
    )
    ax.set_ylabel("Portfolio Value (₹)", color=TEXT, fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    ax.legend(facecolor=GRID, labelcolor=TEXT, fontsize=9, framealpha=0.6)
    ax.annotate(
        f"Strategy: {results['return_pct']:+.1f}%   Buy & Hold: {bh_ret:+.1f}%",
        xy=(0.01, 0.05), xycoords="axes fraction", color=MUTED, fontsize=8,
    )
    fig.tight_layout()


def plot_signals(df: pd.DataFrame, results: dict, metrics: dict) -> None:
    symbol    = results["symbol"]
    strategy  = results["strategy"]
    trade_log = results["trade_log"]

    fig, ax = _make_fig(f"{symbol} — Price & Signals")

    ax.plot(df.index, df["close"], color=MUTED, lw=1, label="Close", zorder=1)

    # EMA overlays (only if strategy stored them)
    if "ema_fast" in df.columns:
        ax.plot(df.index, df["ema_fast"], color=GREEN, lw=1.2, label="EMA Fast", zorder=2)
        ax.plot(df.index, df["ema_slow"], color=RED,   lw=1.2, label="EMA Slow", zorder=2)

    # Scatter trade markers
    for t in trade_log:
        if t.action == "BUY":
            ax.scatter(t.date, t.price, marker="^", color=GREEN, s=80,
                       zorder=5, edgecolors="white", linewidths=0.4)
        elif "SELL" in t.action:
            ax.scatter(t.date, t.price, marker="v", color=RED, s=80,
                       zorder=5, edgecolors="white", linewidths=0.4)
        elif t.action == "STOP-LOSS":
            ax.scatter(t.date, t.price, marker="x", color=AMBER, s=90,
                       zorder=5, linewidths=1.5)
        elif t.action == "TARGET":
            ax.scatter(t.date, t.price, marker="*", color=TEAL, s=100,
                       zorder=5, edgecolors="white", linewidths=0.3)

    # Legend proxies
    from matplotlib.lines import Line2D
    legend_items = [
        Line2D([0], [0], color=MUTED, lw=1, label="Close"),
        Line2D([0], [0], marker="^", color=GREEN, lw=0, markersize=8, label="Buy"),
        Line2D([0], [0], marker="v", color=RED,   lw=0, markersize=8, label="Sell"),
        Line2D([0], [0], marker="x", color=AMBER, lw=0, markersize=8, label="Stop-Loss"),
        Line2D([0], [0], marker="*", color=TEAL,  lw=0, markersize=9, label="Target"),
    ]
    if "ema_fast" in df.columns:
        legend_items.insert(1, Line2D([0], [0], color=GREEN, lw=1.2, label="EMA Fast"))
        legend_items.insert(2, Line2D([0], [0], color=RED,   lw=1.2, label="EMA Slow"))

    pf     = metrics.get("profit_factor")
    pf_str = f"{pf:.2f}" if pf and pf != float("inf") else "∞"
    ax.set_title(
        f"{symbol} — Price + {strategy} Signals\n"
        f"Win Rate {results['win_rate']}%  |  Profit Factor {pf_str}  |  "
        f"Total Trades {results['total_trades']}",
        color=TEXT, fontsize=10, pad=10,
    )
    ax.set_ylabel("Price (₹)", color=TEXT, fontsize=9)
    ax.legend(handles=legend_items, facecolor=GRID, labelcolor=TEXT,
              fontsize=8, ncol=4, framealpha=0.6)
    fig.tight_layout()


def plot_drawdown(results: dict, metrics: dict) -> None:
    symbol  = results["symbol"]
    dates   = results["dates"]
    equity  = results["equity_curve"]

    eq_s     = pd.Series(equity, index=dates)
    roll_max = eq_s.cummax()
    drawdown = (eq_s - roll_max) / roll_max * 100

    fig, ax = _make_fig(f"{symbol} — Drawdown", figsize=(14, 4))

    ax.fill_between(dates, drawdown, 0, color=RED, alpha=0.35)
    ax.plot(dates, drawdown, color=RED, lw=0.9)
    ax.axhline(0, color=MUTED, lw=0.6, linestyle=":")

    ax.set_title(
        f"{symbol} — Drawdown\n"
        f"Max: {metrics['max_drawdown_pct']:.2f}%  |  "
        f"Duration: {metrics['max_dd_duration']} bars",
        color=TEXT, fontsize=10, pad=10,
    )
    ax.set_ylabel("Drawdown (%)", color=TEXT, fontsize=9)
    fig.tight_layout()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # 1. Strategy selection
    strategy_cls = ask_strategy()

    # 2. Strategy-specific parameters
    strategy_params = ask_strategy_params(strategy_cls)

    # 3. General config
    cfg = ask_config(strategy_cls)

    # 4. Symbol
    symbol = ask_symbol()

    # 5. Load data
    print(f"\nLoading data for {symbol}...")
    df = load_data(symbol)
    print(f"Loaded {len(df)} bars  ({df.index[0].date()} → {df.index[-1].date()})")

    # 6. Build components
    strategy = strategy_cls(**strategy_params)
    strategy.position_size_pct = cfg["position_size_pct"]
    strategy.stop_loss_pct     = cfg["stop_loss_pct"]

    broker       = Broker(initial_capital=cfg["capital"])
    risk_manager = RiskManager(strategy=strategy, max_risk_per_trade=cfg["max_risk"])

    print(f"\nStrategy     : {strategy.name}")
    print(f"Risk Manager : {risk_manager}")

    # 7. Run backtest
    print("\nRunning backtest...")
    bt      = Backtest(df=df, strategy=strategy, broker=broker,
                       risk_manager=risk_manager, symbol=symbol)
    results = bt.run()

    # 8. Metrics
    trade_pnls = [
        t.pnl for t in results["trade_log"]
        if t.action in ("SELL", "STOP-LOSS", "TARGET", "SELL (close)")
    ]
    metrics = compute_metrics(
        equity_curve=results["equity_curve"],
        dates=results["dates"],
        initial_capital=cfg["capital"],
        trade_pnls=trade_pnls,
    )

    # 9. Summary
    print_summary(results, metrics)

    # 10. Optional trade log
    show_log = input("\nShow trade log? (y/N): ").strip().lower()
    if show_log == "y":
        print_trade_log(results)

    # 11. Charts (3 separate windows)
    print("\nOpening charts...")

    # Store EMA lines in df if EMACrossover (or any strategy with fast/slow)
    if hasattr(strategy, "fast") and hasattr(strategy, "slow"):
        df["ema_fast"] = df["close"].ewm(span=strategy.fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=strategy.slow, adjust=False).mean()

    plot_equity(df, results, metrics)
    plot_signals(df, results, metrics)
    plot_drawdown(results, metrics)

    plt.show()   # shows all 3 figure windows together


if __name__ == "__main__":
    main()
