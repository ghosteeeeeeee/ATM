# Current State — brain_auditor #288 2026-11-22 04:45 UTC
**Last Updated: 2026-11-22 04:45 UTC**
**Updated by: brain_auditor #288. Prior: #287 2026-11-22 00:55 UTC (preserved in git history).**

## HEADLINE — THE WATCHDOG TOLD US TO DISABLE THE ONE SIGNAL THE NEW GUARD WAS SAVING. steer-002's 4-loss pump-chain+ streak was 100% prearm_lock breakeven caps (-0.01 each vs -0.110 for a real stop); root cause = collect_recent_closed never selected exit_reason, so streak steers were structurally blind to guard exits. Fixed at source, selfcheck + live-verified. 0 trading-constant changes.

1. **PREARM_LOCK_ENFORCE day-2 (change tracking): WORKING.** 10 exits since 11-20 01:26Z, realized avg -0.010 (min -0.030/max +0.010), all fires inside designed [0.25,0.40) pos-peak band. **INTERIM CAUTION: 90m candle reach-proxy 6/10 later touched +0.40 — reach != fk, n=10; full walk due 11-28** via NEW registry entry `prearm-enforce-day7-read` (deadline previously lived only inside a *done* disposition = drop risk, now surfaced).
2. **NEW MED SIDE-FIND — PEAK-SOURCE DIVERGENCE.** #17023 BLUR lock fired with pos-peak +0.40 while `trades.highest_price`=0.580 and 1m candle peak=0.834, trail=FALSE (ARM-GAP peakTrail@0.45=+0.13%); #17037 pos +0.38 vs stored 0.406 → **2 of 10 enforce exits have recorded MFE already in the ARM band.** Same class as #275 MED (IOTA). Guard proposal (skip lock when trades.highest_price >= arm) pre-registered inside the 11-28 entry — needs CEO even if bar trips.
3. **Steers 3/3 dispositioned:** steer-001 = window artifact (20-trade window -0.02 vs full 24h 29T 55.2% gross +0.61, net -0.05 fee-drag) · steer-002 = guard working (fixed text) · steer-003 = BTC manual_sl CEO-domain, 14d ai-trader SHORT 37T +0.46, tag-split due 11-24.
4. **Arm-rate tripwire NOT tripped this cycle:** mfe basis 7d LONG 48.6% (<50 limb, 7th window) / SHORT 54.5% (>55 FAIL by 0.5) — both legs required; advisory no auto-config.
5. **Kill screen 0 rows · AMPLIFY 0 new** (all 7 n>=10 30d winner cells in-flight; formal weekly + jup-long clone-hunt due 11-23). **Flip-KPI MET** (prearm enforce 11-20).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | **29T 55.2% gross +0.61, fees 0.57, NET -0.05** / 125T 48.8% gross +0.44, fees 1.95, **NET -1.50** |
| 14d / 30d | 228T 47.8% gross -0.91 · 653T 52.5% gross -3.37 |
| armed vs never | 7d armed 64T **82.8% +3.96** vs never 61T 13.1% -3.52 · 14d armed 117T 82.9% +7.25 vs never 111T 10.8% -8.16 |
| chop-bleed 7d | **90.5% dollar** (never-armed -3.79 of -4.19) — UNDER 92% gate |
| exits 14d | pm_trail 73T 95.9% **+4.46** ‖ atr_sl 32T 0% -3.47 · HML 26T 0% -2.74 · manual_sl 22T 0% -2.13 (CEO) · prearm_lock 10T 10% -0.10 (guard) |
| regime 7d | NORMAL 18T +0.11 · EXTREME 54T +0.82 · HIGH 53T -0.49 |
| kill screen 14d sub-50 n>=15 | **ZERO rows** (ai-trader LONG 11T / hl_copy LONG 11T both n<15 owned/external; ai-trader SHORT 37T 37.8% net POSITIVE) |

