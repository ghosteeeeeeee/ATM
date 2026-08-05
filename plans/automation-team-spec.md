# Automation Team Spec — 2026-08-04

## Architecture

All automations run via **systemd timers** triggering shell scripts that pipe prompt markdown files into `opencode run` (LLM agent on port 4099). No custom frameworks — raw Python + SQLite + systemd.

```
systemd timer → shell script → cat prompt.md | opencode run --port 4099
```

---

## Core Trading Loop (always-on, ~1min)

| Component | Script | Status |
|-----------|--------|--------|
| Pipeline | `run_pipeline.py` | OK |
| Price Collector | `price_collector.py` | OK |
| Self-Close Watcher | `self_close_watcher.py` | OK |
| Profit Monster | `profit_monster.py` | OK |
| Away Detector | `away_detector.py` | OK (5min timer) |
| HL Sync Guardian | `hl-sync-guardian.py` | OK (long-running daemon) |

## LLM Agents (prompt → opencode run)

| Agent | Schedule | Prompt | Runner | Status |
|-------|----------|--------|--------|--------|
| CEO | 24h | `ceo_prompt.md` | `run_ceo.sh` | OK |
| Orchestrator | 12h | `orchestrator_prompt.md` | `run_orchestrator.sh` | OK |
| Health Monitor | Hourly (:20) | `health_monitor_prompt.md` | `run_health_monitor.sh` | OK |
| Signal Reporter | 6h | `signal_reporter_prompt.md` | `run_signal_reporter.sh` | OK |
| Blacklist Tester | 12h | `blacklist_tester_prompt.md` | `run_blacklist_tester.sh` | OK |
| Summarizer | 12h | `summarizer_prompt.md` | `run_summarizer.sh` | OK |
| Auto-1hr | Hourly (:50) | `auto_1hr_prompt.md` | `run_auto_1hr.sh` | OK |
| Upgrade Implementer | 12h | `upgrade_implementer_prompt.md` | `run_upgrade_implementer.sh` | FAILED (exit 1) |

## Supporting Scripts

| Script | Schedule | Status |
|--------|----------|--------|
| 15m Regime Scanner | 15min | OK |
| 4h Regime Scanner | 4h | OK |
| Signal Decay Detector | ~5h | OK |
| Signal Rotator | ~4h | OK |
| Signal Lifecycle | ~20h | OK |
| Signal Researcher | ~8h | OK |
| Signal Compactor (purge) | hourly | OK |
| Context Compactor | ~15min | OK |
| Better Coder | ~15min | OK |
| Error Analyzer | ~1h | OK |
| Hype Paper Sync | 5min | OK |
| Obs Dashboard | ~5min | OK |
| Study Winning Combos | hourly | OK |
| Trading Checklist | ~48min | FAILED (exit 2) |
| WASP | ~15min | OK |

## Permanent Services

| Service | Status |
|---------|--------|
| Coding MCP Server | OK (running 3 days) |
| Metrics Collector | OK |
| Smoke Test | OK (exited clean) |

---

## FAILED Services (2026-08-04)

| Service | Exit | Error |
|---------|------|-------|
| hermes-upgrade-implementer | 1 | `run_upgrade_implementer.sh` failed |
| hermes-bug-hunter | 1 | `bug_hunter.py` failed |
| hermes-git-release | 1 | `update-git.py --dry-run` failing |
| hermes-trading-checklist | 2 | usage error |
| hermes-mtf-macd-tuner | failed | loaded failed state |

---

## Proposed New Members (CEO approved)

| Member | Priority | Status |
|--------|----------|--------|
| Risk Manager (5min) | P1 | NOT BUILT — no emergency stop exists |
| Data Quality Checker (hourly) | P2 | NOT BUILT |
| Backtester | SKIP | trading-mcp covers this |
| Market Regime Detector | SKIP | duplicates existing scanners |
| Audit Logger | SKIP | git history covers this |

---

## Key Files

| Path | Purpose |
|------|---------|
| `/root/.hermes/scripts/` | All scripts |
| `/root/.hermes/automation/` | Prompt files, runners, reports |
| `/root/.hermes/systemd/` | Systemd timer/service units |
| `/root/.hermes/data/signals_hermes_runtime.db` | Signal outcomes DB |
| `/root/.hermes/scripts/hermes_constants.py` | Constants and kill switches |
| `/root/.hermes/automation/ceo_report.md` | CEO output |
| `/root/.hermes/automation/trading_log.md` | Change log |

---

## Signal Starvation Status (2026-08-04)

- **3 signals enabled** out of 64+ (MA_CROSS_MINUS, ATR_COMPRESSION, VOLUME_HL)
- Trade rate: **<1/hr** — system effectively dead
- All 7d signals negative PnL
- Dynamic inverter deployed for zscore-rising (auto-flip when WR<30%)
- Daily innovation pipeline approved (1 new candidate/day)

---

## Away Detector

**Current:** Calls CEO every 15min when T away >20min. CEO picks actionable task from kanban board.
**Timer:** `hermes-away-detector.timer` — 15min interval
**Prompt:** `automation/ceo_away_prompt.md`
**Kanban:** `automation/ceo_kanban.md` — persistent TODO/IN PROGRESS/DONE/BLOCKED board
**Log:** `logs/away_detector.log`
**Status:** DEPLOYED 2026-08-04
