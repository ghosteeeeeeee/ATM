# HL Wallet Mismatch — 2026-06-18

## Symptom

Guardian `close_position_hl` fails with:
```
'User or API Wallet 0x5ab4ac1b62a255284b54230b980aba66d882d80a does not exist.'
```

Guardian logs `[PASS] [SELF-CLOSE] MORPHO market close OK` — **error dict treated as success** — position left open on HL, bleeding at 5x leverage.

## Actual Root Cause

`/root/.hermes/.secrets.local` has **wrong wallet address** AND **missing signing key**:

```
# Current .secrets.local (WRONG)
SIGNING_WALLET_ADDRESS="0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC"
MAIN_ACCOUNT_ADDRESS="0x324a9713603863FE3A678E83d7a81E20186126E7"
GITHUB_TOKEN=*** HL_SIGNING_KEY is MISSING
```

`~/.secrets/hyperliquid-main.json` (the actual funded wallet on HL):
```json
{
  "hyperliquid_private_key": "0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6",
  "hyperliquid_address": "0x5AB4AC1b62A255284b54230b980AbA66D80A",
  "hyperliquid_api_key": "0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6",
  "main_account_address": "0x324a9713603863FE3A678E83d7a81E20186126E7"
}
```

The correct wallet for HL is `0x5AB4AC1b62A255284b54230b980AbA66D80A` (from `hyperliquid-main.json`), but `.secrets.local` has `0x8507BEE48e89BB6C53096AF9461Be3FE2B78D3AC` — a completely different wallet that doesn't exist on HL.

Additionally, `.secrets.local` is **missing `HL_SIGNING_KEY`** entirely. `hyperliquid_exchange.py` line 24 filters it out (`k not in ("MAIN_ACCOUNT_ADDRESS",)` was the correct form, but if HL_SIGNING_KEY isn't in the file at all, `globals().get("HL_SIGNING_KEY", "")` returns empty string).

## Why Guardian Treated Error as Success

`close_position_hl` returns `{'status': 'err', 'response': 'User or API Wallet ... does not exist'}`.

The guardian then logs `[PASS]` — it checks if the dict has certain keys rather than checking `data.get('ok') == True`. Bug in result handling, not in the secrets.

## Fix Required

Update `/root/.hermes/.secrets.local` with correct values from `~/.secrets/hyperliquid-main.json`:

```
HL_SIGNING_KEY="0x588d57f88d8dd7e0561d2c838a1bb02fdcab56f85ea69c3fc3420879d42c40e6"
SIGNING_WALLET_ADDRESS="0x5AB4AC1b62A255284b54230b980AbA66D80A"
MAIN_ACCOUNT_ADDRESS="0x324a9713603863FE3A678E83d7a81E20186126E7"
```

Then restart the guardian:
```bash
pkill -9 -f hl-sync-guardian && python3 /root/.hermes/scripts/hl-sync-guardian.py &
```

## Verification

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_wallet, get_exchange
w = get_wallet()
print(f"Wallet address: {w.address}")  # Should match 0x5AB4...
# Test close
exchange = get_exchange()
result = exchange.market_close(coin='MORPHO', slippage=0.005)
print(f"Result: {result}")  # Should NOT be {'status': 'err', ...}
```
