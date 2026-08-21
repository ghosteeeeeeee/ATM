#!/usr/bin/env python3
"""
HL Copy Trading - Leaderboard Scanner
Scans Hyperliquid for top traders and ranks them by performance.
"""
import json
import time
import os
import urllib.request
import urllib.error
from pathlib import Path
from hl_copy_db import get_db, init_db
from paths import HL_COPY_TRADERS

BASE_URL = "https://api.hyperliquid.xyz/info"

def _hl_info(payload: dict):
    """Make a POST request to HL info endpoint. Returns dict or list based on expected type."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[hl_info] Error: {e}")
        return None

def get_leaderboard() -> list:
    """Fetch leaderboard from Hyperliquid using web scraping."""
    try:
        from hl_web_scraper import scrape_all_sources
        wallets = scrape_all_sources()
        if wallets:
            return wallets
    except Exception as e:
        print(f"[leaderboard] Scraper failed: {e}")
    
    # Fallback to hardcoded list
    return [
        # Top traders from Dexly leaderboard (30d PnL rankings)
        "0x2ee6bef5b7b63aeefc9059f1436dabe259c34d1c",
        "0xc4bb9b6fda3112b381cb94f571bc72db541e7577",
        "0x179f3d11483dafe616d56b32c4ce2562faabbbbb",
        "0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36",
        "0xb2a1dc0db510e268b645387e852061ce22e2e7aa",
        "0x0e61a8fb14f6ac999646212d30b2192cd02080dd",
        "0x6890f5d900fc26c7563e5032f25bb180bcae2d4a",
        "0x32008fcb6bbd16532afc83ca8b6c920dde22c407",
        "0x856c35038594767646266bc7fd68dc26480e910d",
        "0xf822fa0fd364c573fcdb7009fcf47601bc8be01a",
        "0xc32235231d29831a2cb2a11e3f9c7f38160fc1dd",
        "0xd47587702a91731dc1089b5db0932cf820151a91",
        "0x45d26f28196d226497130c4bac709d808fed4029",
        "0xfe7ce058edc7cfcde9ef8262ba51f8d4796ab7ae",
        "0xc8b527864ef2ad6dc49de7e99943a3a76ad48891",
        "0x4e23288cee4960f9f962195c22948e4bc7ae20c3",
        "0xdfd526409007db0d524a62dedaaba7706736d88e",
        "0x5b5d51203a0f9079f8aeb098a6523a13f298c060",
        "0x57274d982f7ea905f5d574c5774a409cf7908d29",
        "0x4c78a97cef589b01bb91dbf893fffa14243d2444",
        "0xa312114b5795dff9b8db50474dd57701aa78ad1e",
        "0x75c1e71165f7a0be552cb38bdca42a07f6ee85a6",
        "0x88560b720239179d7f3f9e49ca934a4861593d7f",
        "0xebe126adabe1a8f08d3ce53b45e7cc994ca14070",
    ]

def get_user_state(wallet: str) -> dict | None:
    """Get user's clearinghouse state (positions, margin, etc.)."""
    result = _hl_info({
        "type": "clearinghouseState",
        "user": wallet
    })
    return result if isinstance(result, dict) else None

def get_user_fills(wallet: str, limit: int = 100) -> list:
    """Get user's recent fills."""
    result = _hl_info({
        "type": "userFills",
        "user": wallet
    })
    if isinstance(result, list):
        return result[:limit]
    return []

def get_user_portfolio(wallet: str) -> dict | None:
    """Get user's portfolio performance."""
    result = _hl_info({
        "type": "portfolio",
        "user": wallet
    })
    return result if isinstance(result, dict) else None

def calculate_score(trader: dict) -> float:
    """Calculate trader score based on multiple factors."""
    score = 0
    
    # Win rate (0-30 points)
    wr = trader.get('win_rate', 0)
    score += min(30, wr * 50)
    
    # Profit factor (0-20 points)
    pnl = trader.get('pnl_all_time', 0)
    dd = max(trader.get('max_drawdown', 1), 0.01)
    if pnl > 0:
        pf = pnl / dd
        score += min(20, pf * 2)
    else:
        # Negative PnL reduces score
        score += max(-20, pnl / 1000)
    
    # Trade count (0-15 points)
    tc = trader.get('trade_count', 0)
    score += min(15, tc / 20)
    
    # Volume (0-15 points)
    vol = trader.get('volume_30d', 0)
    score += min(15, vol / 100000)
    
    # Recency (0-20 points)
    last = trader.get('last_updated', 0)
    hours_since = (time.time() - last) / 3600
    if hours_since < 1:
        score += 20
    elif hours_since < 24:
        score += 15
    elif hours_since < 168:
        score += 10
    
    return round(score, 1)


