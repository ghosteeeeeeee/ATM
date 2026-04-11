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
**Status:** ✅ COMPLETE — 2026-04-10
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
**Status:** ❌ CLOSED — 2026-04-06
**Owner:** T
**Summary:** Hermes gateway running on 127.0.0.1:18790 but platform tokens (Telegram, Discord) never configured. Project closed — gateway is internal-use only, no external platform integration needed.
**What was planned:** systemd service install, platform tokens, expose on 0.0.0.0
**Why closed:** T decided external platform integration is not needed. Gateway runs as-is for internal use.

---

## Tokyo <-> Dallas Sync
**Status:** ❌ CLOSED — SQLite-only mode (2026-04-06)
**Owner:** T
**Summary:** Tokyo PG server (10.60.72.219) has been asleep/unreachable for days. Decision made: accept SQLite-only mode permanently. `signal_schema.py` functions that required PostgreSQL will fall back gracefully or use SQLite. PostgreSQL workflow_state feature is decommissioned.
**Blockers:** None — explicitly chose SQLite-only
**Key decisions:** [DECISIONS.md] — PostgreSQL was chosen over SQLite for trade state, but Tokyo being unreachable makes it unusable. SQLite is sufficient for the current architecture.

### What's affected
- `signal_schema.py` — connects to Tokyo PG for `trades` table
- `update_trade_workflow_state()` — writes to PostgreSQL
- Real-time trade state for guardian reconciliation

---

## Hot-Set Compaction Rewrite
**Status:** 🚧 PARTIAL — 2026-04-08
**Owner:** Agent
**Summary:** Redesign the hot-set pipeline to match original intent: signals generated in last 10 mins → compacted by AI every 10 mins → top 20 survive → survivors get stronger across rounds → reverse signals penalize and evict. Signals NOT in top 20 are immediately purged (REJECTED column). No signal buildup.
**Reference:** [.hermes/plans/2026-04-08_041613-hotset-depletion-fix.md]
**Blockers:** None

### Completed ✅
- [X] Rewrite AI compaction prompt (Q_final variant) — fixes NO_SIGNALS bug, token `***` anonymization
- [X] Add `***` token recovery logic in parsing — recovers anonymized tokens via direction+confidence match
- [X] Fix `z_val:+.2f` None crash in batch decision prompt (ai_decider.py:1838)
- [X] Add `max_tokens=4000` to ai_decider batch calls ✅ (already done)
- [X] Fix `opened_at` → `open_time` in get_open_trade_details() (ai_decider.py:1749) — was crashing every 10 min
- [X] Fix `needs_sl` undefined in position_manager.py — was crashing ATR update cycle
- [X] Fix RSI/MACD confidence caps: RSI 50→70, MACD 50→80, conf-2s 70→80 (signal_gen.py)
- [X] Confluence 2-source boost: 1.25x→1.3x (signal_gen.py)

### Remaining ⬜
- [ ] Change hot-set query window from 3h → 10 mins (`created_at > datetime('now', '-10 minutes')`)
- [ ] Remove `review_count >= 1` requirement from hot-set query
- [ ] Add PURGE step: non-top-20 signals → `decision='REJECTED', rejected_at=NOW()`
- [ ] Add `rejected_at` and `rejection_reason` columns to signals table
- [ ] Simplify state machine: GENERATED → PENDING → APPROVED (in hot-set) / REJECTED (purged) / EXECUTED (traded)

### Problem Statement
Current broken flow: signals need `review_count>=1` + `created_at < 3 hours` to enter hot-set. But new signals never get reviewed fast enough (10-min AI review cycle), so the 3-hour window expires them before they can accumulate `review_count>=1`. Hot-set goes empty.

### Target Design
```
Every 10 mins:
  1. PURGE: last cycle's non-top-20 → REJECTED (moved to rejected column)
  2. NEW SIGNALS: ~250 signals generated (last 10 mins only)
  3. AI COMPACTION: rank top 20, penalize reverse signals, identify survivors
  4. WRITE HOT-SET: top 20 to hotset.json with survival_round count
  5. DECIDER-RUN: trade highest confidence signal from hot-set only
```

