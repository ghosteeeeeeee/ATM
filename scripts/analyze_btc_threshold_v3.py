#!/usr/bin/env python3
"""Analyze BTC momentum thresholds for pump-chain+ and pump-chain- signals.
    
The plan's claim: BTC momentum (recent % change) at trade open time predicts
whether pump-chain trades will lose. We need to:
1. For each trade, get BTC price at trade open time
2. Get BTC price N minutes before trade open to compute momentum
3. Classify trades by momentum regime
4. Calculate win rates per regime
"""

import json
import sqlite3
from datetime import datetime, timedelta
import math

# ── Load trades ──
trades_file = "/var/www/hermes/data/trades.json"
with open(trades_file, 'r') as f:
    data = json.load(f)

closed = data.get('closed', [])[:50]

print(f"Total closed trades in DB: {data.get('closed_count', '?')}")
print(f"Analyzing last {len(closed)} closed trades")
print("=" * 80)

# ── Load candles DB ──
candles_db = "/root/.hermes/data/candles.db"
conn = sqlite3.connect(candles_db)
cursor = conn.cursor()

# Table uses 'token' not 'symbol'
def get_btc_candle_at(ts_seconds):
    """Get BTC 1m candle at given unix timestamp."""
    cursor.execute("""
        SELECT open, high, low, close, ts
        FROM candles_1m
        WHERE token = 'BTC' AND ts <= ? AND ts > ?
        ORDER BY ts DESC LIMIT 1
    """, (ts_seconds, ts_seconds - 120))
    return cursor.fetchone()

def get_btc_candle_before(ts_seconds, lookback_minutes=15):
    """Get BTC 1m candle N minutes before given timestamp."""
    target = ts_seconds - (lookback_minutes * 60)
    cursor.execute("""
        SELECT open, high, low, close, ts
        FROM candles_1m
        WHERE token = 'BTC' AND ts <= ? AND ts > ?
        ORDER BY ts DESC LIMIT 1
    """, (target + 60, target - 60))
    return cursor.fetchone()

def get_btc_momentum(ts_seconds, lookback_minutes=15):
    """Calculate BTC momentum (% change) over lookback window ending at ts."""
    candle_at = get_btc_candle_at(ts_seconds)
    candle_before = get_btc_candle_before(ts_seconds, lookback_minutes)
    
    if candle_at and candle_before:
        price_now = candle_at[3]  # close
        price_before = candle_before[3]  # close
        if price_before > 0:
            return (price_now - price_before) / price_before * 100
    return None

# ── Get all signal types in last 50 trades ──
signal_counts = {}
for t in closed:
    sig = t.get('signal', 'unknown')
    signal_counts[sig] = signal_counts.get(sig, 0) + 1

print("\nSignal distribution in last 50 trades:")
for sig, count in sorted(signal_counts.items(), key=lambda x: -x[1]):
    print(f"  {sig}: {count}")

# ── Analyze by signal type ──
# Group all trades with pump-chain signals
pump_chain_plus = [t for t in closed if t.get('signal') == 'pump-chain+']
pump_chain_minus = [t for t in closed if t.get('signal') == 'pump-chain-']

print(f"\n{'=' * 80}")
print("DATA VERIFICATION: BTC Momentum at Trade Entry")
print("=" * 80)

# Build enriched trade records with BTC momentum
def enrich_trades(trades, label):
    """Add BTC momentum data to each trade."""
    enriched = []
    for t in trades:
        open_time = t.get('opened', '')
        coin = t.get('coin', '?')
        direction = t.get('direction', '?')
        pnl = t.get('pnl_usdt', 0)
        signal = t.get('signal', '?')
        amount = t.get('amount_usdt', 0)
        
        try:
            open_dt = datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S.%f")
        except:
            try:
                open_dt = datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S")
            except:
                print(f"  Cannot parse time: {open_time}")
                continue
        
        open_ts = int(open_dt.timestamp())
        
        # Get BTC momentum at trade open
        # Try multiple lookback windows
        momentum_5m = get_btc_momentum(open_ts, 5)
        momentum_15m = get_btc_momentum(open_ts, 15)
        momentum_30m = get_btc_momentum(open_ts, 30)
        
        btc_at_open = get_btc_candle_at(open_ts)
        btc_price = btc_at_open[3] if btc_at_open else None
        
        record = {
            'coin': coin,
            'direction': direction,
            'signal': signal,
            'pnl': pnl,
            'amount': amount,
            'open_time': open_time,
            'open_ts': open_ts,
            'btc_price': btc_price,
            'momentum_5m': momentum_5m,
            'momentum_15m': momentum_15m,
            'momentum_30m': momentum_30m,
            'is_win': pnl > 0
        }
        enriched.append(record)
    return enriched

