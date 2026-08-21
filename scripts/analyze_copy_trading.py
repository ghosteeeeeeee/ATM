#!/usr/bin/env python3
"""
Hermes Copy Trader Analysis
Comprehensive analysis of copy trading performance and pro trader evaluation.
"""

import sys
import os
import json
import sqlite3
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

# Add scripts directory to path
sys.path.insert(0, '/root/.hermes/scripts')

def get_postgres_connection():
    """Get PostgreSQL connection."""
    from _secrets import BRAIN_DB_DICT
    DB_CONFIG = BRAIN_DB_DICT.copy()
    DB_CONFIG.setdefault('port', 5432)
    return psycopg2.connect(**DB_CONFIG)

def get_sqlite_connection():
    """Get SQLite connection."""
    from hl_copy_db import get_db
    return get_db()

def analyze_copy_trades(pg_conn):
    """Analyze copy trades from PostgreSQL."""
    print("=" * 80)
    print("SECTION 1: COPY TRADING PERFORMANCE (from PostgreSQL trades table)")
    print("=" * 80)
    
    cursor = pg_conn.cursor()
    
    # Get all copy_trader trades
    query = """
    SELECT id, token, direction, entry_price, hl_entry_price, pnl_pct, pnl_usdt,
           close_reason, _signal_metadata, open_time, close_time, status, leverage, signal
    FROM trades WHERE signal LIKE '%hl_copy_trader%' ORDER BY id
    """
    
    cursor.execute(query)
    trades = cursor.fetchall()
    
    if not trades:
        print("No copy_trader trades found in PostgreSQL.")
        return {}
    
    print(f"\nTotal copy trades found: {len(trades)}")
    
    # Parse trades
    parsed_trades = []
    for trade in trades:
        trade_dict = {
            'id': trade[0],
            'token': trade[1],
            'direction': trade[2],
            'entry_price': trade[3],
            'hl_entry_price': trade[4],
            'pnl_pct': trade[5],
            'pnl_usdt': trade[6],
            'close_reason': trade[7],
            '_signal_metadata': trade[8],
            'open_time': trade[9],
            'close_time': trade[10],
            'status': trade[11],
            'leverage': trade[12],
            'signal': trade[13]
        }
        
        # Parse signal metadata
        if trade_dict['_signal_metadata']:
            try:
                if isinstance(trade_dict['_signal_metadata'], str):
                    trade_dict['metadata'] = json.loads(trade_dict['_signal_metadata'])
                else:
                    trade_dict['metadata'] = trade_dict['_signal_metadata']
            except:
                trade_dict['metadata'] = {}
        else:
            trade_dict['metadata'] = {}
        
        parsed_trades.append(trade_dict)
    
    # Overall statistics
    wins = [t for t in parsed_trades if t['pnl_usdt'] and float(t['pnl_usdt']) > 0]
    losses = [t for t in parsed_trades if t['pnl_usdt'] and float(t['pnl_usdt']) < 0]
    breakeven = [t for t in parsed_trades if t['pnl_usdt'] == 0 or t['pnl_usdt'] is None]
    
    total_pnl = sum(float(t['pnl_usdt'] or 0) for t in parsed_trades)
    win_rate = len(wins) / len(parsed_trades) * 100 if parsed_trades else 0
    
    print(f"\n--- Overall Performance ---")
    print(f"Total Trades: {len(parsed_trades)}")
    print(f"Wins: {len(wins)} ({win_rate:.1f}%)")
    print(f"Losses: {len(losses)}")
    print(f"Breakeven/Unknown: {len(breakeven)}")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Average PnL per trade: ${total_pnl/len(parsed_trades):.2f}" if parsed_trades else "N/A")
    
    # Token breakdown
    print(f"\n--- Token Breakdown ---")
    token_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})
    
    for t in parsed_trades:
        token = t['token'] or 'UNKNOWN'
        token_stats[token]['count'] += 1
        pnl = float(t['pnl_usdt'] or 0)
        token_stats[token]['pnl'] += pnl
        if pnl > 0:
            token_stats[token]['wins'] += 1
        elif pnl < 0:
            token_stats[token]['losses'] += 1
    
    print(f"{'Token':<10} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'Win Rate':<10} {'Total PnL':<12}")
    print("-" * 64)
    
    for token in sorted(token_stats.keys()):
        stats = token_stats[token]
        wr = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
        print(f"{token:<10} {stats['count']:<8} {stats['wins']:<6} {stats['losses']:<8} {wr:.1f}%{'':<5} ${stats['pnl']:.2f}")
    
    # Exit reasons analysis
    print(f"\n--- Exit Reasons ---")
    exit_reasons = defaultdict(int)
    for t in parsed_trades:
        reason = t['close_reason'] or 'UNKNOWN'
        exit_reasons[reason] += 1
    
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        print(f"{reason}: {count} trades")
    
    # Signal metadata analysis - extract trader wallets
    print(f"\n--- Trader Attribution (from signal metadata) ---")
    trader_trades = defaultdict(list)
    for t in parsed_trades:
        metadata = t.get('metadata', {})
        if isinstance(metadata, dict):
            trader_wallet = metadata.get('trader_wallet') or metadata.get('wallet')
            if trader_wallet:
                trader_trades[trader_wallet].append(t)
    
    if trader_trades:
        print(f"Trades attributed to {len(trader_trades)} different pro traders:")
        for wallet, trades in sorted(trader_trades.items(), key=lambda x: -len(x[1])):
            wins_count = sum(1 for t in trades if t['pnl_usdt'] and float(t['pnl_usdt']) > 0)
            total_pnl = sum(float(t['pnl_usdt'] or 0) for t in trades)
            wr = wins_count / len(trades) * 100 if trades else 0
            print(f"  {wallet[:12]}...: {len(trades)} trades, {wins_count} wins ({wr:.1f}%), PnL: ${total_pnl:.2f}")
    else:
        print("No trader wallet attribution found in signal metadata")
    
    # Leverage analysis
    print(f"\n--- Leverage Usage ---")
    leverage_counts = defaultdict(int)
    for t in parsed_trades:
        lev = t['leverage'] or 1
        leverage_counts[lev] += 1
    
    for lev, count in sorted(leverage_counts.items()):
        print(f"{lev}x: {count} trades")
    
    # Recent trades (last 30 days)
    print(f"\n--- Recent Performance (Last 30 Days) ---")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_trades = []
    for t in parsed_trades:
        if t['open_time']:
            open_dt = t['open_time']
            if isinstance(open_dt, str):
                try:
                    open_dt = datetime.fromisoformat(open_dt.replace('Z', '+00:00'))
                except:
                    continue
            if isinstance(open_dt, datetime) and open_dt > thirty_days_ago:
                recent_trades.append(t)
    
    if recent_trades:
        recent_wins = sum(1 for t in recent_trades if t['pnl_usdt'] and float(t['pnl_usdt']) > 0)
        recent_pnl = sum(float(t['pnl_usdt'] or 0) for t in recent_trades)
        recent_wr = recent_wins / len(recent_trades) * 100 if recent_trades else 0
        print(f"Recent trades: {len(recent_trades)}")
        print(f"Recent wins: {recent_wins} ({recent_wr:.1f}%)")
        print(f"Recent PnL: ${recent_pnl:.2f}")
    else:
        print("No recent trades found (or date parsing failed)")
    
    return {
        'trades': parsed_trades,
        'trader_trades': trader_trades,
        'token_stats': token_stats,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'exit_reasons': exit_reasons
    }

