# HL Copy Trading System — Spec

## Overview

Track successful Hyperliquid traders on-chain and copy their trades. All HL trades are public and real-time via API.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        hl_copy_trader.py                         │
├─────────────────────────────────────────────────────────────────┤
│  1. IDENTIFY     2. TRACK      3. ANALYZE     4. COPY           │
│  ───────────     ─────────     ──────────     ──────            │
│  Scan wallets    Poll fills    Score traders  Execute trades    │
│  Find top PnL    Track posns   Filter best    Size positions    │
│  Rank by WR      Log trades    Detect patterns Risk limits      │
└─────────────────────────────────────────────────────────────────┘
         ↓                ↓               ↓              ↓
    traders.json    fills.db       scores.json    hl_orders API
```

## Phase 1: Identify Top Traders

### Data Sources
1. **Leaderboard** — HL shows top traders by PnL
2. **Vaults** — Public vaults with track records
3. **Manual list** — Wallets we know are profitable

### Selection Criteria
| Metric | Threshold | Why |
|--------|-----------|-----|
| Total PnL | > $50k | Not just lucky on one trade |
| Win Rate | > 55% | Consistent edge |
| Avg Hold Time | 1h - 7d | Not scalping, not bagholding |
| Max Drawdown | < 30% | Risk management |
| Trade Count | > 100 | Statistical significance |
| Volume | > $1M | Liquid enough to copy |

### Output
```json
{
  "wallet": "0x...",
  "alias": "Whale#42",
  "pnl_all_time": 250000,
  "win_rate": 0.62,
  "avg_hold_hours": 18.5,
  "max_drawdown": 0.22,
  "trade_count": 347,
  "volume_30d": 5000000,
  "score": 87.5,
  "last_updated": "2026-08-05T22:00:00Z"
}
```

## Phase 2: Track Trader Activity

### Polling Strategy
```
Every 30s:  userFills (new trades)
Every 5m:   clearinghouseState (positions)
Every 1h:   portfolio (PnL update)
Every 24h:  Re-score traders
```

### Fill Tracking
```sql
CREATE TABLE trader_fills (
    id INTEGER PRIMARY KEY,
    wallet TEXT NOT NULL,
    coin TEXT NOT NULL,
    side TEXT NOT NULL,          -- 'B' or 'A'
    px REAL NOT NULL,
    sz REAL NOT NULL,
    time INTEGER NOT NULL,
    closed_pnl REAL DEFAULT 0,
    is_open BOOLEAN NOT NULL,   -- true = opening, false = closing
    copied BOOLEAN DEFAULT false,
    copy_time INTEGER
);

CREATE TABLE trader_positions (
    wallet TEXT NOT NULL,
    coin TEXT NOT NULL,
    sz REAL NOT NULL,
    entry_px REAL NOT NULL,
    unrealized_pnl REAL,
    leverage REAL,
    liquidation_px REAL,
    last_updated INTEGER,
    PRIMARY KEY (wallet, coin)
);
```

### Detection Logic
```python
def detect_new_trades(wallet, current_fills, last_known):
    new_fills = []
    for fill in current_fills:
        if fill['time'] > last_known_time:
            is_open = fill['dir'].startswith('Open')
            new_fills.append({
                'wallet': wallet,
                'coin': fill['coin'],
                'side': fill['side'],
                'px': float(fill['px']),
                'sz': float(fill['sz']),
                'time': fill['time'],
                'is_open': is_open
            })
    return new_fills
```

## Phase 3: Analyze & Score

### Trader Score Formula
```python
score = (
    win_rate * 30 +           # 0-30 points
    (pnl / max_drawdown) * 20 +  # 0-20 points (profit factor)
    consistency * 20 +        # 0-20 points (Sharpe-like)
    volume_score * 15 +       # 0-15 points (liquidity)
    recency_score * 15        # 0-15 points (recent performance)
)
```

### Pattern Detection
```python
def detect_pattern(trader_fills):
    """Classify trader style"""
    avg_hold = mean([f['hold_time'] for f in trader_fills])
    win_rate = sum(1 for f in trader_fills if f['pnl'] > 0) / len(trader_fills)
    
    if avg_hold < 3600:      return 'scalper'
    if avg_hold < 86400:     return 'day_trader'
    if avg_hold < 604800:    return 'swing_trader'
    return 'position_trader'
```

### Filtering Rules
- **Exclude**: Traders with < 100 trades
- **Exclude**: Traders with > 40% drawdown
- **Exclude**: Scalpers (hold < 1 hour) — we can't copy fast enough
- **Exclude**: Traders with suspicious patterns (always same size, etc.)
- **Prefer**: Swing traders (1h-7d hold) — we can copy in time

## Phase 4: Copy Execution

### Position Sizing
```python
def calculate_copy_size(trader_sz, trader_account, our_account, max_pct=0.10):
    """
    Scale position proportionally
    Never risk more than 10% of account per trade
    """
    ratio = our_account / trader_account
    copy_sz = trader_sz * ratio
    
    # Cap at max_pct of our account
    max_sz = our_account * max_pct / current_price
    return min(copy_sz, max_sz)
```

### Risk Limits
| Limit | Value | Action |
|-------|-------|--------|
| Max position % | 10% | Cap size |
| Max daily trades | 50 | Pause copying |
| Max concurrent positions | 10 | Close oldest |
| Max drawdown (copy) | 15% | Stop all copying |
| Min trader score | 70 | Don't copy |

### Order Types
```python
# Trader opens → We open (market order, slight slippage OK)
# Trader closes → We close (market order, immediate)
# Trader adjusts → We adjust proportionally

