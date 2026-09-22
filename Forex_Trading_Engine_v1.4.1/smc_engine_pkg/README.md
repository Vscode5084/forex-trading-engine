# SMC Auto-Engine (Phase 1 — MT5 + Python)

A causal, audited Smart-Money-Concepts engine with an autonomous trading
orchestrator. One verified Python "brain"; runs backtests locally and trades
live on MT5.

## Modules
- `smc_objects.py`   — the SMC OBJECT LAYER (verified/audited): swings+labels,
  structure/BOS/CHoCH, displacement, order blocks (+mitigation/breaker), FVG/IFVG,
  BPR, liquidity pools, sweeps, pullback+reaction, OTE, premium/discount,
  inducement, SCOB, Quasimodo (faithful), Unicorn, sessions/AMD, Judas, PDH/PDL,
  fib grid, HTF bias. All CAUSAL (no repaint, no look-ahead).
- `broker_profile.py`— broker specs: auto (live MT5) / manual (backtest) / hybrid;
  server-time->UTC, symbol map, spread cost.
- `news_feed.py`     — economic calendar: high-impact filter, news-blackout flag,
  TOP-LEFT dashboard block. (Live: MT5 native calendar in the EA; Python: your CSV.)
- `mt5_adapter.py`   — reads MT5 CSV export + live copy_rates -> UTC OHLC.
- `auto_engine.py`   — AUTONOMOUS orchestrator: detect -> safety gates -> risk-size
  -> place (hard SL/TP) -> manage -> log. MockBroker (test) + MT5Broker (live).
- `run_backtest.py`  — replay the engine on local data.
- `run_live_MT5.py`  — live loop on MT5 (Windows + terminal).
- `data_library/`    — 9 instruments (5m/15m/1h/4h) + 21y hourly gold + loader/refetch.

## Safety (auto mode)
mode defaults to **demo**; live requires mode='live' AND confirm_live=True.
Every trade carries a hard stop. Kill switches: daily-loss halt, max positions,
max total open risk, spread guard, news blackout. **Validate on DEMO first.**

## What is verified vs. your-side
- Verified here: object layer (audited correct), broker manual/hybrid, news logic,
  MT5 CSV adapter, the full autonomous loop (replayed on real data).
- Your-side (needs live MT5 / Windows): auto broker capture, live copy_rates,
  MT5Broker order execution. Written correctly; validate on your terminal.

## HONEST NOTE ON EDGE
The measured SMC edge on 21y gold is small (~2%/yr at safe risk, decade-OOS-stable).
This engine executes strategies faithfully and safely — it does not create edge.
Forward-test on demo before any real capital.
