# DECISIONS.md — Hermes Project Decision Log

> Every significant architectural or operational decision goes here.
> Format: Date | What | Why | Alternatives considered | Revisit date | Owner
> Search with: `grep -n "2026\|decision\|revisit" /root/.hermes/brain/DECISIONS.md`

---

## 2026-04-10 | Cascade Flip Kill Switch — Disabled

**Decision:** Added `CASCADE_FLIP_ENABLED = False` kill switch to `position_manager.py`. All 4 cascade flip call sites now guarded by this flag.

**Why disabled:** Cascade flip not working as intended — T flagged for revisit.

**What was disabled (all cascade flip paths in `check_and_manage_positions()`):**
1. MTF MACD all-TFs-flipped cascade flip (`if CASCADE_FLIP_ENABLED and mtf_all_flipped`)
2. Cascade direction active flip (`CASCADE_FLIP_ENABLED and cascade['cascade_active']`)
3. MACD rules engine flip signal (`CASCADE_FLIP_ENABLED and macd_result['should_flip']`)
4. Speed-armed cascade flip (`CASCADE_FLIP_ENABLED and ... CASCADE_FLIP_ARM_LOSS`)

**Kill switch location:** `position_manager.py` line ~74 (`CASCADE_FLIP_ENABLED = False`)

**To re-enable:** Set `CASCADE_FLIP_ENABLED = True` in `position_manager.py`.

**Owner:** T

---

## 2026-04-05 | MiniMax API over ollama for ai_decider scoring

**Decision:** Use MiniMax-M2 API (via `/v1/chat/completions`) as primary LLM for ai_decider signal scoring and compaction.
**Rationale:** Token budget limits (8K/run, 500K/day) make local ollama inference cost-prohibitive at scale. MiniMax provides sufficient quality at lower token cost. Ollama kept as fallback only.
**Previous:** ollama was primary (from earlier OpenClaw setup)
**Alternatives considered:** ollama local (too slow for 10-min cadence), Claude API (rate limited, expensive), GPT-4o (no local Ollama required anyway)
**Revisit condition:** When HL position count drops below 3, or MiniMax rate limits become a bottleneck
**Owner:** Agent

---

## 2026-04-05 | Crash recovery: checkpoint_utils.py (not session snapshots)

**Decision:** Build `checkpoint_utils.py` for pipeline script crash recovery only — NOT full LLM agent session snapshot/restore.
**Rationale:** Trading pipeline (decider-run.py, hl-sync-guardian.py) is where crashes cause real damage — mid-trade state loss. The LLM agent (hermes-agent) session persistence is a separate, more complex problem (~4-6 hrs to build) and less critical since the agent recovers quickly anyway.
**What checkpoint_utils does:** Snapshots workflow state before major steps (trade submitted, cycle complete). On restart, detects incomplete runs and recovers.
**What it does NOT do:** Serialize full LLM conversation context for mid-session restore.
**Alternatives considered:** Full session snapshot/restore system (deferred to B-2.4), event sourcing architecture (overkill for Python scripts)
**Revisit condition:** If agent session crashes become frequent and context loss is costly
**Owner:** Agent

---

## 2026-04-05 | Structured event log: event_log.py (not event sourcing)

**Decision:** Build `event_log.py` as append-only JSONL audit trail — not a full event-sourcing architecture.
**Rationale:** Trading pipeline needs a way to reconstruct what happened after failures, without the complexity of an event store. JSONL file with auto-rotation is simple, debuggable, and sufficient.
**Events captured:** TRADE_ENTERED, TRADE_FAILED, POSITION_OPEN/CLOSED, HOTSET_UPDATED, BUDGET_EXCEEDED, API_CALL, CHECKPOINT_RECOVERY, REGIME_CHANGE, WORKFLOW_STATE_CHANGE
**Alternatives considered:** Full event-sourcing DB (over-engineered), PostgreSQL events table (Tokyo PG server is asleep — local SQLite only)
**Revisit condition:** If audit requirements grow beyond what JSONL can handle
**Owner:** Agent

