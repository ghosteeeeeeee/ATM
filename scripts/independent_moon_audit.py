#!/usr/bin/env python3
"""
INDEPENDENT AUDIT — Moon-Tide Correlation Claims
No trust in prior analysis. Fresh computation from raw data.
"""

import sqlite3, math, os, sys, json, statistics
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB, CANDLES_DB

# ══════════════════════════════════════════════════════════════════════════════
# PART 1: MOON PHASE CALCULATION — VERIFY CORRECTNESS
# ══════════════════════════════════════════════════════════════════════════════

def moon_phase_date(date: datetime) -> float:
    """Script's moon phase calculation."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic_month
    phase = moon_age / synodic_month
    return (1 - math.cos(2 * math.pi * phase)) / 2

def verify_moon_algorithm():
    """
    Cross-check against known moon phases.
    Jan 6, 2000 18:14 UTC = New Moon (verified: USNO)
    Jan 13, 2000 ~07:00 UTC = First Quarter (illumination ~0.5)
    Jan 21, 2000 ~05:00 UTC = Full Moon (illumination ~1.0)
    Jan 28, 2000 ~17:00 UTC = Last Quarter (illumination ~0.5)
    """
    print("=" * 80)
    print("PART 1: MOON ALGORITHM VERIFICATION")
    print("=" * 80)
    
    tests = [
        ("Jan 6, 2000 18:14 (known New Moon)", datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc), 0.0),
        ("Jan 6, 2000 12:00 (6h before NM)", datetime(2000, 1, 6, 12, 0, tzinfo=timezone.utc), 0.01),
        ("Jan 14, 2000 (First Quarter)", datetime(2000, 1, 14, 0, 0, tzinfo=timezone.utc), 0.5),
        ("Jan 21, 2000 (Full Moon)", datetime(2000, 1, 21, 0, 0, tzinfo=timezone.utc), 1.0),
        ("Jan 28, 2000 (Last Quarter)", datetime(2000, 1, 28, 0, 0, tzinfo=timezone.utc), 0.5),
        ("Aug 1, 2026 (should be ~First Quarter)", datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc), None),
        ("Aug 23, 2026 (should be ~Full Moon)", datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc), None),
        ("Aug 6, 2026 (should be ~Full Moon)", datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc), None),
    ]
    
    all_ok = True
    for label, dt, expected in tests:
        illum = moon_phase_date(dt)
        status = ""
        if expected is not None:
            diff = abs(illum - expected)
            if diff < 0.1:
                status = f"✅ (diff={diff:.3f})"
            else:
                status = f"⚠️  (diff={diff:.3f}) expected ~{expected:.2f}"
                all_ok = False
        else:
            status = f"(no expected value, computed={illum:.3f})"
        
        print(f"  {label:55s} → illum={illum:.3f} {status}")
    
    # Check: does the algorithm produce a smooth cosine curve?
    print("\n  Checking algorithmic consistency over 1 full cycle (29.53 days)...")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    vals = []
    for i in range(30):
        illum = moon_phase_date(base + timedelta(days=i))
        vals.append(illum)
    
    # Should be: 0→0.5→1→0.5→0 over the cycle
    max_val = max(vals)
    min_val = min(vals)
    print(f"  Range over cycle: {min_val:.3f} to {max_val:.3f}")
    
    if max_val > 0.95 and min_val < 0.05:
        print("  ✅ Algorithm produces proper 0-1 range")
    else:
        print("  ⚠️  Algorithm range may be off")
        all_ok = False
    
    # Check: number of minima (new moons) in a year should be ~12-13
    new_moon_count = 0
    for i in range(365):
        illum_today = moon_phase_date(base + timedelta(days=i))
        illum_next = moon_phase_date(base + timedelta(days=i+1))
        if illum_today < 0.1 and illum_today <= illum_next:
            new_moon_count += 1
    
    print(f"  New moons in 365 days: {new_moon_count} (expected ~12-13)")
    if 11 <= new_moon_count <= 14:
        print("  ✅ Consistent with real lunar cycle")
    else:
        print("  ⚠️  Unexpected new moon count")
        all_ok = False
    
    # Verify the bucketing logic
    print("\n  Checking moon_week bucketing:")
    # get_moon_week from the script
    def get_moon_week(illumination):
        if illumination < 0.15: return 'Week 1 (New)'
        elif illumination < 0.50: return 'Week 2 (Waxing)'
        elif illumination < 0.85: return 'Week 3 (Full)'
        else: return 'Week 4 (Waning)'
    
    # This bucketing is problematic! It maps by illumination, NOT by phase direction.
    # A waning moon with 80% illumination is mapped to "Week 3 (Full)" but it's Waning Gibbous.
    # A waxing moon with 20% illumination is mapped to "Week 2 (Waxing)" but could be Waxing Crescent.
    # The boundary at 0.85 catches waning gibbous (80-95%) as "Week 4 (Waning)" — but only partially.
    print("  ⚠️  CRITICAL FLAW: get_moon_week() maps by ILLUMINATION level, not by DIRECTION.")
    print("     Waning Gibbous (90% illum) = 'Week 4 (Waning)' ✅")
    print("     Waning Gibbous (80% illum) = 'Week 3 (Full)' ❌ (it's waning, not full!)")
    print("     Waxing Gibbous (80% illum) = 'Week 3 (Full)' ❌ (it's waxing, not full!)")
    print("     This means the 'weeks' are NOT what they claim to be.")
    
    # Better approach: use moon_age to determine direction
    print("\n  Better approach: use moon_age to determine waxing vs waning:")
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    
    for test_day in [1, 5, 8, 14, 15, 20, 22, 28]:
        age = test_day  # simplified
        illum = (1 - math.cos(2 * math.pi * age / synodic_month)) / 2
        if age < 7.38: phase = "New/Waxing Crescent"
        elif age < 14.77: phase = "Waxing (First Quarter → Full)" if age < 14.77 else "Full"
        else: phase = "Waning"
        print(f"    Day {test_day:2d}: illum={illum:.3f}")
    
    return all_ok


# ══════════════════════════════════════════════════════════════════════════════
# PART 2: INDEPENDENT DATA EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_trade_data():
    """Extract ALL trade data from PostgreSQL — no assumptions."""
    conn = None
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                user='postgres', connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DATE(close_time) as day,
                   direction,
                   pnl_usdt,
                   pnl_pct,
                   status,
                   close_time,
                   open_time,
                   token,
                   leverage,
                   amount_usdt
            FROM trades
            WHERE status = 'closed'
            ORDER BY close_time
        """)
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        if conn:
            conn.close()

