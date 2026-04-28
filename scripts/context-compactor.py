#!/usr/bin/env python3
"""
context-compactor.py — Auto-refresh CONTEXT.md Quick Status + Critical Flags every 30 min.

Patches in-place (sed-style), never full rewrite.
Uses flock locking before writing.

Lock: /root/.hermes/locks/context.md.lock
Timeout: 30s wait, 5s polling, SKIPPED on timeout.
"""
import sys, os, re, time, subprocess, json
sys.path.insert(0, '/root/.hermes/scripts')

from paths import *
CONTEXT_FILE         = '/root/.hermes/CONTEXT.md'
ATM_ARCHITECTURE_FILE = '/root/.hermes/ATM/ATM-Architecture.md'
LOCK_FILE    = '/root/.hermes/locks/context.md.lock'
MAX_WAIT     = 30
POLL_INT     = 5

# ── helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[context-compactor] {msg}", file=sys.stderr)

def get_pipeline_status():
    """Check if hermes-pipeline is running via cron jobs.json."""
    try:
        with open('/root/.hermes/cron/jobs.json') as f:
            jobs = json.load(f).get('jobs', [])
        for j in jobs:
            if j['name'] == 'hermes-pipeline':
                last = j.get('last_status', 'unknown')
                return f"PIPELINE: {last.upper()} (last run {j.get('last_run_at', '?')[-8:-1]})"
    except Exception as e:
        return f"PIPELINE: UNKNOWN ({e})"
    return "PIPELINE: not found in cron"

def get_wasp_status():
    """Check WASP errors/warnings from latest report."""
    try:
        import glob
        reports = sorted(glob.glob('/root/.hermes/reports/*.txt'), key=os.path.getmtime)
        if reports:
            latest = reports[-1]
            with open(latest) as f:
                content = f.read()
            errors = content.count('ERROR')
            warnings = content.count('WARNING')
            return f"WASP: {errors} ERR, {warnings} warnings ✅" if errors == 0 else f"WASP: {errors} ERR, {warnings} warnings ⚠️"
    except:
        pass
    return "WASP: unknown"

def get_live_trading_status():
    """Check hype_live_trading.json."""
    try:
        with open(LIVESWITCH_FILE) as f:
            d = json.load(f)
        state = d.get('live_trading_enabled', d.get('enabled', 'UNKNOWN'))
        return f"LIVE TRADING: {'ON ✅' if state else 'OFF ⚠️'}"
    except:
        return "LIVE TRADING: unknown"

def get_position_summary():
    """Get position count + regime from brain DB or trades.json."""
    try:
        # Try brain PostgreSQL
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                                  user='postgres', password='postgres')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), status FROM trades WHERE server='Hermes' GROUP BY status")
        rows = cur.fetchall()
        open_ct = sum(r[0] for r in rows if r[1] == 'open')
        closed_ct = sum(r[0] for r in rows if r[1] == 'closed')
        conn.close()
        return f"POSITIONS: {open_ct} open, {closed_ct} closed (brain)"
    except Exception as e:
        # Fallback to trades.json
        try:
            with open(TRADES_JSON) as f:
                trades = json.load(f)
            open_trades = [t for t in trades if t.get('status') == 'open']
            return f"POSITIONS: {len(open_trades)} open (trades.json)"
        except:
            pass
    return "POSITIONS: unknown"

def get_regime():
    """Get current regime from regime scanner or hotset."""
    try:
        with open(HOTSET_FILE) as f:
            hs = json.load(f)
        regime = hs.get('regime', 'UNKNOWN')
        return f"REGIME: {regime}"
    except:
        return "REGIME: unknown"

def get_quick_status_line():
    """Build the new Quick Status block content (just lines, no backticks)."""
    pipeline = get_pipeline_status()
    wasp     = get_wasp_status()
    live     = get_live_trading_status()
    pos      = get_position_summary()
    regime   = get_regime()
    ts       = time.strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        f"{pipeline} | {wasp}",
        f"{live} | {pos}",
        f"{regime}",
        f"Updated: {ts}",
    ]
    return "\n".join(lines)

