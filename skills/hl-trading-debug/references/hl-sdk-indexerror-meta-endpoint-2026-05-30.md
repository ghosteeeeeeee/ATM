# HL SDK IndexError — Root Cause & Permanent Fix (2026-05-30)

## What Failed

**Symptom**: `Exchange()` initialization crashes with `IndexError: list index out of range` at `info.py:48`. ALL HL API communication (position reads, trading, price data) breaks.

**Root Cause**: Hyperliquid changed their `/info` `spotMeta` endpoint. The `tokens` array now has 464 entries (indexed 0-463). One universe entry `@367` references token index **479** (higher than tokens array length). When `Info.__init__` does `tokens[base]` it throws `IndexError`.

```python
# info.py:48 crashes when token index exceeds list length
base_info = spot_meta["tokens"][base]   # base=479 >= len(tokens)=464
quote_info = spot_meta["tokens"][quote] # same
```

## Permanent Fix (Source Patch)

File: `/usr/local/lib/python3.12/dist-packages/hyperliquid/info.py`

Lines 47-49 — add bounds check before array access:

```python
# BEFORE (crashes on malformed entry):
base_info = spot_meta["tokens"][base]
quote_info = spot_meta["tokens"][quote]

# AFTER (skip malformed entries — HL API schema change 2026-05):
if base >= len(spot_meta["tokens"]) or quote >= len(spot_meta["tokens"]):
    continue  # skip malformed entry (HL API schema change 2026-05)
base_info = spot_meta["tokens"][base]
quote_info = spot_meta["tokens"][quote]
```

Apply via:
```bash
python3 -c "
info_py = '/usr/local/lib/python3.12/dist-packages/hyperliquid/info.py'
with open(info_py, 'r') as f:
    content = f.read()
old = '            base_info = spot_meta[\"tokens\"][base]\n            quote_info = spot_meta[\"tokens\"][quote]'
new = '            if base >= len(spot_meta[\"tokens\"]) or quote >= len(spot_meta[\"tokens\"]):\n                continue\n            base_info = spot_meta[\"tokens\"][base]\n            quote_info = spot_meta[\"tokens\"][quote]'
if old in content:
    content = content.replace(old, new, 1)
    with open(info_py, 'w') as f:
        f.write(content)
    print('Patched successfully')
"
```

**Verification**: `python3 -c "from hyperliquid.exchange import Exchange; from hyperliquid_exchange import get_wallet, MAIN_ACCOUNT_ADDRESS; ex = Exchange(get_wallet(), base_url='https://api.hyperliquid.xyz', account_address=MAIN_ACCOUNT_ADDRESS); print('OK')"`

## Consequence Chain

| Component | Status | Workaround |
|-----------|--------|------------|
| `Exchange()` init | FIXED — SDK patch | SDK patch at info.py |
| `get_open_hype_positions_curl()` | FIXED — uses `user_state()` now | `clearinghouse_state` method doesn't exist on patched Info, use `user_state` |
| `place_order()` REST fallback | BROKEN — nonce 422 | SDK path works (Exchange init fixed); REST nonce path broken but unnecessary now |
| `sync_pnl_from_hype` float-str | FIXED — explicit float() coercion | Line 1485 in hl-sync-guardian.py |
| prices.json | OK — floats, not strings | No fix needed there |

## Post-Fix Verification

After applying the patch and restarting services:
- `get_open_hype_positions_curl()` returns positions correctly
- `user_state()` works (clearinghouseState doesn't exist on patched Info)
- Positions sync with DB (HL: N positions | DB: N open trades)
- `sync_pnl_from_hype` succeeds (no more float-str error)

## Key Finding

The SDK patch persists across restarts (edits the installed package file directly). Nonce endpoint still returns 422 to plain `requests.post()` — but since `Exchange()` now works, trading via SDK path works and the nonce issue is moot.

**`clearinghouse_state` vs `user_state`**: Patched `Info` class has `user_state()` but NOT `clearinghouse_state()`. All code calling `clearinghouse_state` must be updated to call `user_state` instead. This affects `get_open_hype_positions_curl()` in hyperliquid_exchange.py.