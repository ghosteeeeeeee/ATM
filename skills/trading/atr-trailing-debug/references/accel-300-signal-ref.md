# Accel-300 Signal — Implementation Reference (2026-05-15)

## Signal Type
Self-contained momentum signal. Fires accelerated breakouts from EMA(300) on 15m candles. Does NOT own position tracking — relies on position_manager for SL/TP and exit decisions.

## Key Parameters
- `MIN_GAP_PCT = 0.20` — minimum gap % from EMA
- `MIN_GAP_GROWTH_PCT = 0.05` — minimum gap growth % to confirm acceleration
- `bars_since_cross >= 1` — hard requirement (reverted 2026-05-11 after regression)
- SHORT signal: `gap_then - gap_now` (gap growing = SHORT accelerating) — verified 2026-05-14

## Entry Flow
1. accel_300.py fires via signals_runner → writes to `signals_hermes_runtime.db` with source='accel-300+' or 'accel-300-'
2. signal_compactor merges with other sources (RS, trend_purity, etc.) for confluence
3. decider_run executes via `execute_trade()` — sl=0, tp=0 deferred to position_manager
4. position_manager computes ATR-based SL/TP on next cycle

## Critical Dependency
The signal sets direction and confidence, but exit decisions are entirely in position_manager's `_collect_atr_updates()` and `check_atr_tp_sl_hits()`. Bugs in position_manager's SHORT SL direction logic directly affect accel-300 SHORT trades.

**Known impact (2026-05-14):** FIL SHORT (accel-300-) closed in 4s at SL=1.007 (below entry) because position_manager's SHORT SL formula computed from `lowest_price=1.0` instead of `entry`.

## Debugging Commands
```bash
# Check recent accel-300 signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, confidence, source, created_at FROM signals \
   WHERE source LIKE 'accel-300%' ORDER BY created_at DESC LIMIT 20;"

# Check accel-300 entries in hotset
cat /var/www/hermes/data/hotset.json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); \
   accel=[e for e in d.get('hotset',[]) if 'accel-300' in e.get('source','')]; \
   print(f'accel entries: {len(accel)}'); \
   for e in accel: print(f\"  {e['token']} {e['direction']} conf={e['confidence']} src={e['source']}\")"
```

## Signal Parameters (from accel_300.py)
```
MIN_GAP_PCT = 0.20        # was 0.15 (reverted 2026-05-11)
MIN_GAP_GROWTH_PCT = 0.05 # was 0.03 (reverted 2026-05-11)
MIN_ACCEL_BARS = 1        # was 0 (reverted 2026-05-11)
MOMENTUM_CHECK = True     # accel must confirm momentum
GAP_TOLERANCE_PCT = 0.10  # secondary confirmation
```

## Bug History
| Date | Issue | Fix |
|------|-------|-----|
| 2026-05-11 | Parameters too loose — 8 tokens entered simultaneously in sideways market, all closed via atr_sl_hit | Reverted MIN_GAP_PCT→0.20, MIN_GAP_GROWTH_PCT→0.05, added bars_since_cross>=1 |
| 2026-05-14 | SHORT sign inverted — gap_growth negative but condition was `>0` blocking SHORT | gap_then - gap_now for SHORT (gap growing = accelerating downward) |
| 2026-05-15 | FIL SHORT: SL placed BELOW entry (position_manager SHORT SL bug) | position_manager fix — anchor SL to entry for new/in-profit SHORT |