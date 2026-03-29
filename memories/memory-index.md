# Memory Index (auto-generated from sessions)

## Quick Access
- [trading.md](../trading.md) — Trading system & rules
- [lessons.md](../lessons.md) — Hard lessons learned
- [majorissues.md](../majorissues.md) — Known issues
- [brain.md](../brain.md) — Brain system docs
- [USER.md](../USER.md) — User preferences
- [memory/](../memory/) — Daily logs

## Security
- Never expose ports publicly (localhost only)
- Wallet keys: /root/.hermes/.secrets.local (gitignored)

## Git
- /root/.hermes — Hermes Trading System (git commit 7c5ce14)
- Zip: /var/www/git/hermes_20260329_002047.zip

## DB
- Static: signals_hermes.db
- Runtime: signals_hermes_runtime.db
- Seed: signals_hermes.sql (177K rows)

## Tools
- memory_search — Search daily logs
- brain queries — Query brain database
- lcm_grep — Search conversation history
- lcm_expand_query — Deep recall from compacted context
- youtube-watcher skill — For watching YouTube videos

## Hyperliquid Integration
- scripts/hyperliquid_exchange.py — Main module
- Uses market_open/market_close SDK methods
- Min order: $10
- SZ_DECIMALS enforced per coin (HYPE=2, BTC=6, ETH=4, SOL=4)
- Rate limit: 5s gap + exponential backoff
- Mirror hooks in brain.add_trade (open) + position_manager.close_paper_position (close)
- SIGNING=0x5AB4AC1b62A255284b54230b980AbA66d882D80A
- MAIN=0x324a9713603863FE3A678E83d7a81E20186126E7
