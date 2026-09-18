#!/usr/bin/env python3
"""
Linreg MA180 Filter Analysis
=============================
For every closed trade, calculates the linear regression slope of the 1m MA180
at trade entry time. Measures correlation between slope alignment (trade direction
matching slope direction) and trade outcome (win/loss, PnL).

Results stored in: /root/.hermes/data/linreg_ma180_analysis.db

Usage:
    python3 scripts/analysis/linreg_ma180_analysis.py
    python3 scripts/analysis/linreg_ma180_analysis.py --report   # Just print report from existing DB
"""

import sys, os, sqlite3, json, time
from datetime import datetime, timezone
from collections import defaultdict
import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)

from _secrets import BRAIN_DB_DICT

# ── Config ──────────────────────────────────────────────────────────────
CANDLES_DB = '/root/.hermes/data/candles.db'
ANALYSIS_DB = '/root/.hermes/data/linreg_ma180_analysis.db'

# How many 1m candles to look at BEFORE entry for MA180 calc + linreg
# MA180 needs 180 candles, then linreg needs its own window
MA_PERIOD = 180          # 180 * 1m = 3 hours
LINREG_WINDOWS = [30, 60, 90, 120]  # Slope measured over these windows of MA180 values
ALIGNMENT_THRESHOLD = 0.0  # Slope must exceed this to count as "aligned" (0 = any nonzero)

# ── Schema ──────────────────────────────────────────────────────────────
ANALYSIS_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_linreg (
    trade_id INTEGER PRIMARY KEY,
    token TEXT,
    direction TEXT,
    entry_time TEXT,
    entry_price REAL,
    pnl_usdt REAL,
    pnl_pct REAL,
    signal TEXT,
    is_win INTEGER,             -- 1 = win, 0 = loss/breakeven
    
    -- MA180 value at entry
    ma180_at_entry REAL,
    
    -- Linreg slope for each window (per 1-candle unit, normalized)
    slope_30 REAL,              -- Slope of MA180 over last 30 candles
    slope_60 REAL,              -- Slope of MA180 over last 60 candles
    slope_90 REAL,              -- Slope of MA180 over last 90 candles
    slope_120 REAL,             -- Slope of MA180 over last 120 candles
    
    -- Alignment: does slope direction match trade direction?
    aligned_30 INTEGER,         -- 1 if LONG + slope > 0, or SHORT + slope < 0
    aligned_60 INTEGER,
    aligned_90 INTEGER,
    aligned_120 INTEGER,
    
    -- Slope as % of price (normalized slope)
    slope_pct_30 REAL,
    slope_pct_60 REAL,
    slope_pct_90 REAL,
    slope_pct_120 REAL,
    
    -- Price relative to MA180
    price_vs_ma180 REAL,        -- (entry_price - ma180) / ma180 * 100
    
    -- Candles available for analysis
    candles_available INTEGER,
    
    -- Metadata
    analyzed_at TEXT
);

CREATE TABLE IF NOT EXISTS analysis_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_time TEXT,
    total_trades INTEGER,
    trades_analyzed INTEGER,
    trades_skipped INTEGER,
    results_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_trade_linreg_token ON trade_linreg(token);
CREATE INDEX IF NOT EXISTS idx_trade_linreg_direction ON trade_linreg(direction);
CREATE INDEX IF NOT EXISTS idx_trade_linreg_is_win ON trade_linreg(is_win);
"""


def create_analysis_db():
    """Create the analysis database."""
    conn = sqlite3.connect(ANALYSIS_DB)
    conn.executescript(ANALYSIS_SCHEMA)
    conn.commit()
    conn.close()
    print(f"Created analysis DB: {ANALYSIS_DB}")


def get_all_trades():
    """Get all closed trades from PostgreSQL."""
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
               open_time, close_time, signal, volatility_regime
        FROM trades
        WHERE status = 'closed' 
          AND open_time IS NOT NULL
          AND token IS NOT NULL
          AND direction IS NOT NULL
        ORDER BY open_time
    """)
    
    trades = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    
    return trades, cols


