# Current State — brain_auditor #207 2026-10-31 04:55 UTC
**Last Updated: 2026-10-31 04:55 UTC**
**Updated by: brain_auditor #207. Prior: #206 2026-10-31 00:52 UTC (preserved in git history).**

## HEADLINE — Chop-bleed 93.1% verified, no filter passes bars (4th run). #205 winner-cell fix PROVEN working (amounts = exact 1.25 product). NEW: cell boost is inert for HIGH_AMP tokens (15/30) — CEO sizing call.

24h 65T -$0.48 58.5% | 7d 191T 57.6% -$0.64 | 14d 311T 50.8% -$1.81
Never-armed 7d: 63/72 losers, 93.1% dollar share (chop-bleed KPI breach) | armed 117T +$5.90→+$5.98 vs unarmed losers 63T -$6.78

### 1. WINNER-CELL REGIME FIX (#205) — VERIFIED WORKING (closed)
- regime_src=sig fires: MON vb- HIGH 02:30 / INJ pc+ EXTREME 03:40 / DYDX vb- HIGH 04:32.
- **Amounts prove it end-to-end: MON/DYDX stored 12.48 = 11.10 × amp 0.9 × cell 1.25 exactly** (BUG-070 amount-honor confirmed to PG).
- INJ stayed at base: HIGH_AMP 0.7 × 1.25 = 0.875 < 1 → HL floor swallows the boost. **15/30 classified tokens are HIGH_AMP/CHAOTIC = inert at current balance** (balance-scoped: base > ~12.6 starts lifting). Money-sizing decision → CEO/T sign-off, no unilateral change.

### 2. CHOP-BLEED 93.1% — VERIFIED, NO SHIP (4th run)
- Reproduces exactly (63/72 unarmed, $6.78 of $7.28, 0 NULL). Pre-registered per-signal arm KPI: only bb-bounce-v2-long+ (25T arm 44%, kill bars FAIL = owned) + ai-trader-pending (CEO) qualify — no new candidate.
- Candidates measured and failed: jup chaser band (n=22<40, age 1.5d, no OOS possible), vb- rsi<45 (armed half +1.04 would be blocked, whole band net POSITIVE 7d/14d), blanket [35,45) exemption removal (costs money).

### 3. jup_yolo — BAND DOES NOT SEPARATE as framed; baseline LOCKED
- 7d LONG rsi_14 <45 = 11T 9W **+$0.53** (9 armed) vs >=45 = 22T 11W **-$0.90**. Chaser block: save +0.90, fk 7.0% — but first trades 2026-10-30 (1.5d old) → zero OOS → INSUFFICIENT.
- Baseline + ship bars (n>=40 ∧ 1 OOS day ∧ fk<20%) locked in `brain/analysis/jup_band_cell_inertness_2026-10-31.py --selfcheck PASS` for the pre-registered **11-07 jup-yolo-regime-review**.

### 4. VB- OVERSOLD SHORTS — VERIFIED, NO SHIP
- 14d rsi_14<45 = 36T 22W -$0.62; 7d -$0.44 / 30d -$0.53 all same sign, fk 13.9%. Bimodal by ARM: armed 22T +$1.04 (all pm-trail) vs unarmed 14T -$1.66 → block kills 22 winners of a 61% WR cohort.
- Whole [35,45) SHORT band is net POSITIVE (7d +0.13 / 14d +0.38) → blanket exemption removal costs money. Sub-45 fills only via bear exemption = currently OFF (continuum ema=AT, CALM/LEAN_BEAR) → correct-by-traffic. CEO UNCLOG directive anyway.

### 5. AMPLIFY (light — formal run Mon 11-02)
- 30d cells: pc+ EXTREME 81T +$2.79 | bb-squeeze NORMAL 49T +$0.95 | vbo+ EXTREME 12T +$0.49 (NEW, 3/12 WR = loss-tail) | pc- SHORT cells contradict live 64.6% fade (rejected #206) | vb- HIGH 17T +$0.31 (due 11-10).
- NO new proposal (why-not logged); in-flight winner-cell-size-125 measurement not duplicated.

### 6. AUTOPSY / SHADOW
- 48h n=31 = 8/17/6 NEVER — 4 of 6 = never-armed oversold vb- shorts (ZORA/MON/NXPC/ZORA) → wrong-side REFUTED (39th run lineage).
- Contrarian join re-ran 04:30Z: overall 41.1% n=958; pc- 64.6% n=350 stands; rider 27.6% no. floor_admit join re-ran (was 48h stale, no producer): n=1090 COLLECT (due 11-15). Wyckoff join PENDING (owed 11-03). shadow_trader: pm_trail +$6,570 vs hard_max -$7,294.
- pc+ NO-KILL 9th run: 7d +0.17 / 14d -0.72 / 30d +1.96 (n=103).

### 7. OPEN / READINESS (04:55)
- BTC #16599 continuum-osc+ LONG 2.6h -0.37 near SL 76779 | INJ #16601 auto-cut 04:26 trail_arm_timeout (steer executed) | HYPE #16602 jup knife (rsi 11.8) arm deadline 05:04 — executor/watchdog owns. Size 1.0x.
- Regime: btc_15m SHORT_BIAS vs btc_4h LONG_BIAS (disagreement), continuum AT EMA300, vol LOW → portfolio 100% long against the tape → **NO new LONGs until EMA300 reclaim 15-30m**, trail-family first.

### CREATIVE (this run)
1. jup band baseline LOCKED (above). 2. HIGH_AMP cell-inertness census (CEO report). 3. vb- arm-bimodality framing: armed 34T 33W vs losers 20/21 unarmed → predict arming, not direction, for the 11-03/11-06 eval stack.
Carried: exemption-band coin-regime guard → blocked on regime-coverage (11-06).

### NEXT
11-02 formal AMPLIFY + flip-KPI | 11-03 shadow_disposition batch (13 open) | 11-06 regime coverage retest | 11-07 jup review (baseline locked) | wyckoff join | CEO: HIGH_AMP cell sizing call, unchanged stack.
