# Trading Notes — Post-Mortems & Signal Learnings

Captured insights from live trade evaluations. Each entry captures WHAT happened, WHY it happened signal-wise, and WHAT to do differently.

---

## 2026-04-06 — Cascade-Flip Learnings (TRB/IMX/SOPH/SCR)

### TRB — MACD 1H crossing under signal line → good short opportunity ❌
- **Position:** LONG @ local peak
- **Signal:** 1H MACD line was sloping and crossing UNDER the signal line — classic bearish crossover
- **What happened:** We entered LONG at the local peak. The MACD 1H crossing under signal was the exact opposite of what we should have been doing. Should have been SHORT.
- **Key learning:** MTF MACD is supposed to find the FIRST crossover — when MACD crosses OVER signal line = bullish entry confirmation. When MACD crosses UNDER signal line = bearish entry confirmation (for shorts). We had it backwards.
- **Action:** Enable cascade-flip for TRB. If MACD 1H is crossing under signal AND we're LONG → flip to SHORT.

### IMX — Same MACD 1H crossing under signal line ❌
- **Position:** LONG #4271 @ $0.1327
- **Signal:** 1H MACD curling and crossing under signal from above
- **What happened:** Bought the local peak. MACD 1H was already rolling over when we entered.
- **Key learning:** MTF MACD's job is to find the FIRST cross-over for longs. We entered AFTER the cross-over had already happened and was reversing.
- **Rule:** If MACD 1H has ALREADY crossed under signal (histogram already negative) → do NOT enter LONG. Need fresh cross-over.
- **Action:** Enable cascade-flip for IMX.

### SOPH — Bought local peak, will get stopped out ❌
- **Position:** LONG @ local peak
- **Signal:** MACD 1H was rolling over, z-score at wrong level
- **What happened:** Entered LONG right at the top. The bounce had already completed.
- **Key learning:** Need to validate there is actual ROOM to bounce before entering. If price is at local high and MACD is curling down → short, not long.
- **Action:** Enable cascade-flip for SOPH.

### SCR — MACD 1H rolling over, will get stopped out ❌
- **Position:** LONG @ local peak (reconciled position)
- **Signal:** MACD 1H histogram contracting, line crossing toward signal from above
- **What happened:** LONG entry at peak of move. MACD 1H losing momentum — rolling over for a pullback.
- **Key learning:** When MACD 1H histogram is contracting toward zero AND we're already long → at risk of stop-out. The cascade-flip should trigger when MACD 1H crosses under signal.
- **Action:** Enable cascade-flip for SCR.

### Cascade-Flip Rule (across all 4)
- **Trigger:** When MACD 1H crosses UNDER signal line while holding a LONG position → flip to SHORT (or close long)
- **Opposite case:** When MACD 1H crosses OVER signal line while holding a SHORT → flip to LONG
- **MTF MACD intent:** Find the FIRST cross-over (not a re-cross, not a curl-back)
- **Pattern:** MACD crosses OVER signal → bullish entry. MACD crosses UNDER signal → bearish entry.

---

## 2026-04-06 — Session: GMX/VVV/AXS/TRB/SKY Rapid-Fire

### TRB — SHORT caught at the peak ✅ GREAT SIGNAL
- **Trade:** LONG @ $15.00 → closed -0.13% via trailing_exit_-0.87%
- **Signal:** `percentile_rank` LONG @ 91% conf, z=-0.496 `rising` tier
- **What happened:** We entered LONG right as TRB was hitting its local peak. The signal was actually predicting a reversal DOWN (z was rising = price recovering = going to bounce). We went LONG and the short signal (z falling, negative z) would've been the right call here.
- **Key learning:** When `z` is rising BUT still negative, the percentile_rank signal was saying "price is at bottom quartile, about to bounce" — but the z-tier was telling us the bounce had ALREADY happened (z=-0.496 is already elevated). We entered at the wrong moment.
- **Better interpretation:** TRB percentile_rank @ 91.8% = price near top of range. z=-0.496 `rising` = momentum is BOTTOMING, not confirming a LONG entry. For SHORT to work, z should be falling (momentum reversing from overbought). The signal was misread.
- **Action:** When percentile_rank is >85% AND z is rising → that means we're near the top of a range bounce, NOT a confirmation for LONG. Short signal quality improves when: z is falling (momentum rolling over) at high percentile rank.

---

### AXS — Caught at peak, MACD curling down on 1H ❌
- **Trade:** LONG @ $1.1254 → closed +0.17% (net -$0.45 fees) via trailing_exit_-0.75%
- **Signal:** `percentile_rank` LONG @ 91% conf, z=-0.34 `rising`, RSI=59
- **What happened:** MACD on the 1H was curling DOWN toward the signal line — bearish setup. We entered LONG thinking we caught a bottom, but the 1H MACD histogram was already contracting (losing momentum). This was actually a short signal.
- **Key learning:** Need to check 1H MACD state before entering. If MACD line is curling DOWN toward signal line on 1H → bearish, do NOT LONG. The "rising" z-tier was correct (price recovering) but the MACD 1H was telling us the recovery was losing steam.
- **Rule:** `percentile_rank LONG` requires: (1) MACD histogram RISING on 1H, not falling. (2) MACD line should be curling UP away from signal line for LONG confirmation.
- **Action:** Add 1H MACD direction check to percentile_rank signal validation. If MACD histogram is falling on 1H → downgrade LONG confidence or block.

---