print(f"\n{'─' * 80}")
print("PUMP-CHAIN+ (LONG signals)")
print(f"{'─' * 80}")
pc_plus = enrich_trades(pump_chain_plus, "pump-chain+")

# Print raw data table
print(f"\n{'Coin':<8} {'PnL$':>7} {'BTC@Open':>10} {'5m Mom%':>8} {'15m Mom%':>9} {'30m Mom%':>9} {'Result':>6}")
print("-" * 65)
for r in pc_plus:
    mom5 = f"{r['momentum_5m']:+.3f}" if r['momentum_5m'] is not None else "N/A"
    mom15 = f"{r['momentum_15m']:+.3f}" if r['momentum_15m'] is not None else "N/A"
    mom30 = f"{r['momentum_30m']:+.3f}" if r['momentum_30m'] is not None else "N/A"
    btc = f"${r['btc_price']:,.0f}" if r['btc_price'] else "N/A"
    result = "WIN" if r['is_win'] else "LOSS"
    print(f"{r['coin']:<8} {r['pnl']:>+7.2f} {btc:>10} {mom5:>8} {mom15:>9} {mom30:>9} {result:>6}")

print(f"\n{'─' * 80}")
print("PUMP-CHAIN- (SHORT signals)")
print(f"{'─' * 80}")
pc_minus = enrich_trades(pump_chain_minus, "pump-chain-")

print(f"\n{'Coin':<8} {'PnL$':>7} {'BTC@Open':>10} {'5m Mom%':>8} {'15m Mom%':>9} {'30m Mom%':>9} {'Result':>6}")
print("-" * 65)
for r in pc_minus:
    mom5 = f"{r['momentum_5m']:+.3f}" if r['momentum_5m'] is not None else "N/A"
    mom15 = f"{r['momentum_15m']:+.3f}" if r['momentum_15m'] is not None else "N/A"
    mom30 = f"{r['momentum_30m']:+.3f}" if r['momentum_30m'] is not None else "N/A"
    btc = f"${r['btc_price']:,.0f}" if r['btc_price'] else "N/A"
    result = "WIN" if r['is_win'] else "LOSS"
    print(f"{r['coin']:<8} {r['pnl']:>+7.2f} {btc:>10} {mom5:>8} {mom15:>9} {mom30:>9} {result:>6}")

# ── Threshold Analysis ──
# The plan proposes thresholding on "BTC momentum" — we need to determine which
# lookback window makes sense and whether ±0.3% is the right level.

print(f"\n{'=' * 80}")
print("THRESHOLD ANALYSIS: ±0.3% BTC Momentum")
print("=" * 80)

# Test multiple lookback windows and thresholds
threshold = 0.3  # percentage points

