#!/usr/bin/env python3
"""
Signal Auditor: scans all signal types, ranks by edge, suggests actions.

Data source: signal_outcomes (signals_hermes_runtime.db) + SIGNAL_REGISTRY
Output: data/signal_audit.json + automation/signal_audit.md
Timer: every 6 hours (hermes-signal-auditor.timer)

Usage:
  python3 signal_auditor.py           # Full run: audit → rank → suggest
"""

import sys, os, re, fcntl, json, sqlite3
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA

LOCK_FILE = '/tmp/hermes-signal-auditor.lock'
AUDIT_JSON = os.path.join(HERMES_DATA, 'signal_audit.json')
AUDIT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'signal_audit.md')
CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')

# Minimum trades to evaluate
MIN_TRADES_7D = 5
MIN_TRADES_30D = 10

# Thresholds
EDGE_SCORE_STRONG = 0.3     # WR*avg_pnl*sqrt(count) above this → enable candidate
EDGE_SCORE_WEAK = 0.1       # below this → disable candidate
WR_FLOOR = 30               # below 30% WR → candidate for disable
WR_CEIL = 60                # above 60% WR → strong candidate for enable


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)


def get_signal_performance(days=7):
    """Query signal_outcomes for performance by signal_type."""
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    c.execute("""
        SELECT signal_type,
               COUNT(*) as trades,
               SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
               AVG(pnl_pct) as avg_pnl,
               MIN(pnl_pct) as min_pnl,
               MAX(pnl_pct) as max_pnl,
               COUNT(DISTINCT token) as tokens_traded
        FROM signal_outcomes
        WHERE created_at > datetime('now', '-' || ? || ' days')
          AND trade_id IS NOT NULL
        GROUP BY signal_type
        HAVING trades >= ?
        ORDER BY trades DESC
    """, (days, MIN_TRADES_7D if days <= 7 else MIN_TRADES_30D))
    rows = c.fetchall()
    conn.close()
    return rows


def get_registry_status():
    """Get enabled/disabled status from hermes_constants.py."""
    status = {}
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        # Find all *_ENABLED flags
        for match in re.finditer(r'^(\w+_ENABLED)\s*=\s*(True|False)', content, re.MULTILINE):
            flag, value = match.group(1), match.group(2)
            status[flag] = value == 'True'
    except Exception as e:
        log(f"Error reading constants: {e}")
    return status


def compute_edge_score(wins, trades, avg_pnl):
    """Compute edge score: WR * avg_pnl * sqrt(trade_count)."""
    wr = wins / trades if trades > 0 else 0
    return wr * avg_pnl * (trades ** 0.5)


def get_token_breakdown(signal_type, days=7):
    """Get per-token performance for a signal type."""
    conn = sqlite3.connect(RUNTIME_DB)
    c = conn.cursor()
    c.execute("""
        SELECT token, COUNT(*) as trades,
               SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
               AVG(pnl_pct) as avg_pnl
        FROM signal_outcomes
        WHERE signal_type = ?
          AND created_at > datetime('now', '-' || ? || ' days')
          AND trade_id IS NOT NULL
        GROUP BY token
        ORDER BY trades DESC
    """, (signal_type, days))
    rows = c.fetchall()
    conn.close()
    return rows


def map_signal_to_flag(signal_type):
    """Map a signal_type name to its *_ENABLED flag in hermes_constants.py.

    DB signal types use hyphens and +/- suffixes (e.g., 'accel-300+').
    hermes_constants.py flags use underscores and PLUS/MINUS suffixes.
    """
    # Normalize: take first component of compound types, strip +/- suffix
    base = signal_type.split(',')[0].strip()
    suffix = ''
    if base.endswith('+'):
        suffix = '_PLUS'
        base = base[:-1]
    elif base.endswith('-'):
        suffix = '_MINUS'
        base = base[:-1]
    elif base.endswith('_long'):
        suffix = '_PLUS'
        base = base[:-5]
    elif base.endswith('_short'):
        suffix = '_MINUS'
        base = base[:-6]

    # Normalize base to underscore form for lookup
    base_underscore = base.replace('-', '_')

    # Master flag overrides (signals that use a master flag, not directional)
    master_overrides = {
        'bb_squeeze': 'BOLLINGER_SQUEEZE',
        'pattern_scanner': 'PATTERN_FLAG',
        'volume_hl': 'VOLUME_HL',
        'atr_compression': 'ATR_COMPRESSION',
    }

    # Exact overrides for signals with non-standard flag names
    exact_overrides = {
        'accel_300_vel': 'ACCEL_300_VELOCITY',
        'inv_accel_300': 'INVERSE_ACCEL_300',
        'inverse_accel_300_v2': 'INVERSE_ACCEL_300_V2',
        'tl_break_long': 'TL_BREAK_PLUS',   # long → plus
        'tl_break_short': 'TL_BREAK_MINUS',  # short → minus
        'ema9_sma20': 'EMA9_SMA20',
        'ma_cross_5m': 'MA_CROSS_5M',
        'gap_300': 'GAP_300',
        'mtp_zscore': 'MTP_ZSCORE',
    }
    # Signals with a single flag (no PLUS/MINUS variants) — ignore directional suffix
    _single_flag_overrides = {'inverse_accel_300_v2'}

    # Check master overrides first — use directional flag when suffix present
    if base_underscore in master_overrides:
        flag_base = master_overrides[base_underscore]
        return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'

    # Check exact overrides (ignore suffix)
    if base_underscore in exact_overrides:
        flag_base = exact_overrides[base_underscore]
        if base_underscore in _single_flag_overrides or not suffix:
            return f'{flag_base}_ENABLED'
        return f'{flag_base}{suffix}_ENABLED'

    # Default: convert base to uppercase, apply suffix
    flag_base = base_underscore.upper()
    if suffix:
        return f'{flag_base}{suffix}_ENABLED'
    else:
        return f'{flag_base}_ENABLED'


