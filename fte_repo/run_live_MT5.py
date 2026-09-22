"""LIVE auto-trading on MT5. Run on Windows with a running terminal.
SAFETY: mode='demo' by default; set mode='live', confirm_live=True to trade real.
Validate on a DEMO account first."""
import time, pandas as pd
from broker_profile import BrokerProfile
from mt5_adapter import MT5DataAdapter
from auto_engine import AutoEngine, AutoConfig, MT5Broker
from news_feed import NewsFeed
SYMBOLS=["XAUUSD"]; TF="1h"
prof = BrokerProfile.from_mt5(symbols=SYMBOLS)          # auto-captures broker specs (verify printout!)
adpt = MT5DataAdapter(prof)
brok = MT5Broker(prof)
cfg  = AutoConfig(symbols=SYMBOLS, timeframe=TF, mode="demo", confirm_live=False, risk_pct=0.5)
news = NewsFeed.from_records([])                        # plug your calendar CSV here for blackout
eng  = AutoEngine(cfg, brok, profile=prof, newsfeed=news)
seen={}
print("SMC auto-engine live loop started (mode=%s)."%cfg.mode)
while True:
    for s in SYMBOLS:
        df = adpt.from_mt5_rates(s, TF, count=800)
        last = df.index[-2]                            # last CLOSED bar
        if seen.get(s)!=last:
            seen[s]=last; i=len(df)-2
            eng.manage(s, df["high"].values[i], df["low"].values[i], df.index[i])
            eng.on_bar(s, df, i)
    time.sleep(15)
