# Current State — brain_auditor #198 2026-10-29 16:45 UTC
**Last Updated: 2026-10-29 16:45 UTC**
**Updated by: brain_auditor #198. Prior: #197 2026-10-29 04:55 (preserved in git history).**

## HEADLINE — size_mult stamp VERIFIED working; MIDDLE-zone bleed investigated and
## REJECTED as confounder; chop-bleed 3rd breach at 95.0% still awaiting CEO veto decision

0 config changes (vacation review queue honored, session lock absent,
`hermes_constants.py` EMPTY git diff vs HEAD, CEO_PROTECTED 13/13, size-reduce file
absent = 1.0x), **0 ships, 0 trade actions, 2 creative ideas (1 suggested, 1 pre-registered).**

### 1. LAST-RUN VERIFY #197 — all PASS
| Item | Result |
|---|---|
| size_mult stamp at open | **VERIFIED** — BTC #16518 carries `size_mult=1.5` (amount 16.60), all recent opens carry `1.0`; stamp working correctly |
| mfe_write_at_close | **HELD** — all recent closes have mfe_pct |
| bb-squeeze+ weight 1.0 | **POSITIVE** — 8T 100% +0.25 (24h), 27T 74.1% +$0.77 (14d); at ceiling, hold |
| contrarian join mandate | **EXECUTED** fresh 16:30Z — 863 joinable, flip 42.0%; pc− 64.6% n=350 LIVE · rider 26.7% do-NOT-flip |
| floor admit join | **FRESH** — floor 48.1% vs always 44.0%, Fisher p=0.477 → COLLECT |
| #194 0.75x veto | **STILL PENDING CEO** — chop-bleed now 3rd consecutive breach (94.3→94.5→95.0%) |
| constants / lock / size-reduce | EMPTY diff / absent / absent = 1.0x |
| recovery_replay selfcheck | PASS |

### 2. MIDDLE-ZONE bb_position investigation — REJECTED-WITH-DATA (confounder)
**Finding**: MIDDLE zone (bb_position 0.2–0.8) bleeds -$2.90/14d, -$4.89/30d; UPPER positive
+$0.60/14d, +$3.16/30d. Fisher aggregate p=0.017. **BUT**: pump-chain+ specific p=0.826 (NOT
significant) — the MIDDLE bleed is driven by signal mix (ai-trader+, doji, bb-bounce concentrated
in MIDDLE), not that MIDDLE causes losses. Same-signal zone split is noise.
**Per THE PATTERN rules: confounder check FAILS → DO NOT SHIP.** Recorded as monitoring KPI.

### 3. CREATIVE x2 (both zero-code)
1. **bb_position zone distribution KPI** — track per-signal zone distribution each run.
   bb-squeeze+ fires 100% UPPER (75% WR). Signals drifting toward MIDDLE are losing their edge.
2. **bb-squeeze+ DNA: BB-width percentile compression gate** — bb-squeeze+ works because BB
   squeeze = compression before expansion. A universal "BB width bottom 30% of 7d range" filter
   could block expansion-chase entries. Needs BB-width backtest before shipping.

### 4. LOSING AUTOPSY (adverse-first, selfcheck PASS)
24h n=6 losers — **all 6 never-armed (MFE<0.40%)** = classic chop pattern. Worst: BTC #16518
continuum-osc- SHORT -$0.25 (entered SHORT during TRANSITIONING regime, RSI 67 at entry).
**WRONG-SIDE REFUTED 123rd consecutive run** (#61 p=0.116, #84 t=-0.04).

### 5. DEEP-DIVE: 0 NEW sub-50% n≥15 targets
All owned: bbbv2 TAT-LIVE + CEO · pc+ NO-KILL (30d +$1.92) · ai-trader-pending CEO domain.
volume-buildup− 58.5% WR but -$0.63 — losses never arm (MFE 0.211 vs wins 0.884); arm-rate
problem, not WR problem. Not a new kill candidate.

## PG FRESH (16:40 UTC)
24h **23T 73.9% −0.07** · 7d 141T 57.4% −0.54 · 14d 298T 47.0% −3.23
· armed 14d **155T 79.4% +8.10** vs unarmed **143T 11.9% −11.33**
· 7d exits: profit-monster-trail 55T 96.4% +3.05 vs atr_sl_hit 13T 0% −1.52 /
hard_max_loss 8T 0% −1.18 · 14d trail family 132T 89.4% +8.46 vs chop 106T 0.9% −10.35
· chop-bleed 7d: never-armed 50T −5.15 of 56T −5.42 = **95.0%** (3rd breach)

## READINESS — 2 open, WATCH
**COMP #16526 LONG bb-squeeze+** @21.89 + **WLFI #16525 LONG bb-squeeze+** @0.0519 —
both rule-compliant (bb-squeeze+ = trail-family signal). Regime: btc_15m LONG_BIAS vs
btc_4h SHORT_BIAS (disagree) → **NO fresh discretionary directional entries**; LONGs only on
sustained EMA300 reclaim WITH volume; SHORTs only under EMA300 with 4h aligned;
trail-family first; **size 1.0x**.

## QUEUE
**Next run**: verify size_mult continues landing · re-read chop-bleed (4th breach?) ·
**CEO**: 0.75x veto decision (kanban, from #197 — chop-bleed 95.0%) ·
**2026-10-30** scoped momentum time-stop BLIND ·
**2026-11-03** coupled-SL disposition A/B + contrarian conversion KPI + vacation waiver expiry ·
**2026-11-10** CHASE-MOVE flip + MFE-CUT (default KILL) ·
**2026-11-15** floor_admit 30d bar + wyckoff join ·
**CEO queue**: C2 early-arm ladder · CONF_FLOOR fk pin · TAT variant-C (verify stale) ·
tf-authority 1m-vs-5m · bb-bounce.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json,
CURRENT.md.
