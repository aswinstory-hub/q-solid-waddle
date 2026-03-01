import duckdb
import pandas as pd
import yfinance as yf
from datetime import timedelta
from typing import List

DB_PATH = "prices.db"
TABLE_NAME = "prices"


# -----------------------------
# 1. Connect to DuckDB
# -----------------------------
con = duckdb.connect(DB_PATH)


# -----------------------------
# 2. Get the latest date in the database
# -----------------------------
latest_date = con.execute(f"""
    SELECT MAX(date) FROM {TABLE_NAME}
""").fetchone()[0]

start_date = latest_date + timedelta(days=1)
print(f"Latest date in DB: {latest_date}")
print(f"Downloading from:  {start_date}")


# -----------------------------
# 3. Read tickers from file
# -----------------------------
with open("tickers.txt", "r") as f:
    symbols = [line.strip() + ".NS" for line in f if line.strip()]

print(f"Tickers to update:  {len(symbols)}")


# -----------------------------
# 4. Download new prices from yfinance
# -----------------------------
def download_prices(
    symbols: List[str],
    start: str
) -> pd.DataFrame:

    df = yf.download(
        tickers=symbols,
        start=start,
        group_by="ticker",
        threads=True
    )

    if df.empty:
        print("No new data available.")
        return pd.DataFrame()

    frames = []

    if len(symbols) == 1:
        sub = df.copy()
        sub.reset_index(inplace=True)
        sub.columns = [c.lower().replace(" ", "_") for c in sub.columns]
        sub["symbol"] = symbols[0]
        frames.append(sub)
    else:
        for symbol in symbols:
            try:
                sub = df[symbol].copy()
                sub.reset_index(inplace=True)
                sub.columns = [c.lower().replace(" ", "_") for c in sub.columns]
                sub["symbol"] = symbol
                frames.append(sub)
            except KeyError:
                print(f"  Warning: No data for {symbol}, skipping.")

    return pd.concat(frames, ignore_index=True)


prices_df = download_prices(symbols, start=str(start_date))

if not prices_df.empty:
    # -----------------------------
    # 5. Clean and select columns
    # -----------------------------
    prices_df = prices_df[
        ["symbol", "date", "open", "high", "low", "close", "volume"]
    ]

    # -----------------------------
    # 6. Deduplicated insert
    # -----------------------------
    con.execute(f"""
        INSERT INTO {TABLE_NAME}
        SELECT *
        FROM prices_df
        WHERE (symbol, date) NOT IN (
            SELECT symbol, date FROM {TABLE_NAME}
        )
    """)

    print(f"\nInserted {len(prices_df)} new rows.")

    # -----------------------------
    # 7. Sanity check
    # -----------------------------
    print(
        con.execute(f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            MIN(date) AS start_date,
            MAX(date) AS end_date
        FROM {TABLE_NAME}
        GROUP BY symbol
        """).fetchdf()
    )
else:
    print("Database is already up to date.")


# -----------------------------
# 8. Close connection
# -----------------------------
con.close()
