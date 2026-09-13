#!/usr/bin/env python3
"""FINAL AUDIT: Verify accel claim with CORRECT lookback (10 candles) matching rr_structural.py exactly."""
import psycopg2
import sqlite3
import json
from scipy import stats

pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
pg_cur = pg.cursor()
candles_db = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
candles_cur = candles_db.cursor()

LOOKBACK = 10  # RR_STRUCTURAL_ACCEL_LOOKBACK

pg_cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, 
           open_time, close_time, _signal_metadata
    FROM trades 
    WHERE signal LIKE '%rr_struct%' AND status = 'closed'
    ORDER BY open_time
""")
trades = pg_cur.fetchall()

def compute_rr_accel_correct(token, entry_time):
    """EXACT replica of _compute_price_acceleration with lookback=10."""
    try:
        candles_cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? AND is_closed = 1 AND ts <= ?
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), int(entry_time.timestamp()), LOOKBACK + 1))
        rows = candles_cur.fetchall()
        if len(rows) < LOOKBACK + 1:
            return None
        closes = [r[0] for r in reversed(rows)]
        mid = len(closes) // 2
        first_half_delta = closes[mid] - closes[0]
        second_half_delta = closes[-1] - closes[mid]
        return second_half_delta - first_half_delta
    except Exception as e:
        return None

def compute_metadata_accel(token, entry_time):
    """EXACT replica of speed_tracker.py accel computation."""
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

# ── Build full analysis table ─────────────────────────────────────────────
print("=" * 110)
print("CORRECT AUDIT: rr_structural.py accel (lookback=10) vs speed_tracker.py accel")
print("=" * 110)
print(f"{'ID':<6} {'Tok':<8} {'Dir':<6} {'PnL':>7} {'RR_Accel':>10} {'Meta_Accel':>10} {'RR_Al':>8} {'Meta_Al':>8} {'Stored_Accel':>12} {'Stored_Al':>9} {'Result'}")
print("-" * 110)

stored_rr = []  # using stored price_acceleration
entry_rr = []   # using recomputed at entry time
meta_entry = [] # using speed_tracker recomputed at entry time

sign_changes = 0
for trade in trades:
    tid, token, direction, entry_price, exit_price, pnl, open_time, close_time, metadata = trade
    
    stored_accel = metadata.get('price_acceleration') if metadata else None
    entry_rr_accel = compute_rr_accel_correct(token, open_time)
    meta_accel = compute_metadata_accel(token, open_time)
    
    is_win = float(pnl) > 0
    
    def is_aligned(direction, accel):
        if accel is None:
            return None
        if direction == 'SHORT':
            return accel < 0
        else:
            return accel > 0
    
    rr_al = is_aligned(direction, entry_rr_accel)
    meta_al = is_aligned(direction, meta_accel)
    stored_al = is_aligned(direction, stored_accel)
    
    if stored_al is not None and rr_al is not None and stored_al != rr_al:
        sign_changes += 1
    
    stored_rr.append({'id': tid, 'token': token, 'direction': direction, 'accel': stored_accel, 'aligned': stored_al, 'pnl': float(pnl), 'win': is_win})
    entry_rr.append({'id': tid, 'token': token, 'direction': direction, 'accel': entry_rr_accel, 'aligned': rr_al, 'pnl': float(pnl), 'win': is_win})
    meta_entry.append({'id': tid, 'token': token, 'direction': direction, 'accel': meta_accel, 'aligned': meta_al, 'pnl': float(pnl), 'win': is_win})
    
    sa_str = f"{stored_accel:+.6f}" if stored_accel is not None else "N/A"
    ra_str = f"{entry_rr_accel:+.6f}" if entry_rr_accel is not None else "N/A"
    ma_str = f"{meta_accel:+.6f}" if meta_accel is not None else "N/A"
    ra_al = "ALIGNED" if rr_al else ("OPPOSED" if rr_al is False else "N/A")
    ma_al = "ALIGNED" if meta_al else ("OPPOSED" if meta_al is False else "N/A")
    sa_al = "ALIGNED" if stored_al else ("OPPOSED" if stored_al is False else "N/A")
    outcome = "WIN" if is_win else "LOSS"
    
    print(f"{tid:<6} {token:<8} {direction:<6} {pnl:>+7.2f} {ra_str:>10} {ma_str:>10} {ra_al:>8} {ma_al:>8} {sa_str:>12} {sa_al:>9} {outcome}")

print(f"\nSign disagreements between stored and entry-time RR accel: {sign_changes}/21")

# ── Full win rate comparison ──────────────────────────────────────────────
print("\n" + "=" * 110)
print("COMPREHENSIVE WIN RATE COMPARISON")
print("=" * 110)

for label, results in [
    ("A) STORED price_acceleration (current time — WHAT THE CLAIM USED)", stored_rr),
    ("B) ENTRY-TIME rr_structural accel (lookback=10 — WHAT THE FILTER ACTUALLY USED)", entry_rr),
    ("C) ENTRY-TIME speed_tracker accel (what the metadata accel would have been at detection)", meta_entry),
]:
    aligned = [r for r in results if r['aligned'] is True]
    opposed = [r for r in results if r['aligned'] is False]
    neutral = [r for r in results if r['aligned'] is None]
    
    al_w = sum(1 for r in aligned if r['win'])
    op_w = sum(1 for r in opposed if r['win'])
    
    print(f"\n{label}")
    if aligned:
        print(f"  ALIGNED: {al_w}/{len(aligned)} = {al_w/len(aligned)*100:.1f}% WR")
    if opposed:
        print(f"  OPPOSED: {op_w}/{len(opposed)} = {op_w/len(opposed)*100:.1f}% WR")
    if neutral:
        print(f"  NEUTRAL (accel=0): {len(neutral)} trades")
    
    # Fisher's test
    if aligned and opposed:
        table = [[al_w, len(aligned) - al_w],
                 [op_w, len(opposed) - op_w]]
        odds, p_fisher = stats.fisher_exact(table)
        print(f"  Fisher's exact test: p={p_fisher:.4f} {'✓ SIG' if p_fisher < 0.05 else '✗ NOT SIG'} (α=0.05)")

# ── What would happen if we REVERSED the filter? ─────────────────────────
print("\n" + "=" * 110)
print("COUNTERFACTUAL: What if we REVERSED the filter?")
print("  Original: BLOCK when accel opposes direction")
print("  Reversed: BLOCK when accel ALIGNS with direction (keep only opposed)")
print("=" * 110)

# Using ENTRY-TIME values (what the filter actually sees)
aligned = [r for r in entry_rr if r['aligned'] is True]
opposed = [r for r in entry_rr if r['aligned'] is False]

al_pnl = sum(r['pnl'] for r in aligned)
op_pnl = sum(r['pnl'] for r in opposed)

print(f"\nOriginal filter (keep aligned only):")
print(f"  Trades kept: {len(aligned)}  Wins: {sum(1 for r in aligned if r['win'])}/{len(aligned)} = {sum(1 for r in aligned if r['win'])/len(aligned)*100:.1f}% WR")
print(f"  Total PnL: ${al_pnl:+.2f}")

print(f"\nReversed filter (keep opposed only):")
print(f"  Trades kept: {len(opposed)}  Wins: {sum(1 for r in opposed if r['win'])}/{len(opposed)} = {sum(1 for r in opposed if r['win'])/len(opposed)*100:.1f}% WR")
print(f"  Total PnL: ${op_pnl:+.2f}")

print(f"\nNo filter at all:")
all_trades = entry_rr
print(f"  Trades kept: {len(all_trades)}  Wins: {sum(1 for r in all_trades if r['win'])}/{len(all_trades)} = {sum(1 for r in all_trades if r['win'])/len(all_trades)*100:.1f}% WR")
print(f"  Total PnL: ${sum(r['pnl'] for r in all_trades):+.2f}")

# ── Extended: ALL SHORT trades with correct lookback ─────────────────────
print("\n" + "=" * 110)
print("EXTENDED: ALL SHORT trades (correct lookback=10)")
print("=" * 110)

pg_cur.execute("""
    SELECT id, token, direction, signal, entry_price, exit_price, pnl_usdt, 
           open_time, close_time
    FROM trades 
    WHERE direction = 'SHORT' AND status = 'closed'
    ORDER BY open_time
