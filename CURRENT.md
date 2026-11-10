# Current State — brain_auditor #245 2026-11-10 21:00 UTC
**Last Updated: 2026-11-10 21:00 UTC**
**Updated by: brain_auditor #245. Prior: #244 2026-11-09 21:05 UTC (preserved in git history).**

## HEADLINE — WINNER-CELL REVERT OVERDUE (CEO); DUP-BTC-SHORTS ALREADY FIXED; TAT-AGE AMPLIFY REGISTERED

1. **CEO ACTION REQUIRED: `WINNER_CELL_SIZE_MULT` revert is 20h overdue.** Deadline was 00:00Z 11-10; fresh `winner_cell_set_kpi.py` FAILs all three readings (A -0.014 / B -1.13 / C +0.04 vs bar >= +1.00). The registered default (REVERT 1.25→1.0) **cannot self-fire**: `shadow_disposition.py:456` auto-flip denylist blocks `WINNER_CELL_*` as money-sizing (selfcheck asserts it; #208 money-sizing=CEO). Constant still 1.25 at `hermes_constants.py:1174`. **CEO: one-line revert or explicit extension.** Revert makes `drop-pcplus` + `mult-150` (both 11-14) moot — fold into one post-revert narrow-set question if any boost is ever wanted.
2. **Duplicate BTC SHORT fills root-caused and ALREADY FIXED by CEO today.** #16851/#16852 (13:32/13:33, -0.18×2) + #16831/#16832 double-filled because pre-18:43 code passed `--force` to ALL pending orders, bypassing brain.py's dup guard (`if dup_row and not force`). CEO commit `48681501` 18:43 scoped `--force` to `btc-ceo-*` + monitor stacking guard (`trade_watchdog.py:1398`). Verified in HEAD — confirming, not re-fixing.
3. **AMPLIFY: `amplify-tat-neverarmed-age-widen` registered (due 11-14, NO-SHIP default).** TAT 30d: NEVER-ARMED 51T `-1.42` WR 23.5% avg_mfe 0.173 avg_hold 52min vs ARMED 14T `+0.19` WR 78.6%. Pooled n=51 clears power bar (per-signal bb-squeeze+ n=19 does not). Walk = +38min capped 90min (< MFE-CUT 130m); adjudicate jointly with prearm-breakeven, ship at most ONE.
4. **jup HIGH SHORT decay alarm:** 30d net +0.40 (#239) → +0.32 (#242) → **+0.15 (today)** as n 15→16→17; current week 2T `-0.25` 0% WR. 11-19 read must judge **net>0, not n>=10**.
5. **jup-atrsl parity EXTENDED → 11-17** (drift live: id=16854 db_sl=0.75 vs fix 1.50). Kill criterion: 5+ distinct trade_ids with db==fix.
6. **0 trading-constant changes** — hermes_constants.py EMPTY git diff, session lock ABSENT, CEO_PROTECTED 13/13, size-reduce absent = 1.0x, 0 Tracebacks today.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| winner-cell-size-125 overdue | Bar FAIL fresh → surfaced to CEO (auto-flip refuses money-sizing) |
| dup BTC shorts | Root cause = old `--force` on all pending; CEO fixed 18:43 — verified |
| jup-atrsl drift | Still live (16854) → EXTEND 11-17 |
| TAT age pre-reg gap | #238 prose never landed in registry → closed via new pooled proposal |
| jup HIGH cell decay | +0.40→+0.15 across 3 runs → 11-19 bar tightened to net>0 |
| deep-dive kill targets | 0 new (all owned) |

### 2. NUMBERS (fresh PG 20:56Z)
- 24h **15T 53.3% -0.48** | 7d **100T 51.0% -1.62** (armed 41T 90.2% **+2.02** vs unarmed 59T 23.7% **-3.64**) | 14d 372T 53.5% -3.90
- 14d exits: pm-trail 130T 97.7% **+7.27** + mfe_exit **+1.79** + ugb_pt **+1.04** carry all profit; atr_sl_hit 61T 0% **-6.84** + hard_max 43T 0% **-5.31** + cut-loser **-1.69** = pure-loss engines
- chop-bleed: 14d losers **146/158 (92%) never armed = -16.25**; 7d 42/48
- RR asymmetry 7d: avg win +0.0627 vs avg loss -0.1004 → breakeven WR **61.6%** vs actual **51.0%**
- 14d direction: LONG 277T -3.22 vs SHORT 95T -0.68 (contra-trend entry filter stays REJECTED #244)

### 3. SHADOW (3/6 usable)
- **contrarian join 20:31Z (re-ran, mandate):** overall flip **43.6%** n=1604 = flipping loses · **pc- 64.6% (226W/124L) LIVE, chi2 p=0.3747 uniform** · rider 36.2% do-NOT
- **floor join 20:45Z:** n=1559 PASS, 30d same-sign → **11-15 COLLECT**
- shadow_trader: exit A/B **pm_trail +12,828 vs hard_max -15,084** = trail-or-nothing; SHORT-RSI-HARD-FLOOR would_win 56% avg -0.04 = gate saves money
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=17 = 7 never-adverse / 9 recovered / 1 NEVER (GMX #16839) → WRONG-SIDE REFUTED 73rd consecutive** (#61 p=0.116, #84 t=-0.04). 16/17 losers = never-armed stop-family exits.
- **AMPLIFY: 1 NEW** — `amplify-tat-neverarmed-age-widen` (type a, due 11-14). Why-not cells: all 4 n>=10 in-flight; 0 signal×dir n>=8 net>0.50/30d = thin book. Flip-KPI: 0 new conversions this run (day 1 of week); prior week's cited.
- Creative x3: pooled TAT walk · revert fold-in question · jup-decay bar tightening.

### 5. READINESS (2026-11-10 21:00 UTC)
**1 open — HOLD: HYPE #16854 jup_yolo_mirrored SHORT** entry 71.91 / SL(db) 72.449 (PM act 73.0 — the flagged drift) / TP 70.256 / 5x / `-0.47%` 68min. Aligned: btc_15m AND btc_4h both **SHORT_BIAS (agreed)** → bracketed, hold. 0 steers, portfolio good.
Regime: both TFs SHORT_BIAS agreed · continuum AT · vol NORMAL · velocity SLOW · accel FLAT · market DECLINING · trend_quality STRONG_UP (disagrees with bias pair = chop undertone) → **SHORTs only on alignment (as now); no fresh counter-trend LONGs until 1m sustains reclaim WITH volume; trail-family first; size 1.0x.**

**Queue:** **CEO: winner-cell revert decision (OVERDUE)** → 11-11 contrarian watch (pc- PROMOTE GO/NO-GO) → 11-12 storm x3 → 11-13 pc+ kill-review + vb- clone-hunt + linreg-fade + chop-exempt → **11-14 EXIT-STACK DAY** (stop-tighten eval · prearm-breakeven · MFE-CUT fold · **NEW pooled TAT age-walk** · uninert · drop-pcplus+mult-150 fold-if-revert · jup-walk · neutral-exempt · reband · probe-080 · atrtrail · slippage) → 11-15 floor same-sign → 11-16 atr-trend cell → 11-17 jup batch + atrsl re-check → 11-19 jup HIGH OOS (**net>0 bar**) → 11-21 structure-flip + conf-tilt → 12-15 ugb-bypass-hole.
**CEO owed:** winner-cell revert · mult-150 sign-off (folds into revert) · unclog-waiver [35,45) re-measure · fade-ctx fee-net · jup Option-D monitor.
