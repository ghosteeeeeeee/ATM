# TASKS.md — Hermes Task Tracker

> Current todos, linked to projects. Updated every session.
> Format: `- [STATUS] Task (Project) — owner`
> Search with: `grep -n "\- \[ \]\|\- \[P\]\|\- \[!\]" /root/.hermes/brain/TASKS.md`

---

## Priority Tasks

### [🚨] CRITICAL: WR 13.8%, signals direction-inverted — test flip theory
**Project:** Win Rate Investigation
**Owner:** T + Agent
**Due:** 2026-04-06 (initial test)
**What:** Option 1 per incident report: flip signal direction before trading.
79% of SHORT signals had price go UP (wrong direction). ACE = 45% of all trades, 98% of ACE shorts went up.
**Action:** Code flip as 1-line change, run paper trading 24-48h, measure WR.
**Reference:** [INCIDENT_WR_FAILURE.md] — 4 options (flip, fix flip, fix source, wider SL)

---

### [!] WAIT signals never re-reviewed (Signal Quality)
**Project:** Signal Quality Improvement
**Owner:** Agent
**Due:** 2026-04-06
**What:** 5 signals in WAIT state: BIGTIME, SNX, ORDI, DYDX, ZETA
**Action:** Review each in signals DB — approve, reject, or keep waiting.

---

### [!] Hermes Gateway — systemd service install (Gateway Setup)
**Project:** Hermes Gateway Production Setup
**Owner:** T
**Blocked by:** T provides platform tokens
**What:** Install `hermes-gateway` as a proper systemd service instead of running via nohup.
**Steps:**
1. T provides: `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, etc.
2. Configure in `~/.hermes/.env`
3. Change bind from `127.0.0.1` to `0.0.0.0` (if exposing externally)
4. Run: `hermes-gateway install && hermes-gateway start`
**Current state:** Running on port 18790 via nohup (PID 1196631)
**Link:** [PROJECTS.md#Hermes Gateway Production Setup]

---

### [!] Tokyo PG server wake (Tokyo <-> Dallas Sync)
**Project:** Tokyo <-> Dallas Sync
**Owner:** T
**What:** Wake Tokyo server (10.60.72.219) from sleep mode so PostgreSQL brain DB is reachable.
**Why it matters:** `signal_schema.py` functions (workflow state, trade metadata) can't reach the authoritative DB while Tokyo is asleep.
**Action:** T wakes Tokyo server via AWS console or similar.
**Link:** [PROJECTS.md#Tokyo <-> Dallas Sync]

---

## Queued Tasks (Next Sprint)

### [ ] Cascade flip: check APPROVED signals (Signal Enhancement)
**Project:** Cascade Flip Enhancement
**Owner:** TBD
**Effort:** ~1 hr
**What:** Modify `check_cascade_flip()` in `position_manager.py` to query `decision IN ('PENDING', 'APPROVED')` instead of just PENDING.
**Benefit:** Faster flip confirmation — APPROVED signals (conf=80%+) fire before PENDING in the signal lifecycle.
**Reference:** [DECISIONS.md#2026-04-05 | Regime filter applies to APPROVED signals path]
**Link:** [PROJECTS.md#Cascade Flip Enhancement]

---

### [ ] Session checkpoint/restore system (Session Persistence)
**Project:** Session Checkpoint/Restore System
**Owner:** TBD
**Effort:** ~4-6 hrs
**What:** Build full session snapshot/restore for hermes-agent LLM sessions.
**Why:** Hermes has `checkpoints: { enabled: true }` for conversation compression (shadow git repos) but NOT for crash recovery. If agent crashes mid-session, full context is lost.
**Spec:**
- Serialize full conversation state per turn
- Store in `~/.hermes/sessions/{id}/snapshots/`
- Prune to 50 snapshots
- `hermes session restore` command
**Link:** [PROJECTS.md#Session Checkpoint/Restore System]

---

### [ ] 282 low-confidence signals investigation (Signal Quality)
**Project:** Signal Quality Improvement
**Owner:** Agent
**What:** 282 signals below 55% confidence in last hour — signal gen may be flooding.
**Action:** Investigate signal_gen.py — are we generating signals for tokens that don't meet quality thresholds? Should we add a minimum confidence gate before signals are written to DB?
**Link:** [PROJECTS.md#Signal Quality Improvement]

---

### [ ] A/B test variants — need more trades (A/B Testing)
**Project:** Signal Quality Improvement
**Owner:** Agent
**What:** 3 AB test variants with < 5 trades — entry-timing, trailing-stop (2 variants). Too early to conclude.
**Action:** Let them run. Check again after 20+ trades per variant.
**Link:** [PROJECTS.md#Signal Quality Improvement]

---

## Future Build Ideas (Backlog)

> These are exploratory — not yet scheduled. See [PROJECTS.md#Signal Quality Improvement] for context.

- [ ] **Volume displacement filter** — only trigger on breakout + displacement > 0.5%
- [ ] **ATR-adaptive SL/TP** — SL = 1.5× ATR(14) instead of fixed %
- [ ] **ADX trend strength filter** — ADX < 20 = ranging, prefer mean-reversion
- [ ] **Scale-out TP system** — TP1/TP2/TP3 (1R/2R/3R) instead of single exit
- [ ] **Wave quality metric** — HMA slope to distinguish clean swell from chaos
- [ ] **Funding rate integration** — negative funding = tailwind for SHORTs
- [ ] **Wave-of-interest filter** — top 50 tokens in regime direction + speed > 50

---

## Completed (this session)

- [x] Run signal compaction — expired 903 stale WAIT signals, rebuilt hot-set 4→13 tokens
- [x] Build checkpoint_utils.py — crash recovery snapshots
- [x] Build event_log.py — structured audit trail
- [x] Add token budget to ai_decider.py
- [x] Instrument decider-run.py with checkpoints + log_event
- [x] Instrument hl-sync-guardian.py with checkpoints + log_event
- [x] Add workflow_state to signal_schema.py + DB migration
- [x] Run integration test suite — 50/50 tests pass
- [x] Remove OpenClaw (binary, npm, 54 systemd units)
- [x] Start hermes-gateway on port 18790
- [x] Restart hermes-git-release.timer (was dead since Apr 2)
- [x] Audit all 47 OpenClaw skills vs Hermes tools
- [x] Create DECISIONS.md — decision log
- [x] Create PROJECTS.md — project tracker
- [x] Create TASKS.md — task tracker (this file)

---

## Legend

| Prefix | Meaning |
|--------|---------|
| 🚨 | Urgent — blocking or causing losses |
| [!] | High priority — needs T action |
| [ ] | Queued — ready to pick up |
| [P] | In progress |
| [x] | Done |

---

*Format: `- [STATUS] Task (Project) — owner` — update status when it changes.*
*How to read: Most urgent at top. Completed tasks move to bottom section.*