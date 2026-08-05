# Security Architecture

## Principles

- **Polling over webhooks** — no inbound ports except nginx (443)
- **Secrets in `.secrets.local`** — gitignored, never committed
- **Centralized secret loading** — `_secrets.py` module, all scripts import from it
- **Kill switches** — `LIVE_TRADING_ENABLED` in constants + runtime JSON at `/var/www/hermes/data/hype_live_trading.json` (both must be true for real money)

## Secrets Management

| Item | Detail |
|------|--------|
| Location | `.secrets.local` (project root), `.env` |
| Loading | `_secrets.py` — reads `KEY=VALUE` lines into module globals |
| Gitignore | Both files covered in `.gitignore` |
| Rotation | Exchange API keys: quarterly. GitHub token: as needed. |
| Min permissions | Read-only where possible |

**Never commit secrets.** `bug_hunter.py` scans for hardcoded keys.

## Dependency Security

- **Audit:** weekly via `pip-audit` (planned: `audit_dependencies.py`)
- **Pinning:** `requirements.txt` with pinned versions
- **CVE monitoring:** Check HIGH/CRITICAL weekly

## Network Security

- **Inbound:** nginx only (port 443), rate-limited
- **Outbound:** Hyperliquid API, TradingView, exchange APIs
- **No open ports** beyond nginx

## Incident Response

| Condition | Action |
|-----------|--------|
| Vulnerability found | Pause trading, rotate keys, update deps |
| Breach suspected | Rotate all keys immediately, check logs |
| API key compromised | Disable key on exchange, rotate, check trades |

## Files Referenced

- `.secrets.local` — credentials (gitignored)
- `.env` — environment variables (gitignored)
- `scripts/_secrets.py` — centralized loader
- `scripts/hermes_constants.py` — kill switches, config
- `scripts/bug_hunter.py` — hardcoded secret scanner
