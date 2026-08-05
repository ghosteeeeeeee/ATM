# mtp-zscore Signal — Implementation Path

**Created:** 2026-05-27
**Signal:** Multi-Timeperiod Z-Score (trend-following, ALL 3/3 periods agree)

## What was built

- `scripts/signals/mtp_zscore.py` — NEW — detection engine (~405 lines)
- `scripts/signals/__init__.py` — MODIFIED — import + registry + name_to_module
- `scripts/signal_compactor.py` — MODIFIED — SOURCE_WEIGHTS entries
- `scripts/hermes_constants.py` — MODIFIED — 14 new constants (lines 612-638)

## Constants Added to hermes_constants.py

```python
MTP_ZSCORE_ENABLED         = True    # master kill-switch
MTP_ZSCORE_PLUS_ENABLED   = True    # LONG
MTP_ZSCORE_MINUS_ENABLED  = True    # SHORT

MTP_ZSCORE_LB_SHORT       = 50      # fast period
MTP_ZSCORE_LB_MID         = 100     # medium period
MTP_ZSCORE_LB_LONG        = 150     # structural period

Z_SHORT_Z_MIN             = 0.5
Z_SHORT_Z_MAX             = 2.0
Z_MID_Z_MIN               = 0.5
Z_MID_Z_MAX               = 2.5
Z_LONG_Z_MIN              = 0.5
Z_LONG_Z_MAX              = 3.0

MTP_ZSCORE_MIN_AGREE      = 3       # 3/3 — ALL periods must vote same direction
MTP_ZSCORE_BASE_CONF      = 80
MTP_ZSCORE_CONF_BONUS     = 5       # reserved for future 2/3 vs 3/3 tiering
MTP_ZSCORE_COOLDOWN_BARS  = 20      # bars (1m = 20 min)
```

## Registration in signals/__init__.py

**Import block** (after zscore_pump import):
```python
try:
    from signals.mtp_zscore import scan_mtp_zscore_signals as _mtp_zscore_run
except Exception:
    _mtp_zscore_run = None
```

**hermes_constants import** (add to existing from block):
```python
MTP_ZSCORE_ENABLED, MTP_ZSCORE_PLUS_ENABLED, MTP_ZSCORE_MINUS_ENABLED,
```

**SIGNAL_REGISTRY entry** (after zscore_pump):
```python
{'name': 'mtp_zscore', 'enabled': MTP_ZSCORE_ENABLED, 'run': _mtp_zscore_run},
```

**name_to_module dict** (inside `run_all_signals()` — local dict, not module-level):
```python
'name_to_module': {
    # ... existing entries ...
    'mtp_zscore': 'scan_mtp_zscore_signals',
}
```

## SOURCE_WEIGHTS in signal_compactor.py

```python
('mtp_zscore_long',   'mtp-zscore+'):  1.25,  # 3-period upward momentum
('mtp_zscore_short',  'mtp-zscore-'):  1.25,  # 3-period downward momentum
```

## Key Design Decisions

| Decision | Value |
|----------|-------|
| Fire condition | ALL 3/3 periods agree AND all within Z_MIN/Z_MAX bounds |
| Direction | From sign of z (z>0=LONG, z<0=SHORT); abs(z) ONLY for bounds |
| Divergence gate | NONE — trend-following, not mean-reversion |
| z_score stored | Average of the 3 agreeing period z-scores |
| z_score_tier | JSON string with per-period z values + agree_count |
| Cooldown | 20 bars (~20 min) via set_cooldown() |
| Blacklist | SHORT_BLACKLIST blocks all directions; LONG_BLACKLIST blocks LONG only |

## Implementation pitfalls caught during ai-engineer review

**DRY_RUN module level:** `DRY_RUN = '--dry' in sys.argv` is at MODULE level (line ~70), NOT inside the scanner function. Read by the `if __name__ == '__main__':` block.

**name_to_module is local:** `name_to_module` dict is INSIDE `run_all_signals()` at ~line 305 — not a module-level registry. Include full dict context when adding.

**z_score_tier must be explicit JSON:** zscore_pump passes `z_score_tier=None` — silently loses per-period data. mtp_zscore MUST construct and pass JSON:
```python
z_score_tier=json.dumps({
    'z_short': round(z_short, 3),
    'z_mid':   round(z_mid, 3),
    'z_long':  round(z_long, 3),
    'agree_count': 3,
})
```
Requires `import json` — zscore_pump doesn't have this.

**Two staleness check layers:**
- 120s direct check on price_history timestamps (inside `_get_1m_prices`)
- 10min scanner-level check via `price_age_minutes()` in `scan_mtp_zscore_signals`
Both apply — different layers, different purposes.

## Verification Commands

```bash
# Dry run
cd /root/.hermes/scripts && python3 signals/mtp_zscore.py --dry

# Check signals in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, source, z_score, created_at \
   FROM signals WHERE signal_type LIKE 'mtp_zscore%' ORDER BY created_at DESC LIMIT 5;"

# Verify no HL API calls
grep -rn "http_post\|requests\." signals/mtp_zscore.py

# Verify import works
cd /root/.hermes/scripts && python3 -c "from signals.mtp_zscore import scan_mtp_zscore_signals; print('OK')"
```

## Staleness Warning (expected on cold machine)

When run with old price_history data (last ts > 120s), all tokens show `[mtp-zscore] TOKEN: stale price_history — skipping`. This is correct — the 120s staleness gate is working. Signal fires normally when price data is fresh.