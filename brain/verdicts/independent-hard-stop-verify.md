# Independent Verdict: ride_it HARD_MAX_LOSS Option B Backtest Verification

**Auditor:** independent subagent (fresh-eyes audit, no reliance on prior analysis)
**Date:** 2026-10-06
**Files reviewed:** plans/ride-it-hard-max-loss-exemption.md, brain/verdicts/audit_scripts/ride_it_hard_stop_results.json, scripts/ride_it_exit.py, scripts/position_manager.py, scripts/hermes_constants.py, scripts/cut_loser.py, scripts/pnl_utils.py
**Own code:** brain/verdicts/audit_scripts/independent_ride_it_verify.py (fresh implementation)
**Own results:** brain/verdicts/audit_scripts/independent_verify_results.json

---

## === INDEPENDENT VERDICT ===

**Claim:** Option B improves WR +10.5pp without changing avg PnL (Current: WR 61.4%, avg +9.485%, total +540.6%; Option B: WR 71.9%, avg +9.477%, total +540.2%).

**Verdict: DISAGREE**

**Confidence: HIGH**

---

## Evidence

### 1. The claimed backtest is unreproducible and contains physically impossible numbers

- **No generator script exists.** `ride_it_hard_stop_results.json` is the only artifact; a repo-wide search found no script that produces it. The claimed backtest cannot be re-run or audited at the code level.
- **32 of 35 claimed "trail_hit" winners are physically impossible** given the actual candle data (`/root/.hermes/data/candles.db`, candles_5m). For each claimed winner I computed the maximum attainable price move within the claimed hold window from the trade's real entry price. Examples:

  | Token | Claimed PnL | Claimed hold | Max attainable in window | Verdict |
  |-------|------------|--------------|--------------------------|---------|
  | SUPER | +42.36% | 0.17h | +2.22% (+6.67% @3x lev) | Impossible |
  | ALGO | +35.28% | 0.92h | +1.08% | Impossible |
  | BABY | +30.11% | 1.42h | +1.16% | Impossible |
  | W | +28.46% | 0.17h | +1.40% | Impossible |
  | ONDO | +26.96% | 0.17h | **-0.40%** (price never rose) | Impossible |
  | WLD | +22.77% | 0.17h | +0.23% | Impossible |
  | FIL | +13.08% | 0.17h | +0.12% | Impossible |
  | USUAL | +25.62% | 0.33h | +0.18% | Impossible |

  No token in the entire 30-day window ever gained more than ~18% in any 1-hour period (ALGO max +7.3%, W +8.5%, BABY +18.4%, SUPER +12.2%). The claimed PnLs cannot be explained by 3x leverage either. The JSON's biggest winners are fabricated or produced against wrong/mismatched data.

- **10 of 22 claimed "hard_stop" exits never happened in the data.** DYDX, JUP, BANANA, ACE, CFX, CAKE, BLUR, WCT, ADA, YGG: price never dipped to -1.0% within the claimed hold window (dips of -0.05% to -0.80%). Example: CFX claimed hard_stop -1.0% @1.5h — real min dip in first 4h was -0.80%, and the real trade closed +7.36% via UNIVERSAL_MAX_HOLD at 8h.
- **The claimed "current" scenario ignores production's actual exits.** SUPER (real: closed +8.48% pnl via atr_sl_hit at 16 min; claimed: hard_stop -1.0% at 55 min — the -1% dip occurred 52 min AFTER the real close), BLUR, INJ, HYPER, CAKE — claimed sim held trades hours beyond when production actually closed them, then called the later dip a "hard stop". The claimed baseline is not what production delivered on these trades (actual DB outcomes: WR 58.6%, avg +0.94% pnl_pct @3x lev = +0.31% unleveraged — vs claimed "current" avg +9.485%, a ~30x overstatement).
- **PONS trades were simulated despite zero candle coverage.** PONS 5m candles start 2026-10-01; both PONS trades (ids 15232, 15242) were 2026-09-11 and closed as small winners (+0.31%, +0.80% pnl_pct) in 32s/3.5min. The claimed backtest reports them as hard_stop losers at -1.0%/-2.5%. Results were produced where no data exists.
- Claimed internal aggregates (WR/avg/total/reason counts) do check out arithmetically from the JSON itself — the JSON is internally consistent, but its per-trade inputs contradict the real price history.

### 2. My independent simulation (own code, real data, no look-ahead)

57-trade sample (PostgreSQL, LONG, ride_it-mapped LIKE patterns, 30d — matches the claimed sample minus AVAX/15967), 5m candles time-sliced per trade, ATR(14) from 1h candles closed before each check (fixed chronological order), constants imported live from hermes_constants.py. Two stacks per scenario:

