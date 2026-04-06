#!/usr/bin/env python3
"""
purge_and_compact.py — Full signal pipeline reset + hot-set compaction.
1. Delete all non-EXECUTED signals from runtime DB (PENDING/APPROVED/WAIT/EXPIRED/SKIPPED)
2. Clear hotset.json
3. Run ai_decider.py to regenerate signals and build fresh hot-set with compaction
"""
import sys, os, time, json, subprocess
sys.path.insert(0, '/root/.hermes/scripts')

from signal_schema import _get_conn, _runtime

PAPER_JSON   = '/var/www/hermes/data/trades.json'
HOTSET_FILE  = '/var/www/hermes/data/hotset.json'

def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")

def count_signals():
    conn = _get_conn(_runtime())
    c = conn.cursor()
    c.execute("SELECT decision, COUNT(*) FROM signals GROUP BY decision")
    counts = dict(c.fetchall())
    c.execute("SELECT COUNT(*) FROM signals")
    total = c.fetchone()[0]
    conn.close()
    return counts, total

def purge_signals(dry_run=True):
    conn = _get_conn(_runtime())
    c = conn.cursor()
    # Count what will be purged
    c.execute("SELECT COUNT(*) FROM signals WHERE decision != 'EXECUTED'")
    to_purge = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signals WHERE decision == 'EXECUTED'")
    to_keep = c.fetchone()[0]
    if dry_run:
        log(f"[DRY] Would DELETE {to_purge} signals (keeping {to_keep} EXECUTED)", "WARN")
        conn.close()
        return to_purge
    c.execute("DELETE FROM signals WHERE decision != 'EXECUTED'")
    conn.commit()
    log(f"Deleted {c.rowcount} signals (kept {to_keep} EXECUTED)", "PASS")
    conn.close()
    return c.rowcount

def clear_hotset(dry_run=True):
    if dry_run:
        if os.path.exists(HOTSET_FILE):
            with open(HOTSET_FILE) as f:
                d = json.load(f)
            log(f"[DRY] Would clear hotset.json ({len(d.get('hotset', []))} tokens)", "WARN")
        else:
            log("[DRY] hotset.json does not exist", "WARN")
        return
    stub = {'hotset': [], 'timestamp': time.time()}
    with open(HOTSET_FILE, 'w') as f:
        json.dump(stub, f)
    log(f"Cleared hotset.json", "PASS")

def run_ai_decider():
    log("Running ai_decider.py (signal generation + hot-set compaction)...", "INFO")
    result = subprocess.run(
        [sys.executable, '/root/.hermes/scripts/ai_decider.py'],
        capture_output=True, text=True, timeout=300
    )
    # Print last 60 lines of output
    lines = (result.stdout + result.stderr).split('\n')
    recent = [l for l in lines if l.strip()][-60:]
    for l in recent:
        print(l)
    log(f"ai_decider exit code: {result.returncode}", "PASS" if result.returncode == 0 else "FAIL")
    return result.returncode

def main():
    dry = "--dry" in sys.argv
    mode = "DRY" if dry else "APPLY"
    log(f"=== Purge + Compact | Mode: {mode} ===", "INFO")

    # 1. Count before
    before_counts, before_total = count_signals()
    log(f"Before: {before_total} total signals — {dict(before_counts)}", "INFO")

    # 2. Clear hotset
    clear_hotset(dry_run=dry)

    # 3. Purge signals
    n = purge_signals(dry_run=dry)

    if dry:
        log("\n[DRY RUN — no changes made]", "WARN")
        log(f"Run without --dry to apply:", "WARN")
        log(f"  python3 /root/.hermes/scripts/purge_and_compact.py", "WARN")
        return

    # 4. Count after
    after_counts, after_total = count_signals()
    log(f"After purge: {after_total} total signals — {dict(after_counts)}", "INFO")

    # 5. Run ai_decider to regenerate + compact
    log("\n=== Running ai_decider compaction ===", "INFO")
    rc = run_ai_decider()

    # 6. Show hotset result
    if os.path.exists(HOTSET_FILE):
        with open(HOTSET_FILE) as f:
            d = json.load(f)
        entries = d.get('hotset', [])
        log(f"\nHot-set result: {len(entries)} tokens in hotset.json", "PASS")
        for e in entries[:5]:
            log(f"  {e['token']:12} {e['direction']:5} conf={e['confidence']:.0f}% "
                f"sp={e.get('speed_percentile','?')} mom={e.get('momentum_score','?')}", "INFO")
        if len(entries) > 5:
            log(f"  ... +{len(entries)-5} more", "INFO")
    else:
        log("hotset.json not found after compaction", "WARN")

if __name__ == '__main__':
    main()
