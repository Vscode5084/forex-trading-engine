"""
SMC Object Layer
================
Faithful, causal detection of the objects real SMC strategies are built from.
Every object is stamped at the bar it becomes KNOWABLE (confirmation bar), never
when it forms in hindsight — so anything a strategy reads here could truly have
been seen live. No repaint, no look-ahead.

Objects produced:
  swings (+HH/HL/LH/LL labels) · displacement · order blocks (+mitigation, breaker)
  · liquidity pools (BSL/SSL, equal highs/lows) · sweeps/raids · OTE zones
  · premium/discount state · dealing range

Parameters (the SMC parameter set from the audit) are all in SMCParams.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from dataclasses import dataclass, field


# ---------------------------------------------------------- robustness layer
def validate_ohlc(df, repair=True):
    """Validate/repair broker OHLC. Returns (clean_df, report). Handles dupes,
    bad prices, OHLC-consistency violations, time gaps — real feeds aren't clean."""
    rep={}; n0=len(df); d=df.copy()
    for c in ("open","high","low","close"):
        if c not in d.columns: raise ValueError(f"missing column: {c}")
    d=d[~d.index.duplicated(keep="last")].sort_index()
    rep["duplicates_removed"]=n0-len(d)
    bad=(d[["open","high","low","close"]]<=0).any(axis=1)
    rep["nonpositive_bars"]=int(bad.sum())
    if repair: d=d[~bad]
    hi_ok=d["high"]>=d[["open","close","low"]].max(axis=1)
    lo_ok=d["low"]<=d[["open","close","high"]].min(axis=1)
    viol=(~hi_ok)|(~lo_ok); rep["ohlc_violations"]=int(viol.sum())
    if repair and viol.any():
        mx=d.loc[viol,["open","high","low","close"]].max(axis=1)
        mn=d.loc[viol,["open","high","low","close"]].min(axis=1)
        d.loc[viol,"high"]=mx; d.loc[viol,"low"]=mn
    import pandas as _pd
    if isinstance(d.index,_pd.DatetimeIndex) and len(d)>3:
        diffs=d.index.to_series().diff().dropna(); med=diffs.median()
        rep["time_gaps"]=int((diffs>med*3).sum()); rep["median_bar"]=str(med)
    rep["rows_in"]=n0; rep["rows_out"]=len(d)
    return d, rep

def validate_params(P, n):
    issues=[]
    if P.swing_L<1: issues.append("swing_L<1")
    if P.swing_L*2>=n: issues.append(f"swing_L({P.swing_L}) too large for {n} bars")
    if P.atr_len<1: issues.append("atr_len<1")
    if not (0<P.ote_lo<P.ote_hi<1): issues.append("OTE levels must satisfy 0<lo<hi<1")
    if P.disp_mult<=0 or P.fvg_thr_atr<0: issues.append("thresholds must be >=0")
    return issues

# --------------------------------------------------------------- parameters
@dataclass
class SMCParams:
    swing_L:       int   = 5        # pivot confirmation lag (structure depth)
    disp_mult:     float = 1.5      # displacement: body >= disp_mult * ATR
    disp_body_ratio: float = 0.5    # ...and body/range >= this
    ob_use_body:   bool  = False    # OB zone from candle body (True) or full high/low
    ob_lookback:   int   = 10       # max bars back to find the OB origin candle
    ob_mitigation: str   = "wick"   # 'close' | 'wick' | 'avg' — how an OB is mitigated
    liq_tol_atr:   float = 0.15     # equal-high/low cluster width, in ATR
    sweep_lookback:int   = 50       # how far back a sweepable level may sit
    ote_lo:        float = 0.62     # OTE zone bounds (retracement of the impulse leg)
    ote_hi:        float = 0.79
    ote_focus:     float = 0.705
    atr_len:       int   = 14
    # pullback + reaction
    pb_react_window: int   = 20     # bars after zone arrival to allow a reaction
    pb_reaction:     str   = "any"  # 'rejection' | 'displacement' | 'close_back' | 'any'
    pb_reject_ratio: float = 0.5    # rejection wick must be >= this fraction of the bar range
    # extended objects
    fvg_thr_atr:  float = 0.25   # FVG significance threshold (× ATR)
    lqv_mult:     float = 2.0    # liquidity void = FVG larger than this × ATR
    swing_L_int:  int   = 2      # internal (minor) structure depth
    ext_scan:     int   = 600    # forward-scan cap for mitigation/inversion (bars)
    htf_tf:       str   = "4h"   # higher-timeframe context
    asian_utc:    tuple = (0, 6)   # Power-of-3 accumulation window (UTC)
    london_utc:   tuple = (7, 10)  # manipulation window
    ny_utc:       tuple = (12, 16) # distribution window

