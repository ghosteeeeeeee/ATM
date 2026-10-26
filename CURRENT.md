# Current State — brain_auditor #158 2026-10-26 09:55 UTC
**Last Updated: 2026-10-26 09:55 UTC**
**Updated by: brain_auditor #158. Prior: #157 07:55 / #156 07:05 / #155 05:41 (preserved in git history).**

## HEADLINE — TRAIL-STATE ORPHANS WERE A GHOST VETO ON 3 EXIT ENGINES; GC SHIPPED

**1) `_gc_trail_state()` in `scripts/profit_monster.py` (commit 0bd9109e).** Trail-state keys
(`data/profit_monster_trail_state.json`, trade_id → peak/token) were deleted ONLY on a PM trail
exit — every other exit orphans the key forever. **29 orphans had accumulated.** FOUR consumers
read membership as live PM ownership: `position_manager:3920` (UGB-PT enforce skips),
`cut_loser:181` (token-level — ONE orphan blocks cut_loser for the whole token),
`hl_fill_monitor:498` (same helper), `sniper_exit:707/:908` (skip + tier1 exclusion = winner
never booked). **Measured harm:** 6 cut_loser skips 10-15..10-23 (BABY -4.02% / SYRUP -3.09% /
CC -3.95% leveraged = **-$0.53 exact in PG**) each rode to stop; **IO #16407** (02:19 rogue
bypass window, armed 02:27, reverted 02:40 = orphan) skipped **8 UGB-PT would-fire cycles
02:48-03:04** while live ran +0.44→-0.23 → closed atr_sl_hit **-0.45% price-move (-1.25% stored
lev-3) instead of the +0.44% floor**. Fix = set-difference vs managed-open set, SUCCESS path
only (DB-error path returns before GC), WARN-wrapped. `--selfcheck` 5/5 · live GC 08:45:55
dropped 29, **0 Tracebacks in 65min**. Docstring numbers corrected pre-commit (draft claimed
4 fires/-1.18%/+0.47%). **Canary: cut_loser 'Profit monster closing' skips must stay 0 — any
future skip needs a matching PM [TRAIL] exit within 60s or it's a new orphan class (baseline 6/8d).**
Residual MED-LOW: a `current_price<=0` blip drops one armed key for ≤1 60s tick (re-arms at
≥0.40%, peak resets → floor on re-arm peak); non-atomic write = same class as pre-existing
`_save_trail_state` (all readers tolerate JSONDecodeError → {}).

## CREATIVE — WATCHDOG BEST CELLS REJECTED-WITH-DATA (both fail OOS same-sign at 30d)
- SHORT `rsi_14<40`: 7d 11T 9W `+0.53` (p=0.033) → 14d 20T `+0.47` → **30d 33T `-0.30` FLIP**
- LONG `rsi_14>=65`: 7d 16T `+0.54` → 14d 48T `+0.01` → **30d 127T `0.00` WASH**
Never gate on a 7d cell (#85 pattern). Logged creative #2 as rejected.

## MANDATE — CHOP vs TREND (fresh PG, 14d)
- TRAIL/TP **84T 91.7% `+$5.14`** vs CHOP/STOP 166T 3.6% `-$12.52`
  (hard_max_loss 62T 0.0% `-$6.24` · atr_sl_hit 79T 1.3% `-$5.50` · trail_arm_timeout 25T `-$0.78`)
- armed 162T 70.4% `+$8.34` vs unarmed 161T 5.6% `-$12.84` → **entry quality owns the bleed**
- chop-bleed = baseline, no breach

## LOSING AUTOPSY — WRONG-SIDE REFUTED 82nd CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck PASS`, vacuity 181/189):
**48h n=12 = 5 never-adverse / 6 recovered / 1 NEVER** — ICP #16409 (waiver band).
14d 189 losers = 37 / 123 / **29 NEVER = 17.5%** structural (re-enter-on-recovery rejected
p=0.158, not reopened). Refs #61 p=0.116, #84 t=-0.04.

## DEEP-DIVE — 0 new shippable sub-50% n>=15 targets
14d: bb-bounce-v2-long+ 38T 36.8% `-$1.12` (kill bar FAIL #138; TAT-C live) · doji 16T killed ·
ai-trader+ disabled · pump-chain- 36T 22.2% = CONF_FLOOR+PROMOTE · pump-chain+ 44T 31.8%
(conf<30 `-$1.24` vs conf>=30 `+$1.12`; 30d `+$1.88` NO-KILL) · ai-trader-pending CEO.

## CHOP-COVERAGE LEDGER (unchanged this run)
OWNED 57.0% of 14d never-armed bleed (`-$13.22`/147T denominator; killed 21% + ai-trader 8.2%
+ CONF_FLOOR 13.7% + MFE-CUT 14.1%); residual 69T `-$5.68` no cell at n>=20 → **closes only
when CONF_FLOOR ships.**

## SHADOW (2/6 answerable)
contrarian 819 rows fresh 04:26 + #157 control arm (pump-chain- orig 36.6% vs flip 64.6%
p<0.0001 both halves → **PROMOTE Oct 27 stands**; btc-pump-rider+ do-NOT-flip) · shadow_trader
23,693 (CONFLUENCE-EXPIRY gates justified; exit A/B pm_trail `+$3,381` vs hard_max `-$4,969`) ·
floor_admit 2,021 + wyckoff 324 fresh but **PENDING join** · oscillator FROZEN (24,598) ·
rr ORPHANED. session_brain WORKING (4/4 unique hits).

## LAST-RUN VERIFY — #157 ALL PASS
daily_git_commit `--selfcheck` **9/9** (incl. staged-regression case) ·
contrarian_both_sides `--selfcheck` 5/5 · #152 revert holding (constants git diff **0 lines**,
PROFIT_MONSTER_BYPASS pump-chain intact) · kill flags correct (VOLUME_BUILDUP_PLUS/AI_TRADER/
DOJI False) · size-reduce **ABSENT = 1.0x** · session lock absent · session_brain dup drift
RESOLVED (4/4 unique).

