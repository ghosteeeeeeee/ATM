# Things to Monitor

## 1. Accel-300 Flip Rule

**Status:** Active — producing mixed results

**Rule:** z-score contradicts signal direction → flip (trend signals only)
- LONG + z > 0.5 → flip to SHORT (always)
- SHORT + z < -0.5 → flip to LONG (unless accel confirms SHORT)

**Recent wins from flips:**
- TAO SHORT +0.37% (accel-300-vel+ flipped to SHORT)
- AVNT SHORT +0.71% (accel-300-vel+ flipped to SHORT)
- ZK SHORT +0.32% (tl_break_long flipped to SHORT)
- LINK SHORT +0.57% (tl_break_long flipped to SHORT)

**Recent losses from flips:**
- ME SHORT -0.35% (accel-300-vel+ flipped to SHORT)
- TURBO SHORT -0.53% (accel-300-vel+ flipped to SHORT)
- FET SHORT -0.46% (accel-300-vel+ flipped to SHORT)
- MOVE LONG -0.60% (tl_break_short flipped to LONG)

**Watch for:**
- Velocity ignition signals (accel-300-vel) being flipped when momentum confirms
- Whether flips on tl_break signals are net positive vs negative
- Total PnL impact of flips over 7-day window

---

## 2. ATR SL Slip (0.5% Floor Too Tight)

**Status:** Active — causing slippage on volatile tokens

**Issue:** `decider_run.py` sets initial SL at `ATR_SL_MIN_INIT` (0.5%), but position_manager's ATR-based SL (wider) isn't applied until next cycle. On fast moves, the 0.5% SL gets hit and slipped before ATR-based SL takes over.

**Affected trades:**
- MOVE LONG: SL at 0.50%, exit 0.82% below entry (0.32% slip)
- KAITO SHORT: SL at 0.50%, exit 0.70% above entry (0.20% slip)

**Root cause:** 5m candle ranges on volatile tokens (MOVE: 0.50%, KAITO: 1.22%) exceed the 0.5% SL. Price blows through in a single bar.

**Potential fix:** Set initial SL based on ATR, not fixed 0.5% floor. Or add minimum SL distance based on recent range.

---

## 3. Z-Score Chasing Entries (Losing Streak 08:00-10:00 UTC)

**Status:** Mitigated by context gate, but monitor

**Issue:** During 2026-07-31 losing streak, 81 LONG signals fired with avg z=0.11 (11 with z>0.5 = overbought). System was buying overbought tokens. Result: 9.1% WR on LONG signals.

**Mitigation:** Context gate rule 6b flips LONG with z > 0.5 to SHORT.

**Watch for:**
- Whether flips during losing streaks are net positive
- If market regime changes (ranging vs trending) affect flip accuracy
- Signal quality during 08:00-12:00 UTC window

---

## 4. Context Gate Z-Score Source Mismatch

**Status:** Fixed — now uses signal metadata

**Issue:** Context gate computed z-score independently from signal. Signal might have z=-0.41 (confirms SHORT), but context gate computed z=+0.6 at execution time and flipped it.

**Fix:** Context gate now uses signal's own z-score, phase, and momentum when available.

**Watch for:**
- Whether signal metadata is always available and fresh
- If speed_tracker values diverge significantly from signal metadata

---

## 5. Accel-300 Signal Re-enablement

**Status:** Disabled — waiting for velocity ignition mode to prove itself

**Current state:**
- `ACCEL_300_ENABLED = False`
- `ACCEL_300_PLUS_ENABLED = False`
- `ACCEL_300_MINUS_ENABLED = False`

**Changes made:**
- Added velocity ignition mode (`detect_velocity_ignition`)
- Tightened PERSISTENCE_BARS from 18 to 10
- Tightened STALE_BARS from 25 to 15
- Changed MIN_GAP_GROWTH from -0.10 to 0.02

**Watch for:**
- Whether velocity ignition signals have better WR than standard accel-300
- If tighter parameters reduce false signals
- Backtest results before re-enabling

---

## 6. Dead Hours Filter Effectiveness

**Status:** Active — filtering 03:00-08:00 UTC

**Historical data:**
- Dead hours (03-08 UTC): 16.2% WR across 68 trades
- Active hours: 35% WR

**Watch for:**
- Whether dead hours filter is still accurate
- If market patterns shift (crypto is 24/7)
- Edge cases where good trades happen during dead hours

