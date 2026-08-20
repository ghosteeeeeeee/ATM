# Playbook — How We Work

Operational knowledge for the Hermes trading system. Read this when you're unsure
how to do something, not just what to do.

---

## Where Things Go

| What | Where | Why |
|------|-------|-----|
| Plans/specs | `plans/YYYY-MM-DD_topic.md` | Time-stacked, searchable |
| New signals | `scripts/signals/your_signal.py` | Registered in `signals/__init__.py` |
| Constants/thresholds | `hermes_constants.py` | Single source of truth, never hardcode |
| Paths | `scripts/paths.py` | Import with `from paths import *` |
| Runtime state | `/root/.hermes/data/` (HERMES_DATA) | Gitignored, local only |
| Served files | `/var/www/hermes/data/` (WWW_DATA) | nginx, dashboard, kill switch |
| Logs | `/var/www/hermes/logs/` | pipeline.log, signals.log |
| Brain/lessons | `brain/DECISIONS.md`, `brain/tradingnotes.md` | Persistent learnings |
| Skills | `skills/` — each has `SKILL.md` + `references/` | Modular, self-contained |
| SOPs | `SOPs.md` (root) | Plans, commits, signals, debugging, memory |
| Playbook | `brain/PLAYBOOK.md` (this file) | Do's/don'ts, lessons, file conventions |

## Skills

Each skill lives in `skills/<name>/` with:
- `SKILL.md` — instructions, triggers, workflow
- `references/` — data files, templates, backtest results
- No `__init__.py` — skills are loaded by opencode, not imported

**Adding a skill:** Use the `write-trading-skill` or `add-signal` skill. Don't create skills for one-off tasks.

**When to use a skill vs script:**
- Script = runs in pipeline, automated, no LLM needed
- Skill = opencode-loaded, LLM-assisted, for human-triggered workflows

## Do's and Don'ts

### Do
- **Search before building.** Grep for existing patterns. `scripts/signals/` has 30+ signal examples.
- **Use `from paths import *`.** Every script does this. Path constants are in `paths.py`.
- **Close cursors in `finally`.** SQLite connection leaks = "database locked" errors.
- **Commit after each task.** Don't batch. Use the canonical push script, never `git push`.
- **Add debug output.** Print early, print often. We catch bugs from logs, not tests.
- **Query OpenMemory before starting.** Previous sessions left context. Don't repeat work.
- **Use systemd timers.** Never cron. `systemctl list-timers` to check.

### Don't
- **Don't hardcode constants.** Everything goes in `hermes_constants.py`. No magic numbers.
- **Don't modify `hermes_constants.py` without asking.** Line 2 says it all.
- **Don't use `git push` directly.** Use `push_gh.py`. Always.
- **Don't call `ai_decider.py`.** It's defunct. `signal_compactor.py` replaced it.
- **Don't skip bug_hunter.** Every major change gets verified. No exceptions.
- **Don't assume API data is fresh.** Check local DB first (`price_history`, `candles_5m`).
- **Don't create one-off scripts in the root.** Scripts go in `scripts/`, signals in `scripts/signals/`.
- **Don't batch commits.** One logical unit = one commit. The daily timer catches misses.

## Hard-Earned Lessons

### Signal Architecture
- **5m signals are too slow for spike detection.** The IMX spike was a single 1m candle. Use 1m data from `price_history`.
- **Volume is unreliable on Hyperliquid.** `_aggregate_1m.py` hardcodes `volume=0` for aggregated candles. Don't depend on volume for signal quality.
- **ATR compression → expansion is real.** The best signal setup: long quiet period, then sudden expansion. But the old `atr_compression.py` used 5m candles and failed.
- **Pattern scanner ATR flags are disabled for a reason.** 0% WR across the board. Don't re-enable without evidence.
- **Single-candle spikes hold.** The +0.40% breakout candle at 20:51 on IMX never went below its close for 1+ hour. No confirmation needed.

### Database
- **Two databases, not one.** `signals_hermes.db` (static, backfill) vs `signals_hermes_runtime.db` (signals, decisions). Confusing but intentional.
- **SQLite WAL mode is mandatory.** Without it, concurrent reads/writes lock up. `PRAGMA journal_mode=WAL`.
- **Cursors must close in `finally`.** Leaked cursors = "database locked" within minutes. Every script, every time.

### Pipeline
- **Lock file is `/tmp/hermes-pipeline.lock`.** Check if stuck: `cat /tmp/hermes-pipeline.lock`. It auto-releases on exit.
- **price_collector runs on its own timer.** NOT from `run_pipeline.py`. Don't try to integrate it.
- **Regime scanners run independently.** `4h_regime_scanner.py` and `15m_regime_scanner.py` are separate from the main pipeline.

### Git
- **Never `git push` directly.** The push script reads `GITHUB_TOKEN` from `.secrets.local` and handles auth. Direct push will fail or use wrong credentials.
- **Immediate commits > batched commits.** The daily timer exists as a safety net, not primary workflow.
