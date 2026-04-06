#!/usr/bin/env python3
"""
New Trade Rule Checker — runs after decider-run to validate new trades against
the post-mortem signal quality rules.

Fails a trade if:
  1. Counter-regime (LONG_BIAS + SHORT, or SHORT_BIAS + LONG) — hard block
  2. NEUTRAL regime conf > 60% — should WAIT
  3. Token not in regime_4h.json (regime blindspot) — flag for review
  4. z_tier contradicts direction (falling z + SHORT is fine, but check context)

Usage: python3 check_new_trades.py
       python3 check_new_trades.py --watch  (continuous every 60s)
       python3 check_new_trades.py --trade-id 4237  (check specific trade)
"""
import sys, json, sqlite3, argparse
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2

BRAIN_DB_DICT = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}
SIGNAL_DB = '/root/.hermes/data/signals_hermes_runtime.db'
REGIME_JSON = '/var/www/html/regime_4h.json'

def load_regimes():
    try:
        with open(REGIME_JSON) as f:
            d = json.load(f)
            return {k: v for k, v in d.get('regimes', {}).items()}
    except Exception as e:
        print(f"[WARN] Could not load {REGIME_JSON}: {e}")
        return {}

def get_open_trades(since_minutes=15):
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, pnl_pct, status,
               open_time::text, regime, entry_regime_4h
        FROM trades
        WHERE status = 'open'
        AND open_time > NOW() - INTERVAL '%s minutes'
        ORDER BY open_time DESC
    """, (since_minutes,))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    return [dict(zip(cols, r)) for r in rows]

def get_signal_for_trade(token):
    sc = sqlite3.connect(SIGNAL_DB)
    cur = sc.cursor()
    cur.execute("""
        SELECT source, signal_type, direction, confidence, z_score, z_score_tier, rsi_14
        FROM signals
        WHERE token = ?
        AND executed = 1
        ORDER BY updated_at DESC
        LIMIT 1
    """, (token,))
    row = cur.fetchone()
    sc.close()
    if row:
        return {
            'source': row[0], 'signal_type': row[1], 'direction': row[2],
            'confidence': row[3], 'z_score': row[4], 'z_score_tier': row[5], 'rsi_14': row[6]
        }
    return None

def check_trade(trade, regimes):
    token = trade['token']
    direction = trade['direction']
    regime_data = regimes.get(token.upper(), {})
    
    regime_str = regime_data.get('regime', 'NEUTRAL')
    regime_conf = regime_data.get('confidence', 0)
    regime_label = f"{regime_str}@{regime_conf:.0f}%" if regime_data else 'NOT_IN_JSON'
    
    issues = []
    severity = 'PASS'
    
    # Rule 1: Regime hard block
    if not regime_data:
        issues.append(f"regime_blindspot: {token} not in regime_4h.json")
        severity = 'FAIL'
    elif regime_str in ('LONG_BIAS', 'SHORT_BIAS') and regime_conf >= 50:
        if (regime_str == 'LONG_BIAS' and direction == 'SHORT') or \
           (regime_str == 'SHORT_BIAS' and direction == 'LONG'):
            issues.append(f"counter-regime: {regime_label} but trade is {direction}")
            severity = 'FAIL'
        else:
            issues.append(f"regime_ok: {regime_label} aligns with {direction}")
    elif regime_str == 'NEUTRAL' and regime_conf > 60:
        issues.append(f"neutral_high_conf: {regime_label} — should WAIT")
        severity = 'WARN'
    elif regime_str == 'NEUTRAL' and regime_conf <= 60:
        issues.append(f"neutral_low_conf: {regime_label} — borderline")
        severity = 'WARN'
    
    # Rule 2: z_tier check
    signal = get_signal_for_trade(token)
    if signal and signal['z_score_tier']:
        z_tier = signal['z_score_tier']
        z = signal['z_score']
        if z_tier == 'falling' and direction == 'LONG':
            issues.append(f"z_tier_warn: {direction} but z_tier={z_tier} (z={z})")
            severity = max(severity, 'WARN')
        elif z_tier == 'rising' and direction == 'SHORT':
            issues.append(f"z_tier_warn: {direction} but z_tier={z_tier} (z={z})")
            severity = max(severity, 'WARN')
    
    return {
        'token': token,
        'trade_id': trade['id'],
        'direction': direction,
        'entry': trade['entry_price'],
        'regime': regime_label,
        'signal': signal,
        'issues': issues,
        'severity': severity,
        'open_time': trade['open_time'],
    }

def format_result(r):
    icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}.get(r['severity'], '?')
    signal = r['signal']
    sig_str = f"{signal['signal_type']}@{signal['confidence']}%" if signal else 'no_signal'
    z_str = f"z={signal['z_score']:.3f}" if signal and signal['z_score'] is not None else ''
    return (f"{icon} {r['token']} #{r['trade_id']} {r['direction']} | "
            f"regime={r['regime']} | signal={sig_str} {z_str} | "
            f"{'; '.join(r['issues'])}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', action='store_true', help='Run continuously every 60s')
    parser.add_argument('--trade-id', type=int, help='Check specific trade ID')
    parser.add_argument('--minutes', type=int, default=15, help='Check trades opened in last N minutes')
    args = parser.parse_args()

    regimes = load_regimes()
    
    if args.trade_id:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, pnl_pct, status, open_time::text
            FROM trades WHERE id = %s
        """, (args.trade_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            trade = dict(zip(['id','token','direction','entry_price','pnl_pct','status','open_time'], row))
            result = check_trade(trade, regimes)
            print(format_result(result))
        else:
            print(f"Trade #{args.trade_id} not found")
        sys.exit(0)

    while True:
        trades = get_open_trades(since_minutes=args.minutes)
        ts = datetime.now(timezone.utc).strftime('%H:%M:%S')
        
        if trades:
            print(f"\n[{ts}] Checking {len(trades)} recent open trade(s):")
            fails = []
            for t in trades:
                r = check_trade(t, regimes)
                print(f"  {format_result(r)}")
                if r['severity'] == 'FAIL':
                    fails.append(r)
            
            if fails:
                print(f"\n  🚨 {len(fails)} FAIL(s) — review needed:")
                for f in fails:
                    print(f"     {f['token']} #{f['trade_id']}: {f['issues']}")
        else:
            print(f"[{ts}] No new open trades in last {args.minutes} min")
        
        if not args.watch:
            break
        
        import time
        time.sleep(60)
        regimes = load_regimes()  # Refresh regimes
        args.minutes = 2  # Shorter window on subsequent runs