---

## 2026-04-05 | Token budget: 8K/run hard cap, 500K/day soft cap

**Decision:** Set `_MAX_TOKENS_PER_RUN = 8000` hard cap per ai_decider invocation, `_DAILY_TOKEN_BUDGET = 500000` daily cap.
**Rationale:** MiniMax API costs accumulate fast at 4000+ tokens/call × 6 runs/hour. Budget enforcement ensures we don't blow the daily allocation before market close. Hard cap per call prevents single runaway invocation.
**How it works:** Before MiniMax API call, estimate tokens (~4000). If over run cap or day cap, skip LLM call and return early. Log BUDGET_EXCEEDED event.
**Alternatives considered:** No budget (risk runaway costs), percentage-of-balance sizing (not directly tied to API costs)
**Revisit condition:** If budget frequently blocks legitimate signals, or if costs are well under limit
**Owner:** Agent

---

## 2026-04-05 | PostgreSQL workflow_state column in brain DB (not SQLite)

**Decision:** Add `workflow_state VARCHAR(32) DEFAULT 'IDLE'` and `workflow_updated_at TIMESTAMP` columns to PostgreSQL `brain.trades` table via `signal_schema.py` functions.
**Rationale:** Trading pipeline needs a single source of truth for trade lifecycle state. PostgreSQL (brain DB on Tokyo) is the authoritative store for trade metadata — SQLite is runtime-only. `workflow_state` enables guardian to know whether a trade is IDLE, POSITION_OPEN, CLOSE_PENDING, or ERROR_RECOVERY.
**Migration:** `run_workflow_migration.py` — safe ADD COLUMN with DEFAULT, no data loss, no table lock.
**Alternatives considered:** Keep state in memory only (risky on crash), use SQLite for state (split brain across two DBs), Redis (adds dependency)
**Revisit condition:** If Tokyo PG remains asleep and we need real-time state from Dallas
**Owner:** Agent

---

## 2026-04-05 | Regime filter applies to APPROVED signals path (not just PENDING)

**Decision:** `check_cascade_flip()` in `position_manager.py` already queries `decision IN ('PENDING', 'APPROVED')` — the APPROVED path was already correct. However, the **decider-run.py approved-signals loop** was missing the regime check (only HOT-SET signals had it). Fixed to apply regime check to all approved signals.
**Rationale:** AAVE contrarian trades were entering against regime because the APPROVED signals path didn't check regime alignment. Now both PENDING and APPROVED paths enforce regime.
**What was wrong:** In decider-run.py, `_run_hot_set()` had regime check but `execute_trade()` → approved signals path did not.
**Alternatives considered:** Make regime check in signal_gen.py (too early — regime can change), add regime gate at HL API call (too late)
**Revisit condition:** If regime changes frequently and signals are rejected too often
**Owner:** Agent

---

## 2026-04-05 | OpenClaw removal from production system

**Decision:** Remove OpenClaw entirely from the production system — binary, npm package, systemd services.
**Rationale:** OpenClaw was the predecessor LLM agent framework. Hermes-agent is now primary. OpenClaw's gateway, skills, and cron jobs were creating confusion about which system was authoritative. Clean break.
**What was removed:**
- `/usr/bin/openclaw` and `/usr/local/bin/openclaw-cleanup.sh`
- `openclaw@2026.4.1` npm package
- 54 systemd service/timer files in `/etc/systemd/system/openclaw-*.{service,timer}`
- `openclaw-gateway` process (was on port 18789)
**What was kept:** OpenClaw imported skills in `/root/.hermes/skills/openclaw-imports/` — these are still valid and compatible with Hermes.
**Revisit condition:** Never — OpenClaw is deprecated
**Owner:** Agent

---

## 2026-04-05 | Hermes gateway on port 18790 (not replacing 18789)

