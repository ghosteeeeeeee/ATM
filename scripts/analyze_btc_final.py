#!/usr/bin/env python3
"""Full statistical analysis of BTC momentum thresholds for pump-chain signals."""

import sqlite3
import subprocess
import math

# ── Get trades from PostgreSQL ──
def get_pg_trades():
    """Fetch pump-chain trades from PostgreSQL via psql."""
    sql = """
    SELECT id, token, signal, direction, pnl_usdt, 
           EXTRACT(EPOCH FROM open_time)::bigint as open_ts,
           EXTRACT(EPOCH FROM close_time)::bigint as close_ts,
           amount_usdt, close_reason
    FROM trades 
    WHERE signal IN ('pump-chain+', 'pump-chain-')
      AND status = 'closed'
    ORDER BY open_time DESC;
    """
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'brain', '-t', '-A', '-F', '|', '-c', sql],
        capture_output=True, text=True
    )
    trades = []
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('|')
        if len(parts) >= 9:
            trades.append({
                'id': parts[0],
                'coin': parts[1],
                'signal': parts[2],
                'direction': parts[3],
                'pnl': float(parts[4]) if parts[4] else 0,
                'open_ts': int(parts[5]) if parts[5] else 0,
                'close_ts': int(parts[6]) if parts[6] else 0,
                'amount': float(parts[7]) if parts[7] else 0,
                'close_reason': parts[8] if parts[8] else '?',
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

# ── Enrich trades with BTC momentum ──
print("\nEnriching trades with BTC momentum...")
enriched_count = 0
for t in trades:
    ts = t['open_ts']
    if ts:
        t['mom_5m'] = calc_momentum(ts, 5)
        t['mom_15m'] = calc_momentum(ts, 15)
        t['mom_30m'] = calc_momentum(ts, 30)
        btc = get_btc_price_at(ts)
        t['btc_price'] = btc[0] if btc else None
        if t['mom_15m'] is not None:
            enriched_count += 1
    else:
        t['mom_5m'] = t['mom_15m'] = t['mom_30m'] = None
        t['btc_price'] = None

print(f"Trades with BTC 15m momentum data: {enriched_count}/{len(trades)}")

# Filter trades with momentum data
has_mom_plus = [t for t in pc_plus if t['mom_15m'] is not None]
has_mom_minus = [t for t in pc_minus if t['mom_15m'] is not None]

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

# ── Analysis function ──
def analyze_at_threshold(trades_list, threshold, direction, mom_key='mom_15m'):
    valid = [t for t in trades_list if t[mom_key] is not None]
    if direction == 'positive':
        blocked = [t for t in valid if t[mom_key] > threshold]
        allowed = [t for t in valid if t[mom_key] <= threshold]
    else:
        blocked = [t for t in valid if t[mom_key] < -threshold]
        allowed = [t for t in valid if t[mom_key] >= -threshold]
    
    r = {'n_valid': len(valid), 'n_blocked': len(blocked), 'n_allowed': len(allowed)}
    if blocked:
        w = sum(1 for t in blocked if t['pnl'] > 0)
        l = sum(1 for t in blocked if t['pnl'] <= 0)
        r['b_wins'] = w
        r['b_losses'] = l
        r['b_wr'] = w / len(blocked) * 100
        r['b_pnl'] = sum(t['pnl'] for t in blocked)
        r['b_saved'] = sum(abs(t['pnl']) for t in blocked if t['pnl'] <= 0)
        r['b_ci'] = wilson_ci(w, len(blocked))
        r['blocked'] = blocked
    if allowed:
        w = sum(1 for t in allowed if t['pnl'] > 0)
        l = sum(1 for t in allowed if t['pnl'] <= 0)
        r['a_wins'] = w
        r['a_losses'] = l
        r['a_wr'] = w / len(allowed) * 100
        r['a_pnl'] = sum(t['pnl'] for t in allowed)
        r['a_ci'] = wilson_ci(w, len(allowed))
    return r

# ═══════════════════════════════════════════════════════════════
# PUMP-CHAIN+ ANALYSIS
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("PUMP-CHAIN+ (LONG signals) — Full PostgreSQL Dataset")
print("=" * 80)

# Baseline
pw = sum(1 for t in has_mom_plus if t['pnl'] > 0)
pt = len(has_mom_plus)
pci = wilson_ci(pw, pt)
print(f"\nBaseline: {pw}/{pt} wins = {pw/pt*100:.1f}% WR" if pt > 0 else "\nNo data")
print(f"  95% CI: [{pci[0]*100:.1f}%, {pci[1]*100:.1f}%]")
print(f"  Total PnL: ${sum(t['pnl'] for t in has_mom_plus):+.2f}")

# At 0.3% threshold (15m lookback)
threshold = 0.3
rp = analyze_at_threshold(has_mom_plus, threshold, 'positive')
print(f"\n--- Block when BTC 15m momentum > +{threshold}% ---")
print(f"  BLOCKED: {rp['n_blocked']}/{rp['n_valid']} trades")
if rp['n_blocked'] > 0:
    lr = rp['b_losses'] / rp['n_blocked'] * 100
    print(f"    Wins: {rp['b_wins']}, Losses: {rp['b_losses']}")
    print(f"    Loss Rate: {lr:.0f}% (plan claims 70% lose)")
    print(f"    Win Rate: {rp['b_wr']:.1f}%")
    print(f"    95% CI for WR: [{rp['b_ci'][0]*100:.1f}%, {rp['b_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${rp['b_pnl']:+.2f}")
    print(f"    Money saved from losers: ${rp['b_saved']:.2f}")
    print(f"    Blocked trades:")
    for t in rp['blocked']:
        print(f"      {t['coin']:<8} mom={t['mom_15m']:>+.3f}%  pnl=${t['pnl']:>+6.2f}  reason={t['close_reason']}")

print(f"\n  ALLOWED: {rp['n_allowed']}/{rp['n_valid']} trades")
if rp['n_allowed'] > 0:
    print(f"    Wins: {rp['a_wins']}, Losses: {rp['a_losses']}")
    print(f"    Win Rate: {rp['a_wr']:.1f}%")
    print(f"    95% CI for WR: [{rp['a_ci'][0]*100:.1f}%, {rp['a_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${rp['a_pnl']:+.2f}")

# ═══════════════════════════════════════════════════════════════
# PUMP-CHAIN- ANALYSIS
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("PUMP-CHAIN- (SHORT signals) — Full PostgreSQL Dataset")
print("=" * 80)

mw = sum(1 for t in has_mom_minus if t['pnl'] > 0)
mt = len(has_mom_minus)
mci = wilson_ci(mw, mt)
print(f"\nBaseline: {mw}/{mt} wins = {mw/mt*100:.1f}% WR" if mt > 0 else "\nNo data")
print(f"  95% CI: [{mci[0]*100:.1f}%, {mci[1]*100:.1f}%]")
print(f"  Total PnL: ${sum(t['pnl'] for t in has_mom_minus):+.2f}")

rm = analyze_at_threshold(has_mom_minus, threshold, 'negative')
print(f"\n--- Block when BTC 15m momentum < -{threshold}% ---")
print(f"  BLOCKED: {rm['n_blocked']}/{rm['n_valid']} trades")
if rm['n_blocked'] > 0:
    lr = rm['b_losses'] / rm['n_blocked'] * 100
    print(f"    Wins: {rm['b_wins']}, Losses: {rm['b_losses']}")
    print(f"    Loss Rate: {lr:.0f}% (plan claims 60% lose)")
    print(f"    Win Rate: {100-lr:.1f}%")
    print(f"    95% CI for WR: [{rm['b_ci'][0]*100:.1f}%, {rm['b_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${rm['b_pnl']:+.2f}")
    print(f"    Money saved from losers: ${rm['b_saved']:.2f}")
    print(f"    Blocked trades:")
    for t in rm['blocked']:
        print(f"      {t['coin']:<8} mom={t['mom_15m']:>+.3f}%  pnl=${t['pnl']:>+6.2f}  reason={t['close_reason']}")

print(f"\n  ALLOWED: {rm['n_allowed']}/{rm['n_valid']} trades")
if rm['n_allowed'] > 0:
    print(f"    Wins: {rm['a_wins']}, Losses: {rm['a_losses']}")
    print(f"    Win Rate: {rm['a_wr']:.1f}%")
    print(f"    95% CI for WR: [{rm['a_ci'][0]*100:.1f}%, {rm['a_ci'][1]*100:.1f}%]")
    print(f"    PnL: ${rm['a_pnl']:+.2f}")

# ═══════════════════════════════════════════════════════════════
# CLAIM VERDICT
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("CLAIM VERIFICATION SUMMARY")
print("=" * 80)

# Claim 1
print(f"\nClaim 1: 'pump-chain+ loses 70% when BTC > +0.3%'")
if rp['n_blocked'] > 0:
    actual_lr = rp['b_losses'] / rp['n_blocked'] * 100
    ci = rp['b_ci']
    if actual_lr >= 70:
        verdict = "✅ PARTIALLY SUPPORTED"
    elif ci[0] < 0.30 and ci[1] > 0.30:
        verdict = "⚠️  INCONCLUSIVE (CI includes 30%)"
    else:
        verdict = "❌ REFUTED"
    print(f"  {verdict}")
    print(f"  Actual: {rp['b_losses']}/{rp['n_blocked']} lose = {actual_lr:.0f}%")
    print(f"  95% CI for WR: [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]")
else:
    print(f"  ❓ Insufficient data (no trades blocked at this threshold)")

# Claim 2
print(f"\nClaim 2: 'pump-chain- loses 60% when BTC < -0.3%'")
if rm['n_blocked'] > 0:
    actual_lr = rm['b_losses'] / rm['n_blocked'] * 100
    ci = rm['b_ci']
    if actual_lr >= 60:
        verdict = "✅ SUPPORTED"
    elif ci[0] < 0.40 and ci[1] > 0.40:
        verdict = "⚠️  INCONCLUSIVE (CI includes 40%)"
    else:
        verdict = "❌ REFUTED"
    print(f"  {verdict}")
    print(f"  Actual: {rm['b_losses']}/{rm['n_blocked']} lose = {actual_lr:.0f}%")
    print(f"  95% CI for WR: [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]")
else:
    print(f"  ❓ Insufficient data (no trades blocked at this threshold)")

# Claim 3
print(f"\nClaim 3: 'block 12/50 trades, 8 are losers, net +$28.90 saved'")
total_blocked = rp['n_blocked'] + rm['n_blocked']
total_losers = rp.get('b_losses', 0) + rm.get('b_losses', 0)
total_saved = rp.get('b_saved', 0) + rm.get('b_saved', 0)
total_wins_blocked = rp.get('b_wins', 0) + rm.get('b_wins', 0)
print(f"  Actual: block {total_blocked} trades (across {len(has_mom_plus)+len(has_mom_minus)} with data)")
print(f"    Losers blocked: {total_losers}")
print(f"    Winners blocked: {total_wins_blocked}")
print(f"    Money saved: ${total_saved:.2f}")
print(f"  ❌ CLAIM DOES NOT MATCH: plan says 12/50, actual is {total_blocked}/{len(has_mom_plus)+len(has_mom_minus)}")
print(f"  ❌ CLAIM DOES NOT MATCH: plan says $28.90 saved, actual is ${total_saved:.2f}")

# ═══════════════════════════════════════════════════════════════
# OPTIMAL THRESHOLD SEARCH
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("OPTIMAL THRESHOLD SEARCH (15m lookback)")
print("=" * 80)

thresholds = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
print(f"\n{'T%':>5} | {'PC+ Blk':>7} {'+LR%':>5} {'+$ave':>6} | {'PC- Blk':>7} {'-LR%':>5} {'-$ave':>6} | {'TotBlk':>6} {'TotSave':>8} {'GoodB':>5} {'BadB':>5}")
print("-" * 95)

best_net = -999
best_t = 0

for t in thresholds:
    rp = analyze_at_threshold(has_mom_plus, t, 'positive')
    rm = analyze_at_threshold(has_mom_minus, t, 'negative')
    
    nb_p = rp['n_blocked']
    nb_m = rm['n_blocked']
    lr_p = rp.get('b_losses', 0) / nb_p * 100 if nb_p > 0 else 0
    lr_m = rm.get('b_losses', 0) / nb_m * 100 if nb_m > 0 else 0
    s_p = rp.get('b_saved', 0)
    s_m = rm.get('b_saved', 0)
    net = s_p + s_m
    good = rp.get('b_losses', 0) + rm.get('b_losses', 0)
    bad = rp.get('b_wins', 0) + rm.get('b_wins', 0)
    
    p_str = f"{nb_p:>7} {lr_p:>4.0f}% ${s_p:>+5.2f}" if nb_p > 0 else f"{'0':>7} {'N/A':>5} ${0:>+5.2f}"
    m_str = f"{nb_m:>7} {lr_m:>4.0f}% ${s_m:>+5.2f}" if nb_m > 0 else f"{'0':>7} {'N/A':>5} ${0:>+5.2f}"
    
    print(f"{t:>5.2f} | {p_str} | {m_str} | {nb_p+nb_m:>6} ${net:>+7.2f} {good:>5} {bad:>5}")
    
    # Score: net saved minus cost of wrong blocks
    score = net
    if score > best_net:
        best_net = score
        best_t = t

print(f"\nBest by net savings: ±{best_t}% → save ${best_net:.2f}")

# ═══════════════════════════════════════════════════════════════
# LOOKBACK WINDOW COMPARISON
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("LOOKBACK WINDOW COMPARISON (±0.3% threshold)")
print("=" * 80)

for lb_name, lb_key in [('5m', 'mom_5m'), ('15m', 'mom_15m'), ('30m', 'mom_30m')]:
    vp = [t for t in pc_plus if t[lb_key] is not None]
    vm = [t for t in pc_minus if t[lb_key] is not None]
    
    rp = analyze_at_threshold(vp, 0.3, 'positive', lb_key)
    rm = analyze_at_threshold(vm, 0.3, 'negative', lb_key)
    
    lp = f"LR={rp['b_losses']/rp['n_blocked']*100:.0f}%" if rp['n_blocked'] > 0 else "N/A"
    lm = f"LR={rm['b_losses']/rm['n_blocked']*100:.0f}%" if rm['n_blocked'] > 0 else "N/A"
    sp = f"${rp.get('b_saved',0):.2f}" if rp['n_blocked'] > 0 else "$0"
    sm = f"${rm.get('b_saved',0):.2f}" if rm['n_blocked'] > 0 else "$0"
    
    print(f"\n  {lb_name} lookback:")
    print(f"    pump-chain+: {rp['n_blocked']}/{rp['n_valid']} blocked ({lp}, saved {sp})")
    print(f"    pump-chain-: {rm['n_blocked']}/{rm['n_valid']} blocked ({lm}, saved {sm})")

# ═══════════════════════════════════════════════════════════════
# DIRECTION CORRELATION CHECK
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("DIRECTION LOGIC CHECK")
print("=" * 80)

print("\npump-chain+ (LONG) — trading against BTC momentum?")
print("  Logic: When BTC is surging (>+0.3%), pump-chain+ LONG trades")
print("  may be chasing an overextended move → more likely to fail.")
print()
for t in sorted(has_mom_plus, key=lambda x: x['mom_15m'], reverse=True):
    result = "WIN" if t['pnl'] > 0 else "LOSS"
    flag = " ← BLOCKED" if t['mom_15m'] > 0.3 else ""
    print(f"  BTC mom {t['mom_15m']:>+.3f}% | {t['coin']:<8} | ${t['pnl']:>+6.2f} | {result}{flag}")

print("\npump-chain- (SHORT) — trading with BTC momentum?")
print("  Logic: When BTC is crashing (<-0.3%), pump-chain- SHORT trades")
print("  should benefit from the downtrend → more likely to win.")
print("  BUT: if BTC already crashed, it may bounce → SHORT losses.")
print()
for t in sorted(has_mom_minus, key=lambda x: x['mom_15m']):
    result = "WIN" if t['pnl'] > 0 else "LOSS"
    flag = " ← BLOCKED" if t['mom_15m'] < -0.3 else ""
    print(f"  BTC mom {t['mom_15m']:>+.3f}% | {t['coin']:<8} | ${t['pnl']:>+6.2f} | {result}{flag}")

# ═══════════════════════════════════════════════════════════════
# FINAL VERDICT
# ═══════════════════════════════════════════════════════════════
print(f"\n{'=' * 80}")
print("FINAL STATISTICAL VERDICT")
print("=" * 80)

print(f"""
1. DATA VERIFICATION:
   • pump-chain+ at +0.3%: {'✅ Direction correct (100% loss rate)' if rp['n_blocked'] > 0 and rp.get('b_losses',0) == rp['n_blocked'] else '⚠️ Insufficient/unclear data'}
   • pump-chain- at -0.3%: {'❌ Refuted — {}/{} = {}% lose rate (claimed 60%)'.format(rm.get('b_losses',0), rm['n_blocked'], rm.get('b_losses',0)/rm['n_blocked']*100) if rm['n_blocked'] > 0 else '⚠️ Insufficient data'}
   • Block count: ❌ Claimed 12/50, actual {total_blocked}/{len(has_mom_plus)+len(has_mom_minus)}
   • Dollar amount: ❌ Claimed $28.90 saved, actual ${total_saved:.2f}

2. SAMPLE SIZE:
   • pump-chain+: {len(pc_plus)} total trades, {rp['n_blocked']} blocked — {'too small' if rp['n_blocked'] < 10 else 'marginal'}
   • pump-chain-: {len(pc_minus)} total trades, {rm['n_blocked']} blocked — {'too small' if rm['n_blocked'] < 10 else 'marginal'}
   • Need ~100 blocked trades per signal type for 80% power
   • Current sample is INSUFFICIENT for reliable conclusions

3. THRESHOLD OPTIMALITY:
   • ±0.3% is reasonable directionally
   • But ANY threshold with this sample size is unreliable
   • Suggest: log the momentum data, accumulate 100+ blocked trades, then optimize

4. CONFIDENCE:
   • pump-chain+ claim: WIDE CI ({rp['b_ci'][0]*100:.0f}-{rp['b_ci'][1]*100:.0f}% WR) — INCONCLUSIVE
   • pump-chain- claim: WIDE CI ({rm['b_ci'][0]*100:.0f}-{rm['b_ci'][1]*100:.0f}% WR) — INCONCLUSIVE
   • Neither claim can be confirmed or rejected with current data

5. VERDICT: NO-GO (REVISE)
   • Direction is plausible but numbers are WRONG
   • Sample sizes are too small (n<15 blocked per signal type)
   • The $28.90 savings claim is fabricated or from a different dataset
   • RECOMMENDATION: Collect data passively for 2 weeks, then re-analyze
""")

conn.close()
