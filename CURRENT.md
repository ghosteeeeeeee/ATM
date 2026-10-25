# Current State — brain_auditor #135 2026-10-25 ~08:51 UTC
**Last Updated: 2026-10-25 08:51 UTC**
**Updated by: brain_auditor #135. Prior: #134 06:55 + daily_orchestrator 05:10 (both preserved in git history).**

## HEADLINE #135 — SPIDER TRAIL-TIER UNIT BUG (SHIPPED) + ESCALATION #17 LEG 2 MEASURED
`profit_monster.py:517` spider override wrote `PM_TRAIL_TIERS` thresholds as **decimals** (`0.015`/`0.030`)
while `PM_TRAIL_ACTIVATE_PCT`/`PM_TRAIL_DISTANCE_PCT` in the same block were converted `*100` and `peak_pnl`
is **percent** (`pnl_utils.compute_live_pnl` returns 1.5 for 1.5%). `peak >= 0.015` matched **every** activated
peak → the third tier always won → distance **0.50%** → floor `peak - 0.50` sat **BELOW ENTRY** on
**83 of 239** logged `[TRAIL] activated` lines (NEO 10-22 `pnl=0.30 floor=-0.20` · BTC 10-19 `0.37/-0.13` ·
YGG 10-11 `0.32/-0.18`). Inline comments and `plans/spider-profit.md` both specify **0.10%** in the scalp zone.

**FIX:** thresholds → `[(0.0,0.1),(1.5,0.3),(3.0,0.5)]` + `assert min(t[0] for t in PM_TRAIL_TIERS[1:]) > 1.0`
(trips on the old values). Verified: `py_compile` PASS · `_trail_distance_for_peak` repro floor **`+0.20`** at
peak 0.30 (was `-0.20`) · **`hermes_constants.py` git diff EMPTY** · **`CEO_PROTECTED_FLAGS` 13/13**
(`PM_TRAIL_ACTIVATE_PCT`/`PM_TRAIL_DISTANCE_PCT` untouched) · profit-monster is a **oneshot systemd timer**
(fresh process/min) so the module-global override cannot leak across fires · **revert = one line.**
Sweep corroboration: D=0.10 nets `+3.972`/30d vs D=0.50 `+2.121` (fk_zeroed 1.8% vs 3.6%).

**⚠️ `mfe_pct` is SAMPLED, not candle-extreme.** Validated this run: `mfe_from_price` == `mfe_pct` to 3 dp on
9/9 probes, but the 1m candle max favorable is **2-3x higher** (WLFI 0.156 vs 0.454, YGG 0.241 vs 0.663).
So DB `mfe_pct`/`mfe_price` describe what our sampler saw; a resting order sees the candle extreme. Any
arm-based counterfactual must state which model it uses — and be tested under both (leg 2 was: see below).

## ESCALATION #17 — LEG 1 AND LEG 2 MEASURED, ONE PIECE LEFT
**Leg 2 (`brain/analysis/trail_distance_oos_2026-10-25.py`, selfcheck + probe selfcheck PASS):** flat post-arm
leash D swept 0.05→1.60% on the 30d armed non-EXTREME / no-`volume-` cohort (n=216), `pnl_usdt` both sides,
1m **close-through** exit, fee-neutral delta (same round trip both arms). House bars locked pre-run:
n≥20 ∧ net>0 ∧ both 15d halves>0 ∧ p<0.05 ∧ fk_zeroed<20%.

| D | 30d NET | 30d halves | 30d fk_zeroed | t | 14d NET | 7d NET |
|---|---|---|---|---|---|---|
| **0.20%** | **+3.925** ✓ | **+1.759 / +2.166** ✓ | **1.8%** ✓ | **3.122** ✓ | **+1.820** ✓ | +0.137 ✗ halves |
| 0.10% | +3.972 ✓ | +1.961 / +2.012 ✓ | 1.8% ✓ | 2.879 ✓ | +1.803 (p≈0.055 ✗) | — |
| 0.50% | +2.133 ✓ | +0.555 / +1.578 ✓ | 5.3% ✓ | 2.058 ✓ | +1.488 ✗ halves | — |
| 1.20% | +0.442 ✗ p | +0.041 / +0.401 ✓ | 1.8% ✓ | 1.257 ✗ | +0.347 ✗ | — |

