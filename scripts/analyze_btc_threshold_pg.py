#!/usr/bin/env python3
"""Full statistical analysis of BTC momentum thresholds for pump-chain signals.
Uses PostgreSQL (brain DB) for larger sample + candles.db for BTC prices."""

import sqlite3
import subprocess
import json
import math
from datetime import datetime

# ── Get trades from PostgreSQL ──
def get_pg_trades():
    """Fetch pump-chain trades from PostgreSQL via psql."""
    query = """
    SELECT id, token, signal, direction, pnl_usdt, open_time, close_time, 
           amount_usdt, status, entry_price, exit_price, close_reason,
           open_time::bigint as open_ts
    FROM trades 
    WHERE signal IN ('pump-chain+', 'pump-chain-')
      AND status = 'closed'
      AND close_time IS NOT NULL
    ORDER BY open_time DESC;
    """
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-t', '-A', '-F', '|', '-c', query],
        capture_output=True, text=True
    )
    trades = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) >= 13:
            trades.append({
                'id': parts[0],
                'coin': parts[1],
                'signal': parts[2],
                'direction': parts[3],
                'pnl': float(parts[4]) if parts[4] else 0,
                'open_time': parts[5],
                'close_time': parts[6],
                'amount': float(parts[7]) if parts[7] else 0,
                'status': parts[8],
                'entry': float(parts[9]) if parts[9] else 0,
                'exit': float(parts[10]) if parts[10] else 0,
                'close_reason': parts[11],
                'open_ts': int(parts[12]) if parts[12] else 0,
            })
    return trades

print("Fetching pump-chain trades from PostgreSQL...")
trades = get_pg_trades()
print(f"Total pump-chain trades: {len(trades)}")

pc_plus = [t for t in trades if t['signal'] == 'pump-chain+']
pc_minus = [t for t in trades if t['signal'] == 'pump-chain-']
print(f"  pump-chain+: {len(pc_plus)}")
print(f"  pump-chain-: {len(pc_minus)}")

# ── Get BTC candles from SQLite ──
candles_db = "/root/.hermes/data/candles.db"
conn = sqlite3.connect(candles_db)
cursor = conn.cursor()

def get_btc_price_at(ts):
    """Get BTC close price near given unix timestamp."""
    cursor.execute("""
        SELECT close, ts FROM candles_1m 
        WHERE token = 'BTC' AND ts <= ? AND ts > ?
        ORDER BY ts DESC LIMIT 1
    """, (ts + 60, ts - 120))
    return cursor.fetchone()

def get_btc_price_before(ts, minutes):
    """Get BTC close price N minutes before timestamp."""
    target = ts - (minutes * 60)
    cursor.execute("""
        SELECT close, ts FROM candles_1m 
        WHERE token = 'BTC' AND ts <= ? AND ts > ?
        ORDER BY ts DESC LIMIT 1
    """, (target + 60, target - 60))
    return cursor.fetchone()

def calc_momentum(ts, lookback_min):
    """Calculate BTC momentum (%) over lookback window."""
    now = get_btc_price_at(ts)
    before = get_btc_price_before(ts, lookback_min)
    if now and before and before[0] > 0:
        return (now[0] - before[0]) / before[0] * 100
    return None

# ── Enrich all trades with BTC momentum ──
print("\nEnriching trades with BTC 15m momentum...")
for t in trades:
    ts = t['open_ts']
    if ts:
        t['mom_5m'] = calc_momentum(ts, 5)
        t['mom_15m'] = calc_momentum(ts, 15)
        t['mom_30m'] = calc_momentum(ts, 30)
        btc = get_btc_price_at(ts)
        t['btc_price'] = btc[0] if btc else None
    else:
        t['mom_5m'] = t['mom_15m'] = t['mom_30m'] = None
        t['btc_price'] = None

# Filter trades that have momentum data
has_mom = [t for t in trades if t['mom_15m'] is not None]
has_mom_plus = [t for t in pc_plus if t['mom_15m'] is not None]
has_mom_minus = [t for t in pc_minus if t['mom_15m'] is not None]

print(f"Trades with BTC momentum data: {len(has_mom)}/{len(trades)}")
print(f"  pump-chain+: {len(has_mom_plus)}/{len(pc_plus)}")
print(f"  pump-chain-: {len(has_mom_minus)}/{len(pc_minus)}")

# ── Wilson CI helper ──
def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt((p * (1-p) + z**2 / (4*n)) / n) / denom
    return (max(0, center - margin), min(1, center + margin))

