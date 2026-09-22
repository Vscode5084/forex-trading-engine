"""
NewsFeed
========
Economic-calendar layer for the engine + dashboard (top-left news slot).

Sourcing per face (honest):
  MQL5 EA (live)   -> MT5 NATIVE calendar (CalendarValueHistory / CalendarEventById).
                      Real, built-in, no external dependency. (spec'd for the EA port)
  Python bridge    -> trader-supplied feed: CSV export, or an API the trader wires in.
  Backtest         -> historical calendar CSV (point-in-time correct).

CSV schema (UTC):  datetime, currency, impact, event, actual, forecast, previous
  impact in {High, Medium, Low}.  Export from ForexFactory / investing.com / MT5.

Provides: upcoming high-impact events for the dashboard, and a per-bar NEWS-BLACKOUT
flag (bars within +/- N minutes of a high-impact event) that SMC strategies can use —
methodologically consistent, since ICT treats news as the manipulation driver.
"""
from __future__ import annotations
import pandas as pd, numpy as np, datetime as dt
from dataclasses import dataclass

IMPACT_ICON = {"High":"🔴", "Medium":"🟠", "Low":"🟡"}

@dataclass
class NewsEvent:
    time_utc: dt.datetime; currency: str; impact: str; event: str
    actual: str=""; forecast: str=""; previous: str=""

class NewsFeed:
    def __init__(self, events: list[NewsEvent]):
        self.events = sorted(events, key=lambda e: e.time_utc)

    # ---------- sources ----------
    @classmethod
    def from_csv(cls, path: str) -> "NewsFeed":
        df = pd.read_csv(path)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        ev=[NewsEvent(r.datetime.to_pydatetime(), str(r.currency), str(r.impact), str(r.event),
                      str(getattr(r,"actual","")), str(getattr(r,"forecast","")),
                      str(getattr(r,"previous",""))) for r in df.itertuples()]
        return cls(ev)

    @classmethod
    def from_records(cls, rows: list[dict]) -> "NewsFeed":
        return cls([NewsEvent(pd.to_datetime(r["datetime"],utc=True).to_pydatetime(),
                    r["currency"], r["impact"], r["event"],
                    r.get("actual",""), r.get("forecast",""), r.get("previous","")) for r in rows])

    # MQL5 EA uses the native calendar instead of this class; Python bridge can
    # plug an API here by returning a list[dict] to from_records().
    @classmethod
    def from_mt5_native_stub(cls):
        raise NotImplementedError("Live news comes from MT5's native MQL5 calendar in the EA. "
                                  "For Python, supply a CSV/API via from_csv/from_records.")

    # ---------- queries ----------
    def upcoming(self, now: dt.datetime, impacts=("High",), n=6):
        now = pd.Timestamp(now); now = (now.tz_localize("UTC") if now.tz is None else now.tz_convert("UTC")).to_pydatetime()
        return [e for e in self.events if e.time_utc >= now and e.impact in impacts][:n]

    def blackout_mask(self, index: pd.DatetimeIndex, before=30, after=30, impacts=("High",)):
        """Per-bar True if within [before, after] minutes of a high-impact event."""
        idx = index.tz_convert("UTC") if index.tz else index.tz_localize("UTC")
        m = np.zeros(len(idx), bool)
        ev = [pd.Timestamp(e.time_utc) for e in self.events if e.impact in impacts]
        for t in ev:
            lo, hi = t - pd.Timedelta(minutes=before), t + pd.Timedelta(minutes=after)
            m |= (idx>=lo) & (idx<=hi)
        return m

    # ---------- dashboard (TOP-LEFT slot) ----------
    def dashboard_block(self, now: dt.datetime, currencies=None, n=5) -> list[str]:
        now = pd.Timestamp(now); now = (now.tz_localize("UTC") if now.tz is None else now.tz_convert("UTC")).to_pydatetime()
        up = [e for e in self.events if e.time_utc >= now
              and e.impact in ("High","Medium")
              and (currencies is None or e.currency in currencies)][:n]
        out = ["── NEWS (high-impact) ──"]
        if not up:
            out.append("  no upcoming events")
            return out
        for e in up:
            dtm = e.time_utc - now
            mins = int(dtm.total_seconds()//60)
            cd = f"{mins//60}h{mins%60:02d}m" if mins>=60 else f"{mins}m"
            soon = "  <== SOON" if mins<=30 else ""
            out.append(f"{IMPACT_ICON.get(e.impact,'')} {e.time_utc:%H:%M} {e.currency} "
                       f"{e.event[:22]:22s} (in {cd}){soon}")
        return out

# ------------------------------------------------------------ demo (sample calendar)
if __name__ == "__main__":
    now = dt.datetime(2025,1,10,11,0, tzinfo=dt.timezone.utc)
    sample = NewsFeed.from_records([
        {"datetime":"2025-01-10 13:30","currency":"USD","impact":"High","event":"Non-Farm Payrolls","forecast":"160K"},
        {"datetime":"2025-01-10 13:30","currency":"USD","impact":"High","event":"Unemployment Rate","forecast":"4.2%"},
        {"datetime":"2025-01-10 15:00","currency":"USD","impact":"Medium","event":"UoM Sentiment"},
        {"datetime":"2025-01-10 11:20","currency":"EUR","impact":"High","event":"ECB Speech"},
        {"datetime":"2025-01-11 10:00","currency":"GBP","impact":"High","event":"GDP m/m"},
    ])
    print("TOP-LEFT DASHBOARD NEWS BLOCK (now 11:00 UTC):\n")
    for line in sample.dashboard_block(now, currencies=["USD","EUR","XAU"]):
        print("  "+line)
    # blackout demo
    idx = pd.date_range("2025-01-10 12:00","2025-01-10 15:00",freq="15min",tz="UTC")
    bo = sample.blackout_mask(idx, before=30, after=30)
    print(f"\n  news-blackout bars (±30m of High impact): {int(bo.sum())}/{len(idx)} "
          f"-> e.g. {[str(t.time())[:5] for t,x in zip(idx,bo) if x]}")
