# Bug Hunter Verdict — Full Session Fix Audit (2026-10-05 18:00 → 2026-10-06)

**Auditor:** bug_hunter (delegated subagent)
**Audit window:** commits 2026-10-05 18:00 → 2026-10-06 17:00 (14 key commits) + live state as of 2026-10-06 22:20 UTC
**Repo:** /root/.hermes @ dbfe2dd7 (HEAD at audit time; working tree clean)
**Scope:** ~15 commits affecting signal compactor, decider, chop detector, candle pipeline, RSI computation, LLM context gate

---

## VERDICT: SAFE — 0 BLOCKERS, 4 WARNs, 1 SUPERSEDED commit

All 14 audited commits are present in HEAD, syntax-clean, and demonstrably functioning in live logs. The critical failure modes from the session brief (7/7 hard_max_loss, no SHORTs in bear, 69 days flat candles, advisory-only penalty engine) are all resolved or materially improved:

- **SHORTs execute in bear markets again** — live `CONTINUUM-OVERRIDE` SHORT lines firing 21:41–22:00 (ema300=AT path proven); DOGE pump-chain- SHORT won +$0.08 today via RR-engine exit.
- **Candle data recovered** — 1m: 88.8% real OHLC (H>L) vs 0% flat era; 5m: 97.6%; 15m: 97.0% (last 30 min, 17 active tokens).
- **RSI math verified correct** — rsi_utils matched an independent Wilder replica EXACTLY on 10/10 token×TF combos; direction sanity (rising→RSI>50) 10/10 OK; zero remaining inverted-delta sites in any gate path.
- **Penalty engine enforced, not advisory** — live `RR HARD BLOCK R:R=0.66<0.7 → mult=0.00` and `HALL-SHAME WR=40%<55% BLOCKED` lines; both KAS/CRV SHORTs correctly killed at 21:58.
- **hard_max_loss streak broken** — today: SHORT 4T/1W net −$0.29 (2 HML, 1 RR-win, 1 open); LONG 6T/3W net −$0.02. Not zero, but the 7/7 all-losers pattern is gone.

---

## Check Areas (10/10 audited)

### 1. Syntax & Import Integrity — **PASS**
- `ast.parse` OK on all 7 modified files (signal_compactor, decider_run, chop_detector, _aggregate_1m, price_collector, rsi_utils, hermes_constants).
- Import graph extracted; every imported local module resolves on disk (cascade_flip_helpers, continuum_context, hermes_file_lock, hermes_log, market_phase_gate, volatility_gate_v2, confluence_scorer, sl_zones, tide_detector, amplitude_cache, signal_lifecycle_filter, speed_tracker, hebbian_engine, btc_crash_filter, checkpoint_utils, correlation_engine, event_log, hermes_ab_utils, hl_copy_db, hype_cache, position_manager, tpsl_utils, rsi_utils, tokens, signal_schema; `signals` resolves as package dir).
- `get_sl_multiplier_v2(atr_pct, signal_type=None)` signature matches call site (see §7).

### 2. Candle Pipeline (950a1e0b, e9a299ca, 8881b9d4, e5f1dd0a) — **PASS**
- `_aggregate_1m.py`: `MIN_BARS_FOR_CLOSED = 3` (L29), `MIN_BARS_FOR_DEVELOPING = 2` (L30); closed-candle path uses **INSERT OR IGNORE** (L148) with explicit FIX comment (L141–146) — aggregator can no longer overwrite API OHLC with flat ticks. Developing path uses REPLACE only when `is_closed != 1` (L201–202) — closed candles protected.
- `price_collector.py`: `TOKENS_PER_RUN = 10` (L212); `_fetch_hl_candles()` exists (L111) with per-TF interval map incl. 15m (L114); seed TF list `['1m','15m','1h','4h','5m']` (L87); seed loop fetches per-TF limits (L247).
- **Live data quality (last 30 min, 17/18 sampled tokens with data):**

