# Verified Signal Investigation Pattern

## Core Principle: Check signals_hermes_runtime.db FIRST

When user says "signal X should have fired on move Y but didn't":
1. Query signals_hermes_runtime.db for actual fired signals (not price_history)
2. Compare what WAS fired vs what user EXPECTED
3. Then investigate code logic

**Why:** The user sees a trade opportunity in market prices. The system's ground truth is what signals it actually fired. Starting from fired signals vs starting from price history gives completely different debugging paths.

## Pattern
```python
# Step 1: What did the system actually fire?
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c.execute('''
    SELECT signal_type, source, direction, confidence, value, price, created_at
    FROM signals
    WHERE token = ?
    AND created_at >= datetime("now", "-6 hours")
    ORDER BY created_at ASC
''', ('TOKEN',))

# Step 2: Then investigate price data only if Step 1 shows the system
# was genuinely blind to the move (not that it fired the wrong direction)
```

## Key Cases
- accel-300 called SHORT at bottom correctly; user expected LONG on rally → signal worked, V-shaped not a gap_300 pattern
- Signal fires in DB but not in hot-set → confluence gate or compactor issue (NOT a signal detection issue)
- Signal never fires for token → check price_history freshness, then gate-by-gate analysis
