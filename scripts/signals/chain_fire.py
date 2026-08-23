#!/usr/bin/env python3
"""chain_fire — Fire on follower tokens when leader tokens pump.

When a token fires a signal, check the correlation engine for tokens that
tend to follow with high win rate. If a qualifying chain exists, fire a
signal on the follower token.

Example: ASTER fires → correlation engine says 2Z follows (100% WR, 1.8x lift)
→ chain_fire fires on 2Z.
"""
import sys, os, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA, RUNTIME_DB, STATIC_DB

from hermes_constants import (
    CHAIN_FIRE_ENABLED,
    CHAIN_FIRE_PLUS_ENABLED,
    CHAIN_FIRE_MINUS_ENABLED,
    CHAIN_FIRE_MIN_LIFT,
    CHAIN_FIRE_MIN_CONFIDENCE,
    CHAIN_FIRE_MIN_CO_FIRES,
    CHAIN_FIRE_MAX_LEADER_AGE_SECS,
    CHAIN_FIRE_COOLDOWN_HOURS,
    CHAIN_FIRE_MAX_PER_CYCLE,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'chain_fire_long'
SIGNAL_TYPE_SHORT = 'chain_fire_short'
SOURCE_LONG       = 'chain_fire+'
SOURCE_SHORT      = 'chain_fire-'


def _get_recent_leaders():
    """Get tokens that had trades close in the last MAX_LEADER_AGE seconds.

    Returns list of (token, direction, created_at) tuples.
    Uses signal_outcomes which records actual trade executions.
    """
    try:
        conn = sqlite3.connect(f"file:{RUNTIME_DB}?mode=ro", uri=True, timeout=5)
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(
                seconds=CHAIN_FIRE_MAX_LEADER_AGE_SECS
            )).strftime('%Y-%m-%d %H:%M:%S')

            rows = conn.execute("""
                SELECT DISTINCT token, direction, created_at
                FROM signal_outcomes
                WHERE created_at > ?
                ORDER BY created_at DESC
            """, (cutoff,)).fetchall()

            return [(r[0], r[1], r[2]) for r in rows]
        finally:
            conn.close()
    except Exception:
        return []


def _compute_confidence(chain_conf, lift, n):
    """Scale chain correlation data to Hermes confidence range (65-88).

    Base: 75 — chain suggests but doesn't guarantee.
    Boost: up to +13 based on lift, sample size, and chain confidence.
    """
    base = 75

    # Lift bonus: 1.5x → +5, 2.0x → +10, 3.0x → +10 (capped)
    lift_bonus = min(10, int((lift - 1.0) * 10))

    # Sample size bonus: n=5 → +0, n=10 → +2, n=20 → +6
    sample_bonus = min(6, max(0, int((n - 5) * 0.4)))

    # Chain confidence bonus: 0.6 → +0, 0.8 → +2, 0.9+ → +3
    conf_bonus = min(3, max(0, int((chain_conf - 0.6) * 7.5)))

    raw = base + lift_bonus + sample_bonus + conf_bonus
    return max(65, min(88, raw))


def scan_signals():
    """Main scan: check recent leaders, fire on qualifying followers.

    Returns number of chain signals added.
    """
    if not CHAIN_FIRE_ENABLED:
        return 0

    try:
        from correlation_engine import CorrelationEngine
    except ImportError:
        return 0

    engine = CorrelationEngine()
    leaders = _get_recent_leaders()

    if not leaders:
        return 0

    added = 0
    for leader_token, direction, fired_at in leaders:
        if added >= CHAIN_FIRE_MAX_PER_CYCLE:
            break

        # Skip blacklisted leaders
        if leader_token in LONG_BLACKLIST or leader_token in SHORT_BLACKLIST:
            continue

        # Get chain suggestions from correlation engine
        try:
            chains = engine.next_tokens(leader_token, k=5)
        except Exception:
            continue

        for chain in chains:
            if added >= CHAIN_FIRE_MAX_PER_CYCLE:
                break

            follower = chain['token_b']
            lift = chain['lift']
            conf = chain['confidence']
            n = chain['co_fires']
            wr = chain['win_rate']

            # Skip self-referential
            if follower == leader_token:
                continue

            # Filter by thresholds
            if lift < CHAIN_FIRE_MIN_LIFT:
                continue
            if conf < CHAIN_FIRE_MIN_CONFIDENCE:
                continue
            if n < CHAIN_FIRE_MIN_CO_FIRES:
                continue

            # Direction check
            if direction == 'LONG' and not CHAIN_FIRE_PLUS_ENABLED:
                continue
            if direction == 'SHORT' and not CHAIN_FIRE_MINUS_ENABLED:
                continue

            # Blacklist
            if direction == 'LONG' and follower in LONG_BLACKLIST:
                continue
            if direction == 'SHORT' and follower in SHORT_BLACKLIST:
                continue

            # Cooldown
            if get_cooldown(follower, direction=direction):
                continue

            # Price freshness
            if price_age_minutes(follower) > 10:
                continue

            # Get price from latest_prices
            try:
                conn = sqlite3.connect(
                    f"file:{STATIC_DB}?mode=ro",
                    uri=True, timeout=5
                )
                try:
                    row = conn.execute(
                        "SELECT price FROM latest_prices WHERE token = ?",
                        (follower.upper(),)
                    ).fetchone()
                    if not row or not row[0]:
                        continue
                    price = float(row[0])
                finally:
                    conn.close()
            except Exception:
                continue

            # Compute confidence
            confidence = _compute_confidence(conf, lift, n)

            # Fire signal
            sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
            source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

            sid = add_signal(
                token=follower,
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=lift,
                price=price,
                exchange='hyperliquid',
                timeframe='5m',
            )

            if sid:
                added += 1
                set_cooldown(follower, direction, hours=CHAIN_FIRE_COOLDOWN_HOURS)
                print(f"  [CHAIN-FIRE] {leader_token} → {follower} "
                      f"(lift={lift:.1f}x, wr={wr:.0%}, n={n}, conf={confidence})")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # CLI: dry run
    import argparse
    parser = argparse.ArgumentParser(description='Chain fire signal')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.dry:
        print("=== Chain Fire Dry Run ===")
        leaders = _get_recent_leaders()
        print(f"Recent leaders: {len(leaders)}")
        for token, direction, ts in leaders[:10]:
            print(f"  {token} ({direction}) at {ts}")

        try:
            from correlation_engine import CorrelationEngine
            engine = CorrelationEngine()
            for token, direction, ts in leaders[:5]:
                chains = engine.next_tokens(token, k=3)
                if chains:
                    print(f"\n  {token} chains:")
                    for c in chains:
                        print(f"    → {c['token_b']}: lift={c['lift']:.1f}x "
                              f"wr={c['win_rate']:.0%} n={c['co_fires']} "
                              f"conf={c['confidence']:.2f}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        n = run()
        print(f"Chain fire signals added: {n}")
