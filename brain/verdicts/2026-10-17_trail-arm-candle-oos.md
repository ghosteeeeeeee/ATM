# Trail-Arm-Timeout Candle-Level OOS Verdict — 2026-10-17 12:00 UTC (brain_auditor captain run)

**Method:** as-coded condition (`position_manager.py:3589`): still open at age≥T AND live_pnl
(unleveraged %) < 0.40 → close now. 30d LONG closed trades, 1m candle close at open_time+T
as the live mark. Counterfactual $ = amount_usdt × lp/100 (amount is NOTIONAL; pnl_usdt =
amount × unleveraged move — leverage is margin metadata, does NOT scale pnl_usdt).
Script: `analysis/trail_arm_candle_oos_2026-10-17.py` / `.out`.

This is the same test class that killed universal MFE-CUT (selection-on-outcome in the
trades-level "never-armed" cohorts). Trades-level counters look at FINAL MFE; the code
only sees live_pnl at T. Candle OOS evaluates the code as it actually behaves.

## Results (30d)

| Cohort | T | fires (winners_FK) | NET if fired | saves | costs | fk % of cohort winners | Verdict |
|--------|---|--------------------|--------------|-------|-------|------------------------|---------|
| pump-chain+ LIVE | 45m | 60 (21) | **−$0.13** | +$3.18 | −$3.31 | **36.8%** | NEUTRAL — keep, but "immune" claim retracted |
| bb-squeeze+ LIVE | 60m | 20 (5) | **+$1.02** | +$1.37 | −$0.35 | 11.1% | **PASS — CONFIRMED** |
| bb-bounce SHADOW | 55m | 33 (18) | +$0.31 | +$1.03 | −$0.71 | **41.9%** | **FAIL flip (fk bar)** |
| ai-trader SHADOW | 55m | 3 (0) | +$0.26 | +$0.26 | $0.00 | 0% | INSUFFICIENT n — keep shadow |

## Key findings

1. **pump-chain LIVE45 is a wash, not the +$1.48 the trades-level counterfactual claimed.**
   The original "≥45m winners all MFE 2-10% → structurally immune" argument was
   selection-on-outcome: FOGO/AVAX/ADA/JUP were all <0.40% unleveraged at T=45m yet ended
   +4.2% to +6.2% unleveraged. Slow grinders that spike AFTER the check. Saves ($3.18) ≈
   costs ($3.31). fk 36.8% of winners is over the 20% bar, but net ≈ $0 and the mechanism
   is live since Oct 12 with pump-chain+ still the #1 money maker — **no change during
   pause; churn risk > $0.13/30d edge.**

2. **bb-squeeze LIVE60 CONFIRMED** under the harsher test (+$1.02, fk 11.1%). The original
   Oct 12 PASS verdict holds.

3. **bb-bounce T=55 flip path FAILS.** Net +$0.31 is positive but bought by false-killing
   41.9% of cohort winners (bar: ≤20%). Bounce winners run late (MNT/HBAR/ETH flat at
   55m then trail out). Keep shadow collecting (zero behavior); do NOT flip without a
   redesign (e.g., T≥80m or life-detector) that clears the fk bar on fresh OOS.

4. **ai-trader T=55:** only 3 fires/30d — mechanism barely engages (most losers die <55m
   or win earlier). Keep shadow; not worth flipping for $0.26/30d.

5. **Units landmine (systemic):** `pnl_pct` is LEVERAGED % (price_move × lev) while
   `pnl_usdt` = amount_usdt × unleveraged move. Any counterfactual mixing live_pnl
   (unleveraged) with pnl_pct (leveraged) or multiplying pnl_usdt by lev will be ~5×
   wrong. Documented here because MFE-CUT OOS and future exit-ladder work must use
   cf = amount_usdt × live_pnl/100.

## Actions taken

- hermes_constants.py comments updated: pump-chain "structurally immune" retracted →
  "as-coded candle OOS net ≈ 0, fk 37% — accepted wash"; bb-bounce shadow comment gains
  FAIL-flip note. Zero behavior change (comments only).
- Flip candidates for exit-ladder commission: **signal-scoped only**; bb-squeeze pattern
  is the template. Universal cuts remain dead (MFE-CUT verdict same day).
