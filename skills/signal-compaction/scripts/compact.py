#!/usr/bin/env python3
"""
Signal Compaction — Clean up stale signals and rebuild hotset.json

Usage:
  python3 compact.py              # dry-run (audit only)
  python3 compact.py --expire     # expire stale PENDING/APPROVED/WAIT (>3h)
  python3 compact.py --archive    # expire + DELETE old SKIPPED/EXPIRED (>24h)
  python3 compact.py --rebuild    # rebuild hotset.json only
  python3 compact.py --full      # expire + archive + rebuild (full compaction)

Safety:
  - Stale window for PENDING/APPROVED/WAIT = 3 hours (matches _load_hot_rounds)
  - Archive cutoff for SKIPPED/EXPIRED = 24 hours
  - Backup DB before any DELETE operation
  - hotset.json only overwritten after successful rebuild
"""

import sys, os, time, json, sqlite3, shutil, argparse
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
SIGNALS_DB    = "/root/.hermes/data/signals_hermes_runtime.db"
HOTSET_FILE   = "/var/www/hermes/data/hotset.json"
HOTSET_TS_FILE = "/var/www/hermes/data/hotset_last_updated.json"
LOG_FILE      = "/var/www/hermes/logs/compaction.log"

# ── Time windows ───────────────────────────────────────────────────────────────
STALE_HOURS   = 3       # PENDING/APPROVED/WAIT older than this → EXPIRED
ARCHIVE_HOURS = 24      # SKIPPED/EXPIRED older than this → DELETE

# ── Deps (lazy import) ────────────────────────────────────────────────────────
sys.path.insert(0, "/root/.hermes/scripts")