Carried LOW: weekly `Self-healing test: FAIL - ModuleNotFoundError dispatcher.dispatcher`
03:00 Sun (Oct 11/18/25) — #137 health_monitor SKIP branch unverified → Nov 1 ·
`trades.regime` zero-variance · `signal_created_at` dead · `data_integrity_guard.py` never invoked.

24h 20T 60% `-$0.08` | 7d 129T 44.2% `-$0.68` | 14d 326T 38.0% `-$4.47` | 30d ~44% ~`-$2.2`.

## READINESS — 1 open, bracketed
- **BTC #16411 LONG continuum-osc+ @80065** +0.21% 3.9h, meta_rsi 46.6 = mid-band cell,
  SL 79576.2 / TP 81274.6, conf 49.5 → **HOLD on precommitted levels**; mid-band compound
  block MEASURED-REFUTED (#139, re-measure Oct 27 — advisory only). 15m LONG_BIAS +
  continuum ABOVE + trend UP support it; 4h SHORT_BIAS is the counter.

**Rules:** mid-band = no NEW entries either side until conditions · NO NEW LONG exposure
without sustained 1m EMA300 reclaim WITH volume (LOW volume = retest, not reclaim) · SHORTs
at rsi_exec >=45 (waiver lapses **2026-10-27T00:00Z**), never knife <35 · trail-family first ·
size 1.0x (file absent). Regime sources disagree — cite the source: scanners btc_15m LONG_BIAS
vs btc_4h SHORT_BIAS, volatility LOW, CALM, volume LOW.

## QUEUE
**2026-10-27T00:00Z waiver LAPSE** (verify zero allow-lines + `[UNCLOG-EXPIRED]`) ·
**2026-10-27T17:12Z pump-chain- PROMOTE** (control arm attached) · Oct 27 mid-band re-measure
(#139) + re-check today's two rejected cells with fresh data · **Oct 30 scoped momentum
time-stop BLIND run** (bars locked) · Oct 31 short-supply re-measure · **Nov 1 coin_regime +
self-healing SKIP verify** · Nov 8 gate scoreboard · Nov 15 floor_admit/wyckoff joins.
**CEO: fkB FAIL 29.1% ruling → CONF_FLOOR | D=0.20 GO | pump-chain+ kill close-out | identify
the 02:19:30 constants writer (its IO orphan window is now costed at -0.45% + 8 skipped
UGB-PT cycles) | LOSERS set EMPTY (not a live safety layer) | escalation #17 (61st) exit-ladder
candle OOS — still blocks the round-trip recovery path.**
