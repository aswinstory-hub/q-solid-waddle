import numpy as np
import pandas as pd
import duckdb
#from strategies.ema_crossover import EMACrossover
#import utils as u

con = duckdb.connect("prices.db")

tables = con.execute("""
SELECT symbol, close, date
FROM prices
WHERE symbol = ?
""", ["RELIANCE.NS"]).fetchdf()

print(tables)

con.close()