| Table | Candles | REAL (H>L) | FLAT | % real | vol>0 | newest age |
|---|---|---|---|---|---|---|
| candles_1m | 242 | 215 | 27 | **88.8%** | 95.9% | 1.8 min |
| candles_5m | 82 | 80 | 2 | **97.6%** | 30.5% | 5.8 min |
| candles_15m | 33 | 32 | 1 | **97.0%** | 39.4% | 5.8 min |

- New candles DO get volume > 0 on 1m (95.9%). 5m/15m volume coverage partial (30–39%) — API-fetched only for rotating TOKENS_PER_RUN=10 subset; aggregator gap-fills write volume=0 by design (RSI unaffected; volume gates only see API candles). Worst per-token: ATOM 2/11 real, TURBO 1/3 (stale 27 min — rotation lag, not corruption).

### 3. RSI Fixes (273a452a, e8757b7e, 3a244058) — **PASS**
- **Inversion fix verified at all 6 compactor delta sites** — every one computes on DESC closes as `closes[i] - closes[i+1]` (i+1 = older): L2453 (LONG-RSI-BLOCK), L3580 (SPIKE-FILTER), L3644 (SHORT-RSI-FLOOR), L3683 (OVERSOLD-SPIKE), L3901 (SPIKE-FILTER LONG), L4323 (PRESERVE-SPIKE). No `i-1` pattern remains in signal_compactor.
- `decider_run.py:4423` (RSI-DRIFT) still uses `i-1` but **reverses the array first** (L4422 `_rsi_closes.reverse()`) — chronological, correct. `rsi_utils.py` reverses (L91) — correct.
- **Live RSI verification (3+ tokens, computed from candles.db):** rsi_utils vs independent Wilder replica — **EXACT match on 10/10** (BTC/SOL/DOGE/LTC/IO/XRP × 1m/5m); direction sanity 10/10 OK (rising→RSI>50, falling→RSI<50). E.g. SOL 5m: 57.20=57.20 rising OK; XRP 5m: 39.81=39.81 falling OK.
- **1m fallback (e8757b7e) live-firing:** `[EXEC-RSI] ME: 5m stale, using 1m fallback RSI=52.1` (03:45), ZEN 65.0 (14:55), ALT 55.9 (17:10×2). Code at decider L1897–1903: 5m → None → 1m fallback → fail-closed for SHORT when both None (L1906–1908).
- **Continuum delivery fallback (3a244058 F3-1) verified:** decider L1282 `_prompt_cont = market.get('btc_continuum') or _ctx_gate_get_btc_continuum()` — fresh fetch when rule gate returned string.
- *Methodology drift note (pre-existing, not a session regression):* rsi_utils (Wilder, limit=20) vs signals/rsi_1m.py (simple avg, 15 candles) vs decider drift-check (SMA over 14 deltas from LIMIT 15) can disagree near thresholds — BTC 1m live: 56.99 vs 46.20 vs 31.20(respective). All non-inverted; flagged in rsi_utils docstring as known.

### 4. Bullish Override Fixes (114c1897, db49a5d7, 2e63218f) — **PASS**
| Site | Location | Condition | Status |
|---|---|---|---|
| `_cont_bullish` | compactor L2661–2662 | linreg in (LEAN_BULL,BULL) + ema300 in (**ABOVE, AT**) | ✅ |
| `_cont_bearish` (Fix 2) | compactor L2653–2655 | phase in (DECLINING,CALM,RECOVERY) + linreg bear + ema300 in (**BELOW, AT**) | ✅ |
| `_lrc_bullish` | compactor L3804–3805 | linreg bull + ema in (**ABOVE, AT**) | ✅ |
| Chop gate structural bull | compactor L1254–1255 | phase CALM + linreg bull + ema in (**ABOVE, AT**); structural bull any phase + ema in (ABOVE, AT) | ✅ |
| BTC-CRASH-OVERRIDE | decider L3384–3385 | CALM + bull + ema in (**ABOVE, AT**); structural bull any phase + (ABOVE, AT) | ✅ |
| Chop bullish phase set (Fix 3) | chop_detector L528 | phase in (RECOVERY, CALM, NEUTRAL, **DECLINING**) + linreg bull + ema ABOVE | ✅ |

