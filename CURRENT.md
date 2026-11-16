# Current State — brain_auditor #271 2026-11-16 20:50 UTC
**Last Updated: 2026-11-16 20:50 UTC**
**Updated by: brain_auditor #271. Prior: #270 2026-11-16 12:51 UTC (preserved in git history).**

## HEADLINE — EXITSTACK KPI FORMAL READ PASSES BOTH LEGS (due-11-17 closed early); 0 CONFIG CHANGES

1. **exitstack-day-kpi-1114 → DONE, BAR MET.** Trailing-30 closes post-11-14:
   30 closes / 15 losers / **avg_loser -0.0687** vs bar **-0.070** = PASS (baseline
   -0.092 → -0.0687 = 25% loss-magnitude reduction). Second OR-leg ALSO passes:
   **14d unarmed -9.63 vs -13.81** = narrowed 4.18. Robust across 4 cut times
   (37 closes exist since 11-15). No failing leg, no revert flag.
2. **amplify-jup-short-high-cell → DONE, NO-SHIP.** Cell sign-flipped: 30d 25T +0.09
   but **14d 18T -0.28 / 7d 8T -0.06**. Bars: n>=15 PASS, net>0 PASS(30d only),
   jup share 9/50=18% PASS (was 44%), **same-sign FAIL**. Edge decay, not noise.
3. **#270 MED "freq_deviation orphan producer" RETRACTED (false positive).**
   Consumer chain verified end-to-end: jsonl + error_alerts.md (18 lines, last
   11-16 19:00Z) → ceo_dashboard_api.get_error_alerts (last-5 blocks) →
   ceo_dashboard.html. JSONL is 24h-dedup state, not an orphaned output.
   hl_copy OVER-fire 3.73× sustained — did NOT build a duplicate watchdog steer.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 11T 45.5% **-0.02** / 112T 47.3% -0.46 / 238T 50.8% -1.90 / 660T -4.86 |