def analyze_sqlite_data(sqlite_conn):
    """Analyze data from SQLite database."""
    print("\n" + "=" * 80)
    print("SECTION 2: PRO TRADER DATA (from SQLite hl_copy.db)")
    print("=" * 80)
    
    cursor = sqlite_conn.cursor()
    
    # Get active traders
    print(f"\n--- Active Traders ---")
    cursor.execute("SELECT wallet, score, pnl_all_time, win_rate, trade_count, pattern, alias, copy_trades, copy_wins, copy_pnl FROM traders WHERE active = 1 ORDER BY score DESC")
    traders = cursor.fetchall()
    
    if not traders:
        print("No active traders found.")
    else:
        print(f"Total active traders: {len(traders)}")
        print(f"\n{'Wallet (first 12)':<15} {'Alias':<20} {'Score':<8} {'PnL All':<12} {'Win Rate':<10} {'Trades':<8} {'Copy Tr':<10} {'Copy WR':<10}")
        print("-" * 103)
        
        for trader in traders:
            wallet, score, pnl_all_time, win_rate, trade_count, pattern, alias, copy_trades, copy_wins, copy_pnl = trader
            copy_wr = (copy_wins / copy_trades * 100) if copy_trades and copy_trades > 0 else 0
            print(f"{wallet[:12]}...     {alias or 'N/A':<20} {score or 0:<8.1f} ${pnl_all_time or 0:<11.2f} {win_rate or 0:.1f}%{'':<4} {trade_count or 0:<8} {copy_trades or 0:<10} {copy_wr:.1f}%")
    
    # Trader fills analysis
    print(f"\n--- Trader Fills Analysis ---")
    cursor.execute("SELECT COUNT(*) FROM trader_fills")
    total_fills = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT wallet) FROM trader_fills")
    unique_wallets = cursor.fetchone()[0]
    
    print(f"Total fills recorded: {total_fills}")
    print(f"Unique wallets with fills: {unique_wallets}")
    
    # Recent fills (last 30 days)
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    cursor.execute("SELECT COUNT(*) FROM trader_fills WHERE time > ?", (thirty_days_ago,))
    recent_fills_count = cursor.fetchone()[0]
    print(f"Recent fills (last 30 days): {recent_fills_count}")
    
    # Performance by token from fills
    print(f"\n--- Fills Performance by Token ---")
    cursor.execute("""
        SELECT coin, COUNT(*) as count, 
               SUM(CASE WHEN closed_pnl > 0 THEN 1 ELSE 0 END) as wins,
               SUM(closed_pnl) as total_pnl
        FROM trader_fills 
        WHERE closed_pnl != 0 
        GROUP BY coin 
        ORDER BY total_pnl DESC
    """)
    
    token_fills = cursor.fetchall()
    print(f"{'Token':<10} {'Fills':<8} {'Wins':<8} {'Total PnL':<12}")
    print("-" * 38)
    for token, count, wins, total_pnl in token_fills:
        wr = wins / count * 100 if count > 0 else 0
        print(f"{token:<10} {count:<8} {wins:<8} ${total_pnl:.2f}")
    
    # HYPE-specific fills analysis
    print(f"\n--- HYPE Token Trading Performance ---")
    cursor.execute("""
        SELECT wallet, COUNT(*) as trades, 
               SUM(CASE WHEN closed_pnl > 0 THEN 1 ELSE 0 END) as wins,
               SUM(closed_pnl) as total_pnl
        FROM trader_fills 
        WHERE coin = 'HYPE'
        GROUP BY wallet
        HAVING trades > 5
        ORDER BY total_pnl DESC
    """)
    
    hype_traders = cursor.fetchall()
    if hype_traders:
        print(f"{'Wallet (first 12)':<15} {'Trades':<8} {'Wins':<8} {'Win Rate':<10} {'Total PnL':<12}")
        print("-" * 63)
        for wallet, trades, wins, total_pnl in hype_traders:
            wr = wins / trades * 100 if trades > 0 else 0
            print(f"{wallet[:12]}...     {trades:<8} {wins:<8} {wr:.1f}%{'':<5} ${total_pnl:.2f}")
    else:
        print("No HYPE traders with >5 trades found")
    
    # Current positions
    print(f"\n--- Current Trader Positions ---")
    cursor.execute("""
        SELECT tp.wallet, tp.coin, tp.sz, tp.entry_px, tp.unrealized_pnl, tp.leverage, t.alias
        FROM trader_positions tp
        LEFT JOIN traders t ON tp.wallet = t.wallet
        ORDER BY tp.unrealized_pnl DESC
    """)
    
    positions = cursor.fetchall()
    if positions:
        print(f"Total open positions: {len(positions)}")
        print(f"{'Wallet (first 12)':<15} {'Alias':<20} {'Coin':<8} {'Size':<10} {'Entry Px':<12} {'Unreal PnL':<12} {'Lev':<6}")
        print("-" * 93)
        for wallet, coin, sz, entry_px, unreal_pnl, leverage, alias in positions[:20]:  # Top 20
            print(f"{wallet[:12]}...     {alias or 'N/A':<20} {coin:<8} {sz:<10.4f} ${entry_px:<11.2f} ${unreal_pnl:<11.2f} {leverage or 1}x")
    else:
        print("No current positions found")
    
    # Copy performance table
    print(f"\n--- Copy Trade Performance (from trader_performance) ---")
    cursor.execute("""
        SELECT wallet, token, direction, status, COUNT(*) as trades,
               SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
               SUM(pnl_usdt) as total_pnl,
               AVG(pnl_pct) as avg_pnl_pct
        FROM trader_performance
        GROUP BY wallet, token, status
        ORDER BY total_pnl DESC
    """)
    
    perf_data = cursor.fetchall()
    if perf_data:
        print(f"{'Wallet (first 12)':<15} {'Token':<8} {'Dir':<6} {'Status':<10} {'Trades':<8} {'Wins':<8} {'PnL':<12} {'Avg %':<8}")
        print("-" * 85)
        for wallet, token, direction, status, trades, wins, total_pnl, avg_pnl_pct in perf_data[:30]:  # Top 30
            wr = wins / trades * 100 if trades > 0 else 0
            print(f"{wallet[:12]}...     {token or 'N/A':<8} {direction or 'N/A':<6} {status or 'N/A':<10} {trades:<8} {wins:<8} ${total_pnl:<11.2f} {avg_pnl_pct or 0:.2f}%")
    else:
        print("No performance data found")
    
    return {
        'traders': traders,
        'total_fills': total_fills,
        'hype_traders': hype_traders
    }

