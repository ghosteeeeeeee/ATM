# PROJECTS.md — Hermes Project Tracker

> Active projects. Updated at end of every session.
> Search: `grep -n "Status:\|Owner:\|## \|### " /root/.hermes/brain/PROJECTS.md`

---

## Pipeline Health Monitoring (WASP)
**Status:** ✅ ACTIVE — Ongoing
**Owner:** Agent
**Summary:** WASP runs every 5 min via cron. 0 ERRORS, 5 non-blocking warnings.
**Blockers:** None

---

## Hot-Set Compaction Rewrite
**Status:** 🚧 PARTIAL — 2026-04-08
**Owner:** Agent
**Summary:** Redesign hot-set pipeline: 10-min signals → AI compact to top 20 → survivors gain strength → reverse signals penalize/evict. Non-top-20 immediately purged to REJECTED.
**Blockers:** None

### Completed ✅
- AI compaction prompt rewritten (Q_final variant)
- `***` token recovery in parsing
- `z_val:+.2f` None crash fixed (ai_decider.py:1838)
- `opened_at` → `open_time` fixed (ai_decider.py:1749)
- `needs_sl` undefined fixed in position_manager.py
- RSI/MACD confidence caps: RSI 50→70, MACD 50→80, conf-2s 70→80

### Remaining ⬜
- [ ] Change hot-set query 3h → 10 mins
- [ ] Remove `review_count >= 1` requirement
- [ ] Add PURGE step: non-top-20 → `decision='REJECTED', rejected_at=NOW()`
- [ ] Add `rejected_at` and `rejection_reason` columns
- [ ] Simplify state machine: GENERATED → PENDING → APPROVED / REJECTED / EXECUTED

**Critical finding:** MiniMax-M2 with thinking uses full `max_tokens` for BOTH reasoning + output. Need `max_tokens=4000+`.

---

## Signal Quality Improvement
**Status:** 🚧 ONGOING — 2026-04-05
**Owner:** Agent
**Summary:** 282 signals below 55% confidence in last hour — signal gen may be flooding. 5 WAIT signals never re-reviewed: BIGTIME, SNX, ORDI, DYDX, ZETA.
**Blockers:** None

---

## Session Checkpoint/Restore System
**Status:** ⚠️ DEFERRED — 2026-04-05
**Owner:** TBD
**Summary:** Hermes lacks session snapshot/restore for LLM agent. Would need ~4-6 hrs to build.
**Blockers:** Low priority vs pipeline trading issues

---

## AI Trading Machine (ATM) — Standalone Docker
**Status:** 🚧 IN PROGRESS — 2026-04-06
**Owner:** T + Agent
**Summary:** Self-contained Docker container — pipeline, dashboards, noVNC, SSH, paper trading by default.
**Blockers:** Pipeline audit (Step 1) not yet completed
**Reference:** `/root/.hermes/plans/2026-04-05_183622-can-we-set-up-a-new-docker-container.md`

### ATM Structure
```
/root/.hermes/ATM/
├── ATM-Architecture.md      # System design
├── trading-docker.md       # 374-line Docker build spec
└── config/stoploss.md      # All exit rules source of truth
```

### What's Been Done
- Plan written, `ATM/` folder created
- `ATM/config/stoploss.md` — full exit rules reference

### Next Steps
1. Audit pipeline scripts — confirm entry points and dependencies
2. Export `signals_hermes.sql` + `signals_data_snapshot.json` from current DB
3. Write `export_dashboards.py`
4. Fix CSP in nginx.conf
5. Write Dockerfile + docker-entrypoint.sh + docker-compose.yml

---

## Chart Pattern Recognition
**Status:** 🚧 IN PROGRESS — 2026-04-06
**Owner:** Agent + T
**Summary:** Add chart pattern detection (Bull/Bear Flag → H&S → Wyckoff → Elliot Wave) as signal source feeding into Hermes pipeline — initially cascade flip confluence, eventually standalone entries.
**Blockers:** None — Phase 1 ready to build

### Signal Priority — COMPETITION MODEL (T APPROVED 2026-04-06)
- All signal types compete equally — `pattern_*` NOT subordinate to `mtf_macd`
- Pattern scanner runs FIRST so patterns get into DB early
- Pattern signals get **1.25× confidence multiplier** in ai_decider
- After 50+ trades: WR > 55% = boost, WR < 45% = reduction, WR < 40% = disabled

### Phase Breakdown
| Phase | Patterns | Integration | Status |
|-------|----------|-------------|--------|
| Phase 1 | Bull/Bear Flag | Cascade flip confluence | 🚧 In progress |
| Phase 2 | Wyckoff + H&S | Cascade flip + backtest | ⬜ Not started |
| Phase 3 | Elliot Wave | Standalone entry signals | ⬜ Not started |

