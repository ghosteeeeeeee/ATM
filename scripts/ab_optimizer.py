#!/usr/bin/env python3
"""
ab_optimizer.py — A/B test evolution engine for Hermes.

Two responsibilities:

1. EPSILON-GREEDY SELECTION (called by ai-decider on every trade)
   - epsilon = fraction of trades that go to exploration (default 20%)
   - Exploitation: pick the variant with highest win_rate_pct
   - Exploration: pick a random non-killed variant (weighted by remaining weight)

2. EVOLUTION ENGINE (runs on a schedule via cron)
   - After MIN_TRADES_EVOLVE trades per variant, evaluate performance
   - Retire losing variants (win_rate < WIN_RATE_KILL threshold OR pnl negative)
   - Redistribute freed weight to surviving winners
   - Spawn new variant hypotheses to test fresh market conditions
   - Write updated config back to ab-test-config.json
"""
import json, time, os, sys, random, argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# ─── DB ────────────────────────────────────────────────────────────────────────
BRAIN_DB = {
    'host': '/var/run/postgresql', 'dbname': 'brain',
    'user': 'postgres',  'password': 'postgres'
}
AB_CONFIG_FILE = '/root/.hermes/data/ab-test-config.json'
EVOLUTION_LOG   = '/var/www/hermes/logs/ab_evolution.log'
os.makedirs(os.path.dirname(EVOLUTION_LOG), exist_ok=True)


# ─── Evolution Thresholds ──────────────────────────────────────────────────────
MIN_TRADES_EVOLVE   = 30    # trades needed before evaluating a variant (raised to give slow-holding variants time to generate data)
WIN_RATE_KILL       = 0.50  # retire if win_rate below this (50%, lowered to be less aggressive)
PNL_KILL            = -5.0  # retire if total_pnl_pct below this (-5%, widened for longer-hold strategies)
EVOLVE_EVERY_MINUTES = 60   # run evolution at most once per hour
EPSILON             = 0.10  # 10% of trades go to exploration (reduced — let proven variants dominate)
MIN_TRADES_RANDOM   = 5     # variant must have this many trades before competing


