#!/usr/bin/env python3
"""
Investigate SYRUP trades and signals on Sep 10, 2026
"""
import sys
import os
import json
import sqlite3
from datetime import datetime

# Add scripts dir to path
sys.path.insert(0, '/root/.hermes/scripts')
from paths import *
from _secrets import BRAIN_DB_DICT

def query_postgres():
    """Query PostgreSQL brain DB for SYRUP trades on Sep 10, 2026"""
    import psycopg2
    
    print("=" * 80)
    print("POSTGRESQL BRAIN DB - SYRUP TRADES ON SEP 10, 2026")
    print("=" * 80)
    
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    try:
        cur = conn.cursor()
        
        # Get all SYRUP trades on Sep 10, 2026
        cur.execute("""
            SELECT id, token, direction, entry_price, exit_price, pnl_usdt, 
                   open_time, close_time, signal_created_at, 
                   _signal_metadata::text,
                   status, exit_reason, created_at, signal
            FROM trades 
            WHERE token = 'SYRUP' 
            AND (open_time >= '2026-09-10 00:00:00' AND open_time < '2026-09-11 00:00:00')
            ORDER BY open_time;
        """)
        
        rows = cur.fetchall()
        if not rows:
            print("No SYRUP trades found on Sep 10, 2026")
            return
        
        print(f"Found {len(rows)} SYRUP trades on Sep 10, 2026:")
        print("-" * 80)
        
        for row in rows:
            trade_id, token, direction, entry, exit_p, pnl, opened, closed, sig_created, meta, status, exit_reason, created, signal = row
            
            print(f"\nTRADE ID: {trade_id}")
            print(f"  Token: {token}")
            print(f"  Direction: {direction}")
            print(f"  Entry: {entry}")
            print(f"  Exit: {exit_p}")
            print(f"  PnL: {pnl}")
            print(f"  Opened: {opened}")
            print(f"  Closed: {closed}")
            print(f"  Signal Created: {sig_created}")
            print(f"  Status: {status}")
            print(f"  Exit Reason: {exit_reason}")
            print(f"  Signal: {signal}")
            print(f"  Created: {created}")
            
            # Parse signal metadata if present
            if meta:
                try:
                    metadata = json.loads(meta)
                    print(f"  Signal Metadata:")
                    print(f"    Confidence: {metadata.get('confidence', 'N/A')}")
                    print(f"    Source: {metadata.get('source', 'N/A')}")
                    print(f"    Signal Type: {metadata.get('signal_type', 'N/A')}")
                    print(f"    Price at Signal: {metadata.get('price_at_signal', 'N/A')}")
                    print(f"    Timestamp: {metadata.get('timestamp', 'N/A')}")
                    if 'raw_signal' in metadata:
                        raw = metadata['raw_signal']
                        print(f"    Raw Signal ID: {raw.get('id', 'N/A')}")
                        print(f"    Raw Signal Source: {raw.get('source', 'N/A')}")
                        print(f"    Raw Signal Created: {raw.get('created_at', 'N/A')}")
                        print(f"    Raw Signal Confidence: {raw.get('confidence', 'N/A')}")
                except:
                    print(f"  Raw metadata (could not parse): {meta[:500]}")
            else:
                print(f"  Signal Metadata: NONE")
            
            print("-" * 80)
    
    finally:
        cur.close()
        conn.close()

def query_signals_db():
    """Query SQLite signals DB for all SYRUP signals on Sep 10, 2026"""
    print("\n" + "=" * 80)
    print("SQLITE SIGNALS DB - ALL SYRUP SIGNALS ON SEP 10, 2026")
    print("=" * 80)
    
    if not os.path.exists(RUNTIME_DB):
        print(f"Signals DB not found at {RUNTIME_DB}")
        return
    
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        cur = conn.cursor()
        
        # Get all SYRUP signals on Sep 10
        cur.execute("""
            SELECT id, coin, direction, source, confidence, created_at, 
                   executed, decision, price_at_signal, 
                   signal_data
            FROM signals 
            WHERE coin = 'SYRUP' 
            AND created_at >= '2026-09-10 00:00:00' 
            AND created_at < '2026-09-11 00:00:00'
            ORDER BY created_at;
        """)
        
        rows = cur.fetchall()
        if not rows:
            print("No SYRUP signals found in signals DB on Sep 10, 2026")
            return
        
        print(f"Found {len(rows)} SYRUP signals:")
        print("-" * 80)
        
        for row in rows:
            sig_id, coin, direction, source, confidence, created, executed, decision, price_at, sig_data = row
            
            print(f"\nSIGNAL ID: {sig_id}")
            print(f"  Source: {source}")
            print(f"  Direction: {direction}")
            print(f"  Confidence: {confidence}")
            print(f"  Created: {created}")
            print(f"  Executed: {executed}")
            print(f"  Decision: {decision}")
            print(f"  Price at Signal: {price_at}")
            
            # Parse signal data if present
            if sig_data:
                try:
                    data = json.loads(sig_data)
                    print(f"  Signal Data Keys: {list(data.keys())}")
                    if 'confidence' in data:
                        print(f"  Confidence in Data: {data['confidence']}")
                    if 'source' in data:
                        print(f"  Source in Data: {data['source']}")
                except:
                    print(f"  Raw signal data (could not parse): {sig_data[:200]}")
            
            print("-" * 80)
    
    finally:
        cur.close()
        conn.close()

