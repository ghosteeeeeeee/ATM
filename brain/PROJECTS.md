# PROJECTS.md — Hermes Project Tracker

> Active and historical projects. Updated at end of every session.
> Format: `## Project Name | Status | Owner | Last updated`
> Search with: `grep -n "Status:\|Owner:\|## \|### " /root/.hermes/brain/PROJECTS.md`

---

## Trading Pipeline Upgrade (Track A)
**Status:** ✅ COMPLETE — 2026-04-05
**Owner:** Agent
**Summary:** Complete overhaul of crash recovery and audit infrastructure for the trading pipeline.
**Key decisions:** [DECISIONS.md#2026-04-05]
**Blockers:** None

### Deliverables
| Component | File | Status |
|-----------|------|--------|
| Crash recovery snapshots | `/root/.hermes/scripts/checkpoint_utils.py` | ✅ Done |
| Structured event audit trail | `/root/.hermes/scripts/event_log.py` | ✅ Done |
| Token budget for ai_decider | `/root/.hermes/scripts/ai_decider.py` (+76 lines) | ✅ Done |
| Pipeline instrumentation | `/root/.hermes/scripts/decider-run.py` (+41 lines) | ✅ Done |
| Guardian instrumentation | `/root/.hermes/scripts/hl-sync-guardian.py` (5 patches) | ✅ Done |
| Workflow state in DB | PostgreSQL `trades.workflow_state` column | ✅ Done |
| Integration test suite | `/root/.hermes/scripts/test_upgrade_integration.py` (50 tests) | ✅ Done |

---

## Hermes Agent Core (Track B)
**Status:** ⚠️ MOSTLY COMPLETE — 2026-04-05
**Owner:** Agent
**Summary:** Remove OpenClaw dependencies, consolidate Hermes as primary agent framework.
**Key decisions:** [DECISIONS.md#2026-04-05] (OpenClaw removal, Hermes gateway, QMD declined)
**Blockers:** Session checkpoint/restore system not built (~4-6 hrs work)

### Sub-items
| Item | Status | Notes |
|------|--------|-------|
| Config version | ✅ Done | Already at v11 |
| QMD memory backend | ✅ Declined | File-backed memory sufficient |
| Hermes gateway primary | ✅ Done | Running on 127.0.0.1:18790 |
| OpenClaw removal | ✅ Done | Binary, npm, 54 systemd units removed |
| Session checkpoint system | ⚠️ Pending | Would need ~4-6 hrs to build |
| Tool cleanup (47 skills) | ✅ Done | 8 superseded, 12 kept, 27 deprecated |
| Skill conflict resolution | ✅ Done | 0 conflicts |
| hermes-git-release.timer | ✅ Done | Restarted and active |

---

## Session PM System (Project Management Infrastructure)
**Status:** 🚧 IN PROGRESS — 2026-04-05
**Owner:** Agent + T
**Summary:** Build bulletproof project management system so nothing gets lost across sessions.
**Blockers:** None — just needs discipline

### What this is
Plain Markdown files in brain — no API, no dependencies, survives everything:
- `DECISIONS.md` — why we made each call, date, revisit date
- `PROJECTS.md` — active projects, owner, status, blockers
- `TASKS.md` — current todos, linked to projects

### Why Markdown over Linear/Obsidian
- Already in brain (git-backed)
- Dead simple — T lives in terminal
- No API keys, no external services
- I update at end of every session automatically

### Rules
1. Every significant decision → `DECISIONS.md`
2. Every active project → card in `PROJECTS.md`
3. Every session → I read both files first, update at end
4. Revisit dates are real — I check them

---

## Pipeline Health Monitoring (WASP)
**Status:** ✅ ACTIVE — Ongoing
**Owner:** Agent
**Summary:** WASP (System Health & Anomaly Detector) runs every 5 min via cron. 0 ERRORS currently, 5 non-blocking warnings.
**Key decisions:** [DECISIONS.md#2026-04-05] (why we built WASP)
**Blockers:** None

### Current State (2026-04-05)
- WASP cron: INSTALLED (`hermes-wasp.timer` every 5 min)
- Pipeline: RUNNING (every 1 min)
- HL cache: FRESH
- 8 open positions (all SHORT, real HL): MORPHO, ZORA, TRX, UNI, ASTER, ZEC, SKY, TST
- Live trading: ON (`hype_live_trading.json: live_trading=true`)

### Warning Detail
5 non-blocking warnings — check `hermes-wasp.service` logs for specifics.

---

## Hermes Gateway Production Setup
**Status:** ⚠️ PARTIAL — 2026-04-05
**Owner:** T
**Summary:** Hermes gateway running but not as systemd service. Platform tokens (Telegram, Discord, etc.) not configured.
**Blockers:** Platform token configuration (T needs to provide these)
**URL:** `http://127.0.0.1:18790` (loopback only)

### What needs to happen for production
1. T provides: `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, etc.
2. Configure tokens in env or `~/.hermes/.env`
3. Change bind from `127.0.0.1` to `0.0.0.0` (or reverse proxy)
4. Install as systemd service: `hermes-gateway install && hermmes-gateway start`

---

## Tokyo <-> Dallas Sync
**Status:** ⚠️ BLOCKED — Tokyo PG server is asleep
**Owner:** T
**Summary:** PostgreSQL brain DB on Tokyo (10.60.72.219) is the authoritative trade store. Dallas services need to sync against it. Tokyo is currently in sleep mode and unreachable.
**Blockers:** Tokyo server awake (T needs to wake it)
**Key decisions:** [DECISIONS.md] (why PostgreSQL over SQLite for trade state)

### What's affected
- `signal_schema.py` — connects to Tokyo PG for `trades` table
- `update_trade_workflow_state()` — writes to PostgreSQL
- Real-time trade state for guardian reconciliation

---

## Win Rate Investigation
**Status:** 🚨 CRITICAL — 2026-04-05
**Owner:** T + Agent
**Summary:** WR is 13.8% (961 trades, Mar 10-25). 79% of SHORT signals had price move against us. ACE = 45% of all trades, 98% of ACE shorts went UP. Signal direction appears systematically inverted.
**Blockers:** None — test is ready to run
**Key decisions:** [INCIDENT_WR_FAILURE.md] — 3 options, T chose Option 1

### The Numbers
| Metric | Value |
|--------|-------|
| WR | 13.8% |
| Total PnL | -$10.56 |
| Stopped out | 78% |
| SHORTs wrong direction | 79.4% |
| ACE concentration | 45% of all trades |

**Key decisions:** [INCIDENT_WR_FAILURE.md] — 4 options, T chose Option 1

### Options
1. **Option 1 (chosen):** Flip signal before trading — 1-line change, test paper 24-48h
2. **Option 2:** Fix trade flip to reverse faster (still loses on initial wrong entry)
3. **Option 3:** Fix signal gen at source (extensive, days to weeks)
4. **Option 4:** Increase stop-loss tolerance (⚠️ danger — lose even more per trade)

---

## Signal Quality Improvement
**Status:** 🚧 ONGOING — 2026-04-05
**Owner:** Agent
**Summary:** 282 signals below 55% confidence in last hour — signal gen may be flooding. 5 WAIT signals never re-reviewed: BIGTIME, SNX, ORDI, DYDX, ZETA.
**Blockers:** None — workstream ongoing

### Current issues
| Issue | Severity | Status |
|-------|----------|--------|
| Signal flooding (282 low-confidence) | Medium | Investigating |
| WAIT signals never re-reviewed | Medium | Need re-review |
| 3 AB test variants < 5 trades | Low | Too early to conclude |

---

## Session Checkpoint/Restore System
**Status:** ⚠️ DEFERRED — 2026-04-05
**Owner:** TBD
**Summary:** Hermes does NOT have session snapshot/restore for the LLM agent. `checkpoints: { enabled: true }` in config.yaml is the conversation compression system (shadow git repos), not crash recovery. Would need: serialize full conversation state → `~/.hermes/sessions/{id}/snapshots/` → prune to 50 → `hermes session restore` command.
**Effort:** ~4-6 hours to build
**Blockers:** Priority — less urgent than pipeline trading issues

---

## Cascade Flip Enhancement (APPROVED signals)
**Status:** 📋 QUEUED — 2026-04-05
**Owner:** TBD
**Summary:** `check_cascade_flip()` currently only checks PENDING signals for flip confirmation. Should also check APPROVED signals (conf=80%+) to get flip confirmation faster.
**Reference:** [DECISIONS.md] (cascade flip APPROVED idea)
**Blockers:** None — small change, ~1 hr work

---

*Format: `## Project Name | Status | Owner` — update status when it changes.*