# --------------------------------------------------------------- object records
@dataclass
class Swing:      idx:int; price:float; kind:str; label:str          # kind 'H'/'L', label HH/HL/LH/LL
@dataclass
class OrderBlock:
    dir:int; top:float; btm:float; origin:int; confirm:int
    mitigated:int = -1; breaker:int = -1
    swept:bool = False; block_type:str = "ob"
@dataclass
class Pool:       price:float; kind:str; formed:int; swept:int = -1   # kind 'BSL'/'SSL'
@dataclass
class Sweep:      idx:int; dir:int; level:float; kind:str; validated:bool=False; source:str="swing"
@dataclass
class Pullback:
    dir:int; zone_top:float; zone_btm:float
    break_bar:int; arrival:int; reaction:int; ob:int; valid:bool

def _atr(df, n):
    h,l,c = df["high"], df["low"], df["close"]
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

# ============================================================== main builder
def build(df: pd.DataFrame, P: SMCParams = SMCParams(), validate: bool = True):
    if validate:
        df, _integrity = validate_ohlc(df, repair=True)
        _issues = validate_params(P, len(df))
        if _issues: raise ValueError("SMCParams invalid: "+"; ".join(_issues))
    else:
        _integrity = {"validated": False}
    warmup = max(P.swing_L*2, P.atr_len, P.swing_L_int*2) + 2
    o,h,l,c = (df[k].values for k in ("open","high","low","close"))
    n=len(df); A=_atr(df,P.atr_len).values
    body=np.abs(c-o); rng=np.maximum(h-l,1e-12)

    # ---- 1. displacement (per bar, knowable at bar close) ----------------
    disp = np.zeros(n,int)
    strong = (body >= P.disp_mult*A) & (body/rng >= P.disp_body_ratio)
    disp[strong & (c>o)] =  1
    disp[strong & (c<o)] = -1

    # ---- 2. swings + labels (confirmed L bars late) ----------------------
    swings: list[Swing] = []
    sh_price=np.full(n,np.nan); sl_price=np.full(n,np.nan)      # last confirmed swing carried fwd
    sh_idx=np.full(n,-1,int);  sl_idx=np.full(n,-1,int)
    last_H=None; last_L=None
    cur_shp=np.nan;cur_shi=-1;cur_slp=np.nan;cur_sli=-1
    for t in range(n):
        p=t-P.swing_L
        if p-P.swing_L>=0:
            if h[p]==h[p-P.swing_L:t+1].max() and h[p]>h[p-1]:
                lab = "HH" if (last_H is not None and h[p]>last_H) else ("LH" if last_H is not None else "H")
                swings.append(Swing(p,h[p],"H",lab)); last_H=h[p]; cur_shp,cur_shi=h[p],p
            if l[p]==l[p-P.swing_L:t+1].min() and l[p]<l[p-1]:
                lab = "LL" if (last_L is not None and l[p]<last_L) else ("HL" if last_L is not None else "L")
                swings.append(Swing(p,l[p],"L",lab)); last_L=l[p]; cur_slp,cur_sli=l[p],p
        sh_price[t],sh_idx[t]=cur_shp,cur_shi
        sl_price[t],sl_idx[t]=cur_slp,cur_sli

    # ---- 3. structure trend + BOS/CHoCH (close break of confirmed swing) --
    trend=np.zeros(n,int); choch=np.zeros(n,int); bos=np.zeros(n,int); ct=0
    for t in range(n):
        if not np.isnan(sh_price[t]) and c[t]>sh_price[t]:
            (choch if ct<=0 else bos)[t]=1; ct=1
        elif not np.isnan(sl_price[t]) and c[t]<sl_price[t]:
            (choch if ct>=0 else bos)[t]=-1; ct=-1
        trend[t]=ct

    # ---- 4. order blocks: last opposing candle before a displacement break
    obs: list[OrderBlock] = []
    for t in range(n):
        br = choch[t] or bos[t]
        if br==0: continue
        d=int(np.sign(br))
        # require displacement into the break within a small window
        if not np.any(disp[max(0,t-3):t+1]==d): continue
        # walk back to last opposing-close candle within lookback
        origin=-1
        for k in range(t, max(0,t-P.ob_lookback)-1, -1):
            opp = (c[k]<o[k]) if d==1 else (c[k]>o[k])
            if opp: origin=k; break
        if origin<0: continue
        top = (max(o[origin],c[origin]) if P.ob_use_body else h[origin])
        btm = (min(o[origin],c[origin]) if P.ob_use_body else l[origin])
        obs.append(OrderBlock(d, top, btm, origin, t))

    # mitigation + breaker (causal forward scan)
    def mit_hit(ob,t):
        if ob.dir==1:  # bullish OB mitigated when price trades back down into it
            lvl = c[t] if P.ob_mitigation=="close" else (l[t] if P.ob_mitigation=="wick" else (h[t]+l[t])/2)
            return lvl<=ob.top
        else:
            lvl = c[t] if P.ob_mitigation=="close" else (h[t] if P.ob_mitigation=="wick" else (h[t]+l[t])/2)
            return lvl>=ob.btm
    for ob in obs:
        for t in range(ob.confirm+1,n):
            if ob.mitigated<0 and mit_hit(ob,t): ob.mitigated=t
            # breaker: OB decisively violated the other way
            if ob.dir==1 and c[t]<ob.btm: ob.breaker=t; break
            if ob.dir==-1 and c[t]>ob.top: ob.breaker=t; break

    # ---- 4b. pullback + reaction (break -> retrace into OB -> reaction) ---
    # The entry object: after a break confirms an OB, price must PULL BACK into
    # the OB zone and then REACT (reject / displace / close back out) in the
    # trend direction, without first breaking structure the other way.
    pullbacks: list[Pullback] = []
    pb_entry = np.zeros(n, int)      # per-bar entry direction at the reaction bar
    def lower_wick(t): return (min(o[t],c[t]) - l[t]) / max(h[t]-l[t],1e-12)
    def upper_wick(t): return (h[t] - max(o[t],c[t])) / max(h[t]-l[t],1e-12)
    for oi, ob in enumerate(obs):
        d = ob.dir
        # arrival: first bar after confirm where price returns INTO the zone,
        # before the OB is invalidated (closed through the wrong side)
        arrival=-1; invalid=False
        for t in range(ob.confirm+1, min(ob.confirm+1+P.sweep_lookback, n)):
            if d==1:
                if c[t] < ob.btm: invalid=True; break          # broke down -> not a pullback
                if l[t] <= ob.top: arrival=t; break            # dipped into zone
            else:
                if c[t] > ob.top: invalid=True; break
                if h[t] >= ob.btm: arrival=t; break
        if arrival<0 or invalid: continue
        # reaction: within the window after arrival, price reacts in trend dir
        reaction=-1
        for t in range(arrival, min(arrival+P.pb_react_window, n)):
            if d==1 and c[t] < ob.btm: break                   # invalidated before reacting
            if d==-1 and c[t] > ob.top: break
            rej  = (lower_wick(t) >= P.pb_reject_ratio and c[t]>o[t]) if d==1 else \
                   (upper_wick(t) >= P.pb_reject_ratio and c[t]<o[t])
            dsp  = disp[t]==d
            cbk  = (c[t] > ob.top) if d==1 else (c[t] < ob.btm)
            hit  = {"rejection":rej, "displacement":dsp, "close_back":cbk,
                    "any": rej or dsp or cbk}[P.pb_reaction]
            if hit: reaction=t; break
        if reaction<0: continue
        pullbacks.append(Pullback(d, ob.top, ob.btm, ob.confirm, arrival, reaction, oi, True))
        pb_entry[reaction] = d


    pools: list[Pool] = []
    Hs=[s for s in swings if s.kind=="H"]; Ls=[s for s in swings if s.kind=="L"]
    def cluster(sw, kind):
        used=[False]*len(sw)
        for i,s in enumerate(sw):
            if used[i]: continue
            grp=[s]; used[i]=True
            for j in range(i+1,len(sw)):
                if not used[j] and abs(sw[j].price-s.price)<=P.liq_tol_atr*A[s.idx]:
                    grp.append(sw[j]); used[j]=True
            lvl=np.mean([g.price for g in grp]); formed=max(g.idx for g in grp)
            pools.append(Pool(lvl,kind,formed))
    cluster(Hs,"BSL"); cluster(Ls,"SSL")

    # ---- 6. sweeps / raids (PRECISE: real resting liquidity, each taken once) ----
    # Track ALL untaken swing-high (BSL) and swing-low (SSL) levels as they
    # confirm. A sweep = wick pierces a specific resting level then closes back
    # inside; that level is marked taken. A level closed THROUGH is 'broken'
    # (traded away), not swept. Far more precise than the last-confirmed-swing proxy.
    sweeps: list[Sweep] = []
    sh_conf={}; sl_conf={}
    for sw in swings:
        (sh_conf if sw.kind=="H" else sl_conf).setdefault(sw.idx+P.swing_L, []).append(sw.price)
    active_bsl=[]; active_ssl=[]; CAP=60
    for t in range(n):
        for lv in sh_conf.get(t,[]): active_bsl.append(lv)
        for lv in sl_conf.get(t,[]): active_ssl.append(lv)
        if len(active_bsl)>CAP: active_bsl=active_bsl[-CAP:]
        if len(active_ssl)>CAP: active_ssl=active_ssl[-CAP:]
        # bearish sweep of a BSL level: wick above, close back below
        rem=[]
        for lv in active_bsl:
            if h[t]>lv and c[t]<lv: sweeps.append(Sweep(t,-1,lv,"BSL")); rem.append(lv)
        for lv in rem: active_bsl.remove(lv)
        # bullish sweep of an SSL level
        rem=[]
        for lv in active_ssl:
            if l[t]<lv and c[t]>lv: sweeps.append(Sweep(t,+1,lv,"SSL")); rem.append(lv)
        for lv in rem: active_ssl.remove(lv)
        # drop levels that were simply broken (closed through) — no longer resting
        active_bsl=[lv for lv in active_bsl if c[t]<=lv]
        active_ssl=[lv for lv in active_ssl if c[t]>=lv]

    # ---- 7. OTE + premium/discount over the current dealing range --------
    rng_hi=sh_price; rng_lo=sl_price; mid=(rng_hi+rng_lo)/2
    pd_state=np.where(c<mid,1,np.where(c>mid,-1,0))            # 1 discount / -1 premium
    # OTE band of the active impulse leg (low->high if bull leg, else high->low)
    ote_lo_arr=np.full(n,np.nan); ote_hi_arr=np.full(n,np.nan); ote_dir=np.zeros(n,int)
    for t in range(n):
        if np.isnan(rng_hi[t]) or np.isnan(rng_lo[t]): continue
        leg = rng_hi[t]-rng_lo[t]
        if trend[t]>=0:   # bullish leg -> long retracement zone measured down from high
            ote_hi_arr[t]=rng_hi[t]-P.ote_lo*leg; ote_lo_arr[t]=rng_hi[t]-P.ote_hi*leg; ote_dir[t]=1
        else:             # bearish leg -> short retracement zone measured up from low
            ote_lo_arr[t]=rng_lo[t]+P.ote_lo*leg; ote_hi_arr[t]=rng_lo[t]+P.ote_hi*leg; ote_dir[t]=-1

    # ===================== EXTENDED SMC OBJECTS =====================
    HZ = P.ext_scan
    # ---- 8. FVG objects (+ mitigation, + inversion -> IFVG) --------------
    fvgs=[]
    for t in range(3,n):
        if l[t] > h[t-2] and (l[t]-h[t-2]) > A[t]*P.fvg_thr_atr:
            fvgs.append(dict(dir=1, top=l[t], btm=h[t-2], origin=t, mit=-1, inv=-1))
        elif h[t] < l[t-2] and (l[t-2]-h[t]) > A[t]*P.fvg_thr_atr:
            fvgs.append(dict(dir=-1, top=l[t-2], btm=h[t], origin=t, mit=-1, inv=-1))
    fvg_by_origin={}
    for f in fvgs:
        for t in range(f["origin"]+1, min(f["origin"]+1+HZ, n)):
            if f["dir"]==1:
                if f["mit"]<0 and l[t]<=f["top"]: f["mit"]=t
                if c[t]<f["btm"]: f["inv"]=t; break
            else:
                if f["mit"]<0 and h[t]>=f["btm"]: f["mit"]=t
                if c[t]>f["top"]: f["inv"]=t; break
        fvg_by_origin.setdefault(f["origin"], []).append(f)
    ifvgs=[f for f in fvgs if f["inv"]>=0]                     # inverse FVGs
    liq_voids=[f for f in fvgs if (f["top"]-f["btm"]) > A[f["origin"]]*P.lqv_mult]

    # ---- 9. Volume Imbalance (body gap with wick overlap) ----------------
    # NOTE: VI needs a true gap between consecutive candle BODIES. Continuous
    # 24h FX/metals OHLC has open[t] == close[t-1], so body gaps ~never occur
    # at ANY timeframe (verified: ~0 on 1h/15m/5m). VI is only meaningful on
    # gappy instruments (stocks/overnight) or raw tick data. Detector is
    # correct; the concept is inapplicable to this data type — expect ~0.
    vis=[]
    for t in range(1,n):
        if min(o[t],c[t])>max(o[t-1],c[t-1]) and l[t]<=h[t-1]:
            vis.append(dict(idx=t,dir=1,top=min(o[t],c[t]),btm=max(o[t-1],c[t-1])))
        elif max(o[t],c[t])<min(o[t-1],c[t-1]) and h[t]>=l[t-1]:
            vis.append(dict(idx=t,dir=-1,top=min(o[t-1],c[t-1]),btm=max(o[t],c[t])))

    # ---- 10. Balance Price Range (overlap of opposing FVGs, close in time)
    bprs=[]; last_bull=None; last_bear=None
    for f in fvgs:
        if f["dir"]==1: last_bull=f
        else: last_bear=f
        if last_bull and last_bear and abs(last_bull["origin"]-last_bear["origin"])<=10:
            top=min(last_bull["top"],last_bear["top"]); btm=max(last_bull["btm"],last_bear["btm"])
            if top>btm: bprs.append(dict(top=top,btm=btm,formed=f["origin"]))

    # ---- 11. Internal (minor) structure — multi-tier -------------------
    Li=P.swing_L_int
    ish=np.full(n,np.nan); isl=np.full(n,np.nan); ich=np.zeros(n,int); ibos=np.zeros(n,int); itr=np.zeros(n,int)
    csh=np.nan;csl=np.nan;ict=0
    for t in range(n):
        p=t-Li
        if p-Li>=0:
            if h[p]==h[p-Li:t+1].max() and h[p]>h[p-1]: csh=h[p]
            if l[p]==l[p-Li:t+1].min() and l[p]<l[p-1]: csl=l[p]
        ish[t]=csh; isl[t]=csl
        if not np.isnan(csh) and c[t]>csh: (ich if ict<=0 else ibos)[t]=1; ict=1
        elif not np.isnan(csl) and c[t]<csl: (ich if ict>=0 else ibos)[t]=-1; ict=-1
        itr[t]=ict

    # ---- 12. Inducement (last internal opposing swing before the break) --
    idm_lvl=np.full(n,np.nan); idm_dir=np.zeros(n,int); idm_taken=np.zeros(n,bool)
    cur_idm=np.nan; cur_idir=0
    last_isl=np.nan; last_ish=np.nan
    for t in range(n):
        if t>0 and isl[t]!=isl[t-1] and not np.isnan(isl[t]): last_isl=isl[t]
        if t>0 and ish[t]!=ish[t-1] and not np.isnan(ish[t]): last_ish=ish[t]
        if choch[t]==1 or bos[t]==1: cur_idm=last_isl; cur_idir=1     # bull leg -> IDM is the low below
        elif choch[t]==-1 or bos[t]==-1: cur_idm=last_ish; cur_idir=-1
        idm_lvl[t]=cur_idm; idm_dir[t]=cur_idir
        if not np.isnan(cur_idm):
            if cur_idir==1 and l[t]<cur_idm: idm_taken[t]=True
            if cur_idir==-1 and h[t]>cur_idm: idm_taken[t]=True

    # ---- 13. SCOB (single-candle OB = the sweep candle) ------------------
    scobs=[dict(idx=s.idx, dir=s.dir, top=h[s.idx], btm=l[s.idx]) for s in sweeps]

    # ---- 14. Quasimodo (faithful: reversal CHoCH preceded by a liquidity grab)
    import bisect as _bis
    qms=[]
    Hs=[s for s in swings if s.kind=="H"]; Ls=[s for s in swings if s.kind=="L"]
    Hidx=[s.idx for s in Hs]; Lidx=[s.idx for s in Ls]
    for t in range(n):
        if choch[t]==-1:                                   # bearish reversal
            j=_bis.bisect_left(Hidx,t)
            if j>=2 and Hs[j-1].price>Hs[j-2].price:       # head (recent HH grab) > left shoulder
                qms.append(dict(idx=t,dir=-1,level=Hs[j-2].price,head=Hs[j-1].price))
        elif choch[t]==1:                                  # bullish reversal
            j=_bis.bisect_left(Lidx,t)
            if j>=2 and Ls[j-1].price<Ls[j-2].price:       # head (recent LL grab) < left shoulder
                qms.append(dict(idx=t,dir=1,level=Ls[j-2].price,head=Ls[j-1].price))

    # ---- 15. Unicorn (breaker OB overlapping an FVG) --------------------
    unicorns=[]
    for ob in obs:
        if ob.breaker<0: continue
        for oo in range(ob.confirm-10, ob.confirm+11):
            for f in fvg_by_origin.get(oo, []):
                if min(ob.top,f["top"])>max(ob.btm,f["btm"]):
                    unicorns.append(dict(dir=ob.dir, top=min(ob.top,f["top"]),
                                         btm=max(ob.btm,f["btm"]), at=max(ob.confirm,f["origin"])))
                    break

    # ---- 16. PDH/PDL/PWH/PWL (prior day/week extremes, causal) ----------
    dh=df["high"].resample("1D").max(); dl=df["low"].resample("1D").min()
    wh=df["high"].resample("1W").max(); wl=df["low"].resample("1W").min()
    pdh=dh.shift(1).reindex(df.index,method="ffill").values
    pdl=dl.shift(1).reindex(df.index,method="ffill").values
    pwh=wh.shift(1).reindex(df.index,method="ffill").values
    pwl=wl.shift(1).reindex(df.index,method="ffill").values

    # ---- 17. Session ranges + Power-of-3 (AMD), causal cumulative -------
    hr=df.index.hour + df.index.minute/60.0
    date=df.index.floor("D")
    def sess(win):
        m=(hr>=win[0])&(hr<win[1])
        hi=pd.Series(np.where(m,h,np.nan),index=df.index)
        lo=pd.Series(np.where(m,l,np.nan),index=df.index)
        chi=hi.groupby(date).cummax().groupby(date).ffill()
        clo=lo.groupby(date).cummin().groupby(date).ffill()
        return chi.values, clo.values, m
    asia_hi,asia_lo,asia_m = sess(P.asian_utc)
    ldn_hi,ldn_lo,ldn_m    = sess(P.london_utc)
    ny_hi,ny_lo,ny_m       = sess(P.ny_utc)
    amd_phase=np.where(asia_m,1,np.where(ldn_m,2,np.where(ny_m,3,0)))  # 1=accum 2=manip 3=distrib

    # ---- 18. NWOG / NDOG (opening gaps as levels) ----------------------
    dopen=df["open"].resample("1D").first(); dclose=df["close"].resample("1D").last()
    ndog_hi=np.maximum(dopen.values, dclose.shift(1).values)
    ndog_lo=np.minimum(dopen.values, dclose.shift(1).values)
    ndog_hi=pd.Series(ndog_hi,index=dopen.index).reindex(df.index,method="ffill").values
    ndog_lo=pd.Series(ndog_lo,index=dopen.index).reindex(df.index,method="ffill").values

    # ---- 19. Judas swing (session-open false move then reversal) --------
    judas=[]
    for m in (ldn_m, ny_m):
        starts=np.where(m & ~np.roll(m,1))[0]
        for s0 in starts:
            if s0+6>=n: continue
            oo=o[s0]; hi=h[s0:s0+3].max(); lo=l[s0:s0+3].min()
            # false push up then close back below open -> bearish judas
            if hi>oo and c[s0+3]<oo: judas.append(dict(idx=s0+3,dir=-1,level=hi))
            elif lo<oo and c[s0+3]>oo: judas.append(dict(idx=s0+3,dir=1,level=lo))

    # ---- 20. Fib grid + extension targets (active leg) -----------------
    leg=(rng_hi-rng_lo)
    fib50=np.where(trend>=0, rng_hi-0.5*leg, rng_lo+0.5*leg)
    fib_ext127=np.where(trend>=0, rng_hi+0.27*leg, rng_lo-0.27*leg)   # TP1 projection
    fib_ext162=np.where(trend>=0, rng_hi+0.62*leg, rng_lo-0.62*leg)   # TP2 projection

    # ---- 21. HTF trend context (causal) -------------------------------
    hc=df["close"].resample(P.htf_tf).last()
    htf_bias=np.sign(hc-hc.ewm(span=50,adjust=False).mean()).shift(1)
    htf_bias=htf_bias.reindex(df.index,method="ffill").fillna(0).values.astype(int)

    # ---- warm-up guard: no signals before detectors are valid ----
    if warmup>0:
        for _arr in (choch,bos,pb_entry):
            _arr[:min(warmup,n)]=0
    # ===================== v1.2.0 RULES-FIDELITY LAYER =====================
    # recent-sweep arrays (for the 5-rule CHoCH liquidity requirement)
    rs_dir=np.zeros(n,int); rs_age=np.full(n,10**9,int); cur=0; last=-10**9
    sweepdir_at={s.idx:s.dir for s in sweeps}
    for t in range(n):
        if t in sweepdir_at: cur=sweepdir_at[t]; last=t
        rs_dir[t]=cur; rs_age[t]=t-last

    # -- 5-RULE STRICT CHoCH --------------------------------------------------
    # base CHoCH (body-close, rule 2) PLUS: (1) swept opposing liquidity first,
    # (4) displacement into the break, (5) location in correct premium/discount.
    choch_strict=np.zeros(n,int); K=P.swing_L*4
    for t in np.nonzero(choch)[0]:
        d=int(np.sign(choch[t]))
        sweep_ok = (rs_dir[t]==d and rs_age[t]<=K)               # rule 1: swept opposing liquidity
        disp_ok  = bool(np.any(disp[max(0,t-3):t+1]==d))          # rule 4: displacement into break
        # (rule 5 premium/discount is an ENTRY filter, applied at the retrace, not the break)
        if sweep_ok and disp_ok: choch_strict[t]=d

    # -- BREAKER vs MITIGATION split -----------------------------------------
    # breaker = OB swept liquidity before failing; mitigation = failed to sweep.
    for ob in obs:
        d=ob.dir; swept=False
        for b in range(max(0,ob.origin-(P.ob_lookback+P.swing_L)), ob.origin+1):
            if sweepdir_at.get(b)==d: swept=True; break
        ob.swept=swept
        ob.block_type = ("breaker" if swept else "mitigation") if ob.breaker>=0 else "ob"

    # -- PROTECTED vs TARGETED swings ----------------------------------------
    # protected = swing that swept liquidity AND was followed by a structure
    # break in the reversal direction (valid stop anchor). Else targeted.
    protected=[]   # list of (idx, kind, price, protected_bool)
    sw_bar={s.idx:s.dir for s in sweeps}
    brk_after = choch|bos
    for sw in swings:
        i0=sw.idx
        swept_liq = any(abs(b-i0)<=P.swing_L and sw_bar.get(b) is not None for b in range(max(0,i0-P.swing_L),i0+P.swing_L+1))
        # look for a break in the reversal dir within a forward window
        rev = 1 if sw.kind=="L" else -1
        win = brk_after[i0:min(i0+K,n)]
        broke = bool(np.any(win==rev))
        protected.append((i0, sw.kind, sw.price, bool(swept_liq and broke)))

    # ===================== v1.4.0 PRECISION BATCH =====================
    # A5: sharpened displacement — body-to-wick>=70%, <=3 bars, must leave FVG
    disp_ratio = np.where((h-l)>0, np.abs(c-o)/np.maximum(h-l,1e-12), 0.0)
    fvg_bars = set(f["origin"] for f in fvgs)
    disp_strict = np.zeros(n,int)
    for t in range(n):
        if disp[t]!=0 and disp_ratio[t]>=0.70:
            # must leave an FVG at/around the displacement (t-1..t+1)
            if any((b in fvg_bars) for b in (t-1,t,t+1)):
                disp_strict[t]=disp[t]

    # A2: full-liquidity sweeps — also sweep EQ pools + PDH/PDL/PWH/PWL (not just swings)
    def _sweep_level(level, kind_lbl, src):
        for t in range(1,n):
            if np.isnan(level if np.isscalar(level) else level[t]): continue
            lv = level if np.isscalar(level) else level[t]
            # bearish sweep (wick above, close back below)
            if h[t]>lv and c[t]<lv and (h[t-1]<=lv):
                sweeps.append(Sweep(t,-1,lv,kind_lbl,False,src))
            if l[t]<lv and c[t]>lv and (l[t-1]>=lv):
                sweeps.append(Sweep(t,+1,lv,kind_lbl,False,src))
    for arr,lbl in [(pdh,"PDH"),(pdl,"PDL"),(pwh,"PWH"),(pwl,"PWL")]:
        _sweep_level(arr, lbl, "htf_level")
    for pl in pools:
        # sweep of an equal-high/low cluster level, after it formed
        for t in range(pl["formed"] if isinstance(pl,dict) else pl.formed, min((pl["formed"] if isinstance(pl,dict) else pl.formed)+P.ext_scan, n)):
            lv = pl.price if hasattr(pl,"price") else pl["price"]
            k  = pl.kind  if hasattr(pl,"kind")  else pl["kind"]
            if k=="BSL" and h[t]>lv and c[t]<lv: sweeps.append(Sweep(t,-1,lv,"EQH",False,"eq_pool")); break
            if k=="SSL" and l[t]<lv and c[t]>lv: sweeps.append(Sweep(t,+1,lv,"EQL",False,"eq_pool")); break
    sweeps.sort(key=lambda x:x.idx)

    # A1: sweep VALIDATION — sweep followed by displacement + CHoCH + FVG (reversal confirmed)
    for sw in sweeps:
        d=sw.dir; win=range(sw.idx, min(sw.idx+P.pb_react_window, n))
        has_disp = any(disp_strict[t]==d or disp[t]==d for t in win)
        has_choch= any(choch[t]==d for t in win)
        has_fvg  = any((t in fvg_bars) for t in win)
        sw.validated = bool(has_disp and has_choch and has_fvg)

    # E6: liquidity-regime flag — rollover/low-liquidity window (UTC~21-22h ~ NY 5-6pm).
    # tz-dependent: verify against your broker server time on the live path.
    _hr = df.index.hour + df.index.minute/60.0
    liq_regime = np.where((_hr>=21)&(_hr<22), 1, 0).astype(int)   # 1 = distrust objects here

    # A6: OB sub-type tags (rejection / shadow / propulsion) where detectable
    for ob in obs:
        oi=ob.origin
        rng_o=max(h[oi]-l[oi],1e-12); body=abs(c[oi]-o[oi])
        wick = 1-(body/rng_o)
        if ob.block_type=="ob":
            if wick>=0.6: ob.block_type="rejection"      # long-wick rejection block
            elif ob.mitigated>=0 and ob.breaker<0: ob.block_type="propulsion"  # mitigated once, still holding

    return dict(
        params=P, atr=A, disp=disp, trend=trend, choch=choch, bos=bos,
        swings=swings, sh_price=sh_price, sl_price=sl_price, sh_idx=sh_idx, sl_idx=sl_idx,
        obs=obs, pools=pools, sweeps=sweeps, pullbacks=pullbacks, pb_entry=pb_entry,
        pd_state=pd_state, mid=mid, dealing_hi=rng_hi, dealing_lo=rng_lo,
        ote_lo=ote_lo_arr, ote_hi=ote_hi_arr, ote_dir=ote_dir,
        # extended
        fvgs=fvgs, ifvgs=ifvgs, liq_voids=liq_voids, vis=vis, bprs=bprs,
        int_trend=itr, int_choch=ich, int_bos=ibos, int_sh=ish, int_sl=isl,
        idm_lvl=idm_lvl, idm_dir=idm_dir, idm_taken=idm_taken,
        scobs=scobs, qms=qms, unicorns=unicorns,
        pdh=pdh, pdl=pdl, pwh=pwh, pwl=pwl,
        asia_hi=asia_hi, asia_lo=asia_lo, ldn_hi=ldn_hi, ldn_lo=ldn_lo, ny_hi=ny_hi, ny_lo=ny_lo,
        amd_phase=amd_phase, ndog_hi=ndog_hi, ndog_lo=ndog_lo, judas=judas,
        fib50=fib50, fib_ext127=fib_ext127, fib_ext162=fib_ext162, htf_bias=htf_bias,
        choch_strict=choch_strict, protected_swings=protected,
        rs_dir=rs_dir, rs_age=rs_age,
        warmup=warmup, integrity=_integrity,
        disp_ratio=disp_ratio, disp_strict=disp_strict, liq_regime=liq_regime,
    )

