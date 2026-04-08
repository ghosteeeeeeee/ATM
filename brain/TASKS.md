# TASKS.md — Hermes Task Tracker

> Current todos, linked to projects. Updated every session.
> Format: `- [STATUS] Task (Project) — owner`
> Search with: `grep -n "\- \[ \]\|\- \[P\]\|\- \[!\]" /root/.hermes/brain/TASKS.md`

---

## Priority Tasks

### [P] W&B self-learning tracking — all 3 systems (Self-Learning)
**Owner:** Agent + T
**Status:** ✅ DONE 2026-04-06 — Added to: candle_predictor, ab_utils, ai_decider. All run in offline mode, local JSONL backups written. Sweep config ready. T to provide W&B API key to enable cloud sync.

### [🚨] CRITICAL: Cascade flip DONE — thresholds lowered, SKIPPED signals added
**Project:** Cascade Flip Enhancement
**Owner:** Agent
**Status:** ✅ DONE 2026-04-06 — Thresholds lowered: ARM=-0.25%, TRIGGER=-0.50%, HF_TRIGGER=-0.35%. MIN_CONF=60%, MAX_AGE=30min. SKIPPED signals now in confluence check alongside PENDING/WAIT/APPROVED. Volume-confirmation buffer added (0.35% when vol confirms, 0.25% when not).
**Reference:** [DECISIONS.md#2026-04-06 | Cascade flip thresholds lowered + SKIPPED signals added]

---

### [!] WR flip test — outcome documented (Win Rate Investigation)
**Project:** Win Rate Investigation
**Status:** ❌ CLOSED — Flip test FAILED on 2 trades. Historical 79% SHORT-wrong finding did NOT replicate. System continues without signal flip.
**Action:** No further action needed.

---

### [!] Tokyo PG — accept SQLite-only mode permanently
**Status:** ❌ CLOSED — SQLite-only mode. PostgreSQL workflow_state feature decommissioned.
**Action:** No further action needed.

---

## Queued Tasks (Next Sprint)

### [ ] Cascade flip: check APPROVED+SKIPPED signals (Signal Enhancement)
**Project:** Cascade Flip Enhancement
**Status:** ✅ DONE 2026-04-06 — Already included in thresholds-lowered fix. SKIPPED signals added to confluence check. APPROVED signals were already included.

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

---

## Chart Pattern Recognition (Phase 1 — Bull Flag)

### [P] Build pattern_scanner.py — flag detection (Phase 1)
**Project:** Chart Pattern Recognition
**Owner:** Agent
**Status:** ✅ DONE — 2026-04-06
**What:** Created `/root/.hermes/scripts/pattern_scanner.py` with:
- `detect_bull_flag()` — flag pole (>= 3% impulse in <= 8 candles) + consolidation (< 1.5% range) + breakout confirmation
- `detect_bear_flag()` — mirror for shorts
- `detect_ascending_triangle()` — higher lows + horizontal resistance breakout
- `detect_descending_triangle()` — mirror for shorts
- `write_pattern_signal()` — emits to signals DB with `source='pattern_scanner'`
- Tested on synthetic data: bull flag detected at 68.2% ✅
- IMX confirmed: no breakout yet (resistance $0.1364, last close $0.1360) ✅
**Reference:** [PROJECTS.md#Chart Pattern Recognition]

### [P] Integrate pattern_scanner into signal_gen.py (all tokens, run FIRST)
**Project:** Chart Pattern Recognition
**Owner:** Agent
**Status:** ✅ DONE — 2026-04-06
**What:** Added `_run_pattern_signals()` to `signal_gen.py`:
- `import pattern_scanner` at top of signal_gen.py
- `_run_pattern_signals(prices_dict)` — iterates ALL tokens, calls `scan_and_write()` per token
- Called FIRST in `run()` before mtf_macd loop (line ~1941)
- 0.46s for 50 tokens — fast, non-blocking
- Pattern signals compete equally with momentum in the DB
**Reference:** [PROJECTS.md#Chart Pattern Recognition]

### [P] Add WR-based calibration for ALL signals (auto-multiplier)
**Project:** Chart Pattern Recognition
**Owner:** Agent
**Status:** ✅ DONE — 2026-04-06
**What:** Full calibration system added to `ai_decider.py`:
- `get_signal_type_stats()` — queries `signal_outcomes`, computes WR per signal type
- `get_calibration_summary()` — human-readable calibration report
- `get_category_multipliers()` — aggregated category-level multipliers
- `_wr_to_multiplier()` — WR→multiplier mapping
- `SIGNAL_TYPE_CATEGORY_MAP` — maps composite signal types to categories
- `_get_source_weight()` updated to apply WR-based calibration on top of baselines
- `PERF_CAL_MIN_TRADES = 15` — min trades before calibration kicks in

Calibration rules (ALL signals):
  WR >= 55%  → 1.5×  |  WR 45-55%  → 1.25×  |  WR 40-45%  → 0.75×  |  WR < 40%  → 0.0× (disabled)

**Current live calibration findings:**
  decider:         22.8% WR / 101 trades → DISABLED (0.0×)
  conf-2s:         33.3% WR / 39 trades → DISABLED (0.0×)
  conf-3s:         24.0% WR / 25 trades → DISABLED (0.0×)
  conf-1s:         45.5% WR / 110 trades → 1.25× (calibrated good)
  hl_reconcile:    51.0% WR / 51 trades → 1.25×
  pattern_scanner: no data yet → 1.0× baseline (1.25× override active)

Check status: `python3 -c "from ai_decider import get_calibration_summary; print(get_calibration_summary())"`
**Reference:** [PROJECTS.md#Chart Pattern Recognition]

### [ ] Test pattern_scanner on IMX ascending triangle
**Project:** Chart Pattern Recognition
**Owner:** Agent
**What:** Validate live pattern detection. When IMX breaks $0.1366 to upside with volume → first live pattern_flag signal. Track in trading.md.
**Current state:** Ascending triangle forming. Resistance $0.1364, support $0.1350, last close $0.1360. Not yet triggered.
**Reference:** [PROJECTS.md#Chart Pattern Recognition]

---

### [!] Hot-Set Compaction Rewrite — redesign 10-min pipeline (Hot-Set Redesign)
**Project:** Hot-Set Compaction Rewrite
**Status:** ⬜ OPEN — 2026-04-08
**Owner:** Agent
**Summary:** Hot-set design is broken. Signals need `review_count>=1` + 3-hour window to enter hot-set, but new signals never get reviewed fast enough. Full redesign needed: 10-min compaction, top 20 survivors, reverse signal penalization, PURGE of non-top-20. Prompt testing completed — `L_survival_rounds` + `Q_final` are best prompt variants. Key finding: MiniMax needs `max_tokens=4000+` to fit both thinking and output.
**Reference:** [.hermes/plans/2026-04-08_041613-hotset-depletion-fix.md]

---

## Future Build Ideas (Backlog)

### [ ] Trading-Docker — Step 1: Audit pipeline scripts
**Project:** Trading-Docker
**Owner:** Agent
**What:** Audit `/root/.hermes/scripts/` — confirm entry points, startup order, dependencies. Output: confirmed script list + run order for docker-entrypoint.sh
**Reference:** [PROJECTS.md#Trading-Docker], `/root/.hermes/plans/2026-04-05_183622-can-we-set-up-a-new-docker-container.md`

---

> These are exploratory — not yet scheduled. See [PROJECTS.md#Signal Quality Improvement] for context.

- [ ] **Volume displacement filter**
- [ ] **ATR-adaptive SL/TP**
- [ ] **ADX trend strength filter**
- [ ] **Scale-out TP system**
- [ ] **Wave quality metric**
- [ ] **Funding rate integration**
- [ ] **Wave-of-interest filter**

---

## Queued Tasks (Next Sprint)

### [ ] Runtime DB archival strategy — 195MB, signal_history has 697K rows
**Project:** AI Trading Machine (ATM)
**Status:** ⬜ Open
**What:** WASP warning: Runtime DB 192MB (should be < 50MB). `signal_history` table is main culprit. Need compaction or archival strategy.
**Reference:** reports.md (WASP findings)

### [ ] context_window_flooding — add threshold warning to ai_decider
**Project:** Signal Quality Improvement
**Status:** ⬜ Open — reported reports.md
**What:** ai_decider context_window_flooding identified as MEDIUM. Needs a threshold warning when context is getting too large.
**Reference:** reports.md

### [ ] all_signals conf clustering at 65% — add jitter to ENTRY_THRESHOLD
**Project:** Signal Quality Improvement
**Status:** ⬜ Open — reported reports.md
**What:** all_signals 65.6% conf (clustering at ENTRY_THRESHOLD=65). Need jitter fix so signals don't all cluster at the exact threshold.
**Reference:** reports.md

### [ ] orphan_recovery partial — decider-run doesn't handle paper-only
**Project:** Win Rate Investigation
**Status:** ⬜ Open — reported reports.md
**What:** 13 orphan_recovery trades — decider-run.py doesn't handle paper-only mode correctly.
**Reference:** reports.md

### [ ] Funding rate integration — negative funding = tailwind for SHORTs
**Project:** Signal Quality Improvement
**Status:** ⬜ Open
**What:** Use funding rate as additional signal — negative funding is tailwind for SHORT positions.
**Reference:** trading.md Future Build Ideas

### [ ] Wave-of-interest filter — top 50 tokens in regime direction + speed > 50
**Project:** Signal Quality Improvement
**Status:** ⬜ Open
**What:** Add wave-of-interest filter — only consider top 50 tokens in regime direction with speed > 50.
**Reference:** trading.md Future Build Ideas

### [ ] 30% WR winners large losers small — is this sustainable?
**Project:** Win Rate Investigation
**Status:** ⬜ Open — NEEDS ANALYSIS
**What:** 30% WR with avg +7.12% — winners large, losers small. NEEDS ANALYSIS — is cut-loser too tight?
**Reference:** trading.md Known Issues

### [ ] 9 open SHORTs concentration risk — monitor and reduce
**Project:** Win Rate Investigation
**Status:** ⬜ Open — MONITOR
**What:** 9 open SHORTs with SHORT regime bias — concentration risk. MONITOR — consider reducing SHORT concentration.
**Reference:** trading.md Known Issues

### [ ] Verify stale timeouts: winners 15 min, losers 30 min — is this intentional?
**Project:** AI Trading Machine (ATM)
**Status:** ⬜ Open — reported 2026-04-06
**What:** Stale winner = 15 min, stale loser = 30 min. Code is consistent (both correct in code and comment). But should losers be cut faster than 30 min? Current: losers get MORE time than winners. This may be backwards — losers should probably close faster.
**Current:** `STALE_WINNER_TIMEOUT_MINUTES = 15` | `STALE_LOSER_TIMEOUT_MINUTES = 30`
**Question:** Should losers be 15 min and winners 30 min (give winners more time to develop)?
**Reference:** ATM/config/stoploss.md

---

### [ ] Check guardian cron error: "No module named 'fire'"
**Project:** AI Trading Machine (ATM)
**Status:** ⬜ Open — reported 2026-04-06
**What:** `errors.log` shows `No module named 'fire'` every 60s from a cron job trying to call hl-sync-guardian. The guardian daemon itself is running (process alive) but something else (wasp or a sub-cron) is trying to invoke it incorrectly.
**Fix:** Find what's calling hl-sync-guardian with `fire` CLI, fix the invocation
**Reference:** `/root/.hermes/logs/errors.log`

---

## Completed (this session)

- [✅] **Kanban board at `/projects`** (port 54321)
  - API: `/api/config/projects` (GET/POST), data at `/var/www/hermes/data/kanban.json`
  - HTML: `/var/www/hermes/projects.html` — drag-and-drop, inline edit, priority, project labels
- [✅] ATM folder created: `/root/.hermes/ATM/`
- [✅] `ATM/config/stoploss.md` written
- [✅] SOPs.md updated
- [✅] PROJECTS.md: Trading-Docker → renamed AI Trading Machine (ATM), ATM folder structure documented
- [✅] DECISIONS.md: Added "ATM folder created" + "Cut-loser DISABLED" entries
- [✅] Run signal compaction
- [✅] Build checkpoint_utils.py
- [✅] Build event_log.py
- [✅] Add token budget to ai_decider.py
- [✅] Instrument decider-run.py with checkpoints + log_event
- [✅] Instrument hl-sync-guardian.py with checkpoints + log_event
- [✅] Add workflow_state to signal_schema.py + DB migration
- [✅] Run integration test suite
- [✅] Remove OpenClaw (binary, npm, 54 systemd units)
- [✅] Start hermes-gateway on port 18790
- [✅] Restart hermes-git-release.timer (was dead since Apr 2)
- [✅] Audit all 47 OpenClaw skills vs Hermes tools
- [✅] Create DECISIONS.md
- [✅] Create PROJECTS.md
- [✅] Create TASKS.md

---

## Post-Fix Verification (3-day monitoring)

### [ ] (P) Verify SL ATR adjustments improved win rate — owner: ai-engineer — 2026-04-09
Baseline: 51.9% WR / +13.68 USDT net (7d pre-fix). After 3 days, compare WR and net PnL to determine if ATR-based SL is more protective without being too tight.

### [ ] (P) Verify trailing stops no longer false-trigger — owner: ai-engineer — 2026-04-09
Previously `trailing_active = True` was always set due to indentation bug. Check `trailing_stops.json` and PostgreSQL `exit_reason='trailing_exit_*'` for any anomalous early trailing exits in the 3 days post-fix.

### [ ] (P) Verify phase2 buffer ATR logic working correctly — owner: ai-engineer — 2026-04-09
Inspect `trailing_stops.json` for phase2 entries. Confirm `phase2_buffer_atr` values are being used (not falling back to volume-confirmed) for trades where ATR is available.

### [ ] (P) Compare pre/post fix PnL (need baseline from before 2026-04-06) — owner: ai-engineer — 2026-04-09
Query PostgreSQL for 30-day pre-fix baseline. Current post-fix baseline: 54 trades, 51.9% WR, +13.68 USDT net over 7 days. Need historical data from before 2026-04-06 to compute delta.

### [ ] (P) Verify pattern_scanner detects any patterns at all — owner: ai-engineer — 2026-04-07
Pattern scanner has NEVER produced a signal in production (0 pattern_scanner signals in DB). Root causes identified: (1) `_get_active_tokens()` only returns 5 tokens (DYDX, MORPHO, MOVE, TST, XRP) instead of the full hot-set, so only 5 tokens get 1m candles seeded; (2) bull flag requires ≥3% pole move which is very rare on 1m candles. Test: run `python3 pattern_scanner.py TOKEN 240` on 10 different tokens and verify patterns are found OR confirm thresholds are the bottleneck.

### [ ] (P) Fix active_tokens so all hot-set tokens get 1m candles seeded — owner: ai-engineer — 2026-04-07
`_get_active_tokens()` in price_collector.py returns only 5 tokens instead of the full active universe (~236 tokens). This means only 5 tokens ever get 1m OHLCV data in `ohlcv_1m`. Fix to return all tokens that have recent prices (i.e., the full hot-set / active universe). Without this, pattern_scanner can never run on most tokens.

### [ ] (P) Add smaller-scale pattern detection (micro-flags: 0.3% pole, 0.15% range) — owner: ai-engineer — 2026-04-08
Current bull flag params (≥3% pole, ≤1.5% consolidation range) are too strict for 1m candles in sideways/low-volatility markets. Add a parallel detection mode for micro-flags with relaxed params: FLAG_POLE_MIN_PCT=0.3, FLAG_CONSOLIDATION_MAX_PCT=0.15, FLAG_POLE_MAX_CANDLES=15. These should be separate pattern types (e.g., `pattern_micro_flag`) so they can be tracked independently from real flag patterns.

### [ ] (P) Measure pattern backtest accuracy — owner: ai-engineer — 2026-04-08
Backtest patterns vs baseline (minimal prompt) on historical data. backtest_patterns.py shows B_patterns=33.3% vs A_minimal=46.7% on 30 samples — patterns are currently WORSE. Need to run on larger sample (n=200+) and determine if pattern detection parameters need tuning or if the approach is fundamentally flawed for this market regime.

### [ ] (P) Verify pattern signals can reach ai_decider hot-set scoring — owner: ai-engineer — 2026-04-08
Even if pattern_scanner starts producing signals, confirm they flow through to ai_decider scoring. Check: (1) pattern signals written to signals DB with correct source='pattern_scanner', signal_type='pattern_*'; (2) ai_decider's hot-set builder includes pattern_scanner signals in ALL_CATS; (3) pattern signals with 1.25x multiplier appear in pipeline output. Run a full pipeline cycle and grep for pattern_flag in the output.

### [ ] (P) Verify cron jobs survive sessions — owner: T — 2026-04-07
Confirm: (1) Are cron jobs implemented via the agent's built-in cron system (mcp_cronjob action='create') or via system crond/systemd? (2) Do they persist across agent restarts/reboots? (3) Are there any cron jobs showing last_status='error' that need attention? Currently 5 of 8 cron jobs show 'error' status. Investigate and fix.

### [✅] (P) Investigate Speed=50% anomaly — why only hot-set filtering through? — owner: ai-engineer — 2026-04-09
**RESOLVED 2026-04-06.** Root cause: hermes-trades-api.py line ~355 uses `e.get('speed_percentile') or e.get('momentum_score') or 50.0`. The 4 affected tokens (KSHIB, KFLOKI, KBONK, KLUNC) don't exist in SpeedTracker's price history (Solana tokens, no on-chain price data). SpeedTracker defaults to 50.0 for unknown tokens. **Fix:** Seed price history for K* tokens on next pipeline run. All hot-set tokens show 50% because SpeedTracker has no history for any of them — the hot-set is a filtered view that survived AI compaction rounds, not a SpeedTracker output.

### [ ] (P) Verify Speed=50% fix applied — seed price history for KSHIB/KFLOKI/KBONK/KLUNC — owner: ai-engineer — 2026-04-10
CONFIRM that SpeedTracker's price history was seeded for KSHIB, KFLOKI, KBONK, KLUNC. Check speedtracker data or run a pipeline cycle and verify these tokens now have real speed_percentile values (not 50.0). If not seeded, the hot-set will continue showing 50% for these 4 tokens.

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
---

## 2026-04-08 Session Tasks

### [P] SL/TP System Fixes — Phase 1 (done), Phase 2 (done), Phase 3 (done)
**Project:** SL/TP Protection System Fixes
**Status:** ✅ ALL 8 DONE — 2026-04-08
**Date:** 2026-04-08

**All completed:**
- [✅] B8: Atomic write lock added to hermes-trades-api.py + update-trades-json.py
- [✅] B3: SL+TP placed on HL immediately after entry (brain.py add_trade)
- [✅] B2: SL+TP placed on HL after cascade flip (position_manager cascade_flip)
- [✅] B1: Trailing SL pushed to HL every cycle (already implemented, verified)
- [✅] B7: Guardian kill switch created (guardian_kill_switch.json + _is_token_killed check)
- [✅] B6: Standardized close reason vocabulary (UPPERCASE_STANDARD format)
- [✅] B5: 429 backoff retry in position_manager (_retry_hl_call helper)
- [✅] B4: cascade_sequences table + recording in cascade_flip()

**Reference:** [brain/PROJECTS.md#SL/TP Protection System Fixes]

### [🚨] Guardian + Position Manager — confirm online and watching
**Status:** ✅ DONE — Confirmed 2026-04-08
- Guardian: 10/10 positions matched, running every 60s
- Position Manager: 10 open, 6 trailing activations last cycle
- XRP: LONG entry=1.3886, current=1.3690, pnl=-1.23%, SL=1.3608 (NOT stopped out)
- EIGEN: closed at +0.42% (trailing exit -0.12%) — NOT a loss