def cross_reference_analysis(pg_data, sqlite_data):
    """Cross-reference PostgreSQL and SQLite data."""
    print("\n" + "=" * 80)
    print("SECTION 3: CROSS-REFERENCE ANALYSIS")
    print("=" * 80)
    
    if not pg_data or not pg_data.get('trader_trades'):
        print("No cross-reference possible - no trader attribution in PostgreSQL trades")
        return
    
    # Get SQLite trader data
    sqlite_conn = sqlite_data.get('conn')
    if not sqlite_conn:
        print("No SQLite connection available")
        return
    
    cursor = sqlite_conn.cursor()
    
    # For each trader we've copied, check their HYPE performance
    print(f"\n--- Pro Traders We've Copied vs Their Actual Performance ---")
    
    copied_wallets = list(pg_data['trader_trades'].keys())
    
    for wallet in copied_wallets[:10]:  # Top 10
        # Get our trades for this trader
        our_trades = pg_data['trader_trades'][wallet]
        our_wins = sum(1 for t in our_trades if t['pnl_usdt'] and float(t['pnl_usdt']) > 0)
        our_pnl = sum(float(t['pnl_usdt'] or 0) for t in our_trades)
        our_wr = our_wins / len(our_trades) * 100 if our_trades else 0
        
        # Get their HYPE fills
        cursor.execute("""
            SELECT COUNT(*) as trades,
                   SUM(CASE WHEN closed_pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(closed_pnl) as total_pnl
            FROM trader_fills
            WHERE wallet = ? AND coin = 'HYPE'
        """, (wallet,))
        
        their_data = cursor.fetchone()
        their_trades, their_wins, their_pnl = their_data if their_data else (0, 0, 0)
        their_trades = their_trades or 0
        their_wins = their_wins or 0
        their_pnl = their_pnl or 0
        their_wr = their_wins / their_trades * 100 if their_trades > 0 else 0
        
        # Get trader info
        cursor.execute("SELECT alias, score, pnl_all_time, win_rate FROM traders WHERE wallet = ?", (wallet,))
        trader_info = cursor.fetchone()
        alias, score, pnl_all_time, win_rate = trader_info if trader_info else (None, 0, 0, 0)
        
        print(f"\nWallet: {wallet[:12]}... ({alias or 'No alias'})")
        print(f"  Leaderboard Score: {score or 0:.1f}")
        print(f"  Their Lifetime Win Rate: {win_rate or 0:.1f}%")
        print(f"  Their Recent HYPE Win Rate: {their_wr:.1f}% ({their_trades} trades)")
        print(f"  Their Recent HYPE PnL: ${their_pnl:.2f}")
        print(f"  Our Win Rate Copying Them: {our_wr:.1f}% ({len(our_trades)} trades)")
        print(f"  Our PnL Copying Them: ${our_pnl:.2f}")
        
        # Correlation analysis
        if score and score > 50:
            if their_wr > 60 and our_wr > 50:
                print(f"  Assessment: ✅ Strong performer - high score aligns with recent results")
            elif their_wr < 40:
                print(f"  Assessment: ⚠️ Mismatch - high score but poor recent HYPE performance")
            else:
                print(f"  Assessment: ⚡ Mixed - score doesn't clearly predict copy success")
        else:
            print(f"  Assessment: 📊 Low-score trader - limited leaderboard presence")

