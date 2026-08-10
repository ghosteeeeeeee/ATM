#!/usr/bin/env python3
"""Test Hebbian write-back: trade outcome → brain.db associations.

Tests:
1. learn_pair / weaken_pair basics (weight dynamics)
2. learn_trade_outcome() win/loss behavior
3. WEIGHT_FLOOR respected on repeated weakens
4. SetupStats dataclass prevents tuple-shape bugs
5. brain.py close_trade() writes to Hebbian
6. recall() returns expected associations
7. Production brain.db concepts preserved

Uses TEST_* prefixed concepts so it doesn't pollute production data.
Skips cleanup at end so user can inspect brain.db after running.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')

from hebbian_engine import HebbianEngine, WEIGHT_CEILING, WEIGHT_FLOOR, WEIGHT_INCREMENT
from decider_run import similar_setup_lookup, SetupStats


PASS = '\033[32m✅\033[0m'
FAIL = '\033[31m❌\033[0m'
results = []


def check(name, condition, detail=''):
    if condition:
        print(f'{PASS} {name}' + (f' ({detail})' if detail else ''))
        results.append((name, True))
    else:
        print(f'{FAIL} {name}' + (f' ({detail})' if detail else ''))
        results.append((name, False))


def test_hebbian_engine():
    """Test hebbian_engine.py basic operations."""
    print('\n=== 1. HebbianEngine basics ===')
    eng = HebbianEngine()

    # Test 1.1: learn_pair creates synapse at 1.0
    w_before = eng.recall('TEST_HTOK_A', k=20)
    w_initial = next((r[2] for r in w_before if r[0] == 'TEST_HSIG_A'), None)
    eng.learn_pair('TEST_HTOK_A', 'TEST_HSIG_A')
    recall_after = dict((r[0], r[2]) for r in eng.recall('TEST_HTOK_A', k=20))
    w_after_learn = recall_after.get('TEST_HSIG_A')
    check('learn_pair creates synapse',
          w_after_learn is not None and w_after_learn >= WEIGHT_INCREMENT,
          f'weight={w_after_learn}')

    # Test 1.2: weaken_pair decrements weight
    w_before_weaken = w_after_learn
    eng.weaken_pair('TEST_HTOK_A', 'TEST_HSIG_A')
    recall_after = dict((r[0], r[2]) for r in eng.recall('TEST_HTOK_A', k=20))
    w_after_weaken = recall_after.get('TEST_HSIG_A')
    check('weaken_pair decrements weight',
          w_after_weaken is not None and w_after_weaken < w_before_weaken,
          f'{w_before_weaken} → {w_after_weaken}')

    # Test 1.3: WEIGHT_FLOOR respected
    for _ in range(100):
        eng.weaken_pair('TEST_HTOK_B', 'TEST_HSIG_B')  # create at floor (0.5)
    recall_after = dict((r[0], r[2]) for r in eng.recall('TEST_HTOK_B', k=20))
    w_floor = recall_after.get('TEST_HSIG_B')
    check('WEIGHT_FLOOR respected',
          w_floor == WEIGHT_FLOOR,
          f'weight={w_floor}, floor={WEIGHT_FLOOR}')


def test_learn_trade_outcome():
    """Test learn_trade_outcome win/loss logic."""
    print('\n=== 2. learn_trade_outcome win/loss ===')
    eng = HebbianEngine()

    # Test 2.1: WIN strengthens all pairs
    result = eng.learn_trade_outcome(
        token='TEST_TTOK_A', signal='TEST_TSIG_A', direction='LONG',
        pnl_pct=1.5, z_score_tier='neutral', momentum_state='accelerating',
    )
    check('WIN strengthens pairs', result['strengthened'] > 0 and result['weakened'] == 0,
          f'{result}')

    # Test 2.2: LOSS weakens all pairs
    result = eng.learn_trade_outcome(
        token='TEST_TTOK_B', signal='TEST_TSIG_B', direction='SHORT',
        pnl_pct=-1.0, z_score_tier='high', momentum_state='decelerating',
    )
    check('LOSS weakens pairs', result['weakened'] > 0 and result['strengthened'] == 0,
          f'{result}')

    # Test 2.3: Empty concepts (all None) is no-op
    result = eng.learn_trade_outcome(token=None, signal=None, direction=None, pnl_pct=1.0)
    check('All-None concepts is no-op',
          result == {'strengthened': 0, 'weakened': 0},
          f'{result}')

    # Test 2.4: Single concept (no pairs) is no-op
    result = eng.learn_trade_outcome(token='TEST_TTOK_C', signal=None, direction=None, pnl_pct=1.0)
    check('Single concept is no-op',
          result == {'strengthened': 0, 'weakened': 0},
          f'{result}')


def test_weight_dynamics():
    """Test net weight changes over multiple trade outcomes."""
    print('\n=== 3. Weight dynamics over multiple outcomes ===')
    eng = HebbianEngine()
    token, signal, direction = 'TEST_WTOK_A', 'TEST_WSIG_A', 'LONG'

    # Get baseline (may not exist)
    recall_before = dict((r[0], r[2]) for r in eng.recall(token, k=20))
    w_before = recall_before.get(signal, 0)

    # 3 wins, 1 loss → net +2 (WIN=+1, LOSS=-1)
    eng.learn_trade_outcome(token=token, signal=signal, direction=direction, pnl_pct=1.0)
    w_1w = dict((r[0], r[2]) for r in eng.recall(token, k=20)).get(signal, 0)
    eng.learn_trade_outcome(token=token, signal=signal, direction=direction, pnl_pct=1.0)
    w_2w = dict((r[0], r[2]) for r in eng.recall(token, k=20)).get(signal, 0)
    eng.learn_trade_outcome(token=token, signal=signal, direction=direction, pnl_pct=-1.0)
    w_2w1l = dict((r[0], r[2]) for r in eng.recall(token, k=20)).get(signal, 0)
    eng.learn_trade_outcome(token=token, signal=signal, direction=direction, pnl_pct=1.0)
    w_3w1l = dict((r[0], r[2]) for r in eng.recall(token, k=20)).get(signal, 0)

    check('Single WIN adds weight', w_1w > w_before, f'{w_before} → {w_1w}')
    check('Two WINS add 2x weight', abs((w_2w - w_before) - 4.0) < 0.01, f'{w_before} → {w_2w}')
    check('WIN-WIN-LOSS = +2', abs((w_2w1l - w_before) - 2.0) < 0.01, f'{w_before} → {w_2w1l}')
    check('WIN-WIN-LOSS-WIN = +4', abs((w_3w1l - w_before) - 4.0) < 0.01, f'{w_before} → {w_3w1l}')


def test_setup_stats():
    """Test SetupStats dataclass prevents tuple-shape bugs."""
    print('\n=== 4. SetupStats dataclass ===')
    stats = similar_setup_lookup('0G', 'accel-300-', 'SHORT', rsi=44, z_tier='neutral')
    check('similar_setup_lookup returns SetupStats', isinstance(stats, SetupStats),
          f'{type(stats).__name__}')

    if stats:
        check('SetupStats has .n field', hasattr(stats, 'n'), f'n={stats.n}')
        check('SetupStats has .win_rate field', hasattr(stats, 'win_rate'),
              f'win_rate={stats.win_rate:.3f}')
        check('SetupStats has .avg_pnl field', hasattr(stats, 'avg_pnl'),
              f'avg_pnl={stats.avg_pnl:.4f}')
        check('win_rate is 0-1 range', 0 <= stats.win_rate <= 1, f'{stats.win_rate}')

        # Test cache hit returns same SetupStats (no tuple-shape regression)
        stats2 = similar_setup_lookup('0G', 'accel-300-', 'SHORT', rsi=44, z_tier='neutral')
        check('Cache hit returns SetupStats (not tuple)',
              isinstance(stats2, SetupStats) and stats2.n == stats.n,
              f'n={stats2.n} (cache hit)')


def test_brain_close_trade_hebbian():
    """Test brain.py close_trade() triggers Hebbian write-back."""
    print('\n=== 5. brain.py close_trade() → Hebbian ===')
    from brain import get_db_connection, close_trade

    eng = HebbianEngine()
    test_token = 'HTTST'
    test_signal = 'ht_sig'

    # Snapshot Hebbian weight BEFORE
    recall_before = dict((r[0], r[2]) for r in eng.recall(test_token, k=50))
    w_before = recall_before.get(test_signal, 0)

    # Create a test open trade
    from datetime import datetime, timezone
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    c.execute("""
        INSERT INTO trades (token, direction, signal, status, entry_price, amount_usdt,
                           leverage, entry_timing, signal_z_score_tier, signal_momentum_state)
        VALUES (%s, 'LONG', %s, 'open', 1.0, 11.0, 5, %s, 'neutral', 'building')
        RETURNING id
    """, (test_token, test_signal, now))
    trade_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    print(f'  Created test trade id={trade_id}')

    # Close it — this should trigger hebbian writeback
    # Use skip_hl=True to avoid HL API call on test trade
    try:
        result = close_trade(trade_id=trade_id, exit_price=1.01, pnl_usdt=0.55,
                            notes='hebbian_test', close_reason='hebbian_test', skip_hl=True)
        check('close_trade() returns True', result is True, f'returned {result}')
    except Exception as e:
        check('close_trade() runs without error', False, f'{type(e).__name__}: {e}')
        return

    # Verify Hebbian weight increased
    eng2 = HebbianEngine()
    recall_after = dict((r[0], r[2]) for r in eng2.recall(test_token, k=50))
    w_after = recall_after.get(test_signal, 0)
    check('Hebbian weight increased after close',
          w_after > w_before,
          f'{w_before} → {w_after}')

    # Cleanup: remove test trade
    conn = get_db_connection()
    conn.cursor().execute("DELETE FROM trades WHERE id = %s", (trade_id,))
    conn.commit()
    conn.close()


def test_recall_uses_backfilled_data():
    """Test that recall() returns trade-outcome associations."""
    print('\n=== 6. recall() uses backfilled data ===')
    eng = HebbianEngine()

    # These tokens had high-frequency trades in the backfill (e.g., 2Z had 44 SHORT fires)
    recall_short = eng.recall('SHORT', k=20)
    tokens_in_short = [r[0] for r in recall_short]
    check('recall("SHORT") returns tokens',
          len(recall_short) > 0 and len(tokens_in_short) > 0,
          f'{len(recall_short)} associations: {tokens_in_short[:5]}')

    # accel-300- should have associations with direction concepts
    recall_accel = eng.recall('accel-300-', k=20)
    concepts_in_accel = [r[0] for r in recall_accel]
    check('recall("accel-300-") returns concepts',
          len(recall_accel) > 0,
          f'{len(recall_accel)} associations: {concepts_in_accel[:5]}')


def test_production_data_preserved():
    """Verify production brain.db concepts are still present."""
    print('\n=== 7. Production data preserved ===')
    eng = HebbianEngine()
    stats = eng.get_stats()

    # Production had 4 decisions + 3 regimes + 135 tokens = 142 nodes
    # After backfill we should have 142 + ~865 trade concepts
    check('Brain.db has 900+ nodes', stats['nodes'] > 900, f'{stats["nodes"]} nodes')
    check('Brain.db has 5000+ synapses', stats['synapses'] > 5000, f'{stats["synapses"]} synapses')
    check('Production decisions preserved',
          stats['label_distribution'].get('decision', 0) == 4,
          f'{stats["label_distribution"]}')
    check('Production regimes preserved',
          stats['label_distribution'].get('regime', 0) == 3,
          f'{stats["label_distribution"]}')
    check('Production tokens preserved',
          stats['label_distribution'].get('token', 0) >= 135,
          f'{stats["label_distribution"]}')

    # TNSR should still be associated with SHORT_BIAS (top production edge)
    recall_tnsr = dict((r[0], r[2]) for r in eng.recall('TNSR', k=10))
    check('TNSR ↔ SHORT_BIAS production edge intact',
          recall_tnsr.get('SHORT_BIAS', 0) >= 99,
          f'weight={recall_tnsr.get("SHORT_BIAS", 0)}')


def cleanup_test_data():
    """Remove TEST_* concepts and their synapses from brain.db."""
    import sqlite3
    eng = HebbianEngine()
    with sqlite3.connect(eng.db_path) as conn:
        c = conn.cursor()
        # Get TEST_* concept ids
        c.execute("SELECT id FROM concept_nodes WHERE name LIKE 'TEST_%' OR name LIKE 'HTOK%' OR name LIKE 'HSIG%' OR name LIKE 'TTOK%' OR name LIKE 'TSIG%' OR name LIKE 'WTOK%' OR name LIKE 'WSIG%'")
        test_ids = [r[0] for r in c.fetchall()]
        if not test_ids:
            return 0
        placeholders = ','.join('?' * len(test_ids))
        # Delete synapses involving test concepts
        c.execute(f"DELETE FROM synapse_weights WHERE concept_a_id IN ({placeholders}) OR concept_b_id IN ({placeholders})", test_ids + test_ids)
        # Delete test concept nodes
        c.execute(f"DELETE FROM concept_nodes WHERE id IN ({placeholders})", test_ids)
        conn.commit()
        return len(test_ids)


def main():
    print('=' * 60)
    print('HEBBIAN WRITE-BACK TEST SUITE')
    print('=' * 60)

    test_hebbian_engine()
    test_learn_trade_outcome()
    test_weight_dynamics()
    test_setup_stats()
    test_brain_close_trade_hebbian()
    test_recall_uses_backfilled_data()
    test_production_data_preserved()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print()
    print('=' * 60)
    print(f'RESULT: {passed}/{total} tests passed')
    print('=' * 60)

    # Cleanup test data so production brain.db stays clean
    cleaned = cleanup_test_data()
    print(f'\nCleaned up {cleaned} test concepts from brain.db')

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())