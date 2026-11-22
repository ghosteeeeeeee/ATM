# Current State — brain_auditor #289 2026-11-22 16:55 UTC
**Last Updated: 2026-11-22 16:55 UTC**
**Updated by: brain_auditor #289. Prior: #288 2026-11-22 04:45 UTC (preserved in git history).**

## HEADLINE — THE 'CRITICAL' LOSING-STREAK ALARM SAID 'Something is wrong' WHILE THE ANSWER WAS ALREADY KNOWN: 12/13 LOSSES NEVER ARMED. steer-001 now self-diagnoses chop-cohort vs giveback at the alarm site (shipped, live-verified). 0 trading-constant changes.

1. **steer-001 SELF-DIAGNOSIS SHIPPED (`scripts/trade_watchdog.py`).** `mfe_pct` added to `collect_recent_closed`; never-armed majority → "chop cohort, not wrong-side; arm-rate/stall stack owns the fix", armed majority → "exit/lock review", mixed keeps the alarm; exit-reason top-3 mix appended. Constants `STEER_ARMED_MFE_PCT=0.40`, `STEER_NEVER_ARMED_SHARE=0.60`. py_compile PASS · `--selfcheck` 9 fixtures PASS (incl. mfe_pct SELECT mutation guard) · live: *"12/13 losses never armed (MFE<0.40%) = chop cohort… Exits: prearm_lock x6, atr_sl_hit x2, hard_max_loss x2."* Complements #288's per-signal prearm-streak note (steer-003 guard note still live).
2. **HIGH-REGIME BLANKET GATE REJECTED-WITH-DATA.** 30d HIGH 187T 51.3% '-3.17', both split-halves negative — but would block 22 of ~59 7d winners (+1.64, **37% winner-kill > 20% bar**). Bleed is exit-side (atr_sl -3.42 + hard_max -3.25 of -8.52) → owned by stop-family-entry-filter-shadow (11-27). Same verdict class as #287's four rejected candidates.
3. **Steers 3/3 dispositioned:** steer-001 = chop cohort, window artifact (24h gross -0.06 vs watchdog window -0.12; 7d GROSS +0.06 → net -1.79 fee-drag) · steer-002 atr-trend- = EXTREME cell n=8<20 INSUFFICIENT, wins HIGH+NORMAL → MONITOR, auto_1hr NO-block stands · steer-003 = prearm guard working (6/13 window losses are -0.01 caps).
4. **PREARM guard health day-2+: 12 exits since 11-20 01:26Z, avg -0.011 (min -0.03, max +0.01)** = working; full fk walk due 11-28 (`prearm-enforce-day7-read`).
5. **Kill screen 0 rows · AMPLIFY 0 new (why-not with all 7 cells) · Flip-KPI MET** (prearm enforce 11-20). Formal weekly due 11-23 (tomorrow: jup-long clonehunt + weekly).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | **18T 27.8% gross -0.06** (auto_1hr net -0.41, fees 0.29) / 122T 48.4% **gross +0.06, NET -1.79 (fees 1.85)** |
| 14d / 30d | 231T 47.6% -0.58 · 648T 52.9% -2.47 |
| armed vs never | 7d armed 61T **83.6% +3.47** vs never 61T 13.1% -3.41 · 14d armed 118T 83.1% +7.60 vs never 113T 10.6% -8.18 |
| exits 14d | pm_trail 72T 97.2% **+4.55** ‖ atr_sl 32T 0% -3.47 · HML 25T 0% -2.62 · manual_sl 22T 0% -2.13 (CEO) · prearm_lock 12T -0.13 (guard) |
| 30d bleed bucket | **atr_sl_hit 90T 0%W -9.83, 94% never-armed (avg MFE 0.176)** — jup owns 30/90 (-4.03); COVERED by stop-family (11-27) + jup-atrsl parity (12-01) |
| regime 7d | NORMAL 24T 58.3% +0.39 · EXTREME 47T 48.9% +0.14 · HIGH 51T 43.1% -0.47 (blanket gate rejected, above) |
| kill screen 14d sub-50 n>=15 | **ZERO rows** |