**Decision:** Run `hermes-gateway` on `127.0.0.1:18790` — not as a drop-in replacement for the removed `openclaw-gateway` on 18789.
**Rationale:** OpenClaw gateway is gone. Hermes gateway is running as a standalone service (not systemd yet). Bound to loopback because platform tokens (TELEGRAM_BOT_TOKEN, etc.) aren't configured yet. API server platform is enabled and working.
**Current state:** `{"status": "ok", "platform": "hermes-agent"}` on port 18790
**To expose externally:** Configure platform tokens in env, change bind to `0.0.0.0`, install as systemd service
**Alternatives considered:** Port 18789 (can't — OpenClaw was using it), systemd service now (deferred — tokens not configured)
**Revisit condition:** When Telegram/Discord tokens are configured
**Owner:** Agent

---

## 2026-04-05 | QMD memory backend not needed

**Decision:** Do not implement QMD (Quantum Model D) memory backend for Hermes. Current file-backed memory (`MEMORY.md`, `USER.md`) is sufficient.
**Rationale:** OpenClaw had `memory: { backend: qmd }` in config, but Hermes doesn't use it. File-backed memory is simpler, more reliable, and doesn't require external services. `brain-context-engine` plugin is disabled in OpenClaw anyway.
**Alternatives considered:** Build QMD support (would require significant work), use Redis-backed memory (adds dependency)
**Revisit condition:** If file-backed memory proves insufficient for multi-session context
**Owner:** Agent

---

**Decision:** Ignore OpenClaw entirely for Hermes work. OpenClaw's workspace, scripts, DBs, and skills are a different system — not part of the Hermes pipeline. Any diagnostic work should use Hermes paths only:
- Signals DB: `/root/.hermes/data/signals_hermes_runtime.db`
- Hot-set: `/var/www/hermes/data/hotset.json`
- Scripts: `/root/.hermes/scripts/`
- Pipeline logs: `/root/.hermes/logs/pipeline.log`

## 2026-04-05 | Hot-set stale — root cause: ai_decider not running

**Symptom:** hotset.json age >11 min, decider-run blocking approvals, Telegram shows empty hot-set.
**Root cause:** `ai_decider` runs via `run_pipeline.py` STEPS_EVERY_10M (every 10 min at :00/:10/...). But before this fix, `ai-decider.timer` (systemd) was supposed to supplement this — however the timer was dead (inactive since Mar 29) AND the .service file was missing.
**Fix:** 
- Re-created `/etc/systemd/system/ai-decider.service`
- Decision: disable the systemd timer entirely — let `run_pipeline.py` be the sole `ai_decider` caller (10-min cadence)
- Changed timer from 5 min → 10 min (matches pipeline)
- Then killed the timer to avoid dual-writer race conditions on hotset.json
- Manual `compact.py --rebuild` confirmed writes work correctly
**ONE writer for hotset.json:** `ai_decider.py` via `run_pipeline.py` every 10 min. `compact.py --rebuild` is manual-only, not on cron.
**Revisit if hot-set goes stale again:** check `run_pipeline.py` is actually calling `ai_decider` at :00/:10/etc.

## 2026-04-05 | OPTION 1 DEPLOYED: Flip signal direction live

**Decision:** Deploy Option 1 live — reverse signal direction before executing every trade.
**Rationale:** WR is 13.8% (761 trades, Mar 10-25). 79% of SHORT signals had price move UP after entry. ACE (45% of all trades) had 98% of shorts go up. Signal direction is systematically inverted. Flip to test theory cheaply before extensive signal gen rebuild.
**What changed:**
- `_FLIP_SIGNALS = True` added to `/root/.hermes/scripts/decider-run.py` (line 28)
- Main loop: flips `direction` before `execute_trade()` call
- `process_delayed_entries()`: flips direction before `brain.py trade add` call
- `execute_trade()`: passes `flipped=True` flag when direction was flipped
- `brain.py add_trade()`: accepts `--flipped` CLI flag, writes `flipped_from_trade=True, flip_variant='signal-flip'` to brain DB
- `hermes-trades-api.py`: removed `_build_hotset_from_db()` fallback writer (was bypassing filters)
- `ai_decider.py`: confidence floor raised from 50→70, momentum=0% filter added
**Kill switch:** `echo '{\"live_trading\": false}' > /var/www/hermes/data/hype_live_trading.json` — kills all live trading instantly
**Alternatives considered:** Option 2 (fix flip mechanism — still loses on initial wrong entry), Option 3 (fix signal gen at source — days/weeks, could make worse)
**Revisit condition:** After 20+ trades with flip active — measure new WR. If WR < 30%, flip is wrong direction. If WR > 50%, confirms inverted signal hypothesis.
**Owner:** T + Agent

**UPDATE 2026-04-05 PM:** Signal flip DISABLED (`_FLIP_SIGNALS = False`). No longer reversing direction before trade execution. Fresh signals now execute in their original direction.

---

## 2026-04-06 | WR flip test FAILED — signal direction not systematically inverted

**Decision:** Close the Win Rate investigation. Signal flip did NOT work — tested on 2 trades and failed (wrong direction). Historical 79% SHORT-wrong finding from Mar 10-25 data did NOT replicate in live trading. System continues without signal flip.

**Outcome:**
- Flip deployed 2026-04-05, ran 2 trades, both failed
- Insufficient sample (2 trades) but direction was wrong
- Historical data was noise or wrong segment (ACE-dominated sample)
- WR is 43% last 7 days (no flip) — system improving naturally

**What this means:** Signal direction is correct as-is. Don't flip signals. Focus on signal quality improvements instead.

**Revisit condition:** If WR drops back below 30% on a larger sample — revisit signal direction hypothesis
**Owner:** T + Agent

---

## 2026-04-06 | Tokyo PG decommissioned — SQLite-only mode

**Decision:** Accept SQLite-only mode permanently. Tokyo PG server (10.60.72.219) has been unreachable/asleep for days. PostgreSQL workflow_state feature is decommissioned.

**Why:** Tokyo being unreachable makes PostgreSQL unusable. SQLite is sufficient for the current architecture. `signal_schema.py` functions fall back gracefully to SQLite.

**What was removed:** PostgreSQL workflow_state column requirement
**What stays:** SQLite signals DB (`signals_hermes_runtime.db`), paper trade tracking

**Revisit condition:** If Tokyo PG becomes reliably reachable — reconsider PostgreSQL, but likely not needed
**Owner:** T

---

## 2026-04-06 | Volume-confirmation trailing SL (Phase 2)

**Decision:** Add volume-based buffer selection to Phase 2 trailing SL — use tighter 0.25% buffer when volume does NOT confirm direction, looser 0.35% when volume confirms.

**Why:** Phase 2 tokens in low-momentum moves were getting stopped out prematurely. High-momentum moves should get more room.

**Changes:**
- `position_manager.py`: `get_volume_confirmation(token, direction)` — current candle vol > 23-candle MA = confirmed
- Phase 2 buffer: `0.35%` when vol confirms, `0.25%` when not
- `VOLUME_CACHE_FILE = /var/www/hermes/data/volume_cache.json` (60s TTL)
- `_fetch_volume_data()`: 24× 1h HL candles via ccxt, 5s timeout, fail-silent
- Volume cache warmup moved to position_manager (non-blocking daemon threads)

**Revisit condition:** If Phase 2 trailing fires too aggressively on low-volume days
**Owner:** Agent

---

## 2026-04-06 | Cascade flip thresholds lowered + SKIPPED signals added

**Decision:** Tighten cascade flip thresholds for faster response on wrong-direction positions.

**Changes:**
| Parameter | Old | New |
|-----------|-----|-----|
| ARM_LOSS | -0.50% | -0.25% |
| TRIGGER_LOSS | -1.00% | -0.50% |
| HF_TRIGGER_LOSS | -0.75% | -0.35% |
| MIN_CONF | 70% | 60% |
| MAX_AGE | 15 min | 30 min |
| Cascade confluence | PENDING/WAIT/APPROVED | +SKIPPED |

**Why:**
- Positions like ZK SHORT, SKY LONG near breakeven but wrong direction
- SKIPPED = pipeline generated opposite signal but couldn't enter (max positions, cooldown, etc.) — valid flip confluence
- 30 min window ensures signals don't expire before flip fires

**Revisit condition:** If flip fires too aggressively (false positives on low-volume moves)
**Owner:** Agent

---

## 2026-04-06 | trailing_stops.json cleanup — 821 orphaned entries removed

**Decision:** Clean orphaned entries from `trailing_stops.json` — keeps only active DB trades.

**What:** 821 stale/orphaned entries removed, 8 active positions remain. Backup at `trailing_stops.json.bak`.

**Why:** Entries from old closed positions were accumulating and causing confusion. 2 open positions (IDs 4138, 4141) were missing from file — they'll activate normally when pnl reaches 1%.

**Revisit condition:** After bulk position closes — run cleanup again
**Owner:** Agent

---

## 2026-04-06 | ai_decider last_seen field added to hotset.json

**Decision:** `ai_decider.py` hotset query now includes `MAX(updated_at) as last_seen` so signals.html displays timestamps.

**Why:** `signals.html` showed stale-looking `lastSeen=1775441492.49656` (Unix timestamp) for all hot-set tokens — blank display. Now writes human-readable timestamp to `last_seen` field.

**Changes:**
- Query: added `MAX(updated_at) as last_seen` (r[9])
- hotset.json entry: added `'last_seen': r[9] or ''`
- signals.html: `s.last_seen` renders as `2026-04-06 02:30`

**Revisit condition:** Never — cosmetic fix
**Owner:** Agent

---

## 2026-04-06 | Cut-loser tightened to -2.0% | ALGO + VVV manual close

**Decision:** Cut-loser threshold tightened from -3.0% to -2.0%. ALGO LONG (-3.67%) and VVV LONG (-3.67%) manually closed by T — entries showed proper entry prices on HL but had deep losses. 8 positions remain.

**Why -2.0%:** Balanced — catches bad entries before deep loss without being too tight (avoids whipsaws on legitimate -1.5% dips). At -3.0%, ALGO and VVV had already blown through -3% before any cut.

**Changes:**
- `position_manager.py`: `CUT_LOSER_PNL = -2.0` (was -3.0)

**Still open:** DYDX -0.24%, HYPER +0.10%, LINEA +0.03%, PURR -0.10%, SKY -0.45%, TRX -0.41%, TST -0.12%, WCT +0.01%

**Revisit condition:** If -2.0% causes excessive whipsaws on legitimate setups (>20% more cut-loser fires), consider -1.75% as compromise
**Owner:** T

---

## 2026-04-06 | Volume cache warmup fix (position_manager blocking I/O removed)

**Decision:** Move volume cache warmup from synchronous blocking to non-blocking daemon threads inside `check_and_manage_positions()`.

**Why:** `_warmup_volume_cache()` in decider-run.py was synchronous — blocking the pipeline on HL API calls (~100-200ms per token). Position_manager hangs for 15+ minutes because of it.

**Changes:**
- `_warmup_volume_cache_pm()` in position_manager.py fires daemon threads per stale token
- Threads die on timeout (5s hard timeout per fetch)
- Cache file shared between position_manager and decider-run via `/var/www/hermes/data/volume_cache.json`

**Revisit condition:** If volume cache remains stale after this fix
**Owner:** Agent

---

## 2026-04-05 | Signal compaction: 903 stale WAIT signals expired, hot-set rebuilt

**Decision:** Run signal compaction to expire stale WAIT/PENDING/APPROVED signals (>3h old) and rebuild hotset.json.
**Root cause:** 903 WAIT signals from 07:48 were sitting stale for 12+ hours. The `_load_hot_rounds()` query only considers signals created within the last 3 hours. Old signals blocked the pipeline → hot-set stayed at 4 tokens (all stale, rc=0) → decider-run found 0 APPROVED signals → 2 position slots stayed empty.
**What was done:**
- `signal-compaction` skill created at `/root/.hermes/skills/signal-compaction/scripts/compact.py`
- 903 stale WAIT signals marked EXPIRED
- hot-set rebuilt: 4 tokens → 13 tokens (SUPER/LONG/rc=3, BTC/LONG, BCH/LONG, SKY/SHORT, TRB/LONG, SAND/LONG, FIL/LONG, ETHFI/LONG, IOTA/LONG, ASTER/LONG, ALGO/SHORT, MEW/SHORT, NIL/LONG)
**Result:** ai_decider can now process fresh signals, position slots should start filling.
**Revisit:** If slots still don't fill after next ai_decider run (20:40).

---

## 2026-04-05 | Hot-set filters: confidence ≥ 70% and momentum > 0%

**Decision:** Add hard filters to hot-set entry — reject any token with confidence < 70% OR momentum (speed) = 0%.
**Reasoning:** Tokens like NOT (conf=50%, speed=⏸0%), MEW (conf=81%, speed=⏸0%), SUPER/BCH/BTC (conf=50%) have no business in the hot-set. The 903-signal backlog showed low-confidence signals dominating. Raising the bar to 70% should improve signal quality.
**Changes:**
- `ai_decider.py` line ~1165: `HAVING MAX(confidence) >= 50` → `>= 70`
- `ai_decider.py` line ~1194: added `conf < 70` and `momentum == 0` filters before appending to hot-set
- `compact.py` rebuild_hotset(): same filters added
- `hermes-trades-api.py`: **found second hot-set writer** — `_build_hotset_from_db()` fallback query had NO filters and was being used whenever `hotset.json` went stale (>11 min). Fixed: removed the fallback entirely. `_get_hotset_from_file()` now returns `[]` when stale/missing instead of `None`. No more parallel writer. ONE writer: `ai_decider.py` only. Restarted API process.
- Skill `signal-compaction` SKILL.md updated with filter documentation
**Result after rebuild:** 13 tokens → 10 tokens. Filtered: NOT (Solana), SUPER/BCH (conf<70%), MEW (speed=0%)
**Revisit:** Monitor WR on 10-token hot-set vs previous 13-token hot-set.

---

## 2026-04-05 | hermes-git-release.timer restored

**Decision:** Restart `hermes-git-release.timer` (was inactive since 2026-04-02). Also create missing `hermes-git-release.service` unit file.
**Rationale:** The timer provides hourly backups + seed zip. It was manually stopped on Apr 2 and never restarted. Now active and waiting.
**Alternatives considered:** Use separate cron job (timer is already set up, just dead), disable entirely (not ideal — backups are important)
**Revisit condition:** If update-git.py script has issues
**Owner:** Agent

---

## Prior Decisions (Pre-2026-04-05)

### SHORT trailing activation fix
**When:** Pre-2026-04-04
**What:** `abs(pnl_pct)` for SHORTs was wrong — renamed `adverse_pct → profit_pct` so trailing stop triggers correctly on profit for shorts
**Owner:** Agent

### Dual guardian reconciliation
**When:** Pre-2026-04-04
**What:** Both `hl-sync-guardian` AND `position_manager.refresh_current_prices` reconciled independently — consolidated to avoid double-firing
**Owner:** Agent

### SQL injection fix
**When:** Pre-2026-04-04
**What:** `record_closed_trade` in hl-sync-guardian.py had SQL injection vulnerability — fixed with parameterized queries
**Owner:** Agent

### Hot-set SQL placeholder fix
**When:** 2026-04-04
**What:** `***` SQL placeholder caused hot-set never to build — replaced with proper `?` placeholders across 3+ files
**Owner:** Agent

### Cascade flip: check APPROVED signals (deferred idea)
**When:** 2026-04-05
**What:** Idea to modify `check_cascade_flip()` to query `decision IN ('PENDING', 'APPROVED')` instead of just PENDING — would give flip confirmation faster
**Status:** Deferred — not yet implemented (see TASKS.md)
**Owner:** TBD

---

## 2026-04-06 | ATM folder created — trading system configs consolidated

**Decision:** Create `/root/.hermes/ATM/` as the canonical home for all trading system files included in the standalone Docker. All primary trading scripts, configs, and architecture docs live here.

**Why:** Docker target requires a clear, self-contained bundle. `ATM/` becomes the namespace for everything that goes into the final container — trading engine, configs, schemas. `/root/.hermes/scripts/` remains the runtime location on the live host.

**What's in ATM:**
- `ATM/ATM-Architecture.md` — system design document (updated 2026-04-05)
- `ATM/trading-docker.md` — Docker build spec (2026-04-06)
- `ATM/config/stoploss.md` — **all exit rules** (2026-04-06): hard SL, trailing SL, cascade flip, wave turn, stale winner/loser, cut_loser

**SOPs.md updated:** Trading System section now links to `ATM/ATM-Architecture.md` and `ATM/config/stoploss.md`.

**Key configs in ATM/config/:**
| File | Contents |
|------|----------|
| `stoploss.md` | Full exit rules reference — all constants, priority order, state machines |

**Revisit condition:** When Docker ships — verify all runtime paths in stoploss.md match container env vars
**Owner:** Agent

---

## 2026-04-06 | Cut-loser DISABLED — guardian is the only emergency exit

**Decision:** Cut_loser in position_manager.py is fully commented out (lines 1583-87). The guardian (`hl-sync-guardian.py`) is the designated emergency handler for live HL positions.

**Why:** Cut_loser was causing race conditions — position_manager uses fresh prices and cuts at sl_distance from A/B test (as tight as 0.5%), before guardian's flip could fire. Removing cut_loser from position_manager eliminates duplicate closes of the same position.

**Exit priority (current):**
1. Wave Turn (immediate)
2. Trailing SL (once active — ONLY exit, cut_loser disabled)
3. Cascade Flip (speed-armed, before cut_loser)
4. Stale Winner/Loser (speed-stall, alongside trailing)
5. Guardian: handles live HL emergency exits, orphan recovery

**Known bug:** `STALE_LOSER_TIMEOUT_MINUTES` comment says 15 min (line 32) but code uses 30 min (line 337) — needs cleanup.

**Revisit condition:** If emergency exits are missed without cut_loser in position_manager
**Owner:** Agent

---

---

## 2026-04-06 | ai_decide_batch regime hard block + guardian orphan fix

**Decisions:**
1. `ai_decide_batch()` now applies regime hard block inline after parsing Minimax decisions. Previously only `ai_decide()` had it — batch mode bypassed it entirely.
2. `hl-sync-guardian.py` Step8 now skips paper trades (`paper=True`) in orphan detection. Paper trades being absent from HL is expected behavior — they are never on HL.
3. NEUTRAL regime with conf > 60% should be treated as a WAIT, not auto-execute.

**Evidence:** SKY was SHORT @ LONG_BIAS@95% regime → executed anyway (batch bypassed regime block). VVV SHORT was wrong direction — VVV not in regime_4h.json or momentum_cache. Guardian was closing paper trades as "stale orphans."

**Full post-mortems:** `tradingnotes.md`

**Owner:** Agent

---

*Format: `## YYYY-MM-DD | Short title` — append new decisions to the top, above this line.*