**Production-faithful stack** (hard stop + ride_it exit + stale_exit at -1.0%/8min stall + SOFT PEAK-EXIT 2h/0.3% + cut_loser T1 [-2.5..-1.0] for non-bypass signals + profit-monster/PM trail for non-bypass + ATR-engine trail 0.4% act/0.15% dist + UNIVERSAL_MAX_HOLD 8h for non-ride_it signals):

| Metric | Current (-1.0%) | Option B (-2.5%) | Delta |
|--------|----------------|-------------------|-------|
| WR | 54.4% | 57.9% | **+3.5pp** (claimed +10.5pp) |
| avg PnL (unleveraged) | +0.121% | +0.142% | +0.02pp (~unchanged — this part of the claim directionally holds) |
| total PnL | +6.9% | +8.1% | +1.2pp |
| max loss/trade | **-1.41%** | **-2.5%** | worst case doubles |
| avg hold | 1.02h | 1.28h | +0.26h |

**Isolated stack** (hard stop + ride_it exit only — closest reconstruction of the claimed backtest's apparent methodology, but with real data):

| Metric | Current | Option B | Delta |
|--------|---------|----------|-------|
| WR | 24.6% | 38.6% | +14.0pp |
| avg PnL | +0.033% | +0.280% | +0.25pp |
| total | +1.9% | +16.0% | +14.1pp |

Even the isolated reconstruction produces completely different absolute levels than claimed (24.6% vs 61.4% WR current) — the claimed numbers are not reproducible under any methodology I could construct from the real data.

**Per-signal (production stack):**
- `volume-breakout-long+` (n=27): WR 55.6%→63.0% (+7.4pp), avg +0.12%→+0.20% — improves most (directionally consistent with the claim, magnitude smaller than claimed +12.5pp/+0.31%)
- `trend-ride+` (n=7): WR 42.9%→42.9% (flat), avg **-0.31%→-0.43% (worse)** — contradicts the plan's premise that Option B makes ride_it's design "actually function" for trend-ride
- `mover+` (n=22): identical outcomes in both scenarios (PM trail + cut_loser T1 cap losses before the hard stop binds)

**Trade-level flips (production stack, 11 trades change):** 6 improve (WCT -1.21%→+0.64%, JUP -1.10%→+0.92%, ONDO -1.41%→-0.30%, GMX, WCT#2, SUPER trend-ride), **5 worsen** (DYDX -1.01%→-2.46%, USELESS -1.08%→-2.50%, HYPER -1.02%→-2.18%, JUP -1.07%→-1.69%, NOT -1.10%→-1.75%). Net +2 winners on n=57 = +3.5pp — well within binomial noise (1 trade = 1.75pp).

**Validation of my model against reality:** my production-current sim (WR 54.4%, avg +0.121%) approximates actual DB outcomes (WR 58.6%, avg +0.31% unleveraged) — same order of magnitude, unlike the claimed baseline (+9.485% avg, 30x reality).

### 3. Methodology flaws found in the claimed backtest (per audit checklist)

- **ATR:** cannot be verified (no script); my sim used the corrected chronological order (the ride_it_exit.py DESC-order bug fix at lines 60-63). Any sim replicating the pre-fix order would inflate ATR 14-103%.
- **Overlay systems NOT accounted for:** the claimed results show only `hard_stop`/`trail_hit`/`sl_hit` exits. Production also runs stale_exit (STALE_LOSER_MAX_LOSS=-1.0%, 8min stall), SOFT PEAK-EXIT (2h, 0.3% trail — applies to ride_it signals too, no exemption in position_manager.py:3322-3380), cut_loser T1 window [-2.5..-1.0] (applies to mover+ and to underscore-variant signals), PM/profit-monster trail, ATR-engine trail, and hard_tp. Under Option B, trades sitting at -1.0%..-2.5% that stall still get cut by stale_exit — part of the claimed "recovery" cohort never survives in production.
- **PM trail vs ride_it:** the claimed sim appears to model neither the production ATR/PM trail (which exits winners early — real trades closed at +0.1% to +8% pnl via atr_sl_hit/profit-monster-trail/hard_tp, while the claimed sim shows the same trades running to +20-42%) nor the interaction where PM trail (0.4% act) fires long before ride_it's phase-2 (+2% act).
- **Look-ahead / data alignment:** the claimed numbers look like they were computed against misaligned or fabricated candle/trade pairings (impossible PnLs, hard stops where no dip existed, results for trades closed before the claimed exit time, results for trades with no candle data).
- **Sample size:** 57 trades; only ~11 change outcome between scenarios in my sim; only 7 trend-ride+ trades. A +3.5pp realistic delta on n=57 is statistically indistinguishable from noise. Even the claimed +10.5pp (6 trades) would be thin evidence; the claimed magnitude is anyway unsupported.
- **Units confusion:** claimed avg +9.485% is unleveraged price move in the sim, but DB pnl_pct is 3x leveraged — the plan's risk table ("$11 × 2.5% = $0.28") mixes units; real realized hard_max_loss exits on these trades show slippage to -1.2%..-2.1% price move beyond the -1.0% trigger (check-cadence gaps), so the "-1.0% max loss" premise of the Current column is itself optimistic.

### 4. Additional findings (unrelated bugs spotted during audit)

1. **HIGH — underscore/hyphen bypass inconsistency.** `PROFIT_MONSTER_BYPASS_SIGNALS` contains only `volume-breakout` (hyphen). cut_loser.py SQL uses `signal LIKE '%volume-breakout%'`, so underscore-variant ride_it signals (`volume_breakout_long`, e.g. trade 15115 SOL) are NOT excluded from cut_loser — SOL was cut by cut-loser-CL-T1 at -1.79% price move even though it maps to ride_it exit via SIGNAL_EXIT_CONFIG underscore keys. Ride_it-managed trades are being cut by a different engine. Fix: add underscore variants to the bypass list, or normalize signal matching.
2. **MEDIUM — plan's exemption check vs exit-config mapping disagree.** SIGNAL_EXIT_CONFIG removed `mover+` from ride_it (2026-10-05 audit), but position_manager `_is_ride_it` substring check includes `'mover'` → the proposed Option B code would grant `mover+` trades a -2.5% hard stop while ride_it exit does NOT manage them (PM trail does). In my sim mover+ outcomes were unchanged (other engines fire first), but the inconsistency should be resolved before implementation.
3. **LOW — ride_it phase-1 SL "widen" gate:** `should_update = phase1_sl > current_sl * 1.0005 or phase1_sl < current_sl * 0.9995` (ride_it_exit.py:359) widens freely; combined with the 2h phase-1 window this can push SLs to the 2.5% cap on volatile entries — intended per design, but it means Option B's -2.5% hard stop is often the *same level* as the ride_it SL (plan acknowledges this) — the hard stop adds little protection beyond the SL itself.
4. **Data gap:** PONS has no 5m candles before 2026-10-01 (1h data covers it) — any 5m-granularity backtest silently loses/garbles older PONS trades.

---

## Assessment: Is Option B actually better?

**On my independent numbers: marginally, but not for the stated reasons, and not decisively.**

- The *direction* the claim asserts is weakly supported by my production-faithful sim: WR improves slightly (+3.5pp), avg PnL is roughly unchanged (+0.02pp), and volume-breakout-family trades do improve most (+7.4pp WR). The structural fix is real: ride_it's phase-1 SL becomes reachable, which was the point of the design.
- The *magnitude* claimed (+10.5pp, "max_loss=-2.5% with same total PnL") is not supported. It rests on backtest results that are physically impossible against the real candle data, produced by code that no longer exists, for a sample that includes trades with no data and trades that production had already closed.
- **trend-ride+ does not improve** in my sim (WR flat, avg worse) — the signal family the plan is most concerned about.
- **The cost is real and asymmetric:** worst-case loss per ride_it trade doubles (-1.0%→-2.5%, and real slippage means realized losses can exceed the trigger — observed hard_max_loss exits realized -1.2% to -2.1% price moves). 5 of 11 affected trades get worse; the 6 that improve do so by small amounts. On 57 trades the net is +1.2pp total — noise.

## Risks (if Option B is approved anyway)

1. Deeper tail losses: -$0.28 vs -$0.11 per losing trade at $11 notional; slippage can push realized loss past -2.5%.
2. Capital lock-up: avg hold +26%; some trades hold 2-4h+ where they previously died at -1%.
3. stale_exit/-1.0% and cut_loser T1 still cut stalled losers in the -1.0..-2.5 band — the "survive the wait" premise is only partially unblocked.
4. Evidence base: n=57, ~11 changed outcomes, 7 trend-ride+ trades — far below what would justify a risk-increasing change on its own merits.

## Recommendation

1. **Do not approve Option B on the basis of the claimed backtest** — the numbers are not real. Require the backtest author to produce the generator script and explain the impossible PnLs before any further consideration.
2. If the structural fix (ride_it SL reachable) is still desired, the honest path is: fix the underscore/hyphen cut_loser bypass inconsistency first, re-run a reproducible backtest (script committed to brain/verdicts/audit_scripts/) with production overlays, and/or run a **live A/B paper test** (e.g., 2-4 weeks, ride_it signals only, randomize hard stop -1.0% vs -2.5%) rather than scaling from 57 trades.
3. Consider a middle ground not evaluated here: -1.75% ride_it hard stop, or exempting only `volume-breakout*` (where my sim shows the improvement) while keeping -1.0% for trend-ride+ (where it doesn't).

---

*All numbers in this verdict were produced by running code against PostgreSQL (trades) and /root/.hermes/data/candles.db (candles) on 2026-10-06. Reproduction: `cd /root/.hermes/scripts && python3 ../brain/verdicts/audit_scripts/independent_ride_it_verify.py`.*