def get_critical_flags_block():
    """Build the Critical Flags block content."""
    flags = []
    # Check live trading
    try:
        with open(LIVESWITCH_FILE) as f:
            d = json.load(f)
        if not d.get('live_trading_enabled', d.get('enabled', True)):
            flags.append("- ⚠️ LIVE TRADING IS OFF — KILL SWITCH ACTIVE")
        else:
            flags.append("- hype_live_trading.json = ON (KILL SWITCH arm disarmed)")
    except:
        flags.append("- hype_live_trading.json: unknown")

    # Check pipeline
    try:
        with open('/root/.hermes/cron/jobs.json') as f:
            jobs = json.load(f).get('jobs', [])
        error_jobs = [j['name'] for j in jobs if j.get('last_status') == 'error']
        if error_jobs:
            flags.append(f"- ⚠️ Cron jobs with errors: {', '.join(error_jobs)}")
    except:
        pass

    # Check DB freshness
    try:
        age_hrs = (time.time() - os.path.getmtime('/root/.hermes/state.db')) / 3600
        if age_hrs > 1:
            flags.append(f"- ⚠️ state.db stale: {age_hrs:.1f}h old")
    except:
        pass

    if not flags:
        flags.append("- All systems nominal")
        flags.append("- ⚠️ DO NOT change hype_live_trading.json unless T requests")

    return "\n".join(f"- {f}" for f in flags)

# ── lock + patch ─────────────────────────────────────────────────────────────