def identify_best_traders(sqlite_conn):
    """Identify best traders to copy based on recent performance."""
    print("\n" + "=" * 80)
    print("SECTION 4: RECOMMENDED TRADERS TO COPY")
    print("=" * 80)
    
    cursor = sqlite_conn.cursor()
    
    # Get traders with good recent HYPE performance
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    
    cursor.execute("""
        SELECT wallet, 
               COUNT(*) as trades,
               SUM(CASE WHEN closed_pnl > 0 THEN 1 ELSE 0 END) as wins,
               SUM(closed_pnl) as total_pnl,
               AVG(closed_pnl) as avg_pnl
        FROM trader_fills
        WHERE coin = 'HYPE' AND time > ?
        GROUP BY wallet
        HAVING trades >= 3
        ORDER BY total_pnl DESC
    """, (thirty_days_ago,))
    
    recent_hype_performers = cursor.fetchall()
    
    if recent_hype_performers:
        print(f"\n--- Top Recent HYPE Traders (Last 30 Days, Min 3 Trades) ---")
        print(f"{'Wallet (first 12)':<15} {'Trades':<8} {'Wins':<8} {'Win Rate':<10} {'Total PnL':<12} {'Avg PnL':<12}")
        print("-" * 75)
        
        for wallet, trades, wins, total_pnl, avg_pnl in recent_hype_performers[:10]:
            wr = wins / trades * 100 if trades > 0 else 0
            print(f"{wallet[:12]}...     {trades:<8} {wins:<8} {wr:.1f}%{'':<5} ${total_pnl:<11.2f} ${avg_pnl:.2f}")
        
        # Cross-check with leaderboard scores
        print(f"\n--- Cross-check with Leaderboard Scores ---")
        for wallet, trades, wins, total_pnl, avg_pnl in recent_hype_performers[:5]:
            cursor.execute("SELECT score, alias, pnl_all_time FROM traders WHERE wallet = ?", (wallet,))
            trader = cursor.fetchone()
            if trader:
                score, alias, pnl_all_time = trader
                print(f"  {wallet[:12]}... ({alias or 'N/A'})")
                print(f"    Recent HYPE: {trades} trades, {wins/(trades or 1)*100:.1f}% WR, ${total_pnl:.2f}")
                print(f"    Leaderboard: Score={score or 0:.1f}, All-time PnL=${pnl_all_time or 0:.2f}")
                if score and score > 30 and total_pnl > 100:
                    print(f"    Recommendation: 🟢 STRONG CANDIDATE")
                elif score and score > 10:
                    print(f"    Recommendation: 🟡 MODERATE - verify consistency")
                else:
                    print(f"    Recommendation: 🔴 LOW PRIORITY - unproven")
    else:
        print("No recent HYPE traders found with minimum trade threshold")