**Live proof:** `✅ [CONTINUUM-OVERRIDE] BIGTIME SHORT — BTC continuum=DECLINING linreg=LEAN_BEAR ema300=AT, allowing despite velocity=-0.005` (21:41–21:46, repeatedly for BIGTIME/IMX/LINK) — Fix 2 (`('BELOW','AT')`) firing in production; SHORT bypass no longer dead during transitional bear states.

### 5. Bear Override Fixes (cf97a174, c4097276) — **PASS (with WARN W1/W2)**
- **SHORT-RSI-FLOOR** (compactor L3610–3632): bear override present with exact 4-condition + staleness gate — `phase in (DECLINING,CALM,RECOVERY) AND linreg in (LEAN_BEAR,BEAR) AND ema=='BELOW' AND score<30` + `(now − ts) < 600` (L3624–3630). Log line `[SHORT-RSI-FLOOR-OVERRIDE]` present (L3653).
- **PUMP-CHAIN-SHORT-RSI-MIN** (compactor L2897–2928): identical override condition (L2916–2921), log `[PUMP-CHAIN-SHORT-RSI-OVERRIDE]` (L2925). Post-block log confirmed live: `🚫 [SHORT-RSI-FLOOR] APT: SHORT blocked — RSI 29.4 < 40 (extreme oversold — no bearish override)` (22:00).
- **EXEC-RSI-FLOOR** (decider L1920–1922): ⚠️ c4097276's exec-side bear override was **REMOVED after the audit window** by dbfe2dd7 (22:16, "CEO: T directive") per documented standing decision (CURRENT.md: exec RSI≥floor all paths). HARD FLOOR=25 remains **unconditional** at both detection (L1052–1059) and execution (L1912–1915) — no override path exists there. Verified in git: `git log -L 1916,1918` shows the removal diff explicitly.
- **HARD FLOOR (RSI<25) UNCONDITIONAL — verified:** decider L1913 `SHORT_RSI_HARD_FLOOR > 0 and _exec_rsi < SHORT_RSI_HARD_FLOOR` → block, comment "no bearish override"; detection gate L1052–1059 two-layer fail-closed (live+both-None) — correct.

### 6. LLM Context Gate (45ed8064, 3a244058) — **PASS**
- `_ctx_gate_get_btc_continuum()` exists (decider L920–944); **600s staleness guard** at L936 (`if time.time() - _bc_ts > 600: return None`); returns `{'phase','linreg','ema','score','z','bearish'}` with bearish = phase bear + linreg bear + ema BELOW (L939–940); `timeframe='1m'` filter present (F3-5, L929).
- Prompt includes **Live RSI** (L1292 `_rsi_str`, rendered L1338 `Live RSI: {_rsi_str}`) and **BTC Continuum** (L1283–1291 `_cont_str` w/ `[BEAR STRUCTURE]` tag, rendered L1350).
- GO criteria mentions bear structure (L1358: "SHORT with BTC bear structure (LEAN_BEAR/BEAR + BELOW) AND live RSI 40-60 = valid continuation short").
- DEFAULT (L1377–1379): "If uncertain AND BTC has bear structure AND live RSI >= 40: reply GO (continuation short is valid)" — matches spec.
- F3-2 crash-proof: score formatting guard L1285–1286 (`None → '?'`, no `None:.1f` TypeError).

### 7. Keyword Fix (e3be90aa) — **PASS**
- decider L1640: `get_sl_multiplier_v2(atr_pct, signal_type=_vol_source)` — keyword is `signal_type=`, matching `def get_sl_multiplier_v2(atr_pct, signal_type=None)` in volatility_gate_v2.py L750. No `signal=` mismatch remains (grep clean).