""")
all_shorts = pg_cur.fetchall()
print(f"Total SHORT closed trades: {len(all_shorts)}")

short_aligned = []
short_opposed = []
short_none = 0

for trade in all_shorts:
    tid, token, direction, signal, entry_price, exit_price, pnl, open_time, close_time = trade
    accel = compute_rr_accel_correct(token, open_time)
    if accel is None:
        short_none += 1
        continue
    
    is_win = float(pnl) > 0
    entry = {'id': tid, 'token': token, 'pnl': float(pnl), 'win': is_win, 'accel': accel, 'signal': signal}
    
    if accel < 0:  # Aligned with SHORT
        short_aligned.append(entry)
    else:  # Opposed to SHORT
        short_opposed.append(entry)

sa_w = sum(1 for r in short_aligned if r['win'])
so_w = sum(1 for r in short_opposed if r['win'])

print(f"\nRR ACCEL for ALL SHORT trades:")
if short_aligned:
    print(f"  ALIGNED (accel < 0): {sa_w}/{len(short_aligned)} = {sa_w/len(short_aligned)*100:.1f}% WR")
if short_opposed:
    print(f"  OPPOSED (accel > 0): {so_w}/{len(short_opposed)} = {so_w/len(short_opposed)*100:.1f}% WR")
print(f"  No accel data: {short_none}")

# Fisher's test on ALL SHORT
if short_aligned and short_opposed:
    table = [[sa_w, len(short_aligned) - sa_w],
             [so_w, len(short_opposed) - so_w]]
    odds, p_fisher = stats.fisher_exact(table)
    print(f"  Fisher's exact test: p={p_fisher:.4f} {'✓ SIG' if p_fisher < 0.05 else '✗ NOT SIG'} (α=0.05)")

# Breakdown by signal type
print(f"\n  By signal type:")
for sig in sorted(set(r['signal'] for r in short_aligned + short_opposed)):
    sig_aligned = [r for r in short_aligned if r['signal'] == sig]
    sig_opposed = [r for r in short_opposed if r['signal'] == sig]
    if sig_aligned:
        sa = sum(1 for r in sig_aligned if r['win'])
        print(f"    {sig}: ALIGNED {sa}/{len(sig_aligned)} = {sa/len(sig_aligned)*100:.1f}%", end="")
    if sig_opposed:
        so = sum(1 for r in sig_opposed if r['win'])
        print(f"  OPPOSED {so}/{len(sig_opposed)} = {so/len(sig_opposed)*100:.1f}%", end="")
    print()

pg.close()
candles_db.close()
