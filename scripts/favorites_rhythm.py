#!/usr/bin/env python3
"""
favorites_rhythm.py — Weekly wave/cluster analysis for FAVORITES system.

Analyzes 30 days of trade data to find:
  1. Temporal co-occurrence — which coins fire in the same 4h windows
  2. Signal clustering — which coins get triggered by the same signals
  3. Regime correlation — which coins perform in the same regimes
  4. Return correlation — Pearson correlation of daily PnL
  5. Cadence/rhythm — mean time between trades, burstiness, time-of-day patterns

Runs weekly (Sunday 05:00 UTC, before favorites_updater).
Output feeds into favorites_updater.py for promote/demote decisions.

Run via: python3 scripts/favorites_rhythm.py
Timer: hermes-favorites-rhythm.timer (weekly)

Spec: plans/favorites-daily-update-spec.md
"""
import os, sys, json, fcntl, statistics
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from math import sqrt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

LOCK_FILE = '/tmp/hermes-favorites-rhythm.lock'
OUTPUT_FILE = os.path.join(HERMES_DATA, 'favorites_rhythm.json')
LOG_FILE = '/root/.hermes/logs/favorites_rhythm.log'
LOOKBACK_DAYS = 30


def is_blacklisted(token):
    """Check if token is in any blacklist."""
    return token in SHORT_BLACKLIST or token in LONG_BLACKLIST


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def get_db():
    """Get database connection."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    return psycopg2.connect(**BRAIN_DB_DICT)


def analyze_temporal_cooccurrence(conn):
    """Which coins fire in the same 4-hour windows?"""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            token,
            EXTRACT(EPOCH FROM (
                date_trunc('hour', open_time) -
                INTERVAL '3 hours' * MOD(EXTRACT(HOUR FROM open_time)::int, 4)
            )) as window_start,
            EXTRACT(EPOCH FROM (
                date_trunc('hour', close_time) -
                INTERVAL '3 hours' * MOD(EXTRACT(HOUR FROM close_time)::int, 4)
            )) as window_end
        FROM trades
        WHERE status IN ('open', 'closed')
          AND server = 'Hermes'
          AND open_time > NOW() - INTERVAL '%s days'
    """ % LOOKBACK_DAYS)

    # Build token -> set of 4h windows
    token_windows = defaultdict(set)
    for token, w_start, w_end in cur.fetchall():
        if w_start and w_end:
            # Use the opening window
            token_windows[token].add(int(w_start) // (4 * 3600))

    tokens = [t for t in token_windows.keys() if not is_blacklisted(t)]
    if len(tokens) < 2:
        return {'pairs': [], 'groups': []}

    # Compute Jaccard similarity for all pairs
    pairs = []
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens)):
            a, b = tokens[i], tokens[j]
            wa, wb = token_windows[a], token_windows[b]
            intersection = len(wa & wb)
            union = len(wa | wb)
            if union > 0:
                jaccard = round(intersection / union, 3)
                if jaccard > 0.1:  # only meaningful pairs
                    pairs.append({'a': a, 'b': b, 'jaccard': jaccard})

    pairs.sort(key=lambda x: x['jaccard'], reverse=True)

    # Simple greedy clustering based on Jaccard threshold
    groups = []
    used = set()
    for pair in pairs:
        if pair['jaccard'] < 0.3:
            break
        a, b = pair['a'], pair['b']
        if a in used and b in used:
            continue
        # Find or create group
        found_group = None
        for g in groups:
            if a in g['coins'] or b in g['coins']:
                found_group = g
                break
        if found_group:
            found_group['coins'].add(a)
            found_group['coins'].add(b)
        else:
            groups.append({'coins': {a, b}, 'pairs': [pair]})
        used.add(a)
        used.add(b)

    # Convert sets to lists and compute avg internal jaccard
    result_groups = []
    for g in groups:
        coins = sorted(g['coins'])
        if len(coins) < 2:
            continue
        internal_pairs = [p for p in pairs
                         if p['a'] in coins and p['b'] in coins and p['jaccard'] >= 0.3]
        avg_jaccard = round(sum(p['jaccard'] for p in internal_pairs) / len(internal_pairs), 3) if internal_pairs else 0
        result_groups.append({
            'name': f"wave_{len(result_groups) + 1}",
            'coins': coins,
            'avg_internal_jaccard': avg_jaccard
        })

    return {'pairs': pairs[:20], 'groups': result_groups}


