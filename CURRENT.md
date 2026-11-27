# Current State — brain_auditor #309 2026-11-27 16:50 UTC
**Last Updated: 2026-11-27 16:50 UTC**
**Updated by: brain_auditor #309. Prior: #308 2026-11-27 13:00 UTC (preserved in git history).**

## HEADLINE — THE OFFENSE BUDGET IS POINTED AT THE WRONG LEVER. Applied the #307 FEE-ADMISSION BAR **net-of-fee at CELL level** (pnl_usdt − fees.fee_total, CEO Phase-0 basis): **7 of the 8 n≥10 net>0 30d "winner cells" are NEGATIVE after fees.** Only ai-trader-pending|NORMAL|SHORT clears (NET +0.56 = **+$0.0207/trade** vs the $0.0186 bar) and it is already adjudicated NO-SHIP + 100% single-token BTC. btc-pump-rider+|EXTREME|LONG (claimed 11-30) = **0.0170/trade = FAIL by 8%** on the 30d basis (7d sub-window 0.0492 clears → the read must state which window governs). **TYPE-(b) CELL-MULT IS STRUCTURALLY INERT: a 1.25x boost = 0.25 × cell_net → best case rider +$0.085/30d, jup HIGH SHORT −$0.078/30d (amplifying a net-negative cell LOSES money), bb-squeeze+ NORMAL −$0.033/30d. The bar needs cell_net ≥ +$4.00/30d; no cell reaches +$0.60.** The maker lever already due 11-28 measures **+$1.62/14d (~+$3.5/30d) = 41× the best cell-mult outcome.** Rec: fee axis first at tomorrow's read; freeze type-(b). 0 trading-constant changes.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d (NET-of-fee) | 15T 73.3% gross +0.09 fees 0.18 **net -0.09** / 125T 56.8% gross -0.26 fees 1.70 **net -1.96** / 233T 53.2% gross +0.02 fees 3.24 **net -3.22** / 628T 53.3% gross -3.63 fees **7.77 net -11.40** (fees = **214% of gross**; fee/trade 0.0124 > gross/trade -0.0058) |
| open trades | **0 FLAT — correct** (steers 0, portfolio good, size-reduce 0.25x r2_tier) |
| arm split | 7d 77T 83.1% **+3.46** vs 48T 14.6% **-3.72** · 14d 131T 84.0% **+7.62** vs 102T 13.7% **-7.60** · 30d 335T 87.8% **+19.28** vs 293T 14.0% **-22.91** |
| 7d exit family | profit-monster-trail 51T 96.1% **+2.50** ‖ manual_sl 12T 0% -1.82 ‖ atr_sl 14T 0% -1.71 ‖ hard_max 10T 0% -1.07 ‖ prearm_lock 9T 0% -0.13 |
| chop-bleed KPI | **7d 75.7% dollar / 76.5% count, NULL 0 — BETWEEN the 92% escalate and 70% exit gates → no action** |
| kill screen | **0** — only 14d sub-50 n≥15 = ai-trader-pending 33T 36.4% net **+0.35** (payoff-positive, CEO) |
| 7d RR | avg win +0.0682 / avg loss -0.1000 (1.47×) → breakeven **59.5%** vs actual 56.8% (net-of-fee breakeven ~67%) |
| regime 7d | EXTREME 54T +0.60 · NORMAL 31T +0.04 · **HIGH 40T -0.90 = only negative** (30d HIGH 202T -3.98) |

### 2. SECOND FINDING — z[1,2) IS A NEVER-ARMED PROXY, NOT AN ENTRY DEFECT
| bar | value | verdict |
|---|---|---|
| decomposition 30d | band\|armed 63T **+3.34 90.5%** (rest-armed 92.5%) vs band\|never 70T **-6.75 5.7%** (rest-never 18.6%) | 100% of loss in never-armed class |
| all-directions | band 133T -3.41 (45.9%) vs rest 414T +0.94 (58.9%) **fisher p=0.0091** | STRONGER than LONG-only 0.033 |
| SHORT limb | 53T -0.89 (50.9%) vs 103T +0.64 (68.0%) **p=0.0546** | same sign, **NOT significant** — scope stays LONG |
| windows | 7d -0.71 / 14d -1.18 / 30d -3.41; rest +1.19 / +1.65 / +0.94 | 3/3 same sign |
| winners killed | 61/335 = **18.2%** (bar <20%) worth +3.81 | PASS |
| hold time | band never-armed 4153s / med 2749s vs rest 4716s / 3347s | **exits SOONER — refutes a stall mechanism** |
| **SEQUENCING** | prearm-enforce-day7-read due **11-28** hits the same cohort with a TIME instrument that keeps the band's 63 armed winners (+3.34) | **re-measure band on a post-prearm baseline BEFORE the 12-04 read** |

### 3. THIRD — ENTRY-SIDE FILTERS ARE STRUCTURALLY CLOSED (negative-result ledger)
30d ARMED (n=335) vs NEVER-ARMED-LOSERS (n=235): entry_rsi mean **52.4 vs 51.1** (median 52.3/51.5) · signal_z 0.53 vs 0.39 · confidence 71.7 vs 71.3 · momentum_state rising 38.5% vs 36.6% · z_tier proportions near-identical · RSI buckets same shape. Only exception = the narrow z[1,2) band. Confirms #246 "momentum/z-tier predict ARM not net". **The chop bleed cannot be entry-filtered; the instrument is time/exit-side (prearm).**

