#!/usr/bin/env python3
"""DEEP AUDIT Part 2: Reproduce claim using STORED metadata values, compare with entry-time values."""
import psycopg2
import sqlite3
import json
from scipy import stats

pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
pg_cur = pg.cursor()
candles_db = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
candles_cur = candles_db.cursor()

pg_cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, 
           open_time, close_time, _signal_metadata
    FROM trades 
    WHERE signal LIKE '%rr_struct%' AND status = 'closed'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()

def compute_rr_accel(token, entry_time):
    try:
        candles_cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1 AND ts <= ?
            ORDER BY ts DESC LIMIT 31
        """, (token.upper(), int(entry_time.timestamp())))
        rows = candles_cur.fetchall()
        if len(rows) < 16:
            return None
        closes = [r[0] for r in reversed(rows)]
        mid = len(closes) // 2
        first_half_delta = closes[mid] - closes[0]
        second_half_delta = closes[-1] - closes[mid]
        return second_half_delta - first_half_delta
    except:
        return None

def compute_metadata_accel(token, entry_time):
    try:
        candles_cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1 AND ts <= ?
            ORDER BY ts DESC LIMIT 31
        """, (token.upper(), int(entry_time.timestamp())))
        rows = candles_cur.fetchall()
        if len(rows) < 16:
            return None
        closes = [r[0] for r in reversed(rows)]
        def avg_vel(window):
            if len(closes) < window + 1:
                return None
            total = 0.0
            for i in range(1, window + 1):
                p_cur = closes[-i]
                p_prev = closes[-(i + 1)]
                if p_prev <= 0:
                    return None
                total += (p_cur - p_prev) / p_prev * 100
            return total / window
        vel_5m = avg_vel(5)
        vel_15m = avg_vel(15)
        if vel_5m is None or vel_15m is None:
            return None
        return (vel_5m - vel_15m) / 10
    except:
        return None

print("=" * 90)
print("COMPARISON: STORED metadata values vs ENTRY-TIME recomputed values")
print("=" * 90)
print(f"{'ID':<6} {'Tok':<8} {'Dir':<6} {'PnL':>7} {'Stored_Accel':>12} {'Entry_Accel':>12} {'Stored_Sign':>12} {'Entry_Sign':>12} {'SAME?'}")
print("-" * 90)

agree_count = 0
disagree_count = 0
sign_disagree = 0

stored_results = []
entry_results = []

for trade in trades:
    tid, token, direction, entry_price, exit_price, pnl, open_time, close_time, metadata = trade
    
    # Get stored accel from metadata
    stored_accel = metadata.get('price_acceleration') if metadata else None
    
    # Compute entry-time accel
    entry_rr_accel = compute_rr_accel(token, open_time)
    entry_meta_accel = compute_metadata_accel(token, open_time)
    
    is_win = float(pnl) > 0
    
    # Determine alignment using STORED values
    if stored_accel is not None:
        if direction == 'SHORT':
            stored_aligned = stored_accel < 0
        else:
            stored_aligned = stored_accel > 0
    else:
        stored_aligned = None
    
    # Determine alignment using ENTRY-TIME values
    if entry_rr_accel is not None:
        if direction == 'SHORT':
            entry_aligned = entry_rr_accel < 0
        else:
            entry_aligned = entry_rr_accel > 0
    else:
        entry_aligned = None
    
    same = "YES" if stored_aligned == entry_aligned else "NO"
    if stored_aligned is not None and entry_aligned is not None:
        if stored_aligned == entry_aligned:
            agree_count += 1
        else:
            disagree_count += 1
            sign_disagree += 1
    
    stored_sign = "+" if stored_accel and stored_accel > 0 else ("-" if stored_accel and stored_accel < 0 else "0")
    entry_sign = "+" if entry_rr_accel and entry_rr_accel > 0 else ("-" if entry_rr_accel and entry_rr_accel < 0 else "0")
    
    stored_results.append({
        'id': tid, 'token': token, 'direction': direction,
        'accel': stored_accel, 'aligned': stored_aligned, 'pnl': float(pnl), 'win': is_win
    })
    entry_results.append({
        'id': tid, 'token': token, 'direction': direction,
        'accel': entry_rr_accel, 'aligned': entry_aligned, 'pnl': float(pnl), 'win': is_win
    })
    
    sa_str = f"{stored_accel:+.6f}" if stored_accel is not None else "N/A"
    ea_str = f"{entry_rr_accel:+.6f}" if entry_rr_accel is not None else "N/A"
    outcome = "WIN" if is_win else "LOSS"
    
    print(f"{tid:<6} {token:<8} {direction:<6} {pnl:>+7.2f} {sa_str:>12} {ea_str:>12} {stored_sign:>12} {entry_sign:>12} {same}  {outcome}")

