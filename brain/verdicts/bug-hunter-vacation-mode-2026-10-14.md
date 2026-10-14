# Bug Hunter: Vacation Mode Final Verification (2026-10-14)

**Scope:** Final pre-departure check of the 5 shipped items (cell stats wiring, T simulator, ML classifier, vacation plan, CEO recalibration) plus the vacation safety net.
**Method:** All checks executed live (code parsed, DBs queried, scripts run, logs tailed, execution path simulated). No results from memory.

---

# VERDICT: BLOCKER

The five shipped items are implemented correctly and are safe. **But the vacation guardrail — the CEO-mandated "only hard safety net" — cannot actually stop live trading.** `pause_trading()` writes `{"live_trading": false}` to `hype_live_trading.json`, while the real execution gate (`is_live_trading_enabled()`, used by `brain.py:441` and `decider_run.py:3333`) consults ONLY the `LIVE_TRADING_ENABLED` constant and explicitly ignores that JSON. Proven live: simulated a paused switch, gate still returned `True`. 44/44 trades in the last 24h were real (`paper=false`, Hyperliquid) via that exact path.

**Do not depart until the guardrail pause path is wired to actual execution (or the guardrail's claim is downgraded and T accepts unpaused risk).**

---

## Check Results

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Syntax (4 scripts) | **PASS** | `ast.parse` on signal_compactor.py, t_simulator.py, feature_engineering.py, train_classifier.py → `ALL OK` |
| 2 | Cell stats SQL query | **PASS** | `bb_bounce_v2_long LONG HIGH` → wr_raw=0.771, n=35, tradeable=1. 697 cells, 54 tradeable-class rows present, parameterized `?` placeholders (no SQL injection), `_cs_conn` closed in `finally` (signal_compactor.py:2187-2188) |
| 2b | Multiplier math (functional, verbatim block exec'd) | **PASS** | tradeable → 1.2x ✅; n≥15 & wr<0.40 → 0.5x (pump-chain+ HIGH: wr=0.37 n=30 → 0.5) ✅; no-row → 1.0 ✅; None keys → 1.0, no crash ✅ |
| 3 | T simulator search | **PASS** | Index exists: 74 vectors, dim=384, decisions.json=74. Search "should we add a new filter" returned 3 relevant past decisions (filter-deferral, velocity-filter approval, velocity-bypass rejection). All files opened via `with` — no handle leaks |
| 4 | ML model load | **PASS** | `RandomForestClassifier, n_features_in_=80` = `trade_classifier_features.json` feature_cols (80) ✅. Model is **not** consumed by any live decision path (inert) |
| 5 | Recalibration constants | **PASS** | `RETURN_EXHAUSTION_SHORT_ENABLED=False` (L3434), `MAXXED_ATR_PCT_THRESH=6.0` (L765), `PENALTY_MULT_FLOOR=0.5` (L766), `SHORT_RSI_FLOOR=35` (L916), `SHORT_RSI_HARD_FLOOR=35` (L926), `RR_ENGINE_CONF_HARD_BLOCK_RR_CONFIRMED=0.35` (L3958) — all in `scripts/hermes_constants.py` |
| 5b | RR exemption code | **PASS** | `risk_reward_engine.py:1151-1185`: BTC continuum read, <600s freshness, LONG/SHORT structure match, fail-open, connection closed in finally. `[RR-REGIME-EXEMPT]` tag live **410×** in compactor log → revert trigger measurable (prior MEDIUM-1 fixed in 7cc35519 ✅) |
| 5c | Revert triggers logged | **PASS** | SHORT_RSI_FLOOR, HARD_FLOOR, RR_CONFIRMED constants carry explicit revert triggers in comments; RR tag fires live. (MAXXED/floor/return-exhaustion comments lack triggers — cosmetic, see LOW-2) |
| 6 | `_cs_conn` closed in finally | **PASS** | signal_compactor.py:2187-2188 |
| 7 | Pipeline health (errors in last 100 lines) | **PASS** | `grep -cE "Traceback|ERROR" logs/pipeline.log` → **0** |
| 8 | CELL-STATS multiplier firing live | **PASS (with findings)** | Tag never fired (0 occurrences, 35+ min / ~35 cycles since deploy) — **not a code bug**: the block executes every cycle (proved by functional exec) and all 40 live signals resolve **neutral** by design (dominant cell `pump-chain-` SHORT EXTREME: n=119, wr=0.4622 → neutral since wr≥0.40). See MEDIUM-1/MEDIUM-2 for why the wiring is effectively inert today |
| 9 | Plan references & kill criteria | **FAIL (doc)** | Plan file exists, all files it references exist, kill criteria are specific (35% WR / -$3.00 / 10T−$1 / day-14 n≥30). **But commit `477a8f6d` cited for "CEO recalibration" is the WRONG commit** — it is "FIX: bull structure override for pump entry gates" (2026-10-11). Actual recalibration = `84a38707` (verified via `-S` bisection). Also omits follow-up `0ebfd16b` (cell-stats key-mismatch fix). See LOW-1 |
| 10 | **Vacation guardrail pause path** | **FAIL — BLOCKER** | See BLOCKER-1 below |
| 11 | (extra) Guardrail runtime status | **INFO** | Timer live (30-min), last run 16:10 UTC, currently **ESCALATE**: "48h WR 28.3% < 40.0% with 92 trades". 24h PnL −$0.46 (kill criterion −$3.00 not tripped). See MEDIUM-3 |

Commits verified to exist: `12f14b88` ✅, `32266d59` ✅, `a907936c` ✅, `477a8f6d` ✅ (but wrong citation), `84a38707` ✅ (actual recalibration).

---

## Bugs

### 🔴 BLOCKER-1 — Guardrail auto-pause is a no-op for live trading
- **Where:** `scripts/vacation_guardrail.py:64-73` (`pause_trading`) vs `scripts/hyperliquid_exchange.py:273-282` (`is_live_trading_enabled`), consumed by `scripts/brain.py:441` and `scripts/decider_run.py:3333`.
- **What:** `pause_trading()` only writes `{"live_trading": False, ...}` to `hype_live_trading.json`. Since commit `28215e7e`, `is_live_trading_enabled()` returns the static constant `LIVE_TRADING_ENABLED` (=True, L33) and its docstring explicitly states the JSON "is NOT consulted". `brain.py` rejects every trade when `not is_live_trading_enabled()`; `decider_run.py:3333` sets `paper = not is_live_trading_enabled()` → always `--real`.
- **Proof (executed, not read):** pointed `_KILL_FILE` at a temp JSON containing `live_trading:false` (byte-identical to what the guardrail writes) → `_load_flags()` returned the paused flag, `is_live_trading_enabled()` still returned **True**. Corroborating: 44/44 closed trades in 24h are `paper=false` on Hyperliquid via this path; `run_pipeline.py`'s JSON check only sets a log label (`mode`, used at L207/265/272 only).
- **Impact:** The published kill criterion "24h PnL < −$3.00 → **Auto-pause**, alert T" cannot execute. Worse than absent: on trigger the guardrail will log "🛑 TRADING PAUSED" while real orders continue — false assurance during T's absence. The guardrail also does not close existing open positions (unlike `disable_live_trading()`, which does).
- **History note:** the JSON gate was deliberately removed to fix ghost trades (brain rejected while decider thought it succeeded). Any fix must not silently reintroduce that split-brain.
- **Recommended fix (pick one, CEO call):**
  1. **Preferred:** `pause_trading()` calls `hyperliquid_exchange.disable_live_trading()` (closes open positions + writes flags) AND stops the execution timers (`systemctl stop hermes-pipeline.timer hermes-signal-compactor.timer` + decider entrypoint), so pause is physical, not advisory.
  2. Reintroduce the JSON into the single gate: `return LIVE_TRADING_ENABLED and _load_flags().get("live_trading", True)` — one line, keeps constant as master, restores runtime kill; requires re-testing the ghost-trade scenario that motivated its removal.
  3. Minimum honesty fix if neither ships before departure: change the guardrail log/alert text to "PAUSE REQUESTED — NOT ENFORCED" so nobody believes trading stopped.

### 🟠 MEDIUM-1 — Cell-stats wiring is inert for the current signal mix (coverage gap)
- **Where:** `scripts/signal_compactor.py:2142-2190`.
- **What:** Zero `[CELL-STATS]` lines in the entire compactor log (35+ cycles). Reproduced the exact lookup for all 40 live signals: every one resolves neutral. The live key format `pump-chain`/`pump-chain-` matches the historical losing cell `pump-chain-` SHORT EXTREME (n=119, wr=0.4622) — which sits just above the 0.40 dampen threshold, so it gets neither dampen nor boost. Tradeable cells that exist (`pump_chain` LONG EXTREME, n=22, 63.6% WR) are not being hit by the current SHORT-heavy flow.
- **Impact:** The headline feature of vacation mode ("combo selection") currently changes no scores. Not money-losing, but the plan's premise ("entry scoring now uses 697-cell statistics") is not yet observable in production.
- **Fix:** add a debug log (or counter) for neutral resolutions so firing rate is measurable; review with CEO whether wr threshold 0.40/0.60 bands fit the current 45.8% global WR.

### 🟠 MEDIUM-2 — PENALTY_MULT_FLOOR=0.5 swallows most cell-mult effects
- **Where:** `signal_compactor.py:2199-2215` × recalibration change #3.
- **What:** `_cell_mult` is multiplied into `_mult_product`, then `max(product, 0.5)` is applied. Live multiplier products today run 0.003–0.5 (see `[SCORE-FLOOR]` lines). When base product < 0.5, both the 0.5x dampen and the 1.2x boost land at the floor and produce **identical** final scores (e.g. 0.2×0.5=0.1→0.5 and 0.2×1.2=0.24→0.5). The two recalibrations interact: raising the floor to exactly 0.5 made the cell dampen a no-op for the majority of live signals.
- **Impact:** Direction is neutral (no trap), but the cell-stats wiring and the penalty-floor recalibration partially cancel each other. **Fix:** exempt `_cell_mult` from the floor (like `rr_mult`), or apply cell stats post-floor.

### 🟠 MEDIUM-3 — Guardrail is already in ESCALATE at departure, and WARNING alerts reach nobody
- **Evidence:** last run 16:10 UTC: "48h WR 28.3% < 40.0% with 92 trades" → `write_alert('WARNING', ...)` to `automation/ceo/vacation_alerts.json`. Only the CRITICAL branch pauses (which is broken — BLOCKER-1). No notification channel (no page/telegram/email) is wired; a JSON file that T (away) and the CEO cycle must remember to read.
- **Fix:** route WARNING/CRITICAL to whatever channel the watchdog already pages on, and confirm someone monitors it while T is off.

### 🟡 LOW-1 — Plan cites wrong commit for CEO recalibration
`plans/t-vacation-mode-2026-10-14.md:17` cites `477a8f6d` ("FIX: bull structure override for pump entry gates", 2026-10-11). Actual 5-change recalibration = **`84a38707`** (2026-10-13; verified by `git log -S` on all 5 constants). Line 14 also omits follow-up `0ebfd16b` (cell-stats key-mismatch fix) that materially changed the wiring. Fix the table so the audit trail is correct.

### 🟡 LOW-2 — Stale comments (cosmetic, contradicts recalibration)
- `signal_compactor.py:4023` "MAXXED_ATR_PCT_THRESH (4.0)" → now 6.0
- `decider_run.py:1104`, `volatility_gate_v2.py:361` "SHORT_RSI_HARD_FLOOR=45" → now 35
- `hermes_constants.py:4142` `PUMP_CHAIN_V6_SHORT_RSI_MIN` comment "aligned w/ SHORT_RSI_HARD_FLOOR=45" → now 35
- `risk_reward_engine.py:1152` getattr default 0.70 vs `:1182` default 0.55 for the same constant family (constant exists=0.55, runtime unaffected)
- `risk_reward_engine.py:1183` hardcodes "0.35-0.55 band" text (values drift → message lies)

### 🟡 LOW-3 — ML train/inference feature consistency is NOT guaranteed (latent — no consumer today)
`feature_engineering.build_dataset()` computes imputation medians and top-30 one-hot categories **from the batch it is given**. Only `feature_cols` (names) is saved with the model — not the medians or dummy categories. Any future single-row inference will silently build a different 80-col vector. Also: `train_test_split` is random, not temporal, and 5-fold CV AUC is **0.438 ± 0.094** (below chance) while the held-out test AUC is 0.583 — the plan quotes only 0.58. Model is inert today, so no live risk. Fix in v2: persist a sklearn `Pipeline`/ColumnTransformer with the model, use time-based splits, report CV not test AUC.

### ℹ️ INFO
- T simulator index is stale vs source: index built 15:39, `ceo_kanban.md` modified 15:47 — re-run `python3 scripts/t_simulator.py index` before the auditor relies on it (also only 2 files in `brain/decisions/` — thin corpus).
- `vacation_guardrail.py` hardcodes `WWW_DATA := '/var/www/hermes/data'` (walrus) instead of importing from `paths` — convention violation, works today.
- `feature_engineering.query_trades` interpolates `days` into SQL via f-string — int default, local script, low risk; use a bind param.
- MAXXED (6.0) fired 0× today, RETURN_EXHAUSTION 0× (disabled) — both as intended by the recalibration.
- Prior bug_hunter follow-ups MEDIUM-1 (dead RR tag) and MEDIUM-2 (decider 0.3 floor) were both fixed in `7cc35519` — verified in code and live logs.

---

## Recommendations (ordered)

1. **Before T leaves (mandatory):** fix BLOCKER-1 — wire the guardrail pause to physical execution stop + position close, or explicitly accept and document that no auto-pause exists.
2. Fix the plan's commit citation (`84a38707`, plus `0ebfd16b`).
3. Wire guardrail WARNING/CRITICAL to a monitored channel (it is already escalating: 48h WR 28.3%).
4. Add neutral-resolution logging + hit counter to the cell-stats wiring so "is it firing?" is answerable from logs.
5. Decide the floor/cell-mult interaction (exempt `_cell_mult` from SCORE-FLOOR like `rr_mult`).
6. Re-index the T simulator; clean the stale comments; save the ML preprocessing pipeline with the model before building v2 inference.

**Signed:** bug_hunter, 2026-10-14 16:2x UTC — all numbers above come from executed commands in this session.
