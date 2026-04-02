"""
Shared A/B testing utilities — canonical Thompson sampling implementation.
Both ai-decider.py and decider-run.py use this for A/B variant selection.
"""
import random, sys, json, os

EPSILON = 0.1  # 10% exploration rate in epsilon-greedy fallback


def _load_ab_config():
    """Load A/B config from /root/.hermes/config/ab_tests.json."""
    path = '/root/.hermes/config/ab_tests.json'
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def get_ab_variant(test_name: str, direction: str = 'both') -> dict:
    """
    Select A/B variant using Thompson sampling from brain DB (ab_results).
    Fallback chain:
      1. Thompson sampling (if all variants have >= 5 trials in last 30 days)
      2. Epsilon-greedy weighted random (90% exploitation, 10% exploration)
      3. Pure weighted random from config
      4. First enabled variant (ultimate fallback)
    Returns the variant dict (or empty dict if AB disabled/no config).
    """
    try:
        import psycopg2
    except ImportError:
        return {}

    cfg = _load_ab_config()
    if not cfg.get('enabled', False):
        return {}

    test = next((t for t in cfg.get('tests', []) if t['name'] == test_name), None)
    if not test:
        return {}

    variants = [v for v in test.get('variants', []) if v.get('enabled', True)]
    if not variants:
        return {}

    # ── 1. Try Thompson sampling from DB ─────────────────────────────────────
    try:
        conn = psycopg2.connect(
            host='/var/run/postgresql',
            dbname='brain',
            user='postgres',
            password='postgres',
            connect_timeout=2
        )
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '2000ms'")
        cur.execute("""
            SELECT variant_id, wins, losses
            FROM ab_results
            WHERE test_name = %s
              AND updated_at >= NOW() - INTERVAL '30 days'
        """, (test_name,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            variant_stats = {str(r[0]): (int(r[1] or 0), int(r[2] or 0)) for r in rows}
            total_trials = {vid: w + l for vid, (w, l) in variant_stats.items()}
            all_have_data = all(total_trials.get(v.get('id'), 0) >= 5 for v in variants)

            if all_have_data:
                samples = {}
                for v in variants:
                    vid = v.get('id')
                    wins, losses = variant_stats.get(vid, (0, 0))
                    samples[vid] = random.betavariate(wins + 1, losses + 1)
                winner_vid = max(samples, key=samples.get)
                for v in variants:
                    if v.get('id') == winner_vid:
                        return v
    except Exception:
        pass  # Fall through to epsilon-greedy

    # ── 2. Epsilon-greedy weighted random ───────────────────────────────────
    try:
        exploit_vid = None
        try:
            conn = psycopg2.connect(
                host='/var/run/postgresql',
                dbname='brain',
                user='postgres',
                password='postgres',
                connect_timeout=2
            )
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '2000ms'")
            cur.execute("""
                SELECT variant_id, win_rate_pct
                FROM ab_results
                WHERE test_name=%s AND trades >= 5
                ORDER BY win_rate_pct DESC
                LIMIT 1
            """, (test_name,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            exploit_vid = row[0] if row else None
        except Exception:
            exploit_vid = None

        if random.random() < (1.0 - EPSILON) and exploit_vid:
            for v in variants:
                if v.get('id') == exploit_vid:
                    return v
    except Exception:
        pass

    # ── 3. Pure weighted random from config ──────────────────────────────────
    total_weight = sum(v.get('weight', 1) for v in variants)
    r = random.uniform(0, total_weight)
    for v in variants:
        r -= v.get('weight', 1)
        if r <= 0:
            return v

    # ── 4. Ultimate fallback ───────────────────────────────────────────────
    return variants[0]


# ─── Cached variant selection (used by hl-sync-guardian.py) ──────────────────

# BUG-9 fix: cache key is test_name only, NOT token:direction.
# Thompson sampling in get_ab_variant() operates on AGGREGATE performance across ALL tokens.
# Caching per token biases the sampler — variant A losing on BTC should not affect
# the sampling decision for ETH. Now global per test_name.
_ab_variant_cache = {}

def get_cached_ab_variant(token: str, direction: str, test_name: str) -> dict:
    """
    Get A/B variant for test_name, cached globally per test_name.
    Token and direction are accepted for API compatibility but do NOT affect
    the cache key — Thompson sampling operates on aggregate across all tokens.
    """
    if test_name not in _ab_variant_cache:
        _ab_variant_cache[test_name] = get_ab_variant(test_name, direction)
    return _ab_variant_cache[test_name]