print(f"\nAgreement on alignment direction: {agree_count} agree, {disagree_count} DISAGREE")

# ── Compute win rates for BOTH classification methods ────────────────────
print("\n" + "=" * 90)
print("WIN RATES BY CLASSIFICATION METHOD")
print("=" * 90)

for label, results in [("STORED metadata (current time)", stored_results), 
                        ("ENTRY-TIME recomputation", entry_results)]:
    aligned_trades = [r for r in results if r['aligned'] is True]
    opposed_trades = [r for r in results if r['aligned'] is False]
    
    al_wins = sum(1 for r in aligned_trades if r['win'])
    op_wins = sum(1 for r in opposed_trades if r['win'])
    
    al_wr = al_wins/len(aligned_trades)*100 if aligned_trades else 0
    op_wr = op_wins/len(opposed_trades)*100 if opposed_trades else 0
    
    print(f"\n{label}:")
    print(f"  ALIGNED: {al_wins}/{len(aligned_trades)} = {al_wr:.1f}% WR")
    print(f"  OPPOSED: {op_wins}/{len(opposed_trades)} = {op_wr:.1f}% WR")
    
    # Fisher's test
    if aligned_trades and opposed_trades:
        table = [[al_wins, len(aligned_trades) - al_wins],
                 [op_wins, len(opposed_trades) - op_wins]]
        odds, p_fisher = stats.fisher_exact(table)
        print(f"  Fisher's p-value: {p_fisher:.4f} {'(SIG)' if p_fisher < 0.05 else '(NOT SIG)'}")

# ── Check if the claim's exact numbers can be reproduced ────────────────
print("\n" + "=" * 90)
print("CAN WE REPRODUCE THE CLAIM'S NUMBERS?")
print("=" * 90)

# The claim says:
# Metadata ALIGNED: 56.2% WR (16 trades)
# Metadata OPPOSED: 80.0% WR (5 trades)
# RR ALIGNED: 50.0% WR (10 trades)
# RR OPPOSED: 72.7% WR (11 trades)

# Let's try using speed_percentile to determine metadata alignment
# speed_percentile > 50 might mean "fast/accelerating" for metadata
# But the claim says metadata accel is from speed_tracker.py's (vel_5m - vel_15m)

# Let me compute the metadata accel direction from token_speeds at entry time
# But token_speeds is updated frequently, so we can't get historical values.
# Instead, let's see what speed_tracker's accel sign would be.

# Actually, "metadata accel" in the claim might refer to the accel stored in signal_compactor's output
# Let me check what fields are in _signal_metadata

print("\nAll _signal_metadata keys across rr-struct trades:")
all_keys = set()
for trade in trades:
    metadata = trade[8]
    if metadata:
        all_keys.update(metadata.keys())
print(sorted(all_keys))

# Check if there's an 'accel' key or similar
for key in sorted(all_keys):
    if 'accel' in key.lower() or 'speed' in key.lower() or 'vel' in key.lower():
        vals = [(trade[0], trade[1], trade[8].get(key)) for trade in trades if trade[8]]
        non_none = [(t, tok, v) for t, tok, v in vals if v is not None]
        print(f"\n{key}: {len(non_none)} non-null values")
        for t, tok, v in non_none[:5]:
            print(f"  {t} {tok}: {v}")

pg.close()
candles_db.close()
