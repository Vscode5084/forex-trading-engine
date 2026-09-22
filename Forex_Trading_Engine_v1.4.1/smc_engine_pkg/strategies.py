# === Forex Trading Engine v1.4.0 (Phase-1) | Amex Solutions ===
"""
Strategy Assembly Framework (D1) + named SMC strategies (D2) + DoL targets (D4).
A Strategy composes the verified objects into a full setup and yields signals
(dir, stop, target) the auto-engine executes. Each is registered by name so the
trader selects which to run. This is the layer we build strategies on TOGETHER.
"""
import numpy as np, pandas as pd
import smc_objects as M

REGISTRY = {}
def strategy(name):
    def deco(fn): REGISTRY[name]=fn; return fn
    return deco

# ---- DoL target engine (D4): nearest opposing liquidity as the draw ----
def dol_target(S, i, d, entry):
    """Draw-on-Liquidity target: nearest opposing resting liquidity beyond entry."""
    cands=[]
    if d==1:
        for arr in (S["pdh"],S["pwh"]):
            v=arr[i]
            if not np.isnan(v) and v>entry: cands.append(v)
        if not np.isnan(S["dealing_hi"][i]) and S["dealing_hi"][i]>entry: cands.append(S["dealing_hi"][i])
        return min(cands) if cands else None            # nearest above
    else:
        for arr in (S["pdl"],S["pwl"]):
            v=arr[i]
            if not np.isnan(v) and v<entry: cands.append(v)
        if not np.isnan(S["dealing_lo"][i]) and S["dealing_lo"][i]<entry: cands.append(S["dealing_lo"][i])
        return max(cands) if cands else None            # nearest below

def _stop(S, i, d, entry, rr=2.0):
    a=S["atr"][i]; swing=S["sl_price"][i] if d==1 else S["sh_price"][i]
    if np.isnan(swing): return None
    dist=min(max(abs(entry-swing),0.5*a),3.0*a)
    return entry-d*dist, dist

# ================= named strategies (each returns dir or 0 at bar i) =========
@strategy("ob_retrace")           # sweep -> CHoCH -> pullback into OB (the classic)
def s_ob_retrace(S, i, p):
    return int(S["pb_entry"][i])  # pullback+reaction object already encodes this

@strategy("sweep_reversal")       # validated liquidity sweep -> reversal
def s_sweep_reversal(S, i, p):
    for sw in S["_sweep_at"].get(i, []):
        if sw.validated: return sw.dir
    return 0

@strategy("choch_silver_bullet")  # our measured edge: CHoCH inside Silver-Bullet window
def s_choch_sb(S, i, p):
    d=int(S["choch"][i])
    if d==0: return 0
    t=S["_index"][i]; hr=t.hour+t.minute/60.0
    in_sb=(8<=hr<9) or (15<=hr<16) or (19<=hr<20)
    return d if in_sb else 0

@strategy("ote")                  # CHoCH then enter OTE zone (0.62-0.79)
def s_ote(S, i, p):
    d=int(S["choch"][i]);  return d   # entry-zone refinement handled at execution

# ---- signal wrapper the auto-engine calls ----
def make_signal(strategy_name, params=None):
    fn=REGISTRY[strategy_name]; params=params or {}
    def signal(S, i, atr):
        # attach helpers used by strategies
        if "_sweep_at" not in S:
            m={}
            for sw in S["sweeps"]: m.setdefault(sw.idx,[]).append(sw)
            S["_sweep_at"]=m
        d=fn(S, i, params)
        if not d: return None
        entry=None; swing=S["sl_price"][i] if d==1 else S["sh_price"][i]
        if np.isnan(swing): return None
        return dict(dir=d, swing=swing, strategy=strategy_name)
    return signal

if __name__ == "__main__":
    df=pd.read_csv("data_library/XAUUSD_1h.csv",index_col=0,parse_dates=True)
    S=M.build(df); S["_index"]=df.index
    m={}
    for sw in S["sweeps"]: m.setdefault(sw.idx,[]).append(sw)
    S["_sweep_at"]=m
    print("STRATEGY ASSEMBLY FRAMEWORK (D1) — signal counts per named strategy (gold 1h)\n")
    for name,fn in REGISTRY.items():
        cnt=sum(1 for i in range(len(df)) if fn(S,i,{}))
        print(f"  {name:20s}: {cnt} signals")
    # DoL target demo
    i=next((i for i in range(len(df)) if S['pb_entry'][i]!=0), None)
    if i:
        d=int(S['pb_entry'][i]); entry=df['open'].values[min(i+1,len(df)-1)]
        tgt=dol_target(S,i,d,entry)
        print(f"\n  DoL target demo @ bar {i}: dir={d} entry={entry:.2f} draw-on-liquidity={tgt}")
    print("\n  registry:", list(REGISTRY.keys()))
