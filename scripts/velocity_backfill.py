#!/usr/bin/env python3
"""
velocity_backfill.py — Backfill trade duration data and compute velocity stats.

Phase 1 of Trade Velocity Tracking spec.
"""
import sys
import os
import sqlite3
import subprocess
import statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))


def get_pg_trades():
    """Get closed trades from PostgreSQL with open_time and close_time."""
    try:
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-t', '-A', '-F', '|',
             '-c', """
                SELECT id, token, direction, signal, open_time, close_time,
                       pnl_pct, status
                FROM trades
                WHERE status IN ('closed', 'tp_hit', 'sl_hit')
                  AND open_time IS NOT NULL
                ORDER BY close_time DESC
             """],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"PostgreSQL error: {result.stderr}")
            return []

        trades = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 8:
                trades.append({
                    'id': int(parts[0]),
                    'token': parts[1],
                    'direction': parts[2],
                    'signal': parts[3],
                    'open_time': parts[4],
                    'close_time': parts[5],
                    'pnl_pct': float(parts[6]) if parts[6] else 0,
                    'status': parts[7],
                })
        return trades
    except Exception as e:
        print(f"Error fetching trades: {e}")
        return []


def compute_duration(open_time_str, close_time_str):
    """Compute trade duration in seconds."""
    try:
        # Parse timestamps
        for fmt in ['%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%d %H:%M:%S%z',
                     '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
            try:
                open_dt = datetime.strptime(open_time_str, fmt)
                close_dt = datetime.strptime(close_time_str, fmt)
                break
            except ValueError:
                continue
        else:
            return None

        duration = (close_dt - open_dt).total_seconds()
        return max(duration, 0)  # ensure non-negative
    except Exception:
        return None


def backfill_durations():
    """Backfill trade_duration for closed trades."""
    trades = get_pg_trades()
    if not trades:
        print("No trades found to backfill")
        return 0

    updated = 0
    for trade in trades:
        duration = compute_duration(trade['open_time'], trade['close_time'])
        if duration is None:
            continue

        try:
            subprocess.run(
                ['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-c',
                 'UPDATE trades SET trade_duration = $1 WHERE id = $2',
                 '--', str(duration), str(trade['id'])],
                capture_output=True, timeout=10
            )
            updated += 1
        except Exception as e:
            print(f"Error updating trade {trade['id']}: {e}")

    print(f"Backfilled duration for {updated}/{len(trades)} trades")
    return updated


def compute_velocity_stats():
    """Compute velocity stats per signal+token+direction."""
    try:
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-t', '-A', '-F', '|',
             '-c', """
                SELECT signal, token, direction, trade_duration, pnl_pct, status
                FROM trades
                WHERE trade_duration IS NOT NULL
                  AND trade_duration > 0
                  AND status IN ('closed', 'tp_hit', 'sl_hit')
                ORDER BY close_time DESC
             """],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"PostgreSQL error: {result.stderr}")
            return

        # Parse trades
        trades = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 6:
                trades.append({
                    'signal': parts[0],
                    'token': parts[1],
                    'direction': parts[2],
                    'duration': float(parts[3]),
                    'pnl_pct': float(parts[4]) if parts[4] else 0,
                    'status': parts[5],
                })

        # Group by signal+token+direction
        groups = {}
        for t in trades:
            key = (t['signal'], t['token'], t['direction'])
            if key not in groups:
                groups[key] = []
            groups[key].append(t)

        # Compute stats
        conn = sqlite3.connect('/root/.hermes/brain/associative_memory.db')
        cur = conn.cursor()

        for (signal, token, direction), group_trades in groups.items():
            if len(group_trades) < 2:
                continue  # need at least 2 trades for meaningful stats

            durations = [t['duration'] for t in group_trades]
            wins = [t for t in group_trades if t['pnl_pct'] > 0]
            losses = [t for t in group_trades if t['pnl_pct'] <= 0]

            avg_hold = statistics.mean(durations)
            median_hold = statistics.median(durations)
            avg_tp = statistics.mean([t['duration'] for t in wins]) if wins else None
            avg_sl = statistics.mean([t['duration'] for t in losses]) if losses else None

            # Velocity score: fast winners = high score
            if avg_tp and avg_sl and avg_sl > 0:
                speed_ratio = avg_sl / avg_tp
                velocity_score = min(speed_ratio * 10, 30)  # cap at +30
            else:
                velocity_score = 0

            # Efficiency rating: $/minute return
            total_pnl = sum(t['pnl_pct'] for t in group_trades)
            total_minutes = sum(durations) / 60
            efficiency = total_pnl / total_minutes if total_minutes > 0 else 0

            # Upsert stats
            cur.execute("""
                INSERT OR REPLACE INTO signal_velocity_stats
                (signal, token, direction, avg_hold_seconds, median_hold_seconds,
                 avg_time_to_tp, avg_time_to_sl, velocity_score, efficiency_rating,
                 trade_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (signal, token, direction, avg_hold, median_hold,
                  avg_tp, avg_sl, velocity_score, efficiency, len(group_trades)))

        conn.commit()
        conn.close()

        print(f"Computed velocity stats for {len(groups)} signal+token+direction groups")
    except Exception as e:
        print(f"Error computing velocity stats: {e}")


if __name__ == '__main__':
    print("=== Trade Velocity Backfill ===")
    print("\n1. Backfilling trade durations...")
    backfill_durations()
    print("\n2. Computing velocity stats...")
    compute_velocity_stats()
    print("\nDone!")
