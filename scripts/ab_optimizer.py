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
AB_CONFIG_FILE = '/root/.hermes/config/ab_tests.json'
EVOLUTION_LOG   = '/var/www/hermes/logs/ab_evolution.log'
os.makedirs(os.path.dirname(EVOLUTION_LOG), exist_ok=True)


# ─── Evolution Thresholds ──────────────────────────────────────────────────────
# ── Real-data-calibrated (updated 2026-03-31) ──────────────────────────────────
# Historical data shows: PnL% is more important than win rate for this system.
# Winners: SL-1p5 (+7.4%), TS-1p0-0p5 (+10.7%), RETRACE-2 (+4.0%)
# Historical bad actors: IMMEDIATE (416 trades, -57%!), TS-0p5-0p3 (292 trades, -62%!)
# These should have been killed — the WIN_RATE_KILL threshold missed them because
# they had 13-17% WR which was above 10% threshold but catastrophically negative PnL.
# FIX: PnL% kill is now primary; win rate secondary.
MIN_TRADES_EVOLVE   = 15    # trades needed before evaluating
WIN_RATE_KILL       = 0.05  # retire if WR below 5% (much stricter — 13% WR is still catastrophic if avg_loss >> avg_win)
PNL_KILL            = -15.0 # retire if PnL% below -15% (primary kill signal)
EPSILON             = 0.15  # 15% exploration — shift toward exploiting winners now
MIN_TRADES_RANDOM   = 10    # need minimum sample before competing for exploit slot


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
    """Return the variant with the highest TOTAL PnL% from ab_results.
    Win rate is misleading — we care about net PnL, not how often we win.
    Example: SL-2p0 has 24% WR but -48.7% PnL. SL-1p5 has 11.7% WR but +7.4% PnL.
    """
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT variant_id, win_rate_pct, total_pnl_pct, trades, total_pnl_usdt
        FROM ab_results
        WHERE test_name=%s AND trades >= %s
        ORDER BY total_pnl_pct DESC
        LIMIT 1
    """, (test_name, MIN_TRADES_RANDOM))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row:
        return {
            'variant_id': row[0],
            'win_rate_pct': row[1] if row[1] is not None else 0.0,
            'total_pnl_pct': row[2] if row[2] is not None else 0.0,
            'trades': row[3] if row[3] is not None else 0,
            'total_pnl_usdt': row[4] if row[4] is not None else 0.0,
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
    With probability 1-EPSILON: exploit → best-performing variant by TOTAL PnL (not win rate)
    NOTE: Win rate is misleading — high WR with small wins < low WR with big wins.
    PnL% is the true bottom line for this system.

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
                        f'(PnL={best["total_pnl_pct"]:+.1f}%, WR={best["win_rate_pct"]:.0f}%, {best["trades"]} trades)')
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
    # avg_r may not exist in older schema — use COALESCE to be safe
    cur.execute("""
        SELECT test_name, variant_id, trades, wins, losses,
               win_rate_pct, total_pnl_pct, total_pnl_usdt, updated_at
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
            'total_pnl_usdt': r[7] or 0, 'updated_at': r[8],
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
            # ── Kill conditions (primary: PnL, secondary: WR) ──────────────────
            # Primary: any variant with PnL% < -15% gets killed regardless of WR
            # This catches the catastrophic cases (IMMEDIATE=-57%, TS-0p5=-62%) that
            # had decent WR but destroyed PnL through fee drag + small wins
            should_kill = pnl < PNL_KILL
            # Secondary: very low WR AND negative PnL (both bad signals)
            should_kill = should_kill or (win_rate < WIN_RATE_KILL * 100 and pnl < 0)
            if should_kill:
                status = 'KILLED'
                killed_any = True
                kill_reason = []
                if pnl < PNL_KILL:
                    kill_reason.append(f'pnl={pnl:+.1f}% < {PNL_KILL}%')
                if win_rate < WIN_RATE_KILL * 100 and pnl < 0:
                    kill_reason.append(f'low WR + neg PnL')
                log_lines.append(f'    ❌ {vid}: WR={win_rate:.0f}% PnL={pnl:+.1f}% → KILLED ({", ".join(kill_reason)})')
                continue  # skip — variant removed
            # ── Promote condition: strong PnL AND reasonable WR ────────────────────
            elif pnl >= 10 and win_rate >= 15:
                new_weight = min(weight * 1.5, 60)
                variant['weight'] = int(new_weight)
                status = f'PROMOTED (+50% → {new_weight:.0f}%)'
                log_lines.append(f'    🏆 {vid}: WR={win_rate:.0f}% PnL={pnl:+.1f}% → PROMOTED')
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
        # Only redistribute 60% of freed weight — leave 40% headroom for new variant spawns.
        # Prevents total hitting exactly 100 and blocking spawn conditions.
        redistribute_weight = int(killed_weight * 0.6)
        if evolved and redistribute_weight > 0:
            boost_per_winner = redistribute_weight / len(evolved)
            for v in evolved:
                v['weight'] = int(v.get('weight', 1) + boost_per_winner)
            log_lines.append(f'    📦 Redistributed {redistribute_weight:.0f} (of {killed_weight:.0f} freed) across {len(evolved)} survivors')

    # ── Normalize weights to ~90, leaving 10 for new spawn ─────────
    # Always normalize, even when nothing was killed (the initial config has
    # weights summing to 100, which would block spawns).
    total = sum(v.get('weight', 1) for v in evolved)
    if total > 0:
        target = 90  # leave 10 for new variant to get spawned with weight 10
        for v in evolved:
            v['weight'] = max(1, round(v.get('weight', 1) / total * target))

    # ── Spawn new variant ────────────────────────────────────────────
    # Spawn if: ≥2 variants, no spawned variant exists yet, under 6 variants.
    # Weights are now ~90 total so a 10-weight spawn fits under 100.
    total_surviving_weight = sum(v.get('weight', 1) for v in evolved)
    has_spawned_variant = any(v.get('config', {}).get('evolved_from') for v in evolved)
    if len(evolved) >= 2 and total_surviving_weight < 95 and not has_spawned_variant and len(evolved) < 6:
        new_variant = _spawn_new_variant(test_name, evolved)
        if new_variant:
            evolved.append(new_variant)
            log_lines.append(f'    🆕 SPAWNED: {new_variant["id"]} — {new_variant["config"].get("description","")}')

    # ── Clip weights to valid range ─────────────────────────────
    for v in evolved:
        v['weight'] = max(1, min(v['weight'], 60))

    return evolved, '\n'.join(log_lines)

