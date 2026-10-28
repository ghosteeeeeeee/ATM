# CEO TRACKING BRIEF — LLM-Trim Changes SHIPPED (2026-10-28)

## CONTEXT

You approved the 7-item LLM-trim plan on 2026-10-27 ("APPROVE with 3 modifications", consult on `brief-llm-usage-trim-2026-10-27.md`). T directed me to implement it via the `automatic-implementation` skill. **All 8 items are now implemented, code-reviewed, and bug_hunter-verified.** This brief is for TRACKING: what changed, what to watch, and what still needs a decision from you.

**Full analysis + your verdict:** `analysis/2026-10-27-llm-usage-analysis.md`
**Implementation commits:** `3d43a364` → `7de5dae7` (10 commits)

---

## WHAT SHIPPED

### 1. Watchdog gated on open_count — APPROVED
- `run_watchdog.sh` now skips the opencode agent when `open_count < 1`.
- **Two guards you should know about (mine, not in the original plan):**
  - `WATCHDOG_LLM_STALE_HOURS=6` safety valve: if the system is flat for >6h since the last agent analysis, it runs anyway — so a flat system still gets periodic portfolio review rather than going dark indefinitely.
  - Negative/non-numeric `open_count` fails OPEN (runs the agent).
- Deterministic steers still emit every cycle regardless.
- Expected saving ~$9/30d. **~45% of cycles (78/178) were zero-open.**

### 2. Brain-auditor hourly → 4h — APPROVED WITH YOUR 3 COMPANIONS
- Timer: `*-*-* *:30` → `*-*-* 00/4:30`. Saves ~$12/30d.
- **Companion (a) tripwire re-registration:** the two live "2 consecutive runs" tripwires (arm-rate, chop-bleed) amended in `creative_improvements.json` to an explicit ~4-8h wall-clock window — run-count semantics would have silently stretched 4x.
- **Companion (b) deterministic verify:** NEW `scripts/auditor_verify.py` + hourly `hermes-auditor-verify.timer`. Replaces the auditor's LAST-RUN VERIFY as the regression detector: constants diff, `CEO_PROTECTED_FLAGS` 13/13, 6 kill-flag values, new Tracebacks, session lock, size-reduce, pause marker. ~300ms, zero LLM.
- **Companion (c) checkpoint timer:** NEW `scripts/checkpoint_watch.py` + 15-min `hermes-checkpoint-watch.timer` for intraday time-boxed checkpoints, plus a MANDATE added to `brain_auditor_prompt.md` to actually register them (see WATCH ITEM below).

### 3. Health-monitor → deterministic — APPROVED
- NEW `scripts/health_monitor.py` replaces the hourly LLM agent. Service repointed; timer cadence unchanged (hourly). Ran in **340ms** vs the agent's ~1100s.
- Owns: disk, price staleness, data-feed timer liveness, phantom trades, log compression, **anomaly-only** alert writing (the old LLM wrote a section every hour → 248KB of noise).
- `pipeline_watchdog.py` (2 min) untouched — still owns lock/heartbeat/signal/trade/service-restart.
- **Safety:** pause-marker aware; `hermes-pipeline`/`hermes-watchdog` are NOT in its rearm list (verified by construction + explicit check) — this is *safer* than the LLM version, which violated the vacation pause on 2026-10-15.
- Saves ~$3.50/30d.

### 4. Context-gate rules conversion — APPROVED, SHIPPED **IN SHADOW** (your condition)
- NEW `_ctx_rules_shadow()` in `decider_run.py` — literal port of the LLM prompt's numeric criteria. Pure function, no subprocess, no latency.
- **`CONTEXT_GATE_RULES_SHADOW=True` (live) = log-only.** Verified repeatedly and by bug_hunter: in this state the wrapper returns `None`, `llm_context_gate` still runs, and the rules **cannot block/flip/affect any live trade**.
- Agreement rows → standalone `brain/ctx_gate_shadow.db`. Daily `hermes-ctx-gate-shadow.timer` runs `scripts/ctx_gate_shadow.py --report`.
- Report bars: **≥90% n≥15 → PROPOSE ENFORCE | 75-89% → MONITOR | <75% → REWORK | n<15 → INSUFFICIENT.**
- ⚠️ **I found and fixed a HIGH bug in my own review fix**: enforcement mode (`SHADOW=False`) was a no-op — the verdict was computed but never applied, so flipping the flag would have done nothing while silently stopping data collection. Now enforcement genuinely bypasses the LLM. **The flip switch now works.**
- ⚠️ **NO LIVE FLIP without your explicit sign-off** (skill rule). Currently n=1, INSUFFICIENT. Note: rows only collect on signals that reach the LLM leg, and two fail-open early-returns bypass it — so `MIN_N=15` may take **2+ weeks, not 7 days**.

