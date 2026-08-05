# Constants Usage Audit — 2026-05-20

## Scope

Constants defined in `hermes_constants.py` that were NOT imported anywhere in the codebase. Also tracking how `DEFAULT_TRADE_SIZE_USDT` and `HL_MIN_NOTIONAL_USDT` were deployed across files.

## Unused Constants (not imported anywhere)

| Constant | Value | Likely Reason |
|----------|-------|---------------|
| `MAX_POSITIONS` | 5 | Replaced by `MAX_CONCURRENT_POSITIONS` |
| `RSI_PERIOD` | 14 | Signals use inline RSI, not a shared constant |
| `RSI_OVERSOLD` | 30 | Inline threshold, not centralized |
| `RSI_OVERBOUGHT` | 70 | Inline threshold, not centralized |
| `ATR_PERIOD` | 14 | Signals use inline ATR, not shared |
| `BB_PERIOD` | 20 | Not used anywhere |
| `BB_STD_DEV` | 2 | Not used anywhere |
| `MAX_LEVERAGE` | 20 | No centralized leverage enforcement |
| `MIN_LEVERAGE` | 1 | Not used |
| `MomentumThreshold` | 0.5 | Not used |
| `VOLATILITY_ADJUST` | False | Not used |
| `TREND_LOOKBACK` | 100 | Not used |
| `VOLUME_CONFIRM_THRESHOLD` | 1.2 | Not used |
| `MFE_MULTIPLIER` | 2.0 | Not used |
| `MAX_DAILY_LOSS` | -50 | Not enforced via constant |

## Live Constants (actually used)

| Constant | Deployed In | Usage |
|----------|-------------|-------|
| `DEFAULT_TRADE_SIZE_USDT` | `hermes_constants.py` used in `brain.py`, `signal_compactor.py`, `archive-trades.py` | Default position size |
| `HL_MIN_NOTIONAL_USDT` | `signal_compactor.py`, `archive-trades.py` | HL notional filtering |
| `HH_HL_BREAKOUT_THRESHOLD` | `hh_hl.py` (imported at lines 24-32) | HH/HL breakout detection |
| `CASCADE_FLIP_ENABLED` | `position_manager.py`, `cascade_flip.py` | Flip trade enable/disable |
| `DAILY_LOSS_LIMIT_USDT` | `position_manager.py` | Daily loss tracking |

## Key Observation

Constants defined in `hermes_constants.py` but used in scripts need a specific import path. When moving constants between modules (e.g., from `paths.py` to `hermes_constants.py`), verify the import exists BEFORE patching the import statement. A broken import cascades: `cascade_flip.py` imports from `paths` → `paths` constants missing from `hermes_constants` → ImportError at module load → `cascade_flip` import fails → `position_manager` fails → pipeline crashes.

## `DEFAULT_TRADE_SIZE_USDT` — Deployment Audit

Found in 5 locations as a hardcoded value, but should use the constant:

1. `signal_compactor.py` ~line 1475: `AMOUNT_USDT = 50` (hardcoded, should be `DEFAULT_TRADE_SIZE_USDT`)
2. `brain.py` trade_add parser: default `50`
3. `decider_run.py` ~line 1815: `AMOUNT_USDT=50` (inline)
4. `archive-trades.py` column mapping: hardcoded `50`
5. `hermes_constants.py`: `DEFAULT_TRADE_SIZE_USDT = 50`

**Action:** Centralize — import from `hermes_constants` in all 4 script locations.

## `HL_MIN_NOTIONAL_USDT` — Deployment Audit

Used in `signal_compactor.py` and `archive-trades.py` as `50.0`. Centralized in `hermes_constants.py`. No immediate action needed — both files already import it.