def _spawn_new_variant(test_name: str, surviving: List[Dict]) -> Optional[Dict]:
    """
    Generate a new variant based on what we're already testing and market conditions.
    Tries to probe an adjacent hypothesis to the current best performer.

    FIX: Sort by total_pnl_pct DESC (PnL is the true bottom line, not win rate).
    Win rate is misleading — high WR with small wins < low WR with big wins.
    """
    if not surviving:
        return None

    # Fetch actual PnL data for each surviving variant (fixes broken _get_win_rate)
    survivors_with_pnl = []
    for v in surviving:
        stats = _get_variant_stats(v, test_name)
        survivors_with_pnl.append((v, stats))

    # Sort by PnL% DESC (most reliable metric for trading systems)
    survivors_with_pnl.sort(key=lambda x: x[1]['total_pnl_pct'], reverse=True)
    best, best_stats = survivors_with_pnl[0]

    best_cfg = best.get('config', {})
    best_pnl = best_stats['total_pnl_pct']
    best_wr = best_stats['win_rate_pct']

    if test_name == 'sl-distance-test':
        # If 1% SL is winning (positive PnL), try 0.75% (even tighter) or 2.5% (wider)
        # Use 'slDistance' if present (fraction like 0.01), else 'slPct' (percentage like 1.0)
        current_sl_dist = best_cfg.get('slDistance')
        current_sl_pct = best_cfg.get('slPct')
        if current_sl_dist is not None:
            # slDistance is a fraction: 0.01 = 1%
            current_sl = float(current_sl_dist) * 100  # convert to percentage
        elif current_sl_pct is not None:
            current_sl = float(current_sl_pct)
        else:
            current_sl = 1.5  # fallback

        if best_pnl > 0:
            new_sl = round(current_sl * 0.75, 2)  # try tighter
            desc = (f'EVOLVED: tighter SL ({new_sl:.2f}%) derived from '
                    f'{best["id"]} PnL={best_pnl:+.1f}%')
        else:
            new_sl = round(current_sl * 1.5, 1)    # try wider
            desc = (f'EVOLVED: wider SL ({new_sl:.1f}%) derived from '
                    f'{best["id"]} PnL={best_pnl:+.1f}%')
        new_sl = max(0.5, min(new_sl, 5.0))
        return {
            'id': f'SL{new_sl:.0f}pct-E{len(surviving)+1}',
            'name': f'SL-{new_sl:.1f}%-Evo',
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
                'description': f'EVOLVED: {new_mode} {new_pct*100:.1f}% pullback (from {best["id"]})',
                'evolved_from': best['id'],
                'spawned_at': datetime.now().isoformat(),
            }
        }

    elif test_name == 'trailing-stop-test':
        # Evolve around the best trailing params
        current_act = best_cfg.get('trailingActivationPct', 0.01)
        new_act = round(current_act * 0.5, 4)  # try tighter activation
        new_act = max(0.002, min(new_act, 0.05))
        # Calculate trailing distance: 80% of activation (or 0.4x as fallback)
        new_dist_raw = best_cfg.get('trailingDistancePct', current_act * 0.5)
        new_dist = round(new_dist_raw * 0.8, 4)
        new_dist = max(0.001, min(new_dist, 0.05))
        return {
            'id': f'TSEVO-{len(surviving)+1}',
            'name': f'TS-Evolve-{len(surviving)+1}',
            'weight': 10,
            'enabled': True,
            'config': {
                'trailingActivationPct': new_act,
                'trailingDistancePct': new_dist,
                'description': f'EVOLVED: TS activate +{new_act*100:.2f}% dist {new_dist*100:.2f}% (from {best["id"]})',
                'evolved_from': best['id'],
                'spawned_at': datetime.now().isoformat(),
            }
        }

    elif test_name == 'flip-trade-strategy':
        # Evolve flip strategy: learn when flipping is profitable
        # If no-flip is winning: test tighter flip triggers
        # If flip is winning: add trailing to flipped position
        flip_on_hard = best_cfg.get('flipOnHardSL', False)
        flip_on_soft = best_cfg.get('flipOnSoftSL', False)
        has_trailing = best_cfg.get('flipTrailing', False)
        trail_act = best_cfg.get('flipTrailingActivation', 0.005)
        trail_dist = best_cfg.get('flipTrailingDistance', 0.005)

        if not flip_on_hard and not flip_on_soft:
            # Control (no flip) is winning — try flipping on hard SL only
            return {
                'id': f'FLIP-EVO-{len(surviving)+1}',
                'name': f'Flip-Evolve-{len(surviving)+1}',
                'weight': 10,
                'enabled': True,
                'config': {
                    'flipOnSoftSL': False,
                    'flipOnHardSL': True,
                    'flipTrailing': False,
                    'flipTrailingActivation': None,
                    'flipTrailingDistance': None,
                    'description': f'EVOLVED: flip on hard SL only (from {best["id"]})',
                    'evolved_from': best['id'],
                    'spawned_at': datetime.now().isoformat(),
                }
            }
        elif flip_on_hard and not flip_on_soft and not has_trailing:
            # Hard SL flip is winning — add trailing to the flipped position
            return {
                'id': f'FLIP-EVO-{len(surviving)+1}',
                'name': f'Flip-Evolve-{len(surviving)+1}',
                'weight': 10,
                'enabled': True,
                'config': {
                    'flipOnSoftSL': False,
                    'flipOnHardSL': True,
                    'flipTrailing': True,
                    'flipTrailingActivation': 0.005,
                    'flipTrailingDistance': 0.005,
                    'description': f'EVOLVED: hard flip + tight trailing (from {best["id"]})',
                    'evolved_from': best['id'],
                    'spawned_at': datetime.now().isoformat(),
                }
            }
        elif flip_on_hard and has_trailing:
            # Try softer trailing on the flipped position
            return {
                'id': f'FLIP-EVO-{len(surviving)+1}',
                'name': f'Flip-Evolve-{len(surviving)+1}',
                'weight': 10,
                'enabled': True,
                'config': {
                    'flipOnSoftSL': True,
                    'flipOnHardSL': True,
                    'flipTrailing': True,
                    'flipTrailingActivation': round(trail_act * 1.5, 4),
                    'flipTrailingDistance': round(trail_dist * 1.5, 4),
                    'description': f'EVOLVED: soft+hard flip + looser trail (from {best["id"]})',
                    'evolved_from': best['id'],
                    'spawned_at': datetime.now().isoformat(),
                }
            }

    return None


