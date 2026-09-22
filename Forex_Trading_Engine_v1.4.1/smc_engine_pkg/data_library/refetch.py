"""Rebuild the whole data library from GitHub in ~1 minute. Run: python refetch.py"""
import urllib.request, pandas as pd, os, json, shutil
SRC={  # getdata-finance 1-minute (recent ~6-month synchronized window)
 "XAUUSD":"xauusd-1m-ohlcv-metals-historical-data/HEAD/XAUUSD_1m.csv",
 "XAGUSD":"xagusd-1m-ohlcv-metals-historical-data/HEAD/XAGUSD_1m.csv",
 "EURUSD":"eurusd-1m-ohlcv-forex-historical-data/HEAD/EURUSD_1m.csv",
 "GBPUSD":"gbpusd-1m-ohlcv-forex-historical-data/HEAD/GBPUSD_1m.csv",
 "USDJPY":"usdjpy-1m-ohlcv-forex-historical-data/HEAD/USDJPY_1m.csv",
 "AUDUSD":"audusd-1m-ohlcv-forex-historical-data/HEAD/AUDUSD_1m.csv",
 "USDCHF":"usdchf-1m-ohlcv-forex-historical-data/HEAD/USDCHF_1m.csv",
 "USDCAD":"usdcad-1m-ohlcv-forex-historical-data/HEAD/USDCAD_1m.csv",
 "EURJPY":"eurjpy-1m-ohlcv-forex-historical-data/HEAD/EURJPY_1m.csv"}
# deep 21y gold hourly anchor (separate source/window)
DEEP="https://raw.githubusercontent.com/FeziweMelvin/XAUUSD-Gold-Price/HEAD/XAU_1h_data.csv"
def std(df):
    df.columns=[c.strip().lower() for c in df.columns]
    df["datetime"]=pd.to_datetime(df["datetime"],utc=True)
    df=df.set_index("datetime")[["open","high","low","close"]].sort_index()
    return df[~df.index.duplicated(keep="last")].dropna()
def rs(df,rule):
    return df.resample(rule).agg(open=("open","first"),high=("high","max"),
        low=("low","min"),close=("close","last")).dropna()
man=[]
for sym,path in SRC.items():
    raw=urllib.request.urlopen(f"https://raw.githubusercontent.com/getdata-finance/{path}",timeout=90).read()
    open(f"_{sym}_1m.raw","wb").write(raw)
    d=std(pd.read_csv(f"_{sym}_1m.raw"))
    d.to_csv(f"{sym}_1m.csv")
    for rule,tag in {"5min":"5m","15min":"15m","1h":"1h","4h":"4h"}.items():
        rs(d,rule).to_csv(f"{sym}_{tag}.csv")
    h=rs(d,"1h"); man.append(dict(symbol=sym,tf="1h",rows=len(h),
        start=str(h.index[0].date()),end=str(h.index[-1].date())))
    print(sym,"done")
# deep gold
r=urllib.request.urlopen(DEEP,timeout=90).read(); open("_xau_deep.raw","wb").write(r)
g=pd.read_csv("_xau_deep.raw",sep=";"); g.columns=[c.strip().lower() for c in g.columns]
g["datetime"]=pd.to_datetime(g["date"],format="%Y.%m.%d %H:%M",utc=True)
g=g.set_index("datetime")[["open","high","low","close"]].sort_index()
g=g[~g.index.duplicated(keep="last")].dropna(); g.to_csv("XAUUSD_1h_deep.csv")
json.dump(man,open("manifest.json","w"),indent=1)
print("library rebuilt.")
