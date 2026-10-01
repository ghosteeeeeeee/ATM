#!/usr/bin/env python3
"""
Independent audit of RSI band analysis for SHORT and LONG signals.
Verifies claimed findings, tests statistical significance, checks confounders,
simulates filter impact, and tests 60-day stability.

Author: Independent Auditor
Date: 2026-10-01
"""

import psycopg2
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import json

DB_PARAMS = {
    'host': '/var/run/postgresql',
    'dbname': 'brain',
    'user': 'postgres'
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)

def query_trades(conn, days=30, direction=None, with_rsi_only=True):
    """Query closed trades with RSI data."""
    query = """
    SELECT 
        id, token, signal, direction, pnl_usdt, pnl_pct,
        entry_rsi_14, entry_regime_4h, volatility_regime,
        open_time, close_time, exit_reason,
        amount_usdt, leverage
    FROM trades
    WHERE open_time >= now() - interval '%s days'
      AND status = 'closed'
    """ % days
    
    if with_rsi_only:
        query += " AND entry_rsi_14 IS NOT NULL"
    
    if direction:
        query += " AND direction = '%s'" % direction
    
    query += " ORDER BY open_time"
    
    cur = conn.cursor()
    cur.execute(query)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    
    return [dict(zip(cols, row)) for row in rows]

def get_rsi_band(rsi):
    """Categorize RSI into bands."""
    if rsi < 25:
        return '<25'
    elif rsi < 30:
        return '25-30'
    elif rsi < 35:
        return '30-35'
    elif rsi < 40:
        return '35-40'
    elif rsi < 45:
        return '40-45'
    elif rsi < 50:
        return '45-50'
    elif rsi < 55:
        return '50-55'
    elif rsi < 60:
        return '55-60'
    elif rsi < 65:
        return '60-65'
    elif rsi < 70:
        return '65-70'
    else:
        return '70+'

def is_win(pnl_usdt, pnl_pct, criterion='pnl_usdt'):
    """Determine if trade is a win."""
    if criterion == 'pnl_usdt':
        return pnl_usdt > 0
    elif criterion == 'pnl_pct':
        return pnl_pct > 0
    elif criterion == 'pnl_usdt_nonneg':
        return pnl_usdt >= 0

def compute_band_stats(trades, criterion='pnl_usdt'):
    """Compute statistics by RSI band."""
    bands = {}
    for t in trades:
        band = get_rsi_band(t['entry_rsi_14'])
        if band not in bands:
            bands[band] = {'trades': [], 'wins': 0, 'total_pnl': 0.0}
        bands[band]['trades'].append(t)
        bands[band]['total_pnl'] += float(t['pnl_usdt'] or 0)
        if is_win(t['pnl_usdt'], t['pnl_pct'], criterion):
            bands[band]['wins'] += 1
    
    results = []
    for band in sorted(bands.keys()):
        data = bands[band]
        n = len(data['trades'])
        wins = data['wins']
        wr = wins / n * 100 if n > 0 else 0
        avg_pnl = data['total_pnl'] / n if n > 0 else 0
        
        # Compute avg win and avg loss
        win_pnls = [float(t['pnl_usdt'] or 0) for t in data['trades'] if is_win(t['pnl_usdt'], t['pnl_pct'], criterion)]
        loss_pnls = [float(t['pnl_usdt'] or 0) for t in data['trades'] if not is_win(t['pnl_usdt'], t['pnl_pct'], criterion)]
        
        avg_win = np.mean(win_pnls) if win_pnls else 0
        avg_loss = np.mean(loss_pnls) if loss_pnls else 0
        
        results.append({
            'band': band,
            'trades': n,
            'wins': wins,
            'losses': n - wins,
            'wr_pct': round(wr, 1),
            'total_pnl': round(data['total_pnl'], 2),
            'avg_pnl': round(avg_pnl, 3),
            'avg_win': round(avg_win, 3),
            'avg_loss': round(avg_loss, 3)
        })
    
    return results

def proportion_z_test(wins1, n1, wins2, n2):
    """Z-test for difference in proportions."""
    if n1 == 0 or n2 == 0:
        return None, 1.0
    
    p1 = wins1 / n1
    p2 = wins2 / n2
    p_pool = (wins1 + wins2) / (n1 + n2)
    
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    
    if se == 0:
        return 0, 1.0
    
    z = (p1 - p2) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    
    return z, p_value