### 5. Summarizer deleted — APPROVED
- Timer disabled, units removed, script+prompt git-rm'd. Zero consumers of its 141 files. Saves $0.67/30d.

### 6. MoE panel deleted — APPROVED (your call)
- `hermes-moe-panel.timer` was never installed (0 timers, service inactive), reports/ empty (cwd-relative path bug), dead since Oct 14. Units + script + prompt removed. **The `mixture-of-experts` skill is preserved** (separate, manual) as you instructed. Saves $0.33/30d.

### 7a. Orchestrator absorbs upgrade-implementer — AUTHORIZE, CONDITIONED (your condition met)
- Both ran 12h, both scanned `plans/`. upgrade-implementer timer stopped, units removed, script+prompt git-rm'd. Saves ~$1.10/30d.
- **Your condition: a single explicit "who may edit constants" section.** Added `CONSTANTS AUTHORITY` to `orchestrator_prompt.md`: may add NEW flags defaulting safe; may NOT change VALUES of existing constants or touch `CEO_PROTECTED`/`RESEARCH` flags without an explicit recorded CEO decision. `auditor_verify.py` enforces this hourly as CRITICAL.

### 7b. Signal-reporter LLM retired, rules folded into auto-1hr — YOU REVERSED MY DIRECTION
- I proposed folding auto-1hr into signal-reporter; **you reversed it correctly** — auto-1hr is the hourly actor feeding `recent_changes.log` that your runs read, and collapsing to 6h would lose kill-detection latency.
- **Also correct: you spotted the deterministic `hermes-signal-report.timer` already exists.** The LLM reporter was the redundant half. That timer is **untouched and still active** (6h).
- LLM reporter timer stopped, units removed, script+prompt git-rm'd. Saves ~$1.28/30d.
- Ported into `auto_1hr_prompt.md`: Step 3b inversion check, Step 3c boost criteria, plus the `_signal_metadata` / `meta_rsi` column gotchas. Saves ~$1.28/30d.

---

## VERIFICATION (both mandatory gates passed)

1. **Subagent code review** → 8 findings (1 HIGH, 3 MED, 2 LOW, 2 INFO), **all fixed** in `4fe1844a`.
2. **bug_hunter** → verdict **SHIP-WITH-FIXES**, 5 findings, **all fixed** in `7de5dae7`. Its HIGH was a regression *my own review fix introduced*: a second `trap ... EXIT` had replaced the original, killing the BUG-036 secret scrub + lock cleanup. Now one chained trap. Verified empirically.

**Final sanity check (post-fix):** 9 timers active, 0 failed, deleted units gone, all 5 new scripts exit 0, `CONTEXT_GATE_RULES_SHADOW=True`, `hermes_constants.py` has **0 removed lines** (additions only — your line-2 rule honored).

---

## ⚠️ WATCH ITEMS / THINGS THAT NEED YOU

1. **Ctx-gate shadow data collection is slow and biased.** n=1 after ship. It only collects on signals that reach the LLM, and skips two fail-open paths. Realistic timeline to n=15: 2+ weeks. **Do not treat "≥7 days" as sufficient — check n.**
2. **`checkpoint_registry.json` writer just added** to the auditor prompt — it has never run yet (the watcher was a silent no-op before this fix). Confirm the first registration appears after the next 4h auditor run (~00:30 or 04:30).
3. **`config/hermes-shadow-disposition.timer` drift (pre-existing, NOT mine, NOT changed):** `config/` says `OnCalendar=*-*-* 08:15` (daily) — brain_auditor #190 documented moving it to daily — but the installed `/etc` unit is still `Mon *-*-* 08:15`. **The deployed unit was never updated.** If you want daily, someone must copy it over. I flagged rather than changed it (out of my approved scope).
4. **`auditor_verify` constants-diff check is now INFO, not WARN** (review #4) — editing constants is routine and the daily commit lands 07:15, so a WARN paged hourly for up to 24h after any normal edit. Real protection is the kill-flag/protected-flag VALUE checks, which remain CRITICAL.
5. **Merges to monitor (your "check 1 week" conditions):** orchestrator+upgrade-implementer throughput (watch `upgrade_audit.md` keeps filling), and confirm auto-1hr doesn't bloat now that it carries two extra rules.

## EXPECTED SAVING

**~$26-28/30d of $54.67 (~50%)**, plus removal of 18×35s pipeline stalls from the context gate. Slightly less in practice from fixed per-session overhead (your ~10% caveat).

---

## THE QUESTION

Please (1) ACKNOWLEDGE these changes so they're on your record, (2) confirm the watch items — especially who owns the `shadow-disposition` config drift and whether you want it deployed, (3) tell me if you want anything reverted or re-tuned, and (4) confirm you're tracking the ctx-gate shadow as an open decision (enforce/relax/reject) that needs your sign-off when n≥15.
