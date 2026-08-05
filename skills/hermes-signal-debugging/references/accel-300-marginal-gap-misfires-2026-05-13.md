# accel-300 Marginal Gap + Late Bar Misfires — 2026-05-13

## Session Finding

**23/30 losing trades on May 12-13.** T's diagnosis: "signal quality is the root cause, not SL tightness." Increasing stops does NOT fix the problem — signals are mis-firing on bad breakouts.

## The Two Failure Modes

### Failure Mode 1: Marginal Gap (0.20-0.25%)

Tokens firing at the ABSOLUTE FLOOR of MIN_GAP_PCT=0.20%, immediately reversing:

| Token | Gap | Bars | Growth% | Result |
|-------|-----|------|---------|--------|
| NEAR | 0.200% | 1 | 0.331% | LOST — barely above EMA300 |
| FIL | 0.204% | 1-3 | 0.204% | LOST — marginal breakout |
| FET | 0.228% | 1-3 | 0.235% | LOST — marginal |
| SKY | 0.237% | 2 | 0.151% | LOST — marginal, weak growth |
| ZEN | 0.239% | 7 | 0.142% | LOST — bar 7 = catching END of move |
| ZK | 0.207% | 8 | 0.069% | LOST — bar 8 = exhausted move |
| AVAX | 0.217% | 2 | 0.113% | LOST — marginal gap, weak growth |

These are NOT real breakouts. They're micro-rallies that poke 0.20% above EMA300 and immediately fail. The signal fires on the poke, price reverses, SL hits.

### Failure Mode 2: Late Bar Entries (bars 6-10)

When bars_since_cross is 6-10, the move is ALREADY EXHAUSTED. The signal is catching the end of a trend, not the beginning:

- ZK: bars=8 → entered at 13:39, trade lost -0.43%
- ZEN: bars=7 → entered at 13:17, trade lost -0.64%
- LTC: bars=10 → trade lost
- TRB: bars=10 → trade lost
- SUSHI: bars=6-8 → trade lost
- TIA: bars=5-10 → trade lost
- ICP: bars=3-10 → trade lost

### Failure Mode 3: Market-Wide Simultaneous Marginal Firings

On May 12 13:00-16:00, DASH, COMP, VINE, APEX, OP, LTC, ETHFI, MERL ALL fired at exactly 0.200% gap simultaneously. This is the signature of a low-volatility chop market — everything barely pokes above EMA300 at the same time and immediately reverses.

## Full Signal Population Analysis (May 12 13:00-16:00 window)

```
Token      Count  Min Gap  Max Gap  Avg Gap  Low gap entries (<0.25%)
VINE          20    0.200%    0.208%    0.203%  20    ← all fired at floor
APEX          76    0.200%    0.227%    0.218%  76    ← all fired at floor
OP             8    0.200%    0.202%    0.201%   8    ← all fired at floor
LTC           10    0.201%    0.207%    0.204%  10    ← all fired at floor
COMP         122    0.200%    0.283%    0.224% 119    ← 97% at floor
DASH         149    0.200%    0.235%    0.222%  149   ← 100% at floor
```

These are all fired in the SAME 3-hour window. Market was in chop, all these marginal breakouts failed.

## What Good Signals Look Like (winners)

| Token | Gap | Bars | Growth% | Result |
|-------|-----|------|---------|--------|
| BRETT | 1.785% | 1 | 3.327% | +1.11% — real breakout, not marginal |
| VVV | 0.287% | 1 | 0.515% | +2.30% — solid gap, early entry |
| SKR | N/A | N/A | N/A | +1.71% — |

BRETT's gap is 1.785% vs 9x higher than the 0.20% floor tokens. That's the quality difference.

## Required Fixes (in accel_300.py)

### Fix 1: Raise MIN_GAP_PCT

Current: 0.20% (the floor is the problem)
Recommended: 0.30-0.35%

This filters out the choppy micro-rallies that poke just above EMA300 and immediately reverse.

### Fix 2: Add max bars_since_cross

Current: bars 1-10 (fires even at bar 10 when move is exhausted)
Recommended: bars 1-5 maximum, reject after that

Signals at bars 6-10 are catching exhausted moves. Reject or heavily penalize.

### Fix 3: Raise MIN_GAP_GROWTH_PCT

Current: 0.05% (barely requires any acceleration)
Recommended: 0.10-0.15%

Require stronger acceleration, not just barely growing gap.

### Fix 4: Require higher confidence for low-gap signals

If gap < 0.30%: require conf > 85%
If gap 0.30-0.40%: require conf > 75%
If gap > 0.40%: conf > 65% acceptable

### Fix 5: Add market-wide burst detection

If > 20 tokens fire accel-300 within a 15-min window, reduce confidence for all of them by 20%. Market-wide simultaneous firings = chop, not breakout.

## Diagnostic Commands

```bash
# Parse signals.log for gap distribution (May 12 window)
python3 -c "
import re
with open('/var/www/hermes/logs/signals.log', 'rb') as f:
    content = f.read().decode('utf-8', errors='replace')
lines = content.split('\n')
in_window = False
for line in lines:
    if '2026-05-12 13:00' in line: in_window = True
    if '2026-05-12 16:00' in line: in_window = False
    if in_window and 'gap=' in line and 'accel-300' in line:
        m = re.search(r'LONG -accel-300 (\S+).*?conf=(\d+)% gap=([\d.]+)% growth=([\d.]+)% bars_since_cross=(\d+)', line)
        if m: print(f'{m.group(1)}|gap={m.group(3)}%|bars={m.group(5)}|growth={m.group(4)}%')
"

# Find late-bar signals (bars >= 6)
grep -a "bars_since_cross=[6-9]" /var/www/hermes/logs/signals.log | grep "accel-300" | head -20
grep -a "bars_since_cross=10" /var/www/hermes/logs/signals.log | grep "accel-300" | head -20

# Count simultaneous firings in window
grep -a "2026-05-12 14:" /var/www/hermes/logs/signals.log | grep "accel-300" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}' | sort | uniq -c | sort -rn | head -20
```

## Related Files

- `signals/accel_300.py` — MIN_GAP_PCT, bars_since_cross limits
- `signal_compactor.py` — market-wide burst detection logic goes here
- `references/last-30-losers-2026-05-13.md` — full trade table
- `references/accel-300-quality-degradation.md` — prior episode (May 11), same pattern
- `references/counter-trend-entry-bug-2026-05-13.md` — related: entries below EMA300
- `references/accel-300-marginal-acceleration-bug-2026-05-13.md` — inverted conditions bug