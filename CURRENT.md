# Current State — brain_auditor #286 2026-11-21 16:55 UTC
**Last Updated: 2026-11-21 16:55 UTC**
**Updated by: brain_auditor #286. Prior: #285 2026-11-21 08:55 UTC (preserved in git history).**

## HEADLINE — A PAST-DUE AMPLIFY ENTRY WAS STRANDED IN `_doc`, UNREADABLE BY THE DAILY RUNNER. Fixed + root-cause guard shipped (bug_hunter PASS). Separately: the `--prearmed` knife bypass leaks 28 shorts/30d at **t = -0.94 → NOT significant**, so it stays MONITOR; and the watchdog's PATTERN-1 justification is refuted by the entries' own tape stamps.

1. **Stranded registry entry (this run's ship):** `data/shadow_disposition.json` held `amplify-ema300-breakthrough-underdeploy` (open, deadline **2026-11-20**) as a dict inside the `_doc` array. `shadow_disposition.py main()` only iterates `reg['entries']` → the 08:15Z packet, the control tower and the calendar all skipped it and the deadline passed silently (introduced #257 / 919f4d50). **Repaired:** moved to `entries` (135 now), **done / CLOSED SUPERSEDED** — the same work was properly disposed as `amplify-ema300-underdeploy` **CLOSED NO-SHIP 2026-11-18 (#274, bar (i) walk FAIL)**, so no measurement is owed. **Guard shipped:** pure `_stranded_entries(reg)` + `main()` `- ERROR: STRANDED in _doc` report line + `entry_errors` seeding + **6 fixtures + live canary in selfcheck**. py_compile PASS · `--selfcheck SELFCHECK PASS` · **bug_hunter PASS (1 MED + 3 LOW, ALL FIXED)** — the MED was a genuine new crash surface (`_doc` as a JSON scalar would TypeError *outside* `main()`'s try and kill the run before one packet) → isinstance guard added; LOW-3 report/log wording aligned.
2. **`--prearmed` knife cohort — MONITOR, not shipped (watchdog steer #4 answered with data).** `trade_watchdog` appends `--prearmed` to **every** pending fill (CEO 2026-11-20 "we need to catch these shorts"), and brain.py then skips both the knife (<35) and hard-floor (<45) SHORT RSI gates. 30d leak: **28 fills at entry RSI<35, all ai-trader-pending / all BTC, net '-0.80', 39.3% WR, 11 winners '+1.17' vs 17 losers '-1.97' → mean -0.0286, t = -0.94 → NOT distinguishable from 0.** Family context 30d all-RSI = **40T '+0.39' NET POSITIVE**; it is the only rsi<35 SHORT cohort in 30d (every other signal: 0). Counterfactual-if-blocked = +0.80/30d. **Verdict: MONITOR — reversing a 1-day-old CEO directive on t=-0.94 is noise-trading.** Bar **pre-registered (C1)**: n>=40 AND |t|>=2 AND family stays net>0 after removal AND winner-kill <20% AND 14d/30d same-sign. Side-note (LOW): the flag is appended unconditionally while the CEO rationale quoted in the comment is ladder-scoped — 40/40 pending shorts are BTC today, so no live spread.
3. **Watchdog PATTERN-1 justification REFUTED by entry-time stamps (MED drift, reported).** Alert claims "BTC held above continuum EMA300 the entire window" and derives "do not arm BTC SHORT at meta_rsi<35 while 1m above EMA300". The three cited entries' own `_signal_metadata` read **`btc_ema300_position=BELOW`, dist -3.92 / -2.91 / -2.99, STRONG_DOWN** → the rule would have blocked **0 of 3**. Only #17032 (15:17Z, tape **ABOVE** +1.12, rsi 24.64, also lost '-0.11') satisfies it. Content is closed regardless: **#192 pre-registered 10 tape-state tests at 30d → 0 passed Bonferroni** (T6 SHORT pos==BELOW p=0.0246 fails 5x + 7d sign flip). No gate proposed. Creative **C2**: pattern alerts must cite ENTRY-time tape, not window-end tape.
4. **Watchdog R3 (BLUR block) → INSUFFICIENT.** BLUR pump-chain+ LONG 30d **8T 25% '-0.44'** (7d 3T 0%, 14d 3T 0%) vs the n>=20 bar → **monitor, not blocked**. R1/R2 moot (BTC duplicate longs #17026/#17027 both self-closed manual_sl_hit '-0.09' each at 15:17Z before this run). R5 inert (`AI_TRADER_ENABLED=False`). Steers list itself = 0.
5. **0 trading-constant changes of my own** — session lock absent; hermes_constants EMPTY git diff; CEO_PROTECTED untouched; size-reduce file absent = 1.0x; V6 kill (#284) holding, CEO RATIFY/VETO still owed.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | **28T 64.3% '+1.07'** / 123T 51.2% '+0.85' gross (auto_1hr fees 1.86 → net '-0.95') |
| 14d / 30d | 222T 49.5% '-0.52' / 649T 53.3% '-2.77' |
| arm gap 7d | armed 49T **95.9% '+3.62'** vs never 74T 21.6% **'-2.77'** |
| arm gap 14d | armed 82T '+5.15' vs never 140T '-5.67' |
| trail vs chop 14d | `profit-monster-trail` 74T 95.9% **'+4.54'** \|\| `atr_sl_hit` 31T 0% '-3.37' · `hard_max_loss` 25T 0% '-2.64' · `manual_sl_hit` 22T 0% '-2.13' (CEO domain) |
| regime 7d | NORMAL 20T 65.0% '+1.02' · EXTREME 52T 51.9% '+0.66' · HIGH 51T 45.1% '-0.83' |
| kill screen | 14d sub-50 n>=15 net<0 = **0 rows** |
| never-armed bleed owners 14d | atr-trend- 19T '-1.58' (10.5%) · jup 25T '-0.94' · rider 8T '-0.66' (0%) · hl_copy 11T '-0.21' (0% arm) |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
n=14 = 1 never-adverse / 10 recovered / **3 NEVER** (GOAT r2v2-long7 CL-T1 '-0.12' · IMX atr-trend- HML '-0.12' · BLUR pump-chain+ prearm_lock '-0.02') = never-armed chop class → **WRONG-SIDE REFUTED 137th** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (mandate re-runs done)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 16:30Z** — overall flip 46.7% n=2235 (flipping loses) · pc-\|BELOW 64.6% n=48 HOLDS · pc-\|AT 28.6% never blanket · rider chi2 p=4.6e-42 **per-signal only** |
| floor join | **RE-RAN 16:34Z** — 49.8% vs 46.7%, **fisher p=0.2323** (worse than 0.1688 morning read) → route stays CLOSED 11-15 / MONITOR |
| shadow_trader | 16:34Z 129,452 signals — all 11 gates block <=56% would-win negative-EV cohorts · exit A/B **pm_trail '+19,876'** vs hard_max '-25,804' vs rr '-9,420' vs cut_loser '-2,346' = TRAIL-OR-NOTHING |
| rider-fade | **204 lines** (was 138) in `/var/www/hermes/logs/signals.log` — path NOTE at `btc_pump_rider.py:38` holding |
| win-capture | **16 lines** (was 12), all would-capture=YES @ what-if 20% → COLLECT to 11-22 |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + 2 live collectors** |

### 4. DUE (read early)
**11-22 00:00Z** rider-fade formal (fk-only) + win-capture (bar 0.70) — day-scale, `hermes-shadow-disposition.timer` 08:15Z surfaces them → **11-23** jup-long clonehunt + formal weekly AMPLIFY → 11-24 tag-split / gate-cross-tab / brake-cf / regime-tension → 11-25 structure-flip + bb-squeeze reband + watch-contrarian + pcfade + hotset-pin → **11-26 storm waiver** → 11-27 stop-family entry-filter (CEO Phase2) + linregfade + pc-weight → **11-28 maker-entry fill walk** + jup-walk + dual-basis + conf-tilt + prearm fk → 11-29 tape-at-long · 12-03 kill-line (only pending checkpoint) · 12-06 atr-trend-accel · 12-15 ugb-bypass.

### 5. AMPLIFY — 0 new, WHY-NOT (mandate)
All **7** 30d n>=10 net>0 winner cells in-flight or disposed: ai-trader NORMAL SHORT 25T '+1.19' **NO-SHIP** · bb-squeeze+ NORMAL 39T '+0.66' → reband+structure-flip 11-25 · vb- HIGH 20T '+0.49' clone-hunt+underdeploy **done** · **rider EXTREME LONG 13T '+0.35' → combo weight already boosted 0.6→1.3 by auto_1hr 14:55Z today** · atr-trend- NORMAL 17T '+0.26' → accel 12-06 · jup HIGH 27T '+0.22' → walk 11-28 · pc- NORMAL 31T '+0.15' → pc-weight 11-27 + live flip. n>=5 net>=0.5 adds only the same 2 rows; kill screen n>=15 sub-50 net<0 = 0 rows. **Flip-KPI: MET this week (PREARM_LOCK_ENFORCE shadow→live 11-20 01:26).**

### 6. LAST-RUN VERIFY (#285) — ALL PASS
btc_pump_rider.py path NOTE ✓ · maker-entry-fill-walk open 11-28 NO-SHIP default ✓ · ai-trader cell done/NO-SHIP ✓ · win-capture collecting ✓ · V6 kill still False + constants EMPTY ✓ · 0 Tracebacks in `logs/pipeline.log` ✓ · checkpoint_registry only kill-line 12-03 ✓ · 75 hermes timers live ✓ · recovery_replay selfcheck PASS ✓ · shadow_disposition selfcheck PASS (extended) ✓.

### 7. READINESS (2026-11-21 16:50 UTC)
**0 open / 0 steers / portfolio good — FLAT = CORRECT.** btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** vs **continuum ABOVE EMA300** = sources **DISAGREE**; vol LOW, velocity SLOW, acceleration NEGATIVE, trend STRONG_DOWN, market_phase RECOVERY, wyckoff UNKNOWN, BTC meta_rsi ~24.6 at last fill. → **no fresh counter-trend entries while sources disagree; SHORT only on a bounce into RSI 45-55 (knife <35 stays global off the prearmed path); LONG only on pullback-to-structure WITH volume — do not chase (2 of today's 3 BTC LONG losers entered at RSI 66.8/83.4); trail-family first; size 1.0x.**

**CEO owed:** **v6 kill RATIFY/VETO (one-line revert)** · **maker-entry lever ruling (NO-SHIP default)** · prearm first-read ACK.
**Flip-KPI:** MET (prearm enforce, 11-20).
