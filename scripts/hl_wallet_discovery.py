#!/usr/bin/env python3
"""
HL Copy Trading - Wallet Discovery
Periodically scans for new profitable traders from multiple sources.
Runs every 6 hours via systemd timer.
"""
import json
import os
import time
import subprocess
import re
from datetime import datetime
from pathlib import Path
from hl_copy_db import get_db
from paths import HERMES_DATA, WWW_DATA

# Known sources we've already scraped
KNOWN_SOURCES = {
    'dexly', 'hyperstats', 'beacon', 'liquidwhales', 'skynetx',
    'hypercopy', 'bearbullbunny', 'hyprswarm'
}

def run_command(cmd: str) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def discover_new_sources() -> list:
    """Search for new HL leaderboard sources we haven't scraped."""
    print("[discover] Searching for new leaderboard sources...")
    
    # Use the web scraper to find new sources
    from hl_web_scraper import scrape_new_leaderboard_sources
    new_wallets = scrape_new_leaderboard_sources()
    
    return new_wallets

def scrape_new_source(domain: str) -> list:
    """Try to scrape a new source for wallet addresses."""
    print(f"[discover] Scraping {domain}...")
    
    # Try common leaderboard paths
    paths = ['/leaderboard', '/traders', '/top-traders', '/rankings']
    
    for path in paths:
        url = f"https://{domain}{path}"
        cmd = f'''curl -s -L -H "User-Agent: Mozilla/5.0" "{url}" | grep -oP '0x[0-9a-fA-F]{{40}}' | sort -u'''
        output = run_command(cmd)
        
        if output and not output.startswith("Error") and len(output) > 100:
            wallets = output.split('\n')
            print(f"[discover] Found {len(wallets)} wallets from {domain}{path}")
            return wallets
    
    print(f"[discover] No wallets found from {domain}")
    return []

def discover_from_trading_competitions() -> list:
    """Search for wallets from HL trading competitions."""
    print("[discover] Searching trading competition results...")
    
    # Search for competition results
    query = "hyperliquid+trading+competition+winner+wallet"
    cmd = f'''curl -s -L -H "User-Agent: Mozilla/5.0" "https://html.duckduckgo.com/html/?q={query}" | grep -oP '0x[0-9a-fA-F]{{40}}' | sort -u'''
    output = run_command(cmd)
    
    wallets = []
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[discover] Found {len(wallets)} wallets from competitions")
    
    return wallets

def discover_from_social_media() -> list:
    """Search for wallets mentioned on crypto Twitter/Reddit."""
    print("[discover] Searching social media for HL wallets...")
    
    # Search for HL whale discussions
    queries = [
        "hyperliquid+whale+wallet+address",
        "hyperliquid+top+trader+0x",
        "hyperliquid+profitable+trader"
    ]
    
    all_wallets = []
    for query in queries:
        cmd = f'''curl -s -L -H "User-Agent: Mozilla/5.0" "https://html.duckduckgo.com/html/?q={query}" | grep -oP '0x[0-9a-fA-F]{{40}}' | sort -u'''
        output = run_command(cmd)
        
        if output and not output.startswith("Error"):
            wallets = output.split('\n')
            all_wallets.extend(wallets)
    
    unique = list(set(all_wallets))
    print(f"[discover] Found {len(unique)} unique wallets from social media")
    return unique