def analyze_signal_clustering(conn):
    """Which coins get triggered by the same signals?"""
    cur = conn.cursor()
    cur.execute("""
        SELECT token, signal, COUNT(*) as cnt
        FROM trades
        WHERE server = 'Hermes'
          AND close_time > NOW() - INTERVAL '%s days'
          AND signal IS NOT NULL
          AND signal != ''
        GROUP BY token, signal
        HAVING COUNT(*) >= 2
    """ % LOOKBACK_DAYS)

    # Build token -> signal profile
    token_signals = defaultdict(lambda: defaultdict(int))
    for token, signal, cnt in cur.fetchall():
        # Use the primary signal (before comma)
        primary = signal.split(',')[0].strip()
        token_signals[token][primary] += cnt

    tokens = [t for t in token_signals.keys() if not is_blacklisted(t)]
    if len(tokens) < 2:
        return {'groups': []}

    # Compute cosine similarity between token signal profiles
    all_signals = set()
    for sigs in token_signals.values():
        all_signals.update(sigs.keys())
    signal_list = sorted(all_signals)

    def signal_vector(token):
        return [token_signals[token].get(s, 0) for s in signal_list]

    def cosine_sim(v1, v2):
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = sqrt(sum(a * a for a in v1))
        mag2 = sqrt(sum(b * b for b in v2))
        if mag1 == 0 or mag2 == 0:
            return 0
        return dot / (mag1 * mag2)

    # Cluster by signal similarity (simple: group tokens sharing primary signal)
    signal_groups = defaultdict(list)
    for token in tokens:
        if token_signals[token]:
            primary = max(token_signals[token], key=token_signals[token].get)
            signal_groups[primary].append(token)

    groups = []
    for primary_signal, members in sorted(signal_groups.items(), key=lambda x: -len(x[1])):
        if len(members) >= 2:
            groups.append({
                'name': f"{primary_signal}_cluster",
                'coins': sorted(members),
                'primary_signals': [primary_signal],
                'size': len(members)
            })

    return {'groups': groups[:10]}


def analyze_regime_correlation(conn):
    """Which coins perform in the same regimes?"""
    cur = conn.cursor()
    cur.execute("""
        SELECT token, regime,
            COUNT(*) as trades,
            ROUND(AVG(pnl_pct)::numeric, 2) as avg_pnl,
            ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as wr
        FROM trades
        WHERE server = 'Hermes'
          AND close_time > NOW() - INTERVAL '%s days'
          AND regime IS NOT NULL
          AND regime != ''
        GROUP BY token, regime
        HAVING COUNT(*) >= 2
    """ % LOOKBACK_DAYS)

    matrix = defaultdict(dict)
    for token, regime, trades, avg_pnl, wr in cur.fetchall():
        if not is_blacklisted(token):
            matrix[token][regime] = {
                'trades': int(trades),
                'avg_pnl': float(avg_pnl) if avg_pnl else 0,
                'wr': float(wr) if wr else 0
            }

    return {'matrix': dict(matrix)}


def analyze_return_correlation(conn):
    """Pearson correlation of daily PnL across tokens."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            token,
            DATE(close_time) as day,
            ROUND(SUM(pnl_usdt)::numeric, 4) as daily_pnl
        FROM trades
        WHERE server = 'Hermes'
          AND close_time > NOW() - INTERVAL '%s days'
          AND pnl_usdt IS NOT NULL
        GROUP BY token, DATE(close_time)
        HAVING COUNT(*) >= 1
    """ % LOOKBACK_DAYS)

    # Build token -> daily PnL series
    token_daily = defaultdict(lambda: defaultdict(float))
    for token, day, pnl in cur.fetchall():
        token_daily[token][str(day)] = float(pnl)

    tokens = [t for t in token_daily.keys() if not is_blacklisted(t)]
    if len(tokens) < 2:
        return {'top_pairs': []}

    def pearson(a_days, b_days):
        """Compute Pearson correlation between two daily series."""
        common = sorted(set(a_days.keys()) & set(b_days.keys()))
        if len(common) < 10:  # need at least 10 overlapping days for meaningful correlation
            return None
        vals_a = [a_days[d] for d in common]
        vals_b = [b_days[d] for d in common]
        n = len(common)
        mean_a = sum(vals_a) / n
        mean_b = sum(vals_b) / n
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(vals_a, vals_b))
        std_a = sqrt(sum((a - mean_a) ** 2 for a in vals_a))
        std_b = sqrt(sum((b - mean_b) ** 2 for b in vals_b))
        if std_a == 0 or std_b == 0:
            return None
        return round(cov / (std_a * std_b), 3)

    pairs = []
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens)):
            a, b = tokens[i], tokens[j]
            corr = pearson(token_daily[a], token_daily[b])
            if corr is not None and abs(corr) > 0.3:
                pairs.append({'a': a, 'b': b, 'correlation': corr})

    pairs.sort(key=lambda x: -abs(x['correlation']))
    return {'top_pairs': pairs[:15]}


