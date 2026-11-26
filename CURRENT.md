# Current State — brain_auditor #304 2026-11-26 12:51 UTC
**Last Updated: 2026-11-26 12:51 UTC**
**Updated by: brain_auditor #304. Prior: #303 2026-11-26 08:58 UTC (preserved in git history).**

## HEADLINE — HIGH×LONG = 101% of the 30d net bleed, PASSES all six Step-5c bars, and is deliberately LOCKED not shipped: it would have corrupted the pre-registered 11-29 read of REGIME_CONF_HIGH_MULT 0.50. 0 trading-constant changes. Watchdog 0 steers / 24h 24T 70.8% +0.06. Wrong-side refuted 155th.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 24T 70.8% **+0.06** / 126T 54.8% -0.35 / 236T 52.1% +0.13 / 641T 52.9% -4.36 |
| weekly (ISO) | 10-19 +1.06 · 10-26 -1.87 · 11-02 -1.54 · 11-09 -1.08 · 11-16 +0.57 · 11-23 -1.33 |
| open trades | **0** — flat, 0 steers, portfolio good, db_healthy |
| armed vs never | 14d **101T 91.1% +5.98** vs **135T 23.0% -5.85** ‖ 7d 64T 89.1% +3.36 vs 62T 19.4% -3.71 |
| exit families 30d | pm_trail 223T 96.9% **+12.77** ‖ atr_sl_hit 95T 0% **-10.72** ‖ hard_max 71T 0% -8.27 ‖ manual_sl 32T 0% -3.60 (ai-trader) |
| exit families 14d | pm_trail 82T 95.1% +4.85 ‖ manual_sl 24T 0% -3.07 (100% ai-trader) ‖ atr_sl 27T 0% -2.95 ‖ hard_max 26T 0% -2.77 |
| chop-bleed (canonical mfe<0.40) | **7d 75.4% dollar / 77.4% count · 14d 75.2% dollar — all <92 gate** (chop_bleed_kpi.py ran, reproduced) |
| kill screen | **0 new** — only 2 cells negative at 7/14/30 with n>=20: bb-squeeze+ LONG (flat + validated NORMAL winner cell) and atr-trend- SHORT (fk14 20.3% > 20% bar, owned by 12-10 read) |
| regime 30d / 14d / 7d | HIGH 201T **-4.43** 50.2% ‖ NORMAL 241T +0.39 ‖ EXTREME 175T -0.03 ‖ FLAT 24T -0.29 — 14d HIGH -1.84, 7d HIGH -0.87 |
| RR asymmetry | 30d avgW +0.0694 / avgL -0.1006 = **1.45x** → breakeven WR 59.2% vs actual 52.9% (was 1.73x at #239) |
| size-reduce | **0.25x r2_tier** (file truth, written 11-23T15:32Z, "R2-TIER R1 -77.0%") |

### 2. THE HEADLINE MEASUREMENT — HIGH × LONG
| Cut | Result | Test |
|---|---|---|
| 30d | HIGH-LONG **117T -3.58 43.6%** vs nonHIGH-LONG **303T +0.10 53.8%** | Fisher **p<0.0001** |
| 14d | 42T -1.25 38.1% vs 89T +0.96 55.1% | **p<0.0001** |
| 7d | 22T -1.09 40.9% vs 56T +0.77 58.9% | **p=0.0003** |
| weekly | 5/5 ISO weeks negative (10-26 -0.78 / 11-02 -1.17 / 11-09 -0.38 / 11-16 -0.33 / 11-23 -1.00) | same-sign |
| fk14 | 16 of 123 14d winners = **13.0%** | < 20% bar |
| save | **+$3.58/30d** | >= +$1.00 |
| **anatomy** | **ARMED 48T +2.57 89.6% vs NEVER 69T -6.15 11.6%**; 88.9% of loss $ from never-armed mfe<0.40 (56/60 losers) | **ARM-GAP cell, not wrong-side** |

Never-armed LONG loser avg loss by regime: **HIGH -0.1163 > NORMAL -0.0990 > FLAT -0.0967 > EXTREME -0.0892** on an **identical 1.5% initial sl_distance**. Mechanism: **atr_sl_hit realized price move EXTREME -0.959% / HIGH -0.913% / NORMAL -0.690%** → ATR stops widen with vol and the unarmed cohort pays. HIGH atr_sl_hit 33T -4.08 = 38% of the whole atr_sl bleed; jup 33T -4.45 = 41%.

**WHY NOT SHIPPED:** (1) REGIME_CONF_HIGH_MULT 0.70→0.50 landed 2026-11-25T12:43Z with a pre-registered read due **11-29**; a second HIGH-side lever today strips the LONG leg out of that cohort and makes the read uninterpretable. (2) One-variable rule. (3) The armed half wins 89.6% (+2.57/30d) so the right first instrument may be arm-side (PREARM_LOCK_ENFORCE, CEO GO) not entry-side.

### 3. CONFIG CHANGE — **0 trading-constant changes**
Kill screen empty; nothing cleared the bars *and* the one-variable rule. `scripts/hermes_constants.py` diff = `favorites_updater.py` FAVORITES_LONG auto-update (+XPL) only, not mine. CEO_PROTECTED untouched. **0 ships, 0 trade actions.**

### 4. SHIPPED (registry only)
| Action | Detail |
|---|---|
| **NEW `high-long-displacement-read`** | due **11-29**, kind eval, all six bars pre-computed in `threshold`, **default NO-SHIP**, explicit joint-adjudication rule with `regime-conf-high-first-read`: exactly ONE HIGH-side instrument ships that day (mult KEEPS → block becomes next single variable; mult REVERTS → block alone or mult alone, never both) |
| `regime-conf-high-first-read` | direction-split evidence appended: 30d HIGH-SHORT 84T -0.85 59.5% vs HIGH-LONG 117T -3.58; post-ship n=10 = 70% WR / -0.12 / arm 90% vs pre 87T -1.93 / 46% / arm 52% (**EARLY, not claimed**) |

### 5. AUTOPSY (48h, adverse-first, --selfcheck rc=0)
n=11 = **3 never-adverse / 7 recovered / 1 NEVER (#17094 HYPE SHORT jup atr_sl -0.10) → WRONG-SIDE REFUTED 155th** (#61 p=0.116, #84 t=-0.04). Dominant mode = **GIVEBACK 7/11** = exit/arming side, matching chop-bleed ownership at ENTRY gates. 24h losers 7T -0.89, 6/7 LONG, **all never-armed mfe<0.40** — immaterial. Open-anchored replay NOT used (vacuous, #85).

### 6. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **12:30Z** (mandate, unconditional) | overall flip **49.3% n=2998** = coin-flip DO-NOT blanket; rider chi2 p=9.5e-42 / pc- p=0.0084 HETEROGENEOUS → per-token only; rider\|AT 59.1% n=215, pc-\|BELOW 69.4% n=85 vs pc-\|AT 29.7% n=37 |
| shadow_trader --report | ✓ 12:31Z | **pm_trail +23,161** vs hard_max **-30,211** vs rr -11,144 = trail-or-nothing; all gates avg-neg (correct) |
| --analyze-hml | ✓ 12:40Z | biggest negative shadow **open-skies+ 766 @ 17.1% -0.383%** but 0 live closes in 30d = gates holding the worst source |
| chop_bleed_kpi | ✓ | 7d 75.4% / 14d 75.2% |
| floor / oscillator / wyckoff / rr | 11-24 file / fossil / pending / orphaned | **3/6 answerable** |

### 7. AMPLIFY (light screen; formal weekly due Mon 11-30)
**0 NEW — saying why:** every n>=10 net>0 30d cell is (a) claimed by an OPEN entry (rider-EXTREME-LONG 11-30 · bb-squeeze-NORMAL-LONG 12-05 · jup-HIGH-SHORT 11-28 · atr-trend-NORMAL-SHORT 12-01), (b) adjudicated NO-SHIP (ai-trader-pending\|NORMAL\|SHORT, 11-21), (c) a validated WINNER_CELLS member, or (d) below +$1.00 materiality (+0.15/+0.13/+0.07/+0.07/+0.01). Early n5-9 net>+$0.30 = **EMPTY**. gate_shadow cannot carry a clone-hunt: **no blocked-signal column** (`outcome_signal` = follow-on trade's signal, #260 basis defect). **Flip-KPI: 0 conversions this week (stated).**

### 8. CREATIVE ×3
1. **HIGH×LONG as an ARM-GAP cell** — decision rule: arm rate 41.0% → nonHIGH 49.2% removes the bleed with zero blocking; block only if the joint 11-29 read says the arm route is unavailable.
2. **Regime-conditional realized-stop KPI** — atr_sl_hit price move HIGH -0.913% vs NORMAL -0.690% on identical initial SL; the 11-20 scope-widen walk only ever saw the pooled +$0.29.
3. **open-skies+ graveyard receipt** — 766 shadow rows 17.1% WR, 0 live closes = gates-working evidence, prevents a re-proposal.

### 9. LAST-RUN VERIFY (#303/#302/#300) — ALL PASS
jup-trail-atr-arm-shadow in registry (12-10) ✓ · chop_bleed_kpi ran + reproduced ✓ · HIGH 0.50 live (n=10 EARLY) ✓ · EXTREME 0.85 ✓ · MFE_CUT False ✓ · CONTRARIAN_LIVE False ✓ · PREARM_LOCK_ENFORCE False / shadow True thr 0.25 ✓ · WINNER_CELL_SIZE_MULT 1.0 ✓ · WINNER_CELLS_VALIDATED 3 members, pc+ absent ✓ · size-reduce 0.25x ✓ · 0 Tracebacks ✓ · checkpoint watcher active, 0 intraday pending ✓ · recovery + disposition selfcheck rc=0 ✓.
**SIDE-FIND (LOW, new): `shadow_disposition --selfcheck` now prints `BREACH: trial PnL -4.08 < -2.5; worst HML -9.77% < -6.5` on EVERY run — the underlying entry `trial-coupled-cutsloser-sl` is **status=done since 11-03**, so this is the cumulative-since-2026-10-27 trial ledger, not a live gate. Nobody should read it as a current breach; either gate the live-metrics print on entry status or relabel it (owner: main-session, cosmetic).
**SIDE-FIND CLOSED:** #303's BTC #17116 — closed 09:10:39Z UNIVERSAL_MAX_HOLD **+0.04**, peak MFE 0.804%, trailing_activated=False, atr_managed=True, stop 60363 vs entry 60608 → arm never registered while the ATR-managed stop ratcheted; +0.76pp giveback on a 0.804% peak = **arm-side, owned by prearm 11-28, no new defect.**

### 10. SESSION BRAIN
11 run-derived queries / 47 hits / **4 cited**. MANDATORY prior-art for the displacement query = **NO PRIOR ART FOUND** (6 hits, none a block attempt). Cites: [calwndar 2026-10-31] "LONG in HIGH: 55T, 43.6% WR … regime routing + chop mechanics" · [exit asymmetry 2026-10-31] "exit lets losses run 2.7x further — the entry is not the problem" · [mtf macd 2026-10-02] "don't blanket disable anything, use the closed trades to see if the signal is in the wrong volatility regime" · [mtf trend signal 2026-10-01] "LONG high+above … n=83 is noise".

### 11. READINESS (2026-11-26 12:51 UTC)
**0 open / 0 steers / portfolio good.** Regime: btc_15m **LONG_BIAS** + btc_4h **LONG_BIAS** AGREE · continuum **ABOVE** · trend_quality **STRONG_UP** · vol NORMAL · zscore NEUTRAL · wyckoff DISTRIBUTION · market CALM · velocity SLOW · acceleration NEGATIVE. Today's 13 opens = **12 LONG + 1 SHORT = aligned with the trend** (correct side of the market). → trail-family first; size **0.25x**; no regime block.

### QUEUE
**11-27** other-gate default fires (owner signal_analyst) → **11-28** prearm-day7 + jup-walk + cell-tilt + r2v2-clonehunt + longbypass + maker-fill + reentry → **11-29 JOINT READ: regime-conf-high-first-read + high-long-displacement-read (ship at most ONE HIGH-side instrument)** → **11-30** rider/atp/hl-copy cells + **FORMAL WEEKLY AMPLIFY** → **12-01** win-side + stop-family collector confirm-or-close → 12-03 linreg-fade → 12-10 jup-trail-atr-arm + pc-weight-2.

**CEO owed:** manual_sl_hit 14d 24T -3.07 = 100% ai-trader (**4th consecutive run**) · **PREARM_LOCK_ENFORCE GO** (14d never-armed -5.85 = the whole bleed) · stop-family collector ship-or-close (bar unreachable, owner CEO) · slippage-column BUILD.
