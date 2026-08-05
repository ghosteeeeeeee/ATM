# ATOM Phantom Re-Entry — Corrected Root Cause (2026-05-17)

## What Happened — HL History vs System View

User's HL history showed:
```
09:36:07  ATOM Open Short  2.0716
10:04:58  ATOM Close Short 2.1042  loss=-0.16
10:05:26  ATOM Open Short  2.1051
10:07:05  ATOM Close Short 2.1079  loss=-0.02
```

System (PostgreSQL) only had:
```
id=10077: open 07:36:07, close 10:07:05, entry=2.1051, pnl_usdt=-0.03, hype_realized=-0.1725
```

Guardian log showed ATOM never on HL from 09:30-10:04 (HL:5, DB:5 every sync).

## Corrected Timeline

1. **07:36:07** — Pipeline opens ATOM SHORT id=10077 @ 2.1051 (DB record exists)
2. **07:36-10:04** — Position held open for 2.5 hours. Guardian checked HL every 60s, HL:5 DB:5, ATOM never appeared (brief sub-60s position from an earlier signal consumed but never executed)
3. **10:04:23** — Guardian sync: HL:5 DB:5
4. **10:04-10:05** (~60s window) — A separate brief HL position appears and closes. Guardian never saw it.
5. **10:05:24** — Guardian sync: HL:4 DB:5 — ATOM gone from HL, still in DB as "Missing (DB only)"
6. **10:05:26** — LIVE-MISS handler opens new SHORT @ 2.1051 (id=10077, marking phantom record as "executed")
7. **10:07:05** — id=10077 closes via ATR SL, exit=2.1063, pnl_usdt=-0.03, hype_realized=-0.1725

## Root Cause

**Two separate issues combined:**

### Issue 1: Loss cooldown missed (reason='atr_sl_hit', pnl_usdt_val=0, is_loss=False)
`close_paper_position()` — reason string has no PnL% pattern → `pnl_usdt_val=0` → `is_loss=False` → cooldown skipped. hype_realized=-0.1725 proves real loss existed.

**Fixes applied:**
- `close_paper_position()`: DB fallback to `hype_realized_pnl_usdt` when reason has no %
- Sentinel: if `is_loss=False` but `hype_realized_pnl_usdt < 0`, ALERT + call `set_loss_cooldown()`
- STALE_ROTATION path: added `_record_loss_cooldown()` call

### Issue 2: Brief sub-60s position triggered LIVE-MISS spurious re-entry
The original position the user saw at 09:36 (entry=2.0716) was a brief sub-60s position — appeared/disappeared between two guardian sync cycles. Guardian only knew about it from the LIVE-MISS handler at 10:05:24.

**Fix applied:**
- `signal_compactor._get_open_tokens()` now cross-checks `guardian-closing-markers.json` — tokens in closing markers are treated as "open" even if PostgreSQL has a phantom record

## Key Lesson

**HL history is ground truth.** When T says a position was open at time T and the system shows it wasn't, investigate WHY:
1. Could be a brief sub-60s position (system gap, architectural limitation)
2. Could be a DB INSERT failure (system bug)
3. Could be a combination (real position held for hours + separate brief intrusion)

Never tell T his data is wrong without exhausting every system explanation first. When T pushes back on analysis, update the explanation — don't defend the wrong answer.

## Diagnostic Commands

```bash
# Check what guardian saw vs what HL history shows
cat /root/.hermes/data/guardian-missing-tracking.json | python3 -m json.tool | grep ATOM

# Check for hidden losses (pnl_usdt >= 0 but hype_realized < 0)
psql -h /var/run/postgresql -p 5432 -U postgres -d brain -c \
  "SELECT id, token, pnl_usdt, hype_realized_pnl_usdt, close_reason FROM trades \
   WHERE hype_realized_pnl_usdt < 0 AND pnl_usdt >= 0;"

# Check closing markers
cat /root/.hermes/data/guardian-closing-markers.json | python3 -m json.tool
```

## Files Modified (2026-05-17)

| File | Change |
|------|--------|
| `position_manager.py` | hype_realized fallback + sentinel ALERT+ACT + debug traces + verify write |
| `hl-sync-guardian.py` | _record_loss_cooldown debug/verify, _close_paper_trade_db sentinel, _check_stale_rotation cooldown, _load_closing_markers type validation |
| `signal_compactor.py` | `_get_open_tokens()` checks `guardian-closing-markers.json` |