def execute_copy(trade_action, our_size):
    if trade_action == 'open':
        place_market_order(trade_action['coin'], trade_action['side'], our_size)
    elif trade_action == 'close':
        place_market_order(trade_action['coin'], opposite_side(trade_action['side']), our_size)
```

## Phase 5: Monitoring & Output

### Output Channels (NO Telegram)
1. **TUI** — Live terminal view of tracked traders
2. **Markdown reports** — `/var/www/hermes/data/hl_copy_*.md`
3. **HTML dashboard** — Future: `/var/www/hermes/dashboard/hl_copy.html`

### TUI Display
```
═══════════════════════════════════════════════════════════
 HL COPY TRADING — 5 Tracked | 12 Copies Today
═══════════════════════════════════════════════════════════
 WALLET          SCORE  PnL      WR     LAST TRADE
 0x3f69...5728   87.5   +$250k   62%    12m ago
 0x11af...42fa   82.1   +$180k   58%    45m ago
 0x5ac9...9487   79.3   +$95k    55%    2h ago
═══════════════════════════════════════════════════════════
 LAST COPY: BTC Long @ $64,500 | Size: 0.05 | +$12.50
 TOTAL COPY PnL: +$1,250.50 (vs Traders: +$1,890.25)
═══════════════════════════════════════════════════════════
```

### Markdown Report (auto-updated hourly)
```markdown
# HL Copy Trading Report — 2026-08-05

## Active Traders
| Wallet | Score | 30d PnL | WR | Status |
|--------|-------|---------|-----|--------|
| 0x3f69... | 87.5 | +$25k | 62% | Active |

## Trades Today
| Time | Trader | Coin | Side | Size | PnL |
|------|--------|------|------|------|-----|
| 21:45 | 0x3f69... | BTC | Long | 0.05 | +$12.50 |

## Performance
- Copies today: 12
- Win rate: 58%
- Total PnL: +$1,250.50
```

### HTML Dashboard (Phase 2)
- `/var/www/hermes/dashboard/hl_copy.html`
- Charts: Trader performance, copy divergence
- Filters: By trader, coin, time range
- Auto-refresh via nginx

## File Structure

```
scripts/
├── hl_copy_trader.py          # Main orchestrator
├── hl_leaderboard.py          # Scan & rank traders
├── hl_fill_monitor.py         # Track fills in real-time
├── hl_copy_execute.py         # Execute copy trades
├── hl_trader_analyzer.py      # Score & filter traders
└── hl_copy_tui.py             # Terminal UI (curses)

var/www/hermes/data/
├── hl_copy_report.md          # Hourly markdown report
└── hl_copy_traders.json       # Current tracked traders

var/www/hermes/dashboard/      # Future
└── hl_copy.html               # HTML dashboard
```

## Config (hermes_constants.py additions)

```python
# HL Copy Trading
HL_COPY_TRADING_ENABLED = False
HL_COPY_WALLETS = []                    # Manual wallet list
HL_COPY_MAX_POSITION_PCT = 0.10        # Max 10% per trade
HL_COPY_MAX_DRAWDOWN = 0.15            # Stop at 15% drawdown
HL_COPY_MIN_SCORE = 70                 # Minimum trader score
HL_COPY_POLL_INTERVAL = 30             # Seconds between polls
HL_COPY_MAX_DAILY_TRADES = 50          # Daily trade limit
HL_COPY_REPORT_PATH = "/var/www/hermes/data/hl_copy_report.md"
HL_COPY_DASHBOARD_PATH = "/var/www/hermes/dashboard/hl_copy.html"
```

## Data Flow

```
Hyperliquid API
      │
      ▼
┌─────────────┐
│ Poll fills  │ ←── every 30s
└─────────────┘
      │
      ▼
┌─────────────┐
│ Detect new  │
│ trades      │
└─────────────┘
      │
      ├── Trader score >= 70? ──No──→ Skip
      │
      ▼ Yes
┌─────────────┐
│ Calculate   │
│ position sz │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Risk checks │ ←── drawdown, daily limit, etc.
└─────────────┘
      │
      ├── Failed? ──→ Log & Alert
      │
      ▼ Pass
┌─────────────┐
│ Execute     │
│ market order│
└─────────────┘
      │
      ▼
┌─────────────┐
│ Log to DB   │
│ Update stats│
└─────────────┘
```

## MVP (Phase 1)

Start with paper trading only:

1. **Scan leaderboard** — Get top 20 wallets
2. **Track fills** — Log all trades to SQLite
3. **Paper copy** — Simulate copying, track divergence
4. **TUI** — Live terminal view of tracked traders
5. **Markdown report** — Auto-updated hourly
6. **Weekly summary** — Which traders we'd have copied and PnL

Skip for MVP:
- Live execution
- Complex scoring
- Pattern detection
- Auto-stop
- HTML dashboard (Phase 2)

## Open Questions

1. **Leaderboard access** — Is there an API endpoint, or do we scrape?
2. **Rate limits** — How often can we poll userFills?
3. **Position conflicts** — What if we're already in a position?
4. **Partial fills** — How to handle if trader's fill is partial?
5. **Multi-leg trades** — Trader opens with multiple orders?

---

**Status**: Spec complete, awaiting review
**Next**: Build MVP (paper trading)
**Owner**: Hermes
