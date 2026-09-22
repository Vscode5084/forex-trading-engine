"""Run the auto-engine over local data (backtest/replay). Edit SYMBOL/TF."""
import pandas as pd
from auto_engine import AutoEngine, AutoConfig, MockBroker
from news_feed import NewsFeed
from report import write_report
SYMBOL, TF = "XAUUSD", "1h"
df = pd.read_csv(f"data_library/{SYMBOL}_{TF}.csv", index_col=0, parse_dates=True)
cfg = AutoConfig(symbols=[SYMBOL], timeframe=TF, mode="demo", risk_pct=0.5)
bk  = MockBroker(start_equity=100000, tick_value=1.0, tick_size=0.01, spread=30)
eng = AutoEngine(cfg, bk, newsfeed=NewsFeed.from_records([]))
for i in range(60, len(df)):
    eng.manage(SYMBOL, df["high"].values[i], df["low"].values[i], df.index[i])
    eng.on_bar(SYMBOL, df, i)
o=[l for l in eng.log if l[2]=="OPEN"]; c=[l for l in eng.log if l[2]=="CLOSE"]
print(f"{SYMBOL} {TF}: opened {len(o)} closed {len(c)} final_equity {bk.equity():,.0f}")

write_report(eng, tag='backtest_'+SYMBOL)