for lookback in [5, 15, 30]:
    mom_key = f'momentum_{lookback}m'
    
    print(f"\n{'─' * 80}")
    print(f"Lookback: {lookback} minutes")
    print(f"{'─' * 80}")
    
    # Pump-chain+: block when BTC momentum > +0.3% (chasing up)
    print(f"\n  PUMP-CHAIN+ (LONG) — block when BTC momentum > +{threshold}%")
    valid_plus = [r for r in pc_plus if r[mom_key] is not None]
    if valid_plus:
        blocked = [r for r in valid_plus if r[mom_key] > threshold]
        allowed = [r for r in valid_plus if r[mom_key] <= threshold]
        
        print(f"  Total trades with data: {len(valid_plus)}")
        print(f"  Blocked (BTC momentum > +{threshold}%): {len(blocked)}")
        print(f"  Allowed: {len(allowed)}")
        
        if blocked:
            b_wins = sum(1 for r in blocked if r['is_win'])
            b_losses = sum(1 for r in blocked if not r['is_win'])
            b_wr = b_wins / len(blocked) * 100 if blocked else 0
            b_pnl = sum(r['pnl'] for r in blocked)
            b_lost = sum(r['pnl'] for r in blocked if not r['is_win'])
            print(f"  Blocked wins: {b_wins}, Blocked losses: {b_losses}")
            print(f"  Blocked win rate: {b_wr:.1f}% (plan claims 30% = loses 70%)")
            print(f"  Blocked PnL: ${b_pnl:+.2f}")
            print(f"  Money saved from blocked losers: ${b_lost:+.2f}")
            for r in blocked:
                print(f"    {r['coin']}: mom={r[mom_key]:+.3f}%, pnl=${r['pnl']:+.2f}")
        
        if allowed:
            a_wins = sum(1 for r in allowed if r['is_win'])
            a_losses = sum(1 for r in allowed if not r['is_win'])
            a_wr = a_wins / len(allowed) * 100 if allowed else 0
            a_pnl = sum(r['pnl'] for r in allowed)
            print(f"  Allowed wins: {a_wins}, Allowed losses: {a_losses}")
            print(f"  Allowed win rate: {a_wr:.1f}%")
            print(f"  Allowed PnL: ${a_pnl:+.2f}")
    
    # Pump-chain-: block when BTC momentum < -0.3% (chasing down)
    print(f"\n  PUMP-CHAIN- (SHORT) — block when BTC momentum < -{threshold}%")
    valid_minus = [r for r in pc_minus if r[mom_key] is not None]
    if valid_minus:
        blocked = [r for r in valid_minus if r[mom_key] < -threshold]
        allowed = [r for r in valid_minus if r[mom_key] >= -threshold]
        
        print(f"  Total trades with data: {len(valid_minus)}")
        print(f"  Blocked (BTC momentum < -{threshold}%): {len(blocked)}")
        print(f"  Allowed: {len(allowed)}")
        
        if blocked:
            b_wins = sum(1 for r in blocked if r['is_win'])
            b_losses = sum(1 for r in blocked if not r['is_win'])
            b_wr = b_wins / len(blocked) * 100 if blocked else 0
            b_pnl = sum(r['pnl'] for r in blocked)
            b_lost = sum(r['pnl'] for r in blocked if not r['is_win'])
            print(f"  Blocked wins: {b_wins}, Blocked losses: {b_losses}")
            print(f"  Blocked win rate: {100-b_wr:.0f}% lose rate (plan claims 60% lose)")
            print(f"  Blocked PnL: ${b_pnl:+.2f}")
            print(f"  Money saved from blocked losers: ${b_lost:+.2f}")
            for r in blocked:
                print(f"    {r['coin']}: mom={r[mom_key]:+.3f}%, pnl=${r['pnl']:+.2f}")
        
        if allowed:
            a_wins = sum(1 for r in allowed if r['is_win'])
            a_losses = sum(1 for r in allowed if not r['is_win'])
            a_wr = a_wins / len(allowed) * 100 if allowed else 0
            a_pnl = sum(r['pnl'] for r in allowed)
            print(f"  Allowed wins: {a_wins}, Allowed losses: {a_losses}")
            print(f"  Allowed win rate: {a_wr:.1f}%")
            print(f"  Allowed PnL: ${a_pnl:+.2f}")

# ── Optimal Threshold Search ──
print(f"\n{'=' * 80}")
print("OPTIMAL THRESHOLD SEARCH (15m lookback)")
print("=" * 80)

mom_key = 'momentum_15m'
thresholds_to_test = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8, 1.0]

print(f"\n{'Thresh':>7} | {'++Block':>7} {'++Lost$':>8} {'++WR%':>6} | {'--Block':>7} {'--Lost$':>8} {'--WR%':>6} | {'TotBlk':>6} {'TotSave$':>9} {'GoodBlk':>8}")
print("-" * 100)

best_score = -999
best_threshold = 0
best_details = None

for t in thresholds_to_test:
    valid_plus = [r for r in pc_plus if r[mom_key] is not None]
    valid_minus = [r for r in pc_minus if r[mom_key] is not None]
    
    # pump-chain+: block when BTC > +t%
    blocked_plus = [r for r in valid_plus if r[mom_key] > t]
    b_losses_plus = [r for r in blocked_plus if not r['is_win']]
    b_wins_plus = [r for r in blocked_plus if r['is_win']]
    saved_plus = sum(abs(r['pnl']) for r in b_losses_plus)
    wr_plus = (len(b_losses_plus) / len(blocked_plus) * 100) if blocked_plus else 0
    
    # pump-chain-: block when BTC < -t%
    blocked_minus = [r for r in valid_minus if r[mom_key] < -t]
    b_losses_minus = [r for r in blocked_minus if not r['is_win']]
    b_wins_minus = [r for r in blocked_minus if r['is_win']]
    saved_minus = sum(abs(r['pnl']) for r in b_losses_minus)
    wr_minus = (len(b_losses_minus) / len(blocked_minus) * 100) if blocked_minus else 0
    
    total_blocked = len(blocked_plus) + len(blocked_minus)
    total_saved = saved_plus + saved_minus
    good_blocked = len(b_losses_plus) + len(b_losses_minus)
    bad_blocked = len(b_wins_plus) + len(b_wins_minus)
    
    # Score: maximize money saved while minimizing good trades blocked
    # Score = total_saved - (good_blocked * avg_win) 
    score = total_saved - (bad_blocked * 0.15)  # rough avg win
    
    print(f"{t:>7.2f} | {len(blocked_plus):>7} ${saved_plus:>+7.2f} {wr_plus:>5.0f}% | {len(blocked_minus):>7} ${saved_minus:>+7.2f} {wr_minus:>5.0f}% | {total_blocked:>6} ${total_saved:>+8.2f} {bad_blocked:>8}")
    
    if score > best_score:
        best_score = score
        best_threshold = t
        best_details = {
            'threshold': t,
            'blocked_plus': len(blocked_plus),
            'blocked_minus': len(blocked_minus),
            'total_blocked': total_blocked,
            'good_blocked': good_blocked,
            'bad_blocked': bad_blocked,
            'total_saved': total_saved
        }

