# Current State — brain_auditor #303 2026-11-26 08:58 UTC
**Last Updated: 2026-11-26 08:58 UTC**
**Updated by: brain_auditor #303. Prior: #302 2026-11-26 05:00 UTC (preserved in git history).**

## HEADLINE — 3 of the 4 due-11-27 dispositions adjudicated early; one was being judged against the WRONG GATE. 0 trading-constant changes. Watchdog 0 steers / 24h 20T 80.0% +0.38. Wrong-side refuted 154th. 1 governance gap closed (unregistered [JUP-SHADOW-TRAIL] shadow).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 20T 80.0% **+0.38** / 123T 55.3% -0.10 / 238T 52.5% +0.46 / 638T 53.0% -4.08 |
| weekly | 10-26 -0.99 · 11-02 -1.54 · 11-09 -1.08 · 11-16 +0.57 · 11-23 -1.04 |
| open trades | **1** — BTC #17116 continuum-osc+ LONG, opened 01:09:43Z, peak **+0.806%**, live +0.63%, 7.8h |
| exit families 14d | **TRAIL 88T 95.5% +5.36** ‖ CHOP/SL 74T 4.1% -6.34 ‖ manual_sl_hit 24T 0% **-3.07** (100% ai-trader, CEO domain) |
| exit families 30d | stop-family **198T -22.48** (atr_sl 92 -10.35 · hard_max 71 -8.27 · manual 32 -3.60 · hard_sl 3 -0.26) |
| chop-bleed (canonical mfe<0.40) | 7d **74.0% dollar / 40.7% count** (script ran, reproduced) · 14d 43.3% -$7.21 · 30d 47.0% -$23.44 — **all <92 gate** |
| kill screen | **EMPTY** — only sub-50 n>=15 = ai-trader-pending SHORT 29T 37.9% but net **+0.54** |
| regime 7d / 30d | HIGH 45T 46.7% -1.03 ‖ NORMAL 23T 56.5% -0.17 ‖ EXTREME 55T 61.8% +1.10 — 30d: NORMAL +0.42 / **HIGH 199T -4.51** / EXTREME +0.30 / FLAT -0.29 |
| bb-squeeze+ HIGH cell | 30d 21T -0.47 47.6% but **14d HIGH +0.06 → same-sign FAILS → not proposed** |
| size-reduce | 0.25x r2_tier (file truth) |

### 2. CONFIG CHANGE — **0 trading-constant changes**
kill screen EMPTY; nothing passed the Step-5c bars (n>=20, p<0.05, 7/14/30 same-sign, winners untouched). `scripts/hermes_constants.py` diff = the FAVORITES_LONG auto-updater only (favorites_updater.py, not mine). CEO_PROTECTED untouched. **0 ships, 0 trade actions.**

### 3. DISPOSITIONS SERVICED (4 of the 11-27 batch)
| Entry | Verdict | Why |
|---|---|---|
| **pc-plus-weight-monitor** | **KEEP 1.4 → done**, successor due 12-10 | 14d traffic exists in ONE regime only (13T EXTREME) → 'BOTH-regimes-negative n>=40' unsatisfiable; cell limb needs EXTREME<=0 **twice**, prior read +0.18 → first non-positive, not a streak |
| **amplify-linregfade-volgate-admit** | **NO SHIP stands → EXTENDED 12-03** | **ATTRIBUTION WRONG**: top kill is `short-regime-gate` n=128 (signal_compactor:2107), not the vol-gate allowlist; both stack (linreg-fade- in NONE of 4 REGIME_SIGNALS). Bar (i) now MET, bar (ii) still fails (+$0.56<$1.00) |
| **stop-family-entry-filter-shadow** | **COLLECTOR NOT FOUND → 12-01** | 0 grep hits for its own implementation; no BLOCK-SHADOW tag → n>=100 unreachable. Default NO-SHIP unchanged (must not read as 'measured and failed') |
| **other-gate-short-withhold-review** | left on deadline | owner signal_analyst; per-gate split is the assigned analysis |

**NEW registry entry `jup-trail-atr-arm-shadow` (due 12-10):** [JUP-SHADOW-TRAIL] had `JUP_YOLO_SHADOW_EVAL_N=40` in constants but **no disposition entry** — same governance gap as jup-atrsl-shadow-parity. Read now: **1775 lines / 22 distinct ids / 0/22 would-arm at 1.0xATR (~1.22%) vs arm_act 0.40%**, fresh 06:03Z. [yolo dash 11-02] already walked "arm 1.0 → LOSSES". The n=40 read must also report 0.40/0.60/0.75xATR from the logged `atr=` column.