### 2. AUTOPSY (48h, recovery_replay adverse-first, ASSERT PASS)
n=20 = 5 never-adverse / 12 recovered / **3 NEVER** (KAS atr-trend- cut-loser -0.11 MFE 0.0 · BLUR pc+ prearm -0.02 · RESOLV atr-trend+ prearm -0.01) = never-armed chop class → **WRONG-SIDE REFUTED 140th consecutive run** (#61 p=0.116, #84 t=-0.04). Window: max MFE among 13 losers = 0.406 (armed-then-capped); 0 losers entered with momentum and got run over.

### 3. SHADOW (both mandate joins re-run)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 16:30Z** — overall flip **47.3% n=2457** (flipping loses) · pc-\|BELOW ~63-70% holds · pc-\|AT 28.6% never blanket · rider chi2 ~1e-42 per-signal only |
| floor join | **RE-RAN 12:31Z** — floor_only 50.0% vs always 47.2%, **fisher p=0.2862** (worse than 04:44's 0.2532, not converging) → route stays CLOSED |
| shadow_trader | **133,439** signals — all gates block 44-56% would-win avg-negative-EV (earning keep); exit A/B **pm_trail +20,528** vs hard_max -26,645 / rr -9,670 / cut_loser -2,353 = **TRAIL-OR-NOTHING** |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + shadow_trader + 2 live joins** |

### 4. CREATIVE (this run)
- **C1 SHIPPED:** steer-001 self-diagnosis (above).
- **C2 PRE-REGISTERED (NO CODE):** `prearm-band-lower-candle-oos` (due 12-01) — extend prearm band [0.25,0.40) → [0.10,0.40). Ceiling: never-armed loser MFE buckets 0.10-0.25 = +2.42/14d (+8.42/30d); fk surface 66 armed winners mfe<1.0 (+3.05). **Bar: candle-OOS >= +1.00/14d pnl_usdt UNITS (guard #193) + fk<20% + 30d same-sign; default NO SHIP.** Prior art: MFE_EXIT_ARM floor 0→0.004 [yolo dash 11-02] rejected too-low thresholds — that churn risk is what the fk bar tests.
- **C3 MONITOR:** atr_sl_hit as signal-not-exit (owned by in-flight 11-27/12-01).

### 5. DUE
**11-23** jup-long clonehunt + **FORMAL WEEKLY AMPLIFY** → **11-24** tag-split / brake-cf / gate-cross-tab / regime-tension → **11-25** WIN-CAPTURE READ (n>=40, pace >= +$0.10/day, fk<20%) + bbsqueeze reband + structure-flip + watch-contrarian + pcfade + hotset-pin → **11-26** storm waiver (CEO deadline) + capture-leaderboard → **11-27** stop-family (90T/0W bucket) + linregfade + pc-weight → **11-28** maker-entry + **prearm-enforce-day7 fk walk** + jup-walk + dual-basis + conf-tilt + r2v2 + reentry → **11-29** tape-at-long → **12-01** prearm-band-lower walk (NEW) → 12-03 kill-line (only pending checkpoint) → 12-06 atr-trend-accel → 12-15 ugb-bypass.

### 6. CHANGES THIS RUN (both non-trading-behavior)
1. `scripts/trade_watchdog.py` — steer-001 composition diagnosis + `mfe_pct` SELECT + 2 constants + `--selfcheck` 9 fixtures. STEER TEXT ONLY; hermes_constants.py git diff EMPTY; CEO_PROTECTED untouched.
2. `data/shadow_disposition.json` — registered `prearm-band-lower-candle-oos` (kind eval, due 2026-12-01), atomic write.

### 7. LAST-RUN VERIFY (#288) — ALL PASS
steer-003 prearm guard note live ✓ · prearm-enforce-day7-read present (11-28) ✓ · prearm guard working (12 exits avg -0.011) ✓ · no past-due dispositions ✓ · constants EMPTY ✓ · protected untouched ✓ · size-reduce absent = 1.0x ✓ · **0 Tracebacks** ✓ · checkpoint_registry only kill-line 12-03 ✓ · recovery_replay selfcheck PASS ✓.

### 8. READINESS (2026-11-22 16:55 UTC)
**1 open — BTC LONG #17051 ai-trader-pending @60570, +0.70% (+$0.08), 2.4h, SL trailed 60553 BELOW entry = breakeven-protected, TP 62300, meta_rsi 34 — HOLD bracketed.** btc_15m SHORT_BIAS vs btc_4h LONG_BIAS **DISAGREE**, continuum ABOVE, vol LOW, velocity SLOW, market_phase DECLINING vs trend_quality STRONG_UP, auto_trader CHOP/MANAGE_ONLY → **chop: NO fresh counter-trend entries; trail-family first; LONGs only on reclaim-that-holds WITH volume; SHORTs only with 4h aligned; size 1.0x.** Watchdog 'critical' = steer-001 (now self-diagnosed chop cohort), 0 auto-executable steers.

**CEO owed:** **V6 kill RATIFY/VETO** · **rider-fade fk-limb (rec: keep shadow one more 14d read)** · **maker-entry lever ruling (NO-SHIP default)** · **mult-150 label (pending since 11-04, CHASE)** · **storm bar sign-off by 11-26.**
**Flip-KPI:** MET (prearm enforce shadow→live 11-20).
