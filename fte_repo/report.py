# === Forex Trading Engine v1.4.1 (Phase-1) | Amex Solutions ===
"""
Run Reporter — writes each run as a fixed, easy-to-hand-back bundle:
  runs/<timestamp>/summary.json      config + headline stats (paste THIS to Claude)
  runs/<timestamp>/trades.csv        every trade (entry/exit/R/reason)
  runs/<timestamp>/events.log        full engine log
  runs/<timestamp>/broker_profile.txt captured broker specs (verify tz/symbols)
Point Claude at summary.json (upload, Drive connector, or public-repo URL) and
the run is fully legible for analysis + upgrades.
"""
import json, os, csv, datetime as dt
from collections import Counter
try: from version import ENGINE_VERSION, ENGINE_BUILD
except Exception: ENGINE_VERSION, ENGINE_BUILD = "?", "?"

def write_report(engine, out_root="runs", tag=None, profile=None):
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    d = os.path.join(out_root, tag or ts); os.makedirs(d, exist_ok=True)
    log = getattr(engine, "log", [])
    opens  = [l for l in log if len(l)>2 and l[2]=="OPEN"]
    closes = [l for l in log if len(l)>2 and l[2]=="CLOSE"]
    skips  = [l for l in log if len(l)>2 and l[2]=="skip"]
    errs   = [l for l in log if len(l)>2 and l[2] in ("ERROR","error")]
    wins   = sum(1 for l in closes if "WIN" in str(l[3]))
    # R from CLOSE detail like "WIN +2.0R (...)" / "LOSS -1.0R (...)"
    def parse_R(s):
        import re; m=re.search(r'([+-]?\d+\.?\d*)R', str(s)); return float(m.group(1)) if m else 0.0
    Rs=[parse_R(l[3]) for l in closes]
    totR=round(sum(Rs),3)
    summary = {
        "engine": f"Forex Trading Engine v{ENGINE_VERSION} (build {ENGINE_BUILD})",
        "run_utc": ts,
        "config": {k:getattr(engine.cfg,k) for k in vars(engine.cfg)} if hasattr(engine,"cfg") else {},
        "equity": round(getattr(engine.broker,"equity",lambda:0)(),2) if hasattr(engine,"broker") else None,
        "trades_opened": len(opens),
        "trades_closed": len(closes),
        "wins": wins, "losses": len(closes)-wins,
        "win_rate_pct": round(100*wins/len(closes),1) if closes else None,
        "total_R": totR,
        "avg_R": round(totR/len(closes),3) if closes else None,
        "safety_skips": dict(Counter(str(l[3]) for l in skips)),
        "errors": len(errs),
    }
    json.dump(summary, open(os.path.join(d,"summary.json"),"w"), indent=2, default=str)
    with open(os.path.join(d,"trades.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["time","symbol","action","detail"])
        for l in log:
            if len(l)>2 and l[2] in ("OPEN","CLOSE"): w.writerow(l)
    with open(os.path.join(d,"events.log"),"w") as f:
        for l in log: f.write(" | ".join(str(x) for x in l)+"\n")
    if profile is not None:
        import io,contextlib; buf=io.StringIO()
        with contextlib.redirect_stdout(buf): profile.report()
        open(os.path.join(d,"broker_profile.txt"),"w").write(buf.getvalue())
    print(f"[report] wrote {d}/  (summary.json + trades.csv + events.log)")
    return d, summary

if __name__ == "__main__":
    # demo: run a short replay and produce a report bundle
    import pandas as pd
    from auto_engine import AutoEngine, AutoConfig, MockBroker
    from news_feed import NewsFeed
    df=pd.read_csv("data_library/XAUUSD_1h.csv",index_col=0,parse_dates=True)
    eng=AutoEngine(AutoConfig(symbols=["XAUUSD"],timeframe="1h",risk_pct=0.5),
                   MockBroker(100000,1.0,0.01,30), newsfeed=NewsFeed.from_records([]))
    for i in range(60,len(df)):
        eng.manage("XAUUSD",df["high"].values[i],df["low"].values[i],df.index[i]); eng.on_bar("XAUUSD",df,i)
    d,s=write_report(eng, tag="demo_run")
    print(json.dumps(s, indent=2, default=str))