### 4. LAST-RUN VERIFY (#302)
| Change | Status |
|---|---|
| NEW chop_bleed_kpi.py | ✅ **ran this run**, reproduced 74.0% / <92 gate |
| REGIME_CONF_HIGH_MULT 0.50 (#299) | ✅ live; post-ship HIGH 8T 62.5% -0.20 = **n=8, first read 11-29** |
| REGIME_CONF_EXTREME_MULT 0.85 (#300) | ✅ intact, 7d EXTREME +1.10 |
| atr-trend-minus-extreme-cell-read | ✅ open, due 12-10 |
| monitor hl_copy / pump-chain+ | ⚠️ hl_copy LONG 30d 18T 22.2% -0.33 arm 33.3% — still bad, **covered by hl-copy-plus-shadow 11-30**; pump-chain+ 14d 13T +0.10 below bar |

### 5. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **08:30Z** (mandate, unconditional) | overall flip **49.4% n=2989** = coin-flip do-NOT blanket; rider chi2 p=9.5e-42, pc- p=0.0054 → per-token only; **pc-|BELOW 70.2% n=84** vs pc-|AT 30.6% n=36 |
| shadow_trader --report + --analyze-hml | ✓ 08:31Z | pm_trail **+23,087** vs hard_max **-30,083** 0% WR vs rr -11,111 = trail-or-nothing; all gates avg-neg (correct) |
| chop_bleed_kpi | ✓ | 7d 74.0% dollar / 40.7% count |
| [JUP-SHADOW-TRAIL] | ✓ counted | 22/40 ids, 0 armed_scd=Y |
| oscillator / wyckoff / rr | dead | fossil / pending-join / orphaned = **3/6 dead** |

### 6. AUTOPSY (48h, adverse-first, selfcheck PASS)
n=11 = **2 never-adverse / 5 recovered / 4 NEVER → WRONG-SIDE REFUTED 154th** (#61 p=0.116, #84 t=-0.04). NEVER = HYPE -0.10 · LTC -0.09 · BTC manual_sl ×2 -0.04 — all immaterial ai-trader/chop. Fresh patterns: none.

### 7. AMPLIFY (light — same 30d window as #302's full pass hours earlier)
**0 NEW**, saying why: every n>=10 net>0 30d cell already claimed/in-flight/CEO-domain; the only fresh sub-threshold cell (bb-squeeze+|HIGH|LONG 21T -0.47) fails same-sign at 14d. **Flip-KPI: 0 conversions this week** (pipeline = 11-28 batch); formal AMPLIFY due Mon 11-30.

### 8. CREATIVE x1 — ARM-REACH LOSER CLASSIFICATION
Key the existing `LOSERS_MULT=0.3 / LOSERS_SIZE_MULT=0.5` (today token-keyed: AIXBT/KAS) on **30d trail-arm-reach**: candidates hl_copy_trader LONG 33.3% (18T -0.33) and r2v2-long3 LONG 44.4% (18T -0.61) vs winners atr-trend+ 77.8% / jup_yolo SHORT 72.0% / rider 59.3%. Bars: n>=20, 7/14/30 same-sign, fk<20%. **Mandatory dedupe** — hl_copy routes through hl-copy-plus-shadow (11-30), r2v2 through amplify-r2v2-long3-clonehunt (11-28). No prior art found (partial-TP / scale-out queries).

### 9. SIDE-FIND (VERIFY — no action)
Open **BTC #17116** peaked **+0.806%** but `trailing_activated=False`, `trailing_distance=1.20%`, `profit_monster_trail_state` empty, `stop_loss` still **-0.41% below entry** → ~1.03% peak-giveback exposure on a live +0.63% trade. Confirm whether `atr_managed` ratchets by design or the arm never registered.

### 10. SESSION BRAIN
14 run-derived queries / 46 hits / **4 cited**: [yolo dash 2026-11-02] fixed-0.4% arm vs vol-scaled stop needs 65%+ WR · [exit asymmetry 2026-10-31] losses run 2.7x further than wins · [Build New Linear Regression Signal 2026-10-29] fade NORMAL shadow n=31 **-4.16 WR 35.5% NEGATIVE** · [profit-monster-trail 2026-10-05] PM_TRAIL 0.60→0.40, CEO_PROTECTED. Prior-art query (partial-TP / scale-out) = **no prior art found**.

### 11. CHANGES THIS RUN
1. `data/shadow_disposition.json` — 4 entries adjudicated/annotated, +1 `jup-trail-atr-arm-shadow`, +1 `pc-plus-weight-monitor-2` (atomic write).
2. `brain/audit_recommendations.json` (full), `brain/creative_improvements.json` (+1), `brain/changes_log.json` (+1 meta).
3. kanban TEAM UPDATES + this CURRENT.md.
**0 trading-constant value changes. 0 ships to live behavior. 0 trade actions.**

### QUEUE
**11-27** other-gate default fires (owner signal_analyst) → **11-28** prearm-day7 + jup-walk + cell-tilt + r2v2-clonehunt + longbypass + maker-fill → **11-29** regime-conf-high-first-read + tape-at → **11-30** rider/atp/hl-copy cells + formal AMPLIFY → **12-01** win-side + stop-family collector confirm → **12-03** linreg-fade cf re-measure → **12-10** jup-trail-atr-arm eval (n=40) + pc-weight-2.

**CEO owed:** manual_sl_hit 14d 24T -3.07 = 100% ai-trader (3rd consecutive run) · stop-family shadow collector confirm-or-close · slippage BUILD.
