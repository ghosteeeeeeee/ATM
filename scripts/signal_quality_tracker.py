#!/usr/bin/env python3
"""
Signal Quality Tracker — evaluates whether signals correctly predict price direction.

Usage:
  python3 signal_quality_tracker.py --run          # Main loop: poll every 5min for 2h
  python3 signal_quality_tracker.py --eval         # Evaluate expired signals (>2h old)
  python3 signal_quality_tracker.py --report       # Generate final report
  python3 signal_quality_tracker.py --status       # Show current tracking stats
"""

import sys, os, json, time, sqlite3, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# ── Config ────────────────────────────────────────────────────────────────────
TRACKER_DIR = Path(HERMES_DATA) / 'signal_quality'
TRACKER_DIR.mkdir(parents=True, exist_ok=True)
TRACKED_FILE = TRACKER_DIR / 'tracked_signals.json'
RESULTS_FILE = TRACKER_DIR / 'results.json'
REPORT_FILE = TRACKER_DIR / 'signal_quality_report.md'
SIGNALS_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')

POLL_INTERVAL_S = 300   # 5 minutes
HOLD_PERIOD_S = 7200    # 2 hours
EVAL_WINDOW_S = 7200    # 2 hours after signal to evaluate

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc)

def _load_tracked():
    if TRACKED_FILE.exists():
        with open(TRACKED_FILE) as f:
            return json.load(f)
    return {'signals': {}, 'last_poll': None}

