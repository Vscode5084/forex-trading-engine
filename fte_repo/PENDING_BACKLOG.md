# FOREX TRADING ENGINE — PENDING BACKLOG
**Living to-do. Last updated: 2026-09-22 (v1.4.0 — batch executed)**

> v1.4.0 CLOSED (built+tested): A1,A2,A5,A6 (precision), B1 (SMT), D1,D2,D4,D5 (strategy+targets+de-risk), E6 (regime flag).
> STAGED (need dedicated build, testable): A3,A4,A7,B2,B3,C1,C2,C3,D3,E2.
> BLOCKED (not closeable here): B5,B6,B8,G1,G2,G3 (need real volume / unreachable data); F1-F4 (Phase-2, MQL5/Pine can't compile-verify here); E1,E3,E4,E5 (live MT5 your-side).

> Priority: P1 = high value / do first · P2 = valuable · P3 = later/refinement
> Status: OPEN · IN-PROGRESS · DONE (move to CHANGELOG when DONE)
> Testable = can be built+verified in research env · Your-side = needs live MT5 / multi-feed / TV

---
## A. PRECISION UPGRADES (engine objects)
| ID | Item | Priority | Testable? | Source |
|----|------|----------|-----------|--------|
| A1 | **Sweep validation flag** (sweep→displacement→CHoCH→FVG sequence; tag reversal vs continuation) | P1 | yes | sweep-test doc |
| A2 | Real-liquidity sweeps to also test EQH/EQL clusters + PDH/PDL/PWH/PWL (not just swings) | P1 | yes | sweep-test doc |
| A3 | Catalyst-candle OB in overlapping clusters (the candle that swept the cluster) + 50% mean-threshold | P2 | yes | advanced-SMC doc |
| A4 | Precise inducement (IDM) = the specific minor pullback that led to the final high/low (tighten proxy) | P2 | yes | advanced-SMC doc |
| A5 | Displacement ↔ FVG consistency (a displacement bar should reliably leave a detectable gap) | P2 | yes | advanced-SMC doc |
| A6 | OB sub-types: propulsion / rejection / vacuum blocks; shadow (wick) blocks | P3 | yes | advanced-SMC doc |
| A7 | Inducement hierarchy: minor (LTF scalper trap) vs major (HTF swing trap) | P3 | yes | advanced-SMC doc |

## B. NEW OBJECTS / AXES
| ID | Item | Priority | Testable? | Notes |
|----|------|----------|-----------|-------|
| B1 | **SMT divergence** (correlated pairs diverge at liquidity) | P1 | yes* | *needs synchronized data — HAVE IT now (gold/silver, EUR-crosses) |
| B2 | Wyckoff schematics: accumulation/distribution phases, spring/UTAD, SOS/SOW, LPS/LPSY | P2 | yes | distinct lens; mechanizable phase detection |
| B3 | IPDA data cycles (20/40/60-day lookback) as optional filter | P3 | yes | ICT; value unproven → add + measure |
| B4 | Macro time windows (discrete algorithmic minutes) as filter | P3 | yes | ICT; value unproven |
| B5 | CVD / order-flow axis | P3 | partial | non-SMC; needs real volume (this data unreliable) |
| B6 | Volumetric OB (volume-weighted) | P3 | no | needs reliable volume — deferred |
| B7 | Volume Imbalance | — | n/a | INAPPLICABLE to continuous OHLC (documented) |

## C. MULTI-TIMEFRAME (the biggest detection upskill)
| ID | Item | Priority | Testable? | Notes |
|----|------|----------|-----------|-------|
| C1 | **Causal MTF handoff** (HTF POI → LTF execution, repaint-proof) | P1 | partial | build alongside first MTF strategy; DST/repaint = your-side |
| C2 | Synchronized MTF object detection (Daily→H4→M15→M1 cascade) | P1 | partial | depends on C1 |
| C3 | Order-flow chains (sequence OB→FVG→liquidity as one narrative) | P2 | yes | turns detection into setups |

## D. STRATEGY LAYER (do WITH the trader)
| ID | Item | Priority | Testable? | Notes |
|----|------|----------|-----------|-------|
| D1 | **Strategy-assembly framework** (compose named SMC setups from objects into orchestrator signal hook) | P1 | yes | unlocks everything; user + engine jointly |
| D2 | Named strategies: OB-retrace, sweep-reversal, OTE, Silver-Bullet, QM, Unicorn, Power-of-3 | P1 | yes | one at a time, each measured |
| D3 | Entry-model selection (Aggressive limit-touch vs Conservative LTF-CHoCH refinement) | P2 | yes | deferred earlier; decide per strategy |
| D4 | DoL target engine (PDH/PDL/PWH/PWL/PMH, 80/20 partials, opposing pools) wired to exits | P2 | yes | we have the levels; not yet targeting with them |
| D5 | De-risk-on-drawdown sizing (smaller underwater, restore on recovery) | P2 | yes | the safe inverse of recovery-trade |

## E. LIVE EXECUTION / ROBUSTNESS (your-side validation)
| ID | Item | Priority | Testable? | Notes |
|----|------|----------|-----------|-------|
| E1 | Multi-feed consensus guard (confirm break across OANDA/FXCM/ICE; degrade to single) | P2 | your-side | needs multi-feed access; anti-spread-spike |
| E2 | Tiered alert layer (Tier-1 HTF tripwire → Tier-2 LTF execution → invalidation) | P2 | partial | notification module for auto-engine/EA |
| E3 | Spread/rollover audit (mute broker rollover hour, spread spike logger) | P2 | your-side | from sweep-test doc |
| E4 | Live-path validation: auto broker capture, copy_rates, MT5Broker order execution | P1 | your-side | written; validate on demo |
| E5 | DST + MTF repaint-safety validation on live data | P2 | your-side | built/tested on available data |

## F. PLATFORM PORTS (Phase 2)
| ID | Item | Priority | Notes |
|----|------|----------|-------|
| F1 | MQL5 native EA + full object-layer port | P1(P2 phase) | + parity harness vs Python |
| F2 | Parity harness (MQL5/Pine vs Python, bar-for-bar) | P1(P2 phase) | proves ports faithful |
| F3 | TradingView Pine port (windowed) | P2 | native TV detection + alerts |
| F4 | TradingView webhook→broker bridge | P2 | ToS-clean live path |

## G. DATA
| ID | Item | Priority | Notes |
|----|------|----------|-------|
| G1 | More multi-year, multi-instrument real data (verify the 29 live_only, deepen the 13 derived) | P1 | biggest single upskill to trust edges |
| G2 | Real historical economic-calendar CSV (for backtest news-blackout) | P2 | live EA uses MT5 native calendar |
| G3 | Tick-level data (for wick-exact fills, VI, execution realism) | P3 | needs paid/broker source |

---
## SUGGESTED FIRST BATCH (when we execute)
Highest value, mostly testable now, builds on the hardened v1.3.0 base:
1. **D1 strategy-assembly framework** (the keystone — everything routes through it)
2. **A1 + A2 sweep validation & full-liquidity sweeps** (sharpen the trigger)
3. **B1 SMT divergence** (new independent axis, data now available)
4. **C1 causal MTF handoff** (built alongside the first MTF strategy in D2)
5. **D4 DoL target engine** (real exits for the strategies)
Then measure each (D2), and fold platform ports (F) into Phase 2.
