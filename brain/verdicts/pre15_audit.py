#!/usr/bin/env python3
"""Independent audit of pre15_move filter claims for accel_300_short trades."""

import json
import os
from datetime import datetime, timedelta

# ── Load data ──────────────────────────────────────────────────────────────────
DATA_DIR = '/root/.hermes/data'

with open(f'{DATA_DIR}/accel300_short_all_trades.json') as f:
    all_trades = json.load(f)

with open(f'{DATA_DIR}/accel300_short_detailed.json') as f:
    detailed_trades = json.load(f)

print(f"All trades: {len(all_trades)}")
print(f"Detailed trades (with candle data): {len(detailed_trades)}")
print()

# ── Understand what types are in the detailed data ─────────────────────────────
types = {}
for t in detailed_trades:
    tp = t['type']
    types[tp] = types.get(tp, 0) + 1

print("=== Trade types in detailed data ===")
for tp, count in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {tp}: {count}")
print()

# ── Check which types have v3_short ────────────────────────────────────────────
v3_short_trades = [t for t in detailed_trades if 'v3-short' in t['type']]
print(f"V3 SHORT trades in detailed: {len(v3_short_trades)}")
for t in v3_short_trades:
    print(f"  {t['token']} {t['type']} win={t['win']} pnl={t['pnl']:.4f} pre15={t['pre15_move']:.2f}%")
print()

# ── CRITICAL: Analyze ALL types (not just v3-short) ────────────────────────────
# The claims reference 139 trades - let's see what data we have
print("=== CRITICAL ANALYSIS: All detailed trades by win/loss and pre15_move ===")

# Separate wins and losses
wins = [t for t in detailed_trades if t['win'] == 1]
losses = [t for t in detailed_trades if t['win'] == 0]

print(f"Total detailed: {len(detailed_trades)}")
print(f"Wins: {len(wins)}")
print(f"Losses: {len(losses)}")
print()

# ── Analyze pre15_move for wins vs losses ──────────────────────────────────────
print("=== Claim 1: '95% of LOSERS had price RISING 15 minutes before entry' ===")
print()

# pre15_move > 0 means price was rising before entry
rising_before_entry_losses = [t for t in losses if t.get('pre15_move', 0) > 0]
falling_before_entry_losses = [t for t in losses if t.get('pre15_move', 0) <= 0]
falling_before_entry_wins = [t for t in wins if t.get('pre15_move', 0) < 0]
rising_before_entry_wins = [t for t in wins if t.get('pre15_move', 0) >= 0]

print(f"Losses with pre15_move > 0 (price RISING): {len(rising_before_entry_losses)}/{len(losses)} = {len(rising_before_entry_losses)/len(losses)*100:.1f}%")
print(f"Losses with pre15_move <= 0 (price FALLING): {len(falling_before_entry_losses)}/{len(losses)} = {len(falling_before_entry_losses)/len(losses)*100:.1f}%")
print()
print(f"Wins with pre15_move < 0 (price FALLING): {len(falling_before_entry_wins)}/{len(wins)} = {len(falling_before_entry_wins)/len(wins)*100:.1f}%")
print(f"Wins with pre15_move >= 0 (price RISING): {len(rising_before_entry_wins)}/{len(wins)} = {len(rising_before_entry_wins)/len(wins)*100:.1f}%")
print()

# ── Test filter: pre15_move > 0 blocks losses ──────────────────────────────────
print("=== Claim 2: 'Filter pre15_move > 0 gives 46W/3L = 94% WR' ===")
# pre15_move > 0 means price was rising before entry (bad for SHORT)
# If we BLOCK all trades where pre15_move > 0, what remains?
blocked_by_filter = [t for t in detailed_trades if t.get('pre15_move', 0) > 0]
remaining_trades = [t for t in detailed_trades if t.get('pre15_move', 0) <= 0]

remaining_wins = [t for t in remaining_trades if t['win'] == 1]
remaining_losses = [t for t in remaining_trades if t['win'] == 0]

print(f"Blocked by pre15_move > 0: {len(blocked_by_filter)} trades")
print(f"Remaining trades: {len(remaining_trades)}")
print(f"  Remaining wins: {len(remaining_wins)}")
print(f"  Remaining losses: {len(remaining_losses)}")
if len(remaining_trades) > 0:
    print(f"  WR: {len(remaining_wins)/len(remaining_trades)*100:.1f}%")
else:
    print("  WR: N/A (no trades)")
print()

# ── Test filter: pre15_move > -0.5% blocks losses ──────────────────────────────
print("=== Claim 3: 'Filter pre15_move > -0.5% gives 20W/0L = 100% WR' ===")
blocked_by_filter_2 = [t for t in detailed_trades if t.get('pre15_move', 0) > -0.5]
remaining_trades_2 = [t for t in detailed_trades if t.get('pre15_move', 0) <= -0.5]

