# Coin Tracker — Progress

## Phase 1: Core Collector + Dashboard

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | `coin_tracker_schema.py` — DB init, per-coin table creation | ✅ done | 362 lines, context manager for safe connections |
| 2 | `coin_tracker.py` — Main collector (reads allMids + candles, writes events) | ✅ done | 279 lines, batch reads, ~1s per run |
| 3 | `coin_tracker_score.py` — Scoring engine, composite score | ✅ done | 200 lines, importable module |
| 4 | `coin_tracker_api.py` — JSON API for dashboard | ✅ done | 122 lines, atomic JSON writes |
| 5 | `coin_tracker.html` — Live dashboard with mini charts | ✅ done | 300+ lines, SVG sparklines, filter/sort |
| 6 | Integrate into `run_pipeline.py` as step 0 | ✅ done | Runs before signal steps |
| 7 | Systemd timer for 60s cycle | ⬜ skipped | Pipeline runs every 1 min already |
| 8 | Bug hunter + subagent review | ✅ done | Fixed: connection leaks, None meta, batch writes |

## Phase 2: Signal Integration (Future)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 9 | Pipe agg_scores into signal generation | ⬜ pending | |
| 10 | Pattern detection (accumulation/distribution) | ⬜ pending | |
| 11 | Per-coin win rate tracking | ⬜ pending | |
| 12 | Alerting on "ready" state | ⬜ pending | |

## Decisions Log

- **2026-08-12**: Spec created. Per-coin tables in SQLite. AllMids from existing cache. Dashboard with SVG sparklines.
- **2026-08-12**: Phase 1 complete. 892 coins tracked, 1s cycle time. Bug hunter found connection leaks, fixed.
- **2026-08-12**: Key fix: inline DB writes in collect loop (avoided 947 open/close cycles).