def mann_whitney_test(pnls1, pnls2):
    """Mann-Whitney U test for difference in PnL distributions."""
    if len(pnls1) == 0 or len(pnls2) == 0:
        return None, 1.0
    
    try:
        u_stat, p_value = stats.mannwhitneyu(pnls1, pnls2, alternative='two-sided')
        return u_stat, p_value
    except:
        return None, 1.0

def bootstrap_wr_ci(wins, n, n_bootstrap=10000, ci=0.95):
    """Bootstrap confidence interval for win rate."""
    if n == 0:
        return 0, 0, 0
    
    win_rates = []
    for _ in range(n_bootstrap):
        sample_wins = np.random.binomial(n, wins/n)
        win_rates.append(sample_wins / n * 100)
    
    lower = np.percentile(win_rates, (1-ci)/2 * 100)
    upper = np.percentile(win_rates, (1+ci)/2 * 100)
    
    return wins/n*100, lower, upper

def analyze_confounders(trades, direction):
    """Analyze confounding variables: signal, time period, regime."""
    print("\n" + "="*80)
    print("CONFOUNDING VARIABLE ANALYSIS - %s" % direction)
    print("="*80)
    
    # By signal
    print("\n--- BY SIGNAL ---")
    signals = {}
    for t in trades:
        sig = t['signal'] or 'UNKNOWN'
        if sig not in signals:
            signals[sig] = []
        signals[sig].append(t)
    
    signal_stats = []
    for sig, sig_trades in signals.items():
        if len(sig_trades) < 3:
            continue
        wins = sum(1 for t in sig_trades if is_win(t['pnl_usdt'], t['pnl_pct']))
        total_pnl = sum(float(t['pnl_usdt'] or 0) for t in sig_trades)
        avg_rsi = np.mean([t['entry_rsi_14'] for t in sig_trades])
        signal_stats.append({
            'signal': sig,
            'trades': len(sig_trades),
            'wins': wins,
            'wr': round(wins/len(sig_trades)*100, 1),
            'pnl': round(total_pnl, 2),
            'avg_rsi': round(avg_rsi, 1)
        })
    
    signal_stats.sort(key=lambda x: x['trades'], reverse=True)
    for s in signal_stats[:15]:
        print("  %-30s %3dT  %5.1f%% WR  +%7.2f  avgRSI=%5.1f" % (
            s['signal'], s['trades'], s['wr'], s['pnl'], s['avg_rsi']))
    
    # Check if results are dominated by specific signals
    print("\n--- SIGNAL CONCENTRATION CHECK ---")
    top_signals = signal_stats[:3]
    top_trades = sum(s['trades'] for s in top_signals)
    top_pnl = sum(s['pnl'] for s in top_signals)
    total_trades = len(trades)
    total_pnl = sum(float(t['pnl_usdt'] or 0) for t in trades)
    
    print("  Top 3 signals: %dT (%.1f%% of trades), +%.2f (%.1f%% of PnL)" % (
        top_trades, top_trades/total_trades*100,
        top_pnl, top_pnl/total_pnl*100 if total_pnl != 0 else 0))
    
    # By time period (weekly)
    print("\n--- BY TIME PERIOD (WEEKLY) ---")
    weeks = {}
    for t in trades:
        if t['open_time']:
            week = t['open_time'].strftime('%Y-W%W')
            if week not in weeks:
                weeks[week] = []
            weeks[week].append(t)
    
    for week in sorted(weeks.keys()):
        week_trades = weeks[week]
        wins = sum(1 for t in week_trades if is_win(t['pnl_usdt'], t['pnl_pct']))
        total_pnl = sum(float(t['pnl_usdt'] or 0) for t in week_trades)
        avg_rsi = np.mean([t['entry_rsi_14'] for t in week_trades])
        print("  %s: %3dT  %5.1f%% WR  +%7.2f  avgRSI=%5.1f" % (
            week, len(week_trades), wins/len(week_trades)*100, total_pnl, avg_rsi))
    
    # By regime
    print("\n--- BY REGIME ---")
    regimes = {}
    for t in trades:
        reg = t['volatility_regime'] or t['entry_regime_4h'] or 'UNKNOWN'
        if reg not in regimes:
            regimes[reg] = []
        regimes[reg].append(t)
    
    for reg in sorted(regimes.keys()):
        reg_trades = regimes[reg]
        wins = sum(1 for t in reg_trades if is_win(t['pnl_usdt'], t['pnl_pct']))
        total_pnl = sum(float(t['pnl_usdt'] or 0) for t in reg_trades)
        avg_rsi = np.mean([t['entry_rsi_14'] for t in reg_trades])
        print("  %-15s %3dT  %5.1f%% WR  +%7.2f  avgRSI=%5.1f" % (
            reg, len(reg_trades), wins/len(reg_trades)*100, total_pnl, avg_rsi))