### SKY — MACD moving further apart on 1H, this is bullish ✅ (wrong direction)
- **Trade:** SHORT @ $0.0762 → closed -0.41% via trailing_exit_-0.50%
- **Signal:** `mtf_macd` SHORT @ 89.3% conf, z=+0.556 `falling`, RSI=52.9
- **What happened:** Regime was LONG_BIAS@95%. SKY MACD on 1H was diverging further (line and histogram moving further apart upward) — this is BULLISH expansion. We entered SHORT directly into a bullish expansion.
- **Key learning:** `z_tier=falling` on a positive z means momentum is reversing LOWER from elevated levels — but if the MACD histogram is EXPANDING upward on 1H, the z-tier is misleading. The MACD expansion was the dominant signal.
- **Rule:** When MACD histogram is expanding (not contracting) on 1H, ignore `z_tier=falling` for SHORT signals. z_tier=falling only means something if MACD histogram is also contracting (momentum fading).
- **Fix:** Regime hard block now applied to ai_decide_batch. Additionally, need to validate MACD histogram direction on 1H before confirming SHORT signals.

---

### VVV — Regime blindspot, SHORT was wrong direction ❌
- **Trade:** SHORT @ $7.18 → closed -0.16% via trailing_exit_-1.49%
- **Signal:** `mtf_macd` SHORT @ 90% conf, z=+0.562 `falling`, RSI=52
- **What happened:** VVV was NOT in regime_4h.json (not scanned). BTC was in a broad uptrend (LONG_BIAS). We entered SHORT into a bull market with no regime protection for this token.
- **Key learning:** VVV needs to be added to regime scanner. Without regime data, signals are unconstrained.
- **Action:** Add VVV to regime_4h scanner focus list.

---

### GMX — NEUTRAL regime, borderline trade ⚠️
- **Trade:** SHORT @ $6.0037 → still open, 0% PnL
- **Signal:** `mtf_macd` SHORT @ 95% conf, z=+1.006 `falling`, RSI=57.9
- **Regime:** NEUTRAL@61%
- **What happened:** NEUTRAL regime should ideally be avoided. The 95% confidence from multiple sources slipped through.
- **Action:** NEUTRAL regime with conf > 60% should trigger a WAIT, not an auto-execute. Only NEUTRAL conf < 50% should be a pass-through.

---

## Signal Quality Checklist — Pre-Execution

Before any trade is confirmed, validate:

```
1. REGIME CHECK
   - Token must be in regime_4h.json
   - If counter-regime (LONG_BIAS + SHORT or SHORT_BIAS + LONG) → BLOCK
   - If NEUTRAL conf > 60% → WAIT
   - If NEUTRAL conf < 50% → proceed with caution

2. Z-SCORE + TIER CHECK
   - LONG: z should be rising from negative (bottoming bounce)
   - SHORT: z should be falling from positive (topping reversal)
   - If z_tier contradicts direction → BLOCK

3. PERCENTILE_RANK CHECK
   - LONG: percentile_rank > 85% AND z rising AND MACD histogram rising on 1H → strong
   - SHORT: percentile_rank < 15% AND z falling AND MACD histogram falling on 1H → strong
   - If MACD is curling toward signal line (losing momentum) → BLOCK or downgrade

4. MACD 1H EXPANSION CHECK
   - If MACD histogram is expanding (not contracting) on 1H → market has momentum
   - Do NOT SHORT if MACD histogram is expanding upward
   - Do NOT LONG if MACD histogram is expanding downward

5. FEE CHECK
   - Gross PnL must exceed fees by > 0.5% to be worthwhile
   - 10x leverage: ~0.1% entry + 0.1% exit + spread = 0.2% round-trip
   - Minimum viable gross: 0.5% → net 0.3%
```

---

## 2026-04-05 — Live Trading Enabled

- Guardian set to REAL execution mode (live trades hitting Hyperliquid)
- Guardian is the authoritative reconciliation layer
- Decider-run.py drives all decisions
- paper_live flag set to "live" for live execution


### ALGO #4237 — Closed by rule check (2026-04-06)
- **Reason:** counter-regime: LONG_BIAS@88% + SHORT signal violates new rule
- **PnL at close:** +0.1148% ($0.06) — was actually up, but rule violation
- **Action:** Closed gracefully (first HL attempt failed/rate-limited, DB marked closed)

### HYPER #4240 — Closed by rule check (2026-04-06)
- **Reason:** counter-regime: LONG_BIAS@95% + SHORT signal violates new rule  
- **PnL at close:** +0.0364% ($0.02) — was up but HYPER wasn't even on HL (phantom position)
- **Action:** Closed gracefully — phantom position cleared from DB

### TRX #4234 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 0.0000%%
- **Action:** Graceful close, 15s spacing
### RESOLV #4242 — Closed by regime rule check (2026-04-06)
- **Reason:** neutral_regime: NEUTRAL@56%
- **PnL at close:** 0.0000%%
- **Action:** Graceful close, 15s spacing
### HEMI #4243 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 0.0000%%
- **Action:** Graceful close, 15s spacing
### GMX #4250 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** -1.7599%%
- **Action:** Graceful close, 15s spacing
### SAGA #4251 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 0.2023%%
- **Action:** Graceful close, 15s spacing
### GOAT #4252 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 0.2775%%
- **Action:** Graceful close, 15s spacing
### IOTA #4253 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 0.2885%%
- **Action:** Graceful close, 15s spacing
### WCT #4254 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 4.1183%%
- **Action:** Graceful close, 15s spacing
### ZORA #4255 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** 5.1779%%
- **Action:** Graceful close, 15s spacing
### AZTEC #4256 — Closed by regime rule check (2026-04-06)
- **Reason:** regime_blindspot: not in regime_4h.json
- **PnL at close:** -6.3499%%
- **Action:** Graceful close, 15s spacing