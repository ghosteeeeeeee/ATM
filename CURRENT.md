# Current State — brain_auditor #287 2026-11-22 00:55 UTC
**Last Updated: 2026-11-22 00:55 UTC**
**Updated by: brain_auditor #287. Prior: #286 2026-11-21 16:55 UTC (preserved in git history).**

## HEADLINE — LOSS-SIZE IS HARVESTED; THE RESIDUAL IS AN ENTRY-QUALITY GAP. Both past-due 11-22 dispositions read and dispositioned; 0 trading-constant changes.

1. **Structural read (this run):** fee-inclusive breakeven WR vs actual — 30d 66.5% vs 52.7% (gap **13.8pt**) → 14d 61.2% vs 48.5% (12.7pt) → **7d 57.9% vs 48.4% (9.5pt)**. The gap closed on the *loss* side: payoff (avg win / avg loss) recovered **0.73 → 0.91 → 1.05**. Fees = 0.0155/trade = 18% of an average win; 7d gross `+0.50` − fees `1.917` = net `-1.42`. **Direction: steer new work to chop/entry quality (the mandate), not a fourth exit-tightening pass.** Drift note recorded: **PG `pnl_usdt` is GROSS of fees** — net = `pnl_usdt − (fees::jsonb->>'fee_total')::numeric`.
2. **rider-fade enforce-read (due 11-22) → NO FLIP, stays shadow.** lines **204** (bar 15 MET), blocked_net `-0.25` **MET**, live_n 22 / blocked 10, **fk_live FAIL = 4 blocked live winners [16921, 16895, 17017, 17021]** + review-queue signoff absent. Threshold walk: **keep 0.10** (no adjacent threshold beats it in both split-halves same-sign; fk 42–67% everywhere). **NEW: #280's aging caveat REFUTED** — CHIP/ARB aged out and were replaced by two FRESH 11-21 winners (#17017 `+0.07`, #17021 `+0.03`), so the FAIL is not a stale-window artifact. **#282 follow-on NOT opened**: rider LONG 30d n=22 (≥20) but **WR 59.1%** (condition was WR<40%). **CEO: fk limb wants 0 winners while net-EV reads `-0.25` (blocking IS net-positive, 4/10 = 40% fk) → captain rec: keep shadow one more 14d read, do not relax unilaterally.**
3. **win-capture (due 11-22) → COLLECT EXTENDED to 2026-11-25.** 19 raw lines → **8 distinct trade_ids**, all joined to PG. 1m giveback walk (hyp20 vs actual exit, `pnl_usdt` units, #193) = **+0.2609 / 3 days = +0.0870/day vs the +$0.10/day bar (0.87× NOT MET)**, improved **7/8** (only HYPE #17039 `-0.0121`), **fk 0%**, mean capture at live exit 0.549 (baseline 0.57, bar 0.70), **cohort_b (whatif-only additional captures) = 0**. Read bar at 11-25: n≥40 AND pace ≥ +$0.10/day AND fk<20%. `PM_TRAIL_DISTANCE_PCT` leg stays CEO_PROTECTED.
4. **Watchdog triage 2/2.** steer-001 pc+ = REAL streak, below every bar: 24h 6T 0% `-0.13`, 14d 7T 0% (kill n=20 unreachable), 30d 39T 41% `-0.51` **binom p=0.168 n.s.**, last win 10-30 then **12 straight losses 10-31..11-21 net `-0.53`**, all-time 187T 74W **`+2.29'** → **MONITOR, disable = noise-trading**; blind-spot pre-registered as creative **C3** (review-packet trigger, not auto-kill). steer-002 ai-trader-pending = NO ACTION (14d SHORT 37T net `+0.46`; LONG 11T 18.2% n<20, CEO-domain; `manual_sl_hit` 22T 0% `-2.13` = top pure-loss bucket, all CEO BTC).
5. **Four candidates TESTED AND REJECTED-WITH-DATA (0 config changes of my own).** atr-trend- NORMAL-only gate (30d fisher **p=0.2137**, good-cell n=17<20, would block 17/31 winners) · volume-buildup- NORMAL SHORT gate (30d 13T 38.5% `-0.80` = largest single-cell bleed BUT **p=0.0627**, n=13<20, **DORMANT: 0 trades in 14d and 7d**) · burst/concurrency cap (30d burst n=95 WR 52.6% reach40 54.7% vs single n=557 WR 52.8% reach40 53.1% = **identical entry quality**; prior art `JUP_YOLO_MAX_OPEN_SHORTS` / `PUMP_FLOW_MAX_POSITIONS`) · time-based stall exit (**14d unarmed losers median hold 38min vs armed winners 39min = hold time does NOT separate them**; reproduces #244 TAT NO-SHIP; also banned).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | **30T 53.3% gross +0.66, fees 0.532, NET +0.13** / 126T 48.4% gross +0.50, fees 1.917, **NET -1.42** |
| 14d / 30d | 227T 48.5% gross -0.64 / fees 3.341 → net **-3.98** · 653T 52.7% gross -3.15 / fees 7.414 → net **-10.56** |
| arm gap 7d | armed 47T **95.7% `+3.37`** vs unarmed 79T 20.3% `-2.87` |
| arm gap 14d | armed 82T **95.1% `+5.20`** vs unarmed 145T 22.1% `-5.84` |
| trail vs stop 14d | `profit-monster-trail` 74T 95.9% **`+4.59`** ‖ `atr_sl_hit` 31T 0% `-3.38` · `hard_max_loss` 26T 0% `-2.74` · `manual_sl_hit` 22T 0% `-2.13` (CEO domain) |
| regime 7d | NORMAL 19T 63.2% `+0.83` · EXTREME 56T 48.2% `+0.62` · **HIGH 51T 43.1% `-0.95`** (n≥50, but a blanket HIGH block = banned blanket change; `regime-gate-tension-check` 11-24 owns) |
| kill screen 14d n≥10 sub-50 | ai-trader LONG 11T 18.2% `-0.29` · hl_copy LONG 11T 18.2% `-0.21` (reach40 **9.1%** = pure chop, n<20, external) · ai-trader SHORT 37T 37.8% **`+0.46` positive → not a kill** |
| chop share | 14d losers 90/107 (**84%**) never reached `mfe>=0.40` |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
n=18 = 4 never-adverse / 12 recovered / **2 NEVER** (IMX #17001 atr-trend- hard_max_loss `-0.12` · BLUR #17029 pump-chain+ prearm_lock `-0.02`) = never-armed chop class → **WRONG-SIDE REFUTED 138th** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (both mandate joins re-run)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 00:30Z** — overall flip **46.7% n=2235** (flipping loses) · rider\|ABOVE n=1880 45.4% / AT 57.2% / BELOW 46.9% · **pc-\|BELOW 64.6% n=48 HOLDS** (Oct-27 PROMOTE) / pc-\|AT 28.6% never blanket · rider chi2 p=4.6e-42 **per-signal only** |
| floor join | **RE-RAN 00:44Z** — floor_only 49.7% (n=1980) vs always 46.7% (n=456), **fisher p=0.2532** (worse than 11-21's 0.2323, not converging) → route stays **CLOSED / directional-only** |
| shadow_trader | **130,621** signals — all 11 gates block ≤56% would-win, all avg-negative-EV; exit A/B **pm_trail `+20,152`** vs hard_max `-26,147` vs rr `-9,448` vs cut_loser `-2,353` = **TRAIL-OR-NOTHING** |
| rider-fade / win-capture | 204 lines (correct path) / 19 raw → 8 distinct ids |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + 2 live collectors** |

### 4. DUE (read early)
**11-23** jup-long clonehunt + formal weekly AMPLIFY → **11-24** tag-split / brake-cf / gate-cross-tab / **regime-tension (absorbs both rejected regime gates)** → **11-25 WIN-CAPTURE READ** (n≥40, pace ≥ +$0.10/day, fk<20%) + **capture-leaderboard-giveback** + bbsqueeze reband + structure-flip + watch-contrarian + pcfade + hotset-pin → **11-26** storm waiver → **11-27** stop-family (CEO Phase2) + linregfade + pc-weight → **11-28** **maker-entry (fee axis)** + jup-walk + dual-basis + conf-tilt + prearm fk + r2v2-clonehunt + reentry-study → **11-29** tape-at-long → **12-03** kill-line (only pending checkpoint) → 12-06 atr-trend-accel → 12-15 ugb-bypass.

### 5. AMPLIFY — 1 NEW proposal, WHY-NOT for the cells (mandate)
**NEW: `amplify-capture-leaderboard-giveback`** (type a, due 11-26, NO-SHIP default, **blocked on win-capture 11-25**, units guard #193, `PM_TRAIL_DISTANCE` excluded). 30d capture on winners (mfe≥0.30, n≥10): **pump-chain- 0.519 (n=13) / pump-chain+ 0.525 (n=16) / volume-buildup- 0.538 (n=37) / atr-trend- 0.558 / bb-squeeze+ 0.559** vs jup 0.626 and ai-trader-pending 0.810 — one *global* giveback flip would hand the same tightening to signals already at 0.63–0.81.
**Why-not for cells — all 7 n≥10 net>0 30d winner cells already in-flight:** ai-trader NORMAL SHORT 25T `+1.19` NO-SHIP · bb-squeeze+ NORMAL 39T `+0.66` → 11-25 · vb- HIGH 19T `+0.41` clone-hunt done · rider EXTREME LONG 13T `+0.35` combo 0.6→1.3 live · jup HIGH 28T `+0.29` → 11-28 · atr-trend- NORMAL 17T `+0.26` → 12-06 · pc- NORMAL 31T `+0.15` → 11-27. n≥5 net≥0.50 adds only the same 2 rows.
**Flip-KPI: MET this week** — PREARM_LOCK_ENFORCE shadow→live 2026-11-20 01:26Z (+ PUMP_CHAIN_V6 kill 11-21, CEO ratify owed).

### 6. LAST-RUN VERIFY (#286) — ALL PASS
stranded-entries guard holding (0 in `_doc` after this run's 3 writes, `--selfcheck PASS` ×2) ✓ · btc_pump_rider path NOTE present (204 lines on correct path) ✓ · maker-entry-fill-walk open 11-28 NO-SHIP ✓ · V6 still `False` + constants EMPTY ✓ · 0 Tracebacks in `logs/pipeline.log` ✓ · checkpoint_registry only kill-line 12-03 pending (0 intraday boxes) ✓ · 75 hermes timers live ✓ · recovery_replay selfcheck PASS ✓ · floor + contrarian joins re-run ✓.

### 7. READINESS (2026-11-22 00:50 UTC)
**2 open, both bracketed — HOLD.** ZORA `bb-squeeze+` #17041 LONG 00:18 SL 0.00440055 / TP 0.00453798 (HIGH) · BTC `continuum+` #17040 LONG 00:04 SL 59590.7 / TP 61425.4 lev 5 (HIGH). **btc_15m AND btc_4h both LONG_BIAS = AGREE**, continuum AT, vol LOW, velocity SLOW, accel FLAT, volume LOW, trend_quality STRONG_UP, market_phase DECLINING → agree-with-uptrend but DECLINING + LOW volume + AT continuum = **hold the 2 bracketed LONGs, no added size, trail-family first, LONGs only on pullback-to-structure WITH volume, size 1.0x.** 0 auto-executable steers, portfolio good; 2 signal-health warnings triaged.

**CEO owed:** **V6 kill RATIFY/VETO (one-line revert)** · **rider-fade fk-limb calibration ruling (captain rec: keep shadow)** · **maker-entry lever ruling (NO-SHIP default)** · **prearm first-read ACK.**
**Flip-KPI:** MET (prearm enforce 11-20).