def log(msg, tag="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_conn():
    return sqlite3.connect(SIGNALS_DB)


# ── Audit ──────────────────────────────────────────────────────────────────────

def audit():
    """Print current signal state."""
    conn = get_conn()
    cur = conn.cursor()

    # By decision state
    cur.execute("""
        SELECT decision,
               COUNT(*) as cnt,
               MIN(created_at) as oldest,
               MAX(created_at) as newest
        FROM signals
        GROUP BY decision
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()

    print("\n" + "=" * 60)
    print("SIGNAL AUDIT")
    print("=" * 60)
    print(f"{'State':<12} {'Count':>7} {'Oldest':>22} {'Newest':>22}")
    print("-" * 65)
    for r in rows:
        print(f"{str(r[0]):<12} {r[1]:>7} {str(r[2]):>22} {str(r[3]):>22}")

    total = sum(r[1] for r in rows)
    print("-" * 65)
    print(f"{'TOTAL':<12} {total:>7}")

    # Stale breakdown: PENDING/APPROVED/WAIT older than STALE_HOURS
    cur.execute(f"""
        SELECT decision, COUNT(*) as cnt
        FROM signals
        WHERE decision IN ('PENDING', 'APPROVED', 'WAIT')
          AND created_at < datetime('now', '-{STALE_HOURS} hours')
    """)
    stale = cur.fetchall()
    print(f"\nStale signals (> {STALE_HOURS}h old, PENDING/APPROVED/WAIT):")
    if stale:
        for r in stale:
            print(f"  {str(r[0]):<12} {r[1]:>7}")
    else:
        print("  (none)")

    # Old dead signals
    cur.execute(f"""
        SELECT COALESCE(decision, 'NULL') as decision, COUNT(*) as cnt
        FROM signals
        WHERE decision IN ('SKIPPED', 'EXPIRED')
          AND created_at < datetime('now', '-{ARCHIVE_HOURS} hours')
        GROUP BY COALESCE(decision, 'NULL')
    """)
    old_dead = cur.fetchall()
    print(f"\nOld dead signals (> {ARCHIVE_HOURS}h old, SKIPPED/EXPIRED):")
    if old_dead:
        for r in old_dead:
            print(f"  {str(r[0]):<12} {r[1]:>7}")
    else:
        print("  (none)")

    # Hot-set current state
    if os.path.exists(HOTSET_FILE):
        with open(HOTSET_FILE) as f:
            hs = json.load(f)
        print(f"\nHot-set ({len(hs.get('hotset', []))} tokens):")
        for h in hs.get("hotset", []):
            print(f"  {h['token']:10} {h['direction']:6} conf={h['confidence']:.0f}  "
                  f"rc={h.get('review_count', 0)}  {h.get('signal_type', '')}")
        print(f"  Updated: {datetime.fromtimestamp(hs.get('timestamp', 0))}")
    else:
        print("\nHot-set: (file not found)")

    conn.close()


# ── Expire stale signals ───────────────────────────────────────────────────────

def expire_stale(dry_run=True):
    """Mark PENDING/APPROVED/WAIT signals older than STALE_HOURS as EXPIRED."""
    conn = get_conn()
    cur = conn.cursor()

    # Count first
    cur.execute(f"""
        SELECT COALESCE(decision, 'NULL') as decision, COUNT(*) as cnt
        FROM signals
        WHERE decision IN ('PENDING', 'APPROVED', 'WAIT')
          AND created_at < datetime('now', '-{STALE_HOURS} hours')
        GROUP BY COALESCE(decision, 'NULL')
    """)
    counts = cur.fetchall()
    total = sum(r[1] for r in counts)

    if total == 0:
        print(f"\nNo stale PENDING/APPROVED/WAIT signals found (>{STALE_HOURS}h old)")
        conn.close()
        return 0

    print(f"\nExpiring {total} stale signals (>{STALE_HOURS}h old):")
    for r in counts:
        print(f"  {str(r[0]):<12} {r[1]:>7}")

    if dry_run:
        print("  [DRY RUN — no changes]")
        conn.close()
        return total

    # Perform update
    cur.execute(f"""
        UPDATE signals
        SET decision = 'EXPIRED',
            executed = 1,
            decision_reason = 'compaction_stale',
            updated_at = CURRENT_TIMESTAMP
        WHERE decision IN ('PENDING', 'APPROVED', 'WAIT')
          AND created_at < datetime('now', '-{STALE_HOURS} hours')
    """)
    conn.commit()
    affected = cur.rowcount
    print(f"  [APPLIED] {affected} signals marked EXPIRED")
    conn.close()
    return affected


# ── Archive old dead signals ───────────────────────────────────────────────────

def archive_old():
    """DELETE SKIPPED/EXPIRED signals older than ARCHIVE_HOURS (backup first)."""
    conn = get_conn()
    cur = conn.cursor()

    # Count first
    cur.execute(f"""
        SELECT decision, COUNT(*) as cnt
        FROM signals
        WHERE decision IN ('SKIPPED', 'EXPIRED')
          AND created_at < datetime('now', '-{ARCHIVE_HOURS} hours')
        GROUP BY decision
    """)
    counts = cur.fetchall()
    total = sum(r[1] for r in counts)

    if total == 0:
        print(f"\nNo old SKIPPED/EXPIRED signals to archive (>{ARCHIVE_HOURS}h old)")
        conn.close()
        return 0

    print(f"\nArchiving {total} old signals (>{ARCHIVE_HOURS}h old):")
    for r in counts:
        print(f"  {r[0]:<12} {r[1]:>7}")

    # Backup first
    backup = f"{SIGNALS_DB}.bak.{int(time.time())}"
    shutil.copy2(SIGNALS_DB, backup)
    print(f"  Backup: {backup}")

    # Delete
    cur.execute(f"""
        DELETE FROM signals
        WHERE decision IN ('SKIPPED', 'EXPIRED')
          AND created_at < datetime('now', '-{ARCHIVE_HOURS} hours')
    """)
    conn.commit()
    deleted = cur.rowcount
    print(f"  [APPLIED] {deleted} signals DELETED")
    conn.close()
    return deleted


# ── Rebuild hot-set ────────────────────────────────────────────────────────────

def rebuild_hotset():
    """Replicate _load_hot_rounds() query and rewrite hotset.json."""
    # Lazy-load dependencies
    try:
        from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
        from tokens import is_solana_only
    except Exception as e:
        print(f"[WARN] Could not import blacklist/solana filters: {e}")
        SHORT_BLACKLIST = set()
        LONG_BLACKLIST = set()
        def is_solana_only(t): return False

    conn = get_conn()
    cur = conn.cursor()

    # Build speed cache — query token_speeds table directly from DB
    # (SpeedTracker singleton is process-local and empty in compact.py's fresh process)
    speed_cache = {}
    try:
        sp_conn = sqlite3.connect(SIGNALS_DB, timeout=5)
        sp_cur = sp_conn.cursor()
        sp_cur.execute("""
            SELECT UPPER(token), price_velocity_5m, price_velocity_15m,
                   price_acceleration, speed_percentile, is_stale,
                   wave_phase, is_overextended, momentum_score
            FROM token_speeds
            WHERE momentum_score > 0
        """)
        for row in sp_cur.fetchall():
            tok, vel_5m, vel_15m, accel, sp_pctl, is_stale, wave, overext, mom = row
            speed_cache[tok] = {
                "price_velocity_5m": vel_5m,
                "price_velocity_15m": vel_15m,
                "price_acceleration": accel,
                "speed_percentile": sp_pctl,
                "is_stale": bool(is_stale),
                "wave_phase": wave or "neutral",
                "is_overextended": bool(overext),
                "momentum_score": mom or 50.0,
            }
        sp_conn.close()
    except Exception as e:
        print(f"[WARN] Could not load token_speeds from DB: {e}")

    # Query — matches _load_hot_rounds() hot-set SELECT
    cur.execute("""
        SELECT token, direction,
               (SELECT signal_type FROM signals s2
                WHERE s2.token = signals.token
                  AND s2.direction = signals.direction
                  AND s2.decision IN ('PENDING','APPROVED','WAIT')
                  AND s2.executed = 0
                  AND s2.review_count >= 1
                  AND s2.created_at > datetime('now','-3 hours')
                ORDER BY s2.confidence DESC LIMIT 1) as signal_type,
               MAX(confidence) as confidence,
               MAX(compact_rounds) as compact_rounds,
               MAX(survival_score) as survival_score,
               MAX(z_score_tier) as z_score_tier,
               MAX(z_score) as z_score,
               MAX(review_count) as review_count
        FROM signals
        WHERE decision IN ('PENDING','APPROVED','WAIT')
          AND executed = 0
          AND review_count >= 1
          AND created_at > datetime('now', '-3 hours')
        GROUP BY token, direction
        HAVING MAX(confidence) >= 50
        ORDER BY MAX(survival_score) DESC, MAX(confidence) DESC
        LIMIT 50
    """)
    rows = cur.fetchall()
    conn.close()

    hotset = []
    for r in rows:
        token = r[0]
        direction = r[1]

        # Apply blacklist filters
        if direction.upper() == "SHORT" and token in SHORT_BLACKLIST:
            print(f"  [FILTER] {token} SHORT — in SHORT_BLACKLIST")
            continue
        if direction.upper() == "LONG" and token in LONG_BLACKLIST:
            print(f"  [FILTER] {token} LONG — in LONG_BLACKLIST")
            continue
        if is_solana_only(token):
            print(f"  [FILTER] {token} — Solana-only")
            continue

        spd = speed_cache.get(token, {})
        conf = float(r[3]) if r[3] else 0.0
        momentum = spd.get("momentum_score", 50.0)

        # T's filters: skip if confidence < 70% OR speed (momentum) = 0%
        if conf < 70.0:
            print(f"  [FILTER] {token} {direction} conf={conf:.0f}% — below 70% threshold")
            continue
        if momentum == 0.0:
            print(f"  [FILTER] {token} {direction} speed=0% — momentum stalled")
            continue

        hotset.append({
            "token": token,
            "direction": direction,
            "signal_type": r[2],
            "confidence": conf,
            "compact_rounds": r[4] or 0,
            "survival_score": float(r[5]) if r[5] else 0.0,
            "z_score_tier": r[6],
            "z_score": float(r[7]) if r[7] is not None else 0.0,
            "review_count": r[8] or 0,
            "wave_phase": spd.get("wave_phase", "neutral"),
            "is_overextended": spd.get("is_overextended", False),
            "price_acceleration": spd.get("price_acceleration", 0.0),
            "price_velocity_5m": spd.get("price_velocity_5m", 0.0),
            "momentum_score": momentum,
        })

    # Write atomically: temp file then rename
    tmp = HOTSET_FILE + f".tmp.{int(time.time())}"
    with open(tmp, "w") as f:
        json.dump({"hotset": hotset, "timestamp": time.time()}, f, indent=2)
    os.replace(tmp, HOTSET_FILE)

    # Update timestamp file
    with open(HOTSET_TS_FILE, "w") as f:
        json.dump({"last_compaction_ts": time.time()}, f)

    print(f"\nHot-set rebuilt: {len(hotset)} tokens → {HOTSET_FILE}")
    for h in hotset:
        print(f"  {h['token']:10} {h['direction']:6} conf={h['confidence']:.0f}  "
              f"rc={h['review_count']}  {h.get('signal_type', '')}")

    return len(hotset)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Signal Compaction")
    parser.add_argument("--expire", action="store_true",
                        help="Expire stale PENDING/APPROVED/WAIT signals (3h+ old)")
    parser.add_argument("--archive", action="store_true",
                        help="DELETE old SKIPPED/EXPIRED signals (24h+ old) — requires --expire")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild hotset.json only (no DB changes)")
    parser.add_argument("--full", action="store_true",
                        help="Full compaction: expire + archive + rebuild")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("SIGNAL COMPACTION")
    print("=" * 60)

    if args.full:
        print("\n[MODE] FULL — expire + archive + rebuild")
    elif args.expire and args.archive:
        print("\n[MODE] EXPIRE + ARCHIVE")
    elif args.expire:
        print("\n[MODE] EXPIRE ONLY")
    elif args.rebuild:
        print("\n[MODE] REBUILD HOT-SET ONLY")
    else:
        print("\n[MODE] AUDIT ONLY (dry-run)")

    # ── Audit always runs first ───────────────────────────────────────────────
    audit()

    if args.full:
        expire_stale(dry_run=False)
        archive_old()
        rebuild_hotset()

    elif args.expire and args.archive:
        expire_stale(dry_run=False)
        archive_old()

    elif args.expire:
        expire_stale(dry_run=False)

    elif args.rebuild:
        rebuild_hotset()

    else:
        print("\n[DRY RUN] No changes made.")
        print(f"Run with --expire to expire stale signals,")
        print(f"       --full to expire + archive + rebuild.")
        print(f"       --rebuild to rebuild hot-set only.")

    print()


if __name__ == "__main__":
    main()