def simulate_filter_impact(trades, direction, proposed_floor, proposed_ceiling):
    """Simulate impact of proposed RSI filters."""
    print("\n" + "="*80)
    print("FILTER IMPACT SIMULATION - %s (Floor=%s, Ceiling=%s)" % (
        direction, proposed_floor, proposed_ceiling))
    print("="*80)
    
    blocked = []
    allowed = []
    
    for t in trades:
        rsi = t['entry_rsi_14']
        if rsi < proposed_floor or rsi >= proposed_ceiling:
            blocked.append(t)
        else:
            allowed.append(t)
    
    # Current state (no filter)
    current_wins = sum(1 for t in trades if is_win(t['pnl_usdt'], t['pnl_pct']))
    current_pnl = sum(float(t['pnl_usdt'] or 0) for t in trades)
    current_wr = current_wins / len(trades) * 100 if trades else 0
    
    # Blocked trades
    blocked_wins = sum(1 for t in blocked if is_win(t['pnl_usdt'], t['pnl_pct']))
    blocked_pnl = sum(float(t['pnl_usdt'] or 0) for t in blocked)
    blocked_wr = blocked_wins / len(blocked) * 100 if blocked else 0
    
    # Allowed trades (post-filter)
    allowed_wins = sum(1 for t in allowed if is_win(t['pnl_usdt'], t['pnl_pct']))
    allowed_pnl = sum(float(t['pnl_usdt'] or 0) for t in allowed)
    allowed_wr = allowed_wins / len(allowed) * 100 if allowed else 0
    
    print("\n  CURRENT STATE (no filter):")
    print("    Trades: %d, Wins: %d, WR: %.1f%%, Total PnL: +%.2f" % (
        len(trades), current_wins, current_wr, current_pnl))
    
    print("\n  BLOCKED TRADES (would be filtered out):")
    print("    Trades: %d (%.1f%% of total)" % (len(blocked), len(blocked)/len(trades)*100 if trades else 0))
    print("    Wins: %d, WR: %.1f%%" % (blocked_wins, blocked_wr))
    print("    Total PnL: +%.2f" % blocked_pnl)
    print("    Winners blocked: %d" % blocked_wins)
    
    # Detail blocked winners
    blocked_winners = [t for t in blocked if is_win(t['pnl_usdt'], t['pnl_pct'])]
    if blocked_winners:
        print("\n    BLOCKED WINNERS DETAIL:")
        for t in sorted(blocked_winners, key=lambda x: -float(x['pnl_usdt'] or 0))[:10]:
            print("      RSI=%5.1f  +%.2f  %s  %s" % (
                t['entry_rsi_14'], float(t['pnl_usdt'] or 0),
                t['signal'], t['token']))
    
    print("\n  POST-FILTER STATE (allowed trades only):")
    print("    Trades: %d" % len(allowed))
    print("    Wins: %d, WR: %.1f%%" % (allowed_wins, allowed_wr))
    print("    Total PnL: +%.2f" % allowed_pnl)
    print("    WR improvement: %+.1f percentage points" % (allowed_wr - current_wr))
    print("    PnL improvement: +%.2f" % (allowed_pnl - current_pnl))
    
    # Check if filter blocks winners in profitable bands
    print("\n  WINNERS BLOCKED IN 'GOOD' BANDS (potential edge loss):")
    for band_min, band_max, band_name in [(45, 55, '45-55'), (55, 60, '55-60'), (55, 70, '55-70')]:
        band_blocked_wins = [t for t in blocked 
                            if is_win(t['pnl_usdt'], t['pnl_pct'])
                            and band_min <= t['entry_rsi_14'] < band_max]
        band_blocked_pnl = sum(float(t['pnl_usdt'] or 0) for t in band_blocked_wins)
        if band_blocked_wins:
            print("    Band %s: %d winners blocked, +%.2f PnL lost" % (
                band_name, len(band_blocked_wins), band_blocked_pnl))

