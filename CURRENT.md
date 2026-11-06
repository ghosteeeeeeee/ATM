# Current State — brain_auditor #230 2026-11-06 20:55 UTC
**Last Updated: 2026-11-06 20:55 UTC**
**Updated by: brain_auditor #230. Prior: #229 2026-11-06 13:04 UTC (preserved in git history).**

## HEADLINE — shadow-log pseudo-replication is systemic in position_manager (8 per-process dedup sets): jup/vb TAT 6,437 lines = 29 trades (222x), MFE-CUT 8,548 = 65 (131x), HML 29,987, ATRSL 9,244. Warnings added to the 2 undocumented blocks (comment-only, 13 insertions, zero behavior). Structural fix queued. AMPLIFY emit: amplify-bbsqueeze-neutral-exempt (sibling-gate clone-hunt, due 11-14).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **shadow-log dedup (MEDIUM side-find)** | 8 module-level sets reset every STEPS_EVERY_MIN subprocess. Measured: HML-SHADOW 29,987 lines · ATRSL 9,244 · MFE-CUT 8,548 lines/65 trades (131x) · jup-vb TAT 6,437/29 (222x). Same class as gate-shadow event inflation. **WARNINGS ADDED** to jup/vb TAT + MFE-CUT blocks (position_manager.py, comment-only, py_compile PASS). Structural fix = persist sets like profit_monster._load_trail_state — queued, needs subagent+bug_hunter. |
| **AMPLIFY #230 (NEW)** | `amplify-bbsqueeze-neutral-exempt` due 11-14. bb-squeeze+ LONG × LONG-NEUTRAL (sibling of in-flight CHOP-only exempt). 14d tok-day dedup 41ev/17td/68.3%/+1.49 (10-26..11-04); 30d 29td/78.9%/+2.35; family-union 30d 39td/80.9%/+4.18, 14d 27td/73.3%/+2.42. **13/39 neutral token-days sit under BOTH gates** → CHOP-only exempt leaves them shut. CONFLUENCE candidate REJECTED (52/90 events cluster Oct-4/5, 14d collapses to 63.2%). |
| **winner-cell screen** | 4 of 6 n>=10 cells already in-flight. pc- NORMAL LONG REJECTED (born 10-31, daily sign-flip, +0.24 thin). pc-,pc-v6- EXTREME SHORT n=10 WR 30% = noise. |
| **Flip-KPI 0 this week** | mult-150 MET but awaiting CEO label+T sign-off (money-sizing) · fade-ctx fee-net FAIL (-0.37) · storm needs 3 packets (0) · jup/vb TAT no OOS yet. |
| **#229 verify** | combo pin HELD (1.3/1.6 + PINNED_COMBO_WEIGHTS); post-pin bb+ 2T / warrior 0T = INSUFFICIENT, bar 11-10 · gate_shadow_health selfcheck PASS (34 gates) · harvest KEEP-ALL-4 no action · linreg-fade 0 fills (11-13). |
| **jup ATRSL fix side-info** | pre-fix (open<11-03) 96T 59.4% -1.08 vs post-fix 37T 67.6% +0.23. 3d window, regime confound — pre-register 7d re-read, no claim. |
| **Autopsy 48h (MANDATE)** | n=9 = 3 never-adverse / 6 recovered / **0 NEVER** → WRONG-SIDE REFUTED **86th** (#61 p=0.116, #84 t=-0.04) |

### 2. NUMBERS (fresh PG)
- 24h **15T 53.3% '-0.47' RED** | 7d **222T 53.6% '-1.91' RED** | 14d 403T 55.3% '-2.07' | 30d 777T 46.1% gross '-6.28'
- 7d by regime: EXTREME 27T 37.0% '-0.90' · HIGH 69T 56.5% '-0.75' · NORMAL 110T 53.6% '-0.44' · FLAT 16T 68.8% '+0.18'
- 7d exits: **TRAIL 100T 85.0% '+4.89'** + mfe 35T 82.9% '+1.63' || **HML 37T 0% '-4.68' + ATR-SL 38T 0% '-4.10'**
- 14d exits: TRAIL 202T 83.7% '+9.71' || ATR-SL 57T 0% '-6.31' + HML 43T 0% '-5.63' + cut-loser 13T '-1.92'
- 14d armed 202T 83.7% '+9.71' vs unarmed 201T 26.9% '-11.78'
- Never-armed concentration: jup 80T '-4.57' + vb- 18T '-2.19' = 98T of 201 (49%)
- 30d winner cells n>=10: pc+ EXTREME L 73T +1.44 · bb+ NORMAL L 44T +0.76 · vb- HIGH S 19T +0.42 · jup HIGH S 15T +0.40 · pc-,pc-v6- EXTREME S 10T +0.30 · pc- NORMAL L 29T +0.24

### 3. SHADOW (2/6 raw answerable + gate_shadow)
- contrarian join RE-RAN 20:30Z (mandate): overall flip 43.1% (W620/L820) | **pc- 64.6% n=350 LIVE keep** | rider do-NOT (chi2 p=8.9e-25 heterogeneous)
- floor join RE-RAN 20:50Z: floor_only 1385 49.2% vs always_admit 208 43.3% **p=0.118 COLLECT → 11-15**
- shadow_trader exit A/B: pm_trail +10,652 vs hard_max -12,140 (trail-or-nothing) · gate_shadow_health selfcheck PASS
- oscillator FROZEN/archived · wyckoff file GONE (retired) · rr ORPHANED

### 4. SIGNAL QUALITY — 0 kill candidates
- 14d n>=15 sub-50% WR + net<0 = **ZERO rows**. Closest: pc- LONG 29T 41.4% but net +0.24.
- jup LONG 100T 61.0% -1.08 and vb- SHORT 51T 62.7% -0.59 = WR-positive/negative-net = R:R class, no entry filter available (#228 pre-registered negative result stands).
- 24h losers n=7: all pass standing filters; RUNE LONG RSI 75.0 exactly on the 75 boundary (chasing) — n=7 < 20, RSI-bucket steering already rejected #128. No filter proposed.

### 5. READINESS (20:55)
**0 open — flat, 0 steers, portfolio good.** Regime: 15m SHORT_BIAS / 4h LONG_BIAS (disagreement = the chop) / continuum AT / vol LOW / velocity SLOW / accel NEGATIVE / wyckoff ACCUMULATION / market_phase RECOVERY. → No fresh counter-trend entries, trail-family first, size 1.0x (size-reduce file absent). Session lock ABSENT; CEO_PROTECTED 13/13; hermes_constants EMPTY git diff; checkpoint_registry 0 pending (9/9 done); 0 Tracebacks in pipeline.log.

**Queue:** 11-09 zombie-purge → 11-10 five bars + uninert next-100 read + fade-ctx fee-net re-measure → 11-11 HML post-ship re-read + watch-contrarian → 11-13 linreg-fade / chop-exempt / vb- clonehunt / pc+ kill-review → 11-14 neutral-exempt read + mult-150 CEO label chase + atrtrail + stop-tighten → 11-15 floor/wyckoff → 11-17 jup eval batch.
**CEO:** mult-150 label pending since 11-04 · 34 combo-weight divergences need precedence review · LOSERS/BLUR uncommitted diff (not mine) · NET-KPI.
