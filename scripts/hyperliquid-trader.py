#!/usr/bin/env python3
"""
Hyperliquid Auto-Trading Bot v4 - SL/TP Monitoring
"""
import requests
import json
import time
import os
import hashlib
from datetime import datetime
from eth_keys import keys
import subprocess
import traceback
import psycopg2

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'trading.log')
BRAIN_DB = "host=/var/run/postgresql dbname=brain user=postgres password=postgres"

def log(msg, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'[{timestamp}] [{level}] [hyperliquid-trader] {msg}'
    print(log_line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
    except: pass  # Don't crash on log failures

def log_error(msg, exc=None):
    error_msg = f'{msg}'
    if exc:
        error_msg += f': {exc}'
        error_msg += f'\n{traceback.format_exc()}'
    log(error_msg, 'ERROR')

def pg_query(query, params=None):
    """Execute a SELECT query with parameterized inputs"""
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        log_error(f'pg_query: {e}')
        return []

def pg_exec(query, params=None):
    """Execute an UPDATE/DELETE with parameterized inputs"""
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute(query, params or ())
        conn.commit()
        cur.close()
        conn.close()
        return cur.rowcount
    except Exception as e:
        log_error(f'pg_exec: {e}')
        return 0

CONFIG_FILE = "/root/.secrets/hyperliquid-wallet.json"
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'hyperliquid-trading-state.json')

API_URL = "https://api.hyperliquid.xyz/info"

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def get_all_prices():
    try:
        r = requests.post(API_URL, json={"type": "allMids"}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log_error(f'get_all_prices: {e}')
    return {}

def check_sl_tp():
    """Check brain for SL/TP hits - uses parameterized queries"""
    try:
        # Use parameterized psycopg2 query instead of subprocess psql
        rows = pg_query(
            "SELECT id, token, entry_price, stop_loss, target, direction FROM trades WHERE status = 'open' AND server='Hermes'"
        )
        
        prices = get_all_prices()
        hits = []
        
        for row in rows:
            if not row:
                continue
            trade_id = row[0]
            token = row[1]
            entry = float(row[2] or 0)
            sl = float(row[3] or 0)
            tp = float(row[4] or 0)
            direction = (row[5] or 'LONG').strip().upper()
            is_long = direction == 'LONG'
            
            if token in prices:
                current = float(prices[token])
                log(f"Trade #{trade_id} {token}: ${current} (SL: ${sl}, TP: ${tp}, {direction})")
                
                # SL/TP logic differs for LONG vs SHORT
                # LONG: SL hits when price falls below, TP hits when price rises above
                # SHORT: SL hits when price rises above, TP hits when price falls below
                sl_hit = (is_long and sl > 0 and current <= sl) or (not is_long and sl > 0 and current >= sl)
                tp_hit = (is_long and tp > 0 and current >= tp) or (not is_long and tp > 0 and current <= tp)
                
                if sl_hit:
                    hits.append({'id': trade_id, 'token': token, 'action': 'SL_HIT', 'price': current})
                    log(f"🚨 SL HIT: Trade #{trade_id} {token} @ ${current} - AUTO-CLOSING")
                    # Auto-close trade in brain using parameterized query
                    pg_exec(
                        "UPDATE trades SET status = 'closed', exit_price = %s WHERE id = %s",
                        (current, trade_id)
                    )
                elif tp_hit:
                    hits.append({'id': trade_id, 'token': token, 'action': 'TP_HIT', 'price': current})
                    log(f"🎯 TP HIT: Trade #{trade_id} {token} @ ${current} - AUTO-CLOSING")
                    # Auto-close trade in brain using parameterized query
                    pg_exec(
                        "UPDATE trades SET status = 'closed', exit_price = %s WHERE id = %s",
                        (current, trade_id)
                    )
        
        return hits
    except Exception as e:
        log_error(f'check_sl_tp: {e}')
        return []

def main():
    log("=== Hyperliquid Auto-Trading Bot v4 ===")
    config = load_config()
    address = config["hyperliquid_address"]
    private_key = config["hyperliquid_private_key"]
    
    key = bytes.fromhex(private_key[2:])
    priv_key = keys.PrivateKey(key)
    log(f"Wallet: {priv_key.public_key.to_checksum_address()}")
    
    while True:
        try:
            prices = get_all_prices()
            log(f"Prices loaded: {len(prices)} tokens")
            
            # Check SL/TP
            hits = check_sl_tp()
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            log("Stopped")
            break
        except Exception as e:
            log_error(f'main loop: {e}')
            time.sleep(30)

if __name__ == "__main__":
    main()