print(f"\nBest threshold (by score): ±{best_threshold}%")
print(f"  Total blocked: {best_details['total_blocked']}")
print(f"  Good trades wrongly blocked: {best_details['bad_blocked']}")
print(f"  Losers blocked: {best_details['good_blocked']}")
print(f"  Money saved: ${best_details['total_saved']:+.2f}")

# ── Statistical Confidence ──
print(f"\n{'=' * 80}")
print("STATISTICAL CONFIDENCE")
print("=" * 80)

# Wilson score interval for binomial proportion
def wilson_ci(wins, n, z=1.96):
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0, 0)
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    margin = z * math.sqrt((p * (1-p) + z**2 / (4*n)) / n) / denom
    return (max(0, center - margin), min(1, center + margin))

# For the proposed threshold of 0.3%, 15m lookback
t = 0.3
mom_key = 'momentum_15m'
valid_plus = [r for r in pc_plus if r[mom_key] is not None]
valid_minus = [r for r in pc_minus if r[mom_key] is not None]

blocked_plus = [r for r in valid_plus if r[mom_key] > t]
blocked_minus = [r for r in valid_minus if r[mom_key] < -t]

if blocked_plus:
    b_losses_plus = sum(1 for r in blocked_plus if not r['is_win'])
    n_plus = len(blocked_plus)
    ci_lo, ci_hi = wilson_ci(n_plus - b_losses_plus, n_plus)
    print(f"\n  PUMP-CHAIN+ at +{t}% threshold:")
    print(f"    Sample size: {n_plus}")
    print(f"    Loss rate: {b_losses_plus}/{n_plus} = {b_losses_plus/n_plus*100:.1f}%")
    print(f"    95% CI for win rate: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")
    print(f"    Claimed: 70% lose (30% win)")
    if ci_hi < 0.35:
        print(f"    ✅ CI is BELOW 35% win — claim is SUPPORTED")
    elif ci_lo > 0.35:
        print(f"    ❌ CI is ABOVE 35% win — claim is REFUTED")
    else:
        print(f"    ⚠️  CI crosses 35% — claim is INCONCLUSIVE (need more data)")

if blocked_minus:
    b_losses_minus = sum(1 for r in blocked_minus if not r['is_win'])
    n_minus = len(blocked_minus)
    ci_lo, ci_hi = wilson_ci(n_minus - b_losses_minus, n_minus)
    print(f"\n  PUMP-CHAIN- at -{t}% threshold:")
    print(f"    Sample size: {n_minus}")
    print(f"    Loss rate: {b_losses_minus}/{n_minus} = {b_losses_minus/n_minus*100:.1f}%")
    print(f"    95% CI for win rate: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")
    print(f"    Claimed: 60% lose (40% win)")
    if ci_hi < 0.45:
        print(f"    ✅ CI is BELOW 45% win — claim is SUPPORTED")
    elif ci_lo > 0.45:
        print(f"    ❌ CI is ABOVE 45% win — claim is REFUTED")
    else:
        print(f"    ⚠️  CI crosses 45% — claim is INCONCLUSIVE (need more data)")

# ── Baseline win rates (no filter) ──
print(f"\n{'=' * 80}")
print("BASELINE WIN RATES (no filter)")
print("=" * 80)

for label, trades in [("pump-chain+", pc_plus), ("pump-chain-", pc_minus)]:
    if trades:
        wins = sum(1 for r in trades if r['is_win'])
        total = len(trades)
        wr = wins / total * 100
        pnl = sum(r['pnl'] for r in trades)
        ci_lo, ci_hi = wilson_ci(wins, total)
        print(f"\n  {label}: {wins}/{total} = {wr:.1f}% (95% CI: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%])")
        print(f"  Total PnL: ${pnl:+.2f}")

