# ATR Architecture Reference

> ⚠️ **VERIFIED against live hermes_constants.py (2026-05-12)** — inline comments and older reference docs are frequently stale. Always cross-check against the actual source via `grep -n "ATR_" hermes_constants.py`.

## Live constant values (2026-05-12)

```
ATR_SL_MIN         = 0.002   # 0.20% floor
ATR_SL_MAX         = 0.005   # 0.50% cap
ATR_TP_MIN         = 0.015   # 1.5% floor
ATR_TP_MAX         = 0.05    # 5.0% cap
ATR_TP_K_MULT      = 1.25    # TP = k × 1.25 × ATR
ATR_SL_MIN_ACCEL   = 0.005   # 0.50% floor — ACCELERATION phase
ATR_TP_MIN_ACCEL   = 0.006   # 0.60% floor — ACCELERATION phase
ATR_SL_MIN_INIT    = 0.002   # 0.20% — new trades (breathing room)
ATR_SL_MAX_INIT    = 0.005   # 0.50% — new trades cap
SL_PCT_FALLBACK    = 0.015   # 1.5% if ATR unavailable
ATR_K_INITIAL      = 1.0     # initial SL k
ATR_K_LOW_VOL      = 0.5     # atr_pct < 1%
ATR_K_NORMAL_VOL   = 0.75    # 1% <= atr_pct <= 3%
ATR_K_HIGH_VOL     = 1.0     # atr_pct > 3%
ATR_PCT_LOW_THRESH = 0.01    # 1%
ATR_PCT_HIGH_THRESH= 0.03    # 3%
K_PHASE_ACCEL_STALL= 0.15
K_PHASE_ACCEL_FAST = 0.05
K_PHASE_ACCEL_SLOW = 0.10
K_PHASE_EXH_STALL  = 0.25
K_PHASE_EXH_FAST   = 0.15
K_PHASE_EXH_SLOW   = 0.10
K_PHASE_EXT_STALL  = 0.10
K_PHASE_EXT_FAST   = 0.05
```

## Stale values that appear in older docs (DO NOT USE)

| Stale value | Correct value | Notes |
|-------------|---------------|-------|
| ATR_SL_MAX = 0.010 (1.0%) | 0.005 (0.50%) | Older reference docs |
| ATR_SL_MIN_INIT = 0.01 (1.0%) | 0.002 (0.20%) | Old comments |
| ATR_SL_MAX_INIT = 0.01 (1.0%) | 0.005 (0.50%) | Old comments |
| ATR_SL_MIN_ACCEL = 0.002 (0.20%) | 0.005 (0.50%) | Was 0.20% before 2026-05-12 |
| K_PHASE_EXH_STALL = 0.40 | 0.25 | |
| K_PHASE_EXH_FAST = 0.40 | 0.15 | |
| K_PHASE_EXH_SLOW = 0.50 | 0.10 | |
| base_k = 1.0/2.0/2.5 | 0.5/0.75/1.0 | |

## _collect_atr_updates Flow (position_manager.py ~1550–1670)

```
1. Deduplicate tokens — one ATR fetch per unique token
2. _force_fresh_atr(token) → ATR(14) from cache (<300s) / HL API / Binance
3. _atr_sl_k_scaled(token, direction, atr_pct, speed, momentum) → k multiplier
4. sl_pct = k × atr_pct
5. effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING) — floor applied
6. Phase-based floor: ACCEL=0.50%, INIT=0.20%, ESTABLISHED=0.50%
7. ref_price = highest_price (LONG) or lowest_price (SHORT)
8. new_sl = round(ref_price × (1 - effective_sl_pct), 8)
9. new_tp = round(ref_price × (1 + effective_tp_pct), 8)
10. _persist_atr_levels() → write SL/TP to DB
```

### is_new_trade gate (lines 1620–1626)
If `|peak - entry| / entry < 0.001` (0.1%) AND in profit → uses base k, bypasses `_atr_sl_k_scaled` phase multiplier.

## _atr_sl_k_scaled() k multiplier

### base_k from _atr_multiplier()
```
atr_pct < 1.0%  → k=0.5  (LOW_VOL)
atr_pct 1-3%    → k=0.75 (NORMAL)
atr_pct > 3.0%  → k=1.0  (HIGH_VOL)
```

### Phase multipliers applied to base_k
```
phase < 2 (neutral/building):  k = base_k (no change)
phase == 2 (accelerating):
  stalling=True  → mult=0.15
  pctl>=70+fast  → mult=0.05
  slow           → mult=0.10
phase == 3 (exhaustion):
  stalling=True  → mult=0.25
  fast           → mult=0.15
  slow           → mult=0.10
phase == 4 (extreme):
  stalling=True  → mult=0.10
  fast           → mult=0.05
```

Phase detection uses **direction-specific percentile** (percentile_long for LONG, percentile_short for SHORT).

## _force_fresh_atr Fallback Chain

```
1. Try atr_cache.json — fresh if < 300s old
2. HL API candles_snapshot → ATR(14) from 15m candles
3. Binance public API fallback
4. Save result to atr_cache.json
```

If ATR is None: trade skipped in `_collect_atr_updates` (line ~1554: `if atr is None: continue`).

## Key Files

| File | Role |
|------|------|
| `position_manager.py` | `_collect_atr_updates` (~1550–1670), `_atr_sl_k_scaled`, `_persist_atr_levels` |
| `hermes_constants.py` | All ATR_* and K_PHASE_* constants (authoritative source) |
| `signal_gen.py` | Phase definitions, `detect_phase()`, `get_momentum_stats()` |
| `brain.py` | `add_trade()` — peak initialization on INSERT |
| `hl-sync-guardian.py` | Seeds peaks for existing trades, safety net |
| `atr_cache.json` | Live ATR values (written by position_manager every cycle) |

## No hardcoding confirmed (2026-05-12)

All ATR SL/TP values in `position_manager.py`, `self_close_watcher.py`, and `hl-sync-guardian.py` come from `hermes_constants.py`. No numeric literals override these values anywhere in the ATR computation path. The only hardcoded values are:
- `0.001` — is_new_trade detection threshold (0.1% price change)
- `0.95` — stale accel floor detection multiplier (`ATR_SL_MIN_INIT * 0.95`)
- `CLOSE_SLIPPAGE = 0.005` — hl-sync-guardian slippage for emergency closes