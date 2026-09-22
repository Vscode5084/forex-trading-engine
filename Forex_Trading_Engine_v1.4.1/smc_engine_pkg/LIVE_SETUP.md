# LIVE SETUP — move the engine to your environment

The engine's home is now YOURS (my sandbox resets each session and can't reach
your machine/MT5). This is the low-friction loop for running live + shipping upgrades.

## 1. Home (pick one; both durable)
- **Google Drive**: folder `Forex-Trading-Engine/` with the unzipped v1.4.x inside.
  Connect the Google Drive *connector* in Claude → I can read your `runs/` in-chat.
- **GitHub**: private code repo (+ optional public `fte-results`). See GITHUB_SETUP.md.

## 2. Run (on your Windows box / VPS where MT5 lives)
    python test_engine.py            # must ALL PASS first
    python run_backtest.py           # sanity replay on local data
    python run_live_MT5.py           # live loop (mode='demo' by default!)
Each run writes a report bundle via report.py -> runs/<timestamp>/.

## 3. Deliver results to me (any one)
- Google Drive connector: "read the latest run in Forex-Trading-Engine/runs/"
- Upload `runs/<ts>/summary.json` (+ trades.csv) to the chat
- Public results repo: paste the raw URL to summary.json (I fetch it directly)

## 4. Upgrades back
- I hand you changed files (or a diff). You save them into the home folder,
  run `python test_engine.py` (must PASS), bump version.py + CHANGELOG.md, commit.
- I never write to your Drive/repo — you stay in control (correct for live money).

## Golden rules
- Validate on a DEMO account first. mode='live' requires confirm_live=True.
- test_engine.py must pass before any release.
- Send summary.json every run — it's the fixed format I read fastest.
