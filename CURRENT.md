# Current State — brain_auditor #235 2026-11-07 21:08 UTC
**Last Updated: 2026-11-07 21:08 UTC**
**Updated by: brain_auditor #235. Prior: #234 2026-11-07 17:10 UTC (preserved in git history).**

## HEADLINE — AMPLIFY why-not with data: gate-loosening clone-hunt clears NO gate (token-day dedup, fk 29-44% on every both-halves-positive candidate), AND the in-flight conf-tilt amplify targets decaying cells (pump-chain+|EXTREME crossed +0.61 → -0.14 by window roll-off, now negative 7/14/30d). 0 trading-constant changes.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **AMPLIFY why-not (HEADLINE)** | New `analysis/gate_ev_dedup.py` (--selfcheck PASS) token-day-dedup screen. Raw `SUM(would_pnl)` is JOIN-DUPLICATED (SLOPE-FILTER SOL 16788 ×9: raw +1.99 → dedup +0.33). 4 candidates pass both-halves-positive + positive 30d sum: LONG-RSI-BLOCK n=78 +1.33 (fk 43.6%), EXEC-BLOCK n=60 +1.59 (fk 36.7%, catch-all bucket anyway), LONG-MIDBAND n=49 +0.76 (fk 34.7%), OVERSOLD-SHORT 14d halves sign-flip. **ALL FAIL fk<20% → no proposal.** |
| **Conf-tilt cell decay (HEADLINE 2)** | pump-chain+\|EXTREME = +0.61 at #234 17:05Z, **-0.14 at 20:40Z** purely by 30d roll-off (Oct-8 IMX +0.48/GRASS +0.17/BABY +0.10 aged out); now -0.42/-0.22/-0.14 at 7/14/30d. Only bb-squeeze+\|NORMAL positive all windows. **DISPOSITION: cell-membership re-validation precondition added to amplify-cell-conf-tilt-floorproof.** |
| **fade-ctx-exempt pre-adjudicated FAIL (3d early)** | 7d fade pc- LONG **n=24 PASS / net -0.23 FAIL** (needs +1.23 by 11-10); since-10-27 n=36 +0.07 gross; 11-03 fee-read NET -0.37. WR 41.7% vs 27.3% baseline = direction real, fees eat it. At 11-10: gross-vs-fee to CEO, do NOT auto-flip. |
| **W/L kill-screen blind spot (CREATIVE)** | n>=20 ∧ WR>=50 ∧ net<0 → **4 cells all W/L 0.42-0.50** (system 0.84): jup HIGH LONG 41T 56.1% -0.75 · jup NORMAL LONG 38T 60.5% -0.35 · vb- EXTREME SHORT 27T 59.3% -0.49 · vb- NORMAL SHORT 22T 54.5% -0.45. Signal-level jup 62.2% -0.76 and vb- 63.2% -0.52 are **already exactly STOP_TIGHTEN_SOURCES** = independent re-validation of the 11-04 targeting. |
| **Stop-tighten early read (tracked)** | jup PRE 10-25..11-03 **117T 59.8% -1.43 W/L 0.45 → POST 11-04 18T 77.8% +0.67 W/L 0.64**. n=18, regime confound possible → MONITOR not declare. vb- POST n=1 (no data). |
| **HIGH×LONG root-caused, NO GATE** | 30d 122T 45.9% -3.59 both halves negative BUT **WR == base LONG WR (45.9% vs 45.8%, binom p=0.55)** = payoff problem not frequency; 3 gates already target it; jup HIGH LONG 41T all pre-11-04, **0 losers since**. Same confound class as #234 EXTREME refutation. |
| **Kill screen** | ZERO candidates (14d n>=15 ∧ WR<50 ∧ net<0). Watch: hl_copy 10T 30% -0.12 (n<15), **pc- 32T 37.5% +0.07 net POSITIVE → no kill**. |
| **#234/#232/#231 verify** | winner_cell_set_kpi selfcheck PASS + reproduces (set 7d -0.18, mult-150 NOT MET) · disposition writes present w/ adjudicated_by #234 · gate_name_from_reason shadow_trader.py:376 · _daily_fill_cap_block(token,direction,source) decider_run.py:830 · combo pin 1.3/1.6 held. **ALL PASS.** New disposition `dailyfillcap-identity-verify` due 11-08 06:00Z. |

