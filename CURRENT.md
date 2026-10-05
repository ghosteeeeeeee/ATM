# Current State — System Improvement Focus

**Last Updated: 2026-10-05 13:50 UTC**
**Updated by: CEO — freeze-safe verify run (MoE already done 09:55)**

## CEO RUN 13:50 — FREEZE-SAFE VERIFY (0 changes)

**Freeze b960ffe8 until Oct 6 00:38. MoE panel ran 09:55 — not re-run. 0 trading config changes.**

**PG verified this run:** 24h **37T −$0.73 59.5%WR** | 7d **239T +$0.33 54.0%** (LONG +$2.00/181T 56.4%, SHORT −$1.67/58T 48.3%) | 30d **956T −$2.12 51.5%**. Open 2 LONG (ETH bb-bounce-v2 @2717.2 lev5, bb-squeeze+ @4.02 lev3). hard_max_loss 48h **21T −$3.51 avg −4.25%** sole bleed.

**Protected flags verified:** CONFLUENCE_REQUIRED=True, LIVE_TRADING_ENABLED=True, PUMP_CHAIN_V5=False, ATR_TP_MIN=0.013, BTC_CHOP_GATE_THRESHOLD=0.20. decider_run.py:1559 still imports volatility_gate v1 (MoE #2, freeze-blocked).

**Post-freeze queue Oct 6 00:38 (MoE priority):** (1) decider_run v1→v2 + fail-open removal bug_hunter (2) cut-loser-CL-T1 MFE audit bug_hunter (3) STANDALONE_BYPASS expectancy demotion self_learner (4) bb-bounce-v3 NORMAL block + FAMILY_MAP + DRIFT-005 (5) HIGH-regime LONG throttle signal_analyst.

**Sideways:** mtf-regime-trend- SHORT 5T −$0.42/24h pre-fix closes — RSI fix d15b3d88 landed 11:22Z, post-fix n=0. bb-squeeze+ 16T 62.5% −$0.32 R:R tail. Disk 82%. Pipeline healthy, guardian running since Oct 04.

## CEO RUN 22:10 (Oct 4) — BTC CHOP GATE FIX LIVE

**T override executed. Commit 67623191 pushed. Compactor one-shot timer — no restart needed, next fire loads fix.**

**What shipped:**
1. `BTC_CHOP_GATE_3H_PCT = 0.50` added to hermes_constants.py. **`BTC_CHOP_GATE_THRESHOLD` UNCHANGED at 0.20.**
2. Layer A chop gate (signal_compactor.py:1182): flat ONLY if velocity AND |BTC 3h%| both small — OR check via existing `_get_btc_momentum()`.
3. Layer B standalone-bypass (2615): `_vel_ok` gains same 3h OR — **this is the path that blocked ZRO/AVAX/IMX/JUP/WLFI**.
4. Continuum bullish structural override: `LEAN_BULL/BULL + ABOVE` any phase (mirror bear 2026-09-20) — Layer A:1237 + Layer B:2632. DECLINING phase no longer blocks bull structure.

**bug_hunter verification:** initially NOT SAFE — 2 NameErrors in log f-strings (missing `_` prefixes). Layer B one behavioral: NameError on pump path skipped continuum logic → SHORT-deny unreachable. Both fixed. Re-verified: all assertions pass, SHORT-deny confirmed, threshold=0.20, protected flags intact (13 CEO_PROTECTED, LIVE_TRADING=True, CONFLUENCE_REQUIRED=True).

**Live verify at ship:** vel=0.039, 3h=+0.554%, continuum=DECLINING+LEAN_BULL+ABOVE+97.98 → LONG bypass ALLOWED (was blocked). True chop (vel=0.05, 3h=+0.10) still gates. Dump (3h=−0.80) not chop. Mom error → 0.0 → safe fallback velocity-only.

**PG verified this run:** 24h **33T −$0.70 54.5%WR**. Freeze b960ffe8 otherwise stands — no other config changed. Post-freeze queue Oct 6 00:38 unchanged.

**Metrics:** BTC-flat false blocks during |3h|≥0.5% → 0 by Oct 7; hotset approved >0; 24h PnL ≥$0; SHORT 7d ≥$0 by Oct 7.

**Sideways:** bb-bounce-v2-long IS in STANDALONE_BYPASS_SIGNALS (task premise wrong — flow is standalone-bypass path). Layer A structural bull clause ABOVE-only (CALM clause handles AT) — pre-existing asymmetry vs bear, not a regression. Concurrent uncommitted files (price_collector.py, _aggregate_1m.py) are other agents' — NOT committed.

## CEO RUN 21:50 — Freeze-safe verification

**0 trading config changes. Freeze b960ffe8 stands until Oct 6 00:38.** Sunday — MoE skipped.

**PG verified this run:** 24h **33T −$0.70 54.5%WR** | 7d **221T +$0.81 52.9%** (LONG +$2.13/166T 54.8%, SHORT −$1.32/55T 47.3%) | 30d **958T −$0.80 51.8%**. Open 2 (PG+trades.json agree): USELESS bb-squeeze+ HIGH −0.77%, BABY bb-bounce-v2-long+ NORMAL +0.20%.

**bb-bounce-v3 7d regime CONFIRMED:** HIGH 5T 80% +$0.11 KEEP | NORMAL 16T 50% −$0.39 block | FLAT 1T 100% +$0.05. Post-freeze plan stands (NORMAL 0.0 + HIGH 1.0 + FAMILY_MAP underscore).

**Hotset empty:** ~2h census SHORT-CONTINUUM 130 / LONG-NEUTRAL 79 / SHORT-NEUTRAL 76 / HOTSET-FILTER 25 / BTC-CRASH 12 / BTC-CHOP-GATE 10. Chop-gate Option C already queued post-freeze.

**BTC-CRASH LONG blocks = BY DESIGN** (btc_crash_filter.py BTC_LEVEL_TOP_BLOCK_PCT=0.70 — block LONG in top 30% of 60m range). Not a bug.

**Disk 88%:** candles.db-wal 8.4G, PRAGMA checkpoint busy (pipeline writing). Standing rule: no candles vacuum mid-trading. busy_timeout/writer-serialize code fix pending bug_hunter.

**Coin tracker:** 67/112 accumulation, 3 markup; setup mostly NEUTRAL weak; no predictive_score ≥70. Wyckoff/Elliott signal build remains delegated (backlog).

**trades.json healthy** — schema is open/closed keys (not `trades`); open_count=2. Dashboard not dead.

**Sideways:** hermes-wasp timer 35min late (expected 15min, non-trading-path); WAL regrows <1h after checkpoint — writer contention is root of disk pressure.

## CEO DECISIONS 21:15 — BTC Momentum Detection

**DECISION: Option C — BTC multi-window flat check. Queue post-freeze Oct 6 00:38. 0 trading-config changes this run.**

**Verified:** chop threshold live **0.20** (task brief said 0.05 — stale; 0.05 was reverted freeze-violation b5006cd8). velocity=0.017 = **16×5m regression slope_pct (%/5m candle)** from 15m_regime_scanner → SQLite momentum_cache, NOT 30m % as threshold comment claims — **UNIT MISMATCH**. BTC 3h **+0.62%** confirmed (85312→85835); 30m +0.26%. Continuum BTC DECLINING+BULL+ABOVE+99.96 → `_cont_bullish` phase-gated False → velocity fallback → "BTC flat" blocks (ZRO/AVAX/IMX/JUP/WLFI 21:04–21:09). `_get_btc_momentum()` already at signal_compactor.py:898 (tide uses it; chop gate ignores). PG: 24h **32T −$0.70 56.3%** | 7d **221T +$0.79 52.9%** (LONG +$2.11/166T, SHORT −$1.32/55T) | open=0 in PG | 48h hard_max_loss 20T −$3.26.

**Reject A:** TF change ≠ unit fix; lag risk. **Reject B:** live is 0.20 not 0.05; 0.02 still fails 0.017; freeze already reverted this class. **Reject D:** pump not chop — "every pump is a LONG opportunity".

**Post-freeze Oct 6 00:38 — bug_hunter:** (1) hit-rate 0.20 vs unit-corrected first; (2) chop gate Layer A+B not-flat if |vel|>=threshold OR |_get_btc_momentum()|>=**BTC_CHOP_GATE_3H_PCT=0.50** (new constant; DO NOT change BTC_CHOP_GATE_THRESHOLD value); (3) continuum bullish structural override (BULL/LEAN_BULL+ABOVE any phase) mirror 2026-09-20 bearish fix.

**Metrics:** BTC-flat false blocks during |3h|>0.5% → 0 by Oct 7; hotset approved >0; 24h PnL ≥$0. **Sideways:** brief stale on threshold+velocity unit; continuum bullish/bearish asymmetry; chop gate ignores existing 3h helper.

## CEO DECISIONS 21:03 — RSI Consolidation Gap

**Verified:** compactor has 3 inline RSI gates, 0 rsi_utils imports. Floor+sweet-spot=5m, ceiling=1m. Same-pass bonus+block LIVE (HYPER 45.7/75.6, BTC 58.2/79.9). Drought LIVE: 0 approved, 147 sig/2h. 24h DB: 32T -$0.60 56.3%. Open: SEI LONG only.

1. **Compactor consolidation APPROVE — SHIP NOW (bug_hunter).** LONG gates → rsi_utils tf=5m; SHORT ceiling → rsi_utils tf=1m method-only. Constants untouched. Freeze-safe (correctness fix, no VALUE changes).
2. **Full RSI fold-in DEFER** to post-freeze Oct 6 00:38 (signals layer, decider drift, accel_300_v3).
3. **Freeze ruling:** code-path refactor freeze-safe under "crash-bug code fixes allowed." Freeze targets constant VALUES.
4. **Penalty-floor monitor SET** through Oct 6 — hard blocks now truly hard (compactor.py:2023-2024). self_learner owns.

**Post-freeze queue Oct 6 00:38:** full RSI fold + bb-bounce-v3 NORMAL regime-block + FAMILY_MAP underscore + hotset-empty audit + DRIFT-005.

## Current Status

**PIPELINE ACTIVE. Freeze b960ffe8 until Oct 6 00:38 — 0 trading config changes this run.** PG verified 18:40: 24h **29T -$0.87 51.7%** | 7d **220T +$1.43 52.7%** (LONG 165T +$2.75 54.5%, SHORT 55T -$1.32 47.3%) | 30d **951T -$0.92 51.6%**. **5 open:** DOT bb-squeeze+, GMT+IMX pump-chain+, HBAR bb-bounce-v3-long+, ETC bb-bounce-v2+v3 combo. Regime SHORT_BIAS (13L/29S/75N). Disk 81%. Hotset empty (102 sig/h, 0 approved) — recurring, post-freeze audit.

**FREEZE VIOLATIONS:** 2 reverted by CEO 17:49 (b5006cd8 BTC_CHOP_GATE, 18f780ac PUMP_CHAIN_V5). No new violations since — constants/gates clean. ATR_TP_MIN=0.013 remains live.

**b960ffe8 checkpoint:** 1 SHORT since restart 01:50 (RESOLV mtf-regime-trend-, entry_rsi=82.02, closed +1.51%). **Oversold SHORT filter HOLDING** — n=1, RSI well above floor=40. 48h monitor continues to Oct 6 00:38.

**WORST SIGNAL: bb-bounce-v3-long+** 24h 9T -$0.68 33.3%WR. 7d by regime: HIGH 5T 80% +$0.11 (KEEP), NORMAL 15T 46.7% -$0.51 (block candidate). Post-freeze plan stands: NORMAL 0.0x + HIGH 1.0x regime-block + FAMILY_MAP underscore fix. Kill threshold NOT met.

**hard_max_loss:** 24h 11T -$1.74 dominant exit (trail 16T +$1.04). Semantics (price vs leveraged) with bug_hunter — DO NOT change CUT_LOSER_PNL.

## Orchestrator Run 18:45 (freeze-safe)

1. **REGIME_15M.JSON ROOT-CAUSED + ORPHAN REMOVED.** `15m_regime_scanner.py` is a 5m scanner (CANDLE_TF=5m) writing `regime_5m.json` — timer healthy, log fresh 18:30, err.log historical only (FAVORITES bug fixed Oct 2). Production consumers: trade_watchdog.py reads regime_5m.json; signal_schema `_get_regime('15m')` reads candles DB not JSON. **Orphan deleted** + `trade_watchdog_prompt.md` fixed to cat regime_5m.json. Item CLOSED.
2. **No freeze violations** since CEO reverts 17:49 — git diff on constants/gates empty.
3. **PG stats verified** from source of truth (PostgreSQL brain), not memory.
4. **0 trading config changes** — freeze standing.

## MoE Decisions (standing until T overrides)

1. **SHORT model = A:** exec RSI>=40; primary habitat EXTREME; NEUTRAL SHORT blocked.
2. **Implement order:** (1) exec-RSI holes DONE b960ffe8 — monitor 48h; (2) fix 15m/5m scanner (file is 5m data — naming only); (3) RR_ENGINE audit-then-FORCE; (4) SKIP bypass shrink-to-6; (5) SHORT gate = RSI>=40 + EXTREME.
3. **Frequency = B:** fix edge first; raise entry bar only if fee drag still dominates after 48h.
4. **Philosophy = A (amended):** dumps = SHORT only when not oversold. **T must acknowledge before AGENTS.md rewrite.**

## Measurable Goals

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| 24h PnL | -$0.73 | ≥ $0 | next run |
| SHORT 7d PnL | -$1.67 | ≥ $0 | 2026-10-07 |
| Oversold SHORT entries post-fix | 0 new (monitor to Oct 6) | 0 oversold | Oct 6 00:38 |
| 7d PnL | +$0.33 | +$3.00 | 2026-10-06 |
| 30d PnL | -$2.12 | ≥ $0 | 2026-10-11 |
| cut-loser-CL-T1 7d bleed | queued post-freeze | reduced ≥50% | 2026-10-11 |
| decider_run v1→v2 | queued post-freeze | live + v2 blocks execute | post-freeze Oct 6 |
| bb-bounce-v3 regime-block | planned, freeze-blocked | NORMAL 0.0 + HIGH 1.0 | post-freeze Oct 6 |
| mtf-regime-trend- post-fix n | 0 (fix 11:22Z) | ≥10 trades evaluated | 2026-10-07 |
| doji-bottom-long | 9T/7d | 20T | 2026-10-11 |
| ema_reclaim_long | 0 EVER | >0 in shadow | 2026-10-11 |

## Standing Decisions (do not re-litigate)

- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL:** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked.
- **0 config changes when b960ffe8 48h monitor active** (until Oct 6 00:38).
- **ATR_TP_MIN=0.013** — brain_auditor approved, DO NOT REVERT.
- **EXTREME pump-chain- SHORT 0.0→1.0** (brain_auditor 06:39) — DO NOT revert.
- **RR_ENGINE_SHADOW=True** until shadow audit numbers exist.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics with bug_hunter.
- **BTC_CHOP_GATE_THRESHOLD=0.20** — reverted from freeze-violating 0.05.
- **PUMP_CHAIN_V5_ENABLED=False** — standing disable; do not re-enable.
- **hermes_constants.py:** do not change VALUES without CEO/T. Crash-bug code fixes allowed.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled Sep 12 per T.
- **Blacklist testing COMPLETE** — 77 tokens, 0 KEEP. Stop rotating.
- **PM_TRAIL / ATR_SL protected.**
- **ACCEL_300_V3_LONG_ENABLED=False** — do not re-enable without NEUTRAL data.
- **V5 LONG disabled** — do not re-enable.
- **mtf-regime-trend+ disabled** — killed Oct 2.
- **Disk prune** when >88%. Coin_tracker/candles NEVER vacuum during trading.
- **regime_15m.json ORPHAN** — deleted 18:45; scanner writes regime_5m.json; prompt fixed.
- **Agents commit own files only** — concurrent git add -A theft noted (cf866402).

## Monitor List (next 48h)

1. **ZERO oversold SHORT entries** 48h post b960ffe8 — Status: 1 SHORT (RSI 82, not oversold) — filter holding. (self_learner)
2. **SHORT 7d PnL ≥ $0 by 2026-10-07.**
3. **24h PnL back ≥ $0** — -$0.87 this run.
4. **bb-bounce-v3-long+** — post-freeze NORMAL regime-block + DRIFT-005 path audit.
5. ATR_TP_MIN 0.013 impact — need hard_tp/trailing exits to judge.
6. volume-breakout-long+ post-boost — 10+ trades by Oct 11.
7. doji-bottom-long → 20T for conf boost.
8. hard_max_loss semantics — bug_hunter owns; 24h 11T -$1.74.
9. mover+ entry quality (signal_analyst).
10. ema_reclaim_long 0 signals EVER — OVERDUE (signal_analyst).
11. Disk 81% — prune at 88%.
12. **Hotset empty** — 102 sig/h generated, 0 approved. Capital-efficiency bug. Post-freeze audit signal_compactor filters vs SHORT_BIAS.
13. DRIFT-002 — exec-time RSI timeframe (bug_hunter).
14. HL API key reminder STALE — T: verify/correct.
15. Coin tracker Wyckoff/Elliott/Volume unbuilt (signal_analyst).
16. pnl_usdt vs fees accounting (bug_hunter, non-trading-path).
17. OpenMemory service inactive — HTTP API works.
18. 30d -$0.92 — re-check Oct 5.
19. BTC_CHOP_GATE hit-rate 0.20 vs 0.05 on _btc_30m — bug_hunter post-freeze.
20. exit_optimizer_shadow no timer — T/CEO decision pending.
21. ~~regime_15m.json stale~~ **CLOSED 18:45** — orphan removed, scanner healthy.

## Backlog / Delegated (not orchestrator's call)

- **DELEGATE bug_hunter:** BTC_CHOP_GATE hit-rate analysis post-freeze.
- **DELEGATE bug_hunter:** RR_ENGINE shadow-block 7d → FORCE with numbers.
- **DELEGATE bug_hunter:** hard_max_loss semantics fix path (needs numbers).
- **DELEGATE bug_hunter:** fees JSON vs pnl_usdt accounting gap.
- **DELEGATE bug_hunter:** DRIFT-005 path audit (enforce existing RSI_MAX=55).
- **DELEGATE self_learner:** 48h zero-oversold SHORT verification (n=1 RSI 82 so far).
- **DELEGATE signal_analyst:** scanner retune; EXTREME+RSI>=40 SHORT habitat; ema_reclaim coverage; doji execution path; mover+ entry quality; coin_tracker Wyckoff.
- **DELEGATE signal_reporter plan (post-freeze Oct 6):** bb-bounce-v3-long+ NORMAL 0.0x + HIGH 1.0x + FAMILY_MAP underscore fix.
- **T ack required:** AGENTS.md philosophy amendment.
- **T decision pending:** exit_optimizer_shadow timer.
- **Post-freeze audit:** hotset empty — signal_compactor filters vs SHORT_BIAS regime.
- **bollinger_squeeze SHORT side** — research PASS but OFF until SHORT R:R fixed.
- **bugs.json OPEN** — coin_tracker/backfill — not trading-path.

## Orchestrator / CEO Report (2026-10-04 18:45 UTC)

- **0 trading config changes.** Freeze b960ffe8 stands until Oct 6 00:38. No new violations since CEO reverts 17:49.
- **PG verified:** 24h 29T -$0.87 51.7% | 7d 220T +$1.43 52.7% | 30d 951T -$0.92 51.6%. 5 open all LONG. hard_max_loss 11T -$1.74/24h dominant.
- **b960ffe8:** 1 SHORT (RESOLV RSI 82.02, closed +1.51%) — oversold filter holding. Monitor continues.
- **REGIME_15M CLOSED:** scanner is 5m writer to regime_5m.json (healthy); orphan JSON deleted; watchdog prompt fixed. Item 21 resolved.
- **bb-bounce-v3 post-freeze plan confirmed** with fresh regime split: NORMAL 15T 46.7% -$0.51 block / HIGH 5T 80% +$0.11 keep.
- **Hotset empty** flagged for post-freeze audit (102 sig/h, 0 approved).
- Protected flags untouched. Pipeline healthy. Session lock absent.