remaining_wins_2 = [t for t in remaining_trades_2 if t['win'] == 1]
remaining_losses_2 = [t for t in remaining_trades_2 if t['win'] == 0]

print(f"Blocked by pre15_move > -0.5%: {len(blocked_by_filter_2)} trades")
print(f"Remaining trades: {len(remaining_trades_2)}")
print(f"  Remaining wins: {len(remaining_wins_2)}")
print(f"  Remaining losses: {len(remaining_losses_2)}")
if len(remaining_trades_2) > 0:
    print(f"  WR: {len(remaining_wins_2)/len(remaining_trades_2)*100:.1f}%")
else:
    print("  WR: N/A (no trades)")
print()

# ── Show which losses the filter catches and misses ────────────────────────────
print("=== Losses that would be CAUGHT by pre15_move > 0 filter (not traded) ===")
for t in sorted(rising_before_entry_losses, key=lambda x: x['pre15_move'], reverse=True):
    print(f"  {t['token']:8s} pre15={t['pre15_move']:+.2f}% pnl={t['pnl']:+.4f} type={t['type']}")

print()
print("=== Losses that would be MISSED by pre15_move > 0 filter (still traded and lost) ===")
for t in sorted(falling_before_entry_losses, key=lambda x: x['pre15_move']):
    print(f"  {t['token']:8s} pre15={t['pre15_move']:+.2f}% pnl={t['pnl']:+.4f} type={t['type']}")
print()

# ── Check: the pre15_move > 0 filter blocks wins too ───────────────────────────
print("=== Wins that would be BLOCKED by pre15_move > 0 filter (missed profits) ===")
for t in sorted(rising_before_entry_wins, key=lambda x: x['pnl'], reverse=True)[:10]:
    print(f"  {t['token']:8s} pre15={t['pre15_move']:+.2f}% pnl={t['pnl']:+.4f} type={t['type']}")
print(f"  ... ({len(rising_before_entry_wins)} total wins blocked)")
print()

# ── Verify pre15_move calculation ──────────────────────────────────────────────
print("=== DATA QUALITY CHECKS ===")
print()

# Check for suspicious patterns
print("--- pre15_move = 0.0 (possible data issue) ---")
zero_pre15 = [t for t in detailed_trades if t.get('pre15_move') == 0.0]
for t in zero_pre15:
    print(f"  {t['token']:8s} pre15={t['pre15_move']} pre5={t.get('pre5_move', 'N/A')} type={t['type']} date={t['date']}")
print(f"  Total: {len(zero_pre15)} trades with pre15_move = exactly 0.0")
print()

print("--- pre5_move = pre15_move (possible data issue) ---")
same_pre5_pre15 = [t for t in detailed_trades if t.get('pre5_move') == t.get('pre15_move')]
for t in same_pre5_pre15:
    print(f"  {t['token']:8s} pre5={t.get('pre5_move', 0):.4f} pre15={t.get('pre15_move', 0):.4f} type={t['type']}")
print(f"  Total: {len(same_pre5_pre15)} trades")
print()

print("--- vol_ratio = 0 (possible data issue) ---")
zero_vol = [t for t in detailed_trades if t.get('vol_ratio') == 0]
for t in zero_vol:
    print(f"  {t['token']:8s} vol_ratio={t['vol_ratio']} type={t['type']} date={t['date']}")
print(f"  Total: {len(zero_vol)} trades")
print()

print("--- trade_move = 0 (possible data issue) ---")
zero_trade = [t for t in detailed_trades if t.get('trade_move') == 0]
for t in zero_trade:
    print(f"  {t['token']:8s} trade_move={t['trade_move']} pnl={t['pnl']:.4f} win={t['win']} type={t['type']}")
print(f"  Total: {len(zero_trade)} trades")
print()

# ── Check pre15_move range consistency ─────────────────────────────────────────
print("--- pre15_move range analysis ---")
pre15_values = [t.get('pre15_move', 0) for t in detailed_trades]
print(f"  Min: {min(pre15_values):.4f}%")
print(f"  Max: {max(pre15_values):.4f}%")
print(f"  Mean: {sum(pre15_values)/len(pre15_values):.4f}%")
print(f"  Trades > 1%: {len([v for v in pre15_values if v > 1])}")
print(f"  Trades < -1%: {len([v for v in pre15_values if v < -1])}")
print(f"  Trades > 2%: {len([v for v in pre15_values if v > 2])}")
print(f"  Trades < -2%: {len([v for v in pre15_values if v < -2])}")
print()

# ── CRITICAL: Check if the claims are about ALL trades or just v3_short ────────
print("=== CRITICAL: What trade types are included in these claims? ===")
print("The detailed JSON has these types:")
for t in detailed_trades:
    if 'v3-short' in t['type']:
        print(f"  V3-SHORT: {t['token']} {t['type']}")