def get_1m_candles(token, entry_ts, lookback=400):
    """
    Get 1m candles for a token ending at entry_ts.
    Returns list of (ts, close) tuples, oldest first.
    lookback: how many candles before entry to fetch (needs MA_PERIOD + linreg window + buffer)
    """
    conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=10)
    cur = conn.cursor()
    
    # entry_ts is a datetime object
    entry_epoch = int(entry_ts.replace(tzinfo=timezone.utc).timestamp()) if entry_ts.tzinfo is None else int(entry_ts.timestamp())
    start_epoch = entry_epoch - (lookback * 60) - 60  # 60s buffer
    
    cur.execute("""
        SELECT ts, close FROM candles_1m
        WHERE token = ? AND ts >= ? AND ts <= ?
        ORDER BY ts ASC
    """, (token, start_epoch, entry_epoch))
    
    candles = cur.fetchall()
    cur.close()
    conn.close()
    
    return candles


def compute_ma(values, period):
    """Compute simple moving average."""
    if len(values) < period:
        return [None] * len(values)
    
    ma = []
    for i in range(len(values)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(values[i - period + 1:i + 1]) / period)
    return ma


def compute_linreg_slope(values):
    """
    Compute linear regression slope of non-None values.
    Returns slope per unit (i.e., slope in value per candle).
    """
    # Filter out None values
    valid = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(valid) < 10:  # Need at least 10 points
        return None
    
    indices = np.array([v[0] for v in valid], dtype=float)
    vals = np.array([v[1] for v in valid], dtype=float)
    
    # numpy polyfit: slope = m, intercept = b
    # We want slope normalized by the mean value to get % per candle
    try:
        m, b = np.polyfit(indices, vals, 1)
        mean_val = np.mean(vals)
        if mean_val == 0:
            return None
        # Return slope as % per candle (normalized)
        return m / mean_val * 100  # % per candle
    except:
        return None


def analyze_trade(trade_row, cols):
    """Analyze one trade's MA180 slope at entry time."""
    trade = dict(zip(cols, trade_row))
    
    token = trade['token']
    direction = trade['direction']
    entry_time = trade['open_time']
    entry_price = float(trade['entry_price']) if trade['entry_price'] else None
    pnl_usdt = float(trade['pnl_usdt']) if trade['pnl_usdt'] else 0
    pnl_pct = float(trade['pnl_pct']) if trade['pnl_pct'] else 0
    
    if not entry_time or not entry_price or not direction:
        return None
    
    # Get 1m candles
    candles = get_1m_candles(token, entry_time, lookback=MA_PERIOD + max(LINREG_WINDOWS) + 50)
    
    if len(candles) < MA_PERIOD + 10:
        return None  # Not enough data
    
    # Extract close prices
    closes = [c[1] for c in candles]
    
    # Compute MA180
    ma180 = compute_ma(closes, MA_PERIOD)
    
    # Get MA180 value at entry (last valid)
    ma180_at_entry = ma180[-1] if ma180[-1] is not None else None
    if ma180_at_entry is None:
        return None
    
    # Price vs MA180
    price_vs_ma180 = (entry_price - ma180_at_entry) / ma180_at_entry * 100
    
    result = {
        'trade_id': trade['id'],
        'token': token,
        'direction': direction,
        'entry_time': str(entry_time),
        'entry_price': entry_price,
        'pnl_usdt': pnl_usdt,
        'pnl_pct': pnl_pct,
        'signal': trade.get('signal', ''),
        'is_win': 1 if pnl_usdt > 0 else 0,
        'ma180_at_entry': ma180_at_entry,
        'price_vs_ma180': price_vs_ma180,
        'candles_available': len(candles),
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }
    
    # Compute slope for each window
    for w in LINREG_WINDOWS:
        slope = compute_linreg_slope(ma180[-w:])
        result[f'slope_{w}'] = slope
        
        if slope is not None:
            # Alignment: LONG needs slope > 0, SHORT needs slope < 0
            if direction == 'LONG':
                result[f'aligned_{w}'] = 1 if slope > ALIGNMENT_THRESHOLD else 0
            else:
                result[f'aligned_{w}'] = 1 if slope < -ALIGNMENT_THRESHOLD else 0
            result[f'slope_pct_{w}'] = slope
        else:
            result[f'slope_{w}'] = None
            result[f'aligned_{w}'] = None
            result[f'slope_pct_{w}'] = None
    
    return result