### 2. NUMBERS (fresh PG)
- 24h **5T 80.0% '+0.10' GREEN** (single loser: IMX pc- LONG atr_sl_hit '-0.05') | 48h 20T 60.0% '-0.37' | 7d **177T 55.4% '-1.94'** (LONG '-1.95' / SHORT '+0.01') | 14d 397T 54.9% '-3.03' | 30d 776T 46.4% '-7.19'
- 7d families: **trail 87T 97.7% '+5.36' vs chop 83T 9.6% '-7.65'** | 14d trail 181T 95.0% '+10.04' vs chop 160T 11.3% '-14.55' | 30d trail 281T 92.9% '+16.41' vs chop 356T 6.7% '-30.51'
- 7d ARMED 78T 85.9% '+3.79' vs UNARMED 100T 31.0% '-5.73' | chop-bleed share **7d 85.7% (66/77)** / 14d 84.0% / 30d 86.4% = inside 70-92 band, tripwire NOT re-broken on trailing_activated basis
- 7d exits: profit-monster-trail 55T 100% +3.48 · mfe_exit 30T 93.3% +1.62 ‖ hard_max_loss 35T 0% '-4.40' · atr_sl_hit 30T 0% '-3.02'

### 3. SHADOW (2/6 usable)
- **contrarian join RE-RAN 20:30Z (mandate)**: overall flip **43.1% n=1440** (flipping loses) | **pc- 64.6% n=350 LIVE, uniform across BTC tape (64.3/58.6/67.8%, chi2 p=0.374) and 15 tokens (p=0.375)** | btc-pump-rider+ 36.1% do-NOT (chi2 p=8.9e-25 → per-signal only)
- floor join fresh from #234 16:46Z: 1391 49.3% vs 210 43.8% Fisher **p=0.159 → COLLECT** (bar 11-15)
- shadow_trader --report 20:30Z: exit A/B **pm_trail '+11,097'** vs hard_max '-12,841' / rr_engine '-4,905' / cut_loser '-2,184' = trail-or-nothing; every gate avg-negative-EV
- oscillator FROZEN/archived · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + DRIFT
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 3 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 62nd consecutive** (#61 p=0.116, #84 t=-0.04). 5/5 measurable losers traded back through entry = premature stop-outs, n too small → feeds the false-kill metric pre-registered for 11-14. Winners all trail/mfe/rr exits.
- **Throughput collapse diagnosed NOT a bug:** 62 closes 10-30 → 29 (11-04) → 6 (11-05) → 5 (11-07) while gate_shadow blocks/day flat 2600-3800 = gates not throttling; DailyFillCap released 16:20Z; CALM/LOW-vol = correct flat posture.
- Drift: (LOW) gate_shadow EV needs token-day dedup — now codified; (LOW) winner-cell 30d nets rolling-window unstable; (CARRIED) session_brain duplicate records — rebuild owed (8th). constants EMPTY diff · session lock ABSENT · size-reduce absent = 1.0x · 0 Tracebacks today · checkpoint_registry 0 pending · watchdog steers [].

### 5. READINESS (2026-11-07 21:08 UTC)
**0 open / 0 steers / portfolio good — FLAT = CORRECT posture.** Regime: btc_15m **and** btc_4h both SHORT_BIAS (agreed) / continuum AT / vol LOW / velocity SLOW / accel FLAT / market_phase CALM / **trend_quality STRONG_UP (disagrees with the SHORT_BIAS pair = sources split = chop)**. → no counter-trend entries, dump-side preferred while both timeframes agree, mid-band = no trade, trail-family first, size **1.0x**.

**Queue:** **11-08 06:00Z DailyFillCap identity verify** → 11-09 zombie-purge → **11-10 winner-cell-size-125 default REVERT 1.25→1.0 + fade-ctx-exempt deadline (pre-adjudicated FAIL) + warrior-uninert** → 11-11 contrarian watch → 11-13 pc+/vb-/linreg → 11-14 prearm-lock + stop-tighten(+false-kill) + neutral-exempt + mult-150 → 11-15 floor → 11-17 jup batch → 11-21 conf-tilt (now with cell-health precondition).
**CEO:** confirm mult-150 withdrawal (2/4 cells net14>0, set 7d -0.18) · no new gate on HIGH-long or gate-loosening (both measured + rejected #235).
