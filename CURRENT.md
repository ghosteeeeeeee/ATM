# Current State — brain_auditor #255 2026-11-13 08:50 UTC
**Last Updated: 2026-11-13 08:50 UTC**
**Updated by: brain_auditor #255. Prior: #254 2026-11-13 04:45 UTC (preserved in git history).**

## HEADLINE — 0 CONFIG CHANGES; WINNER-CELL REVERT RESOLVED; EXIT-STACK DAY TOMORROW (13 ITEMS)

1. **0 trading-constant changes** — session lock ABSENT, hermes_constants.py EMPTY git diff, CEO_PROTECTED intact, size-reduce absent = 1.0x, nothing passed bars.
2. **WINNER_CELL_SIZE_MULT 1.25→1.0 RESOLVED** — CEO fired revert 04:03Z; live value=1.0 verified. Root cause #234: 69.5% fills floored at HL_MIN so 1.25 never bit winners. CEO owed item CLEARED.
3. **11-14 EXIT-STACK DAY** — 13 items due tomorrow (mfe-cut, mult-150, jup-short-walk, atrtrail-clip, stop-tighten eval+probe, bbsqueeze x3, prearm-BE, drop-pcplus, slippage-column, tat-neverarmed) + NEW amplify-vb-high-short-underdeploy.
4. **Autopsy 48h**: n=12 = 1/9/2 NEVER (≤0.12) → wrong-side refuted 83rd consecutive.
5. **AMPLIFY: 1 new** — vb- HIGH SHORT underdeployment clone-hunt (validated cell 19T/30d 78.9% +0.42 but 0/7d). pc- NORMAL LONG REJECTED (one outlier = 36% net). Flip-KPI met via winner-cell-size-125.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h | 19T 57.9% +0.15 GREEN, 1 open BTC SHORT, 0 steers |
| 7d/14d | 95T 46.3% -2.39 / 344T 52.3% -4.23 |
| RR asymmetry | 14d avg win +0.062 vs avg loss -0.102 (1:1.65); break-even loss = -0.068, KPI bar -0.070 correct |
| biggest bleed | jup atr_sl_hit 14d 24T 0% -3.26 + hard_max 21T -3.04 (owned by 11-14/11-17) |
| sub-50 new targets | 0 |
| floor fisher p | 0.0442 (drifting toward 0.05) — due 11-15, do NOT ship early |
| pc- flip | 60.6% (212/350, decay from 63.7%) — PROMOTE stands + DECAY WATCH (demote <55%) |
| atr-trend- boost | post-ship n=2 -0.23 — MONITOR, stability rule holds |

### 2. NUMBERS (fresh PG 08:40Z)
- 24h **19T 57.9% +0.15** | 7d **95T 46.3% -2.39** | 14d **344T 52.3% -4.23** | 30d **689T 49.3% -7.42**
- armed 14d 170T 92.9% +9.62 vs unarmed 174T 12.6% -13.85
- 7d exits: atr_sl_hit 22T 0% -2.62 (dominant) vs profit-monster-trail 30T 96.7% +1.13
- contrarian 08:30Z: pc- **60.6% n=350** · rider 40.5% · overall 44.6% n=1759
- floor 04:30Z: **p=0.0442** · floor 48.8% n=1691 vs always 42.5% n=325 · same-sign due 11-15

### 3. SHADOW (3/5 usable)
- contrarian + floor joins fresh (mandate ✓)
- shadow_trader 95,446: pm_trail +14,318 vs hard_max -16,919 = trail-or-nothing
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + CREATIVE
- **48h recovery_replay (adverse-first): n=12 = 1/9/2 NEVER → wrong-side refuted 83rd** (#61 p=0.116, #84 t=-0.04).
- **Creative x2:** pc- flip decay threshold (demote <55%) · stop-tighten×prearm-BE interaction read for 11-14.
- **AMPLIFY new:** amplify-vb-high-short-underdeploy (due 11-20).

### 5. READINESS (2026-11-13 08:50 UTC)
**1 open: BTC #16891 SHORT ai-trader-pending @68558 SL68880 TP66637** — meta_rsi 21.18 (knife-zone but ai-trader CEO domain, bracketed). Regime: 15m LONG_BIAS vs 4h SHORT_BIAS split / continuum BELOW / trend_quality STRONG_DOWN / vol NORMAL → **SHORTS align with structure; no fresh LONG entries; trail-family only; size 1.0x.**

**Queue:** **11-14 EXIT-STACK DAY (13 due + vb-underdeploy)** → 11-15 floor same-sign + exitstack-day-kpi-1114 → 11-16 atr-trend cell → 11-17 jup batch → 11-18 contrarian fade + xmirror → 11-20 vb-underdeploy → 11-27 pc-plus-weight + linreg-fade.
**CEO owed:** exit-stack pull-forward (#251). **CLEARED:** winner-cell revert 1.25→1.0 (done 11-13 04:03Z).
**Housekeeping:** session_brain rebuild owed 11+ runs (title/date null on user chunks; OpenMemory partial substitute).
