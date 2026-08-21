# Hermes Tech Stack

| Layer | Tech |
|-------|------|
| Language | Python 3 (~280 scripts, zero frameworks) |
| Local DB | SQLite (WAL mode) — prices, candles, signals |
| Remote DB | PostgreSQL (psycopg2) — trade history, analytics |
| Scheduler | systemd timers (59 timers, no cron) |
| Web server | nginx (serves static JSON dashboard data) |
| Dashboard | Streamlit (port 8501, local ML dashboard) |
| Exchange SDK | `hyperliquid-python-sdk` + `eth_account` |
| Market data | Binance REST API → stored in local SQLite |
| HTTP | `requests` + `urllib.request` (stdlib) |
| Math/ML | `numpy`, `pandas` |
| Config | `hermes_constants.py` (single source of truth) |
| Secrets | `.secrets.local` (gitignored) |
| Locking | `fcntl.flock` (file-level) |
| LLM | `mimo-v2.5` (context gate only, not core trading) |

## Design Choices

- **Local-first data** — all price reads route to local SQLite; external APIs write into local DB
- **Deterministic over LLM** — `signal_compactor.py` replaces LLM for trade decisions
- **File-based state** — JSON files for hotset, signals, regime data; atomic writes via `fcntl.flock`
- **Zero web frameworks** — pure scripts + SQLite + systemd + nginx
- **Two-database split** — SQLite for fast local reads, PostgreSQL for persistent trade history