### Key Decisions (pending)
- [ ] Change hot-set query window from 3h → 10 mins (`created_at > datetime('now', '-10 minutes')`)
- [ ] Remove `review_count >= 1` requirement from hot-set query
- [ ] Add PURGE step: non-top-20 signals → `decision='REJECTED', rejected_at=NOW()`
- [ ] Rewrite AI compaction prompt (best variants: `L_survival_rounds`, `Q_final` from prompt tests)
- [ ] Add `max_tokens=4000` to all ai_decider batch calls (fixes MiniMax thinking budget issue)
- [ ] Add `rejected_at` and `rejection_reason` columns to signals table
- [ ] Simplify state machine: GENERATED → PENDING → APPROVED (in hot-set) / REJECTED (purged) / EXECUTED (traded)

### Prompt Testing Results (2026-04-08)
| Prompt | Tokens | Output Quality |
|--------|--------|----------------|
| `L_survival_rounds` | 1025-3370 | ✅ Best structured, includes survival rounds |
| `Q_final` | 978-2970 | ✅ Clean minimal format, efficient |
| `K_ultraminimal` | 970 | ✅ Simple, fast |
| `A_current` (baseline) | 2088 | ❌ Broken — 2x tokens, wrong task |

**Critical finding:** MiniMax-M2 with thinking uses full `max_tokens` for BOTH reasoning + output. Need `max_tokens=4000+` to get actual output. With `max_tokens=3000`, reasoning consumes 2999 tokens leaving 1 output token.

---