Top-3-contributor sensitivity at 0.20: EX-top3 **`+3.726`** PASS (top3 = LTC pump-chain- `-0.513`,
SEI r2-trend-long4 `+0.407`, BTC continuum-osc+ `+0.305`). By-signal broadest contributor only `+0.605`.
**Sampling robustness:** arm-on-1m-CLOSE → `+3.920` (30d) / `+2.246` (14d), both pass = **not a wick artifact.**

**HEAD-TO-HEAD vs pending BE-at-arm (same 216 armed trades, separate code path):**
trail-0.20 **`+$3.925`** vs BE-at-arm **`+$2.140`** (independently reproduces #134's published figure),
per-trade wins **131 vs 61**, fk_zeroed **1.8% vs 9.4%**. BE only pays on a full round-trip to entry; the
trail floor binds first and still pays `+0.20%` instead of `0%`. → **CEO GO ask UPGRADED to the trail floor**
(same v6 exit-stack path per the Oct-17 verdict).

**DECOMPOSITION — COVERAGE, not LEASH:**

| cohort (30d scoped, D=0.20) | n | net | reading |
|---|---|---|---|
| PM_EXIT (profit-monster-trail) | 131 | **+0.271** | **PM tiers already optimal — NO change to any PM constant** (0.20 base confirmed, CEO-protected stays) |
| BYPASS × non-PM exit | 41 | **+2.368** | signals exempt from PM by design have no post-arm floor at all |
| PM-eligible × non-PM exit | 12-15 | **+1.281** | **13 of 15 have ZERO `[TRAIL] activated` line inside the trade's own window** (2 hit) |

Wick-sampling does **not** explain the misses (98% of armed trades also close-cross +0.40).
→ **PRE-REGISTERED: PM activation-coverage KPI** — open PM-eligible trades where 1m-close MFE ≥ 0.40% but no
activation line exists in-window; evaluate at n≥20. If it holds, the fix is poll cadence or a resting trail
order — **not** a trail parameter.

**Escalation #17 remaining piece:** bypass-engine candle OOS (the 41-trade, `+$2.368`/30d cohort) — largest
single slice of the giveback still unmeasured. **Escalation #17 count: 36th.**

## RE-ENTER-ON-RECOVERY — MEASURED, CLOSED (pre-reg #72, Oct-25 batch)
`brain/analysis/reenter_recovery_cf_2026-10-25.py` (selfcheck PASS, 15 cases). Limit re-entry at original
entry after a 30d loser, 60m trigger + 60m walk, SL-wins-ties, **net-of-fee bars**, candle-containing-close
skipped (avoids the #85 open-anchor vacuity), RAW-bracket scope required alongside ALL.
- **fill rate 31.5%** — the `~71%` census premise does NOT reproduce (it was a ±0.2% band touch, not a fill)
- ALL n=110 net-after-fees `+1.686` but **p=0.158 FAIL**; RAW n=58 **newer-half `-0.041` FAIL**, p=0.52
→ **VERDICT REJECTED-WITH-DATA.** Pre-registration closed; do not re-propose without a redesigned trigger.

## WATCHDOG TRIAGE (08:14 cycle)
Regime **DISAGREED** (15m LONG_BIAS / 4h SHORT_BIAS / continuum NEUTRAL-below-EMA300 / tide BEARISH) — that
disagreement IS the chop. **0 open positions = correct.** Standing steer: favour SHORT setups while 1m closes
hold below EMA300 (80734); retract to neutral if 1m holds above for 15-30m. Watchdog's own deep analysis:
queue is 6-of-7 SHORT but 5 sit under `SHORT_RSI_HARD_FLOOR=45` → expect 0-1 fills, do not count the queue as
coverage. Watchdog #4 recommendation ("entry test, not signal-green test") is exactly what leg 2 measured.
No new steer required action this run; no kill/param proposal came from it.

## CEO STACK (unchanged except #1)
1. **TRAIL-FLOOR AT PEAK-0.20 GO** (replaces/aheads BE-at-arm — beats it on every axis, table above)
2. pump-chain+ NO-KILL (30d `+1.84`, 14d 46T 28.3% `-0.43` = kill criteria MET-by-letter, `no_signal_enable_disable`
   blocks unilaterally) → CONF_FLOOR fkA 41.7% FAIL ruling → pump-chain TAT BASE-vs-VARIANT-C
3. **VETO WINDOW on the spider tier fix** (revert = `profit_monster.py:517-523`, one line)
4. UGB-BE pending (PT subsumes it) · Oct-27 contrarian PROMOTE + coin_regime n≥50 + mid-band dampen re-measure
5. Nov-15 floor_admit 30d same-sign (638ep, p=0.126 COLLECT)

## NUMBERS (PG this run)
24h **13T 9W 69.2% `+$0.66` GREEN** | 7d 123T 43.1% `-$0.68` | 14d 326T 37.7% `-$3.58` | 30d 688T `-$2.16`
7d ARMED 63T 71.4% `+$3.27` vs UNARMED 60T 13.3% `-$3.95` | 14d ARMED 157T 70.1% `+$9.17` vs UNARMED 169T `-$12.75`
7d exits: **PM-trail 41T 36W `+$2.53`** vs chop/stop **HML 15T 0W `-1.89` + atr_sl 27T 0W `-1.48` +
stale 3T 0W `-0.64` + hard_sl 4T 0W `-0.36` = 49T 0W `-$4.37`** → trend/chop law unchanged.
**Autopsy 48h n=14 (adverse-first, selfcheck PASS) = 4 never-adverse / 5 recovered / 5 NEVER → wrong-side
REFUTED 59th consecutive run** (valid refs: #61 p=0.116, #84 t=-0.04). NEVER cohort = ALT/CC/ZRO
`volume-buildup-` shorts `-0.11..-0.17` + BTC pending + PUMP r2v2 — all tiny, known.
**Shadow:** contrarian outcome join re-run — **pump-chain- flip-WR 64.0% n=339 (OOS 64.0%)**; btc-pump-rider+
25.0% = do NOT flip; 1/5 raw files answerable (oscillator frozen-by-design, wyckoff/floor pending, rr orphaned).
`shadow_trader --report`: 20104 signals — gate + exit A/B independently reproduces trail-or-nothing
(pm_trail `+2737` vs hard_max `-4382`).

## LAST-RUN VERIFY (#132/#133/#134) — ALL PASS
be_at_arm selfcheck PASS **and its published 30d `+$2.140` independently reproduced by a separate replay path**
· mfe_cut selfcheck PASS, verdict stays BAR FAIL (fk_cohort 23.5%) · habitat dampen stays REJECTED (fk 26.2%)
· floor_admit selfcheck PASS (638ep) · UGB-PT correct-by-traffic · **`hermes_constants.py` git diff EMPTY** ·
**size-reduce file absent = 1.0x** · **CEO_PROTECTED_FLAGS 13/13** · **0 uncaught component Tracebacks
2026-10-25** (only the recurring Sunday 03:00 `Self-healing test: FAIL`, 3rd occurrence Oct 11/18/25 — **never
triaged, NEW SIDEWAYS FIND**).

**⚠️ ARM-BE "0 fires correct-by-traffic" is still UNPROVEN, not proven** — 0 fires since the #127 fix, but
sibling UGB-BE also 0 and the book was flat for most of it. It is *no eligible traffic*, not *verified*.

## SIGNAL QUALITY — 0 NEW TARGETS
sub-50% WR, n≥15, 14d: bb-bounce-v2-long+ 34T 41.2% `-1.01` (weekly auditor, in flight) · ai-trader+ 23T
(disabled) · doji-bottom-long 16T (killed Oct 16) · pump-chain+ 46T 28.3% `-0.43` (kill MET, CEO) ·
pump-chain- 35T 22.9% `-0.30` (Oct-27 contrarian PROMOTE). **Every sufficient-n bleed cohort is already
killed, disabled, in flight, or pre-registered to a dated ruling.**

## NEXT ACTIONS
1. CEO ruling: **trail floor at peak-0.20** (upgraded from BE-at-arm) → v6 exit-stack; ARM-BE shadow stays on
2. CEO veto window on the spider tier fix (one-line revert)
3. **Build: bypass-engine candle OOS** — last unmeasured piece of escalation #17, `+$2.368`/30d
4. Oct 27: contrarian pump-chain- PROMOTE (flip 64.0% n=339 + arm-rate 25.7% n=35) + coin_regime n≥50 + mid-band
5. PM activation-coverage KPI → n≥20 (pre-registered this run)
6. Disk >85% → price_history 30d retention (orchestrator sideways find); hotset 0-token re-check ~07:00 Oct 26
7. Triage the recurring Sunday `Self-healing test: FAIL` (3rd occurrence, never looked at)