# ── Threshold analysis function ──
def analyze_threshold(trades_list, threshold, direction, lookback_key='mom_15m'):
    """Analyze trades at a given threshold.
    For pump-chain+ (LONG): block when BTC momentum > threshold
    For pump-chain- (SHORT): block when BTC momentum < -threshold
    """
    valid = [t for t in trades_list if t[lookback_key] is not None]
    
    if direction == 'positive':
        blocked = [t for t in valid if t[lookback_key] > threshold]
        allowed = [t for t in valid if t[lookback_key] <= threshold]
    else:
        blocked = [t for t in valid if t[lookback_key] < -threshold]
        allowed = [t for t in valid if t[lookback_key] >= -threshold]
    
    result = {
        'total_valid': len(valid),
        'blocked': blocked,
        'allowed': allowed,
        'n_blocked': len(blocked),
        'n_allowed': len(allowed),
    }
    
    if blocked:
        b_wins = sum(1 for t in blocked if t['pnl'] > 0)
        b_losses = sum(1 for t in blocked if t['pnl'] <= 0)
        result['b_wins'] = b_wins
        result['b_losses'] = b_losses
        result['b_wr'] = b_wins / len(blocked) * 100
        result['b_pnl'] = sum(t['pnl'] for t in blocked)
        result['b_saved'] = sum(abs(t['pnl']) for t in blocked if t['pnl'] <= 0)
        result['b_ci'] = wilson_ci(b_wins, len(blocked))
    
    if allowed:
        a_wins = sum(1 for t in allowed if t['pnl'] > 0)
        a_losses = sum(1 for t in allowed if t['pnl'] <= 0)
        result['a_wins'] = a_wins
        result['a_losses'] = a_losses
        result['a_wr'] = a_wins / len(allowed) * 100
        result['a_pnl'] = sum(t['pnl'] for t in allowed)
        result['a_ci'] = wilson_ci(a_wins, len(allowed))
    
    return result

# ═══════════════════════════════════════════════════════════════
# MAIN ANALYSIS: 15m lookback, 0.3% threshold
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("FULL ANALYSIS: PostgreSQL + BTC Momentum (15m lookback)")
print("=" * 80)

threshold = 0.3
lookback = 'mom_15m'

# ── pump-chain+ ──
print(f"\n{'─' * 80}")
print(f"PUMP-CHAIN+ (LONG) — Block when BTC 15m momentum > +{threshold}%")
print(f"{'─' * 80}")

# Baseline
plus_wins = sum(1 for t in has_mom_plus if t['pnl'] > 0)
plus_total = len(has_mom_plus)
plus_ci = wilson_ci(plus_wins, plus_total)
print(f"\nBaseline: {plus_wins}/{plus_total} = {plus_wins/plus_total*100:.1f}% WR")
print(f"  95% CI: [{plus_ci[0]*100:.1f}%, {plus_ci[1]*100:.1f}%]")
print(f"  Total PnL: ${sum(t['pnl'] for t in has_mom_plus):+.2f}")

r_plus = analyze_threshold(has_mom_plus, threshold, 'positive')
print(f"\nAt threshold +{threshold}%:")
print(f"  Valid trades: {r_plus['total_valid']}")
print(f"  BLOCKED: {r_plus['n_blocked']} trades")
if r_plus['n_blocked'] > 0:
    print(f"    Wins: {r_plus['b_wins']}, Losses: {r_plus['b_losses']}")
    print(f"    Win Rate: {r_plus['b_wr']:.1f}% (plan claims 30% = 70% lose)")
    print(f"    95% CI for WR: [{r_plus['b_ci'][0]*100:.1f}%, {r_plus['b_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${r_plus['b_pnl']:+.2f}")
    print(f"    Money saved: ${r_plus['b_saved']:.2f}")
    for t in r_plus['blocked']:
        print(f"      {t['coin']}: mom={t[lookback]:+.3f}%, pnl=${t['pnl']:+.2f}, reason={t.get('close_reason','?')}")
else:
    print(f"    (no trades blocked)")

print(f"\n  ALLOWED: {r_plus['n_allowed']} trades")
if r_plus['n_allowed'] > 0:
    print(f"    Wins: {r_plus['a_wins']}, Losses: {r_plus['a_losses']}")
    print(f"    Win Rate: {r_plus['a_wr']:.1f}%")
    print(f"    95% CI for WR: [{r_plus['a_ci'][0]*100:.1f}%, {r_plus['a_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${r_plus['a_pnl']:+.2f}")

# ── pump-chain- ──
print(f"\n{'─' * 80}")
print(f"PUMP-CHAIN- (SHORT) — Block when BTC 15m momentum < -{threshold}%")
print(f"{'─' * 80}")

