# Hermes Signal Execution Path — Architecture Reference

## Execution Chain (as of 2026-05-12)

```
signals_runner.py (systemd timer every 1 min)
  └── accel_300.py / rs.py / hh_hl.py etc.
        └── add_signal() → RUNTIME_DB (/root/.hermes/data/signals_hermes_runtime.db)
              table: signals (id, token, signal_type, source, decision, created_at, executed, hot_cycle_count, survival_rounds)

signal_compactor.py (systemd hermes-pipeline.timer every 1 min)
  └── reads RUNTIME_DB (decision=PENDING)
  └── applies confluence gate (2+ unique signal_types required) — signal_compactor.py:545-558
  └── applies hh_hl filter (required for all entries) — signal_compactor.py:882
  └── applies regime scoring multiplier (aligned=1.5x, counter=0.5x) — signal_compactor.py:253-266
  └── writes hotset.json (/var/www/hermes/data/hotset.json)
  └── marks signals APPROVED in RUNTIME_DB (decision='APPROVED')

decider_run.py (runs after signal_compactor in same pipeline)
  └── reads RUNTIME_DB via get_approved_signals() — returns WHERE decision='APPROVED' AND executed=0
  └── reads hotset.json → _hot_tokens list — decider_run.py:905-923
  └── HOT-SET GATE at line 1538: if token not in _hot_tokens → BLOCKED
  └── writes trades to PostgreSQL brain DB
  └── marks signals executed in RUNTIME_DB
```

## Key Discovery: decider_run hot-set gate is the enforcement point

`get_approved_signals()` reads from RUNTIME_DB APPROVED column — signals can persist in DB after hotset.json rotates.
decider_run.py:1538 is where non-hotset signals are blocked:
```python
if not in_hotset:
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} NOT in hot-set — bypass attempt blocked')
    continue
```

## Regime Filtering — Currently SOFT only (2026-05-11 disabled hard block)

- `get_regime_1m()` at signal_compactor.py:113 uses 50-bar 1m LR (not 100)
- Scoring multiplier applies in signal_compactor (aligned=1.5x, counter=0.5x)
- Hard execution block at decider_run.py:1698-1708 was **DISABLED 2026-05-11** — too noisy for 1m
- User may want to re-enable hard regime filtering — block counter-regime signals at decider_run

## Confluence Gate — Known-Good Standalone Exception

The confluence gate (signal_compactor.py:545-558) has an exception for known-good signals:
```python
# Known good standalone signals (avg_pnl >= 0) can pass on their own merit
```
`accel-300+` / `accel-300-` are known good standalone signals — they pass as single source because they make money historically. This is intentional.

## Ghost Trade Review (2026-05-12 08:41)

All 5 live trades opened LEGITIMATELY from hot-set entries:

| Token | Dir | Sources | Hot-Set Entry | Status |
|-------|-----|---------|---------------|--------|
| GALA | LONG | `accel-300+,rs-s360` | 07:49 | dual-source ✓ |
| STRK | SHORT | `accel-300-` | 07:54 | single (known-good) ✓ |
| ZEN | LONG | `accel-300+` | 08:09 | single (known-good) ✓ |
| APEX | LONG | `accel-300+,rs-s130` | 08:17 | dual-source ✓ |
| SNX | LONG | `accel-300+,rs-s240` | 08:17 | dual-source ✓ |

All 5 show `in_hotset=False` at 08:41 — gate IS blocking re-execution after hot-set rotated.

## accel-300 naming convention — hyphen vs underscore

- accel_300.py writes `signal_type='accel_300_long'` (underscore) and `source='accel-300+'` (hyphen) as SEPARATE fields
- Confluence gate checks `source` field → gets hyphen form
- hotset.json stores `accel_300_long` (underscore in source_parts)
- These are different strings but count as 2 unique types if both appear in same source field

## prev_hotset merge bypass (patched 07:46)

signal_compactor.py:933 merge step was adding prev_hotset entries directly as APPROVED without confluence re-check. Patched to add source_parts >= 2 check before merge.