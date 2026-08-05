# Signals EXECUTED=1 But No Trades — 2026-06-18

**CRITICAL CORRECTION (2026-06-19):**
- Working wallet: `0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC` — this is in `.secrets.local` and working TODAY (PEOPLES opened June 19)
- Old/revoked wallet: `0x5AB4AC1b62A255284b54230b980AbA66D80A` — caused June 18 failures
- **Do NOT update `.secrets.local` from `~/.secrets/hyperliquid-main.json`** — that file has the OLD revoked wallet
- `hyperliquid_exchange.py` was the culprit: filter excluded `SIGNING_WALLET_ADDRESS` from loading + hardcoded fallback to old wallet

## Symptom
Pipeline journal shows ONDO SHORT reached hot-set, `brain.py` called `mirror_open()`, but no trade appeared on Hyperliquid and no PostgreSQL record was created. Guardian log shows no execution activity.

## Root Cause Cascade

### Layer 1 — The Immediate Failure
```
brain.py → mirror_open(ONDO, SHORT) → RC=1 FAILED: stderr=(empty)
```
`brain.py` prints the error to stdout (not stderr), so decider_run's `stderr` capture sees nothing. The failure dict `{'success': False, 'message': '...'}` is returned but `brain.py` doesn't surface it to the exit code.

### Layer 2 — Why HL Rejected the Wallet
```
mirror_open result: {
  'success': False,
  'message': 'User or API Wallet 0x5ab4ac1b62a255284b54230b980aba66d882d80a does not exist.'
}
```
The wallet `0x5AB4...` had been revoked/replaced on Hyperliquid. The working wallet is `0x8507...` which IS registered with HL.

### Layer 3 — Why the Old Address Was Being Used
`hyperliquid_exchange.py` line 24 had a guard that **explicitly skipped loading `SIGNING_WALLET_ADDRESS` from `.secrets.local`**:
```python
# WRONG — line 24
if k and v and k not in ("SIGNING_WALLET_ADDRESS", "MAIN_ACCOUNT_ADDRESS"):
    globals()[k] = v.strip('"')
# SIGNING_WALLET_ADDRESS was excluded, then hardcoded at line 28:
SIGNING_WALLET_ADDRESS = "0x5AB4AC1b62A255284b54230b980AbA66d882D80A"  # old revoked wallet
```
The `.secrets.local` file had the correct wallet `0x8507...` but the code ignored it.

### Layer 4 — Guardian Blindness
The guardian had been returning `HL returned empty` since June 13 — it couldn't read HL positions at all (same wallet issue). This masked the problem further since guardian couldn't see that no trades were actually being placed.

## Fix Applied (2026-06-18)

**1. `.secrets.local`** — Already had correct values (correct wallet was there, just being ignored by hyperliquid_exchange.py):
```
SIGNING_KEY="0xa3efd0f6339a7dd8130b2b9ccee331d62585d5de685ddc56eb04d03d55b47140"
SIGNING_WALLET_ADDRESS="0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC"
MAIN_ACCOUNT_ADDRESS="0x324a9713603863FE3A678E83d7a81E20186126E7"
```

**2. `hyperliquid_exchange.py` line 24** — Removed `SIGNING_WALLET_ADDRESS` from filter blocklist:
```python
# BEFORE
if k and v and k not in ("SIGNING_WALLET_ADDRESS", "MAIN_ACCOUNT_ADDRESS"):
# AFTER
if k and v and k not in ("MAIN_ACCOUNT_ADDRESS",):
```

**3. `hyperliquid_exchange.py` line 28** — Changed from hardcoded to loaded-from-secrets:
```python
# BEFORE
SIGNING_WALLET_ADDRESS = "0x5AB4AC1b62A255284b54230b980AbA66d882D80A"
# AFTER
SIGNING_WALLET_ADDRESS = globals().get("SIGNING_WALLET_ADDRESS", "")
```

**Result after fix:**
```
[HYPE Mirror] OPEN SHORT 29 ONDO @ signal=$0.359480 → HL_fill=$0.359430 (1 fills)
mirror_open result: {'success': True, ...}
```
Trade confirmed in PostgreSQL: `('ONDO', 'SHORT', Decimal('0.35943000'), 'open', ...)`

## Diagnostic Pattern

When you see `brain.py RC=1 FAILED: stderr=(empty)` in the pipeline journal:

1. **Check journal for brain.py stdout** — the actual error is in stdout, not stderr:
   ```
   grep "brain.py" /var/log/syslog | tail
   journalctl -u hermes-pipeline | grep "brain.py"
   ```

2. **Test mirror_open directly** (most important diagnostic):
   ```python
   import sys; sys.path.insert(0,'/root/.hermes/scripts')
   from hyperliquid_exchange import mirror_open
   result = mirror_open('ONDO', 'SHORT', 0.359, leverage=5)
   print(result)
   ```

3. **Verify wallet address is loaded correctly**:
   ```python
   from hyperliquid_exchange import get_wallet
   print(f"Wallet: {get_wallet().address}")
   # Should be 0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC (working) NOT 0x5AB4AC... (revoked)
   ```

4. **Check HL API directly**:
   ```bash
   curl -s -X POST http://127.0.0.1:8080/info \
     -H "Content-Type: application/json" \
     -d '{"type":"clearinghouseState","user":"0x324a9713603863FE3A678E83d7a81E20186126E7"}'
   ```

## Key Files
- `/root/.hermes/.secrets.local` — source of truth for all credentials (working wallet: `0x8507...`)
- `/root/.hermes/scripts/hyperliquid_exchange.py` — loads from `.secrets.local` at import time
- `/root/.hermes/scripts/brain.py` — calls `mirror_open`, prints result to stdout
- `~/.secrets/hyperliquid-main.json` — DO NOT USE — has OLD revoked wallet (`0x5AB4...`)

## Prevention
When updating HL credentials: update `.secrets.local` AND verify `SIGNING_WALLET_ADDRESS` in `hyperliquid_exchange.py` is loaded from globals (not hardcoded). Test with `mirror_open` dry-run before leaving the session.
