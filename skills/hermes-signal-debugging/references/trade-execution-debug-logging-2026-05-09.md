# Trade Execution Pipeline Debug Logging Pattern
**Session:** 2026-05-09 | **Scripts:** brain.py, decider_run.py, hl-sync-guardian.py

## The Three-Step Pipeline and Where It Breaks

```
decider_run.py: execute_trade()
  1. mark_signal_executed()      ← atomic claim (can silently fail if executed=1)
  2. subprocess.run(brain.py)   ← brain.py is a SUBPROCESS, RC controls flow
  3. rollback on failure         ← only fires if brain.py returns non-zero
```

brain.py is a CLI subprocess. Its `sys.exit(1)` on rejection is how decider_run knows it failed.
If brain.py's `print()` statements aren't captured and logged, the failure reason is invisible.

## brain.py — Every Gate Must Log Explicitly

brain.py returns `None` silently from many rejection paths. When `None` reaches
decider_run, decider_run only sees RC=0 (brain.py didn't `sys.exit(1)`) but no trade_id
in stdout. Pattern: decider_run treats RC=0 + no "trade #" in stdout as partial failure.

**Logging standard applied (2026-05-09):**
```python
# Rejection gates — use ❌ prefix, include reason
print(f"[brain.py] ❌ REJECTED: {token} {direction} — live_trading DISABLED")
print(f"[brain.py] ❌ REJECTED: {token} {direction} — delisted on Hyperliquid")
print(f"[brain.py] ❌ REJECTED: {token} {direction} — blocked by {bl}")
print(f"[brain.py] ❌ REJECTED: {token} {direction} — DUPLICATE: open trade exists (id={id})")
print(f"[brain.py] 🏚️ STALE ORPHAN: {token} id={id} hl_ep={hl_ep} age={age_hrs}h")

# Success/failure entry/exit — use → ← arrows
print(f"[brain.py] → mirror_open({hype_token}, {direction}, entry_price={entry_price}, leverage={leverage})")
result = mirror_open(...)
print(f"[brain.py] ← mirror_open returned: {result}")
if not result.get("success"):
    print(f"[brain.py] ❌ mirror_open FAILED: {result.get('message')}")
    return None

# PostgreSQL INSERT
print(f"[brain.py] → PostgreSQL INSERT for {token} {direction} trade (hl_entry={hl_entry}, sz={sz})")
try:
    cur.execute(INSERT ...)
    trade_id = cur.fetchone()[0]
    conn.commit()
    print(f"[brain.py] ✅ {hype_token} {direction} trade #{trade_id} confirmed on HL @ ${hl_entry:.6f}")
except Exception as e:
    print(f"[brain.py] ❌ DB INSERT FAILED: {e}")
    print(f"[brain.py]    INSERT params: token={token}, direction={direction}, entry={hl_entry}, exchange={exchange}")
    # ... mirror_close rollback
```

## decider_run.py — Log the Subprocess Call and Return Codes

```python
# Atomic claim — log entry AND return value
log(f'  → mark_signal_executed(token={token}, direction={direction}, signal_id={sig_id}) — atomic claim', 'INFO')
claimed = mark_signal_executed(token, direction, signal_id=sig_id)
log(f'  ← mark_signal_executed returned: {claimed} (0=failed/already-claimed, 1=success)', 'INFO')
if sig_id is not None and claimed == 0:
    log(f'SKIP: {token} {direction} — signal {sig_id} already claimed [executed=1 in DB]')

# brain.py subprocess — log command, RC, stdout, stderr
log(f'  [brain.py] EXEC: {" ".join(cmd[:8])}... [{paper_flag}]')
result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
log(f'  [brain.py] RC={result.returncode} stdout={result.stdout[:200] if result.stdout else "(empty)"}')
if result.returncode == 0:
    # parse trade# from stdout
else:
    log(f'  [brain.py] ❌ FAILED: stderr={result.stderr.strip()[:200] if result.stderr else "(empty)"}')
    return False, result.stderr.strip()[:80]

# PostgreSQL duplicate check — log pass/fail
_dup_row = _dup_cur.fetchone()
_dup_cur.close(); _dup_conn.close()
if _dup_row:
    log(f'  ⛔ DUPLICATE ENTRY BLOCKED in PostgreSQL: {token} {direction} existing_id={dup_row[0]}')
    return False, f'duplicate_entry_blocked ...'
else:
    log(f'  ✔ PostgreSQL duplicate check passed: no open trade for {token} {direction}')
```

## hl-sync-guardian.py — Log Every Orphan Close Step

```python
def close_position_hl(coin: str, reason: str) -> bool:
    log(f'  → close_position_hl({coin}, reason={reason}) — initiating HL market close', 'INFO')
    exchange = get_exchange()
    log(f'  → exchange.market_close(coin={coin}, slippage={CLOSE_SLIPPAGE})', 'INFO')
    result = exchange.market_close(coin=coin, slippage=CLOSE_SLIPPAGE)
    log(f'  ← market_close returned: {type(result).__name__} = {str(result)[:300]}', 'INFO')

# ORPHAN DETECTED — two-line log, FAIL level, explicit about cause
log(f'  ⛔ ORPHAN DETECTED: {coin} HL position has no DB record — guardian CANNOT create trades (skipping). Position LEFT OPEN on HL!', 'FAIL')
log(f'  ⛔ ORPHAN DETECTED: {coin} — this means brain.py INSERT failed and HL position was left dangling!', 'FAIL')
```

## Key Failure Modes and Log Signatures

| Failure Mode | brain.py Log | decider_run Log |
|---|---|---|
| live_trading disabled | `❌ REJECTED: ... live_trading DISABLED` | `[brain.py] RC=0 stdout=(empty)` |
| delisted | `❌ REJECTED: ... delisted` | `[brain.py] RC=0 stdout=(empty)` |
| blacklist | `❌ REJECTED: ... blocked by SHORT/LONG_BLACKLIST` | `[brain.py] RC=0 stdout=(empty)` |
| duplicate | `❌ REJECTED: ... DUPLICATE: open trade exists (id=N)` | `[brain.py] RC=0 stdout=(empty)` |
| stale orphan | `🏚️ STALE ORPHAN: ... age=Xh` | `[brain.py] RC=0 stdout=(empty)` |
| mirror_open failed | `❌ mirror_open FAILED: ...` | `[brain.py] RC=0 stdout=(empty)` |
| PostgreSQL INSERT failed | `❌ DB INSERT FAILED: ...` | `[brain.py] RC=0 stdout=(empty)` |
| atomic claim already-claimed | N/A (decider_run only) | `→ mark_signal_executed ... returned: 0` then `SKIP: ... already claimed` |
| brain.py RC != 0 | sys.exit(1) | `[brain.py] ❌ FAILED: stderr=...` |

## Why stderr Matters

brain.py uses `print()` for all logging (not sys.stderr). When decider_run does
`subprocess.run(..., capture_output=True, text=True)`, stdout captures the prints.
If brain.py hits a rejection gate, it returns `None` and falls through to the end of
`add_trade()` without `sys.exit(1)`. RC=0 but no "trade #" in stdout.

**Fix applied (2026-05-09):** brain.py calls `sys.exit(1)` when `trade_id is None`
(after all rejection gates). This propagates RC=1 to decider_run so the failure is
correctly identified as a rejection, not a silent partial success.

## The Orphan Path — Brain INSERT Failed, Guardian Closes

```
brain.py: mirror_open() succeeds → PostgreSQL INSERT fails → mirror_close() attempted
→ if mirror_close fails or not called → HL position orphaned
→ guardian detects orphan → closes HL position
→ ORPHAN DETECTED log fires (twice, FAIL level)
→ No PostgreSQL record exists for this trade
```

The guardian's `ORPHAN DETECTED` log is the canary. If it fires, brain.py's INSERT failed.
The two-line log explicitly calls this out so it's unambiguous in the pipeline log.