### 8. Live Pipeline Impact — **PASS (hotset currently empty — quiet market, see W6)**
- **Hotset:** empty since ≥22:02 (`No signals after pre-filter`, cycle 13728→13752, all 0 tokens). Root cause visible in logs: market quiet + dbfe2dd7 raised SHORT_RSI_FLOOR to 45 at 22:16 + individual quality gates (see §10). Non-empty earlier today (LTC entered hotset 20:07 conf=88).
- **Open positions:** 1 — `LTC SHORT pump-chain- entry 69.315 open 2026-10-06 20:07:49` (trade_id 15971, actively managed: RR trail SL $69.21→69.26, PHANTOM-DBG confirms SL widened 0.149%→0.468% by ATR fix).
- **Trades closed since 16:00 (PG brain):** 3 —
  - DOGE pump-chain- **SHORT +$0.08** `rr_engine_resistance_break` (open 17:44 close 19:09) ✅ bear-market SHORT win
  - ZRO oversold-bounce+ LONG +$0.23 `profit-monster-trail` (17:27→17:38)
  - IO pump-chain- SHORT −$0.12 `hard_max_loss` (19:25→21:32)
- **Full day (PG):** SHORT 4T: 2×hard_max_loss −$0.37, 1×RR-win +$0.08, 1 open; LONG 6T: 3×hard_max_loss −$0.36, 3×PM-trail +$0.34. hard_max_loss no longer 100% of trades (session brief: 7/7).
- **Errors:** zero `Traceback|ERROR|CRASH` in last 1000 pipeline.log lines.
- **1m RSI fallback firing** (see §3). **Bear structure overrides firing** (see §4).

### 9. Regression Check — **PASS**
- Protected flags intact: `LIVE_TRADING_ENABLED = True` (L33), `CONFLUENCE_REQUIRED = True` (L3067), `PM_TRAIL_ACTIVATE_PCT = 0.004` (L1543, DO-NOT-CHANGE comment preserved), `CUT_LOSER_PNL = -1.00` (L702).
- **All 14 audited commits touched ZERO constants files** (`constants_files=0` × 14). The `cf97a174~1..2e63218f` constants diff exists but comes from OTHER in-window commits (5b626276 tl-bounce bypass add, bd1728f4 MTF-regime-trend- kill, 885021c5 trend_ride filters, 26d3c99b FAMILY_MAP, 61bec3b8 underscore variants, dbfe2dd7 floor 45/continuum 40/HIGH open) — authorized trading-config changes, not part of the audited fixes.
- `SHORT_RSI_HARD_FLOOR = 25` unchanged (L877); `SHORT_RSI_CEILING = 65` unchanged; `PUMP_CHAIN_SHORT_RSI_MIN` 40→45 by dbfe2dd7 (post-window T directive, documented).

### 10. End-to-End Flow Test — **PASS**
Traced 2 SHORT signals that passed with bear override + 3 that were correctly blocked:

**✅ LTC pump-chain- SHORT (EXECUTED, still open):**
1. `20:07:00 [SHORT-NEUTRAL-BYPASS] LTC SHORT — BTC continuum=DECLINING+LEAN_BEAR+BELOW, bearish structure overrides NEUTRAL regime` (bear override enabled passage through NEUTRAL block)
2. `CONFLUENCE-GATE-PASS` (standalone bypass pump-chain-), `BTC-CHOP-OVERRIDE` (BTC-exempt type)
3. `HOTSET-FINAL-ADD LTC:SHORT conf=88 score=99.50` → signal-analyst `PASS score=75`
4. `20:07:41 [DECIDER-LOOP] #1 LTC SHORT conf=112 hotset=YES` → `EXEC @ $69.1205 [pump-chain-] spd=78%`
5. `[VOL-GATE-v2] ATR=0.6534% NORMAL mult=1.0` → `[CTX-GATE] rule-based GO` → `PostgreSQL dup check passed` → `brain.py trade add LTC short --real` → PG open 20:07:49 ✅
Every gate passed/fail-opened with a logged reason; sl_multiplier via `signal_type=` keyword (e3be90aa) evaluated cleanly.

