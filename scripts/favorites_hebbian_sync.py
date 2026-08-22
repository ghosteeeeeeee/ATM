#!/usr/bin/env python3
"""
favorites_hebbian_sync.py — Feed favorites rhythm analysis into hebbian network.

Reads data/favorites_rhythm.json and writes findings into brain/associative_memory.db:
  - Wave sibling synapses (temporal co-occurrence)
  - Signal cluster concepts
  - Regime-coin associations
  - Anti-correlation weakening
  - Cadence pattern concepts
  - Historical snapshots for trend detection

Runs weekly after favorites_rhythm.py (chained via timer or manual).

Run via: python3 scripts/favorites_hebbian_sync.py
Timer: hermes-favorites-rhythm.timer (same as rhythm, runs after)

Spec: plans/favorites-daily-update-spec.md (Part 3: Hebbian Integration)
"""
import os, sys, json, fcntl, sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

LOCK_FILE = '/tmp/hermes-favorites-hebbian-sync.lock'
RHYTHM_FILE = os.path.join(HERMES_DATA, 'favorites_rhythm.json')
BRAIN_DB = '/root/.hermes/brain/associative_memory.db'
LOG_FILE = '/root/.hermes/logs/favorites_hebbian_sync.log'

# Hebbian weight dynamics (match hebbian_engine.py)
WEIGHT_CEILING = 100.0
WEIGHT_FLOOR = 0.5


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


def get_hebbian():
    """Lazy-load hebbian engine."""
    from hebbian_engine import HebbianEngine
    return HebbianEngine()