def analyze_stop_loss_patterns(pg_data):
    """Analyze stop loss patterns to see if ATR stops are hitting too quickly."""
    print("\n" + "=" * 80)
    print("SECTION 5: STOP LOSS & EXIT PATTERN ANALYSIS")
    print("=" * 80)
    
    if not pg_data or not pg_data.get('trades'):
        return
    
    trades = pg_data['trades']
    
    # Exit reason analysis
    print(f"\n--- Exit Reason Distribution ---")
    exit_reasons = pg_data.get('exit_reasons', {})
    total = len(trades)
    
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        print(f"{reason}: {count} ({pct:.1f}%)")
    
    # Calculate average hold time for different exit reasons
    print(f"\n--- Average Hold Time by Exit Reason ---")
    hold_times = defaultdict(list)
    
    for t in trades:
        if t['open_time'] and t['close_time']:
            try:
                open_dt = t['open_time']
                close_dt = t['close_time']
                
                if isinstance(open_dt, str):
                    open_dt = datetime.fromisoformat(open_dt.replace('Z', '+00:00'))
                if isinstance(close_dt, str):
                    close_dt = datetime.fromisoformat(close_dt.replace('Z', '+00:00'))
                
                if isinstance(open_dt, datetime) and isinstance(close_dt, datetime):
                    hold_time = (close_dt - open_dt).total_seconds() / 3600  # hours
                    reason = t['close_reason'] or 'UNKNOWN'
                    hold_times[reason].append(hold_time)
            except:
                pass
    
    if hold_times:
        for reason, times in sorted(hold_times.items(), key=lambda x: -len(x[1])):
            avg_time = sum(times) / len(times) if times else 0
            min_time = min(times) if times else 0
            max_time = max(times) if times else 0
            print(f"{reason}: {len(times)} trades, Avg={avg_time:.1f}h, Min={min_time:.1f}h, Max={max_time:.1f}h")
    
    # PnL by exit reason
    print(f"\n--- PnL by Exit Reason ---")
    pnl_by_reason = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0})
    
    for t in trades:
        reason = t['close_reason'] or 'UNKNOWN'
        pnl = float(t['pnl_usdt'] or 0)
        pnl_by_reason[reason]['count'] += 1
        pnl_by_reason[reason]['pnl'] += pnl
        if pnl > 0:
            pnl_by_reason[reason]['wins'] += 1
    
    for reason, data in sorted(pnl_by_reason.items(), key=lambda x: -x[1]['pnl']):
        wr = data['wins'] / data['count'] * 100 if data['count'] > 0 else 0
        avg_pnl = data['pnl'] / data['count'] if data['count'] > 0 else 0
        print(f"{reason}: {data['count']} trades, ${data['pnl']:.2f} total, {wr:.1f}% WR, ${avg_pnl:.2f} avg")