**✅ DOGE pump-chain- SHORT (EXECUTED, WON):** `17:43:52 EXEC: DOGE SHORT @ $0.094619 conf=99% [pump-chain-]` → open 17:44 → close 19:09 **+$0.08** `rr_engine_resistance_break`. RR engine exit working.

**Correctly-blocked cases (penalty engine enforced, not advisory):**
- APT SHORT ×2 (21:59/22:00): `SHORT-RSI-FLOOR blocked RSI 22.1/29.4 < 40` — no bear override because BTC ema=AT ≠ BELOW (see W1).
- KAS SHORT (21:58): passed confluence + chop override, killed by `HALL-SHAME 30d SHORT WR=40% < 55%` — leaderboard gate enforced.
- CRV SHORT (21:58): passed confluence + chop, killed by `RR HARD BLOCK R:R=0.66 < 0.7 → mult=0.00` — **penalty engine decisive, not advisory** (session fix working).
- Earlier cycle (21:55–21:57): KAS/CRV blocked by `SHORT-CONTINUUM score>30 not STRONG_NEG` — pre-dbfed2dd7 threshold; threshold raised to 40 at 22:16.

---

## Commit Summary Table

| # | Commit | Description | Status |
|---|--------|-------------|--------|
| 1 | `45ed8064` | CEO Fix 3: LLM context gate + BTC continuum context | ✅ PASS — function, 600s guard, prompt sections, GO/DEFAULT text all verified |
| 2 | `3a244058` | F3-1/F3-2/F3-5: continuum delivery fallback + score crash-proof + timeframe | ✅ PASS — fallback L1282, score guard L1285, timeframe='1m' L929 |
| 3 | `114c1897` | `_cont_bullish` ema AT fix | ✅ PASS — L2662 `in ('ABOVE','AT')` |
| 4 | `db49a5d7` | F1/F2/F3: chop gate ema AT + crash override ema AT + audit log | ✅ PASS — L1255, L3384–3385, CONTINUUM-BULL audit logs present |
| 5 | `950a1e0b` | CRITICAL: aggregator INSERT OR IGNORE | ✅ PASS — L148 closed path IGNORE; developing guarded L201 |
| 6 | `e9a299ca` | MIN_BARS 1→3 | ✅ PASS — CLOSED=3, DEVELOPING=2; live flat-candle rate down to 11% (1m) |
| 7 | `8881b9d4` | TOKENS_PER_RUN 2→10 + HL fallback function | ✅ PASS — L212, L111; 1m vol>0 at 95.9% |
| 8 | `273a452a` | RSI inversion fix at 3 gate sites | ✅ PASS — all 6 compactor delta sites DESC-correct; live RSI exact-match verified |
| 9 | `e5f1dd0a` | Add 15m to seed TF list | ✅ PASS — L87; 15m real-OHLC 97.0%, no longer 100% zero-vol |
| 10 | `cf97a174` | Bear override SHORT-RSI-FLOOR + PUMP-CHAIN | ⚠️ PASS w/ WARN — override present w/ exact condition, but ema=='BELOW' strict makes it dormant while BTC ema=AT (W1) |
| 11 | `e3be90aa` | get_sl_multiplier_v2 keyword mismatch | ✅ PASS — `signal_type=` matches signature |
| 12 | `c4097276` | EXEC-RSI-FLOOR bear override in decider | ⚠️ SUPERSEDED — removed post-window by dbfe2dd7 (22:16) per standing decision; HARD FLOOR 25 unconditional intact; not a code defect but the audit's live picture differs from this commit |
| 13 | `e8757b7e` | 1m RSI fallback when 5m stale | ✅ PASS — code L1897–1903 + live firing (ME/ZEN/ALT) |
| 14 | `2e63218f` | Fix 2 `_cont_bearish` BELOW,AT + Fix 3 chop bullish DECLINING | ✅ PASS — both verified + live-proven (CONTINUUM-OVERRIDE ema300=AT lines 21:41+) |

