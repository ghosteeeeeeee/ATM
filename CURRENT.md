# Current State — brain_auditor #285 2026-11-21 08:55 UTC
**Last Updated: 2026-11-21 08:55 UTC**
**Updated by: brain_auditor #285. Prior: #284b 2026-11-21 04:50 UTC (preserved in git history).**

## HEADLINE — FEES ARE 158% OF GROSS. 7d gross flipped POSITIVE (+1.13) but fees 1.787 → net -0.66; 30d gross -6.82 / fees 7.164 / net -13.98. The maker/ALO fee lever exists in code, is used ONLY by the manual CLI, and the pipeline still sends taker Market — measured worth +$1.62/14d. New amplify registered, NO-SHIP default.

1. **Fee-axis finding (this run's offense):** `decider_run.execute_trade` → `brain.py:414` default `order_type="Market"` (0 `order_type` hits in decider_run) while `hyperliquid_exchange.py:1099-1238` supports `Limit` + `tif='Alo'` and `brain.py:1625` exposes `--order-type Limit`. Session prior art [Build New Linear Regression Signal, 2026-10-29] identified taker 0.09% RT vs maker 0.03% RT — built as a manual flag, never wired, 23 days idle.
2. **FILL-WALK (14d n=209, candles_1m proxy: post-only at entry fills iff price revisits entry):** fill 74.2%/82.3%/86.6% @1/3/5m · filled 172 (notional $2287.61, fee $2.677) → save +$1.37/14d · missed 37 net **-0.25** (skipping helps) · **net_cf +$1.62/14d (~+$3.5/30d ≈ 25% of the 30d net bleed)** · halves same-sign +1.09/+0.53 · fk 11.3% $ / 17-18% count. **Registered `amplify-maker-entry-fill-walk` (11-28, DEFAULT NO SHIP)** — outstanding bars: ALO-retry rule (no double-fire) + CEO sign-off (money path). Caveat: fill proxy is best-estimate, not measured fills.
3. **Rider-fade 'DEAD' side-find (#283/#284b) RETRACTED — wrong-file grep.** 138 [RIDER-FADE-SHADOW] lines live in `/var/www/hermes/logs/signals.log` (381MB); `/root/.hermes/logs/signals.log` is a SECOND live file (mtf_macd + signal_confluence). Enforce limb run: lines 138 ✓, blocked net -0.28 ✓, **fk 3 live winners ✗ → NO FLIP, stays shadow**, thr 0.10 keeps. Rider-LONG disable follow-on NOT opened (n=12 < 20). **Ship: path NOTE at `scripts/signals/btc_pump_rider.py:37`** (py_compile PASS).
4. **AMPLIFY served: ai-trader-pending NORMAL SHORT cell → NO-SHIP** (replication FAIL 11-16 week 2T -0.14 vs 11-09 week 22T +1.36; 26/26 BTC FAIL; 77% at HL floor FAIL). Cell stays alive (30d 26T +1.30), RE-READ 12-05, CEO owner. win-capture: collector LIVE (12 lines), capture 0.600/0.581 vs bar 0.70 → COLLECT to 11-22. Flip-KPI MET this week (prearm enforce live 11-20).
5. **0 trading-constant changes of my own** — session lock absent; CEO_PROTECTED untouched; size-reduce file absent = 1.0x; V6 kill (#284) holding, CEO RATIFY/VETO still owed.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | 16T 56.3% **+0.52 gross** / 113T 50.4% **+1.12 gross → -0.66 net-of-fee** |
| 14d / 30d | 209T 48.8% -0.84 (net -4.02) / 635T 53.1% -3.07 (net **-13.98**) |
| arm gap 7d | armed 59T 84.7% **+4.73** (net +3.57) vs never 54T 13.0% **-3.61** (net -4.23) |
| **RR asymmetry** | 7d avg win **+0.1004** vs avg loss **-0.0939** = payoff **1.07** → breakeven WR ~48% vs actual 50.4% = **FLIPPED favorable** (loss-size no longer the lever; fees are) |
| chop-bleed $ | 7d 83.0% UNDER gate · 14d 88.4% · **30d 92.2% AT tripwire** (route CLOSED → MONITOR) |
| 14d families | pm_trail 66T 95.5% **+3.89** + mfe_exit 16T 93.8% +0.93 \|\| atr_sl 31T 0% -3.37 + hard_max 25T 0% -2.64 + manual_sl 19T 0% -1.84 (CEO domain) |
| regime 7d | NORMAL 23T 65.2% +1.60 · EXTREME 39T 48.7% +0.45 · HIGH 51T 45.1% -0.93 |
| kill screen | 14d sub-50 n>=15 net<0 = **0 rows** |
| atr-trend- (watchdog-routed) | EXIT IS NOT THE BUG — armed 28T 100% +1.42 vs never 20T 10% -1.78; NO KILL / NO NEW GATE |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
n=10 = 0 never-adverse / 8 recovered / **2 NEVER** (GOAT r2v2-long7 CL-T1 mfe 0.000 · IMX atr-trend- HML mfe 0.096) = never-armed chop class → **WRONG-SIDE REFUTED 136th** (#61 p=0.116, #84 t=-0.04). 3 BTC ai-trader SHORT manual_sl losses 11-20 were shorting the 55.7k→58.3k pump; we took the LONG side at 06:44 and closed green (BTC +0.20, XPL +0.07).

### 3. SHADOW (mandate re-runs done)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 08:30Z** — overall flip 47.1% n=2155 (flipping loses) · pc-\|BELOW 64.6% n=48 HOLDS · pc-\|AT 28.6% never blanket · rider chi2 p=8.4e-41 per-signal only |
| floor join | 04:31Z p=0.1688 → route CLOSED 11-15, MONITOR |
| rider-fade | **138 lines (path root-caused)** · walk: bar triplet FAIL on fk → NO FLIP |
| win-capture | 12 lines live since 11-20 19:08Z · capture 0.600/0.581 vs 0.70 → COLLECT |
| shadow_trader | 127,948 — exit A/B pm_trail **+19,575** vs hard_max -25,306 vs rr -9,422 = TRAIL-OR-NOTHING; all 11 gates negative-EV |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable** |

### 4. DUE 11-22 (read 15h early)
rider-fade **early FAIL-fk → deadline read is fk-only** · win-capture **COLLECT (0.60 vs 0.70)** · ai-trader cell **DONE NO-SHIP** (bars i/ii/iii fail on substance). Daily `hermes-shadow-disposition.timer` (08:15Z) surfaces the two still-open ones tomorrow.

### 5. AMPLIFY (1 new) + WHY-NOT
**`amplify-maker-entry-fill-walk`** (fee axis — see §HEADLINE). Why-not winner cells: all 6 30d n>=10 net>0 cells in-flight or disposed (ai-trader 26T +1.30 → NO-SHIP, bb-squeeze+ 39T +0.66 → 11-25, vb- 20T +0.49 → clone-hunt, atr-trend- 17T +0.26 → accel 12-06, jup 27T +0.22 → walk 11-28, pc- 31T +0.15 thin); n>=5 net>0.5 = 0 rows. **Flip-KPI: MET this week (PREARM_LOCK_ENFORCE shadow→live 11-20 01:26).**

### 6. LAST-RUN VERIFY (#284b/#284) — ALL PASS
V6 kill holding (0 v6 trades/7d, CEO ratify owed) ✓ · bb-squeeze BLOCKED hermes_log lines flowing (234) ✓ · STOP_TIGHTEN_SOURCES 2-tuple (:761) ✓ · PREARM n=4 all mfe 0.251-0.297 net 0.00 ✓ · constants EMPTY ✓ · 0 Tracebacks ✓ · checkpoint_registry only kill-line 12-03 ✓ · size-reduce absent = 1.0x ✓.

### 7. READINESS (2026-11-21 08:50 UTC)
**0 open / 0 steers / portfolio good — FLAT = CORRECT** (both 07:17 open longs closed green). Regime: btc_15m **SHORT_BIAS** + btc_4h **SHORT_BIAS** agree, but **continuum ABOVE EMA300** (since 06:44) disagrees, BTC flip rate 29/24h ≥ p95 = **UNSTABLE TAPE**, vol LOW, velocity SLOW, trend STRONG_DOWN, market RECOVERY, BTC meta_rsi ~90 extended → **no fresh counter-trend entries while sources disagree; no LONG into the extended pump; SHORT only on bounce to RSI 45-55 (never ≤35 post-dump); trail-family first; size 1.0x; re-check when 15m and continuum agree.**

**Queue:** **11-22 00:00Z** rider-fade formal deadline (fk only) + win-capture deadline (0.70) → **11-23** jup-long clonehunt + formal weekly AMPLIFY → **11-24** tag-split / gate-cross-tab / brake-cf / regime-tension → **11-25** structure-flip probe + bb-squeeze ceiling events + watch-contrarian + pcfade + hotset-pin → **11-26** storm waiver → **11-27** stop-family entry-filter (CEO Phase2) + linregfade + pc-plus-weight → **11-28** PREARM fk re-measure + conf-tilt + r2v2/jup-walk/reentry + dual-basis + **MAKER-ENTRY FILL WALK deadline** → 12-03 kill-line · 12-06 atr-trend-accel · 12-15 ugb-bypass.
CEO: **v6 kill RATIFY/VETO (one-line revert)** · **maker-entry lever (NO-SHIP default)** · prearm first-read ACK. Flip-KPI: MET (prearm).
