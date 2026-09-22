"""
MT5 Data Adapter
================
Reads MetaTrader-5 native data (CSV export OR live copy_rates) and hands clean,
UTC-indexed OHLC to the SMC engine — applying the BrokerProfile for the two
things that always trip people up:
  * server time -> UTC   (MT5 bar times are broker-SERVER time, not UTC)
  * spread -> cost        (per-symbol, for realistic backtest/live costs)

MT5 CSV export columns (tab/comma/semicolon):
  <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>
Live copy_rates fields: time, open, high, low, close, tick_volume, spread, real_volume

The live path needs the Windows-only MetaTrader5 package + a running terminal, so
it can't execute in this sandbox; it's written correctly and validated by you.
The CSV path is fully testable and is what backtesting uses.
"""
from __future__ import annotations
import pandas as pd, numpy as np, io

_TF = {"1m":"TIMEFRAME_M1","5m":"TIMEFRAME_M5","15m":"TIMEFRAME_M15",
       "30m":"TIMEFRAME_M30","1h":"TIMEFRAME_H1","4h":"TIMEFRAME_H4",
       "1d":"TIMEFRAME_D1","1w":"TIMEFRAME_W1"}

class MT5DataAdapter:
    def __init__(self, profile):
        self.p = profile                      # BrokerProfile (holds gmt offset, symbol map, specs)

    # ---------------- CSV export path (fully testable) ----------------
    def from_mt5_csv(self, path_or_buf, assume_server_time=True) -> pd.DataFrame:
        raw = open(path_or_buf).read() if isinstance(path_or_buf,str) else path_or_buf.read()
        # sniff delimiter
        first = raw.splitlines()[0]
        delim = "\t" if "\t" in first else (";" if ";" in first else ",")
        df = pd.read_csv(io.StringIO(raw), sep=delim)
        df.columns = [c.strip().strip("<>").lower() for c in df.columns]
        # build a datetime column from whatever is present
        if "date" in df.columns and "time" in df.columns:
            ts = pd.to_datetime(df["date"].astype(str).str.strip()+" "+df["time"].astype(str).str.strip(),
                                format="mixed", errors="coerce")
        elif "datetime" in df.columns:
            ts = pd.to_datetime(df["datetime"], errors="coerce", utc=False)
        elif "time" in df.columns:                          # epoch seconds (live-export style)
            ts = pd.to_datetime(df["time"], unit="s", errors="coerce")
        else:
            raise ValueError("No date/time column found in MT5 export.")
        df = df.assign(_ts=ts).dropna(subset=["_ts"])
        # server time -> UTC
        if assume_server_time and self.p.server_gmt_offset:
            df["_ts"] = df["_ts"] - pd.Timedelta(hours=self.p.server_gmt_offset)
        df["_ts"] = df["_ts"].dt.tz_localize("UTC")
        out = df.set_index("_ts")[["open","high","low","close"]].astype(float).sort_index()
        out = out[~out.index.duplicated(keep="last")]
        return out[(out>0).all(axis=1)]

    # ---------------- live copy_rates path (validated by you) ----------------
    def from_mt5_rates(self, symbol, tf="1h", count=5000, date_from=None) -> pd.DataFrame:
        try:
            import MetaTrader5 as mt5
        except Exception as e:
            raise RuntimeError("MetaTrader5 package unavailable (Windows + terminal only). "
                               "Use from_mt5_csv() for backtesting.") from e
        bsym = self.p.broker_symbol(symbol)
        tfc  = getattr(mt5, _TF[tf])
        if date_from is not None:
            rates = mt5.copy_rates_from(bsym, tfc, pd.Timestamp(date_from).to_pydatetime(), count)
        else:
            rates = mt5.copy_rates_from_pos(bsym, tfc, 0, count)
        if rates is None or len(rates)==0:
            raise RuntimeError(f"No rates for {bsym} {tf}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        ts = pd.to_datetime(df["time"], unit="s")            # server clock
        ts = ts - pd.Timedelta(hours=self.p.server_gmt_offset)
        df.index = ts.dt.tz_localize("UTC")
        out = df[["open","high","low","close"]].astype(float).sort_index()
        return out[~out.index.duplicated(keep="last")]

    # ---------------- cost helper (feeds the backtester) ----------------
    def cost(self, symbol) -> float:
        return self.p.cost_price(symbol)

# ------------------------------------------------------------ test (CSV path)
if __name__ == "__main__":
    from broker_profile import BrokerProfile
    # simulate a broker on UTC+2: reformat our real gold into MT5 export format with server time
    src = pd.read_csv("data_library/XAUUSD_1h.csv", index_col=0, parse_dates=True).head(300)
    server = src.copy(); server.index = server.index + pd.Timedelta(hours=2)   # server = UTC+2
    lines = ["<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>"]
    for t,r in server.iterrows():
        lines.append(f"{t:%Y.%m.%d}\t{t:%H:%M:%S}\t{r.open}\t{r.high}\t{r.low}\t{r.close}\t100\t0\t30")
    mt5_csv = "\n".join(lines); open("_mt5_export_test.csv","w").write(mt5_csv)

    prof = BrokerProfile.from_manual(dict(server_gmt_offset=2,
              symbol_map={"XAUUSD":"XAUUSD.m"},
              specs={"XAUUSD":dict(point=0.01,spread=30)}))
    ad = MT5DataAdapter(prof)
    df = ad.from_mt5_csv("_mt5_export_test.csv")
    print("MT5 ADAPTER TEST — parsed MT5 export, server(UTC+2) -> UTC")
    print(f"  rows={len(df)}  first_bar_UTC={df.index[0]}  (server was {server.index[0]} -> minus 2h)")
    print(f"  UTC recovery correct: {df.index[0]==src.index[0]}")
    print(f"  cost(XAUUSD)={ad.cost('XAUUSD'):.4f}   broker_symbol={prof.broker_symbol('XAUUSD')}")
    # prove it feeds the engine
    import smc_objects as M
    S = M.build(df)
    print(f"  engine ran on MT5 data: swings={len(S['swings'])} OB={len(S['obs'])} FVG={len(S['fvgs'])} sweeps={len(S['sweeps'])}")