## Win Rate Investigation
**Status:** ❌ CLOSED — WR flip test FAILED (2026-04-06)
**Owner:** T + Agent
**Summary:** WR flip test ran on 2 trades and failed — insufficient sample but direction was wrong. 79% SHORT wrong direction finding from historical data did NOT replicate in live test. System continues without signal flip. Real-world current 10 positions: mix of LONG/SHORT near breakeven (CFX +2%, VVV -1.17%, most others flat).
**Key decisions:** [INCIDENT_WR_FAILURE.md] — Option 1 (flip) tested on 2 trades, failed. Signal direction is NOT systematically inverted — historical data was noise or wrong segment.
**Reference:** [DECISIONS.md#2026-04-05 | OPTION 1 DEPLOYED: Flip signal direction live]

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

## Cascade Flip Enhancement (APPROVED+SKIPPED signals)
**Status:** ✅ DONE — 2026-04-06
**Owner:** Agent
**Summary:** Cascade flip thresholds lowered (ARM=-0.25%, TRIGGER=-0.50%, HF_TRIGGER=-0.35%), MIN_CONF=60%, MAX_AGE=30min. SKIPPED signals now included in cascade flip confluence check alongside PENDING/WAIT/APPROVED. Volume-confirmation buffer (0.35% vol confirmed / 0.25% not) added to Phase 2.
**Key decisions:** [DECISIONS.md#2026-04-06 | Cascade flip thresholds lowered + SKIPPED signals added]
**Blockers:** None
**Reference:** [DECISIONS.md#2026-04-06 | Volume-confirmation trailing SL (Phase 2)]

---

## True-MACD Cascade System (Core Strategy)
**Status:** ✅ LIVE — 2026-04-06
**Owner:** Agent
**Sub-project of:** Trading Pipeline

### Summary
Multi-timeframe MACD alignment and cascade detection system. One of Hermes's **core strategy filters** — prevents bad entries at local peaks and triggers cascade flips when smaller timeframes lead a reversal.

**Core insight:** 15m leads → 1h follows → 4h confirms. We were entering LONG when 4h looked great but 15m had already flipped bearish — getting run over by the cascade before it reached larger TFs.

### Key Files
| Component | File | Role |
|-----------|------|------|
| MACD rules engine | `/root/.hermes/scripts/macd_rules.py` | EMA(12/26/9), histogram, regime, bullish_score (-3 to +3) |
| Cascade detection | `/root/.hermes/scripts/candle_db.py` | Local SQLite candles, `detect_cascade_direction()` |
| Entry guard | `/root/.hermes/scripts/signal_gen.py` | Blocks signals when MACD rules say market not in valid regime |
| Cascade flip | `/root/.hermes/scripts/position_manager.py` | Exits/flips when MTF alignment flips |

### Sub-components
| Function | Location | Returns |
|----------|----------|---------|
| `compute_macd_state()` | macd_rules.py | Full MACD state: regime, crossover age, histogram_rate, bullish_score |
| `get_macd_entry_signal()` | macd_rules.py | `allowed: bool + reason` for LONG/SHORT entry |
| `get_macd_exit_signal()` | macd_rules.py | `should_exit/should_flip + reasons` |
| `compute_mtf_macd_alignment()` | macd_rules.py | MTF score 0-3, direction, confidence (0.0-1.0), per-TF states |
| `cascade_entry_signal()` | macd_rules.py | Cascade LONG/SHORT allowed + block reason |
| `detect_cascade_direction()` | candle_db.py | lead TF, confirmation count, reversal_score |

### Cascade Entry Rules
```
LONG entry — ALL 3 conditions:
  1. 15m macd_above_signal=True AND histogram_positive=True (lead TF flipped)
  2. At least one of (1h, 4h) also BULL (confirmation received)
  3. 4h regime is BULL (anchor hasn't diverged)

SHORT entry: mirror logic

Entry BLOCKED when:
  - 15m flipped but larger TFs still opposite → "early entry danger"
  - 15m/1h conflict → no clear direction
  - 4h already flipped away → "missed the move"
```

### signal_gen.py Integration
- Cascade ACTIVE + aligns with direction → **+10 confidence boost**
- Cascade ACTIVE but OPPOSITE to direction → **BLOCK entry**

### position_manager.py Integration
- Cascade ACTIVE + cascade direction ≠ current position → **immediate flip, conf=95**

### Live Readings (2026-04-06 ~18:00 UTC)
```
BTC: cascade=LONG  | LONG_ALLOW=True  | 15m=BULL, 1h=BEAR, 4h=BULL
ETH: cascade=LONG  | LONG_ALLOW=True  | 15m=BEAR, 1h=BEAR, 4h=BULL
TRB: cascade=SHORT | LONG_ALLOW=False | block: "4h_already_flipped_away_missed_move"
IMX: cascade=SHORT | LONG_ALLOW=False | block: "4h_already_flipped_away_missed_move"
```
TRB/IMX SHORT blocked because 4h still BULL while 15m/1h already BEAR — larger TF hasn't confirmed yet.

### What Was Wrong Before (TRB/IMX/SOPH/SCR Losses)
We entered LONG at local peaks. 15m had already flipped bearish, but 4h still looked bullish — giving false confidence. By the time 4h confirmed, we were already stopped out.

### Related
- [DECISIONS.md#2026-04-06 | Cascade flip thresholds + SKIPPED signals]
- [brain/trading.md##True-MACD Cascade System]

---

## AI Trading Machine (ATM) — Standalone Docker
**Status:** 🚧 IN PROGRESS — 2026-04-06
**Owner:** T + Agent
**Summary:** Self-contained Docker container running the full Hermes trading system — pipeline, dashboards, noVNC, SSH — zero manual setup. All core files organized under `/ATM/` for Docker bundling. Paper trading by default.
**Blockers:** Pipeline audit (Step 1) not yet completed
**Reference:** `/root/.hermes/plans/2026-04-05_183622-can-we-set-up-a-new-docker-container.md`
**Key decisions:** [DECISIONS.md#2026-04-06 | ATM folder created]

### ATM Folder Structure
```
/root/.hermes/ATM/
├── ATM-Architecture.md      # System design doc
├── trading-docker.md         # Docker build spec (374-line plan)
└── config/
    └── stoploss.md           # All exit rules: hard SL, trailing, cascade flip, wave turn, stale (2026-04-06)
```

### What's in Scope
- Full pipeline scripts + dashboards in container
- SSH daemon (port 3333), nginx (port 8888), noVNC (port 5902)
- Auto-init of SQLite signals DB with seed data on first start
- `export_dashboards.py` for continuous JSON generation
- Paper trading mode (no keys required)
- All configs in `ATM/config/` — stoploss.md is the source of truth for exit rules

### What's Been Done
- Plan written (374-line spec in `/root/.hermes/plans/`)
- `ATM/` folder created (2026-04-06)
- `ATM/config/stoploss.md` written — full exit rules reference
- SOPs.md updated with ATM links (2026-04-06)

### Next Steps (from plan)
1. Audit pipeline scripts — confirm entry points and dependencies
2. Export `signals_hermes.sql` + `signals_data_snapshot.json` from current DB
3. Write `export_dashboards.py`
4. Fix CSP in nginx.conf
5. Write Dockerfile + docker-entrypoint.sh + docker-compose.yml

---

---

## Chart Pattern Recognition
**Status:** 🚧 IN PROGRESS — 2026-04-06
**Owner:** Agent + T
**Summary:** Add real-time chart pattern detection (Bull/Bear Flag → H&S → Wyckoff → Elliot Wave) as a signal source that feeds into the existing Hermes pipeline — initially as cascade flip confluence, eventually as standalone entry signals.
**Key decisions:** [DECISIONS.md#2026-04-06 | Pattern scanner approach]
**Blockers:** None — Phase 1 ready to build

### Architecture
```
signal_gen.py (existing)
    └── pattern_scanner.py (NEW — reads ohlcv_1m from local SQLite)
            ├── detect_flag(candles)     → pattern_flag signal | None
            ├── detect_head_shoulders() → pattern_hns signal | None
            ├── detect_wyckoff()        → pattern_wyckoff signal | None
            └── detect_elliot()         → pattern_elliot signal | None

cascade_flip (position_manager.py)
    └── checks pattern signals as confluence (signal DB → coin-regime → pattern → hold)

All pattern reads → get_ohlcv_1m() from signal_schema.py → local SQLite (ohlcv_1m table)
```

### Signal Priority & Integration — COMPETITION MODEL (T APPROVED 2026-04-06)
- **Signal type priority:** All signal types compete equally — `pattern_*` signals are NOT subordinate to `mtf_macd`
- **Run order:** Pattern scanner runs FIRST (before mtf_macd loop) so patterns get into the DB early and can bubble up
- **Weight in decider:** Pattern signals get a **1.25× confidence multiplier** applied in ai_decider when building the hot-set — patterns that consistently perform well get 1.5×, poor performers get 0.75×
- **No hard-coded hierarchy** — the decider scores all signal types the same way; pattern multiplier is adjustable and tracked
- **Signal types compete:** `pattern_flag`, `pattern_hns`, `pattern_wyckoff`, `pattern_elliot` vs `momentum` (mtf_macd)
- **Performance tracking:** After 50+ trades per signal type, compare win rates. Pattern signals with WR > 55% get weight boost; WR < 45% get weight reduction; WR < 40% get disabled
- **Phase 1 (V1):** Patterns are independent primary signals, not cascade flip confluence. They can trigger entries directly.

### Integration into signal_gen.py
```
run():
  1. _run_pattern_signals()    ← NEW: runs first, all tokens
  2. _run_mtf_macd_signals()   ← existing mtf_macd (runs second)
  3. run_confluence_detection() ← existing confluence
```

Pattern signals written to signals DB with `signal_type='pattern_*'`, `source='pattern_scanner'`, `decision='PENDING'`.

### Phase Breakdown
| Phase | Patterns | Integration | Status |
|-------|----------|-------------|--------|
| Phase 1 | Bull/Bear Flag | Cascade flip confluence | 🚧 In progress |
| Phase 2 | Wyckoff + H&S | Cascade flip + backtest VVV | ⬜ Not started |
| Phase 3 | Elliot Wave | Standalone entry signals | ⬜ Not started |

### Key Files
| File | Change |
|------|--------|
| `/root/.hermes/scripts/pattern_scanner.py` | **NEW** — all pattern detection logic |
| `/root/.hermes/scripts/signal_gen.py` | Calls pattern_scanner, emits pattern signals |
| `/root/.hermes/scripts/position_manager.py` | Cascade flip queries pattern_scanner as confluence |
| `/root/.hermes/scripts/signal_schema.py` | `get_ohlcv_1m()` already exists ✅ |
| `/root/.hermes/scripts/price_collector.py` | Seeds ohlcv_1m for active tokens ✅ |

### IMX Test Case (Current)
- Pattern: **Ascending triangle** (not bull flag — higher lows, resistance at $0.1366)
- Price range: $0.1337 → $0.1369 (+2.39%) over 4 hours
- Target: Break above $0.1366 → $0.139+ (upside measured from support at $0.1337)
- Status: Forming — not yet triggered

### Open Questions
1. **Pattern confidence calibration:** What % should a flag breakout get? Need historical baseline.
2. **Pattern vs existing signals:** Replace mtf_macd as primary, or only act as flip confluence?
3. **Which timeframe for detection:** 1m for position management, 5m for signal generation?
4. **Volume quality:** Filter dust trades? Require minimum volume on breakout?

---

## Self-Learning via Weights & Biases (W&B)
**Status:** ✅ LIVE — 2026-04-06
**Owner:** Agent + T
**Summary:** W&B offline experiment tracking added to all three core systems. Enables systematic ML-driven self-improvement by recording every decision, trade outcome, and model run with full audit trails and visual comparison dashboards.

### What It Enables

**1. candle_predictor — model training & hyperparameter tuning**
- Logs: per-run predicted/inverted counts, tokens processed, errors, success flag
- Local backup: `/root/.hermes/wandb-local/candle-predictor-<ts>.json`
- Sweep config ready: `/root/.hermes/scripts/candle_predictor_sweep.yaml`
- What it unlocks: compare `qwen2.5:1.5b` vs other models, tune inversion_threshold, batch size, learning rate — all visualized
- Next: run `wandb agent` against the sweep yaml once API key is available

**2. ab_utils — A/B test comparison dashboard**
- Logs: every variant assignment (token, direction, variant name) + outcomes (win/loss/metric_value)
- Local backup: `/root/.hermes/wandb-local/ab-tests.jsonl` (JSON Lines, append-only)
- What it unlocks: visually compare variant A vs B performance per test, per token, over time
- Current A/B tests already tracked via `get_cached_ab_variant()` + `record_ab_outcome()`
- Calling code just imports and calls `record_ab_outcome('test_name', 'variant_id', 'win')` — zero extra work per test

**3. ai_decider — decision audit trail**
- Logs: every hot-set decision cycle — winner token, direction, score, regime, speed percentile, n_signals, n_pattern_signals, decision reason
- Local backup: `/root/.hermes/wandb-local/decisions.jsonl` (JSON Lines, append-only)
- What it unlocks: replay any decision, see exactly why a token won over others, track pattern vs momentum signal win rates over time
- Per-decision cycle (not per-token) — each cycle logs the winner only

### Architecture
```
Offline mode (anonymous, no API key):
  wandb init mode=offline project=hermes-ai
  → Run files queued to /root/.hermes/wandb-local/wandb/

Local backups always written regardless of W&B state:
  candle_predictor → /root/.hermes/wandb-local/candle-predictor-<ts>.json
  ab_tests          → /root/.hermes/wandb-local/ab-tests.jsonl
  ai_decider        → /root/.hermes/wandb-local/decisions.jsonl

Sync later (one command, once API key available):
  WANDB_API_KEY=key /root/.hermes/scripts/wandb-sync.sh
```

### Files Changed
| File | Change |
|------|--------|
| `/root/.hermes/scripts/candle_predictor.py` | +wandb.init/log/finish, `--nowandb` flag, local JSON backup |
| `/root/.hermes/scripts/candle_predictor_sweep.yaml` | **NEW** — bayes sweep over inversion_threshold, temp |
| `/root/.hermes/scripts/ab_utils.py` | +`_get_wandb_run()`, `record_ab_outcome()`, local .jsonl backup |
| `/root/.hermes/scripts/ai_decider.py` | +`_log_wandb()` per decision cycle, local .jsonl backup |
| `/root/.hermes/scripts/wandb-sync.sh` | **NEW** — sync offline runs when API key available |
| `/root/.hermes/wandb-local/` | **NEW** — local backup directory |

### Next Steps (once you have W&B API key)
1. Get key: wandb.ai → Settings → API keys
2. Store it: `echo 'WANDB_API_KEY=your_key' >> /root/.hermes/scripts/.env`
3. Sync: `WANDB_API_KEY=your_key /root/.hermes/scripts/wandb-sync.sh`
4. View: wandb.ai/hermes-ai — full dashboards for all 3 systems
5. Run sweeps: `wandb agent hermes-ai/candle-predictor --count 50` (tunes model params automatically)

### Local Streamlit Dashboard — LIVE
**URL:** http://localhost:8501
**Start:** `/root/.hermes/scripts/dashboard.sh start`
**Stop:** `/root/.hermes/scripts/dashboard.sh stop`
**Status:** `/root/.hermes/scripts/dashboard.sh status`
**Health check:** cron runs every 5 min to keep it alive

5 pages:
- 🏠 Overview — quick stats across all 3 systems
- 🕯️ candle_predictor — run history, predicted/inverted counts, trends
- 🔀 A/B Tests — variant win rates, event log, per-test breakdown
- 🎯 ai_decider — full decision audit, regime breakdown, speed vs score scatter
- 📈 Signal Stats — live from signals DB, calibration status, WR by signal type

No internet required. Data from local JSONL files, auto-refreshes every 10s.

---

## ATR + Trailing Stop Bug Fixes (Session 2026-04-06)
**Status:** ✅ COMPLETE — 2026-04-06
**Owner:** ai-engineer
**Summary:** Five bug fixes applied to position_manager.py and decider-run.py addressing trailing stop false-triggers, missing TP_PCT constant, phase2 ATR buffer, and dynamic SL in delayed entries.

### Fixes Applied

| # | Fix | File | Line | Status |
|---|-----|------|------|--------|
| 1 | `trailing_active = True` indentation corrected — was inside `if profit_pct >= trailing_start_pct:` block, always evaluating to True regardless of condition | `position_manager.py` | ~1609 | ✅ Verified |
| 2 | Phase2 buffer ATR logic — `phase2_buffer_atr` now used when available; falls back to volume-confirmed buffer | `position_manager.py` | ~1295 | ✅ Verified |
| 3 | `TP_PCT = 0.08` constant added — was referenced in `get_trade_params()` but missing, causing NameError on import | `position_manager.py` | ~61 | ✅ Verified |
| 4 | Trailing activation ATR-based trigger — activates at `1× ATR profit` instead of fixed 1% | `position_manager.py` | ~1597 | ✅ Verified |
| 5 | Trailing buffer ATR-based — buffer = `30% × ATR` (floored at 0.2% absolute) | `position_manager.py` | ~1281 | ✅ Verified |
| 6 | `decider-run.py` `execute_trade()` uses `_compute_dynamic_sl()` for entry SL | `decider-run.py` | ~627 | ✅ Verified |
| 7 | `decider-run.py` `_execute_delayed_entries()` uses `_compute_dynamic_sl()` for delayed entry SL | `decider-run.py` | ~551 | ✅ Verified |

### ATR-based SL Test Results (Verified)
```
DYDX LONG: entry=0.102, SL=0.0998 (2.16%)  — ATR 1.08%, k=2.0
DYDX SHORT: entry=0.102, SL=0.1042 (2.16%)
SOL LONG: entry=90.0, SL=88.8664 (1.26%)   — ATR 0.84%, k=1.5
BTC LONG: entry=95000, SL=94287.50 (0.75%) — ATR 0.43%, floor applied
TAO LONG: entry=250, SL=242.32 (3.07%)    — ATR 1.54%, k=2.0
```

### PostgreSQL Trade Performance (Last 7 Days — Baseline Before Fix)
- **Total closed:** 54 | **Win rate:** 51.9% | **Net PnL:** +13.68 USDT
- **Avg trade:** +0.25 USDT (+0.76%)
- **Avg duration:** 1.4 hours
- **Direction:** LONG n=29 net=+5.00 | SHORT n=25 net=+8.68

### Findings
1. **Speed=50% anomaly**: The signals DB schema has NO `speed` column. The "50%" figure is likely computed at display/report level, not stored in DB. All 1056 hot-set signals (`review_count >= 1`) pass through the filter; 360 signals have `review_count=0` and never enter hot-set. Root cause of "only hot-set filtering through" needs further investigation in the reporting layer.
2. **Phase2 ATR fix**: Verified at line ~1295 — `phase2_buffer_atr` is now checked via `'phase2_buffer_atr' in dir()` before falling back to volume-confirmed.
3. **trailing_active indentation**: Fixed at line ~1609 — `trailing_active = True` is now correctly inside the `if profit_pct >= trailing_start_pct:` block.

---

*Format: `## Project Name | Status | Owner` — update status when it changes.*
---

## SL/TP Protection System Fixes
**Status:** 🚧 PHASE 1 DONE — 2026-04-08
**Owner:** Agent
**Summary:** 8 bugs confirmed in stop-loss and trailing stop-loss system. 4 fixed (B1/B2/B3/B8), 4 remaining (B4/B5/B6/B7). Live trading active with `hype_live_trading.json = true`.

### Bug Registry (as of 2026-04-08)
| # | Bug | File | Impact | Status |
|---|-----|------|--------|--------|
| B1 | Trailing SL never pushed to HL after activation | position_manager.py | ATR calculated but `place_sl()` only called on entry | ✅ FIXED (already had BUG-8 fix, verified) |
| B2 | Cascade new position has no SL | position_manager.py | Post-flip position has no HL protection | ✅ FIXED (cascade_flip now calls place_sl+TP) |
| B3 | No TP/SL placed on initial entry | brain.py | `place_order()` fires but SL/TP never sent to HL | ✅ FIXED (brain.py add_trade now calls place_sl+TP) |
| B4 | Cascade PnL tracking absent | position_manager.py | Can't determine if flips succeeded → cooldown dead | ✅ FIXED (cascade_sequences table created, recording in cascade_flip) |
| B5 | HL rate-limit skips cycles silently | hl-sync-guardian.py + position_manager | 429 causes silent skip, no cache, no retry | ✅ FIXED (position_manager B5 retry added, guardian already had backoff) |
| B6 | Guardian reason = "guardian_missing" | hl-sync-guardian.py | No trackability, all closes logged as same value | ✅ FIXED (standardized reason vocabulary) |
| B7 | No manual close kill switch | hl-sync-guardian.py | T can't tell guardian "I closed this" | ✅ FIXED (guardian_kill_switch.json + _is_token_killed check) |
| B8 | Two scripts writing trades.json | hermes-trades-api.py + update-trades-json.py | Race condition risk | ✅ FIXED (atomic flock added to both scripts) |

### Fixes Applied 2026-04-08

**B8 (Atomic Write Lock):**
- Added `_atomic_write()` using `fcntl.flock()` to both `hermes-trades-api.py` and `update-trades-json.py`
- `update-trades-json.py` KEPT as safety net (not removed — it has no `signal_schema` import overhead)
- Both scripts write to same path with proper locking

**B3 (Entry SL+TP):**
- `brain.py add_trade()`: after `mirror_open()` succeeds, now calls `place_sl()` and `place_tp()` on HL immediately
- SL/TP read back from trade record (stop_loss, target columns)
- Non-fatal if SL placement fails — paper trade still tracked

**B2 (Cascade SL+TP):**
- `position_manager.py cascade_flip()`: after `place_order()` succeeds, reads back new trade's SL/TP from DB and calls `place_sl()` + `place_tp()` on HL

**B1:** Already implemented (BUG-8 fix in position_manager — verified in code at line ~1895-1920)

**B7 (Kill Switch):**
- Created `/var/www/hermes/data/guardian_kill_switch.json`
- Added `_is_token_killed()`, `_add_to_kill_switch()`, `_remove_from_kill_switch()` to hl-sync-guardian.py
- `_close_paper_trade_db()` now checks kill switch before closing any token
- T can manually close a token on HL and add it to kill switch — guardian will NOT close the paper trade

**B6 (Standardized Reasons):**
- All `close_reason`/`exit_reason`/`guardian_reason` now use UPPERCASE_STANDARD vocabulary:
  - `ORPHAN_PAPER`, `MAX_POSITIONS`, `HOTSET_BLOCKED`, `HOTSET_BLOCKED_SHORT`, `HOTSET_BLOCKED_LONG`
  - `CUT_LOSER`, `STALE_ROTATION`, `CASCADE_FLIP`, `MANUAL_CLOSE`
- Updated all SQL `UPDATE` statements and `_close_paper_trade_db()` call sites

**B5 (429 Backoff):**
- Added `_retry_hl_call()` helper inside trailing SL push section
- Retries up to 3× with exponential backoff (5s, 10s, 20s) on 429/rate-limit errors
- Both `get_open_hype_positions()` and `exchange.order()` now use retry logic

**B4 (Cascade Sequences):**
- Created `cascade_sequences` table in brain DB (sequence_id, parent_trade_id, trade_id, direction, entry_px, exit_px, pnl_usdt, pnl_pct, close_reason, created_at, closed_at)
- Added `_record_cascade_sequence()` function to position_manager.py
- `cascade_flip()` now records: (a) the close of the old trade with PnL, (b) the open of the new trade with new trade_id
- All flips in same cascade share `sequence_id = parent_trade_id`
- B4: Add `cascade_sequences` table to brain DB
- B5: Add retry/backoff to position_manager for 429 responses
- B6: Fix guardian reason column with specific close reasons
- B7: Create `guardian_kill_switch.json` with manual close protection

**Reference:** [.hermes/plans/2026-04-08_010451-conversation-plan.md](./.hermes/plans/2026-04-08_010451-conversation-plan.md)


## Hebbian Associative Memory Network
**Status:** 🚧 IN PROGRESS — 2026-04-09
**Owner:** Agent
**Summary:** Build a Hebbian "neural network" memory layer for Hermes — "neurons that fire together, wire together." When concepts co-occur across any domain (trading, projects, infrastructure, skills), their connection strength grows. Retrieval returns ranked associations based on Hermes's own experience.

**Why:** Current memory is structural (brain/*.md files) and semantic (Tokyo Brain API). Neither links concepts by co-occurrence experience. Hebbian memory fills this gap.

**Architecture:** SQLite-based `associative_memory.db` — concept_nodes + synapse_weights. Self-contained, no external deps.

### Components
| Component | File | Status |
|-----------|------|--------|
| Core engine | `scripts/hebbian_engine.py` | ✅ Done |
| Initial seeding | `scripts/hebbian_learner.py` | ✅ Done — 82 nodes from brain files |
| Retroactive seed | `scripts/hebbian_seed_sessions.py` | ✅ Done 2026-04-09 — 9,705 sessions → 1.04M pairs |
| Integration hooks | SOUL.md + entity extractor + session learner | ✅ Done 2026-04-09 |
| Daily crons | systemd timers (no cron) | ✅ Done 2026-04-09 |
| MCP tool | ⚠️ Skipped | No MCP server found — superseded by direct CLI + cron |
| Decay cron | TBD | 🚧 Pending |

**Key decisions:** [.hermes/plans/2026-04-09_060840-how-would-we-create-a-neural-network-type.md](./.hermes/plans/2026-04-09_060840-how-would-we-create-a-neural-network-type.md)

**Reference:** Donald Hebb, 1949 — "Neurons that fire together, wire together"
