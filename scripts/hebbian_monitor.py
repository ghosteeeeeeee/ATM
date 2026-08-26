#!/usr/bin/env python3
"""Hebbian Network Monitor — dashboard for associative memory health.

Shows:
1. Top strengthened synapses (what the system "knows" works)
2. Top weakened synapses (what the system "knows" doesn't work)
3. Trade outcome statistics
4. Concept node activity
5. Hebbian gate influence on recent trades

Run manually or via systemd timer for monitoring.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA

DB_PATH = os.path.join(HERMES_DATA, '..', 'brain', 'associative_memory.db')
STATS_FILE = os.path.join(HERMES_DATA, 'hebbian_monitor_stats.json')


def _connect():
    return sqlite3.connect(DB_PATH, timeout=10)


def get_synapse_stats():
    """Get top strengthened and weakened synapses."""
    conn = _connect()
    cur = conn.cursor()
    
    # Top strengthened (high weight = strong association)
    cur.execute("""
        SELECT s.weight, s.co_occurrences, s.last_updated,
               a.name as concept_a, a.label_type as label_a,
               b.name as concept_b, b.label_type as label_b
        FROM synapse_weights s
        JOIN concept_nodes a ON s.concept_a_id = a.id
        JOIN concept_nodes b ON s.concept_b_id = b.id
        WHERE s.co_occurrences > 0
        ORDER BY s.weight DESC
        LIMIT 20
    """)
    strengthened = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
    
    # Top weakened (low weight = negative association)
    cur.execute("""
        SELECT s.weight, s.co_occurrences, s.last_updated,
               a.name as concept_a, a.label_type as label_a,
               b.name as concept_b, b.label_type as label_b
        FROM synapse_weights s
        JOIN concept_nodes a ON s.concept_a_id = a.id
        JOIN concept_nodes b ON s.concept_b_id = b.id
        WHERE s.co_occurrences > 0 AND s.weight < 1.0
        ORDER BY s.weight ASC
        LIMIT 20
    """)
    weakened = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
    
    # Most active synapses (highest co_occurrences)
    cur.execute("""
        SELECT s.weight, s.co_occurrences, s.last_updated,
               a.name as concept_a, a.label_type as label_a,
               b.name as concept_b, b.label_type as label_b
        FROM synapse_weights s
        JOIN concept_nodes a ON s.concept_a_id = a.id
        JOIN concept_nodes b ON s.concept_b_id = b.id
        WHERE s.co_occurrences > 0
        ORDER BY s.co_occurrences DESC
        LIMIT 20
    """)
    most_active = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
    
    conn.close()
    return strengthened, weakened, most_active


def get_trade_stats():
    """Get trade outcome statistics."""
    conn = _connect()
    cur = conn.cursor()
    
    # Overall stats
    cur.execute("SELECT count(*) FROM trade_log")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM trade_log WHERE won = 1")
    wins = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM trade_log WHERE won = 0")
    losses = cur.fetchone()[0]
    
    cur.execute("SELECT AVG(pnl_pct) FROM trade_log")
    avg_pnl = cur.fetchone()[0] or 0
    
    # Recent activity
    cur.execute("SELECT count(*) FROM trade_log WHERE created_at > datetime('now', '-1 day')")
    last_24h = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM trade_log WHERE created_at > datetime('now', '-7 days')")
    last_7d = cur.fetchone()[0]
    
    # Last trade
    cur.execute("SELECT token, signal, direction, won, pnl_pct, close_time FROM trade_log ORDER BY rowid DESC LIMIT 1")
    last_trade = cur.fetchone()
    
    # Win rate by signal family
    cur.execute("""
        SELECT signal, count(*) as cnt, sum(won) as wins, avg(pnl_pct) as avg_pnl
        FROM trade_log
        WHERE created_at > datetime('now', '-7 days')
        GROUP BY signal
        HAVING cnt >= 3
        ORDER BY cnt DESC
        LIMIT 15
    """)
    signal_stats = [dict(zip(['signal', 'trades', 'wins', 'avg_pnl'], r)) for r in cur.fetchall()]
    
    conn.close()
    return {
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': wins / total * 100 if total else 0,
        'avg_pnl': avg_pnl,
        'last_24h': last_24h,
        'last_7d': last_7d,
        'last_trade': last_trade,
        'signal_stats': signal_stats,
    }


def get_concept_stats():
    """Get concept node statistics."""
    conn = _connect()
    cur = conn.cursor()
    
    cur.execute("SELECT count(*) FROM concept_nodes")
    total_nodes = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM synapse_weights")
    total_synapses = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM synapse_weights WHERE co_occurrences > 0")
    active_synapses = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM synapse_weights WHERE weight > 1.0")
    strengthened = cur.fetchone()[0]
    
    cur.execute("SELECT count(*) FROM synapse_weights WHERE weight < 1.0 AND co_occurrences > 0")
    weakened = cur.fetchone()[0]
    
    # Label type distribution
    cur.execute("""
        SELECT label_type, count(*) as cnt
        FROM concept_nodes
        GROUP BY label_type
        ORDER BY cnt DESC
    """)
    label_dist = dict(cur.fetchall())
    
    # Recently active concepts
    cur.execute("""
        SELECT name, label_type, last_seen
        FROM concept_nodes
        ORDER BY last_seen DESC
        LIMIT 10
    """)
    recent_concepts = [dict(zip(['name', 'label_type', 'last_seen'], r)) for r in cur.fetchall()]
    
    conn.close()
    return {
        'total_nodes': total_nodes,
        'total_synapses': total_synapses,
        'active_synapses': active_synapses,
        'strengthened': strengthened,
        'weakened': weakened,
        'label_distribution': label_dist,
        'recent_concepts': recent_concepts,
    }


def get_gate_influence():
    """Get hebbian gate influence from hebbian_gate_stats.json."""
    stats_file = os.path.join(HERMES_DATA, 'hebbian_gate_stats.json')
    try:
        with open(stats_file) as f:
            data = json.load(f)
        return data
    except Exception:
        return {'auto_decisions': [], 'error': 'File not found or empty'}


def generate_report():
    """Generate full monitoring report."""
    print("=" * 70)
    print("🧠 HEBBIAN NETWORK MONITOR")
    print(f"   Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    
    # 1. Trade stats
    trade_stats = get_trade_stats()
    print(f"\n📊 TRADE OUTCOMES")
    print(f"   Total: {trade_stats['total_trades']} | Wins: {trade_stats['wins']} | Losses: {trade_stats['losses']}")
    print(f"   Win Rate: {trade_stats['win_rate']:.1f}% | Avg PnL: {trade_stats['avg_pnl']:.3f}%")
    print(f"   Last 24h: {trade_stats['last_24h']} trades | Last 7d: {trade_stats['last_7d']} trades")
    if trade_stats['last_trade']:
        lt = trade_stats['last_trade']
        print(f"   Last Trade: {lt[0]} {lt[2]} {'WON' if lt[3] else 'LOST'} ({lt[4]:+.3f}%) @ {lt[5]}")
    
    # Signal stats
    if trade_stats['signal_stats']:
        print(f"\n   Signal Performance (7d, 3+ trades):")
        for s in trade_stats['signal_stats']:
            wr = s['wins'] / s['trades'] * 100 if s['trades'] else 0
            emoji = '🟢' if wr >= 55 else '🟡' if wr >= 45 else '🔴'
            print(f"   {emoji} {s['signal'][:45]:<45s} {s['trades']:3d}T WR={wr:5.1f}% avg={s['avg_pnl']:+.3f}%")
    
    # 2. Concept network
    concept_stats = get_concept_stats()
    print(f"\n🕸️  CONCEPT NETWORK")
    print(f"   Nodes: {concept_stats['total_nodes']} | Synapses: {concept_stats['total_synapses']}")
    print(f"   Active: {concept_stats['active_synapses']} | Strengthened: {concept_stats['strengthened']} | Weakened: {concept_stats['weakened']}")
    print(f"   Label Distribution: {concept_stats['label_distribution']}")
    
    # 3. Top strengthened synapses
    strengthened, weakened, most_active = get_synapse_stats()
    
    if strengthened:
        print(f"\n💪 TOP STRENGTHENED SYNAPSES (what works)")
        for s in strengthened[:10]:
            print(f"   {s['concept_a'][:30]:<30s} ↔ {s['concept_b'][:30]:<30s} weight={s['weight']:.2f} co={s['co_occurrences']}")
    
    if weakened:
        print(f"\n📉 TOP WEAKENED SYNAPSES (what doesn't work)")
        for s in weakened[:10]:
            print(f"   {s['concept_a'][:30]:<30s} ↔ {s['concept_b'][:30]:<30s} weight={s['weight']:.2f} co={s['co_occurrences']}")
    
    if most_active:
        print(f"\n🔥 MOST ACTIVE SYNAPSES (most co-occurrences)")
        for s in most_active[:10]:
            emoji = '🟢' if s['weight'] > 1.0 else '🔴' if s['weight'] < 1.0 else '⚪'
            print(f"   {emoji} {s['concept_a'][:30]:<30s} ↔ {s['concept_b'][:30]:<30s} weight={s['weight']:.2f} co={s['co_occurrences']}")
    
    # 4. Gate influence
    gate = get_gate_influence()
    if gate.get('auto_decisions'):
        print(f"\n🚪 HEBBIAN GATE INFLUENCE")
        recent = gate['auto_decisions'][-5:]
        for d in recent:
            print(f"   {d.get('token', '?')} {d.get('signal', '?')}: boost={d.get('boost', 0):.2f} wr={d.get('wr', 0):.1%} n={d.get('n', 0)}")
    
    print("\n" + "=" * 70)


def save_stats():
    """Save stats to JSON for dashboard API."""
    trade_stats = get_trade_stats()
    concept_stats = get_concept_stats()
    strengthened, weakened, most_active = get_synapse_stats()
    
    data = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'trades': trade_stats,
        'concepts': concept_stats,
        'top_strengthened': strengthened[:10],
        'top_weakened': weakened[:10],
        'most_active': most_active[:10],
    }
    
    fd, tmp = os.path.mkstemp(dir=os.path.dirname(STATS_FILE), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, STATS_FILE)
        print(f"Saved stats to {STATS_FILE}")
    except Exception as e:
        os.unlink(tmp)
        print(f"Error saving stats: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Hebbian Network Monitor')
    parser.add_argument('--save', action='store_true', help='Save stats to JSON')
    args = parser.parse_args()
    
    generate_report()
    
    if args.save:
        save_stats()
