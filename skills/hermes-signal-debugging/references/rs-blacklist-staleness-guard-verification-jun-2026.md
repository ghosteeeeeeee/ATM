# RS Blacklist + Staleness Guard Verification — 2026-06-08

## Question Asked
Are RS signals using the blacklists to filter out blacklisted coins before signal generation, especially for stale prices?

## Answer: Guards Are Correct

RS signal generation (`signals/rs.py` → `scan_rs_signals()`) has a3-layer guard chain:

### Layer 1 — Stale Price Guard (`_get_candles_1m`, line699)
```python
if (time.time() - most_recent_ts) > 120:
    print(f"[rs] {token}: stale price_history (last ts {most_recent_ts}, skipping)")
    return []
```
Returns `[]` if most recent 1m candle is >120 seconds old. **Currently firing for ALL 230 tokens** — their last price_history update is timestamp1779941848 (weeks old).

### Layer 2 — Directional Kill-Switch (lines 752-756)
```python
from hermes_constants import RS_PLUS_ENABLED, RS_MINUS_ENABLED
if sig['direction'] == 'LONG' and not RS_PLUS_ENABLED:
    continue
if sig['direction'] == 'SHORT' and not RS_MINUS_ENABLED:
    continue
```

### Layer 3 — Blacklist Guard (lines 760-763)
```python
token_upper = token.upper()
if sig['direction'] == 'LONG' and token_upper in LONG_BLACKLIST:
    continue
if sig['direction'] == 'SHORT' and token_upper in SHORT_BLACKLIST:
    continue
```
Correctly checks `LONG_BLACKLIST` for LONG signals and `SHORT_BLACKLIST` for SHORT signals.

## Guard Order Is Correct
Stale tokens are caught at Layer 1 before they reach Layer 3. Blacklisted tokens with fresh prices would be blocked at Layer 3 before `add_signal()` is called.

## Critical Finding: ALL230 Tokens Are Stale

```
[rs] ACE: stale price_history (last ts 1779941848, skipping)
[rs] AI16Z: stale price_history (last ts 1779941848, skipping)
[rs] APE: stale price_history (last ts 1779941848, skipping)
... (all 230 tokens same ts)
```

Timestamp1779941848 ≈ early May 2026. Every token's `price_history` table in `signals_hermes.db` stopped updating weeks ago. This means **zero RS signals are firing** — not due to blacklists, but because the staleness guard catches everything.

## Blacklist Scope
- `SHORT_BLACKLIST`: 129 tokens (BTC, SOL, DOGE, ARB, APT, OP, ATOM, NEAR, etc.)
- `LONG_BLACKLIST`: 71 tokens (ETHFI, COMP, DYDX, INJ, FIL, SUI, etc.)
- 60 tokens in BOTH (Solana chain tokens, phantom order tokens)

## Diagnostic Commands

```bash
# Check staleness of all tokens' price_history
python3 -c "
import sys, time
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import get_all_latest_prices
from signals.rs import _get_candles_1m, RS_LEVEL_LOOKBACK
import hermes_constants as hc

prices = get_all_latest_prices()
print(f'Total tokens: {len(prices)}')

stale = []
for token in prices:
    candles = _get_candles_1m(token)
    has_data = bool(candles and len(candles) >= RS_LEVEL_LOOKBACK * 2)
    if not has_data:
        stale.append(token)

print(f'Stale (no valid candles): {len(stale)}')
print(f'Fresh: {len(prices) - len(stale)}')
" 2>&1 | grep -E "Total|stale|Fresh"

# Verify blacklist guard logic directly
python3 -c "
import sys
sys.path.insert(0, '/root/.hermes/scripts')
import hermes_constants as hc

test_cases = [('BTC','SHORT'), ('ETH','LONG'), ('SOL','SHORT'), ('OX','LONG'), ('OX','SHORT')]
for token, direction in test_cases:
    t = token.upper()
    if direction == 'LONG' and t in hc.LONG_BLACKLIST:
        print(f'BLOCKED {token} {direction} → LONG_BLACKLIST')
    elif direction == 'SHORT' and t in hc.SHORT_BLACKLIST:
        print(f'BLOCKED {token} {direction} → SHORT_BLACKLIST')
    else:
        print(f'ALLOWED  {token} {direction}')
"
```

## Related References
- `rs-stale-bug-2026-05-12.md` — RS silent failure from missing add_signal args (not staleness)
- `signal-blacklist-debugging.md` — SIGNAL_SOURCE_BLACKLIST (different from LONG/SHORT_BLACKLIST)
- `accel-300-staleness-fix.md` — accel_300 staleness guard pattern
