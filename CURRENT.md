# Current State — brain_auditor #310 2026-11-27 20:55 UTC
**Last Updated: 2026-11-27 20:55 UTC**
**Updated by: brain_auditor #310. Prior: #309 2026-11-27 16:50 UTC (preserved in git history).**

## HEADLINE — A DISPOSITION WAS PREMISED ON A FLAG THAT HAD BEEN TURNED OFF 5 DAYS BEFORE ITS OWN DEADLINE
`prearm-enforce-day7-read` (due 11-28) requires "7 enforce days". **`PREARM_LOCK_ENFORCE` went False 2026-11-22 (commit `1de08caf`, CEO major-break redesign: prearm's [0.25,0.40) domain handed to structure stops)** — the enforce window was 11-20 01:26Z → 11-22, cohort **FROZEN at n=12**. Ran the read anyway: `brain/analysis/prearm_day7_read_2026-11-27.py --selfcheck PASS`.
- **bar1** fk reach-proxy **7/12 = 58.3% vs the 13.9% walk baseline = FAIL** (reach ≠ winner-fk, labeled) · **n>=15 NOT MET** (12)
- **bar2** realized net **−0.13** pnl_usdt (avg −0.0108) **FAIL**
- **bar3 TRIPS (≥2): 5 of 12 fires had 1m-CLOSE favorable peak ≥ PM_TRAIL_ACTIVATE 0.40 during the hold** (17023 BLUR +0.693 / 17029 +0.642 / 17033 APT +0.427 / 17037 BLUR +0.630 / 17045 RESOLV +0.485) — `trades.highest_price` cleared it on **0**, DB `mfe_pct` on only **2**
- **bar4** 14d same-sign **MOOT**
→ **CLOSED MOOT-ENFORCE-OFF.** The guard it would have owed (skip lock when DB-or-candle peak ≥ arm) is **moot while OFF and is NOT shipped** — money-path, CEO-only.

## SECOND — THE NEVER-ARMED LABEL IS A THREE-SOURCE LABEL WITH ~15% NOISE
30d n=616: **44 trades = 15.0% of the 293 DB never-armed (`mfe_pct<0.40`) DID reach +0.40% favorable on 1m CLOSE during their hold (combined −1.53)**; 30 go the reverse way → **both directions disagree = source jitter, not bias.** Row **#17023** carries three disagreeing peaks in one record: **`highest_price` +0.396% (0.004pp under the arm line) vs `mfe_price` +0.580% vs 1m close +0.693% vs 1m high +0.834%.**
Feed sanity (not a venue artifact): candles_1m close vs `trades.exit_price` mean |diff| **0.110%** (n=12) while observed peak gaps run **0.44–0.79pp**.
**NOT a refutation** — the 44 mislabeled trades lost −1.53 too; it **bounds** the label. The chop-bleed KPI and #309's z[1,2) fisher **p=0.0091** both read it.
**Prior art (do not re-derive):** [yolo dash 2026-11-02] *"guardian.py:1885 writes current_price without peaks; observed 0.17% disagreement (3× the MFE threshold) and highest_price < current_price on 16629 — pre-existing dual-writer"* · [ugb_pt exit 2026-10-31] *"MFE/MAE columns are all zeros"*. This run is the **cohort quantification** of a known class.
→ **NEW disposition `peak-source-divergence-neverarmed` (12-04, default NO CHANGE)** owns the re-measure + the re-GO guard draft.

## THIRD — EVERY n≥20 30d CELL FAILS THE FEE-ADMISSION BAR
Extends #309's 7-of-8 gross-positive screen to its complement (ALL cells): best net/trade **btc-pump-rider+|LONG −0.0022**, worst **atr-trend−|SHORT −0.0225**. Book 30d **gross −4.13 / fees 7.78 / net −11.91 = fees are 188% of the gross loss** (fee/trade 0.01247 vs gross/trade −0.00662).
7 cells at WR≥55% n≥15 are net-negative with **avg_loss 1.4–2.0× avg_win** (jup LONG needs 66.7% breakeven, actual 62.8%) = **the loss-SIZE lever, not an entry lever**. Entry-filter avenue stays closed (#309, not re-derived).

### 1. FINDINGS THIS RUN (NET-of-fee)
| Window | n | WR | gross | fees | **net** |
|---|---|---|---|---|---|
| 24h | 12 | 50.0% | −0.65 | 0.15 | **−0.80** |
| 7d | 124 | 56.5% | −0.75 | 1.66 | **−2.41** |
| 14d | 233 | 53.2% | −0.09 | 3.23 | **−3.32** |
| 30d | 624 | 52.9% | −4.13 | 7.78 | **−11.91** |

| Item | Result |
|---|---|
| open trades | **0 FLAT — correct** (steers 0, portfolio good, db healthy, autopilot, size-reduce 0.25x r2_tier) |
| arm split (`trailing_activated`) | 7d True 67T **89.6% +3.19** vs False 57T 17.5% **−3.94** · 30d True 281T **88.6% +14.43** vs False 343T 23.6% **−18.56** |
| 7d exit family | profit-monster-trail 51T 96.1% **+2.36** ‖ atr_sl 15T 0% −1.88 ‖ manual_sl 10T 0% −1.67 ‖ hard_max 10T 0% −1.07 ‖ prearm 9T 0% −0.13 ‖ timeout/cut/stale −0.47 = pure-loss **−5.22** |
| chop-bleed KPI | **7d 77.0% dollar / 78.4% count, NULL 0 — BETWEEN the 70% exit-ownership and 92% escalate gates → no action** |
| kill screen | **0** — only 14d sub-50 n≥15 = ai-trader-pending 32T 37.5% net **+0.41** (payoff-positive, CEO-owned) |
| 7d RR | avg win +0.0643 / avg loss −0.1029 (1.59×) → breakeven **61.5%** vs actual 56.5%; **NET-of-fee breakeven 69.6%** |
| regime 7d | EXTREME 54T +0.46 · NORMAL 31T +0.04 · **HIGH 39T −1.25 = only negative** (30d HIGH 204T 33% of trades, **−6.95 net = 58% of the bleed**) |
| 30d chop screen | only **pump-chain+\|LONG** under 30% arm-rate (22.6%, n=31) and it is **GROSS POSITIVE +0.15** = fee victim, not a chop signal |

### 2. AUTOPSY (adverse-first anchor, selfcheck PASS)
- **48h n=11 = 2 never-adverse / 8 recovered / 1 NEVER (17139 MERL SHORT atr-trend− stale_exit −0.13) → WRONG-SIDE REFUTED 161st consecutive run** (#61 p=0.116, #84 t=−0.04)
- **168h n=51 = 12 / 30 / 9 NEVER = 17.6%** = at the 17.5% #85 baseline (**not elevated**). Composition: 5/9 SHORT (3× atr-trend−), 4/9 LONG (2× prearm_lock)
- Dominant mode = **giveback / never-armed chop**, not direction. All 6 30h losers: MERL stale_exit, SOL jup atr_sl, RUNE/XPL hard_max, BABY atr_sl, BTC atr_sl — mfe 0.012–0.356.

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED **16/16**; PREARM_LOCK_ENFORCE **False** (line 2294) intact; WINNER_CELL_SIZE_MULT 1.0; size-reduce 0.25x. **0 ships, 0 trade actions.** 1 disposition CLOSED + 1 REGISTERED. 0 overdue; registry 1 pending (12-03); 0 intraday checkpoints needed.

### 4. JOIN + SHADOW (3/6 usable)
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **20:31:23Z** (mandate, no systemd producer) | overall flip **47.8%** n=3159 = coin-flip DO-NOT blanket · pump-chain-\|BELOW **70.8%** n=89 (decayed) · rider chi2 **p=6.4e-41** / pc- p=0.0084 = **PER-TOKEN ONLY** |
| shadow_trader --report | ✓ 20:33Z (155,454) | **pm_trail +23,855** vs **hard_max −31,318** vs rr −11,623 vs cut_loser −2,424 = **TRAIL-OR-NOTHING**; every gate cohort avg-negative = gates earning keep |
| shadow_trader --analyze-hml | ✓ 20:34Z | worst n≥10: ema300-breakthrough+ 25T 16.0% · tl-bounce+2 39T 10.3% · r2-trend-long6 27T 14.8% |
| chop_bleed_kpi | ✓ | 7d **77.0%**, between gates |
| oscillator / wyckoff / floor / rr | fossil / pending / CLOSED / orphaned | **3/6 usable** |

**STORM:** fired twice today (14:55Z window-min −3.72%, 15:57Z −3.89%); book stayed FLAT, cf **−1.07** combined, waiver already CLOSED KEEP-SHADOW 11-26 = **storm handling working, not re-proposed.**

### 5. AMPLIFY (0 NEW, saying why) · formal weekly due **Mon 11-30**
Every n≥20 cell is fee-negative → no type-(b) can qualify (1.25× ceiling **+$0.085/30d** < the **+$1.00/30d** bar) and all gross-positive cells already carry the six 11-28 items → emitting one would be a duplicate. **Flip-KPI 0 this week (stated)**; grind-exempt (12-11) stands.

### 6. CREATIVE ×3
1. **Disposition close + successor** — queue hygiene, SHIPPED.
2. **Three-source never-armed label quantified** — recorded, prior art cited.
3. **net/trade-per-cell standing screen** pre-computed for the 11-30 AMPLIFY.

### 7. LAST-RUN VERIFY (#309) — ALL PASS
evidence_note_309 present on 7 dispositions · eval-long-z-midband-1-2 open/12-04 intact · chop_bleed_kpi RAN · contrarian mandate HELD 20:31Z · recovery selfcheck rc=0 · prearm day7 selfcheck PASS · disposition JSON valid (165) · session lock ABSENT · constants EMPTY · CEO_PROTECTED 16/16 · **0 Tracebacks** · registry 1 pending · 0 overdue.

### 8. SESSION BRAIN
8 run-derived queries / 40 hits / **7 cited**. Prior art: [Build New Linear Regression Signal 2026-10-29] maker fee lever (29d old, still unimplemented) · [yolo dash 2026-11-02] dual-writer peak disagreement (25d) · [ugb_pt exit 2026-10-31] MFE columns zeros · [risk-budget decision 2026-10-21] no blanket regime kills · [ai-trader live trades 2026-10-15] manual-SL losing streak. **NO prior art** for "PREARM_LOCK_ENFORCE off redesign" (0 hits — the ruling lives only in constants + commit `1de08caf`).

### 9. READINESS (2026-11-27 20:10Z watchdog)
**0 open / 0 steers / portfolio good / db healthy / autopilot — FLAT = CORRECT.** Both timeframes **ALIGNED at LONG_BIAS** but trend_quality **STRONG_DOWN** + volume LOW + velocity SLOW + acceleration FLAT + continuum BELOW + wyckoff ACCUMULATION + market RECOVERY = **no confirmed trend in either direction → NO fresh entries until 1m sustains one side WITH volume; trail-family first (51T 96.1% +2.36/7d is the only paying exit family); size 0.25x (inert at the $11 floor).**

### QUEUE
**11-28 SIX due** — **maker fee walk = PRIORITY (bars (i)–(v) already MET: +$1.62/14d, fill 82.3%, both halves same-sign, fk 18%/17% count & 11.3% dollars; blocked only on (vi) ALO no-retry rule + (vii) CEO sign-off)** · prearm-day7 **NOW CLOSED MOOT — do not re-run** · jup-short-walk · conf-tilt-floorproof · r2v2-clonehunt · longbypass-dual-basis → **11-29 JOINT HIGH read (ONE instrument only)** → 11-30 rider/atp/hl-copy cells + **FORMAL WEEKLY AMPLIFY** → 12-01 linreg-fade storm / jup-atrsl / win-side / stale-block → **12-04 z-midband first read + peak-source re-measure** → 12-05 reband + rr-engine → 12-11 grind-exempt.

**CEO owed:** maker ALO retry rule + sign-off (11-28) · PREARM stays OFF (11-22 ruling, standing) · **manual_sl_hit 30d 31T 0% −3.54 = 100% ai-trader (10th run)** · peak-source GUARD **only if prearm is ever re-GO'd** · z-midband kill (12-04, independent verification first).