def analyze_cadence(conn):
    """Mean time between trades, burstiness, time-of-day patterns."""
    cur = conn.cursor()
    cur.execute("""
        SELECT token, open_time
        FROM trades
        WHERE server = 'Hermes'
          AND open_time > NOW() - INTERVAL '%s days'
        ORDER BY token, open_time
    """ % LOOKBACK_DAYS)

    token_times = defaultdict(list)
    for token, open_time in cur.fetchall():
        token_times[token].append(open_time)

    result = {}
    for token, times in token_times.items():
        if len(times) < 3:
            continue

        # Inter-trade intervals in hours
        intervals = []
        for i in range(1, len(times)):
            delta = (times[i] - times[i - 1]).total_seconds() / 3600
            intervals.append(delta)

        mean_interval = statistics.mean(intervals) if intervals else 0
        burstiness = round(statistics.stdev(intervals) / mean_interval, 2) if mean_interval > 0 and len(intervals) > 1 else 0

        # Time-of-day distribution
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        for t in times:
            hour_counts[t.hour] += 1
            day_counts[t.strftime('%A')] += 1

        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
        peak_day = max(day_counts, key=day_counts.get) if day_counts else None

        result[token] = {
            'mean_hours_between': round(mean_interval, 1),
            'burstiness': burstiness,
            'total_trades': len(times),
            'peak_hour_utc': peak_hour,
            'peak_day': peak_day,
            'hour_distribution': dict(sorted(hour_counts.items())),
        }

    return result


def generate_recommendations(clusters, cadence, current_favs):
    """Auto-generated suggestions for the daily updater."""
    recs = []

    # Wave sibling recommendations
    temporal_groups = clusters.get('temporal', {}).get('groups', [])
    for group in temporal_groups:
        coins = set(group['coins'])
        fav_overlap = coins & current_favs
        non_fav = coins - current_favs
        if len(fav_overlap) >= 2 and non_fav:
            recs.append({
                'type': 'promotion_hint',
                'message': f"{', '.join(sorted(non_fav))} are wave-siblings with favorites "
                           f"{', '.join(sorted(fav_overlap))} (Jaccard={group['avg_internal_jaccard']})",
                'priority': 'medium'
            })

    # Anti-correlation diversification
    corr_pairs = clusters.get('return_correlation', {}).get('top_pairs', [])
    for pair in corr_pairs[:3]:
        if pair['correlation'] < 0:
            a_in = pair['a'] in current_favs
            b_in = pair['b'] in current_favs
            if a_in and not b_in:
                recs.append({
                    'type': 'diversification_hint',
                    'message': f"{pair['b']} is negatively correlated with favorite "
                               f"{pair['a']} ({pair['correlation']}) — consider for diversification",
                    'priority': 'low'
                })

    # Cadence warnings
    for token, info in cadence.items():
        if info.get('burstiness', 0) > 3:
            recs.append({
                'type': 'cadence_warning',
                'message': f"{token} is very bursty (burstiness={info['burstiness']}) — "
                           f"reduce FAVORITES_SIZE_MULT for this coin",
                'priority': 'medium'
            })

    # Signal cluster recommendations
    signal_groups = clusters.get('signal', {}).get('groups', [])
    for group in signal_groups:
        coins = set(group['coins'])
        fav_overlap = coins & current_favs
        non_fav = coins - current_favs
        if len(fav_overlap) >= 1 and non_fav and len(non_fav) <= 2:
            recs.append({
                'type': 'signal_cluster_hint',
                'message': f"{', '.join(sorted(non_fav))} share signal profile with "
                           f"favorite {', '.join(sorted(fav_overlap))} ({group['name']})",
                'priority': 'low'
            })

    return recs


def run():
    lock_fd = None
    conn = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("Another instance running — skipping")
        return

    try:
        conn = get_db()

        log("Analyzing temporal co-occurrence...")
        temporal = analyze_temporal_cooccurrence(conn)

        log("Analyzing signal clustering...")
        signal = analyze_signal_clustering(conn)

        log("Analyzing regime correlation...")
        regime = analyze_regime_correlation(conn)

        log("Analyzing return correlation...")
        returns = analyze_return_correlation(conn)

        log("Analyzing cadence...")
        cadence = analyze_cadence(conn)

        conn.close()

        # Build clusters object
        clusters = {
            'temporal': {**temporal, 'description': 'Coins that fire in the same 4h windows'},
            'signal': {**signal, 'description': 'Coins triggered by the same signals'},
            'regime': {**regime, 'description': 'Coins that perform in the same regimes'},
            'return_correlation': {**returns, 'description': 'Daily PnL correlation'},
        }

        # Load current favorites for recommendations
        try:
            from hermes_constants import FAVORITES
            current_favs = set(FAVORITES)
        except Exception:
            current_favs = set()

        recommendations = generate_recommendations(clusters, cadence, current_favs)

        output = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'lookback_days': LOOKBACK_DAYS,
            'clusters': clusters,
            'cadence': cadence,
            'recommendations': recommendations,
        }

        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        # Summary
        n_pairs = len(temporal.get('pairs', []))
        n_groups = len(temporal.get('groups', []))
        n_signal_groups = len(signal.get('groups', []))
        n_corr_pairs = len(returns.get('top_pairs', []))
        n_cadence = len(cadence)

        log(f"Written rhythm analysis: "
            f"{n_pairs} temporal pairs, {n_groups} wave groups, "
            f"{n_signal_groups} signal clusters, {n_corr_pairs} correlated pairs, "
            f"{n_cadence} cadence profiles, {len(recommendations)} recommendations")

    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            try: conn.close()
            except Exception: pass
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


if __name__ == '__main__':
    run()
