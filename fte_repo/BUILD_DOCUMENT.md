# FOREX TRADING ENGINE — BUILD DOCUMENT
**Version 1.4.1  ·  Phase-1 (MT5 + Python, auto-mode)  ·  build 2026-09-22 (v1.2.0)  ·  Amex Solutions**

> Purpose of this document: capture the EXACT state of the engine so any future
> session resumes instantly — what exists, what is verified, what is pending,
> the design decisions, and the data. Read this first before extending the engine.

---
## 1. WHAT THIS ENGINE IS
A causal Smart-Money-Concepts (SMC/ICT) detection + autonomous execution engine.
One verified Python "brain" (`smc_objects.py`) feeds every face: backtest, live
MT5 (Python bridge), and — later — native MQL5 EA and TradingView Pine.
Guiding rule: **the Python object layer is the single source of truth; every
platform port must reproduce it bar-for-bar (parity).**

## 2. ARCHITECTURE (one brain, many faces)
```
              SMC OBJECT LAYER (Python)  ← audited ground truth
                        │
   ┌──────────┬─────────┼───────────┬──────────────┐
 MT5 data   BrokerProfile  NewsFeed   AUTO-ENGINE   (Phase-2: MQL5 EA,
 adapter    (broker specs) (calendar) (orchestrator) TradingView Pine)
```

## 3. FILE MAP
| File | Role | Verified |
|---|---|---|
| version.py | brand + version single-source | ✅ |
| smc_objects.py | SMC object layer (all concepts) | ✅ audited |
| broker_profile.py | auto/manual/hybrid broker capture | manual/hybrid ✅ |
| news_feed.py | calendar, blackout, dashboard block | logic ✅ |
| mt5_adapter.py | MT5 CSV + copy_rates → UTC OHLC | CSV ✅ |
| auto_engine.py | autonomous orchestrator + brokers | loop ✅ |
| run_backtest.py | local replay runner | ✅ |
| run_live_MT5.py | live MT5 runner (demo-default) | your-side |
| data_library/ | data + loader + refetch | ✅ |

## 4. SMC OBJECT INVENTORY  (all in smc_objects.py, all causal)
Structure: swings + HH/HL/LH/LL, BOS, CHoCH, trend, internal (multi-tier).
Zones: order blocks (+mitigation +breaker), FVG, IFVG, liquidity void, BPR,
  volume imbalance*, SCOB, Unicorn.
Liquidity: pools (BSL/SSL, EQH/EQL), sweeps/raids, inducement (IDM).
Entry: pullback+reaction, OTE, premium/discount, Quasimodo (faithful).
Time: sessions, Power-of-3 (AMD), Judas, killzones, Silver-Bullet.
Levels: PDH/PDL/PWH/PWL, NDOG, fib grid + extension targets, HTF bias.
Params: all in `SMCParams` (swing depth, displacement, OB rule, thresholds, OTE...).
(*Volume Imbalance inapplicable to continuous OHLC — needs tick/gappy data.)

## 5. AUTONOMOUS ORCHESTRATOR (auto_engine.py)
Flow per closed bar: build objects → strategy signal (hook) → SAFETY GATES →
risk-size → place with hard SL/TP → manage (SL/TP) → log.
SAFETY: mode='demo' default (live needs mode='live'+confirm_live=True); hard stop
always; daily-loss halt; max positions; max total open risk; spread guard; news
blackout. Brokers: MockBroker (replay, verified) / MT5Broker (live, your-side).
Signal hook currently = pullback placeholder; real named strategies plug here (1.1.0).

## 6. VERIFIED RESULTS (research env, honest)
- Object correctness audit: 9 core detectors 100% obey their rules; QM fixed faithful.
- Identification across 9 instruments: all concepts fire, counts scale with bars.
- SMC EDGE (21y gold, decade out-of-sample): CHoCH + Silver-Bullet holds — test
  expectancy ~+0.19R, ~2%/yr at safe risk, 16/22 years positive, -5.7% max DD.
  Small but genuine. Filter-stacking that overfit train FAILED out-of-sample (caught).