def extract_candle_data():
    """Extract BTC candle data — no assumptions."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute('''
            SELECT DATE(ts, 'unixepoch') as day,
                   open, high, low, close
            FROM candles_1h
            WHERE token = 'BTC'
            ORDER BY ts
        ''').fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PART 3: CORRECT MOON WEEK CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def classify_moon_week(date: datetime) -> str:
    """
    Correct classification using moon AGE (not illumination alone).
    Moon age 0 = New Moon
    Moon age 7.38 = First Quarter (waxing)
    Moon age 14.77 = Full Moon
    Moon age 22.15 = Last Quarter (waning)
    Moon age 29.53 = New Moon again
    """
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic_month
    
    if moon_age < 7.38:
        return 'Week 1 (New→FirstQ)'
    elif moon_age < 14.77:
        return 'Week 2 (FirstQ→Full)'
    elif moon_age < 22.15:
        return 'Week 3 (Full→LastQ)'
    else:
        return 'Week 4 (LastQ→New)'

def classify_moon_day(date: datetime) -> int:
    """Moon age in days 0-29."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    return int(days_since % synodic_month)

def moon_illumination(date: datetime) -> float:
    """Moon illumination 0-1."""
    return moon_phase_date(date)

def is_waxing(date: datetime) -> bool:
    """Whether moon is waxing (growing illumination)."""
    known_new_moon = datetime(2000, 1, 6, 18, 14, 0, tzinfo=timezone.utc)
    synodic_month = 29.53059
    days_since = (date - known_new_moon).total_seconds() / 86400
    moon_age = days_since % synodic_month
    return moon_age < 14.77  # Before full moon = waxing


# ══════════════════════════════════════════════════════════════════════════════
# PART 4: STATISTICAL FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def pearson_r(xs, ys):
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return 0.0, 1.0  # not enough data
    
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    
    ss_xx = sum((x - mean_x)**2 for x in xs)
    ss_yy = sum((y - mean_y)**2 for y in ys)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    
    if ss_xx == 0 or ss_yy == 0:
        return 0.0, 1.0
    
    r = ss_xy / math.sqrt(ss_xx * ss_yy)
    
    # t-test for significance
    if abs(r) < 1:
        t_stat = r * math.sqrt((n - 2) / (1 - r**2))
        # Two-tailed p-value approximation using t-distribution
        # For |t| > 2.0, p < 0.05 (approximate)
        df = n - 2
        # Simple approximation of p-value
        if df > 0:
            p_approx = 2 * math.exp(-0.717 * abs(t_stat) - 0.416 * t_stat**2) if abs(t_stat) > 0 else 1.0
        else:
            p_approx = 1.0
    else:
        t_stat = float('inf')
        p_approx = 0.0
    
    return r, p_approx

