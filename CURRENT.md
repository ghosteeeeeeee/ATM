# Current State — brain_auditor #222 2026-11-05 00:55 UTC
**Last Updated: 2026-11-05 00:55 UTC**
**Updated by: brain_auditor #222. Prior: #221 2026-11-04 21:10 UTC (preserved in git history).**

## HEADLINE — UGB-PT bypass-skip hole root-caused (hl_copy armed rides +3.6% peaks into hard_max_loss) → pre-registered, population-capped. ARM-GAP units-label fix shipped (3rd #193 landmine sighting). 0 trading-constant changes.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **UGB-PT bypass hole (NEW, MED)** | `position_manager.py:4267 _is_bypassed` (commit c384a2d5, 2026-10-31) skips UGB-PT ENFORCE for everything in `PROFIT_MONSTER_BYPASS_SIGNALS`. That list conflates **"another engine trails it"** (pump-chain → pump_exit) with **"nobody trails it"** (`hl_copy_trader`). Result: hl_copy armed trades get neither PM trail (bypass by design) nor UGB-PT (skipped) = **zero giveback protection**. Proof: XPL #16731 MFE **3.68%** → pg_pnl_pct **-2.90** (CF peakTrail +3.21%), FARTCOIN #16739 MFE **3.64%** → **-3.71** (CF +3.17%), both 17h holds, trail=FALSE, exit hard_max_loss. UGB-PT `[SHADOW] would-fire` DID log them (PONS #16754 repeatedly) — enforce only. 30d cohort (bypassed, mfe>=0.40, stop exit): **n=8 actual -0.43 vs peak-0.45 CF +1.10 = +1.53 gross** (hl_copy 6T +1.15). **n=8 < 20 → NOT shipped.** Registered `amplify-ugb-bypass-hole` (deadline 2026-12-15, default NO SHIP, **population-capped: all bypassed families = 26T/30d**). Also falsifies the 10-25 claim "escalation #17 closed — UGB-PT IS the universal post-arm floor". |
| **ARM-GAP units/temporal mix (FIXED, bug-hunter audited)** | The `[ARM-GAP]` line pairs `peakTrail@` (UNLEVERAGED price-move %) with leveraged `pnl=`, and that `pnl=` is the **close-time commit** which `hl_sync_guardian._backfill_hl_pnl_recent_closes` (`hl_sync_guardian.py:563`) rewrites ≥30s later with HL-fill ground truth — XPL #16731 close-time **-4.15 → PG -2.90**, FARTCOIN #16739 **-5.30 → -3.71** (~43%). **SHIPPED** log-only fix: SELECT adds `pnl_pct`, line appends `pg_pnl_pct=` as the **close-time baseline** (None→NA) so the backfill delta is measurable from the log alone, + units comment. py_compile PASS; self-check reproduces XPL pg -2.90 / peakTrail +3.21; no parser consumed the old format. **bug_hunter: 0 CRITICAL/HIGH, 1 MEDIUM (first comment misattributed the cause to 'local vs committed' and the field looked tautological) + 1 LOW (NULL→+0.00) — both fixed.** |
| amplify-winner-cell-mult-150 | **STILL MET** at 00:45Z re-read (net30 all 4 >0: 1.45 / 0.73 / 0.42 / 0.78; net14 3/4 >0 with pc+ exactly 0.00; net7 set **+0.34**) — still **AWAITING CEO label + T sign-off** (money-sizing #208). Note bb-squeeze+ NORMAL 7d drifted to -0.07 (set still positive, revert bar not tripped). |
| fade-btc-crash-postflip | deadline moved 11-05 → **11-06**; preliminary 24h read: **1 unique event** (ANIME), `coherent=NO` → **default KEEP pre-flip behavior** stands; full read 11-06. |
| AMPLIFY weekly screen (Wed, light) | 30d n>=10 net>0 = 7 cells, **identical set to #220/#221**; all VALIDATED / why-not'd / in-flight. **1 NEW proposal emitted** (amplify-ugb-bypass-hole above). Flip-KPI: 0 new conversions (in-flight watch-contrarian 11-11, fade-ctx + winner-cell-125 11-10, harvest 11-07, xmirror 11-18). |
| TAT peak-guard re-count | 14d trail_arm_timeout exits **49, mfe>=0.40 = 11** (7d: 31 exits / 7) → **still n=11 < 20, bar NOT met**, keep collecting. |

### 2. NUMBERS (fresh PG)
- 24h **27T 55.6% gross '-0.12'** | 7d **277T 54.5% gross '-1.82'** | 30d 785T 45.4% '-6.11' | 11-04 daily 29T 55.2% '-0.14'
- 7d **armed 144T 91.0% '+8.66'** vs **unarmed 133T 15.0% '-10.48'** | never-armed = **90.0%** of 7d gross loss (104/113 losers mfe<0.40)
- 7d trail_family 179T 82.7% '+9.03' vs chop_stop 85T **0%** '-10.33' (hard_max 37T -4.73 · atr_sl 39T -4.28 · cut-loser 8T -1.25) | 14d chop_stop 114T 0% '-13.85' vs other 292T 76.4% '+11.82'
- Contrarian join **re-ran 00:30Z** (mandate): overall 44.1% n=1341 | pc- 226W/124L **64.6% LIVE** | rider 625L/365W **36.8% do-NOT** | pc- chi2 p=0.3747 uniform
- shadow_trader --report: CONFLUENCE-EXPIRY 15262 blocked @47% avg -0.13 · exit A/B pm_trail +9499 vs hard_max -10761

### 3. AUTOPSY + DEEP-DIVE
- **48h adverse-first n=30 = 7 never-adverse / 23 recovered / 0 NEVER → WRONG-SIDE REFUTED 76th** (#61 p=0.116, #84 t=-0.04)
- **14d sub-50% n>=15 = pump-chain- only** (30T 40.0% but **net +0.32** = positive, not a bleed; fade/CONF_FLOOR-owned). **0 new targets.**
- **R:R-class (owned, not new):** jup 14d 127T 60.6% '-1.18' (avg win +0.063 / avg loss -0.121 → breakeven WR **65.8%** vs 60.6%); vb- 58T 60.3% '-0.89' (0.054/-0.121 → breakeven **69%** vs 60.3%, cut-loser 8T '-1.13' is the drag). → jup regime review 11-07 · vb- stop-tighten/validated HIGH cell.

### 4. LAST-RUN VERIFY (ALL PASS)
#220 dedupe selfcheck PASS (raw=27 dedup=18 p=0.1189) + file was **UNTRACKED** → committed this run | #219 guardian PID 3978501 running since 04:43:44 HOLDING | #218 disposition timer `OnCalendar=*-*-* 08:15:00` active | constants **EMPTY** diff vs HEAD | CEO_PROTECTED **13/13** | session lock absent | size-reduce absent = 1.0x | 0 Tracebacks in pipeline.log | recovery_replay selfcheck PASS | checkpoint_registry 9 entries **0 pending**.

### 5. READINESS (00:55)
**0 open — flat.** BTC #16787 closed 23:46Z mfe_exit +0.05 (MFE never armed, exited on the mfe_exit path). Watchdog: 0 steers, portfolio good, auto_trader CHOP with BRACKET armed both ways (long +5 / short -15). Regime: btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** (disagree — cite sources), continuum **ABOVE**, vol NORMAL, velocity SLOW, market_phase DECLINING, trend_quality STRONG_UP. Size 1.0x; no fresh entries while 15m/4h disagree.

**Queue:** 11-06 fade-btc-crash full read + coverage batch + harvest first read → 11-07 harvest full + jup regime review → 11-09 zombie-purge + timer 08:15Z → 11-10 fade-ctx / winner-cell-125 / bear-single-source / probe-080 label → 11-11 watch-contrarian → 11-13 pc+ kill-review → 11-14 stop-tighten + atrtrail-clip-12 → 11-15 floor/wyckoff joins → 12-15 amplify-ugb-bypass-hole.
**CEO:** winner-cell-mult-150 sign-off (**MET twice consecutively**) · stop-tighten-probe-080 label · NET-KPI switch · hail-mary brief answers.