- Autonomous loop: replayed on real gold, correct sizing + safety-gate firing.

## 6b. INSTRUMENT UNIVERSE (instruments.py) — v1.1.0
52 instruments registered (7 majors, 2 metals, 21 crosses, 22 exotics) in 9
correlation clusters (USD_MAJ, EUR, GBP, JPYX, COMM, CHF, METAL, SCANDI, EM).
Trader opts in via select(clusters/categories/symbols/verified_only/testable_only).
Data status: verified(10 raw) · derived(13 crosses from real majors) · live_only(29).
Testable now = 23. Backtest blocked on live_only (never faked).

## 7. DATA LIBRARY
- Synchronized set (2026-03..2026-09, 5m/15m/1h/4h): XAUUSD XAGUSD EURUSD GBPUSD
  USDJPY AUDUSD USDCHF USDCAD EURJPY. Use for cross-market / SMT.
- Deep anchor: XAUUSD_1h_deep (21y hourly gold 2004-2025). Use for OOS robustness.
- loader.load(sym,tf); refetch.py rebuilds from GitHub (~1 min).
- CAVEATS: sources public/unverified; two windows don't overlap; 2026 metal
  prices run high (verify); timezone assumed UTC.

## 8. KNOWN GAPS / PENDING  (the to-do for next session)
| Item | Status | Notes |
|---|---|---|
| SMT divergence object | pending, now BUILDABLE | data loaded (gold/silver, EUR-crosses) |
| Strategy assembly framework | pending | named SMC setups → orchestrator hook |
| Cross-market edge test | pending | run validated config on 8 other instruments |
| MQL5 native EA + object port | pending (Phase-2) | + parity harness vs Python |
| TradingView Pine port + webhook | pending (Phase-2) | windowed; parity vs Python |
| Volumetric OB | deferred | needs real volume |
| Entry-model selection (QM A vs B, etc.) | deferred | decide during strategy phase |

## 8b. RULES-FIDELITY FINDINGS (v1.2.0)
- Advanced-SMC reference doc integrated as RULES, not claims. Its headline
  entry-tightener (5-rule strict CHoCH) was MEASURED and did NOT hold out-of-
  sample (overfit) -> not adopted. base CHoCH + Silver-Bullet stays the config.
- Kept: Breaker/Mitigation split, Protected/Targeted swings (structural aids).
- Lesson reinforced: every rule is tested before adoption; sounding rigorous
  is not the same as improving out-of-sample results.

## 8c. HARDENING (v1.3.0) — robust + precise
- Data-integrity layer (validate_ohlc) repairs dirty broker data; build()
  validates by default. Param validation rejects nonsense. Warm-up guard.
- Sweeps upgraded to PRECISE real-liquidity model (each resting level swept once).
- test_engine.py = standing 16-check suite (determinism, scale-invariance,
  edge-case fuzz, causality). MUST pass before any release. Run: python test_engine.py
- Still your-side: DST edge cases & MTF repaint-safety need live MT5 data to
  fully validate (built + tested here on available data).

## 9. HONEST STANDING NOTE
This engine EXECUTES strategies faithfully and safely; it does NOT create edge.
Measured SMC edge is small (~2%/yr on gold). Any "X% per week/day" target is not
achievable on this edge without reintroducing blow-up risk. Grow return the honest
way: more instruments, more independent validated edges, sizing to a real drawdown
budget. Always forward-test on DEMO before real capital.

## 10. HOW TO RESUME (future sessions)
1. Unzip package; `python version.py` confirms build.
2. `python test_engine.py` (must ALL PASS) then `python run_backtest.py`.
3. Read §8 for the pending list; pick the next item.
4. Update CHANGELOG.md + bump version.py + update this doc on every change.