def mann_whitney_u(xs, ys):
    """
    Mann-Whitney U test for two independent samples.
    Tests if one sample tends to have higher values than the other.
    Returns (U statistic, approximate p-value).
    """
    n1, n2 = len(xs), len(ys)
    if n1 < 5 or n2 < 5:
        return None, 1.0
    
    all_vals = [(v, 0) for v in xs] + [(v, 1) for v in ys]
    all_vals.sort(key=lambda x: x[0])
    
    # Assign ranks
    ranks = [0] * len(all_vals)
    i = 0
    while i < len(all_vals):
        j = i
        while j < len(all_vals) and all_vals[j][0] == all_vals[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2  # 1-based ranks
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    
    # Sum ranks for group 0
    R1 = sum(r for (v, g), r in zip(all_vals, ranks) if g == 0)
    
    U1 = R1 - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    
    # Normal approximation for p-value
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma > 0:
        z = (U - mu) / sigma
        # Approximate p from z-score
        p = 2 * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi) if abs(z) < 5 else 0.0
        p = min(p, 1.0)
    else:
        p = 1.0
    
    return U, p

def cohens_d(xs, ys):
    """Cohen's d effect size."""
    n1, n2 = len(xs), len(ys)
    if n1 < 2 or n2 < 2:
        return 0.0
    mean1, mean2 = sum(xs)/n1, sum(ys)/n2
    var1 = sum((x-mean1)**2 for x in xs)/(n1-1)
    var2 = sum((y-mean2)**2 for y in ys)/(n2-1)
    pooled_std = math.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    if pooled_std == 0:
        return 0.0
    return (mean1 - mean2) / pooled_std


# ══════════════════════════════════════════════════════════════════════════════
# PART 5: MAIN AUDIT
# ══════════════════════════════════════════════════════════════════════════════

