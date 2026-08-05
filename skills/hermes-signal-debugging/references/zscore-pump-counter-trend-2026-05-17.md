# zscore-pump Counter-Trend Fires — ATOM (2026-05-17)

## What Happened
ATOM was marching straight up (~2% gain). zscore-pump- SHORT fired with rs-r78 confluence, then closed at a loss.

**The zscore_pump.py direction logic is CORRECT as-is:**
```python
# zscore_pump.py line 190 — ALREADY CORRECT
direction = 'LONG' if z > 0 else 'SHORT'  # positive z = upward momentum → LONG
```

The SHORT signal was wrong not because of inversion, but because zscore-pump is a **short-term momentum signal** — it detected a brief pullback negative z even though the major trend was up.

## T's Rule
**Counter-regime signals should NOT be blocked at the signal level.** Let the per-coin regime filter decide whether to escalate or de-escalate. Do not hard-block signals based on regime at the signal generation layer.

## Implication
zscore-pump SHORT can fire against a major uptrend if short-term momentum turns negative. The fix is NOT in zscore_pump.py direction logic — it's that the decider or regime filter should require regime alignment before acting on counter-trend zscore-pump signals.

## Files
- `signals/zscore_pump.py` line 190 — direction logic (correct)
- `signals/rs.py` — rs-r78 resistance/confluence signal
- `signal_compactor.py` / `decider_run.py` — regime filter application