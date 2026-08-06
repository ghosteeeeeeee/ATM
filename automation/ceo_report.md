# CEO Report — 2026-08-06 06:50 UTC

## System Status: HEALTHY ✅

| Metric | Value |
|--------|-------|
| Pipeline | active ✅ |
| HL-Sync-Guardian | active ✅ |
| Live Trading | enabled ✅ |
| Open positions | 6/6 |
| Closed today | 42 |
| Net PnL | **+4.38%** |

## Current Positions
AVAX, LINK, AAVE, JUP, UMA, MORPHO — all managed by guardian with ATR-based SL/TP.

## Active Signals (8)
zscore_rising, hzscore, rs, tl_break, pattern_scanner, vortex_break, return_exhaustion, ma_100_cross

## Pending Signal
PNUT SHORT (conf=97.1) — blocked by max positions 6/6. Will enter on next close.

## Key Findings

**bb_bounce RESOLVED** — No longer in active signal list. Previous reports of 18 trades/24h appear fixed. Directional flags (PLUS/MINUS_ENABLED) were the root cause, now set False.

**vel-hermes- STILL FIRING** — In NEVER_REENABLE_FLAGS but still generating 46 trades. Signal registration leak in `signals/__init__.py`. Needs code-level fix.

**Performance Leaders:**
- `tl_break_long`: 82.4% WR, 17 trades, +$1.63/24h (protected, sustained)
- `hzscore+` confluence: 100% WR, 5 trades today
- `ma_100_cross`: First live trade (W LONG), 48h monitoring window

## Decisions

1. **DELEGATE to bug_hunter**: vel-hermes- signal leak — NEVER_REENABLE_FLAGS not blocking registration in `signals/__init__.py:351`. Find bypass.
2. **CONTINUE monitoring** ma_100_cross (48h trial), vortex_break + return_exhaustion (48h trial).
3. **System profitable** — no parameter changes needed. Let signals run.
