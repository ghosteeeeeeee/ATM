# Reminder: Enable Risk-Reward Engine (Exit Shadow Mode)

**Created:** 2026-09-02
**Due:** 2026-09-05 (3 days) → Full enable by 2026-09-09 (7 days shadow)
**Priority:** HIGH

## What to do

1. Check shadow mode data:
   ```bash
   grep "SHADOW BLOCK" /root/.hermes/logs/pipeline.log | tail -50
   ```

2. Cross-reference blocked signals with actual trade outcomes:
   - If blocked signals had <40% WR → the engine is working, enable it
   - If blocked signals had >50% WR → engine is too aggressive, tune thresholds

3. Enable enforcement:
   ```python
   # In hermes_constants.py, change:
   RR_ENGINE_SHADOW = False      # was True
   RR_ENGINE_FORCE = True        # was False
   RR_ENGINE_CONF_SHADOW = False # was True
   ```

4. Commit:
   ```bash
   cd /root/.hermes && git add -A && git commit -m "feat: RR engine exit shadow mode — enforcement enabled"
   ```

## Current state (as of 2026-09-02)

- `RR_ENGINE_ENABLED = True`
- `RR_ENGINE_SHADOW = True` (logs but doesn't block)
- `RR_ENGINE_FORCE = False`
- `RR_ENGINE_CONF_ENABLED = True`
- `RR_ENGINE_CONF_SHADOW = True` (logs but doesn't adjust confidence)

## What the engine does

- Evaluates structural R:R using multi-source S/R (candle swings + order book + liquidation clusters)
- Adjusts confidence: 0.0x (hard block) to 1.30x (exceptional setup)
- If R:R < 1.0 → trade killed (0.0x multiplier)
- If R:R 4.0+ Grade A → 1.30x confidence boost

## Files

- `scripts/risk_reward_engine.py` — core engine
- `scripts/entry_gates.py` — rr_gate() integration
- `scripts/signal_compactor.py` — rr_mult in _score_signal()
- `scripts/hermes_constants.py` — RR_ENGINE_* constants
- `brain/specs/risk_reward_engine_spec.md` — spec
- `brain/specs/rr_engine_bug_hunt.md` — bug hunt report
- `brain/specs/rr_engine_post_change.md` — verification report
