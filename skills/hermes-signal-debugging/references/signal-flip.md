---
name: signal-flip
description: Enable or disable the signal direction flip for Hermes trading pipeline. Reverses signal direction before trade execution — used to test if signals are direction-inverted. Also closes open positions to free slots for testing.
category: trading
tags: [hermes, trading, signal, flip, direction, incident]
author: Agent
created: 2026-04-05
updated: 2026-04-05
---

# Signal Flip — Enable/Disable Direction Inversion

Reverses signal direction before every trade is executed in the Hermes pipeline.

**Use case:** WR incident (13.8% WR, 79% of SHORTs wrong direction) — testing whether signals are systematically inverted.

## Quick Commands

### Check current status
```bash
grep "_FLIP_SIGNALS" /root/.hermes/scripts/decider_run.py | head -1
```
Or:
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import decider_run_module  # can't import directly due to side effects
# Instead, just grep the file
```

### Enable flip
```bash
sed -i 's/_FLIP_SIGNALS = False/_FLIP_SIGNALS = True/' /root/.hermes/scripts/decider_run.py
# Verify:
grep "_FLIP_SIGNALS" /root/.hermes/scripts/decider_run.py | head -1
# Should show: _FLIP_SIGNALS = True
```

### Disable flip
```bash
sed -i 's/_FLIP_SIGNALS = True/_FLIP_SIGNALS = False/' /root/.hermes/scripts/decider_run.py
# Verify:
grep "_FLIP_SIGNALS" /FLIP_SIGNALS" /root/.hermes/scripts/decider_run.py | head -1
# Should show: _FLIP_SIGNALS = False
```

### Verify flip is firing (watch logs)
```bash
tail -f /root/.hermes/logs/pipeline.log | grep -i "FLIP\|flip\|enter\|signal"
# Look for: [FLIP] {TOKEN} SHORT → LONG (WR incident fix)
# Or: [FLIP] {TOKEN} LONG → SHORT (WR incident fix)
```

---

## Full Python Script

Save as `/tmp/signal_flip.py` and run with `python3 /tmp/signal_flip.py [on|off|status]`

```python
#!/usr/bin/env python3
"""Signal flip enable/disable script for Hermes trading pipeline."""
import sys, re, argparse

FILE = '/root/.hermes/scripts/decider_run.py'

def get_status():
    with open(FILE) as f:
        content = f.read()
    m = re.search(r'_FLIP_SIGNALS\s*=\s*(True|False)', content)
    if m:
        return m.group(1) == 'True'
    return None

def set_flip(enabled: bool):
    value = 'True' if enabled else 'False'
    with open(FILE) as f:
        content = f.read()
    if f'_FLIP_SIGNALS = {value}' in content:
        print(f'Flip already {\"ENABLED\" if enabled else \"DISABLED\"} (no change needed)')
        return
    # Replace
    new_content = re.sub(r'_FLIP_SIGNALS\s*=\s*(True|False)', f'_FLIP_SIGNALS = {value}', content)
    with open(FILE, 'w') as f:
        f.write(new_content)
    print(f'Flip {\"ENABLED\" if enabled else \"DISABLED\"} — takes effect on next pipeline run (~1 min)')

def main():
    parser = argparse.ArgumentParser(description='Signal flip for Hermes')
    parser.add_argument('action', choices=['on', 'off', 'status'], help='on=enable, off=disable, status=check')
    args = parser.parse_args()

    if args.action == 'status':
        status = get_status()
        if status is None:
            print('ERROR: _FLIP_SIGNALS not found in decider-run.py')
            sys.exit(1)
        print(f'Signal flip is: {\"ENABLED\" if status else \"DISABLED\"}')
    elif args.action == 'on':
        set_flip(True)
    elif args.action == 'off':
        set_flip(False)

if __name__ == '__main__':
    main()
```

---

## Kill Switch

If you need to stop ALL trading instantly (not just the flip):

```bash
echo '{"live_trading": false}' > /var/www/hermes/data/hype_live_trading.json
```

---

## Implementation Details

**File changed:** `/root/.hermes/scripts/decider_run.py`
**Flag location:** Line 28 (`_FLIP_SIGNALS = True`)
**Execution paths affected:**
1. Main approved-signals loop → flips before `execute_trade()` call
2. `process_delayed_entries()` → flips before `brain.py trade add` call

**Pipeline cadence:** hermes-pipeline.timer runs every 1 minute — flip takes effect within ~60 seconds of enabling.

**Guardian:** The `hl-sync-guardian.py` cascade flip logic is NOT affected by this flag. It operates on existing open positions, not on new entries.

## End-to-End Flip Chain (2026-04-05)

When `_FLIP_SIGNALS = True`, the flip propagates through the full pipeline:

```
decider-run.py (line ~1372)
  direction = SHORT if direction == LONG else LONG    # flip
  flipped_direction = 'SHORT' or 'LONG'               # non-None → was flipped

  execute_trade(..., flipped=bool(flipped_direction))
      → decider-run.py line ~553: adds '--flipped' to brain.py cmd

brain.py add_trade(flipped_from_trade=True)
      → INSERT: flipped_from_trade=True, flip_variant='signal-flip'
      → writes to PostgreSQL brain.trades DB

All SL/TP remain correct because they are always computed from entry price
and direction at execution time (LONG → SL below entry, SHORT → SL above entry).
The direction flip does NOT affect SL/TP — only the entry direction changes.
```

---

## Incident Context

- **INCIDENT:** INCIDENT_WR_FAILURE.md (in `/root/.hermes/brain/`)
- **Decision:** DECISIONS.md entry: "OPTION 1 DEPLOYED: Flip signal direction live"
- **Data:** 961 trades, Mar 10-25 2026. WR=13.8%. 79% of SHORTs had price go UP after entry.
- **Revisit condition:** After 20+ trades with flip active — if WR < 30%, flip is wrong direction. If WR > 50%, confirms inverted signal hypothesis.

## When to Disable Flip

- After the test concludes (flip test is diagnostic, not a permanent fix)
- If market regime changes and flip WR drops below 30%
- When Option 3 (fix signal gen at source) is implemented