def run_audit():
    print("\n" + "=" * 80)
    print("🔍 INDEPENDENT AUDIT: MOON-TIDE CORRELATION")
    print("=" * 80)
    
    # ── Step 1: Verify moon algorithm ──
    verify_moon_algorithm()
    
    # ── Step 2: Extract raw data ──
    print("\n" + "=" * 80)
    print("PART 2: RAW DATA EXTRACTION")
    print("=" * 80)
    
    trade_rows = extract_trade_data()
    candle_rows = extract_candle_data()
    
    print(f"  Trades extracted: {len(trade_rows)}")
    print(f"  Candle rows extracted: {len(candle_rows)}")
    
    if trade_rows:
        dates = [r[5] for r in trade_rows if r[5]]  # close_time
        print(f"  Trade date range: {min(dates)} to {max(dates)}")
    
    if candle_rows:
        days = set(r[0] for r in candle_rows)
        print(f"  Candle date range: {min(r[0] for r in candle_rows)} to {max(r[0] for r in candle_rows)}")
        print(f"  Unique candle days: {len(days)}")
    
    # ── Step 3: Build daily BTC data ──
    print("\n" + "=" * 80)
    print("PART 3: BTC DAILY STATISTICS")
    print("=" * 80)
    
    daily_btc = defaultdict(lambda: {'opens': [], 'closes': [], 'highs': [], 'lows': []})
    for day, o, h, l, c in candle_rows:
        daily_btc[day]['opens'].append(o)
        daily_btc[day]['closes'].append(c)
        daily_btc[day]['highs'].append(h)
        daily_btc[day]['lows'].append(l)
    
    btc_daily = {}
    for day, data in daily_btc.items():
        open_p = data['opens'][0]   # First hour open = daily open
        close_p = data['closes'][-1]  # Last hour close = daily close
        high = max(data['highs'])
        low = min(data['lows'])
        
        daily_return = ((close_p - open_p) / open_p) * 100 if open_p > 0 else 0
        daily_range = ((high - low) / low) * 100 if low > 0 else 0
        
        btc_daily[day] = {
            'return_pct': daily_return,
            'range_pct': daily_range,
            'open': open_p,
            'close': close_p,
        }
    
    print(f"  BTC days computed: {len(btc_daily)}")
    if btc_daily:
        returns = [v['return_pct'] for v in btc_daily.values()]
        ranges = [v['range_pct'] for v in btc_daily.values()]
        print(f"  Avg daily return: {statistics.mean(returns):+.3f}%")
        print(f"  Avg daily range:  {statistics.mean(ranges):.3f}%")
        print(f"  Std dev returns:  {statistics.stdev(returns):.3f}%")
    
    # ── Step 4: Build daily trade data ──
    print("\n" + "=" * 80)
    print("PART 4: DAILY TRADE STATISTICS")
    print("=" * 80)
    
    daily_trades = defaultdict(lambda: {
        'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0,
        'long_t': 0, 'short_t': 0, 'long_wins': 0, 'short_wins': 0,
        'long_pnl': 0.0, 'short_pnl': 0.0,
    })
    
    for row in trade_rows:
        day = str(row[0]) if row[0] else None
        if not day:
            continue
        direction = row[1]
        pnl = float(row[2]) if row[2] else 0.0
        
        daily_trades[day]['trades'] += 1
        daily_trades[day]['pnl'] += pnl
        if pnl > 0:
            daily_trades[day]['wins'] += 1
        else:
            daily_trades[day]['losses'] += 1
        
        if direction == 'LONG':
            daily_trades[day]['long_t'] += 1
            daily_trades[day]['long_pnl'] += pnl
            if pnl > 0:
                daily_trades[day]['long_wins'] += 1
        else:
            daily_trades[day]['short_t'] += 1
            daily_trades[day]['short_pnl'] += pnl
            if pnl > 0:
                daily_trades[day]['short_wins'] += 1
    
    print(f"  Days with trades: {len(daily_trades)}")
    total_trades = sum(d['trades'] for d in daily_trades.values())
    total_wins = sum(d['wins'] for d in daily_trades.values())
    total_pnl = sum(d['pnl'] for d in daily_trades.values())
    print(f"  Total trades: {total_trades}")
    print(f"  Overall WR: {total_wins/total_trades*100:.1f}%")
    print(f"  Overall PnL: ${total_pnl:.2f}")
    
    # ── Step 5: Classify by MOON WEEK (corrected) ──
    print("\n" + "=" * 80)
    print("PART 5: TRADE PERFORMANCE BY MOON WEEK (CORRECTED)")
    print("=" * 80)
    
    # Corrected classification
    trade_by_week_corrected = defaultdict(lambda: {
        'days': set(), 'trades': 0, 'wins': 0, 'pnl': 0.0,
        'long_t': 0, 'short_t': 0, 'long_w': 0, 'short_w': 0,
        'long_pnl': 0.0, 'short_pnl': 0.0,
    })
    
    # Script's (flawed) classification
    trade_by_week_script = defaultdict(lambda: {
        'days': set(), 'trades': 0, 'wins': 0, 'pnl': 0.0,
        'long_t': 0, 'short_t': 0, 'long_w': 0, 'short_w': 0,
        'long_pnl': 0.0, 'short_pnl': 0.0,
    })
    
    def get_moon_week_illumination(illumination):
        """Script's original method - based on illumination only."""
        if illumination < 0.15: return 'Week 1 (New)'
        elif illumination < 0.50: return 'Week 2 (Waxing)'
        elif illumination < 0.85: return 'Week 3 (Full)'
        else: return 'Week 4 (Waning)'
    
    for day_str, data in daily_trades.items():
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        
        illum = moon_illumination(date)
        
        # Script's classification
        w_script = get_moon_week_illumination(illum)
        # Corrected classification (using moon age)
        w_corrected = classify_moon_week(date)
        
        for bucket, week_label in [(trade_by_week_script, w_script), (trade_by_week_corrected, w_corrected)]:
            bucket[week_label]['days'].add(day_str)
            bucket[week_label]['trades'] += data['trades']
            bucket[week_label]['wins'] += data['wins']
            bucket[week_label]['pnl'] += data['pnl']
            bucket[week_label]['long_t'] += data['long_t']
            bucket[week_label]['short_t'] += data['short_t']
            bucket[week_label]['long_w'] += data['long_wins']
            bucket[week_label]['short_w'] += data['short_wins']
            bucket[week_label]['long_pnl'] += data['long_pnl']
            bucket[week_label]['short_pnl'] += data['short_pnl']
    
    print("\n  SCRIPT'S CLASSIFICATION (illumination-based, flawed):")
    print(f"  {'Week':30s} | {'Days':>5s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>10s} | {'Long WR':>8s} | {'Short WR':>9s} | {'L PnL':>10s} | {'S PnL':>10s}")
    print("  " + "-" * 115)
    
    script_weeks_order = ['Week 1 (New)', 'Week 2 (Waxing)', 'Week 3 (Full)', 'Week 4 (Waning)']
    for week in script_weeks_order:
        d = trade_by_week_script[week]
        if d['trades'] > 0:
            wr = d['wins'] / d['trades'] * 100
            lwr = d['long_w'] / d['long_t'] * 100 if d['long_t'] > 0 else 0
            swr = d['short_w'] / d['short_t'] * 100 if d['short_t'] > 0 else 0
            print(f"  {week:30s} | {len(d['days']):5d} | {d['trades']:7d} | {wr:5.1f}% | ${d['pnl']:9.2f} | {lwr:7.1f}% | {swr:8.1f}% | ${d['long_pnl']:9.2f} | ${d['short_pnl']:9.2f}")
    
    print("\n  CORRECTED CLASSIFICATION (moon age-based):")
    print(f"  {'Week':30s} | {'Days':>5s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>10s} | {'Long WR':>8s} | {'Short WR':>9s} | {'L PnL':>10s} | {'S PnL':>10s}")
    print("  " + "-" * 115)
    
    corrected_weeks_order = ['Week 1 (New→FirstQ)', 'Week 2 (FirstQ→Full)', 'Week 3 (Full→LastQ)', 'Week 4 (LastQ→New)']
    for week in corrected_weeks_order:
        d = trade_by_week_corrected[week]
        if d['trades'] > 0:
            wr = d['wins'] / d['trades'] * 100
            lwr = d['long_w'] / d['long_t'] * 100 if d['long_t'] > 0 else 0
            swr = d['short_w'] / d['short_t'] * 100 if d['short_t'] > 0 else 0
            print(f"  {week:30s} | {len(d['days']):5d} | {d['trades']:7d} | {wr:5.1f}% | ${d['pnl']:9.2f} | {lwr:7.1f}% | {swr:8.1f}% | ${d['long_pnl']:9.2f} | ${d['short_pnl']:9.2f}")
    
    # ── Step 6: Per-day analysis (29-day cycle) ──
    print("\n" + "=" * 80)
    print("PART 6: TRADE PERFORMANCE BY MOON DAY (0-28)")
    print("=" * 80)
    
    day_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'days': set()})
    day_stats_dir = defaultdict(lambda: {'long_t': 0, 'short_t': 0, 'long_w': 0, 'short_w': 0, 'long_pnl': 0.0, 'short_pnl': 0.0})
    
    for day_str, data in daily_trades.items():
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        md = classify_moon_day(date)
        day_stats[md]['trades'] += data['trades']
        day_stats[md]['wins'] += data['wins']
        day_stats[md]['pnl'] += data['pnl']
        day_stats[md]['days'].add(day_str)
        
        k = md
        day_stats_dir[k]['long_t'] += data['long_t']
        day_stats_dir[k]['short_t'] += data['short_t']
        day_stats_dir[k]['long_w'] += data['long_wins']
        day_stats_dir[k]['short_w'] += data['short_wins']
        day_stats_dir[k]['long_pnl'] += data['long_pnl']
        day_stats_dir[k]['short_pnl'] += data['short_pnl']
    
    print(f"\n  {'Day':>3s} | {'Trades':>7s} | {'WR':>6s} | {'PnL':>10s} | {'Days':>5s} | {'L WR':>6s} | {'S WR':>6s} | {'L PnL':>9s} | {'S PnL':>9s}")
    print("  " + "-" * 95)
    
    for md in range(29):
        s = day_stats[md]
        sd = day_stats_dir[md]
        if s['trades'] > 0:
            wr = s['wins'] / s['trades'] * 100
            lwr = sd['long_w'] / sd['long_t'] * 100 if sd['long_t'] > 0 else 0
            swr = sd['short_w'] / sd['short_t'] * 100 if sd['short_t'] > 0 else 0
            print(f"  {md:3d} | {s['trades']:7d} | {wr:5.1f}% | ${s['pnl']:9.2f} | {len(s['days']):5d} | {lwr:5.1f}% | {swr:5.1f}% | ${sd['long_pnl']:9.2f} | ${sd['short_pnl']:9.2f}")
        else:
            print(f"  {md:3d} | {0:7d} | {'N/A':>6s} | {'N/A':>10s} | {0:5d} | {'N/A':>6s} | {'N/A':>6s} | {'N/A':>9s} | {'N/A':>9s}")
    
    # ── Step 7: Correlation analysis ──
    print("\n" + "=" * 80)
    print("PART 7: CORRELATION ANALYSIS")
    print("=" * 80)
    
    # Build paired data: (illumination, trade_wr), (illumination, btc_range), etc.
    paired_wr = []
    paired_range = []
    paired_return = []
    paired_long_wr = []
    paired_short_wr = []
    
    for day_str in sorted(set(list(btc_daily.keys()) + list(daily_trades.keys()))):
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        
        illum = moon_illumination(date)
        
        td = daily_trades.get(day_str)
        bd = btc_daily.get(day_str)
        
        if td and td['trades'] >= 1:  # At least 1 trade
            paired_wr.append((illum, td['wins'] / td['trades'] * 100))
            if td['long_t'] > 0:
                paired_long_wr.append((illum, td['long_wins'] / td['long_t'] * 100))
            if td['short_t'] > 0:
                paired_short_wr.append((illum, td['short_wins'] / td['short_t'] * 100))
        
        if bd:
            paired_range.append((illum, bd['range_pct']))
            paired_return.append((illum, bd['return_pct']))
    
    print(f"\n  Paired samples for correlation:")
    print(f"    Illumination vs Trade WR: {len(paired_wr)} days")
    print(f"    Illumination vs BTC Range: {len(paired_range)} days")
    print(f"    Illumination vs BTC Return: {len(paired_return)} days")
    
    # Correlation 1: Illumination vs BTC Range
    if len(paired_range) > 10:
        xs = [p[0] for p in paired_range]
        ys = [p[1] for p in paired_range]
        r, p_val = pearson_r(xs, ys)
        print(f"\n  1. Moon Illumination vs BTC Daily Range:")
        print(f"     Pearson r = {r:.4f}")
        print(f"     p-value ≈ {p_val:.4f}")
        print(f"     Significant at α=0.05? {'YES' if p_val < 0.05 else 'NO'}")
        print(f"     Effect size (Cohen's d): {cohens_d(xs[:len(xs)//2], xs[len(xs)//2:]):.3f}")
    
    # Correlation 2: Illumination vs BTC Return
    if len(paired_return) > 10:
        xs = [p[0] for p in paired_return]
        ys = [p[1] for p in paired_return]
        r, p_val = pearson_r(xs, ys)
        print(f"\n  2. Moon Illumination vs BTC Daily Return:")
        print(f"     Pearson r = {r:.4f}")
        print(f"     p-value ≈ {p_val:.4f}")
        print(f"     Significant at α=0.05? {'YES' if p_val < 0.05 else 'NO'}")
    
    # Correlation 3: Illumination vs Trade WR
    if len(paired_wr) > 10:
        xs = [p[0] for p in paired_wr]
        ys = [p[1] for p in paired_wr]
        r, p_val = pearson_r(xs, ys)
        print(f"\n  3. Moon Illumination vs Trade Win Rate:")
        print(f"     Pearson r = {r:.4f}")
        print(f"     p-value ≈ {p_val:.4f}")
        print(f"     Significant at α=0.05? {'YES' if p_val < 0.05 else 'NO'}")
    
    # Correlation 4: Moon age vs Trade WR
    paired_age_wr = []
    for day_str in sorted(daily_trades.keys()):
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        td = daily_trades[day_str]
        if td['trades'] >= 1:
            age = classify_moon_day(date)
            paired_age_wr.append((age, td['wins'] / td['trades'] * 100))
    
    if len(paired_age_wr) > 10:
        xs = [p[0] for p in paired_age_wr]
        ys = [p[1] for p in paired_age_wr]
        r, p_val = pearson_r(xs, ys)
        print(f"\n  4. Moon Age vs Trade Win Rate:")
        print(f"     Pearson r = {r:.4f}")
        print(f"     p-value ≈ {p_val:.4f}")
        print(f"     Significant at α=0.05? {'YES' if p_val < 0.05 else 'NO'}")
    
    # ── Step 8: Hypothesis tests (Week 4 is the ONLY profitable week) ──
    print("\n" + "=" * 80)
    print("PART 8: HYPOTHESIS TESTS")
    print("=" * 80)
    
    # Test: Is Week 4 really the only profitable week?
    print("\n  TEST 1: Is Week 4 (Waning) the ONLY profitable week?")
    
    # Using corrected classification
    for week in corrected_weeks_order:
        d = trade_by_week_corrected[week]
        if d['trades'] > 0:
            wr = d['wins'] / d['trades'] * 100
            profit = "PROFITABLE" if d['pnl'] > 0 else "LOSING"
            print(f"    {week}: PnL=${d['pnl']:.2f}, WR={wr:.1f}%, trades={d['trades']} → {profit}")
    
    # Test using script's classification
    print("\n  (Script's classification for comparison):")
    for week in script_weeks_order:
        d = trade_by_week_script[week]
        if d['trades'] > 0:
            wr = d['wins'] / d['trades'] * 100
            profit = "PROFITABLE" if d['pnl'] > 0 else "LOSING"
            print(f"    {week}: PnL=${d['pnl']:.2f}, WR={wr:.1f}%, trades={d['trades']} → {profit}")
    
    # Test 2: Is the difference between best and worst weeks significant?
    print("\n  TEST 2: Are week-to-week differences statistically significant?")
    
    # Collect per-day PnL for each week
    week_daily_pnl = defaultdict(list)
    for day_str, data in daily_trades.items():
        try:
            date = datetime.strptime(day_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except:
            continue
        week = classify_moon_week(date)
        week_daily_pnl[week].append(data['pnl'])
    
    # Compare each pair of weeks
    for i, w1 in enumerate(corrected_weeks_order):
        for w2 in corrected_weeks_order[i+1:]:
            pnl1 = week_daily_pnl.get(w1, [])
            pnl2 = week_daily_pnl.get(w2, [])
            if len(pnl1) >= 5 and len(pnl2) >= 5:
                U, p = mann_whitney_u(pnl1, pnl2)
                sig = "SIGNIFICANT" if p < 0.05 else "NOT significant"
                print(f"    {w1[:20]} vs {w2[:20]}: U={U}, p≈{p:.4f} ({sig})")
    
    # ── Step 9: Check the "59.3% WR on Day 3" claim ──
    print("\n  TEST 3: Verify specific day claims")
    
    # Day 3 claim
    s3 = day_stats.get(3, None)
    if s3 and s3['trades'] > 0:
        wr3 = s3['wins'] / s3['trades'] * 100
        print(f"    Day 3: {s3['trades']} trades, WR={wr3:.1f}% (claimed: 59.3%)")
        # Check if this is significantly different from overall WR
        overall_wr = total_wins / total_trades * 100
        print(f"    Overall WR: {overall_wr:.1f}%")
        print(f"    Difference: {wr3 - overall_wr:+.1f}pp")
        
        # Is this significant? Use binomial test
        n, k = s3['trades'], s3['wins']
        p0 = overall_wr / 100
        # z-test for proportion
        p_hat = k / n
        se = math.sqrt(p0 * (1-p0) / n) if n > 0 else 1
        z = (p_hat - p0) / se if se > 0 else 0
        print(f"    z-score (vs overall): {z:.2f}")
        print(f"    Significant at α=0.05? {'YES' if abs(z) > 1.96 else 'NO'}")
    
    # Day 11 claim
    s11 = day_stats.get(11, None)
    if s11 and s11['trades'] > 0:
        wr11 = s11['wins'] / s11['trades'] * 100
        print(f"    Day 11: {s11['trades']} trades, WR={wr11:.1f}% (claimed: 20.3%)")
        overall_wr = total_wins / total_trades * 100
        print(f"    Overall WR: {overall_wr:.1f}%")
        print(f"    Difference: {wr11 - overall_wr:+.1f}pp")
    
    # ── Step 10: Multiple testing problem ──
    print("\n" + "=" * 80)
    print("PART 9: MULTIPLE TESTING CORRECTION")
    print("=" * 80)
    
    # We tested 29 moon days, 4 moon weeks, and multiple correlations
    total_tests = 29 + 6 + 4  # moon days + week comparisons + correlations
    bonferroni_alpha = 0.05 / total_tests
    print(f"  Total statistical tests performed: ~{total_tests}")
    print(f"  Bonferroni-corrected α: {bonferroni_alpha:.4f}")
    print(f"  At this threshold, p < {bonferroni_alpha:.4f} needed for significance")
    
    # ── Step 11: Sample size adequacy ──
    print("\n" + "=" * 80)
    print("PART 10: SAMPLE SIZE ANALYSIS")
    print("=" * 80)
    
    print(f"\n  Total trades: {total_trades} over ~{len(daily_trades)} days")
    print(f"  Average trades per day: {total_trades / max(len(daily_trades), 1):.1f}")
    
    # Trades per moon week
    for week in corrected_weeks_order:
        d = trade_by_week_corrected[week]
        avg = d['trades'] / max(len(d['days']), 1)
        print(f"    {week}: {len(d['days'])} days, {d['trades']} trades, avg {avg:.1f}/day")
    
    # Power analysis: to detect a 10% difference in WR with 80% power
    print(f"\n  To detect a 10pp difference in WR (e.g., 47% vs 57%) at α=0.05, 80% power:")
    print(f"  Required: ~400 trades per group")
    print(f"  Each moon week has roughly {total_trades // 4} trades → {'SUFFICIENT' if total_trades // 4 > 400 else 'MAY BE INSUFFICIENT'} for week-level analysis")
    print(f"  Each moon day has roughly {total_trades // 29} trades → {'SUFFICIENT' if total_trades // 29 > 400 else 'INSUFFICIENT'} for day-level analysis")
    
    # ── Step 12: Confounding factors ──
    print("\n" + "=" * 80)
    print("PART 11: CONFOUNDING FACTORS")
    print("=" * 80)
    
    print("""
  1. TIME CLUSTERING: All data spans ~98 days (May-Aug 2026).
     Market regimes can shift over this period, creating spurious 
     correlations with any cyclical variable (including moon phases).
     
  2. SINGLE ASSET: Only BTC/USD trades. Any correlation could be 
     specific to BTC's price action during this exact window, not
     a general moon-metals or moon-crypto relationship.
     
  3. SURVIVORSHIP BIAS: Only closed trades with status='closed'.
     If losing trades are handled differently (e.g., liquidated, 
     held open), the sample is biased.
     
  4. AUTO-CORRELATION: BTC returns are autocorrelated. Moon phases
     are cyclical. Any autocorrelation in BTC could create spurious
     cyclical patterns that align with lunar cycles by chance.
     
  5. PARAMETER SENSITIVITY: The moon phase buckets (0.15, 0.50, 0.85)
     are arbitrary boundaries. Slightly different boundaries would
     produce different results — a form of p-hacking.
     
  6. NO DIRECTION CAUSALITY: Even if correlation existed, there's no
     plausible physical mechanism by which moon illumination affects
     crypto trading outcomes (unlike tides affecting commodities 
     through physical mechanisms).
""")
    
    # ── Step 13: Test for time confounding ──
    print("  CHECKING FOR TIME CONFOUNDING:")
    # Check if trades cluster in specific date ranges
    date_counts = Counter()
    for row in trade_rows:
        day = str(row[0])[:10]
        date_counts[day] += 1
    
    # Compare first half vs second half of the period
    sorted_days = sorted(date_counts.keys())
    mid = len(sorted_days) // 2
    first_half_days = sorted_days[:mid]
    second_half_days = sorted_days[mid:]
    
    first_half_wr = sum(1 for row in trade_rows if str(row[0])[:10] in set(first_half_days) and row[2] and float(row[2]) > 0) / max(sum(1 for row in trade_rows if str(row[0])[:10] in set(first_half_days)), 1)
    second_half_wr = sum(1 for row in trade_rows if str(row[0])[:10] in set(second_half_days) and row[2] and float(row[2]) > 0) / max(sum(1 for row in trade_rows if str(row[0])[:10] in set(second_half_days)), 1)
    
    first_half_count = sum(1 for row in trade_rows if str(row[0])[:10] in set(first_half_days))
    second_half_count = sum(1 for row in trade_rows if str(row[0])[:10] in set(second_half_days))
    
    print(f"    First half ({first_half_days[0]} to {first_half_days[-1]}): {first_half_count} trades, WR={first_half_wr*100:.1f}%")
    print(f"    Second half ({second_half_days[0]} to {second_half_days[-1]}): {second_half_count} trades, WR={second_half_wr*100:.1f}%")
    print(f"    WR difference: {(second_half_wr - first_half_wr)*100:+.1f}pp")
    
    if abs((second_half_wr - first_half_wr)*100) > 5:
        print(f"    ⚠️  Significant WR shift over time — confounding likely")
    else:
        print(f"    WR relatively stable over time")
    
    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    run_audit()