### 2. AUTOPSY (48h, recovery_replay adverse-first, ASSERT PASS)
n=19 = 5 never-adverse / 12 recovered / **2 NEVER** (IMX #17001 atr-trend- HML -0.12 · BLUR #17029 pc+ prearm -0.02) = never-armed chop class → **WRONG-SIDE REFUTED 139th** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (both mandate joins re-run)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 04:30Z** — overall flip **46.6%** (flipping loses) · pc-\|BELOW **62.7% n=51 HOLDS** · pc-\|AT 28.6% never blanket · rider chi2 p=4.6e-42 **per-signal only** |
| floor join | **RE-RAN 00:44Z** — floor_only 49.7% vs always 46.7%, **fisher p=0.2532** (not converging) → route stays CLOSED |
| shadow_trader | **131,234** signals — all gates block <=56% would-win, all avg-negative-EV; exit A/B **pm_trail +20,230** vs hard_max -26,296 / rr -9,486 / cut_loser -2,353 = **TRAIL-OR-NOTHING** |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + shadow_trader + 2 live collectors** |

### 4. DUE
**11-23** jup-long clonehunt + formal weekly AMPLIFY → **11-24** tag-split / brake-cf / gate-cross-tab / regime-tension → **11-25 WIN-CAPTURE READ** (n>=40, pace >= +$0.10/day, fk<20%) + bbsqueeze reband + structure-flip + watch-contrarian + pcfade + hotset-pin → **11-26** storm waiver + capture-leaderboard → **11-27** stop-family + linregfade + pc-weight → **11-28** maker-entry + **prearm-enforce-day7-read (NEW)** + jup-walk + dual-basis + conf-tilt + r2v2-clonehunt + reentry → **11-29** tape-at-long → **12-03** kill-line → 12-06 atr-trend-accel → 12-15 ugb-bypass.

### 5. CHANGES THIS RUN (both non-trading-behavior)
1. `scripts/trade_watchdog.py` — exit_reason in collect_recent_closed + prearm-streak guard note in the losing-streak steer + `--selfcheck` 3 fixtures PASS. Steer TEXT only; py_compile PASS; live-verified (steer-002 guard note, steer-003 unchanged).
2. `data/shadow_disposition.json` — registered `prearm-enforce-day7-read` (eval, due 2026-11-28): fk walk bar <20% (n>=15), realized net >=0, peak-source divergence census (>=2 fires with DB/candle >=0.40 → CEO guard proposal), units guard #193. Atomic write, selfcheck PASS.

### 6. LAST-RUN VERIFY (#287) — ALL PASS
rider-fade dispositioned done (NO FLIP holds) · win-capture open deadline 11-25 · capture-leaderboard open 11-26 · #286 stranded-entries guard selfcheck PASS · constants EMPTY · protected untouched · size-reduce absent = 1.0x · **0 Tracebacks** · checkpoint_registry only kill-line 12-03 pending · recovery_replay ASSERT PASS.

### 7. READINESS (2026-11-22 04:45 UTC)
**1 open — BTC SHORT #17043 ai-trader-pending @59623, SL 59664.6 / TP 56909, lev 10, +0.07, 1.4h, meta_rsi 38.27 — HOLD bracketed.** btc_15m SHORT_BIAS vs btc_4h LONG_BIAS **DISAGREE**, continuum BELOW, vol LOW, velocity SLOW, accel NEGATIVE, volume LOW, market_phase DECLINING vs trend_quality STRONG_UP → **sources disagree: hold the bracketed SHORT, NO fresh entries until aligned; trail-family first; LONGs only on pullback-to-structure WITH volume; SHORTs only with 4h aligned; size 1.0x.** Watchdog health 'critical' = the 3 dispositions above, 0 auto-executable steers.

**CEO owed:** **V6 kill RATIFY/VETO** · **rider-fade fk-limb (rec: keep shadow one more 14d read)** · **maker-entry lever ruling (NO-SHIP default)** · **prearm day-2 observation (6/10 reach-proxy, await 11-28 full fk).**
**Flip-KPI:** MET (prearm enforce shadow→live 11-20).
