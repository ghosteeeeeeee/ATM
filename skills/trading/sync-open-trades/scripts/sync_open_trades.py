#!/usr/bin/env python3
"""
sync_open_trades.py — Reconcile paper and brain open positions against live HL.
Close orphaned entries (exist in paper/brain but not on HL) from both stores.
No real HL trades are placed.
"""
import sys, json, time, psycopg2
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl

PAPER_JSON = "/var/www/hermes/data/trades.json"
BRAIN_DB   = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")

# ── HL ────────────────────────────────────────────────────────────────────────

def get_hype_positions():
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log(f"Failed to fetch HL positions: {e}", "WARN")
        return {}

# ── Paper trades.json ─────────────────────────────────────────────────────────

def get_paper_positions():
    try:
        with open(PAPER_JSON) as f:
            data = json.load(f)
        positions = []
        for p in data.get("open", []):
            positions.append({
                "token":     p.get("token"),
                "direction": p.get("direction"),
                "entry":     p.get("entry"),
                "current":   p.get("current", p.get("entry")),
                "pnl_usdt":  p.get("pnl_usdt", 0),
                "opened":    p.get("opened", ""),
                "exchange":  p.get("exchange", ""),
            })
        return positions
    except Exception as e:
        log(f"Failed to load paper trades: {e}", "FAIL")
        return []

def close_paper_orphaned(orphaned: list, dry_run: bool = True):
    """Remove orphaned positions from trades.json open list."""
    if not orphaned:
        return 0
    with open(PAPER_JSON) as f:
        data = json.load(f)

    removed = []
    for orphan in orphaned:
        token = orphan["token"]
        new_open = [p for p in data["open"] if p.get("token") != token]
        if len(new_open) < len(data["open"]):
            closed_entry = {
                "token":       token,
                "direction":   orphan["direction"],
                "entry":       orphan["entry"],
                "exit":        orphan.get("current", orphan["entry"]),
                "pnl_pct":     0.0,
                "pnl_usdt":    0.0,
                "closed_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "reason":      "orphan_sync",
            }
            data["open"] = new_open
            data.setdefault("closed", []).append(closed_entry)
            data["open_count"]   = len(data["open"])
            data["closed_count"] = len(data.get("closed", []))
            data["updated"] = datetime.now().isoformat() + "Z"
            removed.append(token)
            tag = "DRY" if dry_run else "PASS"
            log(f"  [{tag}] Closed paper: {token} {orphan['direction']} @ {orphan['entry']:.6f}", "WARN" if not dry_run else "INFO")

    if not dry_run and removed:
        with open(PAPER_JSON, "w") as f:
            json.dump(data, f, indent=2)
        log(f"Updated {PAPER_JSON}", "PASS")

    return len(removed)

# ── Brain PostgreSQL ──────────────────────────────────────────────────────────

def get_brain_positions():
    conn = psycopg2.connect(**BRAIN_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, leverage, open_time
            FROM trades
            WHERE status = 'open'
              AND paper = FALSE
              AND server = 'Hermes'
              AND exchange = 'Hyperliquid'
            ORDER BY token
        """)
        rows = cur.fetchall()
        return [{'id': r[0], 'token': r[1], 'direction': r[2],
                 'entry_price': float(r[3]), 'leverage': r[4], 'open_time': r[5]} for r in rows]
    except Exception as e:
        log(f"Failed to query brain DB: {e}", "FAIL")
        return []
    finally:
        conn.close()

def close_brain_trade(trade_id: int, token: str, exit_price: float, dry_run: bool = True):
    """Close a trade in brain DB with zero PnL (never was on HL)."""
    if dry_run:
        log(f"  [DRY] Would close brain trade {trade_id}: {token} @ exit={exit_price}", "WARN")
        return True

    conn = psycopg2.connect(**BRAIN_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET
                status      = 'closed',
                close_time  = NOW(),
                exit_price  = %s,
                pnl_usdt    = 0,
                pnl_pct     = 0,
                exit_reason = 'orphan_sync',
                close_reason= 'orphan_sync',
                updated_at  = NOW()
            WHERE id = %s AND status = 'open'
        """, (exit_price, trade_id))
        conn.commit()
        log(f"  Closed brain trade {trade_id}: {token}", "PASS")
        return True
    except Exception as e:
        log(f"  Failed to close brain trade {trade_id}: {e}", "FAIL")
        return False
    finally:
        conn.close()

