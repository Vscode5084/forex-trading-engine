# GitHub Setup — click-by-click

Goal: put the engine in a repo YOU own (durable home + real version history),
and optionally expose only run RESULTS publicly so Claude can read them by URL.

## A. One-time: create the code repo (keep PRIVATE — it's your strategy IP)
1. github.com → top-right **+** → **New repository**.
2. Name: `forex-trading-engine`  ·  Visibility: **Private**  ·  Create.
3. Put the engine in it (pick one):
   - Web: repo → **Add file → Upload files** → drag the unzipped v1.4.x contents → Commit.
   - Or GitHub Desktop: Clone → copy files in → Commit → Push.
   - Or CLI: `git init && git add . && git commit -m "v1.4.1" && git remote add origin <url> && git push -u origin main`
4. Commit every upgrade I hand you, bumping version.py + CHANGELOG.md each time.

## B. Optional: a PUBLIC results repo (so Claude pulls runs automatically)
Claude's sandbox can read PUBLIC GitHub raw files (not private). To close the loop
without manual uploads, keep a tiny public repo for OUTPUTS ONLY — no strategy code.
1. New repository → name `fte-results` → Visibility: **Public** → Create.
2. Point the engine's report output here (or copy `runs/<ts>/summary.json` into it and push).
3. Give Claude the raw URL, e.g.:
   `https://raw.githubusercontent.com/<you>/fte-results/main/runs/<ts>/summary.json`
   Claude fetches it directly — no upload needed.

## C. The loop
1. Run on your MT5 box → engine writes `runs/<ts>/` (see report.py).
2. Deliver results: push summary.json to `fte-results` (public) and paste the raw URL,
   OR upload summary.json to the chat, OR use the Google Drive connector.
3. Claude analyzes → hands back changed files/diffs.
4. You save to the private repo → run `python test_engine.py` (must PASS) → commit.

## Privacy note
Public code = anyone sees your strategy logic. Recommended: **private code repo +
small public results repo** (results only). Claude cannot read private repos.