---

## Data Quality Metrics

| Metric | Value | Source |
|---|---|---|
| 1m real OHLC (H>L), last 30m | **88.8%** (215/242) | candles.db indexed query |
| 5m real OHLC | **97.6%** (80/82) | same |
| 15m real OHLC | **97.0%** (32/33) | same |
| 1m volume>0 | 95.9% | same |
| 5m/15m volume>0 | 30.5% / 39.4% | same (API-rotation limited; RSI unaffected) |
| Newest 1m candle age | 1.8 min | same |
| RSI accuracy vs independent replica | **10/10 EXACT** (BTC/SOL/DOGE/LTC/IO/XRP × 1m/5m) | live computation |
| RSI direction sanity | 10/10 OK | same |
| Remaining inverted-delta sites | **0** | grep audit, all 3 files |

## Live Pipeline Status (2026-10-06 22:20 UTC)

| Item | Value |
|---|---|
| Hotset | **empty** (0 tokens, quiet market + floor raised to 45 at 22:16) |
| Open positions | 1 — LTC SHORT pump-chain- @ 69.315 (open 20:07:49, actively trailed) |
| Trades since 16:00 | 3 closed: DOGE SHORT +$0.08, ZRO LONG +$0.23, IO SHORT −$0.12 |
| Day SHORT stats | 4T / 1W / net −$0.29 (7/7 HML pattern broken) |
| Day LONG stats | 6T / 3W / net −$0.02 |
| Errors in last 1000 log lines | 0 |
| Bear overrides firing | YES (CONTINUUM-OVERRIDE SHORT ema300=AT 21:41–21:46) |
| Penalty engine | ENFORCED (RR HARD BLOCK mult=0.00; HALL-SHAME block; live evidence) |

---

## Findings / Regressions / New Bugs

### WARN W1 (MEDIUM) — Bear-override ema gap: compactor SHORT gates require strict `ema=='BELOW'` while BTC is live at `ema=AT`
- Sites: compactor L3628 (`_rsf_be == 'BELOW'`) and L2919 (`_pcs_be == 'BELOW'`).
- `_cont_bearish` (Fix 2, 2e63218f) was widened to `('BELOW','AT')` on the exact rationale that AT = transitional bear — but the SHORT-RSI-FLOOR / PUMP-CHAIN overrides did NOT receive the same widening. Same class of bug 114c1897/db49a5d7 fixed for bulls.
- **Live impact:** BTC = DECLINING+LEAN_BEAR+**AT** at 21:55–22:00 → APT SHORT (RSI 29.4, between hard floor 25 and soft floor 40) blocked "no bearish override" even though bear structure present. Momentum SHORTs pass via the widened `_cont_bearish` path, but **oversold-continuation SHORTs remain gated out in the current AT state**.
- Caveat: this may be intentional conservatism (oversold + transitional = riskier than oversold + BELOW). Either way it should be an explicit decision, not drift.

### WARN W2 (MEDIUM) — c4097276 superseded post-window + stale comment
- dbfe2dd7 (22:16, after audit window) removed the exec-time bear override citing standing decision (CURRENT.md: exec RSI≥floor all paths; 7d SHORT meta RSI<40 = 31%WR −$0.77). HARD FLOOR 25 unconditional — intact. The compactor-side overrides (cf97a174) remain live.
- Stale comment: decider L1917 says "exec RSI>=40 all paths" but SHORT_RSI_FLOOR is now **45** — comment not updated with the constant. Doc-drift only.
- Net: audit target #5's exec-side expectation is intentionally not met; the pipeline is stricter than the commit, not looser. Safe direction.