def run_analysis():
    """Main analysis pipeline."""
    create_analysis_db()
    
    print("Fetching all trades from PostgreSQL...")
    trades, cols = get_all_trades()
    print(f"Found {len(trades)} closed trades")
    
    # Check if we already have results
    existing = sqlite3.connect(ANALYSIS_DB)
    cur = existing.cursor()
    cur.execute("SELECT COUNT(*) FROM trade_linreg")
    existing_count = cur.fetchone()[0]
    cur.close()
    existing.close()
    
    if existing_count > 0:
        print(f"Found {existing_count} existing results. Clearing and re-running...")
        existing = sqlite3.connect(ANALYSIS_DB)
        existing.execute("DELETE FROM trade_linreg")
        existing.execute("DELETE FROM analysis_summary")
        existing.commit()
        existing.close()
    
    analyzed = 0
    skipped = 0
    results = []
    
    print("Analyzing trades...")
    start_time = time.time()
    
    for i, trade_row in enumerate(trades):
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(trades) - i - 1) / rate if rate > 0 else 0
            print(f"  {i+1}/{len(trades)} analyzed ({analyzed} success, {skipped} skipped) "
                  f"[{rate:.0f}/s, ETA {eta:.0f}s]")
        
        result = analyze_trade(trade_row, cols)
        if result:
            results.append(result)
            analyzed += 1
        else:
            skipped += 1
    
    elapsed = time.time() - start_time
    print(f"\nAnalysis complete: {analyzed} analyzed, {skipped} skipped in {elapsed:.1f}s")
    
    # Store results
    if results:
        db = sqlite3.connect(ANALYSIS_DB)
        cur = db.cursor()
        
        # Insert results
        first = results[0]
        cols_list = list(first.keys())
        placeholders = ','.join(['?'] * len(cols_list))
        insert_sql = f"INSERT INTO trade_linreg ({','.join(cols_list)}) VALUES ({placeholders})"
        
        for r in results:
            values = [r[c] for c in cols_list]
            cur.execute(insert_sql, values)
        
        db.commit()
        cur.close()
        db.close()
        print(f"Stored {len(results)} results in {ANALYSIS_DB}")
    
    # Generate summary
    generate_report(results)


