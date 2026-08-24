#!/usr/bin/env python3
"""signal_confluence — meta-signal detecting persistence + compounding of first-order signals.

Looks backward over a 30-minute rolling window of first-order signals and fires when:
1. Multiple independent signal sources have fired in the same direction (compounding)
2. Price hasn't moved against those signals (persistence)

Cadence: slow signal — runs every 5 minutes (in _SLOW_SIGNALS).
"""
import sys, os, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown, get_all_latest_prices
from paths import HERMES_DATA

from hermes_constants import (
    SIGNAL_CONFLUENCE_ENABLED,
    SIGNAL_CONFLUENCE_PLUS_ENABLED,
    SIGNAL_CONFLUENCE_MINUS_ENABLED,
    SIGNAL_CONFLUENCE_WINDOW_MINUTES,
    SIGNAL_CONFLUENCE_PERSISTENCE_MAX_DRAWDOWN,
    SIGNAL_CONFLUENCE_MIN_COMPOUND,
    SIGNAL_CONFLUENCE_CONFIDENCE_THRESHOLD,
    SIGNAL_CONFLUENCE_COMPOUND_WEIGHT,
    SIGNAL_CONFLUENCE_SURVIVED_BONUS,
    SIGNAL_CONFLUENCE_RECENCY_BONUS,
    SIGNAL_CONFLUENCE_COOLDOWN_HOURS,
    SIGNAL_CONFLUENCE_MAX_PRICE_AGE,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE = 'signal_confluence'
SOURCE_LONG  = 'confluence+'
SOURCE_SHORT = 'confluence-'

_RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')


def _log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] [signal_confluence] {msg}'
    print(line, flush=True)
    try:
        log_path = os.path.join(HERMES_DATA, '..', 'logs', 'signals.log')
        with open(log_path, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _get_recent_signals(window_minutes):
    """Fetch signals from the past N minutes that haven't been executed."""
    conn = None
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute("""
            SELECT token, direction, signal_type, source, confidence, price, created_at
            FROM signals
            WHERE created_at > ?
              AND executed = 0
            ORDER BY token, direction, created_at
        """, (cutoff,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        _log(f'ERROR fetching recent signals: {e}')
        return []
    finally:
        if conn:
            conn.close()


def _get_current_price(token):
    """Get current price from latest_prices."""
    prices = get_all_latest_prices()
    data = prices.get(token.upper())
    if data and data.get('price') and data['price'] > 0:
        return data['price']
    return None


def _normalize_source(source):
    """Extract base source tags for compounding count.
    Handles comma-separated merged sources (e.g. 'hzscore,pct-hermes+').
    Returns a SET of normalized source names.
    """
    if not source:
        return set()
    results = set()
    for part in source.split(','):
        part = part.strip()
        if not part:
            continue
        base = part.split('@')[0]
        base = base.rstrip('+-').rstrip('0123456789')
        if base and base != 'unknown':
            results.add(base)
    return results


def _score_group(token, direction, signals):
    """Score a (token, direction) group for confluence."""
    # Get current price
    current_price = _get_current_price(token)
    if current_price is None:
        return None

    # Persistence check — price hasn't moved against the original direction
    entry_prices = [s['price'] for s in signals if s['price'] and s['price'] > 0]
    if not entry_prices:
        return None

    if direction == 'LONG':
        worst_entry = min(entry_prices)
        survived = current_price >= worst_entry * (1 - SIGNAL_CONFLUENCE_PERSISTENCE_MAX_DRAWDOWN)
    else:
        worst_entry = max(entry_prices)
        survived = current_price <= worst_entry * (1 + SIGNAL_CONFLUENCE_PERSISTENCE_MAX_DRAWDOWN)

    # Compounding: count unique source types (split comma-separated merged sources)
    unique_sources = set()
    for s in signals:
        bases = _normalize_source(s.get('source', ''))
        for base in bases:
            if base != 'confluence':  # exclude self-referencing
                unique_sources.add(base)

    compound_count = len(unique_sources)

    # Recency bonus — fresher signals = more relevant
    now = datetime.now(timezone.utc)
    most_recent = None
    for s in signals:
        try:
            created = datetime.strptime(s['created_at'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            if most_recent is None or created > most_recent:
                most_recent = created
        except Exception:
            pass

    recency_bonus = 0
    if most_recent:
        minutes_ago = (now - most_recent).total_seconds() / 60
        if minutes_ago < 10:
            recency_bonus = SIGNAL_CONFLUENCE_RECENCY_BONUS

    # Final score
    score = (
        compound_count * SIGNAL_CONFLUENCE_COMPOUND_WEIGHT
        + (SIGNAL_CONFLUENCE_SURVIVED_BONUS if survived else 0)
        + recency_bonus
    )

    if score < SIGNAL_CONFLUENCE_CONFIDENCE_THRESHOLD or compound_count < SIGNAL_CONFLUENCE_MIN_COMPOUND:
        return None

    return {
        'direction': direction,
        'confidence': min(88, score),  # add_signal() caps at 88
        'value': compound_count,
        'price': current_price,
        'survived': survived,
        'compound_count': compound_count,
        'unique_sources': list(unique_sources),
    }


def scan_signals() -> int:
    """Main scan — query recent signals, group by (token, direction), score, fire confluence."""
    if not SIGNAL_CONFLUENCE_ENABLED:
        return 0

    added = 0
    recent = _get_recent_signals(SIGNAL_CONFLUENCE_WINDOW_MINUTES)
    if not recent:
        _log('No recent signals in window')
        return 0

    # Group by (token, direction)
    groups = {}
    for sig in recent:
        token = sig['token']
        direction = sig['direction']
        key = (token, direction)
        if key not in groups:
            groups[key] = []
        groups[key].append(sig)

    _log(f'Found {len(groups)} (token, direction) groups from {len(recent)} signals')

    for (token, direction), signals in groups.items():
        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not SIGNAL_CONFLUENCE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not SIGNAL_CONFLUENCE_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Price freshness
        if price_age_minutes(token) > SIGNAL_CONFLUENCE_MAX_PRICE_AGE:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        # Score
        result = _score_group(token, direction, signals)
        if result is None:
            continue

        # Fire
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=SIGNAL_TYPE,
            source=source,
            confidence=result['confidence'],
            value=result['value'],
            price=result['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=SIGNAL_CONFLUENCE_COOLDOWN_HOURS)
            _log(f'FIRED: {token} {direction} conf={result["confidence"]:.0f} '
                 f'compound={result["compound_count"]} sources={result["unique_sources"]}')

    _log(f'Added {added} confluence signals')
    return added


def run():
    """Entry point for signals_runner. No params — reads from DB directly."""
    return scan_signals()


if __name__ == '__main__':
    # Allow direct execution for testing
    n = scan_signals()
    print(f'signal_confluence: {n} signals emitted')
