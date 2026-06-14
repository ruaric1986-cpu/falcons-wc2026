# Falcons WC2026 Predictor
Leaderboard site + daily WhatsApp digest.

## Source of truth
The data tables in `data/` are the single source of truth, edited directly in
this repo:
- `predictions.json` — each player's scoreline per match (`{ "<match#>": { "Player": "H-A" } }`)
- `players.json` — player list / column order
- `fixtures.json` — match list (teams, group/stage, kickoff); knockout teams & dates auto-refresh from the API
- `results.json` — final scores; once a match is recorded it's frozen and never overwritten by the API (`fetch_results` only adds new matches). Edit by hand to correct.

To change predictions, edit `data/predictions.json` and commit. The daily
GitHub Action runs entirely off these files.

The OneDrive spreadsheet is now only a **non-authoritative backup**. `./sync`
(`scripts/sync.py`) still works for exporting/importing, but running
`sync export` overwrites the canonical `data/*.json` from the sheet — only do
this deliberately if the sheet is genuinely more up to date.

Daily GitHub Action runs at 06:30 UTC (07:30 UK).
Site: https://ruaric1986-cpu.github.io/falcons-wc2026/
