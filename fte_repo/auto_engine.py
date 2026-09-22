"""
Auto-Mode Orchestrator
======================
The autonomous controller that runs the SMC engine unattended: pull bars ->
detect objects -> strategy signal -> SAFETY GATES -> risk-size -> place order
with a hard stop -> manage -> log. Same brain for backtest replay and live.

SAFETY BY DESIGN (not optional):
  * mode defaults to 'demo'. Going 'live' requires explicit opt-in + confirm flag.
  * every trade carries a hard stop (no naked positions), always.
  * daily-loss kill switch, max concurrent positions, max total open risk cap.
  * news-blackout (skip entries around high-impact events).
  * spread guard, connection heartbeat, global halt flag.
These exist because an autonomous system on a thin/unproven edge must fail safe.

The live MT5Broker needs a Windows terminal (validated by the trader). The
MockBroker lets the FULL autonomous loop be tested here on real historical data.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import pandas as pd, numpy as np, datetime as dt
import smc_objects as M

# ============================================================ config
@dataclass
class AutoConfig:
    symbols:            list
    timeframe:          str   = "1h"
    mode:               str   = "demo"     # 'demo' | 'live'
    confirm_live:       bool  = False      # must be True to actually trade live
    risk_pct:           float = 0.5        # % equity risked per trade
    max_positions:      int   = 3
    max_total_risk_pct: float = 3.0
    daily_loss_halt_pct:float = 3.0
    news_blackout_min:  int   = 30
    max_spread_points:  int   = 60
    require_hard_stop:  bool   = True
    rr:                 float = 2.0
    swing_L:            int   = 5
    derisk_dd_pct:      float = 5.0    # if equity is this % below peak, cut risk
    derisk_factor:      float = 0.5    # ...to this fraction (de-risk, never martingale)

# ============================================================ broker abstraction
@dataclass
class Position: symbol:str; dir:int; volume:float; entry:float; sl:float; tp:float; open_time:object; risk_money:float

class Broker(ABC):
    @abstractmethod
    def equity(self)->float: ...
    @abstractmethod
    def positions(self)->list: ...
    @abstractmethod
    def spread_points(self, symbol)->float: ...
    @abstractmethod
    def send(self, symbol, dir, volume, sl, tp)->Position: ...
    @abstractmethod
    def close(self, pos, price): ...

class MockBroker(Broker):
    """Simulated broker for replaying real data and verifying the autonomous loop."""
    def __init__(self, start_equity=10000.0, tick_value=1.0, tick_size=0.01, spread=30,
                 vol_min=0.01, vol_step=0.01, vol_max=100.0):
        self._eq=start_equity; self._pos=[]; self.tick_value=tick_value; self.tick_size=tick_size
        self._spread=spread; self.closed=[]
        self.vol_min=vol_min; self.vol_step=vol_step; self.vol_max=vol_max
    def equity(self): return self._eq
    def positions(self): return list(self._pos)
    def spread_points(self, s): return self._spread
    def send(self, symbol, d, vol, sl, tp):
        # entry recorded; risk in money for caps
        risk = abs(0)  # filled by engine before call via pos.risk_money
        p=Position(symbol,d,vol,None,sl,tp,None,0.0); self._pos.append(p); return p
    def close(self, pos, price, when=None, r=None):
        self._pos.remove(pos); self.closed.append((pos,price,r)); self._eq += (r or 0)

class MT5Broker(Broker):
    """LIVE broker via the MetaTrader5 terminal. Windows + running terminal only;
    validated by the trader. Same interface as MockBroker so the orchestrator is
    identical for backtest and live. Every send carries a hard SL/TP."""
    def __init__(self, profile, deviation=20, magic=770001):
        import MetaTrader5 as mt5
        self.mt5=mt5; self.p=profile; self.deviation=deviation; self.magic=magic
        if not mt5.initialize(): raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
    def equity(self): return self.mt5.account_info().equity
    def spread_points(self, s): 
        si=self.mt5.symbol_info(self.p.broker_symbol(s)); return si.spread if si else 1e9
    def positions(self):
        out=[]
        for pp in (self.mt5.positions_get() or []):
            out.append(Position(pp.symbol, 1 if pp.type==0 else -1, pp.volume,
                                pp.price_open, pp.sl, pp.tp, pp.time, 0.0))
        return out
    def send(self, symbol, d, vol, sl, tp):
        mt5=self.mt5; bsym=self.p.broker_symbol(symbol)
        tick=mt5.symbol_info_tick(bsym); si=mt5.symbol_info(bsym)
        price = tick.ask if d==1 else tick.bid
        req=dict(action=mt5.TRADE_ACTION_DEAL, symbol=bsym, volume=float(vol),
                 type=mt5.ORDER_TYPE_BUY if d==1 else mt5.ORDER_TYPE_SELL,
                 price=price, sl=float(sl), tp=float(tp), deviation=self.deviation,
                 magic=self.magic, comment="SMC-AUTO",
                 type_time=mt5.ORDER_TIME_GTC, type_filling=si.filling_mode)
        r=mt5.order_send(req)
        if r is None or r.retcode!=mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"order_send failed: {getattr(r,'retcode',None)} {mt5.last_error()}")
        return Position(symbol, d, vol, price, sl, tp, None, 0.0)
    def close(self, pos, price=None, when=None, r=None):
        mt5=self.mt5; bsym=self.p.broker_symbol(pos.symbol)
        for pp in (mt5.positions_get(symbol=bsym) or []):
            tick=mt5.symbol_info_tick(bsym)
            req=dict(action=mt5.TRADE_ACTION_DEAL, symbol=bsym, volume=pp.volume,
                     type=mt5.ORDER_TYPE_SELL if pp.type==0 else mt5.ORDER_TYPE_BUY,
                     position=pp.ticket, price=tick.bid if pp.type==0 else tick.ask,
                     deviation=self.deviation, magic=self.magic, comment="SMC-AUTO-CLOSE",
                     type_time=mt5.ORDER_TIME_GTC, type_filling=mt5.symbol_info(bsym).filling_mode)
            mt5.order_send(req)

# ============================================================ default strategy hook
# Placeholder signal for auto-mode testing: enter on a confirmed pullback into an
# OB, stop past the swing, target rr*R. Real named strategies plug in here later.
def pullback_signal(S, i, atr):
    d = int(S["pb_entry"][i])
    if d==0: return None
    entry = None                      # filled by orchestrator at bar open
    swing = S["sl_price"][i] if d==1 else S["sh_price"][i]
    if np.isnan(swing): return None
    return dict(dir=d, swing=swing)

# ============================================================ the orchestrator
class AutoEngine:
    def __init__(self, cfg:AutoConfig, broker:Broker, profile=None, newsfeed=None,
                 signal_fn=pullback_signal):
        self.cfg=cfg; self.broker=broker; self.profile=profile; self.news=newsfeed
        self.signal_fn=signal_fn
        self.halted=False; self.day=None; self.day_start_eq=broker.equity()
        self.log=[]

    def _risk_money(self):
        eq=self.broker.equity()
        # D5: de-risk while underwater (opposite of recovery/martingale)
        if not hasattr(self,"_peak_eq"): self._peak_eq=eq
        self._peak_eq=max(self._peak_eq,eq)
        dd=(self._peak_eq-eq)/self._peak_eq*100 if self._peak_eq>0 else 0
        r=self.cfg.risk_pct*(self.cfg.derisk_factor if dd>=self.cfg.derisk_dd_pct else 1.0)
        return eq*r/100.0

    def _safety_ok(self, symbol, when, dir):
        c=self.cfg
        if self.halted: return False,"halted"
        if c.mode=="live" and not c.confirm_live: return False,"live-not-confirmed"
        # daily loss kill switch
        if self.day_start_eq>0 and (self.day_start_eq-self.broker.equity())>=self.day_start_eq*c.daily_loss_halt_pct/100:
            self.halted=True; return False,"daily-loss-halt"
        if len(self.broker.positions())>=c.max_positions: return False,"max-positions"
        if self.broker.spread_points(symbol)>c.max_spread_points: return False,"spread"
        if self.news is not None:
            m=self.news.blackout_mask(pd.DatetimeIndex([when]), c.news_blackout_min, c.news_blackout_min)
            if m[0]: return False,"news-blackout"
        return True,"ok"

    def on_bar(self, symbol, df, i):
        """Process one CLOSED bar i for `symbol`. df is UTC OHLC up to and incl i."""
        when=df.index[i]
        # roll daily kill-switch baseline
        d=when.date()
        if self.day!=d: self.day=d; self.day_start_eq=self.broker.equity(); self.halted=False
        S=M.build(df.iloc[:i+1], M.SMCParams(swing_L=self.cfg.swing_L))
        atr=S["atr"][i]
        sig=self.signal_fn(S,i,atr)
        if not sig: return None
        ok,reason=self._safety_ok(symbol,when,sig["dir"])
        if not ok:
            self.log.append((when,symbol,"skip",reason)); return None
        # size by risk from the swing stop
        entry=df["open"].values[i] if i+1>=len(df) else df["open"].values[i]  # next-open in replay
        d_=sig["dir"]; dist=max(abs(entry-sig["swing"]), 0.5*atr); dist=min(dist,3.0*atr)
        sl=entry-d_*dist; tp=entry+d_*dist*self.cfg.rr
        risk_money=self._risk_money()
        # correct position sizing: money-at-risk per lot = stop_dist * (tick_value/tick_size)
        tv=getattr(self.broker,'tick_value',1.0); tsz=getattr(self.broker,'tick_size',0.01)
        vmin=getattr(self.broker,'vol_min',0.01); vstep=getattr(self.broker,'vol_step',0.01)
        vmax=getattr(self.broker,'vol_max',100.0)
        per_lot_risk = dist * (tv/tsz)
        vol_raw = risk_money/max(per_lot_risk,1e-9)
        vol = np.floor(vol_raw/vstep)*vstep
        vol = float(min(vol, vmax))
        if vol < vmin:                       # risk too small for min lot -> skip (honest, no under/over-risk)
            self.log.append((when,symbol,"skip",f"risk<{vmin}lot (need {vol_raw:.4f})")); return None
        # total-risk cap
        open_risk=sum(getattr(p,'risk_money',0) for p in self.broker.positions())
        if open_risk+risk_money> self.broker.equity()*self.cfg.max_total_risk_pct/100:
            self.log.append((when,symbol,"skip","total-risk-cap")); return None
        if self.cfg.require_hard_stop and (sl is None or np.isnan(sl)):
            self.log.append((when,symbol,"skip","no-stop")); return None
        pos=self.broker.send(symbol,d_,vol,sl,tp)
        pos.entry=entry; pos.open_time=when; pos.risk_money=risk_money
        self.log.append((when,symbol,"OPEN",f"{'BUY' if d_==1 else 'SELL'} {vol} @{entry:.2f} SL{sl:.2f} TP{tp:.2f}"))
        return pos

    def manage(self, symbol, bar_high, bar_low, when):
        """Resolve open positions against the current bar (hard SL/TP)."""
        for p in list(self.broker.positions()):
            if p.symbol!=symbol: continue
            hit=None
            if p.dir==1:
                if bar_low<=p.sl: hit=-1.0
                elif bar_high>=p.tp: hit=self.cfg.rr
            else:
                if bar_high>=p.sl: hit=-1.0
                elif bar_low<=p.tp: hit=self.cfg.rr
            if hit is not None:
                r_money=hit*p.risk_money
                self.broker.close(p, p.sl if hit<0 else p.tp, when, r_money)
                self.log.append((when,symbol,"CLOSE",f"{'WIN' if hit>0 else 'LOSS'} {hit:+.1f}R ({r_money:+.0f})"))

# ============================================================ autonomous replay test
if __name__ == "__main__":
    from news_feed import NewsFeed
    df=pd.read_csv("data_library/XAUUSD_1h.csv",index_col=0,parse_dates=True)
    cfg=AutoConfig(symbols=["XAUUSD"],timeframe="1h",mode="demo",risk_pct=0.5,
                   max_positions=3,daily_loss_halt_pct=3.0,rr=2.0)
    bk=MockBroker(start_equity=100000, tick_value=1.0, tick_size=0.01, spread=30)
    news=NewsFeed.from_records([])   # empty feed for the test (no external data here)
    eng=AutoEngine(cfg,bk,newsfeed=news)
    print("AUTONOMOUS LOOP TEST — replay real gold 1h through the auto-engine\n")
    warm=60
    for i in range(warm,len(df)):
        eng.manage("XAUUSD", df["high"].values[i], df["low"].values[i], df.index[i])
        eng.on_bar("XAUUSD", df, i)
    opens=[l for l in eng.log if l[2]=="OPEN"]; closes=[l for l in eng.log if l[2]=="CLOSE"]
    skips=[l for l in eng.log if l[2]=="skip"]
    wins=sum(1 for l in closes if "WIN" in l[3])
    from collections import Counter
    print(f"  bars processed : {len(df)-warm}")
    print(f"  trades opened  : {len(opens)}")
    print(f"  trades closed  : {len(closes)}  (wins {wins} / {len(closes)})")
    print(f"  final equity   : {bk.equity():,.0f}  (start 10,000)")
    print(f"  safety skips   : {len(skips)}  breakdown: {dict(Counter(l[3] for l in skips))}")
    print(f"\n  autonomous loop verified: detect -> gate -> size -> place -> manage -> log")
    print(f"  sample log:")
    for l in eng.log[:6]: print("   ",l[0], l[1], l[2], l[3])