def check_signal_compactor_logs():
    """Check pipeline logs for signal compactor activity on Sep 10"""
    print("\n" + "=" * 80)
    print("PIPELINE LOG - SYRUP RELATED ENTRIES ON SEP 10, 2026")
    print("=" * 80)
    
    log_file = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
    if not os.path.exists(log_file):
        print(f"Log file not found at {log_file}")
        return
    
    # Read the log and search for SYRUP entries
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    syrup_lines = []
    for i, line in enumerate(lines):
        if 'SYRUP' in line and '2026-09-10' in line:
            syrup_lines.append((i+1, line.strip()))
    
    if not syrup_lines:
        print("No SYRUP entries found in pipeline.log for Sep 10")
        return
    
    print(f"Found {len(syrup_lines)} SYRUP related log lines:")
    print("-" * 80)
    
    for line_num, line in syrup_lines[:50]:  # Limit to 50 lines
        print(f"Line {line_num}: {line}")
    
    if len(syrup_lines) > 50:
        print(f"... and {len(syrup_lines) - 50} more lines")

def check_other_signal_sources():
    """Check if there are other signal sources that could have confidence 99"""
    print("\n" + "=" * 80)
    print("CHECKING OTHER SIGNAL SOURCES FOR SYRUP ON SEP 10")
    print("=" * 80)
    
    if not os.path.exists(RUNTIME_DB):
        print(f"Signals DB not found at {RUNTIME_DB}")
        return
    
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        cur = conn.cursor()
        
        # Check what sources exist in the signals table
        cur.execute("""
            SELECT DISTINCT source, COUNT(*) as count
            FROM signals 
            WHERE coin = 'SYRUP' 
            AND created_at >= '2026-09-10 00:00:00' 
            AND created_at < '2026-09-11 00:00:00'
            GROUP BY source;
        """)
        
        sources = cur.fetchall()
        print("Signal sources for SYRUP on Sep 10:")
        for source, count in sources:
            print(f"  {source}: {count} signals")
        
        # Check for any high confidence signals
        cur.execute("""
            SELECT id, source, confidence, created_at, executed, decision
            FROM signals 
            WHERE coin = 'SYRUP' 
            AND created_at >= '2026-09-10 00:00:00' 
            AND created_at < '2026-09-11 00:00:00'
            AND confidence >= 90
            ORDER BY confidence DESC;
        """)
        
        high_conf = cur.fetchall()
        if high_conf:
            print("\nHigh confidence signals (>=90):")
            for sig_id, source, conf, created, executed, decision in high_conf:
                print(f"  ID {sig_id}: {source}, confidence {conf}, created {created}, executed {executed}, decision {decision}")
        else:
            print("\nNo signals with confidence >= 90 found")
    
    finally:
        cur.close()
        conn.close()

def check_trade_execution_logs():
    """Check for trade execution logs around 12:39-12:48 on Sep 10"""
    print("\n" + "=" * 80)
    print("PIPELINE LOG - ENTRIES BETWEEN 12:35 AND 12:50 UTC ON SEP 10")
    print("=" * 80)
    
    log_file = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
    if not os.path.exists(log_file):
        print(f"Log file not found at {log_file}")
        return
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    time_range_lines = []
    for i, line in enumerate(lines):
        if '2026-09-10' in line:
            # Check if the time is between 12:35 and 12:50
            try:
                # Extract time from log line (assuming format like "2026-09-10 12:45:30")
                time_str = line.split(' ')[1] if len(line.split(' ')) > 1 else ''
                if time_str >= '12:35' and time_str <= '12:50':
                    time_range_lines.append((i+1, line.strip()))
            except:
                pass
    
    if not time_range_lines:
        print("No entries found between 12:35 and 12:50 UTC on Sep 10")
        return
    
    print(f"Found {len(time_range_lines)} log entries in time range:")
    print("-" * 80)
    
    for line_num, line in time_range_lines[:30]:  # Limit to 30 lines
        print(f"Line {line_num}: {line}")
    
    if len(time_range_lines) > 30:
        print(f"... and {len(time_range_lines) - 30} more lines")

if __name__ == "__main__":
    print("Starting SYRUP trade and signal investigation...")
    print(f"Date: 2026-09-10")
    print(f"Coin: SYRUP")
    
    try:
        query_postgres()
        query_signals_db()
        check_signal_compactor_logs()
        check_other_signal_sources()
        check_trade_execution_logs()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)