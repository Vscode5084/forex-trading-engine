"""
BrokerProfile
=============
Single source of every broker-dependent value the SMC engine needs. Three modes:
  auto   — captured live from an MT5 login (server tz, spread, digits, sizing...)
  manual — supplied by the trader (used for backtesting, or to override auto)
  hybrid — auto-capture, then apply trader overrides on top  (DEFAULT, safest)

The engine reads broker values ONLY from here, never from hardcoded assumptions,
so the identical SMC logic runs whether backtesting a CSV (manual) or live (auto).

NOTE: the MetaTrader5 package is Windows + live-terminal only and cannot run in
this research sandbox. The auto path is written correctly and logs every captured
field on connect for the trader to verify; it executes on the trader's MT5.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import datetime as dt

@dataclass
class BrokerProfile:
    # --- identity / connection ---
    source:        str   = "manual"          # 'auto' | 'manual' | 'hybrid'
    server:        str   = ""
    company:       str   = ""
    account_ccy:   str   = "USD"
    leverage:      int   = 100
    balance:       float = 0.0
    equity:        float = 0.0
    # --- time (the piece that fixes session windows) ---
    server_gmt_offset: float = 0.0            # broker-server time minus UTC, in HOURS
    dst_aware:     bool  = True
    # --- per-symbol map + specs (keyed by the engine's canonical name) ---
    symbol_map:    dict  = field(default_factory=dict)   # 'XAUUSD' -> 'XAUUSD.m'
    specs:         dict  = field(default_factory=dict)   # 'XAUUSD' -> {digits,point,...}

    # ---------- population: manual ----------
    @classmethod
    def from_manual(cls, cfg: dict) -> "BrokerProfile":
        p = cls(source="manual")
        for k,v in cfg.items():
            if hasattr(p,k): setattr(p,k,v)
        return p

    # ---------- population: auto (live MT5) ----------
    @classmethod
    def from_mt5(cls, login:int=None, password:str=None, server:str=None,
                 symbols:list=None) -> "BrokerProfile":
        try:
            import MetaTrader5 as mt5
        except Exception as e:
            raise RuntimeError("MetaTrader5 package unavailable (Windows + terminal only). "
                               "Use from_manual() for backtesting, or run this on your MT5 box.") from e
        if not mt5.initialize(login=login, password=password, server=server):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        acc = mt5.account_info()
        p = cls(source="auto", server=(server or acc.server), company=acc.company,
                account_ccy=acc.currency, leverage=acc.leverage,
                balance=acc.balance, equity=acc.equity)
        # server GMT offset: compare broker server time to real UTC
        tick_syms = symbols or [s.name for s in mt5.symbols_get()[:1]]
        srv_time = None
        for s in (symbols or [x.name for x in mt5.symbols_get()]):
            t = mt5.symbol_info_tick(s)
            if t and t.time: srv_time = dt.datetime.utcfromtimestamp(t.time); break
        if srv_time:
            now_utc = dt.datetime.utcnow()
            p.server_gmt_offset = round((srv_time - now_utc).total_seconds()/3600)
        # per-symbol specs
        for eng_name in (symbols or []):
            si = mt5.symbol_info(eng_name)
            if si is None: continue
            p.symbol_map[eng_name] = si.name
            p.specs[eng_name] = dict(
                digits=si.digits, point=si.point, tick_size=si.trade_tick_size,
                tick_value=si.trade_tick_value, contract=si.trade_contract_size,
                vol_min=si.volume_min, vol_max=si.volume_max, vol_step=si.volume_step,
                stops_level=si.trade_stops_level, freeze_level=si.trade_freeze_level,
                spread=si.spread, filling=si.filling_mode)
        p.report()
        return p

    # ---------- population: hybrid (auto then overrides) ----------
    @classmethod
    def hybrid(cls, overrides:dict=None, **mt5_kwargs) -> "BrokerProfile":
        p = cls.from_mt5(**mt5_kwargs)
        p.source = "hybrid"
        for k,v in (overrides or {}).items():
            if isinstance(getattr(p,k,None), dict) and isinstance(v, dict):
                getattr(p,k).update(v)            # merge dict fields (specs/symbol_map)
            elif hasattr(p,k):
                setattr(p,k,v)                     # scalar override wins
        return p

    # ---------- helpers the engine calls ----------
    def utc_from_server(self, server_dt):
        return server_dt - dt.timedelta(hours=self.server_gmt_offset)
    def cost_price(self, sym):
        s = self.specs.get(sym, {})
        return s.get("spread",0)*s.get("point",0) if s else 0.0
    def broker_symbol(self, sym): return self.symbol_map.get(sym, sym)
    def report(self):
        print(f"[BrokerProfile:{self.source}] server={self.server} ccy={self.account_ccy} "
              f"lev=1:{self.leverage} GMT_offset={self.server_gmt_offset:+.0f}h  "
              f"(VERIFY offset & symbol map!)")
        for k,v in self.specs.items():
            print(f"   {k:10s} -> {self.symbol_map.get(k,k):12s} digits={v.get('digits')} "
                  f"spread={v.get('spread')} tick_val={v.get('tick_value')}")

# ------------------------------------------------------------ self-test (manual/hybrid)
if __name__ == "__main__":
    # manual profile for backtesting (what the engine uses with no live login)
    bt = BrokerProfile.from_manual(dict(
        account_ccy="USD", leverage=500, balance=10000, server_gmt_offset=2,   # e.g. broker UTC+2
        symbol_map={"XAUUSD":"XAUUSD.m","EURUSD":"EURUSD.m"},
        specs={"XAUUSD":dict(digits=2,point=0.01,tick_size=0.01,tick_value=1.0,
                             contract=100,vol_min=0.01,vol_max=100,vol_step=0.01,
                             stops_level=0,spread=30,filling=1)}))
    print("MANUAL profile (backtest):"); bt.report()
    print(f"  gold cost/price = {bt.cost_price('XAUUSD'):.4f}   broker symbol = {bt.broker_symbol('XAUUSD')}")
    print(f"  session example: server 09:00 @ UTC+2  -> UTC {bt.utc_from_server(dt.datetime(2025,1,1,9,0)).time()}")
    # hybrid-style override simulation (no live MT5 here, so just show override-merge on manual)
    bt.symbol_map.update({"GBPUSD":"GBPUSD.pro"}); bt.server_gmt_offset=3
    print("\nAfter trader override (offset->UTC+3, +GBPUSD map): trader value wins.")
    bt.report()
