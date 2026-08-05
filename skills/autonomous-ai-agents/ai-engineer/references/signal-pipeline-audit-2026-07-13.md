# Signal Pipeline Audit Session — 2026-07-13

Cron-driven ai-engineer audit. 12 signal scripts. Zero P0/P1 findings. All recent fixes verified intact.

## What was checked

Files audited (all in `/root/.hermes/scripts/`):

| File | py_compile | Path | SQL Pattern | set_cooldown |
|------|------------|------|-------------|--------------|
| gap300_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | via state table |
| ma_cross_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| ma_fast_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| zscore_momentum.py | ✅ | _PRICE_DB | double-subquery ✅ (timestamp included) | direct set_cooldown(0.5h) |
| rs_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| r2_trend_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| macd_1m_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | direct set_cooldown(1h) |
| volume_1m_signals.py | ✅ | _PRICE_DB (price) + _CANDLES_DB (volume) | double-subquery ✅ | caller-dedupe |
| ma300_candle_confirm_signals.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| macd_rules.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |
| ma_cross_5m.py | ✅ | CANDLES_DB (intentional, 5m aggregates) | reads candles_5m | direct set_cooldown(1h) |
| pattern_scanner.py | ✅ | _PRICE_DB | double-subquery ✅ | caller-dedupe |

## Recent-fix baseline verified

- `paths.py: COOLDOWN_FILE` defined at line 88 ✓
- `signal_schema.set_cooldown` writes to `LOSS_COOLDOWN_FILE` (line 1759) in dict format with `{'expires', 'hours', 'reason'}` ✓
- `signal_schema.clear_cooldown` uses `LOSS_COOLDOWN_FILE` (line 1787) ✓
- `zscore_momentum.py` subquery includes `'timestamp'` in inner SELECT (line 131) ✓
- `r2_trend_signals.py` has sqlite3 import (line 27) ✓
- `ma_cross_signals.py` debug prints removed from hot loops (only signal-fire + error prints remain) ✓
- `volume_1m_signals.py` debug prints removed (only single `except` print at line 96) ✓

## Constants / Blacklist (P0 check)

```
hermes_constants.py:
  SHORT_BLACKLIST       line 26  ✓ populated
  LONG_BLACKLIST        line 86  ✓ populated
  SIGNAL_SOURCE_BLACKLIST line 104 ✓ populated
  CONFLUENCE_REQUIRED    line 727 ✓ True
```

Blacklist intact. No regression vs. 2026-05-13 RESOLVED state.

## Patterns captured (now in SKILL.md)

- **Pattern 68** — Signal scripts live in TWO places (legacy top-level + `signals/` package); audit the LIVE one wired into `signal_gen.py`.
- **Pattern 69** — Canonical price_history read pattern (double-subquery with timestamp in inner SELECT).
- **Pattern 70** — Synthesize-ohlcv pattern for close-only price_history is intentional; downstream code that depends on `c['close'] != c['open']` is dead.
- **Pattern 71** — "Missing set_cooldown" is usually a false positive; caller-level `recent_trade_exists` in `signal_gen.py` is the established dedup pattern.
- **Pattern 72** — 9-step cron-driven signal audit checklist (parallelizable, ~10 min total).
- **Pattern 73** — "No bugs found" is a valid audit outcome; don't manufacture findings.

## Key session takeaways

1. The P0 blacklist check ran FIRST and confirmed the 2026-05-13 fix is intact — 4 months without regression.
2. `signal_gen.py` (NOT `signal_runner.py`) is the canonical import surface — `signal_runner.py` doesn't exist; the brain description for it is misleading.
3. The "missing set_cooldown" pattern is a recurring false positive trap for any auditor not familiar with the caller-level dedup design.
4. The 12-script audit took ~10 minutes using the parallelizable checklist — well within cron budget.
5. The double-subquery pattern is now stable across all 12 files; no need to keep re-verifying.