def _save_tracked(data):
    with open(TRACKED_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def _load_results():
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {'completed': [], 'stats': {}}

def _save_results(data):
    with open(RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def _get_current_price(token):
    """Get latest price for a token from price_history."""
    try:
        conn = sqlite3.connect(PRICE_DB)
        cur = conn.cursor()
        cur.execute(
            "SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1",
            (token,)
        )
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None

def _get_recent_signals(since_minutes=5):
    """Get signals from the last N minutes."""
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction, source, confidence, created_at, z_score
            FROM signals
            WHERE created_at > datetime('now', '-' || ? || ' minutes')
            ORDER BY created_at DESC
        """, (since_minutes,))
        rows = cur.fetchall()
        conn.close()
        results = []
        for row in rows:
            results.append({
                'token': row[0],
                'direction': row[1],
                'source': row[2],
                'confidence': row[3],
                'created_at': row[4],
                'z_score': row[5],
            })
        return results
    except Exception as e:
        print(f"Error reading signals: {e}")
        return []

def _get_entry_price(token, signal_time):
    """Get price closest to signal time."""
    try:
        conn = sqlite3.connect(PRICE_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT price FROM price_history 
            WHERE token=? AND timestamp <= ? 
            ORDER BY timestamp DESC LIMIT 1
        """, (token, signal_time))
        row = cur.fetchone()
        if row:
            conn.close()
            return float(row[0])
        # Fallback: get latest price
        cur.execute("""
            SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1
        """, (token,))
        row = cur.fetchone()
        conn.close()
        return float(row[0]) if row else None
    except Exception:
        return None

def _signal_type_key(part):
    """Normalize signal source to type (same as signal_compactor.py)."""
    import re
    part = re.sub(r'-broken$', '', part)
    part = re.sub(r'^rs-[sr]', 'rs', part)
    return re.sub(r'\d+$', '', part) or part

# ── Core Logic ────────────────────────────────────────────────────────────────

def poll_signals():
    """Poll for new signals and start tracking them."""
    tracked = _load_tracked()
    now = _now()
    since = tracked.get('last_poll', (now - timedelta(seconds=POLL_INTERVAL_S)).isoformat())
    
    signals = _get_recent_signals(since_minutes=10)  # look back 10min to catch all
    
    new_count = 0
    for sig in signals:
        key = f"{sig['token']}_{sig['direction']}_{sig['source']}_{sig['created_at']}"
        if key in tracked['signals']:
            continue
        
        # Get entry price
        entry_price = _get_entry_price(sig['token'], sig['created_at'])
        if not entry_price:
            continue
        
        # Normalize source to signal type
        source_parts = [p.strip() for p in sig['source'].split(',') if p.strip()]
        signal_types = list(set(_signal_type_key(p) for p in source_parts))
        
        tracked['signals'][key] = {
            'token': sig['token'],
            'direction': sig['direction'],
            'source': sig['source'],
            'signal_types': signal_types,
            'confidence': sig['confidence'],
            'z_score': sig.get('z_score'),
            'created_at': sig['created_at'],
            'entry_price': entry_price,
            'entry_time': now.isoformat(),
            'status': 'tracking',  # tracking, win, loss, expired
            'current_price': entry_price,
            'price_history': [{'time': now.isoformat(), 'price': entry_price}],
        }
        new_count += 1
    
    tracked['last_poll'] = now.isoformat()
    _save_tracked(tracked)
    return new_count

def evaluate_expired():
    """Evaluate signals that are past the hold period."""
    tracked = _load_tracked()
    results = _load_results()
    now = _now()
    
    evaluated = 0
    for key, sig in tracked['signals'].items():
        if sig['status'] != 'tracking':
            continue
        
        entry_time = datetime.fromisoformat(sig['entry_time'])
        if (now - entry_time).total_seconds() < EVAL_WINDOW_S:
            continue
        
        # Get final price
        final_price = _get_current_price(sig['token'])
        if not final_price:
            final_price = sig.get('current_price', sig['entry_price'])
        
        # Determine win/loss
        entry = sig['entry_price']
        direction = sig['direction']
        
        if direction == 'LONG':
            won = final_price > entry
        else:  # SHORT
            won = final_price < entry
        
        pnl_pct = ((final_price - entry) / entry * 100) if direction == 'LONG' else ((entry - final_price) / entry * 100)
        
        sig['status'] = 'win' if won else 'loss'
        sig['final_price'] = final_price
        sig['pnl_pct'] = round(pnl_pct, 4)
        sig['evaluated_at'] = now.isoformat()
        
        # Add to results
        results['completed'].append({
            'token': sig['token'],
            'direction': sig['direction'],
            'source': sig['source'],
            'signal_types': sig['signal_types'],
            'confidence': sig['confidence'],
            'entry_price': entry,
            'entry_time': sig['entry_time'],
            'final_price': final_price,
            'pnl_pct': round(pnl_pct, 4),
            'won': won,
            'evaluated_at': now.isoformat(),
        })
        
        evaluated += 1
    
    # Update stats
    completed = results['completed']
    if completed:
        total = len(completed)
        wins = sum(1 for c in completed if c['won'])
        results['stats'] = {
            'total': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': round(wins / total * 100, 1) if total > 0 else 0,
            'avg_pnl_pct': round(sum(c['pnl_pct'] for c in completed) / total, 4),
            'last_updated': now.isoformat(),
        }
    
    _save_tracked(tracked)
    _save_results(results)
    return evaluated

def update_prices():
    """Update current prices for all tracked signals."""
    tracked = _load_tracked()
    now = _now()
    updated = 0
    
    for key, sig in tracked['signals'].items():
        if sig['status'] != 'tracking':
            continue
        
        price = _get_current_price(sig['token'])
        if price:
            sig['current_price'] = price
            sig['price_history'].append({'time': now.isoformat(), 'price': price})
            # Keep only last 24 price points (2h at 5min intervals)
            if len(sig['price_history']) > 24:
                sig['price_history'] = sig['price_history'][-24:]
            updated += 1
    
    _save_tracked(tracked)
    return updated

def generate_report():
    """Generate markdown report and summary stats."""
    results = _load_results()
    tracked = _load_tracked()
    now = _now()
    
    completed = results['completed']
    if not completed:
        print("No completed evaluations yet.")
        return
    
    # Overall stats
    total = len(completed)
    wins = sum(1 for c in completed if c['won'])
    win_rate = round(wins / total * 100, 1) if total > 0 else 0
    
    # By signal type
    by_type = {}
    for c in completed:
        for st in c['signal_types']:
            if st not in by_type:
                by_type[st] = {'total': 0, 'wins': 0}
            by_type[st]['total'] += 1
            if c['won']:
                by_type[st]['wins'] += 1
    
    # By direction
    by_dir = {'LONG': {'total': 0, 'wins': 0}, 'SHORT': {'total': 0, 'wins': 0}}
    for c in completed:
        d = c['direction']
        by_dir[d]['total'] += 1
        if c['won']:
            by_dir[d]['wins'] += 1
    
    # By confidence bucket
    by_conf = {'high': {'total': 0, 'wins': 0}, 'mid': {'total': 0, 'wins': 0}, 'low': {'total': 0, 'wins': 0}}
    for c in completed:
        conf = c.get('confidence', 0) or 0
        if conf >= 80:
            bucket = 'high'
        elif conf >= 65:
            bucket = 'mid'
        else:
            bucket = 'low'
        by_conf[bucket]['total'] += 1
        if c['won']:
            by_conf[bucket]['wins'] += 1
    
    # By source
    by_source = {}
    for c in completed:
        src = c['source'].split(',')[0].rsplit('-', 1)[0] if '-' in c['source'] else c['source']
        if src not in by_source:
            by_source[src] = {'total': 0, 'wins': 0}
        by_source[src]['total'] += 1
        if c['won']:
            by_source[src]['wins'] += 1
    
    # Generate report
    report = f"""# Signal Quality Report
Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Overall
| Metric | Value |
|--------|-------|
| Total signals evaluated | {total} |
| Wins | {wins} |
| Losses | {total - wins} |
| **Win Rate** | **{win_rate}%** |
| Avg PnL | {results['stats'].get('avg_pnl_pct', 0):.4f}% |

## By Signal Type
| Type | Total | Wins | Win Rate |
|------|-------|------|----------|
"""
    for st, data in sorted(by_type.items(), key=lambda x: x[1]['total'], reverse=True):
        wr = round(data['wins'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        report += f"| {st} | {data['total']} | {data['wins']} | {wr}% |\n"
    
    report += f"""
## By Direction
| Direction | Total | Wins | Win Rate |
|-----------|-------|------|----------|
"""
    for d, data in by_dir.items():
        wr = round(data['wins'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        report += f"| {d} | {data['total']} | {data['wins']} | {wr}% |\n"
    
    report += f"""
## By Confidence
| Bucket | Total | Wins | Win Rate |
|--------|-------|------|----------|
"""
    for b, data in by_conf.items():
        wr = round(data['wins'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        report += f"| {b} | {data['total']} | {data['wins']} | {wr}% |\n"
    
    report += f"""
## By Source
| Source | Total | Wins | Win Rate |
|--------|-------|------|----------|
"""
    for s, data in sorted(by_source.items(), key=lambda x: x[1]['total'], reverse=True):
        wr = round(data['wins'] / data['total'] * 100, 1) if data['total'] > 0 else 0
        report += f"| {s} | {data['total']} | {data['wins']} | {wr}% |\n"
    
    report += f"""
## Recent Results (last 20)
| Token | Dir | Source | Conf | Entry | Exit | PnL | Result |
|-------|-----|--------|------|-------|------|-----|--------|
"""
    for c in completed[-20:]:
        result = "WIN" if c['won'] else "LOSS"
        report += f"| {c['token']} | {c['direction']} | {c['source'][:20]} | {c.get('confidence', 0):.0f}% | {c['entry_price']:.4f} | {c['final_price']:.4f} | {c['pnl_pct']:+.4f}% | {result} |\n"
    
    with open(REPORT_FILE, 'w') as f:
        f.write(report)
    
    print(f"Report written to {REPORT_FILE}")
    print(f"Win rate: {win_rate}% ({wins}/{total})")
    return win_rate

def show_status():
    """Show current tracking status."""
    tracked = _load_tracked()
    results = _load_results()
    now = _now()
    
    tracking = sum(1 for s in tracked['signals'].values() if s['status'] == 'tracking')
    completed = len(results['completed'])
    wins = sum(1 for c in results['completed'] if c['won'])
    win_rate = round(wins / completed * 100, 1) if completed > 0 else 0
    
    print(f"Tracking: {tracking} signals")
    print(f"Completed: {completed} (win rate: {win_rate}%)")
    print(f"Last poll: {tracked.get('last_poll', 'never')}")
    
    # Show some tracked signals
    if tracking > 0:
        print(f"\nSample tracked signals:")
        count = 0
        for key, sig in tracked['signals'].items():
            if sig['status'] == 'tracking' and count < 5:
                entry_time = datetime.fromisoformat(sig['entry_time'])
                age_min = (now - entry_time).total_seconds() / 60
                pnl = ((sig['current_price'] - sig['entry_price']) / sig['entry_price'] * 100) if sig['direction'] == 'LONG' else ((sig['entry_price'] - sig['current_price']) / sig['entry_price'] * 100)
                print(f"  {sig['token']} {sig['direction']} src={sig['source'][:20]} conf={sig.get('confidence', 0):.0f}% age={age_min:.0f}m pnl={pnl:+.4f}%")
                count += 1

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Signal Quality Tracker')
    parser.add_argument('--run', action='store_true', help='Run the polling loop')
    parser.add_argument('--eval', action='store_true', help='Evaluate expired signals')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--once', action='store_true', help='Run one poll cycle')
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.eval:
        n = evaluate_expired()
        print(f"Evaluated {n} signals")
    elif args.report:
        generate_report()
    elif args.once:
        new = poll_signals()
        updated = update_prices()
        evald = evaluate_expired()
        print(f"Poll: {new} new, {updated} price updates, {evald} evaluated")
    elif args.run:
        print(f"Starting signal quality tracker (poll every {POLL_INTERVAL_S}s, hold {HOLD_PERIOD_S}s)")
        start = _now()
        end = start + timedelta(hours=2)
        
        while _now() < end:
            new = poll_signals()
            updated = update_prices()
            evald = evaluate_expired()
            remaining = (end - _now()).total_seconds() / 60
            print(f"[{_now().strftime('%H:%M')}] Poll: {new} new, {updated} prices, {evald} eval — {remaining:.0f}min remaining")
            time.sleep(POLL_INTERVAL_S)
        
        # Final evaluation
        evaluate_expired()
        generate_report()
        show_status()
        print("\n=== TRACKING COMPLETE ===")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