def generate_report(results=None):
    """Generate analysis report from stored data."""
    db = sqlite3.connect(ANALYSIS_DB)
    cur = db.cursor()
    
    if results is None:
        cur.execute("SELECT * FROM trade_linreg")
        # Get column names
        col_names = [d[0] for d in cur.description]
        rows = cur.fetchall()
        results = [dict(zip(col_names, r)) for r in rows]
    
    if not results:
        print("No results to report.")
        db.close()
        return
    
    print("\n" + "="*80)
    print("LINREG MA180 FILTER ANALYSIS REPORT")
    print("="*80)
    print(f"Total analyzed: {len(results)}")
    
    # Overall win rates
    wins = [r for r in results if r['is_win'] == 1]
    losses = [r for r in results if r['is_win'] == 0]
    total_pnl = sum(r['pnl_usdt'] for r in results)
    print(f"Wins: {len(wins)} ({len(wins)/len(results)*100:.1f}%)")
    print(f"Losses: {len(losses)} ({len(losses)/len(results)*100:.1f}%)")
    print(f"Total PnL: ${total_pnl:.2f}")
    
    # Per-direction
    for direction in ['LONG', 'SHORT']:
        dir_trades = [r for r in results if r['direction'] == direction]
        if not dir_trades:
            continue
        dir_wins = [r for r in dir_trades if r['is_win'] == 1]
        dir_pnl = sum(r['pnl_usdt'] for r in dir_trades)
        print(f"\n{direction}: {len(dir_trades)} trades, {len(dir_wins)} wins "
              f"({len(dir_wins)/len(dir_trades)*100:.1f}%), PnL: ${dir_pnl:.2f}")
    
    # ── ALIGNED vs NOT ALIGNED for each window ──
    print("\n" + "-"*80)
    print("ALIGNED vs NON-ALIGNED PERFORMANCE")
    print("-"*80)
    
    for w in LINREG_WINDOWS:
        aligned_col = f'aligned_{w}'
        slope_col = f'slope_pct_{w}'
        
        aligned = [r for r in results if r[aligned_col] == 1]
        not_aligned = [r for r in results if r[aligned_col] == 0]
        no_data = [r for r in results if r[aligned_col] is None]
        
        if not aligned and not not_aligned:
            continue
        
        print(f"\n  Window: {w} candles ({w} minutes)")
        print(f"  Aligned: {len(aligned)}, Not aligned: {len(not_aligned)}, No data: {len(no_data)}")
        
        if aligned:
            a_wins = len([r for r in aligned if r['is_win'] == 1])
            a_pnl = sum(r['pnl_usdt'] for r in aligned)
            a_avg_pnl = a_pnl / len(aligned)
            print(f"  ALIGNED:     {len(aligned)} trades, {a_wins} wins "
                  f"({a_wins/len(aligned)*100:.1f}%), Avg PnL: ${a_avg_pnl:.3f}, Total: ${a_pnl:.2f}")
        
        if not_aligned:
            na_wins = len([r for r in not_aligned if r['is_win'] == 1])
            na_pnl = sum(r['pnl_usdt'] for r in not_aligned)
            na_avg_pnl = na_pnl / len(not_aligned)
            print(f"  NOT ALIGNED: {len(not_aligned)} trades, {na_wins} wins "
                  f"({na_wins/len(not_aligned)*100:.1f}%), Avg PnL: ${na_avg_pnl:.3f}, Total: ${na_pnl:.2f}")
        
        if aligned and not_aligned:
            # Edge calculation
            edge_wr = a_wins/len(aligned)*100 - na_wins/len(not_aligned)*100
            edge_pnl = a_avg_pnl - na_avg_pnl
            print(f"  EDGE:        +{edge_wr:.1f}% WR, +${edge_pnl:.3f} avg PnL")
    
    # ── Per-direction aligned analysis ──
    print("\n" + "-"*80)
    print("ALIGNED vs NON-ALIGNED BY DIRECTION (best window: 60)")
    print("-"*80)
    
    for direction in ['LONG', 'SHORT']:
        dir_trades = [r for r in results if r['direction'] == direction]
        aligned = [r for r in dir_trades if r['aligned_60'] == 1]
        not_aligned = [r for r in dir_trades if r['aligned_60'] == 0]
        
        print(f"\n  {direction}:")
        if aligned:
            a_wins = len([r for r in aligned if r['is_win'] == 1])
            a_pnl = sum(r['pnl_usdt'] for r in aligned)
            print(f"    ALIGNED:     {len(aligned)} trades, {a_wins} wins "
                  f"({a_wins/len(aligned)*100:.1f}%), Total: ${a_pnl:.2f}")
        if not_aligned:
            na_wins = len([r for r in not_aligned if r['is_win'] == 1])
            na_pnl = sum(r['pnl_usdt'] for r in not_aligned)
            print(f"    NOT ALIGNED: {len(not_aligned)} trades, {na_wins} wins "
                  f"({na_wins/len(not_aligned)*100:.1f}%), Total: ${na_pnl:.2f}")
    
    # ── Slope magnitude buckets ──
    print("\n" + "-"*80)
    print("SLOPE MAGNITUDE vs WIN RATE (60-candle window)")
    print("-"*80)
    
    # Bucket slopes
    buckets = [
        ("Strong DOWN  (<-0.05%)", lambda s: s is not None and s < -0.05),
        ("Mild DOWN    (-0.05 to -0.02%)", lambda s: s is not None and -0.05 <= s < -0.02),
        ("Flat/Slight  (-0.02 to +0.02%)", lambda s: s is not None and -0.02 <= s <= 0.02),
        ("Mild UP      (+0.02 to +0.05%)", lambda s: s is not None and 0.02 < s <= 0.05),
        ("Strong UP    (>+0.05%)", lambda s: s is not None and s > 0.05),
    ]
    
    for label, bucket_fn in buckets:
        bucket = [r for r in results if bucket_fn(r['slope_pct_60'])]
        if not bucket:
            print(f"  {label}: 0 trades")
            continue
        b_wins = len([r for r in bucket if r['is_win'] == 1])
        b_pnl = sum(r['pnl_usdt'] for r in bucket)
        b_avg = b_pnl / len(bucket)
        
        # Split by direction
        longs = [r for r in bucket if r['direction'] == 'LONG']
        shorts = [r for r in bucket if r['direction'] == 'SHORT']
        
        l_info = ""
        s_info = ""
        if longs:
            l_wins = len([r for r in longs if r['is_win'] == 1])
            l_info = f"  LONG: {len(longs)}T/{l_wins}W ({l_wins/len(longs)*100:.0f}%)"
        if shorts:
            s_wins = len([r for r in shorts if r['is_win'] == 1])
            s_info = f"  SHORT: {len(shorts)}T/{s_wins}W ({s_wins/len(shorts)*100:.0f}%)"
        
        print(f"  {label}: {len(bucket)}T, {b_wins}W ({b_wins/len(bucket)*100:.1f}%), "
              f"Avg: ${b_avg:.3f}, Total: ${b_pnl:.2f}")
        if l_info:
            print(f"    {l_info}")
        if s_info:
            print(f"    {s_info}")
    
    # ── Price vs MA180 position ──
    print("\n" + "-"*80)
    print("PRICE vs MA180 POSITION at entry")
    print("-"*80)
    
    pos_buckets = [
        ("Well above MA180 (>+1%)", lambda p: p is not None and p > 1.0),
        ("Above MA180 (+0.2% to +1%)", lambda p: p is not None and 0.2 < p <= 1.0),
        ("Near MA180 (-0.2% to +0.2%)", lambda p: p is not None and -0.2 <= p <= 0.2),
        ("Below MA180 (-1% to -0.2%)", lambda p: p is not None and -1.0 <= p < -0.2),
        ("Well below MA180 (<-1%)", lambda p: p is not None and p < -1.0),
    ]
    
    for label, bucket_fn in pos_buckets:
        bucket = [r for r in results if bucket_fn(r['price_vs_ma180'])]
        if not bucket:
            print(f"  {label}: 0 trades")
            continue
        b_wins = len([r for r in bucket if r['is_win'] == 1])
        b_pnl = sum(r['pnl_usdt'] for r in bucket)
        print(f"  {label}: {len(bucket)}T, {b_wins}W ({b_wins/len(bucket)*100:.1f}%), Total: ${b_pnl:.2f}")
    
    # ── Save summary ──
    summary = {
        'total': len(results),
        'wins': len(wins),
        'overall_wr': len(wins)/len(results)*100,
        'total_pnl': total_pnl,
    }
    
    db.execute("""
        INSERT INTO analysis_summary (run_time, total_trades, trades_analyzed, trades_skipped, results_json)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now(timezone.utc).isoformat(), len(results), len(results), 0, json.dumps(summary)))
    db.commit()
    db.close()
    
    print("\n" + "="*80)
    print("Done. Results stored in:", ANALYSIS_DB)
    print("="*80)


if __name__ == '__main__':
    if '--report' in sys.argv:
        generate_report()
    else:
        run_analysis()