def close_brain_orphaned(orphaned: list, dry_run: bool = True):
    """Close orphaned trades in brain DB."""
    if not orphaned:
        return 0
    count = 0
    for pos in orphaned:
        if close_brain_trade(pos['id'], pos['token'], pos['entry_price'], dry_run=dry_run):
            count += 1
    return count

# ── Main ──────────────────────────────────────────────────────────────────────

def find_orphaned(paper_positions, brain_positions, hype_positions):
    """Return (paper_orphaned, brain_orphaned) lists."""
    hype_tokens = set(hype_positions.keys())

    # Paper orphaned
    paper_orphaned = []
    for p in paper_positions:
        if p.get("exchange", "").lower() != "hyperliquid":
            continue
        if p["token"] not in hype_tokens:
            paper_orphaned.append(p)
            log(f"  {p['token']}: ORPHANED in paper ({p['direction']} @ {p['entry']:.6f}) — no HL position", "WARN")
        else:
            log(f"  {p['token']}: confirmed on HL ✓", "INFO")

    # Brain orphaned
    brain_orphaned = []
    for b in brain_positions:
        if b["token"] not in hype_tokens:
            brain_orphaned.append(b)
            log(f"  {b['token']}: ORPHANED in brain ({b['direction']} @ {b['entry_price']:.6f}) — no HL position", "WARN")
        else:
            log(f"  {b['token']}: confirmed on HL ✓", "INFO")

    return paper_orphaned, brain_orphaned

def main(apply: bool = False):
    dry_run = not apply
    mode    = "DRY" if dry_run else "APPLY"
    log(f"=== Sync Open Trades | Mode: {mode} ===", "INFO")

    # 1. Fetch current state
    log("Fetching HL positions...", "INFO")
    hype = get_hype_positions()
    log(f"  HL open: {len(hype)} — {sorted(hype.keys())}", "INFO")

    log("Loading paper positions...", "INFO")
    paper = get_paper_positions()
    paper_hl = [p for p in paper if p.get("exchange","").lower()=="hyperliquid"]
    log(f"  Paper open (Hyperliquid): {len(paper_hl)}", "INFO")

    log("Loading brain positions...", "INFO")
    brain = get_brain_positions()
    log(f"  Brain open: {len(brain)}", "INFO")

    if not hype:
        log("WARNING: Could not reach HL — proceeding with paper+brain orphan check only", "WARN")

    # 2. Find orphaned
    log("\nFinding orphaned positions...", "WARN")
    paper_orphaned, brain_orphaned = find_orphaned(paper_hl, brain, hype)

    total_orphaned = len(paper_orphaned) + len(brain_orphaned)
    if total_orphaned == 0:
        log("Paper and brain are fully in sync with HL ✓", "INFO")
        return

    log(f"\nOrphaned: {len(paper_orphaned)} in paper, {len(brain_orphaned)} in brain", "WARN")

    # 3. Close orphaned
    if dry_run:
        log(f"\n[DRY RUN — no changes made]", "WARN")
    else:
        log(f"\n[APPLYING CHANGES]", "WARN")

    n_paper = close_paper_orphaned(paper_orphaned, dry_run=dry_run)
    n_brain = close_brain_orphaned(brain_orphaned, dry_run=dry_run)

    # 4. Summary
    prefix = "Dry-run: " if dry_run else ""
    log(f"\n{prefix}Closed {n_paper} from paper, {n_brain} from brain", "PASS")
    if dry_run:
        log("Run with --apply to execute:", "WARN")
        log("  python3 skills/trading/sync-open-trades/scripts/sync_open_trades.py --apply", "WARN")

if __name__ == "__main__":
    apply = "--apply" in sys.argv
    main(apply=apply)
