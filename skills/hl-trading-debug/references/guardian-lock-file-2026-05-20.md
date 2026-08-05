# Guardian Lock File — Operational Notes (2026-05-20)

## Location
`/tmp/hermes-guardian.lock`

## Symptom
Guardian refuses to start with `[FATAL] Guardian already running — exiting` even when no guardian process is running.

## Root Cause
The lock file persists after guardian process dies (kill -9, segfault, OOM kill, etc.). The guardian checks for the lock file before checking if the PID inside is actually alive.

## Fix
```bash
rm -f /tmp/hermes-guardian.lock
```

Then restart guardian normally.

## Prevention
- Always use `pkill -f hl-sync-guardian.py` to stop (lets guardian clean up lock)
- Avoid `kill -9` on guardian — it leaves the lock stranded
- If you must kill -9, follow with `rm -f /tmp/hermes-guardian.lock`

## Guardian Startup Sequence
1. Check for `/tmp/hermes-guardian.lock`
2. If exists, read PID and check if process alive
3. If process alive → exit with FATAL
4. If process dead → remove lock, proceed
5. Write own PID to lock file
6. Begin sync cycle

## Related
- `LIVE_TRADING_ENABLED=False` in hermes_constants.py — separate kill switch from the lock file
- Guardian closing markers: `/var/www/hermes/data/guardian-closing-markers.json` (separate mechanism, different lock)