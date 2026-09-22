# Forex Trading Engine — Changelog

All notable changes. Format: Semantic Versioning (MAJOR.MINOR.PATCH).

## [1.4.1] — 2026-09-22 — Live workflow enablement
### Added
- report.py: standardized run reporter -> runs/<ts>/summary.json + trades.csv +
  events.log + broker_profile.txt. The fixed format to hand back for analysis.
- GITHUB_SETUP.md: click-by-click repo setup (private code + optional public
  results repo Claude can read by raw URL).
- LIVE_SETUP.md: the run -> report -> upgrade loop (Drive connector or GitHub).
- run_backtest.py now writes a report bundle automatically.
### Note
- Home is now the trader's (Drive/GitHub). Claude reads results via upload,
  Drive connector, or PUBLIC github raw URL; cannot read private repos or Drive
  from its sandbox. Claude hands back files/diffs; trader commits (stays in control).

## [1.4.0] — 2026-09-22 — Backlog batch: precision + SMT + strategy framework
### Added / Closed (built + tested here)
- A1 Sweep validation flag (sweep->displacement->CHoCH->FVG => reversal-confirmed).
- A2 Full-liquidity sweeps: swings + EQH/EQL pools + PDH/PDL/PWH/PWL (source-tagged).
- A5 Sharpened displacement (disp_strict: body/range>=70%, leaves FVG).
- A6 OB sub-types (rejection / propulsion / breaker / mitigation).
- B1 SMT divergence (smt_divergence.py) across synchronized correlated pairs
  (XAU/XAG, EUR/GBP, EUR/AUD, GBP/EURGBP...). The independent axis — now built.
- D1 Strategy-assembly framework (strategies.py) + REGISTRY.
- D2 Named strategies: ob_retrace, sweep_reversal, choch_silver_bullet, ote.
- D4 DoL target engine (nearest opposing PDH/PDL/PWH/PWL/dealing-range).
- D5 De-risk-on-drawdown sizing in auto-engine (cut risk when underwater; never martingale).
- E6 Liquidity-regime flag (rollover/low-liquidity window; tz-verify live).
### Verified
- All 16 robustness/precision tests still PASS after the batch.
- SMT produces events on all synchronized pairs; strategy framework yields signals.
### Staged (testable, need dedicated build): A3 catalyst-OB refine, A4/A7 IDM tags,
  B2 Wyckoff, B3 IPDA levels, C1/C2 causal MTF handoff, C3 order-flow chains, D3
  entry-model select, E2 tiered alerts.