def acquire_lock():
    """Acquire exclusive lock with timeout. Returns fd or None."""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
    for _ in range(MAX_WAIT // POLL_INT):
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            open(LOCK_FILE, 'w').write(str(os.getpid()))
            return fd
        except BlockingIOError:
            try:
                holder = open(LOCK_FILE).read().strip()
            except:
                holder = "?"
            log(f"Locked by [{holder}], waiting...")
            time.sleep(POLL_INT)
    log(f"SKIPPED: context.md lock held after {MAX_WAIT}s")
    os.close(fd)
    return None

def release_lock(fd):
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    try:
        os.unlink(LOCK_FILE)
    except:
        pass

def patch_context_file(quick_status, critical_flags, timestamp):
    """Patch Quick Status and Critical Flags sections in-place using regex."""
    try:
        with open(CONTEXT_FILE, 'r') as f:
            content = f.read()
    except Exception as e:
        log(f"ERROR: cannot read CONTEXT.md: {e}")
        return False

    # Patch ## Quick Status block
    # Match from "## Quick Status\n```\n" to the next "```\n"
    # The ## Quick Status block has format:
    # ## Quick Status\n    # ```\n    # content...\n    # ```
    # We replace the entire content between the outer ``` delimiters
    qs_pattern = r'(## Quick Status\n```\n).*?(\n```\n)'
    qs_replacement = f'\\1{quick_status}\\2'
    new_content, n_qs = re.subn(qs_pattern, qs_replacement, content, flags=re.DOTALL)
    if n_qs == 0:
        log("WARNING: Quick Status block not found, skipping qs patch")
    else:
        log(f"Patched Quick Status ({n_qs} replacement)")

    # Patch Critical Flags block (look for "## Critical Flags\n" followed by list)
    # We update the flags section within the "Recurring Remember Rules" area
    # or add a Critical Flags section if not present
    cf_pattern = r'(## Critical Flags\n)\n(.*?)(\n\n|\Z)'
    cf_replacement = f'\\1\n{critical_flags}\\3'
    new_content2, n_cf = re.subn(cf_pattern, cf_replacement, new_content, flags=re.DOTALL)
    if n_cf == 0:
        # Try inline patch — look for "- hype_live_trading" line and update around it
        log("WARNING: Critical Flags section not found in expected format, skipping")

    # Patch timestamp at bottom
    ts_pattern = r'^\*Updated:.*UTC\*$'
    ts_replacement = f"*Updated: {timestamp} UTC*"
    new_content3, n_ts = re.subn(ts_pattern, ts_replacement, new_content2, flags=re.MULTILINE)
    if n_ts == 0:
        # Try to append
        new_content3 = new_content2.rstrip() + f"\n*Updated: {timestamp} UTC*\n"
        log("Appended timestamp")
    else:
        log(f"Patched timestamp ({n_ts} replacement)")

    # ── ATM Architecture Snapshot: REPLACE in-place, don't append ─────────────────
    # CONTEXT.md already references ATM-Architecture.md at the top.
    # The static content ends at ## ATM_SNAP (line 35), the snapshot is everything after.
    # On every run: find the static/snapshot boundary, remove old snapshot, insert fresh.
    try:
        with open(ATM_ARCHITECTURE_FILE, 'r') as f:
            arch_content = f.read().strip()

        # Anchor: ## ATM_SNAP (section header). Using a ## header as anchor lets us
        # match the entire snapshot block with \n## ATM_SNAP\n.*?(?=\n## |\Z) reliably,
        # since no ## can appear inside the architecture content legitimately.
        SNAP_ANCHOR = '## ATM_SNAP'
        SNAP_HEADER = '# ATM ARCHITECTURE SNAPSHOT (auto-generated, see: ATM-Architecture.md)'

        # ── 1. Find the LAST ## ATM_SNAP in the file (the one we appended last run) ──
        # Using last occurrence is critical: the snapshot content itself contains
        # the same section headers as static content (## Data Flow, ## Pipeline, etc.),
        # so a forward search would hit the static copy's header and fail to clean up.
        all_snap_matches = list(re.finditer(r'\n## ATM_SNAP\n', new_content3))
        if all_snap_matches:
            # Use the LAST occurrence as our boundary — that's the one we appended
            snap_match = all_snap_matches[-1]
            static_prefix = new_content3[:snap_match.start()]
            log(f"Found {len(all_snap_matches)} ATM_SNAP anchor(s), using the last one at pos {snap_match.start()}")
        else:
            # No anchor yet — find last HR as boundary
            last_hr = new_content3.rfind('\n---\n')
            static_prefix = new_content3[:last_hr] if last_hr >= 0 else new_content3
            log("No ## ATM_SNAP anchor found, using last HR boundary")

        # ── 2. Remove old snapshot block ──────────────────────────────────────────
        # Remove EVERYTHING from the LAST ## ATM_SNAP to end of file
        # (the snapshot we appended last run, which may have duplicated content)
        old_snap_start = all_snap_matches[-1].start() if all_snap_matches else -1
        if old_snap_start >= 0:
            # Verify this ## ATM_SNAP is followed by our header marker
            remainder = new_content3[old_snap_start:]
            SNAP_HEADER = '# ATM ARCHITECTURE SNAPSHOT (auto-generated'
            if SNAP_HEADER in remainder:
                # Truncate at this anchor — remove the old snapshot entirely
                new_content3 = new_content3[:old_snap_start]
                log("Removed old ATM Architecture snapshot (confirmed by header)")

        # ── 3. Insert fresh snapshot after static prefix ──────────────────────────
        new_content3 = static_prefix + '\n## ATM_SNAP\n' + SNAP_HEADER + '\n' + arch_content + '\n'
        log("Inserted ATM Architecture snapshot")
    except Exception as e:
        log(f"WARNING: could not manage ATM Architecture: {e}")

    # Write back via lock
    fd = acquire_lock()
    if fd is None:
        return False
    try:
        with open(CONTEXT_FILE, 'w') as f:
            f.write(new_content3)
        # Save post-write hash so agents can verify at session start
        import hashlib
        with open(CONTEXT_FILE) as f:
            file_hash = hashlib.md5(f.read().encode()).hexdigest()
        hash_file = '/root/.hermes/data/CONTEXT_MD_HASH.txt'
        with open(hash_file, 'w') as f:
            f.write(file_hash)
        log(f"CONTEXT.md patched successfully, hash={file_hash}")
        return True
    finally:
        release_lock(fd)

def main():
    log("Starting context-compactor run...")
    ts = time.strftime('%Y-%m-%d %H:%M')

    quick_status   = get_quick_status_line()
    critical_flags = get_critical_flags_block()

    success = patch_context_file(quick_status, critical_flags, ts)
    if success:
        log("Done.")
    else:
        log("SKIPPED — lock not acquired")

if __name__ == '__main__':
    main()