minus_wins = sum(1 for t in has_mom_minus if t['pnl'] > 0)
minus_total = len(has_mom_minus)
minus_ci = wilson_ci(minus_wins, minus_total)
print(f"\nBaseline: {minus_wins}/{minus_total} = {minus_wins/minus_total*100:.1f}% WR")
print(f"  95% CI: [{minus_ci[0]*100:.1f}%, {minus_ci[1]*100:.1f}%]")
print(f"  Total PnL: ${sum(t['pnl'] for t in has_mom_minus):+.2f}")

r_minus = analyze_threshold(has_mom_minus, threshold, 'negative')
print(f"\nAt threshold -{threshold}%:")
print(f"  Valid trades: {r_minus['total_valid']}")
print(f"  BLOCKED: {r_minus['n_blocked']} trades")
if r_minus['n_blocked'] > 0:
    print(f"    Wins: {r_minus['b_wins']}, Losses: {r_minus['b_losses']}")
    print(f"    Loss Rate: {(r_minus['b_losses']/r_minus['n_blocked']*100):.0f}% (plan claims 60%)")
    print(f"    95% CI for WR: [{r_minus['b_ci'][0]*100:.1f}%, {r_minus['b_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${r_minus['b_pnl']:+.2f}")
    print(f"    Money saved: ${r_minus['b_saved']:.2f}")
    for t in r_minus['blocked']:
        print(f"      {t['coin']}: mom={t[lookback]:+.3f}%, pnl=${t['pnl']:+.2f}, reason={t.get('close_reason','?')}")
else:
    print(f"    (no trades blocked)")

print(f"\n  ALLOWED: {r_minus['n_allowed']} trades")
if r_minus['n_allowed'] > 0:
    print(f"    Wins: {r_minus['a_wins']}, Losses: {r_minus['a_losses']}")
    print(f"    Win Rate: {r_minus['a_wr']:.1f}%")
    print(f"    95% CI for WR: [{r_minus['a_ci'][0]*100:.1f}%, {r_minus['a_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${r_minus['a_pnl']:+.2f}")

# ═══════════════════════════════════════════════════════════════
# CLAIM VERIFICATION
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("CLAIM VERIFICATION")
print("=" * 80)

claims = [
    ("pump-chain+ loses 70% when BTC > +0.3%", 
     r_plus['n_blocked'] > 0 and r_plus['b_losses']/r_plus['n_blocked'] >= 0.7 if r_plus['n_blocked'] > 0 else False),
    ("pump-chain- loses 60% when BTC < -0.3%", 
     r_minus['n_blocked'] > 0 and r_minus['b_losses']/r_minus['n_blocked'] >= 0.6 if r_minus['n_blocked'] > 0 else False),
]

for claim, verified in claims:
    status = "✅ VERIFIED" if verified else "❌ NOT VERIFIED"
    print(f"\n  {status}: {claim}")
    if 'pump-chain+' in claim and r_plus['n_blocked'] > 0:
        print(f"    Actual: {r_plus['b_losses']}/{r_plus['n_blocked']} = {r_plus['b_losses']/r_plus['n_blocked']*100:.0f}% lose")
        print(f"    95% CI: [{r_plus['b_ci'][0]*100:.1f}%, {r_plus['b_ci'][1]*100:.1f}%] win rate")
    elif 'pump-chain-' in claim and r_minus['n_blocked'] > 0:
        print(f"    Actual: {r_minus['b_losses']}/{r_minus['n_blocked']} = {r_minus['b_losses']/r_minus['n_blocked']*100:.0f}% lose")
        print(f"    95% CI: [{r_minus['b_ci'][0]*100:.1f}%, {r_minus['b_ci'][1]*100:.1f}%] win rate")

# Claim about blocking 12/50 trades - check on last 50
print(f"\n  Claim: 'block 12/50 trades, 8 are losers, net +$28.90 saved'")
# We can only check this on the last 50 from trades.json, not PG
# But we can compute what our thresholds would block in the full PG dataset
total_blocked = r_plus['n_blocked'] + r_minus['n_blocked']
total_losers = r_plus.get('b_losses', 0) + r_minus.get('b_losses', 0)
total_saved = r_plus.get('b_saved', 0) + r_minus.get('b_saved', 0)
print(f"  Actual (full PG dataset): block {total_blocked}/{len(has_mom)} pump-chain trades")
print(f"    {total_losers} losers blocked, ${total_saved:.2f} saved")

# ═══════════════════════════════════════════════════════════════
# OPTIMAL THRESHOLD SEARCH
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("OPTIMAL THRESHOLD SEARCH (15m lookback)")
print("=" * 80)