def ensure_snapshot_table():
    """Create favorites_snapshots table if not exists."""
    with sqlite3.connect(BRAIN_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                favorites_list TEXT NOT NULL,
                wave_groups TEXT NOT NULL,
                signal_clusters TEXT NOT NULL,
                top_correlations TEXT NOT NULL,
                cadence_summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def learn_wave_siblings(engine, temporal_groups, min_jaccard=0.3):
    """Strengthen synapses between coins that fire in the same 4h windows."""
    learned = 0
    for group in temporal_groups:
        coins = group.get('coins', [])
        avg_j = group.get('avg_internal_jaccard', 0)
        if avg_j < min_jaccard or len(coins) < 2:
            continue

        # Increment scales with Jaccard: higher co-occurrence = stronger learning
        increment = min(2.0, avg_j * 2)

        for i in range(len(coins)):
            for j in range(i + 1, len(coins)):
                engine.learn_pair(coins[i], coins[j], increment=increment)
                learned += 1

    return learned


def learn_signal_clusters(engine, signal_groups):
    """Create cluster concepts and link all member coins."""
    learned = 0
    for group in signal_groups:
        coins = group.get('coins', [])
        name = group.get('name', 'unknown')
        if len(coins) < 2:
            continue

        cluster_concept = f"cluster:{name}"
        for coin in coins:
            engine.learn_pair(coin, cluster_concept, increment=1.0)
            learned += 1

        # Also learn coin-coin pairs within the cluster (weaker)
        for i in range(len(coins)):
            for j in range(i + 1, len(coins)):
                engine.learn_pair(coins[i], coins[j], increment=0.5)
                learned += 1

    return learned


def learn_regime_associations(engine, regime_matrix, min_wr=60.0):
    """Strengthen synapses between coins and regimes they perform well in."""
    learned = 0
    for token, regimes in regime_matrix.items():
        for regime, stats in regimes.items():
            wr = stats.get('wr', 0)
            if wr >= min_wr:
                concept = f"regime:{regime}"
                # Scale increment with WR strength
                increment = min(2.0, (wr - 50) / 25)  # 0 at 50%, 2.0 at 100%
                engine.learn_pair(token, concept, increment=increment)
                learned += 1

    return learned


def weaken_anti_correlations(engine, corr_pairs, threshold=-0.5):
    """Weaken synapses between negatively correlated coins.
    Only weakens existing synapses to avoid creating noise entries."""
    weakened = 0
    for pair in corr_pairs:
        corr = pair.get('correlation', 0)
        if corr >= threshold:
            continue

        a, b = pair['a'], pair['b']
        # Only weaken if synapse already exists (avoid noise creation)
        weight, count = engine.synapse_weight(a, b)
        if count == 0:
            continue  # Skip — no existing relationship to weaken

        # Scale weakening with correlation strength
        increment = min(2.0, abs(corr) * 2)
        engine.weaken_pair(a, b, increment=increment)
        weakened += 1

    return weakened


def learn_cadence_patterns(engine, cadence_data, burstiness_threshold=3.0):
    """Learn burstiness patterns as concepts."""
    learned = 0
    for token, info in cadence_data.items():
        burstiness = info.get('burstiness', 0)
        if burstiness >= burstiness_threshold:
            engine.learn_pair(token, "pattern:bursty", increment=1.0)
            learned += 1
        elif burstiness > 0 and burstiness < 1.0:
            engine.learn_pair(token, "pattern:steady", increment=1.0)
            learned += 1

    return learned


def save_snapshot(rhythm_data, favorites_list):
    """Save a snapshot of the analysis for historical trend detection."""
    try:
        snapshot_date = rhythm_data.get('updated_at', datetime.now(timezone.utc).isoformat())
        with sqlite3.connect(BRAIN_DB) as conn:
            conn.execute("""
                INSERT INTO favorites_snapshots
                (snapshot_date, favorites_list, wave_groups, signal_clusters,
                 top_correlations, cadence_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot_date,
                json.dumps(sorted(favorites_list)),
                json.dumps(rhythm_data.get('clusters', {}).get('temporal', {}).get('groups', [])),
                json.dumps(rhythm_data.get('clusters', {}).get('signal', {}).get('groups', [])),
                json.dumps(rhythm_data.get('clusters', {}).get('return_correlation', {}).get('top_pairs', [])),
                json.dumps(rhythm_data.get('cadence', {})),
            ))
            conn.commit()
        return True
    except Exception as e:
        log(f"Snapshot save error: {e}")
        return False


def run():
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("Another instance running — skipping")
        return

    try:
        # Load rhythm data
        try:
            rhythm_data = json.loads(Path(RHYTHM_FILE).read_text())
        except Exception as e:
            log(f"Cannot load rhythm data: {e}")
            return

        # Load current favorites
        try:
            from hermes_constants import FAVORITES
            favorites_list = set(FAVORITES)
        except Exception:
            favorites_list = set()

        # Init hebbian engine and snapshot table
        engine = get_hebbian()
        ensure_snapshot_table()

        clusters = rhythm_data.get('clusters', {})
        cadence = rhythm_data.get('cadence', {})

        # ── Learn wave siblings ──────────────────────────────────────────
        temporal = clusters.get('temporal', {})
        n_wave = learn_wave_siblings(engine, temporal.get('groups', []))
        log(f"Learned {n_wave} wave sibling synapses")

        # ── Learn signal clusters ────────────────────────────────────────
        signal = clusters.get('signal', {})
        n_signal = learn_signal_clusters(engine, signal.get('groups', []))
        log(f"Learned {n_signal} signal cluster associations")

        # ── Learn regime associations ────────────────────────────────────
        regime = clusters.get('regime', {})
        n_regime = learn_regime_associations(engine, regime.get('matrix', {}))
        log(f"Learned {n_regime} regime associations")

        # ── Weaken anti-correlations ─────────────────────────────────────
        corr = clusters.get('return_correlation', {})
        n_weak = weaken_anti_correlations(engine, corr.get('top_pairs', []))
        log(f"Weakened {n_weak} anti-correlated synapses")

        # ── Learn cadence patterns ───────────────────────────────────────
        n_cadence = learn_cadence_patterns(engine, cadence)
        log(f"Learned {n_cadence} cadence pattern concepts")

        # ── Save snapshot ────────────────────────────────────────────────
        if save_snapshot(rhythm_data, favorites_list):
            log("Saved favorites snapshot to brain.db")

        # ── Summary ──────────────────────────────────────────────────────
        total = n_wave + n_signal + n_regime + n_weak + n_cadence
        log(f"Hebbian sync complete: {total} total operations "
            f"(wave={n_wave}, signal={n_signal}, regime={n_regime}, "
            f"weakened={n_weak}, cadence={n_cadence})")

    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


from pathlib import Path

if __name__ == '__main__':
    run()
