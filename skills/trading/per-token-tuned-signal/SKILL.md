---
name: per-token-tuned-signal
description: How to add a new per-token tuned signal to Hermes — scanner, tuner DB, daily systemd timer, and signal_gen registration.
triggers:
  - add new signal to Hermes
  - per-token tuned indicator
  - candle aggregation 1m to higher TF
---

# Per-Token Tuned Signal — Add to Hermes

How to add a new per-token tuned signal to Hermes that aggregates from 1m candles.

## Pattern

A per-token tuned signal has 3 components:

1. **Scanner script** (`scripts/<name>.py`) — aggregates 1m→higher TF, runs crossover/indicator logic, emits signals via `signal_schema.add_signal()`
2. **Tuner DB** (`data/<name>_tuner.db`) — SQLite storing per-token best params per direction
3. **Systemd timer** (`systemd/hermes-<name>.timer` + `.service`) — runs `--sweep` daily

## Step-by-Step

### 1. Create the scanner script

Key sections needed:

```python
# Paths
_DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')
_TUNER_DB = os.path.join(_DATA_DIR, '<name>_tuner.db')
_CANDLES_DB = os.path.join(_DATA_DIR, 'candles.db')

# ── 5m aggregation from 1m ──────────────────────────────────────────────────
def get_5m_candles(token: str, lookback_1m: int = 600) -> List[dict]:
    """Fetch 1m candles, aggregate to 5m OHLCV (oldest first)."""
    rows = list(reversed(rows))
    bars = []
    for i in range(0, len(rows), 5):
        chunk = rows[i:i+5]
        open_, high, low, close, volume = chunk[0][1], max(r[2] for r in chunk), min(r[3] for r in chunk), chunk[-1][4], sum(r[5] for r in chunk)
        bars.append({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume})
    return bars

# ── Tuner DB ─────────────────────────────────────────────────────────────────
def init_tuner_db():
    conn = sqlite3.connect(_TUNER_DB, timeout=10)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS <name>_best (
        token TEXT NOT NULL, direction TEXT NOT NULL,
        fast INTEGER NOT NULL, slow INTEGER NOT NULL,
        win_rate REAL NOT NULL, avg_pnl_pct REAL NOT NULL,
        signal_count INTEGER NOT NULL,
        total_long INTEGER NOT NULL DEFAULT 0,
        total_short INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL,
        PRIMARY KEY (token, direction))""")
    conn.commit(); conn.close()

def load_token_params() -> Dict: ...
def save_token_params(token, direction, fast, slow, win_rate, avg_pnl_pct, signal_count, ...): ...

# ── Backtest sweep ───────────────────────────────────────────────────────────
# Sweep fast/slow grid, backtest each combo for each direction.
# Score by avg_pnl_pct (primary), signal_count (tiebreak).
# Use _backtest_pair(closes, fast, slow, direction) returning win_rate/pnl/count.

def run_sweep_all_tokens() -> int:
    """Sweep all tokens in candles.db, save best params per token+direction."""

# ── Scanner ─────────────────────────────────────────────────────────────────
# Guards: open positions, recent trades, delisted, blacklisted, stale price.
# After signal: set_cooldown(token, direction, hours=1).

def scan_<name>_signals(prices_dict: dict) -> int:
    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (recent_trade_exists, is_delisted, SHORT_BLACKLIST,
                            MIN_TRADE_INTERVAL_MINUTES, set_cooldown)

# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sweep', action='store_true')
    parser.add_argument('--scan',  action='store_true')
    # ...
```

### 2. Create systemd timer + service

`/root/.hermes/systemd/hermes-<name>.timer`:
```ini
[Unit]
Description=Hermes <Name> Tuner — full sweep every 24h
After=network.target

[Timer]
OnBootSec=5
OnUnitActiveSec=24h
Persistent=true

[Install]
WantedBy=timers.target
```

`/root/.hermes/systemd/hermes-<name>.service`:
```ini
[Unit]
Description=Hermes <Name> Tuner
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /root/.hermes/scripts/<name>.py --sweep
WorkingDirectory=/root/.hermes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl link /root/.hermes/systemd/hermes-<name>.timer /root/.hermes/systemd/hermes-<name>.service
sudo systemctl enable --now hermes-<name>.timer
```

### 3. Register in signal_gen.py

Add import:
```python
from <name> import scan_<name>_signals
```

Add call in `run()`:
```python
<name>_added = scan_<name>_signals(prices_dict)
if <name>_added:
    print(f'  <Name> signals: {<name>_added} <name> emitted')
```

## Signal source naming convention

Use `<indicator>[-<tf>]-<direction>`:
- `macd-1m-long` / `macd-1m-short`
- `zscore-long` / `zscore-short`
- `ma-5m-long` / `ma-5m-short`

## Key constraints

- **Sweep grid**: slow >= 2.5 * fast (prevents overfitting fast/slow too close)
- **Min signals for tuned**: tokens with <15 historical signals use defaults
- **Backtest scoring**: avg_pnl_pct primary, signal_count tiebreak
- **No dual fire**: if SHORT fires for a token, skip LONG that run

## Files created for ma_cross_5m (example)

- `/root/.hermes/scripts/ma_cross_5m.py`
- `/root/.hermes/systemd/hermes-ma-cross-5m-tuner.timer`
- `/root/.hermes/systemd/hermes-ma-cross-5m-tuner.service`
