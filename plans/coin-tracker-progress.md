# Coin Tracker — Progress

## Phase 1: Core Collector + Dashboard

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `coin_tracker_schema.py` — DB init, per-coin table creation | ⬜ pending | |
| 2 | `coin_tracker.py` — Main collector (reads allMids + candles, writes events) | ⬜ pending | |
| 3 | `coin_tracker_score.py` — Scoring engine, composite score | ⬜ pending | |
| 4 | `coin_tracker_api.py` — JSON API for dashboard | ⬜ pending | |
| 5 | `coin_tracker.html` — Live dashboard with mini charts | ⬜ pending | |
| 6 | Integrate into `run_pipeline.py` as step 0 | ⬜ pending | |
| 7 | Systemd timer for 60s cycle | ⬜ pending | |
| 8 | Bug hunter + subagent review | ⬜ pending | |

## Phase 2: Signal Integration (Future)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 9 | Pipe agg_scores into signal generation | ⬜ pending | |
| 10 | Pattern detection (accumulation/distribution) | ⬜ pending | |
| 11 | Per-coin win rate tracking | ⬜ pending | |
| 12 | Alerting on "ready" state | ⬜ pending | |

## Decisions Log

- **2026-08-12**: Spec created. Per-coin tables in SQLite. AllMids from existing cache. Dashboard with SVG sparklines.