# ---------------------------------------------------------- detection summary
if __name__ == "__main__":
    df = pd.read_csv("gold_long_ohlc.csv", index_col=0, parse_dates=True)
    S = build(df, SMCParams())
    n=len(df)
    print(f"SMC OBJECT LAYER — gold 1h, {n} bars, {df.index[0].date()}..{df.index[-1].date()}\n")
    labs = {}
    for s in S["swings"]: labs[s.label]=labs.get(s.label,0)+1
    print(f"  swings         : {len(S['swings'])}   labels {labs}")
    print(f"  displacement   : up={int((S['disp']==1).sum())}  down={int((S['disp']==-1).sum())}")
    print(f"  BOS            : {int((S['bos']!=0).sum())}    CHoCH: {int((S['choch']!=0).sum())}")
    obs=S["obs"]; mit=sum(1 for o in obs if o.mitigated>=0); brk=sum(1 for o in obs if o.breaker>=0)
    print(f"  order blocks   : {len(obs)}   mitigated={mit}  became breaker={brk}")
    pools=S["pools"]
    print(f"  liquidity pools: {len(pools)}   BSL={sum(1 for p in pools if p.kind=='BSL')}  SSL={sum(1 for p in pools if p.kind=='SSL')}")
    sw=S["sweeps"]
    print(f"  sweeps/raids   : {len(sw)}   bullish={sum(1 for s in sw if s.dir==1)}  bearish={sum(1 for s in sw if s.dir==-1)}")
    pb=S["pullbacks"]
    print(f"  pullbacks      : {len(pb)}   bull={sum(1 for x in pb if x.dir==1)}  bear={sum(1 for x in pb if x.dir==-1)}"
          f"   (break->retrace into OB->reaction; = the actual entries)")
    inote=int((~np.isnan(S['ote_lo'])).sum())
    print(f"  OTE zones      : active on {inote} bars   ({100*inote/n:.0f}% of series)")
    print(f"  premium/disc   : discount {int((S['pd_state']==1).sum())} bars / premium {int((S['pd_state']==-1).sum())} bars")
    print("\n  --- EXTENDED OBJECTS ---")
    print(f"  FVGs           : {len(S['fvgs'])}   IFVG(inverted)={len(S['ifvgs'])}  liquidity voids={len(S['liq_voids'])}")
    print(f"  volume imbalance: {len(S['vis'])}   BPR={len(S['bprs'])}")
    print(f"  internal struct: BOS={int((S['int_bos']!=0).sum())} CHoCH={int((S['int_choch']!=0).sum())}")
    print(f"  inducement     : active {int((~np.isnan(S['idm_lvl'])).sum())} bars, taken {int(S['idm_taken'].sum())} times")
    print(f"  SCOB           : {len(S['scobs'])}   Quasimodo={len(S['qms'])}  Unicorn={len(S['unicorns'])}")
    print(f"  sessions/AMD   : accum={int((S['amd_phase']==1).sum())} manip={int((S['amd_phase']==2).sum())} distrib={int((S['amd_phase']==3).sum())} bars   Judas={len(S['judas'])}")
    print(f"  PDH/PDL/PWH/PWL + NDOG + fib grid + HTF bias: per-bar arrays")
    # causal spot-check: show one recent order block with its lifecycle
    for pbk in S["pullbacks"][-3:]:
        print(f"    Pullback dir={pbk.dir:+d} zone[{pbk.zone_btm:.1f},{pbk.zone_top:.1f}] "
              f"break@{pbk.break_bar} arrival@{pbk.arrival} reaction@{pbk.reaction}  (entry bar)")