def main():
    """Main analysis function."""
    print("HERMES COPY TRADER COMPREHENSIVE ANALYSIS")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Connect to PostgreSQL
        print("\nConnecting to PostgreSQL...")
        pg_conn = get_postgres_connection()
        
        # Connect to SQLite
        print("Connecting to SQLite...")
        sqlite_conn = get_sqlite_connection()
        
        # Run analyses
        pg_data = analyze_copy_trades(pg_conn)
        sqlite_data = analyze_sqlite_data(sqlite_conn)
        sqlite_data['conn'] = sqlite_conn  # Add connection for cross-reference
        
        cross_reference_analysis(pg_data, sqlite_data)
        identify_best_traders(sqlite_conn)
        analyze_stop_loss_patterns(pg_data)
        
        # Final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        
        if pg_data:
            print(f"\nKey Findings:")
            print(f"1. Total copy trades analyzed: {len(pg_data.get('trades', []))}")
            print(f"2. Overall win rate: {pg_data.get('win_rate', 0):.1f}%")
            print(f"3. Total PnL: ${pg_data.get('total_pnl', 0):.2f}")
            
            # Top performing tokens
            token_stats = pg_data.get('token_stats', {})
            if token_stats:
                best_token = max(token_stats.items(), key=lambda x: x[1]['pnl'])
                print(f"4. Best performing token: {best_token[0]} (${best_token[1]['pnl']:.2f})")
            
            # Exit reason insights
            exit_reasons = pg_data.get('exit_reasons', {})
            if exit_reasons:
                top_exit = max(exit_reasons.items(), key=lambda x: x[1])
                print(f"5. Most common exit: {top_exit[0]} ({top_exit[1]} trades)")
        
        print(f"\nRecommendations:")
        print(f"1. Focus on traders with >60% recent HYPE win rate")
        print(f"2. Avoid traders where score ≠ actual performance")
        print(f"3. Monitor exit reasons - if too many 'ATR_STOP' hits, adjust parameters")
        print(f"4. Consider position sizing based on trader confidence score")
        
        # Close connections
        pg_conn.close()
        sqlite_conn.close()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())