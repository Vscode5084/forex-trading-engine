"""Local data library loader.  load('EURUSD','1h') -> OHLC DataFrame."""
import pandas as pd, json
from pathlib import Path
DIR = Path(__file__).parent
def load(symbol, tf="1h"):
    return pd.read_csv(DIR/f"{symbol}_{tf}.csv", index_col=0, parse_dates=True)
def available():
    return json.load(open(DIR/"manifest.json"))
if __name__=="__main__":
    for m in available(): print(m)