def check_boundaries(trades, direction, boundaries=[25, 30, 35, 40, 45, 50, 55, 60, 65, 70]):
    """Check trades exactly at RSI boundaries."""
    print("\n" + "="*80)
    print("BOUNDARY ANALYSIS - %s" % direction)
    print("="*80)
    
    for boundary in boundaries:
        # Trades within ±0.5 of boundary
        near_boundary = [t for t in trades if abs(t['entry_rsi_14'] - boundary) < 0.5]
        exact_boundary = [t for t in trades if t['entry_rsi_14'] == boundary]
        
        if near_boundary or exact_boundary:
            print("\n  RSI ≈ %d (±0.5): %d trades" % (boundary, len(near_boundary)))
            if near_boundary:
                wins = sum(1 for t in near_boundary if is_win(t['pnl_usdt'], t['pnl_pct']))
                total_pnl = sum(float(t['pnl_usdt'] or 0) for t in near_boundary)
                print("    Wins: %d, WR: %.1f%%, PnL: +%.2f" % (
                    wins, wins/len(near_boundary)*100, total_pnl))
                
                # Show individual trades
                for t in sorted(near_boundary, key=lambda x: x['entry_rsi_14']):
                    pnl = float(t['pnl_usdt'] or 0)
                    win_mark = "W" if is_win(t['pnl_usdt'], t['pnl_pct']) else "L"
                    print("      RSI=%5.2f  %s  +%.2f  %s  %s" % (
                        t['entry_rsi_14'], win_mark, pnl, t['signal'], t['token']))
            
            if exact_boundary:
                print("    EXACT boundary=%d: %d trades" % (boundary, len(exact_boundary)))

def analyze_60day_stability(direction):
    """Analyze 60-day data for pattern stability."""
    print("\n" + "="*80)
    print("60-DAY STABILITY ANALYSIS - %s" % direction)
    print("="*80)
    
    conn = get_connection()
    trades_60d = query_trades(conn, days=60, direction=direction)
    conn.close()
    
    print("\n  60-day trades with RSI: %d" % len(trades_60d))
    
    # Split into 30-day windows
    trades_30d_recent = [t for t in trades_60d if t['open_time'] >= datetime.now() - timedelta(days=30)]
    trades_30d_older = [t for t in trades_60d if t['open_time'] < datetime.now() - timedelta(days=30)]
    
    print("  Recent 30d: %d trades" % len(trades_30d_recent))
    print("  Older 30d: %d trades" % len(trades_30d_older))
    
    # Compare bands between periods
    print("\n  BAND COMPARISON (Recent 30d vs Older 30d):")
    print("  %-10s | %-25s | %-25s" % ("Band", "Recent 30d", "Older 30d"))
    print("  " + "-"*65)
    
    recent_stats = {r['band']: r for r in compute_band_stats(trades_30d_recent)}
    older_stats = {r['band']: r for r in compute_band_stats(trades_30d_older)}
    
    all_bands = sorted(set(list(recent_stats.keys()) + list(older_stats.keys())))
    
    for band in all_bands:
        rec = recent_stats.get(band, {'trades': 0, 'wr_pct': 0, 'total_pnl': 0})
        old = older_stats.get(band, {'trades': 0, 'wr_pct': 0, 'total_pnl': 0})
        
        rec_str = "%3dT %5.1f%%WR %+6.2f" % (rec['trades'], rec['wr_pct'], rec['total_pnl'])
        old_str = "%3dT %5.1f%%WR %+6.2f" % (old['trades'], old['wr_pct'], old['total_pnl'])
        
        # Mark consistency
        if rec['trades'] >= 5 and old['trades'] >= 5:
            if (rec['wr_pct'] > 50) == (old['wr_pct'] > 50):
                consistent = " ✓"
            else:
                consistent = " ✗"
        else:
            consistent = "  "
        
        print("  %-10s | %-25s | %-25s%s" % (band, rec_str, old_str, consistent))
    
    return trades_60d

