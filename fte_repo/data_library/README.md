# Local Market Data Library

Standardized OHLC data for offline backtesting. All files: UTC datetime index,
columns open/high/low/close. Load with `loader.py`:

    from loader import load, available
    df = load("EURUSD", "1h")     # or "XAUUSD_1h_deep" for 21y gold
    available()                    # manifest

## Contents

**Synchronized multi-instrument set** (same ~6-month window, for cross-market / SMT):
  XAUUSD, XAGUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD, EURJPY
  Timeframes shipped: 5m, 15m, 1h, 4h   (window: 2026-03-12 .. 2026-09-11)

**Deep single-instrument anchor** (for long-horizon / out-of-sample robustness):
  XAUUSD_1h_deep  — 21 years hourly gold, 2004-06 .. 2025-06  (122,028 bars)

## Rebuild anytime (if the CSVs aren't at hand)

    python refetch.py     # re-pulls from GitHub and rebuilds everything (~1 min)

Also regenerates the 1m files (not shipped in the zip to keep it small).

## IMPORTANT CAVEATS — read before trusting a backtest

- **Source unverified.** getdata-finance (multi-instrument) and FeziweMelvin
  (deep gold) are public GitHub datasets, not audited feeds. Spot-check against
  a broker before using for anything real.
- **Metal price levels look high** in the 2026 window (gold ~3930-5228,
  silver ~56-98). Internally consistent (gold/silver ratio ~55-65) but confirm.
- **Two windows do NOT overlap.** Deep gold ends 2025-06; the multi-instrument
  set starts 2026-03. SMT / cross-market work uses the synchronized set only;
  deep robustness uses the 21y gold only.
- **Timezone assumed UTC.** Session/killzone logic depends on this; if the feed
  is offset, session windows shift.
- **Volume dropped.** Where present it was tick-count (unreliable), so OHLC only.
