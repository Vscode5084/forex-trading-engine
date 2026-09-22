# === Forex Trading Engine v1.4.0 (Phase-1) | Amex Solutions ===
"""
SMT Divergence (B1)  — the one genuinely independent SMC signal axis.
Two correlated instruments should sweep liquidity together. When one takes out
its swing (makes a new extreme) and the correlated one FAILS to, that divergence
reveals institutional absorption -> reversal bias on the failing side.

Requires SYNCHRONIZED data for the pair (we have it: XAU/XAG, EUR/GBP, USD-crosses).
Causal: uses only confirmed swings known at each bar.
"""
import numpy as np, pandas as pd
import smc_objects as M

# canonical correlation pairs (positively correlated -> classic SMT)
SMT_PAIRS = [("XAUUSD","XAGUSD"), ("EURUSD","GBPUSD"), ("AUDUSD","NZDUSD"),
             ("EURUSD","AUDUSD"), ("GBPUSD","EURGBP")]

def detect_smt(dfA, dfB, P=M.SMCParams()):
    """Return list of SMT events: (time, dir, note). dir +1 bullish (A swept low,
    B held) / -1 bearish (A swept high, B held). Aligned on common timestamps."""
    idx = dfA.index.intersection(dfB.index)
    A = M.build(dfA.loc[idx], P); B = M.build(dfB.loc[idx], P)
    a_h,a_l,a_c = dfA.loc[idx,"high"].values, dfA.loc[idx,"low"].values, dfA.loc[idx,"close"].values
    b_h,b_l,b_c = dfB.loc[idx,"high"].values, dfB.loc[idx,"low"].values, dfB.loc[idx,"close"].values
    ashh,asll = A["sh_price"], A["sl_price"]; bshh,bsll = B["sh_price"], B["sl_price"]
    n=len(idx); out=[]
    for t in range(1,n):
        # bearish SMT: A takes out its swing high, B fails to take its swing high
        if not np.isnan(ashh[t]) and not np.isnan(bshh[t]):
            a_took = a_h[t] > ashh[t]
            b_took = b_h[t] > bshh[t]
            if a_took and not b_took and a_c[t] < ashh[t]:      # A swept & rejected, B held
                out.append((idx[t], -1, "A swept high, B held"))
        # bullish SMT: A takes out its swing low, B fails
        if not np.isnan(asll[t]) and not np.isnan(bsll[t]):
            a_took = a_l[t] < asll[t]
            b_took = b_l[t] < bsll[t]
            if a_took and not b_took and a_c[t] > asll[t]:
                out.append((idx[t], +1, "A swept low, B held"))
    return out

if __name__ == "__main__":
    print("SMT DIVERGENCE (B1) — synchronized correlated pairs\n")
    for a,b in SMT_PAIRS:
        try:
            dfa=pd.read_csv(f"data_library/{a}_1h.csv",index_col=0,parse_dates=True)
            dfb=pd.read_csv(f"data_library/{b}_1h.csv",index_col=0,parse_dates=True)
        except FileNotFoundError:
            print(f"  {a}/{b}: skip (no synchronized data)"); continue
        ev=detect_smt(dfa,dfb)
        bull=sum(1 for e in ev if e[1]==1); bear=sum(1 for e in ev if e[1]==-1)
        print(f"  {a}/{b}: {len(ev)} SMT events  (bull {bull} / bear {bear})"
              + ("" if ev else "  <- none in window"))
