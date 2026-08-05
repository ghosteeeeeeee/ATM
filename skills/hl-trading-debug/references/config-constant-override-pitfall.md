# Config File Constant Override Pitfall

## The Pattern

Scripts that define module-level constants in `hermes_constants.py` but then use `cfg.get()` with those constants as defaults:

```python
# In hermes_constants.py:
PROFIT_MIN_PCT = 1.0
PROFIT_MAX_PCT = 2.0

# In profit_monster.py — WRONG pattern:
min_pct = cfg.get("min_profit_pct", PROFIT_MIN_PCT)   # config wins if key exists
max_pct = cfg.get("max_profit_pct", PROFIT_MAX_PCT)   # config wins if key exists
```

When the config JSON file has a key for these values, the config **always wins** — the constants in `hermes_constants.py` become dead code. This is silent: no error, no warning, the script runs fine but uses wrong thresholds.

## Symptoms

- Profit Monster closing at 0.5% instead of 1.0% (config: `min_profit_pct=0.5`, constant: `PROFIT_MIN_PCT=1.0`)
- Cut Loser cutting losers at wrong thresholds
- Any script with numeric constants that seem to be ignored

## Investigation

1. Read the script — check if it uses `cfg.get("key", CONSTANT)` pattern
2. Read the config file — see if the key exists with a different value than the constant
3. The constant is the intended value (commented in `hermes_constants.py`); the config is the override

## Fix

Remove the `cfg.get()` fallback so the constant is always used:

```python
# RIGHT — constants are the only source
in_range = filter_profitable_positions(positions, PROFIT_MIN_PCT, PROFIT_MAX_PCT)
to_close = select_positions(in_range, max_close=MAX_CLOSE_PER_WAKE, skip_top_pct=SKIP_TOP_PCT)
```

Keep only non-numeric config keys (enabled, ab_group, dry_run).

## Affected Scripts

- `profit_monster.py` — was using cfg for `min_profit_pct`, `max_profit_pct`, `max_closes_per_wake`, `skip_top_pct`
- `cut_loser.py` — same pattern, check before debugging
- Any other script that imports from `hermes_constants` AND has a corresponding JSON config file

## General Rule

If `hermes_constants.py` is supposed to be the single source of truth for a numeric value, the script must NOT use `cfg.get(key, CONSTANT)` — it must use the constant directly. Config files can still exist for state (enabled, ab_group, dry_run) but numeric thresholds belong in constants only.