def _get_variant_stats(variant: Dict, test_name: str) -> Dict:
    """
    Fetch complete stats for a variant from ab_results.
    Returns dict with total_pnl_pct, win_rate_pct, trades, total_pnl_usdt.
    Uses variant 'id' as variant_id (NOT 'name' — 'name' is a human description).
    Requires test_name to be passed since variants don't store their own test_name.
    """
    try:
        conn = _db_conn()
        cur = conn.cursor()
        vid = variant.get('id', '')
        cur.execute("""
            SELECT total_pnl_pct, win_rate_pct, trades, total_pnl_usdt
            FROM ab_results
            WHERE test_name=%s AND variant_id=%s
        """, (test_name, vid))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            return {
                'total_pnl_pct': float(row[0]) if row[0] is not None else 0.0,
                'win_rate_pct': float(row[1]) if row[1] is not None else 50.0,
                'trades': int(row[2]) if row[2] is not None else 0,
                'total_pnl_usdt': float(row[3]) if row[3] is not None else 0.0,
            }
        return {'total_pnl_pct': 0.0, 'win_rate_pct': 50.0, 'trades': 0,
                'total_pnl_usdt': 0.0}
    except Exception:
        return {'total_pnl_pct': 0.0, 'win_rate_pct': 50.0, 'trades': 0,
                'total_pnl_usdt': 0.0}


def _get_win_rate(variant: Dict) -> float:
    """
    DEPRECATED: This function cannot determine test_name for the SQL query.
    Use _get_variant_stats(variant, test_name) instead, which returns
    both win_rate_pct and total_pnl_pct.
    This function now falls back to PnL-based sorting (the correct approach).
    """
    return 50.0  # Fallback — actual data should come from _get_variant_stats


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

        # ── Backfill ab_results stats into each variant so they survive across restarts ─
        results_by_vid = {r['variant_id']: r for r in test_results}
        for variant in evolved_variants:
            vid = variant.get('id', '')
            result = results_by_vid.get(vid, {})
            variant['trades'] = result.get('trades', 0)
            variant['wins'] = result.get('wins', 0)
            variant['losses'] = result.get('losses', 0)
            variant['winRate'] = round(result.get('win_rate_pct', 0), 1)
            variant['totalPnlPct'] = round(result.get('total_pnl_pct', 0), 2)
            variant['lastUpdated'] = str(result.get('updated_at', '')) if result.get('updated_at') else None

        killed = old_count - len(evolved_variants)
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