def main():
    print("="*80)
    print("INDEPENDENT RSI BAND AUDIT")
    print("="*80)
    print("Date: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("Database: brain @ /var/run/postgresql")
    print("Window: Last 30 days (primary), 60 days (stability)")
    print("="*80)
    
    conn = get_connection()
    
    # Query 30-day data
    trades_short = query_trades(conn, days=30, direction='SHORT')
    trades_long = query_trades(conn, days=30, direction='LONG')
    
    print("\n" + "="*80)
    print("DATA SUMMARY")
    print("="*80)
    print("  SHORT trades with RSI (30d): %d" % len(trades_short))
    print("  LONG trades with RSI (30d): %d" % len(trades_long))
    
    # ===== SHORT ANALYSIS =====
    print("\n" + "="*80)
    print("SHORT SIGNAL ANALYSIS")
    print("="*80)
    
    print("\n--- RSI BAND STATISTICS (30d) ---")
    short_stats = compute_band_stats(trades_short, criterion='pnl_usdt')
    print("  %-10s %5s %5s %5s %8s %10s %10s %10s" % (
        "Band", "Trades", "Wins", "Losses", "WR%", "TotalPnL", "AvgWin", "AvgLoss"))
    print("  " + "-"*70)
    for s in short_stats:
        print("  %-10s %5d %5d %5d %7.1f%% %+10.2f %+10.3f %+10.3f" % (
            s['band'], s['trades'], s['wins'], s['losses'],
            s['wr_pct'], s['total_pnl'], s['avg_win'], s['avg_loss']))
    
    # Verify claimed SHORT numbers
    print("\n--- CLAIM VERIFICATION: SHORT ---")
    claims_short = [
        ('<25', 22, 9.1, -2.49),
        ('30-35', 19, 26.3, -1.85),
        ('45-50', 18, 61.1, 0.14),
        ('50-55', 10, 90.0, 1.04),
        ('55-60', 10, 50.0, 0.27),
    ]
    
    stats_by_band = {s['band']: s for s in short_stats}
    
    for band, claim_trades, claim_wr, claim_pnl in claims_short:
        if band in stats_by_band:
            s = stats_by_band[band]
            trades_match = "✓" if s['trades'] == claim_trades else "✗"
            wr_match = "✓" if abs(s['wr_pct'] - claim_wr) < 0.2 else "✗"
            pnl_match = "✓" if abs(s['total_pnl'] - claim_pnl) < 0.02 else "✗"
            print("  RSI %-6s: Claimed %2dT %.1f%%WR +%.2f | Actual %2dT %.1f%%WR +%.2f [%s %s %s]" % (
                band, claim_trades, claim_wr, claim_pnl,
                s['trades'], s['wr_pct'], s['total_pnl'],
                trades_match, wr_match, pnl_match))
    
    # Sweet spot verification
    sweet_spot_short = [s for s in short_stats if s['band'] in ['45-50', '50-55', '55-60']]
    ss_trades = sum(s['trades'] for s in sweet_spot_short)
    ss_wins = sum(s['wins'] for s in sweet_spot_short)
    ss_pnl = sum(s['total_pnl'] for s in sweet_spot_short)
    ss_wr = ss_wins / ss_trades * 100 if ss_trades > 0 else 0
    
    print("\n  SWEET SPOT RSI 45-60:")
    print("    Claimed: 38T, 65.8%WR, +$1.45")
    print("    Actual:  %dT, %.1f%%WR, +%.2f" % (ss_trades, ss_wr, ss_pnl))
    
    # ===== LONG ANALYSIS =====
    print("\n" + "="*80)
    print("LONG SIGNAL ANALYSIS")
    print("="*80)
    
    print("\n--- RSI BAND STATISTICS (30d) ---")
    long_stats = compute_band_stats(trades_long, criterion='pnl_usdt')
    print("  %-10s %5s %5s %5s %8s %10s %10s %10s" % (
        "Band", "Trades", "Wins", "Losses", "WR%", "TotalPnL", "AvgWin", "AvgLoss"))
    print("  " + "-"*70)
    for s in long_stats:
        print("  %-10s %5d %5d %5d %7.1f%% %+10.2f %+10.3f %+10.3f" % (
            s['band'], s['trades'], s['wins'], s['losses'],
            s['wr_pct'], s['total_pnl'], s['avg_win'], s['avg_loss']))
    
    # Verify claimed LONG numbers
    print("\n--- CLAIM VERIFICATION: LONG ---")
    claims_long = [
        ('55-60', 15, 66.7, 1.00),
        ('60-65', 20, 35.0, 0.86),
        ('65-70', 24, 58.3, 0.34),
    ]
    
    stats_by_band_long = {s['band']: s for s in long_stats}
    
    for band, claim_trades, claim_wr, claim_pnl in claims_long:
        if band in stats_by_band_long:
            s = stats_by_band_long[band]
            trades_match = "✓" if s['trades'] == claim_trades else "✗"
            wr_match = "✓" if abs(s['wr_pct'] - claim_wr) < 0.2 else "✗"
            pnl_match = "✓" if abs(s['total_pnl'] - claim_pnl) < 0.02 else "✗"
            print("  RSI %-6s: Claimed %2dT %.1f%%WR +%.2f | Actual %2dT %.1f%%WR +%.2f [%s %s %s]" % (
                band, claim_trades, claim_wr, claim_pnl,
                s['trades'], s['wr_pct'], s['total_pnl'],
                trades_match, wr_match, pnl_match))
    
    # Sweet spot verification (with pnl_pct criterion to match claim)
    print("\n--- LONG SWEET SPOT VERIFICATION ---")
    sweet_spot_long = [s for s in long_stats if s['band'] in ['55-60', '60-65', '65-70']]
    ss_trades_l = sum(s['trades'] for s in sweet_spot_long)
    ss_wins_l = sum(s['wins'] for s in sweet_spot_long)
    ss_pnl_l = sum(s['total_pnl'] for s in sweet_spot_long)
    ss_wr_l = ss_wins_l / ss_trades_l * 100 if ss_trades_l > 0 else 0
    
    print("  Claimed: 59T, 55.9%WR, +$2.20")
    print("  Actual (pnl_usdt>0): %dT, %.1f%%WR, +%.2f" % (ss_trades_l, ss_wr_l, ss_pnl_l))
    
    # Check with pnl_pct criterion
    trades_long_55_70 = [t for t in trades_long if 55 <= t['entry_rsi_14'] < 70]
    wins_pct_criterion = sum(1 for t in trades_long_55_70 if is_win(t['pnl_usdt'], t['pnl_pct'], 'pnl_pct'))
    wr_pct_criterion = wins_pct_criterion / len(trades_long_55_70) * 100 if trades_long_55_70 else 0
    print("  Actual (pnl_pct>0): %dT, %.1f%%WR, +%.2f" % (
        len(trades_long_55_70), wr_pct_criterion, sum(float(t['pnl_usdt'] or 0) for t in trades_long_55_70)))
    
    # ===== STATISTICAL SIGNIFICANCE =====
    print("\n" + "="*80)
    print("STATISTICAL SIGNIFICANCE TESTS")
    print("="*80)
    
    # SHORT: 45-60 vs 30-45
    print("\n--- SHORT: RSI 45-60 vs RSI 30-45 ---")
    short_45_60 = [t for t in trades_short if 45 <= t['entry_rsi_14'] < 60]
    short_30_45 = [t for t in trades_short if 30 <= t['entry_rsi_14'] < 45]
    
    wins_45_60 = sum(1 for t in short_45_60 if is_win(t['pnl_usdt'], t['pnl_pct']))
    wins_30_45 = sum(1 for t in short_30_45 if is_win(t['pnl_usdt'], t['pnl_pct']))
    
    n_45_60 = len(short_45_60)
    n_30_45 = len(short_30_45)
    
    print("  RSI 45-60: %dT, %dW, %.1f%%WR" % (n_45_60, wins_45_60, wins_45_60/n_45_60*100 if n_45_60 else 0))
    print("  RSI 30-45: %dT, %dW, %.1f%%WR" % (n_30_45, wins_30_45, wins_30_45/n_30_45*100 if n_30_45 else 0))
    
    z, p_value = proportion_z_test(wins_45_60, n_45_60, wins_30_45, n_30_45)
    if z is not None:
        print("  Z-test: z=%.3f, p-value=%.4f" % (z, p_value))
        print("  Significant at α=0.05: %s" % ("YES ✓" if p_value < 0.05 else "NO ✗"))
        print("  Significant at α=0.10: %s" % ("YES ✓" if p_value < 0.10 else "NO ✗"))
    
    # Bootstrap CI
    wr_45_60, ci_low, ci_high = bootstrap_wr_ci(wins_45_60, n_45_60)
    print("  RSI 45-60 WR 95%% CI: [%.1f%%, %.1f%%]" % (ci_low, ci_high))
    wr_30_45, ci_low2, ci_high2 = bootstrap_wr_ci(wins_30_45, n_30_45)
    print("  RSI 30-45 WR 95%% CI: [%.1f%%, %.1f%%]" % (ci_low2, ci_high2))
    
    # Mann-Whitney for PnL
    pnls_45_60 = [float(t['pnl_usdt'] or 0) for t in short_45_60]
    pnls_30_45 = [float(t['pnl_usdt'] or 0) for t in short_30_45]
    u_stat, u_pvalue = mann_whitney_test(pnls_45_60, pnls_30_45)
    if u_stat is not None:
        print("  Mann-Whitney U test (PnL): U=%.1f, p-value=%.4f" % (u_stat, u_pvalue))
        print("  PnL distributions differ significantly: %s" % ("YES ✓" if u_pvalue < 0.05 else "NO ✗"))
    
    # LONG: 55-70 vs 40-55
    print("\n--- LONG: RSI 55-70 vs RSI 40-55 ---")
    long_55_70 = [t for t in trades_long if 55 <= t['entry_rsi_14'] < 70]
    long_40_55 = [t for t in trades_long if 40 <= t['entry_rsi_14'] < 55]
    
    wins_55_70 = sum(1 for t in long_55_70 if is_win(t['pnl_usdt'], t['pnl_pct']))
    wins_40_55 = sum(1 for t in long_40_55 if is_win(t['pnl_usdt'], t['pnl_pct']))
    
    n_55_70 = len(long_55_70)
    n_40_55 = len(long_40_55)
    
    print("  RSI 55-70: %dT, %dW, %.1f%%WR" % (n_55_70, wins_55_70, wins_55_70/n_55_70*100 if n_55_70 else 0))
    print("  RSI 40-55: %dT, %dW, %.1f%%WR" % (n_40_55, wins_40_55, wins_40_55/n_40_55*100 if n_40_55 else 0))
    
    z, p_value = proportion_z_test(wins_55_70, n_55_70, wins_40_55, n_40_55)
    if z is not None:
        print("  Z-test: z=%.3f, p-value=%.4f" % (z, p_value))
        print("  Significant at α=0.05: %s" % ("YES ✓" if p_value < 0.05 else "NO ✗"))
        print("  Significant at α=0.10: %s" % ("YES ✓" if p_value < 0.10 else "NO ✗"))
    
    wr_55_70, ci_low3, ci_high3 = bootstrap_wr_ci(wins_55_70, n_55_70)
    print("  RSI 55-70 WR 95%% CI: [%.1f%%, %.1f%%]" % (ci_low3, ci_high3))
    wr_40_55, ci_low4, ci_high4 = bootstrap_wr_ci(wins_40_55, n_40_55)
    print("  RSI 40-55 WR 95%% CI: [%.1f%%, %.1f%%]" % (ci_low4, ci_high4))
    
    pnls_55_70 = [float(t['pnl_usdt'] or 0) for t in long_55_70]
    pnls_40_55 = [float(t['pnl_usdt'] or 0) for t in long_40_55]
    u_stat, u_pvalue = mann_whitney_test(pnls_55_70, pnls_40_55)
    if u_stat is not None:
        print("  Mann-Whitney U test (PnL): U=%.1f, p-value=%.4f" % (u_stat, u_pvalue))
        print("  PnL distributions differ significantly: %s" % ("YES ✓" if u_pvalue < 0.05 else "NO ✗"))
    
    # ===== CONFOUNDING VARIABLES =====
    analyze_confounders(trades_short, 'SHORT')
    analyze_confounders(trades_long, 'LONG')
    
    # ===== FILTER IMPACT =====
    simulate_filter_impact(trades_short, 'SHORT', proposed_floor=45, proposed_ceiling=60)
    simulate_filter_impact(trades_long, 'LONG', proposed_floor=20, proposed_ceiling=70)
    
    # ===== BOUNDARY ANALYSIS =====
    check_boundaries(trades_short, 'SHORT')
    check_boundaries(trades_long, 'LONG')
    
    # ===== 60-DAY STABILITY =====
    trades_60d_short = analyze_60day_stability('SHORT')
    trades_60d_long = analyze_60day_stability('LONG')
    
    # ===== OVERALL SUMMARY =====
    print("\n" + "="*80)
    print("OVERALL AUDIT SUMMARY")
    print("="*80)
    
    conn.close()
    
    return {
        'short_stats': short_stats,
        'long_stats': long_stats,
        'trades_short': len(trades_short),
        'trades_long': len(trades_long)
    }

if __name__ == '__main__':
    results = main()