def log(msg: str, level: str = 'INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} [{level}] {msg}'
    print(line)
    try:
        with open(EVOLUTION_LOG, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def _db_conn():
    import psycopg2
    return psycopg2.connect(**BRAIN_DB)


# ─── 1. Epsilon-Greedy Variant Selection ──────────────────────────────────────

def get_best_variant_for_test(test_name: str) -> Optional[Dict]:
    """Return the variant with the highest win rate from ab_results."""
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT variant_id, win_rate_pct, total_pnl_pct, trades, total_pnl_usdt, avg_r
        FROM ab_results
        WHERE test_name=%s AND trades >= %s
        ORDER BY win_rate_pct DESC, total_pnl_pct DESC
        LIMIT 1
    """, (test_name, MIN_TRADES_RANDOM))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        return {
            'variant_id': row[0],
            'win_rate_pct': row[1],
            'total_pnl_pct': row[2],
            'trades': row[3],
            'total_pnl_usdt': row[4],
            'avg_r': row[5],
        }
    return None


def get_exploration_variant_for_test(test_name: str, config: Dict) -> Optional[Dict]:
    """
    Pick a random variant for exploration, weighted by the config's weight field.
    Excludes any variant that has been flagged as 'killed'.
    """
    active = [v for v in config.get('variants', []) if v.get('enabled', True)]
    if not active:
        return None
    # Weight-proportional random selection
    total_weight = sum(v.get('weight', 1) for v in active)
    r = random.uniform(0, total_weight)
    cum = 0
    for v in active:
        cum += v.get('weight', 1)
        if r <= cum:
            return v
    return active[-1]


def epsilon_greedy_pick(test_name: str, config: Dict) -> Optional[Dict]:
    """
    Epsilon-greedy selection for a single A/B test.

    With probability EPSILON: explore → random variant (weighted)
    With probability 1-EPSILON: exploit → best-performing variant by win rate

    Returns the selected variant dict (or None).
    """
    if random.random() < EPSILON:
        variant = get_exploration_variant_for_test(test_name, config)
        if variant:
            log(f'EPSILON EXPLORE: {test_name} → {variant.get("id")} '
                f'(win_rate={variant.get("config",{}).get("winRateOverride","N/A")})')
        return variant
    else:
        best = get_best_variant_for_test(test_name)
        if best and best.get('trades', 0) >= MIN_TRADES_RANDOM:
            # Find the matching variant in config
            vid = best['variant_id']
            for v in config.get('variants', []):
                if v.get('id') == vid:
                    log(f'EPSILON EXPLOIT: {test_name} → {vid} '
                        f'(win_rate={best["win_rate_pct"]:.0f}%, trades={best["trades"]}, pnl={best["total_pnl_pct"]:+.1f}%)')
                    return v
        # Not enough data — fall back to random
        return get_exploration_variant_for_test(test_name, config)


# ─── 2. Evolution Engine ───────────────────────────────────────────────────────

def load_config() -> Dict:
    with open(AB_CONFIG_FILE) as f:
        return json.load(f)


def save_config(cfg: Dict):
    with open(AB_CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_all_results() -> Dict[str, List[Dict]]:
    """Fetch all ab_results grouped by test_name."""
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT test_name, variant_id, trades, wins, losses,
               win_rate_pct, total_pnl_pct, total_pnl_usdt, avg_r, updated_at
        FROM ab_results
        ORDER BY test_name, win_rate_pct DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    results = {}
    for r in rows:
        test = r[0]
        if test not in results:
            results[test] = []
        results[test].append({
            'variant_id': r[1], 'trades': r[2], 'wins': r[3], 'losses': r[4],
            'win_rate_pct': r[5] or 0, 'total_pnl_pct': r[6] or 0,
            'total_pnl_usdt': r[7] or 0, 'avg_r': r[8] or 0, 'updated_at': r[9],
        })
    return results


def evolve_test(test: Dict, results: List[Dict]) -> tuple[List[Dict], str]:
    """
    Evaluate a single A/B test and evolve it.

    Returns (updated_variants_list, log_message).
    """
    variants = test.get('variants', [])
    test_name = test['name']
    total_weight = sum(v.get('weight', 1) for v in variants)

    log_lines = [f'  Evolving {test_name}: {len(variants)} variants']

    # Group results by variant_id
    results_by_vid = {r['variant_id']: r for r in results}
    killed_any = False
    evolved = []

    for variant in variants:
        vid = vname = variant.get('id', '')
        cfg = variant.get('config', {})
        weight = variant.get('weight', 1)
        result = results_by_vid.get(vid, {})
        trades = result.get('trades', 0)
        win_rate = result.get('win_rate_pct', 0)
        pnl = result.get('total_pnl_pct', 0)

        status = 'ACTIVE'

        if trades >= MIN_TRADES_EVOLVE:
            # ── Kill condition ────────────────────────────────
            if win_rate < WIN_RATE_KILL * 100 or pnl < PNL_KILL:
                status = 'KILLED'
                killed_any = True
                log_lines.append(f'    ❌ {vid}: win_rate={win_rate:.0f}% pnl={pnl:+.1f}% '
                                 f'→ KILLED (thr: win_rate<{WIN_RATE_KILL*100:.0f}% OR pnl<{PNL_KILL}%)')
                continue  # skip — variant removed
            # ── Promote condition ────────────────────────────
            elif win_rate >= 60 and pnl >= 10:
                new_weight = min(weight * 1.5, 60)
                variant['weight'] = int(new_weight)
                status = f'PROMOTED (+50% → {new_weight:.0f}%)'
                log_lines.append(f'    🏆 {vid}: win_rate={win_rate:.0f}% pnl={pnl:+.1f}% → PROMOTED')
        else:
            status = f'learning ({trades}/{MIN_TRADES_EVOLVE} trades)'

        evolved.append(variant)
        log_lines.append(f'    {"✓" if status=="ACTIVE" else "→"} {vid}: {trades} trades | '
                         f'win_rate={win_rate:.0f}% pnl={pnl:+.1f}% → {status}')

    # ── Redistribute weight from killed variants ───────────────
    if killed_any:
        killed_weight = sum(v.get('weight', 1) for v in variants if
                            results_by_vid.get(v.get('id', ''), {}).get('trades', 0) >= MIN_TRADES_EVOLVE and
                            (results_by_vid.get(v.get('id', ''), {}).get('win_rate_pct', 0) < WIN_RATE_KILL * 100 or
                             results_by_vid.get(v.get('id', ''), {}).get('total_pnl_pct', 0) < PNL_KILL))
        freed_weight = killed_weight  # already removed from evolved list
        if evolved and freed_weight > 0:
            boost_per_winner = freed_weight / len(evolved)
            for v in evolved:
                v['weight'] = int(v.get('weight', 1) + boost_per_winner)
            log_lines.append(f'    📦 Redistributed {freed_weight:.0f} weight across {len(evolved)} survivors')

    # ── Spawn new variant if market changed significantly ─────
    # Only spawn if we have ≥2 surviving variants and total surviving weight < 90
    total_surviving_weight = sum(v.get('weight', 1) for v in evolved)
    if len(evolved) >= 2 and total_surviving_weight < 90:
        new_variant = _spawn_new_variant(test_name, evolved)
        if new_variant:
            evolved.append(new_variant)
            log_lines.append(f'    🆕 SPAWNED: {new_variant["id"]} — {new_variant["config"].get("description","")}')

    # ── Normalize weights to 100 ───────────────────────────────
    total = sum(v.get('weight', 1) for v in evolved)
    if total > 0:
        for v in evolved:
            v['weight'] = max(1, round(v.get('weight', 1) / total * 100))

    return evolved, '\n'.join(log_lines)


def _spawn_new_variant(test_name: str, surviving: List[Dict]) -> Optional[Dict]:
    """
    Generate a new variant based on what we're already testing and market conditions.
    Tries to probe an adjacent hypothesis to the current best performer.
    """
    # Sort surviving by win rate
    survivors_sorted = sorted(surviving,
                              key=lambda v: _get_win_rate(v),
                              reverse=True)
    if not survivors_sorted:
        return None

    best = survivors_sorted[0]
    best_cfg = best.get('config', {})
    best_wr = _get_win_rate(best)

    if test_name == 'sl-distance-test':
        # If 1% SL is winning, try 0.75% (even tighter) or 2.5% (wider)
        current_sl = best_cfg.get('slPct', 1.5)
        if best_wr >= 55:
            new_sl = round(current_sl * 0.75, 2)  # try tighter
            desc = f'EVOLVED: even tighter SL ({new_sl}%) derived from {best["id"]} win={best_wr:.0f}%'
        else:
            new_sl = round(current_sl * 1.5, 1)    # try wider
            desc = f'EVOLVED: wider SL ({new_sl}%) derived from {best["id"]} win={best_wr:.0f}%'
        new_sl = max(0.005, min(new_sl, 3.0))
        return {
            'id': f'SL{new_sl*100:.0f}pct-E{len(surviving)+1}',
            'name': f'SL-{new_sl*100:.0f}%-Evo',
            'weight': 10,
            'enabled': True,
            'config': {
                'slDistance': new_sl / 100,
                'slPct': new_sl,
                'description': desc,
                'evolved_from': best['id'],
                'spawned_at': datetime.now().isoformat(),
            }
        }

    elif test_name == 'entry-timing-test':
        # If IMMEDIATE is winning, try 0.5% pullback. If PULLBACK is winning, try 3%
        current_mode = best_cfg.get('entryMode', 'immediate')
        if current_mode == 'immediate':
            new_pct = 0.005
            new_mode = 'pullback'
        else:
            new_pct = 0.03
            new_mode = 'pullback'
        return {
            'id': f'EVO-{len(surviving)+1}',
            'name': f'Entry-Evolve-{len(surviving)+1}',
            'weight': 10,
            'enabled': True,
            'config': {
                'entryMode': new_mode,
                'pullbackPct': new_pct,
                'maxWaitMinutes': 60,
                'description': f'EVOLVED: {new_mode} {new_pct*100:.1f}% pullback',
                'evolved_from': best['id'],
                'spawned_at': datetime.now().isoformat(),
            }
        }

    elif test_name == 'trailing-stop-test':
        # Evolve around the best trailing params
        current_act = best_cfg.get('trailingActivationPct', 0.01)
        new_act = round(current_act * 0.5, 4)  # try tighter activation
        new_act = max(0.002, min(new_act, 0.05))
        return {
            'id': f'TSEVO-{len(surviving)+1}',
            'name': f'TS-Evolve-{len(surviving)+1}',
            'weight': 10,
            'enabled': True,
            'config': {
                'trailingActivationPct': new_act,
                'trailingDistancePct': round(new_act * 0.8, 4),
                'description': f'EVOLVED: TS activate at +{new_act*100:.2f}% (from {best["id"]})',
                'evolved_from': best['id'],
                'spawned_at': datetime.now().isoformat(),
            }
        }

    return None


def _get_win_rate(variant: Dict) -> float:
    """Get win rate for a variant from ab_results."""
    try:
        conn = _db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT win_rate_pct FROM ab_results
            WHERE test_name=%s AND variant_id=%s
        """, (variant.get('name', ''), variant.get('id', '')))
        row = cur.fetchone()
        cur.close(); conn.close()
        return float(row[0]) if row else 50.0
    except Exception:
        return 50.0


def run_evolution() -> Dict[str, Any]:
    """
    Run the full evolution cycle across all tests.
    Returns a summary dict.
    """
    log('═' * 60)
    log('A/B EVOLUTION CYCLE STARTING')
    log(f'  Thresholds: min_trades={MIN_TRADES_EVOLVE}, win_rate_kill={WIN_RATE_KILL*100:.0f}%, '
        f'pnl_kill={PNL_KILL}%, epsilon={EPSILON*100:.0f}%')

    cfg = load_config()
    results = get_all_results()

    summary = {'tests_evolved': 0, 'variants_killed': 0,
               'variants_spawned': 0, 'variants_promoted': 0}

    for test in cfg.get('tests', []):
        test_name = test['name']
        test_results = results.get(test_name, [])

        total_trades = sum(r['trades'] for r in test_results)
        log(f'\nTest: {test_name} ({total_trades} total trades across variants)')

        if total_trades == 0:
            log(f'  No data yet — skipping')
            continue

        evolved_variants, detail = evolve_test(test, test_results)
        log(detail)

        old_count = len(test.get('variants', []))
        test['variants'] = evolved_variants

        killed = old_count - len(evived_variants)
        spawned = sum(1 for v in evolved_variants
                      if v.get('config', {}).get('evolved_from'))
        promoted = old_count - killed  # rough
        summary['variants_killed'] += killed
        summary['variants_spawned'] += spawned
        summary['tests_evolved'] += 1

    save_config(cfg)
    log(f'\n✅ Evolution complete: {summary["tests_evolved"]} tests evolved | '
        f'{summary["variants_killed"]} killed | {summary["variants_spawned"]} spawned')
    log('═' * 60)
    return summary


# ─── 3. Snapshot for Dashboard ─────────────────────────────────────────────────

def get_evolution_snapshot() -> Dict:
    """Return a readable snapshot of current experiment state for the dashboard."""
    cfg = load_config()
    results = get_all_results()

    snapshot = {'timestamp': datetime.now().isoformat(), 'tests': []}
    for test in cfg.get('tests', []):
        test_name = test['name']
        test_results = results.get(test_name, [])
        r_by_vid = {r['variant_id']: r for r in test_results}

        variants_summary = []
        for v in test.get('variants', []):
            vid = v['id']
            r = r_by_vid.get(vid, {})
            variants_summary.append({
                'id': vid,
                'name': v.get('name', vid),
                'weight': v.get('weight', 1),
                'enabled': v.get('enabled', True),
                'config': v.get('config', {}),
                'trades': r.get('trades', 0),
                'win_rate': round(r.get('win_rate_pct', 0), 1),
                'pnl_pct': round(r.get('total_pnl_pct', 0), 1),
                'wins': r.get('wins', 0),
                'losses': r.get('losses', 0),
                'evolved_from': v.get('config', {}).get('evolved_from', ''),
                'ready_to_evolve': r.get('trades', 0) >= MIN_TRADES_EVOLVE,
            })
        snapshot['tests'].append({
            'name': test_name,
            'description': test.get('description', ''),
            'variants': variants_summary,
            'total_trades': sum(v['trades'] for v in variants_summary),
        })
    return snapshot


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A/B Evolution Engine')
    parser.add_argument('--dry-run', action='store_true', help='Simulate evolution without writing config')
    parser.add_argument('--snapshot', action='store_true', help='Print current state snapshot')
    args = parser.parse_args()

    if args.snapshot:
        import pprint
        pprint.pprint(get_evolution_snapshot())
    elif args.dry_run:
        cfg = load_config()
        results = get_all_results()
        for test in cfg.get('tests', []):
            print(f'\n=== {test["name"]} ===')
            evolve_test(test, results.get(test['name'], []))
    else:
        run_evolution()
