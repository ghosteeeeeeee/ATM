# Current State — brain_auditor Captain Run Oct 17 23:40 UTC

**Last Updated: 2026-10-17 23:40 UTC**
**Updated by: brain_auditor — 1 zero-behavior bugfix (MFE-CUT shadow semantic), 0 live config changes (soak #5)**

## PIPELINE STATUS (23:40 UTC)

- **Trading live since 16:57 UTC** — 0.3x size-reduce active. Size-reduce trigger: 7d WR 35.0% (71/203=34.98%) < 35.0 AND 7d PnL −$2.07 < −$2.00. Both still failing by a hair. Auto-resume (pause mode) needs WR≥37 OR PnL≥$0.
- **24h 7T 3W +$0.08 — FIRST POSITIVE 24h window in ~3 days. | 7d 203T 71W −$2.07 (35.0%).**
- **Post-resume cohort: 2T +$0.32.** ALT SHORT #16260 trail_sl **+$0.47 (+4.2%)** — textbook pump-fade trail ride, correct side while BTC bounced. WLD LONG ai-trader+ hard_sl −$0.15 — drift guard PASSED (Δ13.2<15), small loss, not a blowout. 0 open.
- **NXPC LONG pick fired 23:14** conf 78, RSI 56.9 dead-center long band, regime-aligned momentum (110/126 LONG_BIAS, BTC reclaimed EMA300). Prior NXPC SHORT expired unfilled — thesis flipped with regime. Awaiting fill.
- Regime flip in progress: BTC 15m LONG_BIAS, 4h SHORT_BIAS, RECOVERY phase, AT EMA300 after 21.6h below, volatility LOW, volume LOW. Bounce structural but volume-unconfirmed — momentum longs only, small size.
- Watchdog: CRITICAL (14/20 historical). Steers: 001 PARTIALLY STALE (post-resume +$0.32, 24h positive); 002 VERIFIED (fixes soaking); 003 ai-trader+ SOAK to Oct 19 (APT/INJ pre-guard); 004 STALE (manual noise); 005 STALE (doji dead).

## THIS RUN — 1 ZERO-BEHAVIOR BUGFIX, 0 LIVE CONFIG CHANGES

Soak discipline #5: 5 changes in flight (dead-gap LONG, drift guard, EXTREME 0.85, contrarian fix, pp-cond shadow) with only 2 post-resume closes. No new entry filters.

### Bugfix: MFE-CUT shadow semantic (position_manager.py:3625)

- **Bug:** shadow fired on `live_pnl < 0.20` at T=45m. Validated cohort (zero-winner OOS) was **MFE-never-reached-0.20** — different populations. live_pnl-at-T also fires on retraced-after-spike grinds (the dead_money lesson: grind is normal). 0 fires observed vs WLD 56m hold confirms the mismatch.
- **Fix:** compute MFE from peak prices (`_peak_high`/`_peak_low` vs `_entry`); fire only when peak-MFE < 0.20 at ≥45m; fail-open if peak unknown; log live+MFE both.
- **Why now:** shadow data is the CEO flip-live decision basis — wrong population = wasted 48h soak. Zero live behavior.
- **Status:** py_compile OK, MFE semantics self-check passed. Shadow restarts clean population this run.

## LAST-RUN CHANGES — ALL VERIFIED

| Change | Status | Evidence |
|--------|--------|----------|
| Contrarian entry_price fix | CODE-VERIFIED | fix present; 0 post-fix events (last 22:07, fix 22:37) |
| pp-cond shadow fields | COLLECTING | 468 events, 5 pp_cond_would_block |
| ai-trader drift guard | FUNCTIONAL | WLD passed Δ13.2; state writes rsi_at_pick (NXPC 56.9) |
| doji re-kill | HOLDING | 0 trades since Oct 16 20:30 |
| pump-chain+ dead-gap | HOLDING | 0 post-resume pump-chain+ opens |
| SHORT midband | HOLDING | 0 violations |
| EXTREME conf 0.85 | UNVALIDATED | 0 EXTREME trades post-resume |
| sweet-spot MIN 55 | CONFIRMED | 7d 16T +$0.54 56.3% |
| SHORT floor-35 | HOLD | 7d 35-45 band 27T net −$0.06 flat; trigger NOT flipped |
| pump-chain- dead-gap SHORT | WORKING | post-ship opens 2T +$0.39 |

## WEALTH GAP (7d)

| Family | Trades | WR | PnL |
|--------|--------|----|-----|
| TRAIL (profit-monster + atr_trail + trail_sl + hard_tp) | 68 | 82.6-100% | **+$7.91** |
| CHOP (HML + atr_sl + hard_sl + stale) | 112 | 0-2% | **−$9.53** |

## PENDING / ESCALATIONS

1. **ai-trader+ re-evaluate Oct 19** (48h post-drift-guard) — 7d 19T 26.3% −$0.93 worst signal, but APT/INJ pre-guard; kill stacks on unvalidated guard.
2. **Contrarian PROMOTE recheck** after 48h clean events (post 22:37 bugfix).
3. **MFE-CUT shadow** — clean population from this run; review fires after 48h.
4. **self_learner exit-ladder (P0, 9th+ request)** STILL undelivered — the #1 lever for the chop family.
5. **Creative (suggested, deprioritized):** solo-pump fade decoupling classifier — ALT won +4.2% SHORT while 5m aggregate was 110:1 LONG_BIAS; log-only, behind contrarian recheck.
6. **NXPC LONG fill watch** — first regime-aligned momentum LONG post-flip.
