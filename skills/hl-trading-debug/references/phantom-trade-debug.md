# Phantom Trade Debug

HL shows a position, but PostgreSQL has no matching open trade record.

## Quick Diagnostic

```bash
# Guardian missing tracking — first_seen tells you when the system first noticed
cat /root/.hermes/data/guardian-missing-tracking.json | python3 -m json.tool

# Guardian closing markers (active orphan closes)
cat /root/.hermes/data/guardian-closing-markers.json

# Check loss_cooldowns for a token
cat /root/.hermes/data/loss_cooldowns.json | python3 -m json.tool | grep -A5 -B1 ATOM

# Find trades with hidden loss (hype_realized < 0 but pnl_usdt >= 0)
psql -h /var/run/postgresql -p 5432 -U postgres -d brain -c \
  "SELECT id, token, pnl_usdt, hype_realized_pnl_usdt, close_reason FROM trades \
   WHERE hype_realized_pnl_usdt < 0 AND pnl_usdt >= 0 AND close_time >= NOW() - INTERVAL '7 days';"
```

## Key Insight: HL History is Ground Truth

**When T says a position was open at time T and guardian logs say it wasn't — investigate WHY.** Two distinct scenarios:

### Scenario A: Brief sub-60s position (visible in guardian log)
- Position opens and closes between two guardian sync cycles (~60s window)
- Guardian never knew about it → LIVE-MISS handler fires → spurious re-entry
- `guardian-missing-tracking.json` first_seen is AFTER T
- Fix: `signal_compactor._get_open_tokens()` now cross-checks `guardian-closing-markers.json`

### Scenario B: Position held for hours (HL history shows duration)
- `guardian-missing-tracking.json` first_seen is AFTER T
- But PostgreSQL HAS a record for that token (the real tracked position)
- Separate brief sub-60s position appears/disappears → LIVE-MISS handler → spurious re-entry
- hype_realized_pnl_usdt captures the combined HL loss of real position + brief intrusion

**The ATOM case (2026-05-17) — Scenario B:**
- DB id=10077: open 07:36:07, close 10:07:05, held 2.5h, hype_realized=-0.1725 (real HL loss)
- Guardian at 10:05:24 detected SEPARATE brief sub-60s position (not in any sync log)
- LIVE-MISS created spurious re-entry at 10:05:26
- **Key lesson:** When T corrects analysis, his HL history is ground truth. Exhaust every system explanation before disagreeing.

## Common Patterns

### Pattern 1: Signal consumed, never executed on HL
- signal_compactor marks signal as PENDING
- decider_run/execute_trade fails silently (HL order never fires)
- PostgreSQL has a PENDING signal with no corresponding HL position
- Guardian's LIVE-MISS handler sees "DB says open, HL says closed" and re-opens

### Pattern 2: Brief HL position (sub-60-second window)
- Position opens on HL and closes within one guardian sync cycle
- Guardian never knew about it
- Guardian's "Missing" detection re-enters

### Pattern 3: Orphan guard race
- `add_orphan_trade()` is skipped because guardian orphan guard blocks it (HL position found but no DB record)
- HL position stays open
- Guardian's orphan close fires but position already closed
- Result: phantom DB record remains, no cooldown set

## Diagnostic Queries

```sql
-- Find phantom DB records (open in DB, never appeared on HL)
SELECT token, direction, open_time, entry_price, signal
FROM trades
WHERE status = 'open'
ORDER BY open_time DESC;

-- Compare HL history timestamps vs guardian first_seen
-- If first_seen is AFTER the HL history timestamp,
-- the system never saw the original position
-- But if the position was held for hours, investigate Scenario B above
```