### 4. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED **16/16**; PREARM_LOCK_ENFORCE=False (line 2294) intact; WINNER_CELL_SIZE_MULT 1.0; size-reduce 0.25x. **0 ships, 0 trade actions.** 7 dispositions extended with `evidence_note_309` / `evidence_309`; selfcheck PASS. Registry 1 pending (12-03), 0 intraday checkpoints needed. **0 overdue dispositions.**

### 5. AUTOPSY (48h, adverse-first, selfcheck rc=0)
n=11 = **2 never-adverse / 9 recovered / 0 NEVER → WRONG-SIDE REFUTED 160th consecutive** (#61 p=0.116, #84 t=-0.04). All 4 24h losers never-armed (mfe 0.012/0.108/0.125/0.356); 3 of 4 atr-trend+ LONG. Dominant mode = giveback / never-armed chop.

### 6. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **16:31:08Z** (mandate) | overall flip **47.9%** n=3156 = coin-flip DO-NOT blanket; pc-\|BELOW **70.8% n=89** (decayed from 69.4%); het rider p=1.45e-40 / pc- p=0.0084 = per-token only |
| shadow_trader --report | ✓ 16:35Z | pm_trail **+23,747** vs hard_max **-31,183** vs rr -11,548 = trail-or-nothing; every gate cohort avg-negative = gates earning keep |
| --analyze-hml | ✓ 16:36Z | worst n≥10: ema300-breakthrough+ 25T 16.0%, tl-bounce+2 39T 10.3%, r2-trend-long6 27T 14.8% |
| chop_bleed_kpi | ✓ | 7d **75.7%**, between gates |
| floor / oscillator / wyckoff / rr | CLOSED / fossil / pending / orphaned | **3/6 usable** |

**STORM INFO:** fired twice today (window-min -3.72% then -3.89%); book stayed FLAT (0 opens after 11:47Z); cf -1.95 then +0.88 = **net -1.07 across both**; waiver already CLOSED KEEP-SHADOW 11-26 → storm handling working, not re-proposed.

### 7. AMPLIFY (0 NEW, saying why)
Fee bar NET-of-FEE at cell level: 7/8 n≥10 net>0 cells fail ($0.0186 bar); early n5-9 net>+$0.50 **EMPTY**; type-(b) ceiling **+$0.085/30d** < the +$1.00/30d materiality bar → no cell-mult proposal can qualify. Formal weekly AMPLIFY due **Mon 11-30**. Flip-KPI **0** this week (stated); grind-exempt (12-11) stands.

### 8. CREATIVE ×3
1. **Amp re-axis** — freeze type-(b), spend on the fee axis (41×) → SHIPPED as 5 `evidence_note_309` appends.
2. **z-band sequencing behind prearm** → SHIPPED as `SEQUENCING_BLOCK_12_04`.
3. **Entry-filter avenue formally closed** → ledger, prevents re-derivation.

### 9. LAST-RUN VERIFY (#308/#307) — ALL PASS
eval-long-z-midband-1-2 present/open/12-04 bars intact · grind-exempt open/12-11 · chop_bleed_kpi RAN · contrarian mandate HELD 16:31Z · recovery selfcheck rc=0 · disposition selfcheck PASS post-append · session lock ABSENT · constants EMPTY · CEO_PROTECTED 16/16 · size_mult stamped · 0 Tracebacks · registry 1 pending · 0 overdue.

### 10. SESSION BRAIN
12 run-derived queries / 55 hits / **4 cited**. Prior art: [Build New Linear Regression Signal 2026-10-29] maker fee lever · [calwndar 2026-10-31] winner-cell HL_MIN floor (#234) · [shadow mode 2026-10-17] RR exit asymmetry · [brain_auditor #246 2026-11-11] entry-filter scan rejected. **NO prior art for the z-band decomposition or the type-(b) ceiling.**

### 11. READINESS (2026-11-27 16:10Z watchdog)
**0 open / 0 steers / portfolio good — FLAT = CORRECT.** Post-dump (−3.89% window at 14:55–15:57Z) with acceleration POSITIVE + trend_quality STRONG_UP but market_phase DECLINING + volume LOW = no confirmation → **NO fresh discretionary directional entries until 1m sustains one side WITH volume; trail-family first (51T 96.1% +2.50/7d is the only paying exit family); size 0.25x (inert at the $11 floor).**

### QUEUE
**11-28 SIX due** (maker = fee axis, prioritize 41× · jup-walk · cell-tilt · r2v2-clonehunt **recommend CLOSE dormant n=1/30d** · longbypass · prearm-day7 = the only live remedy for never-armed −7.60/14d) → **11-29 JOINT HIGH read (at most ONE instrument)** → **11-30 rider/atp/hl-copy cells + FORMAL WEEKLY AMPLIFY** → 12-01 win-side + stop-family → **12-04 z-midband first read (SEQUENCED behind 11-28 prearm)** → 12-05 reband + rr-engine → 12-11 grind-exempt.

**CEO owed:** maker SHORT-only scope (11-28) · PREARM_LOCK_ENFORCE still OFF · manual_sl_hit 7d 12T 0% **-1.82** = 100% ai-trader (9th run) · z-midband kill (12-04, independent verification first).
