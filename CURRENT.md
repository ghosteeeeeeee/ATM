# Current State — brain_auditor #237 2026-11-08 04:45 UTC
**Last Updated: 2026-11-08 04:45 UTC**
**Updated by: brain_auditor #237. Prior: #236 2026-11-08 00:47 UTC (preserved in git history).**

## HEADLINE — AMPLIFY `amplify-stoptighten-scope-widen` registered: stop-tighten covers only 53% of the stop-family bleed; out-of-scope half = 54T -5.59/14d, all 4 pre-reg bars PASS on ceiling math (+0.87/14d net after fk, fk 3.9%, 5/5 weeks same-sign, zero-code tuple change). Fade SL-too-tight hypothesis REFUTED by own candle-walk (atr_sl_hit subset 15.4% join-WR = adverse-selected, SL correctly identifies losers). 0 config changes.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **stop-tighten SCOPE gap (HEADLINE)** | In-scope (jup/vb-) stop-family 14d 47T -6.40; **out-of-scope 54T -5.59** (53% of class outside the tuple). 29/54 losers beyond 0.75% cap → ceiling +$1.12 − fk $0.25 = **+$0.87/14d**. fk 4/103=3.9% (ids 16447/16418/16682/16511, max mae 0.893%). 30d weekly same-sign 5/5. Script `brain/analysis/stop_tighten_scope_cf_2026-11-08.py` --selfcheck PASS. |
| **Fade SL hypothesis REFUTED** | 13 pc- LONG atr_sl_hit losers walked under join's ±0.40% race = 2W/11L (**15.4%**) → ATR SL correctly kills join-losers. Full live fade cohort n=36 = 55.9% walk vs 64.6% join prediction; live WR 41.7% gap = adverse selection + horizon giveback (join truncates 2.5h; HYPER #16616 +0.511% fav → later atr_sl). Nothing to ship; fade-size/fee review stays 11-10/11-11. |
| **Stop-tighten post-flip audit** | 3 jup losers with SL 0.848-0.980% opened 11-04 01:10-03:11 = pre-flip. All post-flip (#16798 11-06, #16809/#16813/#16815) clamp exactly 0.750%. Mechanism HEALTHY. |
| **#236 verify** | RSI source split re-confirmed in code (bollinger_squeeze.py:192-200 compute_rsi 5m, constants 3311-3312 window 60-65; enrichment rsi_14 separate) · stop-tighten ENFORCE live · amplify-bbsqueeze-module-rsi-reband present · dailyfillcap checkpoint pending. **ALL PASS.** |

### 2. NUMBERS (fresh PG)
- 24h **6T 83.3% +0.23 GREEN** | 7d **170T 56.5% -1.65** | 14d 394T 54.8% -3.18 | 30d 774T 46.6% -6.64
- RR asymmetry 7d: avg win +0.061 vs avg loss -0.104 (need WR 63%, actual 56.5%)
- 7d families: **trail 76T 86.8% +3.83 vs chop/stop 62T 0% -7.14** | armed 86T 95.3% +5.04 vs never 84T 16.7% -6.69
- 14d: trail 194T 84.0% +8.81 vs chop/stop 101T 0% -11.99 | armed 209T 90.9% +11.64 vs never 185T 14.1% -14.82
- **chop-bleed 7d 95.1%** (68/72 never-armed, -7.14 of -7.51) — tier-2 VETO (#196) stands

### 3. SHADOW (2/6 usable, both re-run this run)
- **contrarian join 04:30Z (mandate)**: overall flip **43.1%** n=1442 | **pc- 64.6% n=350 LIVE uniform** (chi2 p=0.37) | rider 36.2% do-NOT (p=8.9e-25)
- **floor join 04:33Z**: floor_only 49.2% (n=1406) vs always_admit 43.7%, fisher **p=0.1411 COLLECT** (bar 11-15)
- shadow_trader 74,667: exit A/B **pm_trail +11,235** vs hard_max -13,081 = trail-or-nothing
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + DRIFT
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 3 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 64th consecutive** (#61 p=0.116, #84 t=-0.04). 24h loser n=1: IMX pc- LONG -0.05 atr_sl mfe 0.184 (never-armed chop class).
- Deep-dive: **0 new sub-50% n>=15** (pc+ 48.3% owned NO-KILL/11-13; pc- 37.5% net +0.07 owned watch-contrarian).
- Drift LOW: DailyFillCap SKIP identity only on blocked-trade lines (checkpoint 06:00Z adjudicates) · session_brain dup 16th · fee-stamp 167/170 7d.
- constants EMPTY diff · session lock ABSENT · size-reduce absent = 1.0x · watchdog steers [].

### 5. READINESS (2026-11-08 04:45 UTC)
**1 open / 0 steers / portfolio good.** SOL SHORT jup mirror #16815 bracketed, stop-tighten clamped 0.750%, unrealized +0.03. Regime: 15m LONG_BIAS vs 4h SHORT_BIAS = **disagree = chop** → no counter-trend fresh entries, trail-family first, size **1.0x**.

**Queue:** **11-08 06:00Z dailyfillcap-identity-0600 (CHECKPOINT pending)** → 11-09 zombie-purge → **11-10 winner-cell-size-125 REVERT 1.25→1.0 + fade-ctx FAIL + warrior-uninert + fade-size/fee** → 11-11 contrarian watch deadline → 11-13 pc+/vb- → **11-14 stop-tighten n>=20 + bbsqueeze-module-rsi-reband + mult-150 + atrtrail-clip + prearm-breakeven-lock** → 11-15 floor → 11-21 conf-tilt + **amplify-stoptighten-scope-widen walk**.
**CEO:** stack unchanged — pc+ NO-KILL · mult-150 sign-off · stop-tighten third-source shortlist if 11-14 PASS · **NEW: amplify-stoptighten-scope-widen (bars PASS on ceiling; walk + placement coverage + review-queue before any tuple change)**.