def evaluate_wallet(wallet: str) -> dict | None:
    """Evaluate if a wallet is worth tracking."""
    import urllib.request
    
    BASE_URL = 'https://api.hyperliquid.xyz/info'
    
    def hl_info(payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(BASE_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    
    try:
        # Check account value
        state = hl_info({'type': 'clearinghouseState', 'user': wallet})
        if not state or 'marginSummary' not in state:
            return None
        
        account_value = float(state['marginSummary'].get('accountValue', 0))
        if account_value < 1000:  # Skip small accounts
            return None
        
        # Get fills
        fills = hl_info({'type': 'userFills', 'user': wallet})
        if not fills or not isinstance(fills, list):
            return None
        
        # Calculate stats
        total_pnl = sum(float(f.get('closedPnl', 0)) for f in fills)
        wins = sum(1 for f in fills if float(f.get('closedPnl', 0)) > 0)
        total_closed = sum(1 for f in fills if float(f.get('closedPnl', 0)) != 0)
        wr = wins / total_closed if total_closed > 0 else 0
        
        # Only track profitable traders
        if total_pnl <= 0 or wr < 0.5:
            return None
        
        # Calculate score
        score = 0
        score += min(30, wr * 50)
        score += min(20, total_pnl / 1000)
        score += min(15, len(fills) / 20)
        score += 20  # Recency bonus
        
        return {
            'wallet': wallet,
            'account_value': account_value,
            'pnl': total_pnl,
            'win_rate': wr,
            'trade_count': len(fills),
            'score': min(100, score)
        }
        
    except Exception as e:
        return None

def save_new_trader(trader: dict):
    """Save a new trader to the database."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO traders 
            (wallet, pnl_all_time, win_rate, trade_count, volume_30d, 
             score, last_updated, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            trader['wallet'],
            trader['pnl'],
            trader['win_rate'],
            trader['trade_count'],
            trader['account_value'],
            trader['score'],
            int(time.time())
        ))
        conn.commit()
    finally:
        conn.close()

def save_discovery_log(discoveries: list):
    """Save discovery results to log file."""
    log_file = f"{HERMES_DATA}/hl_discovery_log.json"
    
    try:
        with open(log_file) as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        log = []
    
    log.append({
        'timestamp': datetime.now().isoformat(),
        'discoveries': len(discoveries),
        'wallets': [d['wallet'] for d in discoveries[:10]]
    })
    
    # Keep last 100 entries
    log = log[-100:]
    
    tmp_path = log_file + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(log, f, indent=2)
    os.replace(tmp_path, log_file)

def run_discovery():
    """Main discovery function."""
    print("=" * 60)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running wallet discovery")
    print("=" * 60)
    
    all_wallets = []
    
    # 1. Search for new sources and scrape them
    print("\n[1/3] Discovering and scraping new sources...")
    new_wallets = discover_new_sources()
    all_wallets.extend(new_wallets)
    
    # 2. Search trading competitions
    print("\n[2/3] Searching trading competitions...")
    comp_wallets = discover_from_trading_competitions()
    all_wallets.extend(comp_wallets)
    
    # 3. Search social media
    print("\n[3/3] Searching social media...")
    social_wallets = discover_from_social_media()
    all_wallets.extend(social_wallets)
    
    # Deduplicate
    unique_wallets = list(set(all_wallets))
    print(f"\n[discover] Total unique wallets found: {len(unique_wallets)}")
    
    # Evaluate and save new traders
    discoveries = []
    for wallet in unique_wallets[:50]:  # Limit to 50 evaluations
        # Check if already tracked
        conn = get_db()
        try:
            existing = conn.execute(
                "SELECT wallet FROM traders WHERE wallet = ?", (wallet,)
            ).fetchone()
        finally:
            conn.close()
        
        if existing:
            continue  # Skip already tracked
        
        trader = evaluate_wallet(wallet)
        if trader and trader['score'] >= 50:
            save_new_trader(trader)
            discoveries.append(trader)
            print(f"[discover] ✅ {wallet[:10]}... | Score: {trader['score']} | PnL: ${trader['pnl']:.0f} | WR: {trader['win_rate']:.1%}")
        time.sleep(0.5)  # Rate limit
    
    # Save log
    save_discovery_log(discoveries)
    
    print(f"\n[discover] Found {len(discoveries)} new profitable traders")
    return discoveries

if __name__ == "__main__":
    discoveries = run_discovery()