### Blocked (honest): B5/B6/B8 & G1/G2/G3 need real volume / unreachable data;
  F1-F4 Phase-2 (MQL5/Pine — can't compile-verify here); E1/E3/E4/E5 live MT5 (your-side).

## [1.3.0] — 2026-09-22 — Robustness & Precision hardening
### Added (robustness)
- validate_ohlc(): repairs dupes, nonpositive prices, OHLC-consistency
  violations; flags time gaps. build() validates input by default.
- validate_params(): rejects nonsensical SMCParams (swing_L too large, bad OTE...).
- Warm-up guard: no CHoCH/BOS/pullback signals before detectors are valid.
- test_engine.py: standing suite (determinism, validation, param checks,
  scale-invariance across JPY/EUR/gold, edge-case fuzzing [flat bars, spikes,
  short series], warm-up, causality, sweep-rule). 16 checks, ALL PASS. Run
  before every release = regression guard.
### Changed (precision)
- Sweeps rebuilt: PRECISE real-liquidity model. Tracks all untaken swing-high
  (BSL) / swing-low (SSL) levels; sweeps each specific resting level once
  (wick pierces + close back inside); levels closed-through are 'broken' not
  swept. Replaces the stale last-confirmed-swing proxy.
### Verified
- All 16 robustness/precision tests pass on real data across 4 instruments.
- Determinism, scale-invariance, edge-case safety, causality all confirmed.

## [1.2.0] — 2026-09-22 — SMC rules-fidelity layer (from advanced SMC reference doc)
### Added
- Breaker vs Mitigation split: OB.block_type ('breaker'=swept liquidity before
  failing / 'mitigation'=failed to sweep). OB.swept flag.
- Protected vs Targeted swings (protected = swept liquidity + subsequent BOS;
  valid stop anchors) — smc_objects: protected_swings.
- Strict 5-rule CHoCH (choch_strict): body-close + swept opposing liquidity +
  displacement. (Premium/discount is an ENTRY filter, not applied at break.)
- Recent-sweep arrays (rs_dir, rs_age).
### Measured / decision (measure-don't-assume)
- Strict CHoCH + Silver-Bullet vs base + Silver-Bullet on 21y gold, out-of-sample:
  base test exp +0.187 PF 1.31 (n=207)  vs  strict test exp +0.122 PF 1.19 (n=52).
  Strict overfit (better in-sample, WORSE out-of-sample) -> NOT ADOPTED as default.
  base CHoCH + Silver-Bullet remains the validated config. choch_strict kept as
  an available option for further testing on other instruments/timeframes.
### Notes
- Breaker/Mitigation split & Protected/Targeted swings are structural objects
  (not entry triggers) -> kept as engine features for the strategy-assembly phase.
- Deferred from the doc: overlapping-cluster OB refinement, DoL target matrix
  (best measured during strategy assembly against real exits).

## [1.1.0] — 2026-09-22 — Instrument universe + best-effort verification
### Added
- `instruments.py` — full universe of 52 instruments (7 majors, 2 metals,
  21 crosses, 22 exotics) with correlation clusters, pip factor, spread tier.
- Trader OPT-IN selection API: select(clusters=, categories=, symbols=,
  verified_only=, testable_only=, exclude_tiers=). Nothing trades unless chosen.
- Best-effort data verification: 23 instruments now testable
  (10 verified raw + 13 derived from real synchronized USD-majors).
### Data-status tiers
- verified (10): raw real data, wick-accurate.
- derived (13): crosses computed from real majors; OHLC wick-approximate
  (good for structure; slightly soft on exact sweep/OB wicks).
- live_only (29): no local data; tradeable when the broker feed supplies them.
### Notes
- Exotics tagged spread_tier='high'; cost model applies wide spreads. Backtest
  is blocked on live_only instruments so results are never faked.
### Pending (still in 1.1.0 scope)
- SMT divergence object; strategy-assembly framework; cross-market edge test.

## [1.0.0] — 2026-09-21  — Phase-1: MT5 + Python, auto-mode
### Added
- SMC OBJECT LAYER (`smc_objects.py`), causal / no-repaint / no-look-ahead:
  swings + HH/HL/LH/LL labels, BOS/CHoCH, displacement, order blocks
  (+mitigation +breaker), pullback+reaction (entry), FVG/IFVG, liquidity void,
  volume imbalance*, BPR, internal (multi-tier) structure, inducement (IDM),
  SCOB, Quasimodo (faithful spec), Unicorn, liquidity pools (BSL/SSL, EQH/EQL),
  sweeps/raids, OTE, premium/discount, PDH/PDL/PWH/PWL, sessions + Power-of-3
  (AMD), Judas, NDOG, fib grid + extension targets, HTF bias.
- `broker_profile.py` — auto (live MT5) / manual / hybrid capture; server→UTC,
  symbol map, spread cost.
- `news_feed.py` — economic calendar, high-impact filter, news-blackout flag,
  top-left dashboard block.
- `mt5_adapter.py` — MT5 CSV export + live copy_rates → UTC OHLC.
- `auto_engine.py` — autonomous orchestrator (detect→gate→size→place→manage→log),
  MockBroker (test) + MT5Broker (live). Safety: demo-default, hard-stop-always,
  daily-loss halt, max-positions, max-total-risk, spread guard, news blackout.
- `data_library/` — 9 instruments (5m/15m/1h/4h) + 21y hourly gold + loader/refetch.
- `version.py` — single-source brand + version.

### Verified (in research env)
- Object layer audited: 9 core detectors 100% correct; QM fixed to faithful spec.
- Broker manual/hybrid, news logic, MT5 CSV adapter, full autonomous loop on real data.
- SMC edge measured on 21y gold: CHoCH+Silver-Bullet ~2%/yr, decade out-of-sample stable.

### Known limits / your-side validation
- *Volume Imbalance inapplicable to continuous OHLC (needs tick/gappy data).
- SMT divergence: buildable now (multi-instrument data loaded) but NOT yet built.
- Volumetric OB: needs real volume (tick-count unreliable) — deferred.
- Live paths (auto broker capture, copy_rates, MT5Broker orders): validate on your MT5.
- Data sources are public/unverified; metal prices in 2026 window run high — verify.

## [Unreleased] — planned
- 1.1.0: SMT divergence object; strategy-assembly framework (named SMC setups
  into the orchestrator signal hook); cross-market edge test across 9 instruments.
- 1.2.0 / Phase-2: MQL5 native EA + object-layer port + parity harness;
  TradingView Pine port + webhook bridge.