| armed vs never 7d | ARMED 56T 85.7% **+4.10** vs NEVER 56T 8.9% **-4.56** |
| trail vs chop 14d | profit-monster 72T 95.8% **+4.23** · mfe_exit 26T 100% +1.51 vs atr_sl 42T 0% **-4.75** · hard_max 37T 0% **-4.21** |
| chop-bleed dollar | 7d **84.1%** / 14d 88.9% — under 92% gate both windows |
| steer-001 | ai-trader-pending 3-consec-loss ANSWERED — CEO manual pending, 14d net **+0.14**, NORMAL cell +1.12 → report only |
| arm-rate axis screen (#194 pre-reg) | 1 qualifier: hl_copy 15T arm 33.3% net -0.30 — **FAILS p<0.05 (fisher p=0.185)** → no dampen |
| sub-50% n>=15 (14d) | 0 kill candidates: hl_copy (CEO shadow live) + ai-trader-pending (CEO, net +) |

### 2. REJECTED WITH DATA
- **hl_copy arm-rate dampen:** fisher p=0.185 vs rest-of-system arm rate → noise.
- **freq-deviation watchdog steer (my own candidate):** consumer already exists
  (error_alerts → CEO dashboard) → building a second one = duplication.
- **jup SHORT HIGH size-up:** sign-flip (above) → NO-SHIP, closed.

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, --selfcheck exit=0): n=20 = 3 never-adverse /
  14 recovered / 3 NEVER** (HYPE jup -0.12, ALGO atr-trend- -0.11, ZRO hl_copy -0.01)
  = 15.0% structural → **wrong-side REFUTED 122nd consecutive run** (#61 p=0.116,
  #84 t=-0.04). 13/20 recovered = exit-side, not entry-side.
- **Contrarian join RE-RAN 20:31Z (mandate):** overall 45.9% n=1822 |
  **pump-chain- 68W/36L = 65.4% STABLE** (live fade holds) | rider 44.7% do-NOT |
  het p=4e-35 → per-signal only.
- **Floor join RE-RAN 20:34Z:** floor_only 49.5% n=1764 vs always 45.0% n=371,
  fisher p=0.1229, same_sign_30d FAIL → **#264 NO-SHIP stays CLOSED**.
- **shadow_trader 20:35Z:** 111,051 signals; exit A/B **pm_trail +16,760 (100%) vs
  hard_max -21,327 (0%)** → trail-or-nothing unchanged. Gates justified.
- oscillator FROZEN / wyckoff PENDING / rr ORPHANED → **3/6 answerable + freq chain
  verified.**

### 4. AMPLIFY (weekly offense)
0 NEW — **why-not: all 6 n>=10 net>0 30d cells already carry open amplify entries**
(ai-trader NORMAL SHORT→11-22 · bb-squeeze+ NORMAL→11-17 · vb- HIGH→11-20 ·
pc- NORMAL via watch-contrarian-live→11-18 · atr-trend- NORMAL · jup HIGH→closed
this run); early n=5-9 covered (pcv6/warrior/r2v2/jup-FLAT) or below +0.10.
**1 entry SERVED:** jup-short-high closed NO-SHIP. **Flip-KPI 0 this week** — why:
3 candidate shadows all SHIPPED 11-16 (deadlines 11-20/30 = too early); exitstack
KPI closed PASS; fade-ctx-exempt converted 11-09 20:55Z = 7d1h ago, just outside.

### 5. LAST-RUN VERIFY (#270)
- **exposure KPI PASS** — present at 20:38Z: {24h, 11.8% in-market, 12 trades}
  (was 32.8% at 12:51 — exposure dropped with the quiet tape).
- **COPY-STALE guard PASS** — 3/3 post-fix <5s phantoms logged (17:44/18:27/18:29Z,
  all ZRO hl_copy), log-only, phantoms netted +0.05.
- **slippage BUILD #1 RESOLVED** by main-session 11-16 — `exit_slippage_pct`
  GENERATED column live; atr_sl_hit 30d avg 0.1093% n=110 reproduces exactly.
- entry_feature_split selfcheck sample-shrink: still open (carried).
- constants EMPTY diff · CEO_PROTECTED 13/13 · session lock absent · size-reduce
  absent = 1.0x · 0 Tracebacks in pipeline.log · recovery selfcheck exit=0.

### 6. DRIFT / SIDE-FINDs
- **RESOLVED:** #270 freq-orphan MED (retracted above) · slippage BUILD #1 (shipped).
- **MED (carried):** entry_feature_split sample-shrink · wyckoff join unbuilt.
- **LOW (carried):** session_brain duplicate-text rebuild.

### 7. READINESS (20:50Z)
**0 open / FLAT — correct.** Last trade ZORA bb-squeeze+ LONG #16950 closed
20:44:34Z **profit-monster-trail +0.02, mfe 0.551 ARMED, 13.4m** — trail won again.
Regime (watchdog 20:38Z): 15m NEUTRAL vs 4h SHORT_BIAS + continuum ABOVE + vol LOW
+ velocity SLOW + market_phase DECLINING + trend STRONG_UP = **mixed, chop pin
stands** → no fresh counter-trend entries; trail-family first; size 1.0x; LONGs only
on a sustained 15-30m reclaim WITH volume; SHORTs only under EMA300 with 4h aligned.

**Queue:** **11-17** jup batch (atr_sl 15T -1.99 = #1 bleed) + **12 due-11-17
dispositions** (jup-trail, jup-atrsl, short-regime-exempt, flip1-bear-reshadow,
bear-single-source, volgate-short-exempt, maxxed-short-exempt, long-bypass-regime,
jup-cluster-gate, jup-anti-chase, jup-pro-selection, btc-standalone-deny,
setup-recall) | **11-18** watch-contrarian-live + xmirror-giveback + jup-long-flat +
grind-breakout-underdeploy + pcfade-windowfix | **11-19/20/21/22** batches |
**11-30** hl-copy-plus adjudication (report freq-ratio 3.73× beside WR) |
CEO: slippage BUILD #1 **CLOSED** · LONG arm tripwire (7d 49-52% borderline) ·
NET-KPI.
