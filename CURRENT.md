# Current State — brain_auditor #193 2026-10-28 08:45 UTC
**Last Updated: 2026-10-28 08:45 UTC**
**Updated by: brain_auditor #193. Prior: #192 05:00 (preserved in git history).**

## HEADLINE — MFE-CUT re-measure hit the UNITS LANDMINE and was corrected before shipping
0 trading-constant changes (`constants_change_review_queue` active per T 2026-10-23 — propose →
CEO auto-approve, auditor-direct is not the channel; hermes_constants.py EMPTY git diff; session
lock absent; size-reduce file absent = 1.0x). 2 non-constant changes (mfe backfill, checkpoint
disposition), 0 ships, 0 trade actions.

### 1. MFE-CUT trades-level counterfactual — RAW vs CORRECTED
Log-derived, decision-time fire condition (mfe-so-far <0.20% at age >=45m — **not** the invalidated
selection-on-FINAL-MFE form), 34 distinct fires / 33 closed, 2026-10-19..10-28:
- **RAW (wrong):** cut -7.97pp vs actual -41.95pp → delta **-33.98pp, t=-3.156, p=0.0035**, better
  24/33. Ship-grade looking.
- **CORRECTED:** `compute_live_pnl` (pnl_utils.py:46-67) is **UNLEVERED raw price return**; PG
  `pnl_pct` is **LEVERAGED**. Recompute both on unlevered price-move and on `pnl_usdt`:
  cut -7.97pp vs actual -10.04pp → delta **-2.07pp, mean -0.063pp, t p=0.3503, wilcoxon p=0.3669,
  better 20/33, USD delta -$0.23 over 33 trades.** → **NOISE.**
- Consequence: standing 30d candle-OOS verdict **FLIP PATH BLOCKED** (517 fires / 145 false-kills /
  ~$9.90 cost per 30d) and the **2026-11-10 default KILL** both STAND. This is the same landmine as
  run #119 (`+$145pp` → `+$0.19`) and `analysis/tat_variant_c_candle_oos_2026-10-24.py`.
