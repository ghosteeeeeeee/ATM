#!/usr/bin/env python3
"""Archive and compact terminal signals from the Hermes runtime DB.

Archives to JSONL (one file per month) for audit/analysis, then deletes
archived rows and VACUUMs to reclaim space.

Usage:
    python3 archive-signals.py           # dry run (print what would be archived)
    python3 archive-signals.py --apply   # actually archive + delete + vacuum
    python3 archive-signals.py --stats   # just show current table stats
"""
import sqlite3, os, json, gzip, time
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_DB  = '/root/.hermes/data/signals_hermes_runtime.db'
ARCHIVE_DIR = '/root/.hermes/archive/signals'
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# WAIT is included because stale WAIT signals block hot-set auto-approvals
# (WASP flagged: "5 WAIT signals never re-reviewed" — same root cause)
ARCHIVABLE_DECISIONS = {'SKIPPED', 'EXPIRED', 'EXECUTED', 'COMPACTED', 'WAIT'}
CUTOFF_HOURS_APPROVED = 6    # archive APPROVED signals older than this
CUTOFF_HOURS_OTHERS   = 6    # archive SKIPPED/EXPIRED/EXECUTED/COMPACTED/WAIT older than this
CUTOFF_HOURS_PENDING  = 1    # archive PENDING signals older than this (stale, not worth keeping)


def get_stats(conn):
    rows = conn.execute('''
        SELECT decision, COUNT(*) as cnt,
               MIN(created_at), MAX(created_at)
        FROM signals
        GROUP BY decision
        ORDER BY cnt DESC
    ''').fetchall()
    print(f"{'Decision':<15} {'Count':>7}  {'Oldest':<26}  {'Newest':<26}")
    print("-" * 80)
    total = 0
    for r in rows:
        print(f"{r[0]:<15} {r[1]:>7}  {str(r[2]):<26}  {str(r[3]):<26}")
        total += r[1]
    print(f"{'TOTAL':<15} {total:>7}")
    print(f"\nDB size: {os.path.getsize(RUNTIME_DB) / 1024/1024:.1f} MB")


def archive_month(conn, rows, year, month):
    """Write rows to a gzipped JSONL file for the given year/month."""
    ym = f"{year}-{month:02d}"
    path = Path(ARCHIVE_DIR) / f"signals_{ym}.jsonl.gz"
    existing = set()
    if path.exists():
        # Skip rows already in this file (idempotent on re-run)
        with gzip.open(path, 'rt') as f:
            for line in f:
                try:
                    existing.add(json.loads(line)['id'])
                except Exception:
                    pass
    count = 0
    with gzip.open(path, 'at') as f:
        for row in rows:
            if row['id'] in existing:
                continue
            rec = {
                **row,
                'archived_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'archive_file': str(path),
            }
            f.write(json.dumps(rec) + '\n')
            count += 1
    return count


def run_archive(conn, dry_run=True):
    now = datetime.now(timezone.utc)
    total_archived = 0
    total_deleted = 0

    cols = [desc[0] for desc in conn.execute('SELECT * FROM signals LIMIT 0').description]

    # ── Gather rows to archive ─────────────────────────────────────────────
    to_archive = []

    # APPROVED older than cutoff
    rows = conn.execute(f'''
        SELECT * FROM signals
        WHERE decision = 'APPROVED'
          AND created_at < datetime('now', '-{CUTOFF_HOURS_APPROVED} hours')
    ''').fetchall()
    to_archive.extend([dict(zip(cols, r)) for r in rows])

    # ARCHIVABLE decisions older than cutoff (SKIPPED/EXPIRED/EXECUTED/COMPACTED/WAIT)
    placeholders = ','.join(['?'] * len(ARCHIVABLE_DECISIONS))
    rows = conn.execute(f'''
        SELECT * FROM signals
        WHERE decision IN ({placeholders})
          AND created_at < datetime('now', '-{CUTOFF_HOURS_OTHERS} hours')
    ''', tuple(ARCHIVABLE_DECISIONS)).fetchall()
    to_archive.extend([dict(zip(cols, r)) for r in rows])

    # PENDING older than 1 hour — stale, not worth keeping (they didn't make the cut)
    rows = conn.execute(f'''
        SELECT * FROM signals
        WHERE decision = 'PENDING'
          AND created_at < datetime('now', '-{CUTOFF_HOURS_PENDING} hours')
    ''').fetchall()
    to_archive.extend([dict(zip(cols, r)) for r in rows])

    if not to_archive:
        print("Nothing to archive.")
        return

    print(f"Rows to archive: {len(to_archive)}")
    if dry_run:
        print("DRY RUN — no changes made. Use --apply to archive for real.")
        print("\nSample rows:")
        for r in to_archive[:3]:
            print(f"  id={r['id']} token={r['token']} decision={r['decision']} created_at={r['created_at']}")
        return

    # ── Group by year/month and archive ─────────────────────────────────────
    by_ym = {}
    for r in to_archive:
        created_str = r.get('created_at', '')
        # Handle Unix timestamp stored as string (e.g. '1775779899') or bad data
        if created_str and created_str[0].isdigit() and len(created_str) >= 10:
            try:
                dt = datetime.fromtimestamp(int(created_str[:10]))
            except Exception:
                dt = datetime.now(timezone.utc)
        else:
            try:
                dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            except Exception:
                dt = datetime.now(timezone.utc)
        ym = dt.strftime('%Y-%m')
        by_ym.setdefault(ym, []).append(r)

    for ym, rows in sorted(by_ym.items()):
        year, month = map(int, ym.split('-'))
        count = archive_month(conn, rows, year, month)
        total_archived += count
        print(f"  Archived {count} rows to signals_{ym}.jsonl.gz")

    # ── Delete archived rows ─────────────────────────────────────────────────
    ids = [r['id'] for r in to_archive]
    if ids:
        placeholders = ','.join(['?'] * len(ids))
        cur = conn.execute(f'DELETE FROM signals WHERE id IN ({placeholders})', ids)
        total_deleted = cur.rowcount
        conn.commit()
        print(f"Deleted {total_deleted} rows from runtime DB.")

    # ── VACUUM ───────────────────────────────────────────────────────────────
    print("Running VACUUM (reclaims space)...")
    t0 = time.time()
    conn.execute('VACUUM')
    elapsed = time.time() - t0
    size_after = os.path.getsize(RUNTIME_DB) / 1024/1024
    print(f"VACUUM done in {elapsed:.1f}s — DB now {size_after:.1f} MB")

    print(f"\nSummary: {total_archived} rows archived, {total_deleted} rows deleted.")
    return total_archived, total_deleted


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Archive and compact Hermes signals DB')
    parser.add_argument('--apply', action='store_true', help='Actually archive + delete + vacuum')
    parser.add_argument('--stats', action='store_true', help='Show stats and exit')
    parser.add_argument('--days', type=int, default=None,
                        help='Override cutoff hours for terminal decisions')
    args = parser.parse_args()

    conn = sqlite3.connect(RUNTIME_DB, timeout=60)
    conn.row_factory = sqlite3.Row

    if args.days:
        CUTOFF_HOURS_OTHERS = args.days * 24
        CUTOFF_HOURS_APPROVED = args.days * 24

    if args.stats:
        get_stats(conn)
    else:
        run_archive(conn, dry_run=not args.apply)

    conn.close()