# Hyperliquid Wallet Configuration

## Accounts
- **SIGNING_WALLET**: 0x5AB4AC1b62A255284b54230b980AbA66d882D80A — signs transactions
- **MAIN_ACCOUNT**: 0x324a9713603863FE3A678E83d7a81E20186126E7 — trades from this sub-account

## Keys
Stored in `/root/.hermes/.secrets.local` (gitignored). Never commit keys.

## Module
`scripts/hyperliquid_exchange.py` — uses `hyperliquid-python-sdk` + `eth-account`.
Signs with funding wallet, trades from main sub-account via `account_address` param.

## Requirements
- hyperliquid-python-sdk (0.22.0)
- eth-account (0.13.7)
- CCXT (4.5.42)

## Account State (as of 2026-03-28)
- ~$33.70 USDT perp value
- 0 open positions
- $36K all-time volume
- Account has been active (freqtrade active historically)