- **Family split (pre-registered, all n<=8):** cut-better `bb-bounce-v2-long+` 6/8 -1.43pp ·
  `ai-trader-pending` 4/4 -1.12pp · `continuum-trend+` 4/5 -0.91pp — cut-worse `volume-buildup-`
  0/3 +0.74pp · `continuum-osc+` +0.57 · `continuum+` +0.58 · `r2v2-long4` +0.66. Matches the
  redesign `position_manager.py:3855` already demands ("family-scoped timeouts, not a universal
  cut"). Bar for any flip: **family n>=20 AND net USD >= +$2.00/14d.**

### 2. LAST-RUN VERIFY #192 — ALL PASS
- BTC tape-state stamp: **11/11 opens since 02:06Z carry `btc_ema300_*`** (was 5/5), 0 missing.
- CHASE_MOVE_SHADOW: 5 log lines, **1 real fire** (KAS 03:03:21 move=0.673%, counterfactual
  +$0.12, n=1). Flip review still 2026-11-10. CHASE_RATIO still False — no regression.
- **Coupled-SL trial hierarchy inversion CONFIRMED live:** post (since 10-27 15:00) 14T -0.33,
  `hard_max_loss` **0** (was 14 pre), `atr_sl_hit` **28.6%** of exits (was 9.8%). n=14 <15 → early,
  rolling-7d threshold (< -2.50) NOT met (7d now -0.77). Proposal A/B still lodged, due 11-03.
- auto_1hr bb-squeeze+ weight 0.8→0.9 (04:30Z, outside this agent): **0 closes since** → check next run.
- Checkpoint `btc-16450-8h-stale` → **DISPOSITIONED done** (BTC #16450 self-closed 05:55:24Z
  UNIVERSAL_MAX_HOLD -0.41%, condition moot before the 06:39Z grace).

### 3. MANDATED CHECKS
- **Losing autopsy (adverse-first):** 48h n=22 = **3 never-adverse / 16 recovered / 3 NEVER** →
  **WRONG-SIDE REFUTED 118th run** (#61 p=0.116, #84 t=-0.04). NEVER = PURR #16452 (FRESH 10-28
  02:06, mfe 0.048) + AERO #16432 + CC #16423 (both waiver-era 10-26, class closed 10-27 00:00Z).
  n=1 fresh NEVER → noted, not reopened.
- **Chop-bleed official KPI:** 7d **88.1%** dollar (4.74/5.38) · 14d 85.0% · 30d 81.3% → under the
  92% escalation gate, far from the <=70% exit-ownership trigger. **Tripwires: arm-rate NOT tripped
  (LONG 56.0% / SHORT 63.6%, needs LONG<50) · route-reopen NOT tripped (needs <70% x2).**
- **Deep-dive: 0 NEW sub-50% n>=15 targets.** Every candidate owned: bbbv2 (vol-gate NORMAL 0.0 —
  **verified live**: commit 5395c3a8 2026-10-26 21:45Z, **0 NORMAL opens since**, last 3 all
  pre-commit) · ai-trader+ / doji-bottom (disabled) · pump-chain- (CONTRARIAN_LIVE flip 10-27) ·
  pc+ NO-KILL (30d +1.77) · ai-trader-manual/pending + hl_copy (CEO/copy-trader domain).
- **Shadow 4/6 used:** contrarian join 10-27T18:31Z pc- flip **64.5% n=350** (LIVE, 0 real fade
  closes yet) / rider 26.0% do-NOT-flip · shadow_trader 31,157 signals, exit A/B **pm_trail
  +4,441** vs hard_max **-6,280** (0% WR) → trail-or-nothing again · floor p=0.138 COLLECT ·
  oscillator fossil / wyckoff 11-15 / rr orphaned.
- **Verification:** constants EMPTY diff · session lock absent · size-reduce absent=1.0x ·
  Tracebacks 5 total newest 2026-10-11 (0 new) · signal_compactor py_compile PASS (its .err.log
  IndentationError is mtime 10-24 historical) · timers live (pipeline/watchdog/shadow/checkpoint).

### 4. DATA REPAIR
3 rows closed with `mfe_pct NULL` inside 7d (BABY #16458, NEAR #16454 + 1) → backfilled
(`cell_stats.backfill_mfe_mae(days=2)`). These rows sit in the chop-bleed **denominator** but not
the numerator, so NULLs drag the reported share DOWN — pre-backfill NULL-inclusive read **93.9%**
vs official **88.1%** = 5.8pt swing on the same window. Creative improvement #3 pins the NULL count
beside the KPI so this never looks like a math bug again (#184's false alarm).

## DRIFT / SIDE-FINDS
- (LOW) AGENTS.md says the contrarian join runs every 15 min — systemd shows **HOURLY** at :00.
- (LOW) `vacation_mode.json` still true (22nd+ run) — review-queue honored, 0 auditor-direct changes.
- (INFO) `hl-copy.err.log` 28.4MB / `signal-compactor.err.log` 5.8MB unrotated — policy check later.

## PG FRESH (08:43 UTC)
24h **19T 52.6% '-0.44' RED** · 7d 137T 51.8% '-0.77' · 14d 289T 43.6% '-3.47' · 30d 739T '-3.87'
· armed 7d **79T 86.1% '+4.20'** vs unarmed **56T 5.4% '-4.66'** (LONG 84.3/+2.44 vs 5.0/-3.18;
SHORT 89.3/+1.76 vs 6.3/-1.48) · trail14 pm_trail **83T 92.5% '+4.63'** vs hard_max_loss
**34T 0% '-4.15'** / atr_sl_hit 65T 5% '-5.04'.

## READINESS — 2 open, HOLD both
- **ICP #16460 LONG bb-squeeze+** @2.5994 lev5, SL 2.5604 / TP 2.6408, RSI 68.42 (under the
  LONG_RSI_CEILING 75 — legal), age 0.2h, -0.26%.
- **FOGO #16459 SHORT volume-buildup-** @0.00323 lev3, SL 0.003311 / TP 0.003165, RSI 60.0,
  age 0.9h, +0.03%. Against a both-TF LONG_BIAS, but volume-buildup- is the healthiest short family
  (14d 39T 64.1% '+0.14') → HOLD, no force-unload. 0 watchdog steers.
- Regime: 15m+4h **LONG_BIAS** · continuum ABOVE · vol HIGH · zscore STRONG_POS · wyckoff MARKUP ·
  trend_quality STRONG_UP · **acceleration NEGATIVE · market_phase DECLINING** →
  prefer LONGs on pullback-to-structure **with volume**, do not chase into negative acceleration,
  no fresh entries until sources agree. Trail-family first, size **1.0x**.

## QUEUE
**Next run:** bb-squeeze+ weight-0.9 effect (0 closes so far) · coupled-SL post cohort toward n>=15
**2026-10-30** scoped momentum time-stop BLIND run (do not peek) · **2026-11-03** coupled-SL
disposition (Proposal A/B) + shadow_disposition batch + Z-FLIP conversion + contrarian KPI ·
**2026-11-04+** coin_regime · **2026-11-10** CHASE-MOVE flip · **MFE-CUT disposition → default KILL
(units guard FIRST)** · **2026-11-15** floor_admit/wyckoff · **CEO** CONF_FLOOR fk pin ·
tf-authority · bb-bounce keep-vs-disable · TAT flip · MFE-CUT enforcement.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json,
brain/changes_log.json, data/checkpoint_registry.json, CURRENT.md.

### 5. BUG_HUNTER (independent) — PASS + one MED side-find it surfaced
Every digit of section 1 reproduced from raw logs+PG (raw -33.9822pp p=0.0035; corrected
unlevered -2.0737pp / t p=0.3503 / wilcoxon p=0.3669 / USD -$0.2313). Independently confirmed:
`compute_live_pnl` unlevered · `trades.pnl_pct` leveraged (32/34 exact) · `pnl_usdt` unit-consistent
34/34 · fire condition is **decision-time** (position_manager.py:3874-3885, running MFE-so-far at
age>=45) not final-MFE.
- **Disclosure 1:** my n=33 silently excluded trade 16259 (WLD) — older log format lacks `live=`.
  With it: unlevered -2.68pp, t p=0.2427, USD -$0.36. **Conclusion unchanged.**
- **Disclosure 2 — MED SIDE-FIND: `trades.pnl_pct` has TWO unit conventions.** 271/289 (93.8%) of
  14d rows = `price_move x leverage` (documented); **17/289 (5.9%) = `price_move` ONLY**
  (avg |pnl_pct/pm| = 0.999). Mix: hard_sl 11 / trail_sl 3 / HL_CLOSED 2 / trail_arm_timeout 1,
  across 9 signals and 10 days. Candidate writers verified present — `position_manager.py:2725`
  persists the UNLEVERED `compute_live_pnl` value on open rows; `brain.py:1018/1032/1045` divides
  by `calc_notional` which is `hl_notional_usdt` when provided (comment "~$7") rather than
  `amount_usdt*lev`. **Exact per-row attribution NOT established and NOT claimed.**
- **Impact:** any SUM/AVG of `pnl_pct` mixes units and is biased low on the deviant rows. WR-by-sign
  and `pnl_usdt` are unaffected (verified consistent). **Use `pnl_usdt` in all aggregates.**
- **Not changed this run** — normalizing the writer changes stored-analytics semantics (and
  `hype_pnl_pct`, which other code reads) → T/CEO visibility. Queued: pin one convention at the
  write path + backfill the 17 rows.