### WARN W3 (MEDIUM, pre-existing debt) — `_ctx_bearish_override` dead code in decider detection gate
- decider L1066–1088 computes `_ctx_bearish_override` from BTC continuum but **never consults it** — L1090–1093 SKIP returns are unconditional on RSI < SHORT_RSI_FLOOR.
- Known since 3a244058 ("Fix 1 infrastructure computed but never wired into floor checks — ships post-freeze"). Still unwired.
- Impact: a SHORT passing compactor via bear override with detection-time RSI below floor will be hard-SKIPped at the decider detection gate (defense-in-depth layer). Live LTC passed because live+detect RSI were above floor at exec time. Either wire it (mirror compactor's exact 4-condition + 600s) or delete the dead block.

### WARN W4 (MEDIUM, pre-existing) — Cross-module RSI methodology drift
- rsi_utils (Wilder, limit=20), signals/rsi_1m.py (simple average, 15 candles), decider drift-check (SMA over LIMIT-15 window), plus compactor inline sites (Wilder over last-14 deltas). All now non-inverted, but they can disagree near thresholds: BTC 1m live ≈ 57 / 46 / 31 respectively.
- rsi_utils docstring documents this as known. Residual risk: a gate using module A passes while module B blocks the same token at nearly the same moment.

### WARN W5 (LOW) — RSI-DRIFT check fragility (decider L4406–4444)
- Uses `LIMIT 15` → 14 deltas → pure SMA seed, no smoothing — very noisy window for a >15pt drift reject.
- `if _al > 0` fail-open: when avg_loss == 0 (pure pump candle window), `_live_rsi` stays None and drift check silently skipped. Pre-existing; not part of audited commits.

### WARN W6 (LOW/INFO) — Hotset empty all evening
- 0 tokens from ≥22:02 (before dbfe2dd7) — market quiet; KAS/CRV/CHIP SHORT candidates died at quality gates (HALL-SHAME, RR HARD BLOCK) rather than RSI logic. With floor 45 + HIGH opens + continuum 40 (T directive), monitor 48h per commit note: SHORT volume, 30-40 continuum band WR, HIGH 40-45 leak.

### WARN W7 (LOW) — signal-analyst metadata oddity
- `20:07:10 [signal-analyst] PASS: LTC SHORT ... rsi=10` while exec-time RSI gates passed — suggests a signal-metadata RSI field mismatch (DRIFT-009 class, 3a244058 partially addressed via _exec_meta fallback at trade INSERT). Cosmetic today; worth verification.
- `conf=211%` (IO SHORT) — confidence >100% from multiplier stacking; cosmetic.

---

## Recommendations

1. **Decide explicitly on W1:** either widen compactor bear overrides (`_rsf_be`/`_pcs_be`) to `('BELOW','AT')` to mirror `_cont_bearish`, or document strict-BELOW as intentional for oversold SHORT gates. Given the T directive just raised floors, observe 48h first; then one-line change if AT-states keep blocking valid bear continuation shorts.
2. **Resolve W3 debt:** wire `_ctx_bearish_override` into the decider detection gate (exact same 4-condition + 600s as compactor) or delete the dead block — dead code that looks like protection is worse than none.
3. **Unify RSI methodology (W4):** migrate signals layer + decider drift-check onto rsi_utils (single source of truth intent already documented).
4. **Fix stale comment** at decider L1917 (`>=40` → `>=45`) when constants change.
5. **Run the mandated 48h monitor** from dbfe2dd7 and re-audit SHORT flow ~2026-10-08 22:00 (continuum 30-40 band WR, HIGH vol leak, hard_max_loss share).
6. **5m/15m volume backfill (W5/§2):** consider backfilling `volume` for existing zero-vol 5m/15m API candles, or increasing rotation coverage — volume-based gates currently see only the rotating subset.

---

*Audit method: read-only inspection + live computation. Every PASS backed by code inspection at exact line numbers, git diff/`git log -L` history, SQLite indexed queries on candles.db, PostgreSQL (brain) trade queries, and pipeline.log evidence. No numbers estimated — all metrics produced by executed code.*