def suggest_action(sig, registry):
    """Suggest enable/disable/tune action for a signal."""
    signal_type = sig['signal_type']
    wr = sig['wins'] / sig['trades'] * 100 if sig['trades'] > 0 else 0
    avg_pnl = sig['avg_pnl']
    edge = sig['edge_score']
    flag = map_signal_to_flag(signal_type)
    is_enabled = registry.get(flag, None) if flag else None

    action = 'monitor'
    reason = ''

    if is_enabled is False and wr >= WR_CEIL and sig['trades'] >= MIN_TRADES_7D:
        action = 'enable_candidate'
        reason = f'Strong WR ({wr:.0f}%) but disabled — consider enabling'
    elif is_enabled is True and wr < WR_FLOOR and sig['trades'] >= MIN_TRADES_7D:
        action = 'disable_candidate'
        reason = f'Weak WR ({wr:.0f}%) and losing money — consider disabling'
    elif is_enabled is True and edge < EDGE_SCORE_WEAK:
        action = 'disable_candidate'
        reason = f'Low edge score ({edge:.3f}) — bleeding capital'
    elif wr >= WR_CEIL and avg_pnl > 0:
        action = 'prioritize'
        reason = f'Winner: {wr:.0f}% WR, avg PnL={avg_pnl:+.4f}%'

    return {
        'action': action,
        'reason': reason,
        'flag': flag,
        'is_enabled': is_enabled,
    }


def write_audit_md(audit_results):
    """Write human-readable audit report."""
    os.makedirs(os.path.dirname(AUDIT_MD), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    tmp = AUDIT_MD + '.tmp'
    with open(tmp, 'w') as f:
        f.write(f"# Signal Audit — {ts}\n\n")
        f.write(f"## Summary\n")
        f.write(f"- Signals evaluated: {len(audit_results)}\n")
        winners = [r for r in audit_results if r['action'] == 'prioritize']
        f.write(f"- Winners: {len(winners)}\n")
        enables = [r for r in audit_results if r['action'] == 'enable_candidate']
        f.write(f"- Enable candidates: {len(enables)}\n")
        disables = [r for r in audit_results if r['action'] == 'disable_candidate']
        f.write(f"- Disable candidates: {len(disables)}\n\n")

        f.write(f"## Ranked by Edge Score\n\n")
        f.write(f"| # | Signal | Trades | WR | Avg PnL | Edge | Enabled | Action |\n")
        f.write(f"|---|--------|--------|-----|---------|------|---------|--------|\n")
        for i, r in enumerate(audit_results, 1):
            wr = r['wins'] / r['trades'] * 100 if r['trades'] > 0 else 0
            enabled_str = '✅' if r['is_enabled'] is True else ('❌' if r['is_enabled'] is False else '❓')
            action_emoji = {'prioritize': '🏆', 'enable_candidate': '📈', 'disable_candidate': '📉', 'monitor': '👁️'}.get(r['action'], '')
            f.write(f"| {i} | {r['signal_type'][:25]} | {r['trades']} | {wr:.0f}% | {r['avg_pnl']:+.4f}% | {r['edge_score']:.3f} | {enabled_str} | {action_emoji} {r['action']} |\n")
    os.replace(tmp, AUDIT_MD)


def main():
    log("=== Signal Auditor ===")

    # Lock
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fd.close()
        log("Another instance running, exiting")
        return

    try:
        # Get performance data
        rows = get_signal_performance(days=7)
        log(f"Found {len(rows)} signal types with >= {MIN_TRADES_7D} trades (7d)")

        # Get registry status
        registry = get_registry_status()

        # Build audit results
        audit_results = []
        for signal_type, trades, wins, avg_pnl, min_pnl, max_pnl, tokens in rows:
            edge = compute_edge_score(wins, trades, avg_pnl)
            sig = {
                'signal_type': signal_type,
                'trades': trades,
                'wins': wins,
                'avg_pnl': avg_pnl,
                'min_pnl': min_pnl,
                'max_pnl': max_pnl,
                'tokens': tokens,
                'edge_score': edge,
                'wr': wins / trades * 100 if trades > 0 else 0,
            }
            suggestion = suggest_action(sig, registry)
            sig.update(suggestion)
            audit_results.append(sig)

        # Sort by edge score
        audit_results.sort(key=lambda x: x['edge_score'], reverse=True)

        # Print summary
        for r in audit_results[:10]:
            log(f"  {r['signal_type']:<25} WR={r['wr']:.0f}% PnL={r['avg_pnl']:+.4f} Edge={r['edge_score']:.3f} [{r['action']}]")

        # Write outputs atomically
        os.makedirs(os.path.dirname(AUDIT_JSON), exist_ok=True)
        tmp = AUDIT_JSON + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'signals': audit_results,
            }, f, indent=2, default=str)
        os.replace(tmp, AUDIT_JSON)

        write_audit_md(audit_results)

        log(f"Audit complete. {len(audit_results)} signals ranked.")

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == '__main__':
    main()