thresholds = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8, 1.0]
print(f"\n{'Thresh':>7} | {'++N':>4} {'++Blok':>5} {'++W':>3} {'++L':>3} {'++WR%':>5} {'++Save$':>7} | {'--N':>4} {'--Blok':>5} {'--W':>3} {'--L':>3} {'--LR%':>5} {'--Save$':>7} | {'NetSav$':>8}")
print("-" * 110)

best_score = -999
best_t = 0

for t in thresholds:
    rp = analyze_threshold(has_mom_plus, t, 'positive')
    rm = analyze_threshold(has_mom_minus, t, 'negative')
    
    n_b = rp['n_blocked'] + rm['n_blocked']
    s_plus = rp.get('b_saved', 0)
    s_minus = rm.get('b_saved', 0)
    net_saved = s_plus + s_minus
    
    l_plus = rp.get('b_losses', 0)
    l_minus = rm.get('b_losses', 0)
    w_plus = rp.get('b_wins', 0)
    w_minus = rm.get('b_wins', 0)
    
    wr_plus = f"{rp['b_wr']:.0f}" if rp['n_blocked'] > 0 else "N/A"
    wr_minus = f"{(l_minus/(l_minus+w_plus)*100 if (l_minus+w_plus)>0 else 0):.0f}" if rm['n_blocked'] > 0 else "N/A"
    
    # Score: net benefit
    score = net_saved
    
    print(f"{t:>7.2f} | {rp['total_valid']:>4} {rp['n_blocked']:>5} {w_plus:>3} {l_plus:>3} {wr_plus:>5}% ${s_plus:>+6.2f} | {rm['total_valid']:>4} {rm['n_blocked']:>5} {w_minus:>3} {l_minus:>3} {wr_minus:>5}% ${s_minus:>+6.2f} | ${net_saved:>+7.2f}")
    
    if score > best_score:
        best_score = score
        best_t = t

print(f"\nBest threshold by net savings: ±{best_t}%")

# ═══════════════════════════════════════════════════════════════
# SAMPLE SIZE ASSESSMENT
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("SAMPLE SIZE ASSESSMENT")
print("=" * 80)

# Power analysis: minimum sample to detect 20% difference at 80% power
# Using rule of thumb: n ≈ 16 / (effect_size)^2 for 80% power
# For detecting 70% vs 30% (effect = 0.4), need n ≈ 100

r_blocked_plus = analyze_threshold(has_mom_plus, 0.3, 'positive')
r_blocked_minus = analyze_threshold(has_mom_minus, 0.3, 'negative')

n_blocked_plus = r_blocked_plus['n_blocked']
n_blocked_minus = r_blocked_minus['n_blocked']

print(f"\nAt ±0.3% threshold:")
print(f"  pump-chain+ blocked: {n_blocked_plus}")
print(f"  pump-chain- blocked: {n_blocked_minus}")

# Minimum for meaningful result
print(f"\n  Minimum sample for 80% power to detect 30% win rate difference:")
print(f"    Rule of thumb: n ≈ 100 trades needed")
print(f"    pump-chain+ has {len(pc_plus)} total trades, ~{n_blocked_plus} at threshold")
print(f"    pump-chain- has {len(pc_minus)} total trades, ~{n_blocked_minus} at threshold")
print(f"\n  ⚠️  SAMPLE SIZE IS TOO SMALL for reliable conclusions")

# ═══════════════════════════════════════════════════════════════
# LOOKBACK WINDOW COMPARISON
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("LOOKBACK WINDOW COMPARISON (at ±0.3% threshold)")
print("=" * 80)

for lb_name, lb_key in [('5m', 'mom_5m'), ('15m', 'mom_15m'), ('30m', 'mom_30m')]:
    valid_plus_lb = [t for t in pc_plus if t[lb_key] is not None]
    valid_minus_lb = [t for t in pc_minus if t[lb_key] is not None]
    
    rp = analyze_threshold(valid_plus_lb, 0.3, 'positive', lb_key)
    rm = analyze_threshold(valid_minus_lb, 0.3, 'negative', lb_key)
    
    print(f"\n  {lb_name} lookback:")
    print(f"    pump-chain+: {rp['n_blocked']}/{rp['total_valid']} blocked", end="")
    if rp['n_blocked'] > 0:
        print(f" (WR={rp['b_wr']:.0f}%, saved=${rp['b_saved']:.2f})", end="")
    print()
    print(f"    pump-chain-: {rm['n_blocked']}/{rm['total_valid']} blocked", end="")
    if rm['n_blocked'] > 0:
        lr = rm['b_losses']/rm['n_blocked']*100 if rm['n_blocked'] > 0 else 0
        print(f" (LR={lr:.0f}%, saved=${rm['b_saved']:.2f})", end="")
    print()

conn.close()
