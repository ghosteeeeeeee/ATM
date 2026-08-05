# Guardian Silent HL Failure — Market Close Error Treated as Success

**Date:** 2026-06-18
**Status:** MORPHO SHORT open since 17:40 UTC — position left dangling

## Timeline

| Time (UTC) | Event |
|---|---|
| 2026-06-18 17:34 | `accel-300-,rs-s-broken` signal EXECUTED for MORPHO SHORT @ $1.9296 |
| 2026-06-18 17:39:17 | Guardian reconcile: HL has 3 positions (STRK, MORPHO, XMR), DB has 3 |
| 2026-06-18 17:39:18 | Guardian detects breach: `guardian_tp (px=1.92165 <= tp=2.0038638)` |
| 2026-06-18 17:39:18 | `close_position_hl(MORPHO, reason=guardian_tp)` initiated |
| 2026-06-18 17:39:18 | `market_close` returns: `{'status': 'err', 'response': 'User or API Wallet 0x5ab4ac1b62a255284b54230b980aba66d882d80a does not exist.'}` |
| 2026-06-18 17:39:18 | Guardian logs `[PASS] [SELF-CLOSE] MORPHO market close OK` |
| 2026-06-18 17:39:54 | Fill poll: `No HL close fills found for MORPHO after 6 polls (30s)` |
| 2026-06-18 17:41:34 | `guardian-closing-markers.json` written with MORPHO entry |
| 2026-06-18 → | Guardian reconciles MORPHO from HL every 60s; closing marker active but position never closes |

## Root Cause Chain

```
/root/.hermes/.secrets.local has WRONG wallet address (0x8507...)
    ↓
hyperliquid_exchange.py uses 0x8507... for get_wallet()
    ↓
market_close() signs with wrong wallet → HL rejects "Wallet does not exist"
    ↓
Guardian result handler checks dict truthiness not result.get('ok')
    ↓
non-empty dict is truthy → logs [PASS] even though HL rejected
    ↓
No closing marker set (guardian thinks it succeeded)
    ↓
Position left open on HL
    ↓
Guardian reconciles it back into DB every cycle
    ↓
SELF-CLOSE computes wrong TP (1.926 vs correct 1.884)
    ↓
Price hasn't breached wrong TP → no re-attempt
    ↓
Position bleeds at 5x leverage indefinitely
```

## Actual Secrets State

`/root/.hermes/.secrets.local` (WRONG — causes the failure):
```
SIGNING_WALLET_ADDRESS="0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC"  ← does not exist on HL
MAIN_ACCOUNT_ADDRESS="0x324a9713603863FE3A678E83d7a81E20186126E7"
GITHUB_TOKEN=***
HL_SIGNING_KEY is MISSING
```

`~/.secrets/hyperliquid-main.json` (correct wallet on HL):
```json
{
  "hyperliquid_private_key": "0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6",
  "hyperliquid_address": "0x5AB4AC1b62A255284b54230b980AbA66D80A",
  "hyperliquid_api_key": "0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6",
  "main_account_address": "0x324a9713603863FE3A678E83d7a81E20186126E7"
}
```

The HL API error `0x5ab4ac...` is the CORRECT wallet that should be used — but `.secrets.local` has a different address and is missing the signing key entirely.

## Guardian TP/SL Values at Breach

- **Guardian TP:** $1.926118 — stored in `tpsl_self_close`
- **Correct TP:** $1.8841
- **Difference:** ~$0.042 (~4.2%) — catastrophic

At 17:39:18 when breach fired:
- Price was $1.92165 (below guardian TP of $1.926)
- TP trigger for SHORT: `curr < TP` → $1.92165 < $1.926 = TRUE (wrong trigger)
- But correct TP ($1.884) was never breached — $1.92165 > $1.884

## Guardian Log Location

```
/root/.hermes/logs/sync-guardian.log   ← actual guardian output (stdout/stderr redirected)
/var/www/hermes/data/guardian.log      ← WRONG file, empty since May 20
```

## Diagnostic Commands

```bash
# Check what wallet .secrets.local is actually loading
grep -v TOKEN /root/.hermes/.secrets.local

# Check if loaded wallet matches HL
python3 -c "
import sys; sys.path.insert(0,'/root/.hermes/scripts')
from hyperliquid_exchange import get_wallet, SIGNING_WALLET_ADDRESS, _SIGNING_KEY
w = get_wallet()
print(f'Loaded wallet:   {w.address}')
print(f'Expected:       {SIGNING_WALLET_ADDRESS}')
print(f'Key present:    {_SIGNING_KEY[:10]}...')
"

# Check current closing markers
cat /root/.hermes/data/guardian-closing-markers.json

# Check guardian log for MORPHO
strings /root/.hermes/logs/sync-guardian.log | grep -i MORPHO | tail -30
```

## The Fix

1. **Update `/root/.hermes/.secrets.local`** with correct values:
   ```
   HL_SIGNING_KEY="0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6"
   SIGNING_WALLET_ADDRESS="0x5AB4AC1b62A255284b54230b980AbA66D80A"
   MAIN_ACCOUNT_ADDRESS="0x324a9713603863FE3A678E83d7a81E20186126E7"
   ```
2. **Clear the stuck closing marker:**
   ```bash
   rm /root/.hermes/data/guardian-closing-markers.json
   ```
3. **Restart guardian:**
   ```bash
   pkill -9 -f hl-sync-guardian && python3 /root/.hermes/scripts/hl-sync-guardian.py &
   ```
4. **Verify:**
   ```python
   # In python3
   from hyperliquid_exchange import get_wallet
   w = get_wallet()
   print(w.address)  # Should be 0x5AB4AC1b62A255284b54230b980AbA66D80A
   ```

## Reference: Guardian Log at Failure

```
[2026-06-18 17:39:18] [WARN] [SELF-CLOSE] MORPHO BREACH (SHORT): guardian_tp (px=1.92165 <= tp=2.0038638)
[2026-06-18 17:39:18] [INFO]   close_position_hl(MORPHO, reason=guardian_tp...) initiating HL market close
[2026-06-18 17:39:18] [INFO]   get_exchange() for MORPHO
[2026-06-18 17:39:18] [INFO]   exchange.market_close(coin=MORPHO, slippage=0.005)
[2026-06-18 17:39:18] [INFO]   market_close returned: {'status': 'err', 'response': 'User or API Wallet 0x5ab4ac1b62a255284b54230b980aba66d882d80a does not exist.'}
[2026-06-18 17:39:18] [WARN]   MORPHO: unexpected result structure: {'status': 'err', 'response': 'User or API Wallet ... does not exist.'}
[2026-06-18 17:39:18] [PASS]   [SELF-CLOSE] MORPHO market close OK
[2026-06-18 17:39:29-54] [WARN] Fill poll attempts 1-6 — no fills found
[2026-06-18 17:39:54] [FAIL] No HL close fills found for MORPHO after 6 polls (30s)
```
