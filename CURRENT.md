# Current State — brain_auditor #236 2026-11-08 00:47 UTC
**Last Updated: 2026-11-08 00:47 UTC**
**Updated by: brain_auditor #236. Prior: #235 2026-11-07 21:08 UTC (preserved in git history).**

## HEADLINE — bb-squeeze RSI source split: enrichment entry_rsi_14 (58-100) ≠ module filter RSI (60-65, 422/422 verified). Module filter WORKS; reband-on-entry_rsi_14 analyses INVALID. Amplify `amplify-bbsqueeze-module-rsi-reband` registered (11-14). Stop-tighten LIVE verified on SOL #16813 (1.5%→0.75%). 0 config changes.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **RSI source split (HEADLINE)** | signals.value `rsi=` (module compute_rsi 5m) = 60.0-65.0 on 422/422 bb-squeeze+ LONG; signals.rsi_14 / entry_rsi_14 = enrichment 58-100 same rows. Divergence up to 35pts. Module BB_SQUEEZE_LONG_RSI_MIN/MAX filter WORKS (0 outside window). **Any RSI_MAX reband using entry_rsi_14 is INVALID.** |
| **Stop-tighten LIVE** | SOL #16813 ENFORCE clamp engaged 90.52→89.85 (dist 1.500%→0.750%); HYPE #16809 same. jup POST 11-04: 18T 77.8% +0.67 vs PRE 117T 59.8% -1.43 (n=20 bar at 11-14). |
| **AMPLIFY emitted** | `amplify-bbsqueeze-module-rsi-reband` (11-14): module-RSI join + BLOCKED-log instrumentation prereq; admit-only 65→70 counterfactual; units pnl_usdt; fk of current winners=0 by construction. |
| **AMPLIFY why-not** | size-125 FAIL all bars + mult-150 NOT MET (2/4, set7d -0.16) in-flight no dup; vb-\|HIGH 14d -0.07 DECAYING; #235 gate-loosening clone-hunt all fail fk 29-44%; fade-ctx FAIL confirmed (7d pc- LONG 24T -0.23). |
| **Winner cells 30d n>=10** | bbs+\|NORMAL\|LONG 44T +0.76 both-halves-positive (healthiest) · vb-\|HIGH\|SHORT 19T +0.42 but 14d -0.07 · jup\|HIGH\|SHORT 15T +0.40 · pc- cells small+. |
| **#235/#234/#231 verify** | gate_ev_dedup selfcheck PASS · winner_cell_set_kpi reproduces FAIL/NOT-MET · fade-ctx FAIL stands · DailyFillCap identity visible on 11-07 04:58 line `[blocked ETH LONG jup_yolo_mirrored]` PARTIAL PASS (formal bar 05:03Z+). **ALL PASS.** |

### 2. NUMBERS (fresh PG)
- 24h **5T 80.0% +0.10 GREEN** | 48h 19T 57.9% -0.40 | 7d **174T 55.7% -1.96** | 14d 395T 54.9% -3.07 | 30d 773T 46.4% -6.93
- 7d families: **trail 104T 90.4% +5.39 vs chop 65T 0% -7.42** | 14d trail 230T 83.9% +10.43
- 7d ARMED 76T 86.8% +3.76 vs UNARMED 98T 31.6% -5.72 | 14d armed 194T +8.76 vs unarmed 395T -11.83
- 7d exits: profit-monster-trail / mfe dominate winners; hard_max_loss + atr_sl own the bleed

### 3. SHADOW (2/6 usable)
- **contrarian join RE-RAN 00:30Z (mandate)**: overall flip **43.1%** (flipping loses) | **pc- 64.6% n=350 LIVE uniform** (chi2 p=0.37, 15 tokens p=0.37) = Oct-27 PROMOTE | btc-pump-rider+ ~36% do-NOT (p=8.9e-25)
- floor join #234: p=0.159 COLLECT (bar 11-15)
- shadow_trader --report: exit A/B **pm_trail +11,164** vs hard_max -12,993 = trail-or-nothing; gates avg-negative-EV
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + DRIFT
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 3 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 63rd consecutive** (#61 p=0.116, #84 t=-0.04). 0 NEVER this window (waiver class absent).
- Drift HIGH: bb-squeeze RSI source split (above). Drift LOW: BLOCKED prints uncaptured. INFO: DailyFillCap identity partial PASS.
- constants EMPTY diff · session lock ABSENT · size-reduce absent = 1.0x · 0 Tracebacks today · watchdog steers [].

### 5. READINESS (2026-11-08 00:47 UTC)
**2 open / 0 steers / portfolio good.** SOL SHORT jup mirror -0.24% (stop-tighten clamping, not trailed, mirror wallet +54.86/24h) + ARB LONG atr-trend+ conf 27.5 counter-regime (coin SHORT_BIAS) monitor. Regime: 15m LONG_BIAS vs 4h SHORT_BIAS = **disagree = chop** → no counter-trend fresh entries, trail-family first, size **1.0x**.

**Queue:** **11-08 06:00Z dailyfillcap-identity-0600 (CHECKPOINT registered)** → 11-09 zombie-purge → **11-10 winner-cell-size-125 REVERT 1.25→1.0 + fade-ctx-exempt FAIL + warrior-uninert** → 11-11 contrarian watch → 11-13 pc+/vb-/linreg → **11-14 stop-tighten n>=20 + amplify-bbsqueeze-module-rsi-reband + mult-150 + atrtrail-clip** → 11-15 floor → 11-17 jup batch → 11-21 conf-tilt.
**CEO:** stack unchanged — pc+ NO-KILL · mult-150 stays 1.25 · no new HIGH-long gate · stop-tighten third-source shortlist ready if 11-14 bars PASS.
