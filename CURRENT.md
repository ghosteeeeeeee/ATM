# Current State — brain_auditor #239 2026-11-08 12:50 UTC
**Last Updated: 2026-11-08 12:50 UTC**
**Updated by: brain_auditor #239. Prior: #238 2026-11-08 08:45 UTC (preserved in git history).**

## HEADLINE — FALSE AMPLIFY CAUGHT BEFORE IT SHIPPED: `grind-breakout-` SHORT looked like a conversion (raw n=32, 93.8% WR, candle fwd4h +3.155% t=5.40) but shadow_trades.db pseudo-replication collapses it to n=11 / t=1.42 n.s. / second half negative. Detector `brain/analysis/shadow_dup_check_2026-11-08.py` shipped (--selfcheck PASS). 0 config changes, 0 new amplify proposals.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **grind-breakout- AMPLIFY (HEADLINE)** | REFUTED-WITH-DATA. Raw 32T 93.8% fwd4h +3.155% t=5.40 91% win → **deduped n=11 +2.208% t=1.42 n.s., second half -0.095 NEGATIVE**. Knife-floor-blocked subset 14 raw → **5 deduped** (bar 20). Leave-one-out on the raw set was clean, which is why dedup — not the walk — is the killer. |
| **shadow_trades pseudo-replication (ROOT CAUSE)** | rows unique by signal_id 75,694/75,694, but same-second re-emission under distinct ids → distinct(source,token,created_at) = 72,712 (3.9%). Concentrated: grind-breakout- 2.9x, btc-pump-rider+ 904→486, ichimoku+ 1249→798; gate counts **CTX-GATE 2453→929 (2.6x)**, COOLDOWN-SKIP 317→146, EXEC-FAIL 495→302. Same class as gate-shadow (7-10x, due 11-10) — disposition extended, second DB. |
| **stop-tighten mid-eval (rule 7)** | ENFORCE **WORKING** (13 enforce lines, cap 0.750, clamps on 16809/16813/16815/16818). Post-ship jup+vb **20T 80.0% +0.710** vs pre-ship 181T 60.2% -2.31; jup LONG post 6T +0.13 / SHORT post 13T 84.6% +0.56. **fisher p=0.094 NOT significant** + volume-collapse confound (43/day → 5/day). **MED: pipeline.log retains STOP-TIGHTEN only from 11-07 14:12 (rotation) = 4 ids — 11-14 eval must pull rotated logs or it under-counts the ≥20-id bar.** |
| **RR asymmetry (structural)** | 7d breakeven WR **63.4%** vs actual **56.4%** — avg win +0.063 vs avg loss -0.109 (1.73x). WR climbed 46.6% (30d) → 56.4% (7d) yet PnL stays negative. Remaining lever = **loss SIZE**, not entry count. |
| **#238 verify** | drop-pcplus still open (pc+ EXTREME -0.04/30d, bar unchanged) · dailyfillcap-identity NO-TRAFFIC holds (0 lines after 05:03Z) · joins re-run. **ALL PASS.** |

### 2. NUMBERS (fresh PG 12:35Z)
- 24h **9T 66.7% +0.08 GREEN** | 7d **156T 56.4% -1.75** (LONG 116T 53.4% -1.74 / SHORT 40T 65.0% -0.01) | 14d 392T 54.6% -3.35 | 30d 774T 46.6% -6.76
- 7d exit families: **TRAIL/TP 93T 91.4% +5.11 vs CHOP/STOP 59T 0% -6.93** (hard_max_loss 34T 0% -4.17 · atr_sl_hit 25T 0% -2.76)
- 7d regime: NORMAL 85T 62.4% -0.02 | FLAT 12T 66.7% -0.03 | HIGH 41T 51.2% -0.97 | EXTREME 18T 33.3% -0.73 (sign-flips vs 30d EXTREME-best → no regime gate)
- **jup fill cap HOLDING: last-50 jup share 30.0% < 35% bar** (post-11-04 35.7%)

### 3. SHADOW (2/6 usable, both re-run this run)
- **contrarian join 12:30Z**: overall flip **43.1%** n=1442 | **pc- 64.6% (226W/124L) LIVE uniform** chi2 p=0.375 | rider 36.2% do-NOT
- **floor join 08:30Z**: floor_only 49.2% vs always_admit 43.7%, fisher **p=0.1411 COLLECT** (bar 11-15)
- shadow_trader **75,685**: gates justified (CONFLUENCE-EXPIRY 15,841 @43% avg -0.13; CONFLUENCE only >50% at 56% but still -0.09) · exit A/B **pm_trail +11,328 vs hard_max -13,275** = trail-or-nothing
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED — **per-source n in the shadow report is NOT citable without dedup**

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 3 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 66th consecutive** (#61 p=0.116, #84 t=-0.04).
- Deep-dive: **0 new sub-50% n>=15** (pc+ 29T 48.3% owned NO-KILL/CONF_FLOOR; pc- 32T 37.5% **net +0.07** owned watch-contrarian).
- **AMPLIFY this run: NONE — rule-3 why-not recorded.** All 4 VALIDATED/early cells with n≥10 net>0 already carry in-flight proposals (size-125 11-10 · vb- clone-hunt 11-13 · jup-short-walk 11-14 + jup-short-high-cell 11-19); pc- NORMAL LONG amplitude +0.19/30d is below materiality (1.25x ≈ +0.05/30d); the only fresh clone-hunt hit was refuted above. **Flip-KPI MET this week** (stop-tighten ENFORCE 11-04, SHORT_RSI_CEILING 65→75 11-03, harvest 11-04); 0 new conversions, stated here.
- Creative x3: dedup guard (shipped) · stop-tighten mid-eval read · RR-asymmetry framing.
- constants EMPTY diff · session lock ABSENT · CEO_PROTECTED 13/13 · size-reduce absent = 1.0x · watchdog steers [] · checkpoint_registry 0 pending.

### 5. READINESS (2026-11-08 12:50 UTC)
**0 open / 0 steers / portfolio good.** 0 open is CORRECT: btc_15m LONG_BIAS vs btc_4h SHORT_BIAS = **disagree = chop**, continuum AT, vol LOW, velocity SLOW, volume LOW, trend_quality STRONG_DOWN. No counter-trend fresh entries while the two timeframes disagree; trail-family first; LONGs only on a sustained EMA300 reclaim WITH volume; size **1.0x**.

**Queue:** **11-09 zombie-purge DECIDE** → **11-10 gate-shadow-dedup-convention fold (now covers shadow_trades.db) + size-125 + fade-ctx + warrior-uninert + jup-atrsl-parity + conf-filter-parity + rsi-ceiling-75 + mfe-cut-arm-be + ichimoku-dampen** → 11-11 contrarian watch → 11-12 storm-waiver bar → 11-13 pc+ kill-review + vb- clone-hunt + linreg-fade funnel → **11-14 stop-tighten eval (READ ROTATED LOGS) + drop-pcplus + probe-080 + bbsqueeze reband/neutral-exempt + mult-150 adjudication + atrtrail-clip + prearm-breakeven + TAT-age-sweep** → 11-15 floor → 11-19 jup HIGH OOS → 11-21 conf-tilt + stop-tighten scope-widen walk.
**CEO:** stack unchanged — **mult-150 sign-off (evidence decayed: judge ex-pc+ or drop first)** · stop-tighten scope-widen walk (11-21) · **jup HIGH cell HOLD (bars met but 2-week-old cell, no OOS)**.
