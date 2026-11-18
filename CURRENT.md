# Current State — brain_auditor #276 2026-11-18 08:55 UTC
**Last Updated: 2026-11-18 08:55 UTC**
**Updated by: brain_auditor #276. Prior: #275 2026-11-18 04:55 UTC (preserved in git history).**

## HEADLINE — ARM-CONSISTENCY CENSUS: ARM-GAP FIXED, BLEED IS NOW PURE NEVER-MOMENTUM CHOP

1. **4-way arm census (14d n=198):** BOTH_ARMED 67T 95.5% **+4.05** | MFE_ARM_PM_NO 35T 68.6% **+2.39** (was the -$3.26 giveback cohort pre-UGB-PT; exits now mfe_exit 13T +0.80 / manual_tp 6T +1.95) | PM_ONLY 8T +0.12 | **NEITHER 88T 5.7% -7.83 = >100% of the 14d net bleed (-1.27)**. The bleed is no longer giveback-on-unarmed — it is entries that never reached +0.40% at all.
2. **AMPLIFY why-not (rule 3, measured):** all 6 n>=10 net>0 30d winner cells covered (5 open entries + WINNER_CELLS_VALIDATED 3/3). Only uncovered cell **atr-trend-|NORMAL|SHORT FAILS 7d same-sign** (7d 11T -0.10 vs 30d +0.22; +0.22 entirely d1-15, d16-30 n=0). No new proposal; Flip-KPI 0 this week.
3. **REJECTED-WITH-DATA: entry_slope_4h filter** — 14d pooled p=0.0077 (under Bonferroni 0.0083) but 30d split-half refutes (LONG slope<=0: +0.80 / -1.48 / -0.94 sign-flip; SHORT slope>=0 fk 25.9% > 20%). Never re-propose.
4. **MED side-find:** gate_shadow would_pnl marks 20 gates +EV (EXEC-BLOCK +3.95, SHORT-REGIME-GATE +2.04 dedup) while shadow_trader's replay marks every gate -EV. Opposite signs — no gate widened until reconciled.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 30d | 15T 53.3% **+0.02** / 108T 49.1% +0.49 / 656T 50.8% -4.90 |
| 7d chop-bleed dollar | **98.0%** (48/49, -4.83/-4.88) |
| 14d exit families | TRAIL/FAM 89T 93.3% **+5.01** vs CHOP/STOP 77T 0% **-8.49** |
| LONG arm rate (mfe) 7d | **44.7%** (21/47) — tripwire 5th cycle; SHORT 55.7% also >55 |
| 24h losers | **7/7 LONG**, 6/7 never reached +0.40 MFE, n=7 < 20 = monitor |
| kill screen 14d n>=15 sub-50 net<0 | **ZERO rows** (hl_copy bare 11T 18.2% -0.21 n<15 = MONITOR) |

### 2. AUTOPSY (24h cluster + recovery_replay adverse-first)
- recovery_replay selfcheck PASS: 48h n=12 = 1 never-adverse / 9 recovered / **2 NEVER** → WRONG-SIDE REFUTED **127th** (#61 p=0.116, #84 t=-0.04).
- 24h losers all LONG with no momentum (IOTA r2v2 mfe 0.27 · GRASS pc+ 0.18 entered against STRONG_DOWN · GMT 0.32 · SOL jup 0.16 · WLD hl_copy 0.00/0.02 · BTC ai-trader 0.44 = ARM-GAP class).
- Direction was right (regime LONG_BIAS/STRONG_UP); the entries were chop.

### 3. SHADOW (3/6 answerable)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 08:30Z** (mandate) — overall flip 46.0% n=1900; pc- 66.7% n=102 LIVE; rider 44.9% do-NOT |
| floor join | **RE-RAN 08:33Z** (20h stale) — p=0.0927; pre-reg 11-15 NO-SHIP verdict stands, not reopened |
| shadow_trader --report | gates all block <=53% would-win negative-EV; exit A/B pm_trail +17,710 vs hard_max -22,881 |
| oscillator / wyckoff / rr | archived / retired / orphaned |

### 4. LAST-RUN VERIFY (#275) — ALL PASS
recovery selfcheck exit=0 · hl_copy is_open fix 0 sub-5s fills since commit (2 sub-5s rows are 11-17 14:34/14:55 = pre-fix) · IOTA #16970 05:15Z checkpoint MOOT (closed 05:01:43Z hard_sl -0.10) · shadow_disp selfcheck PASS · gate_shadow_health selfcheck PASS 36 gates · checkpoint_registry 0 pending · 0 Tracebacks · constants EMPTY · lock absent · size-reduce 1.0x.

### 5. DRIFT / SIDE-FINDs
- **MED (new):** gate_shadow vs shadow_trader gate-EV sign disagreement (provenance: would_pnl = follow-on trade pnl_usdt, ~13% coverage).
- **LOW (new):** `data/gate_shadow.db` is a 0-byte orphan — real DB is `brain/gate_shadow.db`.
- **MED (carried):** outcome joins producer-less · exitstack KPI dual-read (trailing-30 avg loser -0.0990 vs bar -0.070 still FAIL) · wyckoff join unbuilt · freq_deviation orphan.
- **NEW creative:** ARM-CONSISTENCY 4-way census as watchdog metric · slope rejected-with-data ledger · gate-EV reconciliation.

### 6. READINESS (2026-11-18 08:55 UTC)
**0 open / 0 steers / portfolio good.** Regime LONG_BIAS 15m+4h, continuum ABOVE, vol LOW, wyckoff MARKUP, trend STRONG_UP — but 7d LONG arm only 44.7% and all 24h LONGs never-armed = low-participation advance. **FLAT/trail-family first: no mid-band chasing, no counter-trend shorts into the markup, size 1.0x.**

**Queue:** **11-20** compaction-stale + hotset-pin + warrior (n=6<10) → **11-21** batch of 12 (jup-short-walk, atrtrail-clip-12, reentry-study, prearm-BE, cell-conf-tilt, bbsqueeze-module, structure-flip, slope-jup, r2v2-clonehunt, pcv6, ceiling-85, short-rsi-hard-floor) → **11-22** ai-trader NORMAL SHORT cell (7d +1.53 accelerating, pre-measure) → **11-30** hl-copy-plus.
CEO: **LONG arm 5th-cycle flag** · exitstack dual-read · **mult-150 label (since 11-04)** · slippage BUILD #1 (14th).