# ── ALL signal types combined (to verify "block 12/50 trades" claim) ──
print(f"\n{'=' * 80}")
print("FULL 50-TRADE BLOCK ANALYSIS")
print("=" * 80)

all_enriched = []
for t in closed:
    open_time = t.get('opened', '')
    try:
        open_dt = datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S.%f")
    except:
        try:
            open_dt = datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S")
        except:
            continue
    open_ts = int(open_dt.timestamp())
    mom = get_btc_momentum(open_ts, 15)
    
    all_enriched.append({
        'coin': t.get('coin', '?'),
        'signal': t.get('signal', '?'),
        'pnl': t.get('pnl_usdt', 0),
        'is_win': t.get('pnl_usdt', 0) > 0,
        'momentum_15m': mom,
        'amount': t.get('amount_usdt', 0)
    })

# Apply the proposed filter
blocked_trades = []
for r in all_enriched:
    if r['momentum_15m'] is None:
        continue
    if r['signal'] == 'pump-chain+' and r['momentum_15m'] > 0.3:
        blocked_trades.append(r)
    elif r['signal'] == 'pump-chain-' and r['momentum_15m'] < -0.3:
        blocked_trades.append(r)

print(f"\nAll pump-chain+ trades blocked: {sum(1 for r in blocked_trades if r['signal'] == 'pump-chain+')}")
print(f"All pump-chain- trades blocked: {sum(1 for r in blocked_trades if r['signal'] == 'pump-chain-')}")
print(f"Total trades blocked: {len(blocked_trades)}/50")

if blocked_trades:
    total_blocked_pnl = sum(r['pnl'] for r in blocked_trades)
    losers_blocked = [r for r in blocked_trades if not r['is_win']]
    winners_blocked = [r for r in blocked_trades if r['is_win']]
    saved = sum(abs(r['pnl']) for r in losers_blocked)
    lost_from_winners = sum(r['pnl'] for r in winners_blocked)
    
    print(f"\nBlocked trades breakdown:")
    print(f"  Losers blocked: {len(losers_blocked)}")
    print(f"  Winners blocked: {len(winners_blocked)}")
    print(f"  Net PnL of blocked trades: ${total_blocked_pnl:+.2f}")
    print(f"  Money saved from blocked losers: ${saved:+.2f}")
    print(f"  Money lost from blocked winners: ${lost_from_winners:+.2f}")
    print(f"  Net benefit: ${saved + lost_from_winners:+.2f}")
    
    print(f"\n  Plan claims: block 12/50, 8 losers, +$28.90 saved")
    print(f"  Actual:      block {len(blocked_trades)}/50, {len(losers_blocked)} losers, ${saved:+.2f} saved")
    
    print(f"\n  Individual blocked trades:")
    for r in blocked_trades:
        result = "WIN" if r['is_win'] else "LOSS"
        print(f"    {r['signal']:<15} {r['coin']:<8} mom={r['momentum_15m']:>+6.3f}% pnl=${r['pnl']:>+6.2f} {result}")

# ── ALSO: check momentum threshold on ALL signal types ──
print(f"\n{'=' * 80}")
print("EXPLORATORY: Does BTC momentum affect other signal types?")
print("=" * 80)

other_signals = {}
for r in all_enriched:
    if r['signal'] not in ('pump-chain+', 'pump-chain-'):
        sig = r['signal']
        if sig not in other_signals:
            other_signals[sig] = {'high_mom': [], 'low_mom': [], 'mid': []}
        if r['momentum_15m'] is not None:
            if r['momentum_15m'] > 0.3:
                other_signals[sig]['high_mom'].append(r)
            elif r['momentum_15m'] < -0.3:
                other_signals[sig]['low_mom'].append(r)
            else:
                other_signals[sig]['mid'].append(r)

for sig in sorted(other_signals.keys()):
    data = other_signals[sig]
    all_trades = data['high_mom'] + data['low_mom'] + data['mid']
    if all_trades:
        wins = sum(1 for r in all_trades if r['is_win'])
        wr = wins / len(all_trades) * 100
        print(f"\n  {sig}: {len(all_trades)} trades, WR={wr:.0f}%")
        
        for regime, label in [('high_mom', 'BTC>+0.3%'), ('low_mom', 'BTC<-0.3%'), ('mid', 'Neutral')]:
            trades = data[regime]
            if trades:
                w = sum(1 for r in trades if r['is_win'])
                wr_r = w / len(trades) * 100
                pnl = sum(r['pnl'] for r in trades)
                print(f"    {label}: {len(trades)} trades, WR={wr_r:.0f}%, PnL=${pnl:+.2f}")

conn.close()
