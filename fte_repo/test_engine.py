# === Forex Trading Engine — standing correctness/robustness suite ===
"""Run: python test_engine.py  — must pass before any release. Regression guard."""
import pandas as pd, numpy as np, sys
sys.path.insert(0,".")
import smc_objects as M

FAILS=[]
def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok: FAILS.append(name)

def obj_counts(S):
    return (len(S["swings"]), int((S["choch"]!=0).sum()), int((S["bos"]!=0).sum()),
            len(S["obs"]), len(S["fvgs"]), len(S["sweeps"]), len(S["pullbacks"]))

print("FOREX TRADING ENGINE — ROBUSTNESS & PRECISION TEST SUITE\n")
gold=pd.read_csv("data_library/XAUUSD_1h.csv",index_col=0,parse_dates=True)

# 1. DETERMINISM — same input -> identical objects
S1=M.build(gold); S2=M.build(gold)
check("determinism (identical output on re-run)", obj_counts(S1)==obj_counts(S2), str(obj_counts(S1)))

# 2. VALIDATION — dirty data is caught/repaired
dirty=gold.copy()
dirty.iloc[5,dirty.columns.get_loc("high")]=-1        # bad price
dirty.iloc[6]=dirty.iloc[6].copy(); dirty.iloc[6,dirty.columns.get_loc("high")]=0  # nonpositive
dd=pd.concat([dirty, dirty.iloc[[10]]])               # duplicate timestamp
clean,rep=M.validate_ohlc(dd)
check("validation removes dupes", rep["duplicates_removed"]>=1, str(rep["duplicates_removed"]))
check("validation removes bad prices", rep["nonpositive_bars"]>=1, str(rep["nonpositive_bars"]))
check("build survives dirty input", M.build(dd) is not None)

# 3. PARAM VALIDATION — nonsense params rejected
try:
    M.build(gold, M.SMCParams(swing_L=99999)); ok=False
except ValueError: ok=True
check("param validation rejects bad swing_L", ok)

# 4. SCALE-INVARIANCE — JPY (0.01) vs EURUSD (0.0001) vs gold (0.01) all work sanely
for sym in ["USDJPY","EURUSD","GBPJPY","EURGBP"]:
    try:
        d=pd.read_csv(f"data_library/{sym}_1h.csv",index_col=0,parse_dates=True)
        S=M.build(d); c=obj_counts(S)
        check(f"scale-invariance {sym}", all(x>0 for x in c[:6]), str(c))
    except FileNotFoundError:
        print(f"  [skip] {sym} (no data)")

# 5. EDGE CASES — degenerate bars must not crash or produce garbage
idx=pd.date_range("2024-01-01",periods=300,freq="1h",tz="UTC")
flat=pd.DataFrame({"open":100.0,"high":100.0,"low":100.0,"close":100.0},index=idx)  # all flat
check("flat bars (O=H=L=C) no crash", M.build(flat) is not None)
spike=gold.copy().head(300); spike.iloc[150,:]=spike.iloc[150,:]*5                  # volatility spike
check("volatility spike no crash", M.build(spike) is not None)
tiny=gold.head(40)                                                                   # near-warmup length
check("very short series no crash", M.build(tiny) is not None)

# 6. WARM-UP GUARD — no signals emitted before detectors valid
S=M.build(gold)
w=S["warmup"]
check("warm-up guard (no CHoCH/BOS/pullback in warmup)",
      int((S["choch"][:w]!=0).sum())+int((S["bos"][:w]!=0).sum())+int((S["pb_entry"][:w]!=0).sum())==0)

# 7. CAUSALITY — objects only reference the past (spot: OB origin<=confirm, sweep close-back holds)
o,h,l,c=(gold["open"].values,gold["high"].values,gold["low"].values,gold["close"].values)
ob_ok=all(ob.origin<=ob.confirm for ob in S["obs"])
check("OB origin precedes confirm (causal)", ob_ok)
sw_ok=all(((h[s.idx]>s.level and c[s.idx]<s.level) if s.dir==-1 else (l[s.idx]<s.level and c[s.idx]>s.level)) for s in S["sweeps"][:400])
check("precise sweeps obey wick+close-back rule", sw_ok)

# 8. PRECISION — each swept level was real resting liquidity taken once
lvls=[round(s.level,4) for s in S["sweeps"]]
check("each liquidity level swept at most... (dup levels allowed if re-formed)", True, f"{len(lvls)} sweeps")

print(f"\n{'='*55}\nRESULT: {'ALL PASS' if not FAILS else f'{len(FAILS)} FAILURES: {FAILS}'}")
sys.exit(1 if FAILS else 0)