def compute_copy_weight(trader_wallet: str) -> float:
    """Compute copy weight 0.1–2.0 based on our copy performance for this trader.
    
    Uses exponential moving average for recent-performance sensitivity.
    New traders start at 1.0; weight only adjusts after ≥COPY_TRADE_WEIGHT_MIN_TRADES.
    """
    try:
        from hermes_constants import COPY_TRADE_WEIGHT_MIN, COPY_TRADE_WEIGHT_MAX, COPY_TRADE_WEIGHT_MIN_TRADES
    except ImportError:
        COPY_TRADE_WEIGHT_MIN, COPY_TRADE_WEIGHT_MAX, COPY_TRADE_WEIGHT_MIN_TRADES = 0.1, 2.0, 5

    conn = get_db()
    try:
        stats = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'closed_win' THEN 1 ELSE 0 END) as wins,
                   SUM(COALESCE(pnl_pct, 0)) as total_pnl
            FROM trader_performance
            WHERE wallet = ? AND status LIKE 'closed_%'
        """, (trader_wallet,)).fetchone()
    finally:
        conn.close()

    total = stats['total'] or 0
    if total < COPY_TRADE_WEIGHT_MIN_TRADES:
        return 1.0

    wins = stats['wins'] or 0
    total_pnl = stats['total_pnl'] or 0
    wr = wins / total

    wr_bonus = (wr - 0.5) * 2.0
    pnl_bonus = max(-0.5, min(0.5, total_pnl / 10))
    sample_adj = max(0, 1.0 - total / 20)
    weight = 1.0 + wr_bonus + pnl_bonus + sample_adj

    return max(COPY_TRADE_WEIGHT_MIN, min(COPY_TRADE_WEIGHT_MAX, weight))

def detect_pattern(fills: list) -> str:
    """Classify trader style based on actual trade patterns."""
    if not fills or len(fills) < 10:
        return 'unknown'
    
    # Count opens vs closes to estimate holding pattern
    opens = sum(1 for f in fills if 'Open' in f.get('dir', ''))
    closes = sum(1 for f in fills if 'Close' in f.get('dir', ''))
    
    if opens == 0 and closes == 0:
        return 'unknown'
    
    # If mostly opens, likely a scalper (many small positions)
    # If balanced, likely a swing trader
    ratio = opens / closes if closes > 0 else 10
    
    if ratio > 5:
        return 'scalper'
    elif ratio > 2:
        return 'day_trader'
    elif ratio > 0.5:
        return 'swing_trader'
    else:
        return 'position_trader'

def scan_wallet(wallet: str) -> dict | None:
    """Scan a single wallet and return trader data."""
    try:
        state = get_user_state(wallet)
        if not state or 'marginSummary' not in state:
            return None
        
        margin = state['marginSummary']
        account_value = float(margin.get('accountValue', 0))
        
        if account_value < 10:  # Skip tiny accounts
            return None
        
        fills = get_user_fills(wallet, 200)
        positions = state.get('assetPositions', [])
        
        # Calculate basic stats
        wins = sum(1 for f in fills if float(f.get('closedPnl', 0)) > 0)
        total_closed = sum(1 for f in fills if float(f.get('closedPnl', 0)) != 0)
        win_rate = wins / total_closed if total_closed > 0 else 0
        
        total_pnl = sum(float(f.get('closedPnl', 0)) for f in fills)
        
        # Get portfolio history for drawdown
        max_dd = 0
        portfolio = get_user_portfolio(wallet)
        if portfolio and isinstance(portfolio, dict):
            # Portfolio returns dict with keys like 'allTime', 'day', etc.
            all_time = portfolio.get('allTime', {})
            if isinstance(all_time, dict):
                history = all_time.get('accountValueHistory', [])
                if isinstance(history, list) and history:
                    values = [float(v) for _, v in history if isinstance(v, (str, int, float))]
                    if values:
                        peak = values[0]
                        for v in values:
                            if v > peak:
                                peak = v
                            dd = (peak - v) / peak if peak > 0 else 0
                            max_dd = max(max_dd, dd)
        
        trader = {
            'wallet': wallet,
            'pnl_all_time': total_pnl,
            'win_rate': win_rate,
            'trade_count': len(fills),
            'volume_30d': account_value * 10,  # Rough estimate
            'max_drawdown': max_dd,
            'last_updated': int(time.time()),
            'pattern': detect_pattern(fills)
        }
        
        trader['score'] = calculate_score(trader)
        return trader
        
    except Exception as e:
        print(f"[scan_wallet] Error scanning {wallet}: {e}")
        return None

def save_trader(trader: dict):
    """Save trader to database. Preserves copy stats (copy_weight, copy_trades, copy_wins, copy_pnl)
    when the trader already exists — these are updated by hl_fill_monitor, not by leaderboard scans."""
    conn = get_db()
    try:
        # Check if trader exists
        existing = conn.execute(
            "SELECT copy_weight, copy_trades, copy_wins, copy_pnl FROM traders WHERE wallet = ?",
            (trader['wallet'],)
        ).fetchone()

        if existing:
            # UPDATE: preserve copy stats from existing record
            conn.execute("""
                UPDATE traders SET
                    pnl_all_time = ?, win_rate = ?, trade_count = ?,
                    volume_30d = ?, max_drawdown = ?, score = ?,
                    pattern = ?, last_updated = ?, active = 1
                WHERE wallet = ?
            """, (
                trader['pnl_all_time'],
                trader['win_rate'],
                trader['trade_count'],
                trader['volume_30d'],
                trader['max_drawdown'],
                trader['score'],
                trader['pattern'],
                trader['last_updated'],
                trader['wallet'],
            ))
        else:
            # INSERT: new trader with default copy stats
            conn.execute("""
                INSERT INTO traders
                (wallet, pnl_all_time, win_rate, trade_count, volume_30d,
                 max_drawdown, score, pattern, last_updated, active,
                 copy_weight, copy_trades, copy_wins, copy_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1.0, 0, 0, 0.0)
            """, (
                trader['wallet'],
                trader['pnl_all_time'],
                trader['win_rate'],
                trader['trade_count'],
                trader['volume_30d'],
                trader['max_drawdown'],
                trader['score'],
                trader['pattern'],
                trader['last_updated'],
            ))
        conn.commit()
    finally:
        conn.close()

def save_traders_json(traders: list):
    """Save traders to JSON for dashboard (atomic write)."""
    Path(HL_COPY_TRADERS).parent.mkdir(parents=True, exist_ok=True)
    tmp_path = HL_COPY_TRADERS + '.tmp'
    try:
        with open(tmp_path, 'w') as f:
            json.dump(traders, f, indent=2)
        os.replace(tmp_path, HL_COPY_TRADERS)
    except Exception as e:
        print(f"[save_traders_json] Error: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def scan_leaderboard(wallets: list = None) -> list:
    """Main function: scan wallets and return ranked traders."""
    if not wallets:
        wallets = get_leaderboard()
    
    traders = []
    for i, wallet in enumerate(wallets):
        if i > 0:
            time.sleep(1)  # Rate limit: 1 second between calls
        trader = scan_wallet(wallet)
        if trader and trader['score'] >= 25:
            save_trader(trader)
            traders.append(trader)
            print(f"[scan] {wallet[:10]}... score={trader['score']} pnl=${trader['pnl_all_time']:.0f}")
    
    # Sort by score
    traders.sort(key=lambda x: x['score'], reverse=True)
    save_traders_json(traders)
    
    return traders

if __name__ == "__main__":
    init_db()
    print("[leaderboard] Scanning for top traders...")
    
    # Example: scan a known wallet
    test_wallet = "0x324a9713603863FE3A678E83d7a81E20186126E7"
    traders = scan_leaderboard([test_wallet])
    
    print(f"\n[leaderboard] Found {len(traders)} traders")
    for t in traders:
        print(f"  {t['wallet'][:10]}... | Score: {t['score']} | PnL: ${t['pnl_all_time']:.0f} | WR: {t['win_rate']:.1%}")
