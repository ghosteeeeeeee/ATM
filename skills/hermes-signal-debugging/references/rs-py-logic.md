# rs.py — signal logic reference
# Updated 2026-06-01

## Signal types emitted by rs.py

| Source | Direction | Trigger | Regime penalty |
|--------|-----------|---------|---------------|
| `rs-s{count}` | LONG | Support level + bounce confirmation (price bounced up from level) | SHORT_BIAS: 0.80x |
| `rs-r{count}` | SHORT | Resistance level + rejection confirmation (price bounced down from level) | LONG_BIAS: 0.80x |
| `rs-s-broken` | SHORT | Support level was breached (price crossed below, level now broken) | LONG_BIAS: 0.80x |
| `rs-r-broken` | LONG | Resistance level was breached (price crossed above, level now broken) | SHORT_BIAS: 0.80x |
| `rs-s-broken` | LONG | Resistance broken → acts as support (price above, bouncing from broken res) | SHORT_BIAS: 0.80x |
| `rs-r-broken` | SHORT | Support broken → acts as resistance (price below, bouncing from broken support) | LONG_BIAS: 0.80x |

Wait — the breach signals are:
- support broken → SHORT (not LONG)
- resistance broken → LONG (not SHORT)

This is because a broken support acts as resistance (price fell through, now below it = rejection potential),
and a broken resistance acts as support (price broke through, now above it = bounce potential).

## Key guards in scan_rs_signals()

Applied in this order (each is a continue skip):
1. `RS_ENABLED` global kill-switch
2. `RS_PLUS_ENABLED` (LONG) / `RS_MINUS_ENABLED` (SHORT) direction kill-switch
3. `LONG_BLACKLIST` / `SHORT_BLACKLIST` — tokens in these sets skip that direction entirely
4. signal_schema `add_signal()` — applies its own blacklist + cooldown

## _level_recently_broken() — detection logic

Uses close-only candle data (price_history has open=high=low=close):
- Resistance broken: `prev_close < level < curr_close` (two consecutive closes straddle the level, price crossed above)
- Support broken: `prev_close > level > curr_close` (price crossed below)

lookback = RS_LEVEL_BROKEN_LOOKBACK (hermes_constants, default 200 candles ~8hrs)

## _bounce_confirmation() — bounce detection

Works on close-only synthesized candles. Detects two conditions:
- Touch candle itself was bullish (LONG: close > open) or bearish (SHORT: close < open)
- OR next candle had partial follow-through (>0.025% move in expected direction)

threshold: `_BOUNCE_THRESH_ATR * ATR(14)` — volatility-adaptive, not fixed %

## Blacklists (hermes_constants.py)

`SHORT_BLACKLIST` — ~90 tokens that should never be shorted (meme coins, 0% WR tokens, phantom-order tokens)
`LONG_BLACKLIST` — ~70 tokens that should never be longed (similar criteria, less aggressive)

Both sets include Solana-chain tokens (BONK, WIF, PYTH, etc.) — not tradeable on HL.