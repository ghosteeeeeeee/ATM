#!/usr/bin/env python3
"""Backfill Hebbian associations from historical closed trades.

Learns all pairs from each closed trade: token ↔ signal ↔ direction ↔
z_score_tier ↔ momentum_state. Won → strengthen. Lost → weaken.

Reads: PostgreSQL trades table (close_time IS NOT NULL).
Writes: brain.db /root/.hermes/brain/associative_memory.db.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')

from _secrets import BRAIN_DB_DICT
from hebbian_engine import HebbianEngine
import psycopg2
import time


def main():
    print("Loading closed trades from PostgreSQL...")
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    c = conn.cursor()
    c.execute("""
        SELECT token, signal, direction, pnl_pct,
               signal_z_score_tier, signal_momentum_state
        FROM trades
        WHERE close_time IS NOT NULL
          AND signal IS NOT NULL
          AND token IS NOT NULL
          AND pnl_pct IS NOT NULL
        ORDER BY open_time
    """)
    rows = c.fetchall()
    conn.close()
    print(f"  {len(rows)} closed trades to learn from")

    eng = HebbianEngine()
    wins = losses = 0
    t0 = time.time()
    for i, (token, signal, direction, pnl_pct, z_tier, momentum) in enumerate(rows):
        result = eng.learn_trade_outcome(
            token=token, signal=signal, direction=direction, pnl_pct=pnl_pct,
            z_score_tier=z_tier, momentum_state=momentum,
        )
        if pnl_pct > 0:
            wins += 1
        else:
            losses += 1
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(rows)}] {time.time()-t0:.1f}s — wins={wins} losses={losses}")

    print(f"\nDone: {len(rows)} trades learned in {time.time()-t0:.1f}s")
    print(f"  Wins: {wins} | Losses: {losses}")

    stats = eng.get_stats()
    print(f"\nBrain.db state:")
    print(f"  Nodes:    {stats['nodes']}")
    print(f"  Synapses: {stats['synapses']}")
    print(f"  Total weight: {stats['total_weight']:.1f}")
    print(f"  Label distribution: {stats['label_distribution']}")


if __name__ == '__main__':
    main()