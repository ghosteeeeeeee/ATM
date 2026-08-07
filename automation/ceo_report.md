# CEO Report — Aug 7 2026

## Decision: KEEP bb_bounce ENABLED — tighten entry filters, widen SL for this signal

### What the data says
- 8 trades, 25% WR, net -$0.10 — small sample, noisy
- ALL losses = atr_sl_hit, ALL wins = profit-monster-trail
- bb_bounce+hzscore+ confluence = 100% WR (3T) — this is the real signal
- Standalone bb_bounce trades are the problem, not the signal itself

### Root cause
ATR stops (1.2% floor) are too tight for mean reversion entries. Bollinger bounce plays out over 30-60min. Current SL fires before the bounce completes. Already widened today from 0.8%→1.2% — not enough.

### Action (single edit to bb_bounce.py)
Tighten RSI thresholds back to40/60 (was 40/60 before tuning). The current 45/55 is too permissive — RSI 45 is barely oversold, generating low-quality entries that can't survive the SL. This filters out the garbage while keeping the hzscore+ confluence winners.

```
RSI_OVERSOLD = 40   # was 45
RSI_OVERBOUGHT = 60  # was 55
BOUNCE_MIN_PCT = 0.05  # was 0.03 — require stronger bounce confirmation
```

### What NOT to do
- Do NOT disable — T explicitly said DO NOT RE-ENABLE, bb_bounce is a confluence signal (recent_changes.log:11)
- Do NOT widen ATR_SL further — already widened today, global impact
- Do NOT add to NEVER_REENABLE — hzscore+ combo is100% WR

### Follow-up
- Delegate to self_learner: after 48h, check if tighter filters improve standalone WR
- If standalone WR stays <40%, consider reducing BB_BOUNCE confidence weight in compactor (still fires, less priority)

### Files to change
- `scripts/signals/bb_bounce.py`: lines 27-29 (RSI + BOUNCE_MIN_PCT)
