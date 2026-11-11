# Current State — brain_auditor #247 2026-11-11 04:51 UTC
**Last Updated: 2026-11-11 04:51 UTC**
**Updated by: brain_auditor #247. Prior: #246 2026-11-11 00:50 UTC (preserved in git history).**

## HEADLINE — GUARDRAIL ESCALATE ACTIVE (alert-only); NEW AMPLIFY UGB-BYPASS-ARMGAP; WINNER-CELL REVERT STILL OVERDUE

1. **VACATION-GUARDRAIL ESCALATE firing every 30min since 00:49Z** — 48h WR 36.7-37.5% < 40.0 with 29-32 trades. **Alert-only: pause thresholds NOT met** (pnl_24h -0.54 > -3.00; 7d WR 51.1% > 35; size-reduce absent = 1.0x). Composition scattered: ai-trader-pending SHORT -0.44 (biggest, CEO/autopilot domain), jup SHORT -0.32, atr-trend- -0.25. Guardrail working as designed — no action.
2. **AMPLIFY NEW: `amplify-ugb-bypass-armgap`** (type a, due 11-18, NO-SHIP default). 30d arm-gap atr_sl (MFE>=0.40, trailing_activated=False, exit atr_sl_hit) = **34T -$2.17; ~32/34 are PROFIT_MONSTER_BYPASS signals** (pump-chain± 22, ai-trader± 5, r2-trend 2, continuum-osc 1, hl_copy 2) that UGB-PT skips by 2026-10-31 design. They reach trail activation then surrender the full move to ATR SL. Candle-walk bar: n>=20 ∧ net>=$1.00/30d pnl_usdt (units guard) ∧ fk of would-be-killed winners <20% ∧ 14d same-sign.
3. **CEO ACTION STILL REQUIRED: `WINNER_CELL_SIZE_MULT` 1.25→1.0 revert ~28h OVERDUE** (deadline was 00:00Z 11-10). Constant still 1.25 at `hermes_constants.py:1174`. One-line CEO act or explicit extension.
4. **0 trading-constant changes** — session lock ABSENT, hermes_constants EMPTY git diff (only auto-generated `_candidates` backtest metadata touched by candidate pipeline 03:58Z), CEO_PROTECTED intact, size-reduce absent = 1.0x, 0 Tracebacks today.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| guardrail escalate | ALERT-ONLY — pause bars not met; no action |
| arm-gap bypass giveback | 34T -$2.17 unowned → amplify registered due 11-18 |
| deep-dive kill targets | 0 new (pc+ CONF_FLOOR, pc- PROMOTE net-positive) |
| winner-cell revert | STILL overdue ~28h → resurfaced |

### 2. NUMBERS (fresh PG 04:45Z)
- 24h **17T 52.9% -0.54** | 48h **32T 37.5% -1.33** | 7d **90T 51.1% -1.52** | 14d **374T 53.5% -3.74** | 30d **749T 46.6% -9.27**
- armed 14d **192T 90.6% +10.99** vs unarmed 182T 14.3% **-14.73** | armed 7d 48T 89.6% +2.36 vs unarmed 42T 7.1% -3.88
- 14d exits: profit-monster-trail **133T 97.7% +7.43** | mfe_exit 38T 84.2% +1.79 | **atr_sl_hit 59T 0% -6.49 (#1 bleed)** | hard_max_loss 44T 0% -5.41
- chop-bleed share 7d: **91.9%** (just under 92% push threshold)

### 3. SHADOW (3/5 usable)
- **contrarian join 04:30Z (mandate):** overall flip **44.8%** n=1648 · **pc- 64.6% (226W/124L n=350) STABLE** · rider 39.5% do-NOT · pc- chi2 p=0.375 uniform
- floor join 11-10 20:36Z fresh → 11-15 same-sign read on track
- shadow_trader 04:32Z 86,543 signals: gates justified; exit A/B **pm_trail +13,034 vs hard_max -15,350** = trail-or-nothing
- oscillator FROZEN (archived) · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=19 = 6 never-adverse / 10 recovered / 3 NEVER (FOGO -0.13, DYDX -0.10, GMX -0.10 immaterial) → WRONG-SIDE REFUTED 75th consecutive.** 16/19 never-armed.
- **AMPLIFY: 1 NEW** — amplify-ugb-bypass-armgap (type a, due 11-18). Flip-KPI: 0 new conversions this run (week day 2).
- Creative x1: UGB-PT bypass-armgap extension (see audit_recommendations).

### 5. READINESS (2026-11-11 04:51 UTC)
**0 open — CORRECT.** btc_15m LONG_BIAS vs btc_4h SHORT_BIAS disagree; continuum BELOW; trend_quality STRONG_DOWN; vol NORMAL; auto_trader CHOP (long -5 / short -35 → BRACKET); no steers. Flat until a side sustains 15-30m. Trail-family first; size 1.0x; no size added.

**Queue:** **CEO: winner-cell revert (OVERDUE ~28h)** + fade fee/size input → 11-12 storm x3 → 11-13 pc+ kill-review + vb- clone-hunt + linreg fill + chop-exempt → **11-14 EXIT-STACK DAY** (13 entries) → 11-15 floor same-sign → 11-16 atr-trend cell → 11-17 jup batch + atrsl + 7 shadow bars → **11-18 contrarian fade read + atr-trend clone-hunt n + UGB-bypass-armgap candle-walk** → 11-19 jup HIGH OOS → 11-21 structure-flip + conf-tilt → 12-15 ugb-bypass-hole.
**CEO owed:** winner-cell revert · fade fee/size review · mult-150 sign-off (folds into revert) · unclog-waiver [35,45) re-measure · fade-ctx fee-net · jup Option-D monitor.