---

## 7. Signal Inversion (accel-300+ LONG / accel-300- SHORT)

**Status:** Disabled — was producing 3-7% WR

**Historical data:**
- accel-300+ LONG: 53 signals, 3.8% WR (30d)
- accel-300- SHORT: 71 signals, 2.8% WR (30d)

**Watch for:**
- Whether re-enabling with velocity ignition mode changes WR
- If new parameters (tighter persistence, stale bars) help
- Backtest results before re-enabling

---

## 8. Context Gate Performance

**Status:** Active — rule-based + LLM fallback

**Rules:**
- Speed < 20% → SKIP
- |z| > 1.5 + speed < 50 + counter-trend → SKIP
- |z| < 0.5 + speed < 25 → SKIP
- Speed > 70% + z confirms direction → GO
- Wrong phase for signal type → SKIP
- Phase contradicts direction → FLIP
- Z-score contradicts direction → FLIP

**Watch for:**
- LLM gate accuracy (currently 5-10 calls/hr)
- Whether rule-based gates are catching most bad trades
- False positive rate (blocking good trades)

---

## 9. Moving Average Confluence

**Status:** Active — `ACCEL_300_BLOCK_COSIGS` blocks signals with conflicting co-signals

**Blocked co-signals:**
- `ma-cross-5m+` (16.7% WR)
- `pct-hermes+` (35.7% WR)

**Watch for:**
- Whether blocked co-signals improve or hurt performance
- If new co-signals should be added to blocklist
- Co-signal effectiveness over time

---

## 10. Token-Specific Performance

**Status:** Active — tracking per-token WR

**Current allowlist:** Empty (no filter, fire on all tokens)

**Watch for:**
- Tokens with <50% WR and >=3 trades (should be blocked)
- Tokens with consistently good performance (potential allowlist)
- Delisted tokens that might still be in signal pipeline

---

## 11. Z-Score Direction Filter (Signal Generation)

**Status:** Active — added 2026-07-31

**Issue:** Signal generation was firing LONG when z < -0.5 (price below average). During 08:00-09:30 losing streak, 26% of LONG signals had z < -0.5 — chasing downtrends.

**Fix:** Added z-score filter to tl_break.py and accel_300.py:
- Block LONG when z < -0.5 (price below average)
- Block SHORT when z > 0.5 (price above average)

**Impact:** Should reduce bad signals at source, not just at context gate.

**Watch for:**
- Whether this reduces signal count significantly
- If it catches the wrong-direction signals before they reach context gate
- Impact on overall WR and PnL over 7-day window

---

## 12. TP/SL Rebalance (Proposed)

**Status:** Planned — see `plans/2026-07-31_tp-sl-rebalance.md`

**Issue:** Current TP/SL settings have 7.3% WR on backtest. 5/9 recent trades had favorable moves but hit SL instead of TP.

**Proposed Changes:**
- ATR_TP_MIN: 1.5% → 1.0% (catch profits before reversal)
- ATR_SL_MIN_INIT: 0.5% → 0.75% (survive normal retracements)
- TRAILING_ACTIVATION: 0.5% → 0.3% (lock profits sooner)
- TRAILING_DISTANCE: 0.4% → 0.5% (give trades room)

**Backtest Results:**
- Current: WR=7.3%, PnL=+3.93%
- Proposed A: WR=39.0%, PnL=+6.27% ← WINNER

**Watch for:**
- WR improvement from 37% to 39%+
- PnL improvement from +$0.31 to +$0.50+ per day
- Max drawdown staying below 5%

---

## 13. Token Sentiment Filter (Hebbian Phase 3a)

**Status:** Implemented — DISABLED by default (`TOKEN_SENTIMENT_ENABLED=False`)

**Implementation:**
- `hebbian_engine.py`: `token_sentiment(token, k=20)` → returns -1.0 to +1.0
- `decider_run.py`: wired into context gate after similar_setup_lookup
- Skips tokens with sentiment ≤ -0.7 (negative history)
- Hard skips tokens with sentiment ≤ -0.85 (chronic losers)
- Boosts tokens with sentiment ≥ +0.7 (+3 confidence)

**Watch for:**
- Whether chronic loser filter reduces bad entries without blocking good tokens
- If sentiment scores are meaningful (need 50+ trades with decision labels)
- Backtest results before enabling live

---

## Last Updated

2026-08-02: Added token sentiment filter (item 13)