### Key Files
| File | Role |
|------|------|
| `pattern_scanner.py` | **NEW** — all pattern detection logic |
| `signal_gen.py` | Calls pattern_scanner, emits pattern signals |
| `position_manager.py` | Cascade flip queries pattern_scanner as confluence |
| `signal_schema.py` | `get_ohlcv_1m()` already exists ✅ |

---

## True-MACD Cascade System (Core Strategy)
**Status:** ✅ LIVE — 2026-04-06
**Owner:** Agent
**Summary:** MTF MACD alignment + cascade detection — core strategy filter. 15m leads → 1h follows → 4h confirms. Prevents bad entries at local peaks.

### Cascade Entry Rules
```
LONG: 15m macd_above_signal + histogram_positive + (1h OR 4h BULL) + 4h BULL regime
SHORT: mirror logic
BLOCKED: 15m flipped but larger TFs opposite / 15m/1h conflict / 4h already flipped
```

### Integration
- signal_gen.py: Cascade ACTIVE + aligns → **+10 boost**; OPPOSITE → **BLOCK**
- position_manager.py: Cascade ACTIVE + direction ≠ position → **immediate flip, conf=95**

---

## Self-Learning via Weights & Biases (W&B)
**Status:** ✅ LIVE — 2026-04-06
**Owner:** Agent + T
**Summary:** W&B offline experiment tracking for all 3 core systems — systematic ML-driven self-improvement with full audit trails.

### 3 Systems Tracked
| System | Logs | Local Backup |
|--------|------|--------------|
| candle_predictor | per-run predicted/inverted counts, tokens | `candle-predictor-<ts>.json` |
| ab_utils | variant assignments + outcomes | `ab-tests.jsonl` |
| ai_decider | hot-set decision cycles | `decisions.jsonl` |

### Streamlit Dashboard — LIVE
**URL:** http://localhost:8501 | **Start:** `dashboard.sh start` | **Health:** cron every 5 min

5 pages: Overview, candle_predictor, A/B Tests, ai_decider, Signal Stats

---

## SL/TP Protection System Fixes
**Status:** 🚧 PHASE 1 DONE — 2026-04-08
**Owner:** Agent
**Summary:** 8 bugs in stop-loss/trailing system. 4 fixed (B1/B2/B3/B8), 4 remaining (B4/B5/B6/B7). Live trading active.

### Bug Registry
| # | Bug | Status |
|---|-----|--------|
| B1 | Trailing SL never pushed to HL after activation | ✅ FIXED |
| B2 | Cascade new position has no SL | ✅ FIXED |
| B3 | No TP/SL placed on initial entry | ✅ FIXED |
| B4 | Cascade PnL tracking absent | ✅ FIXED |
| B5 | HL rate-limit skips cycles silently | ✅ FIXED |
| B6 | Guardian reason = "guardian_missing" | ✅ FIXED |
| B7 | No manual close kill switch | ✅ FIXED |
| B8 | Two scripts writing trades.json (race) | ✅ FIXED |

### Key Fixes
- **B8:** `fcntl.flock()` atomic write lock on both trade-writers
- **B3:** `brain.py add_trade()` now calls `place_sl()` + `place_tp()` after `mirror_open()`
- **B2:** `cascade_flip()` reads back new trade's SL/TP and calls HL
- **B7:** `guardian_kill_switch.json` — T can manually close, guardian won't
- **B5:** 3× retry with exponential backoff (5s, 10s, 20s) on 429 errors
- **B4:** `cascade_sequences` table records flip PnL per sequence

---

## Hebbian Associative Memory Network
**Status:** 🚧 IN PROGRESS — 2026-04-09
**Owner:** Agent
**Summary:** Hebbian "neural network" memory layer — "neurons that fire together, wire together." SQLite-based `associative_memory.db`.

### Components
| Component | File | Status |
|-----------|------|--------|
| Core engine | `scripts/hebbian_engine.py` | ✅ Done |
| Initial seeding (82 nodes) | `scripts/hebbian_learner.py` | ✅ Done |
| Retroactive seed (9,705 sessions → 1.04M pairs) | `scripts/hebbian_seed_sessions.py` | ✅ Done 2026-04-09 |
| Integration hooks | SOUL.md + entity extractor + session learner | ✅ Done 2026-04-09 |
| Daily crons | systemd timers | ✅ Done 2026-04-09 |
| MCP tool | ⚠️ Skipped | Superseded by CLI + cron |
| Decay cron | TBD | 🚧 Pending |

**Reference:** Donald Hebb, 1949

---

*Format: `## Project Name | Status | Owner` — update status when it changes.*