print()

# ── Re-run analysis for ONLY v3-short trades ───────────────────────────────────
print("=== Analysis for V3-SHORT trades ONLY ===")
v3_short = [t for t in detailed_trades if 'v3-short' in t['type']]
v3_wins = [t for t in v3_short if t['win'] == 1]
v3_losses = [t for t in v3_short if t['win'] == 0]
print(f"V3-SHORT trades: {len(v3_short)}")
print(f"  Wins: {len(v3_wins)}")
print(f"  Losses: {len(v3_losses)}")
print()

for t in v3_short:
    pre15 = t.get('pre15_move', 0)
    status = "BLOCKED" if pre15 > 0 else "PASSES"
    result = "WIN" if t['win'] == 1 else "LOSS"
    print(f"  {t['token']:8s} pre15={pre15:+.2f}% {status} → {result} pnl={t['pnl']:+.4f}")
print()

# ── Run filters on v3-short only ──────────────────────────────────────────────
print("=== Filter on V3-SHORT only: pre15_move > 0 ===")
v3_blocked = [t for t in v3_short if t.get('pre15_move', 0) > 0]
v3_remaining = [t for t in v3_short if t.get('pre15_move', 0) <= 0]
v3_rem_w = len([t for t in v3_remaining if t['win'] == 1])
v3_rem_l = len([t for t in v3_remaining if t['win'] == 0])
print(f"  Blocked: {len(v3_blocked)}")
print(f"  Remaining: {len(v3_remaining)} ({v3_rem_w}W/{v3_rem_l}L)")
if v3_remaining:
    print(f"  WR: {v3_rem_w/len(v3_remaining)*100:.1f}%")
print()

print("=== Filter on V3-SHORT only: pre15_move > -0.5% ===")
v3_blocked2 = [t for t in v3_short if t.get('pre15_move', 0) > -0.5]
v3_remaining2 = [t for t in v3_short if t.get('pre15_move', 0) <= -0.5]
v3_rem_w2 = len([t for t in v3_remaining2 if t['win'] == 1])
v3_rem_l2 = len([t for t in v3_remaining2 if t['win'] == 0])
print(f"  Blocked: {len(v3_blocked2)}")
print(f"  Remaining: {len(v3_remaining2)} ({v3_rem_w2}W/{v3_rem_l2}L)")
if v3_remaining2:
    print(f"  WR: {v3_rem_w2/len(v3_remaining2)*100:.1f}%")
print()

# ── Breakdown by type for the full analysis ────────────────────────────────────
print("=== Win rate by pre15_move bucket (all detailed trades) ===")
buckets = [
    ("pre15 > 1%", lambda x: x > 1),
    ("pre15 0.5% to 1%", lambda x: 0.5 < x <= 1),
    ("pre15 0% to 0.5%", lambda x: 0 < x <= 0.5),
    ("pre15 -0.5% to 0%", lambda x: -0.5 < x <= 0),
    ("pre15 -1% to -0.5%", lambda x: -1 < x <= -0.5),
    ("pre15 < -1%", lambda x: x <= -1),
]

for name, cond in buckets:
    bucket = [t for t in detailed_trades if cond(t.get('pre15_move', 0))]
    w = len([t for t in bucket if t['win'] == 1])
    l = len([t for t in bucket if t['win'] == 0])
    total = w + l
    wr = w/total*100 if total > 0 else 0
    print(f"  {name:20s}: {total:3d} trades ({w:2d}W/{l:2d}L) WR={wr:.1f}%")
print()

# ── Check: Is the pre15_move calculation even accurate? ────────────────────────
print("=== pre15_move CALCULATION ACCURACY CHECK ===")
print("pre15_move = % change from price 15 candles ago to entry price")
print("Formula: (entry_price - price_15min_ago) / price_15min_ago * 100")
print()
print("NOTE: These are 1m candles. 15 candles = 15 minutes.")
print("The calculation looks at the CLOSE of the candle 15 minutes before entry.")
print()
print("DATA ISSUES FOUND:")
for t in detailed_trades:
    pre15 = t.get('pre15_move', 0)
    pre5 = t.get('pre5_move', 0)
    # Check if pre15 is suspiciously small
    if abs(pre15) < 0.001 and abs(pre5) > 0.1:
        print(f"  WARNING: {t['token']} pre15={pre15:.6f}% but pre5={pre5:.4f}% - suspicious ratio")
    # Check if pre15 and pre5 have same sign but very different magnitudes
    if pre5 > 0 and pre15 < 0 and abs(pre15) > abs(pre5) * 3:
        print(f"  NOTE: {t['token']} pre5={pre5:.4f}% (rising) but pre15={pre15:.4f}% (falling) - possible data issue")
