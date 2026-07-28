#!/usr/bin/env python3
"""
Cut Loser — closes medium-loss positions (-0.5% to -3%) at random intervals.
Never touches profitable positions. A/B testable fire intervals (5-10min vs 10-18min).
"""
from paths import *
from hermes_constants import (
    CUT_LOSER_ENABLED, LOSS_MIN_PCT, LOSS_MAX_PCT,
    CUT_LOSER_MAX_CLOSE, SKIP_BOTTOM_PCT, CUT_LOSER_FIRE_WINDOWS
)
import sys, os, json, time, random, argparse
from pathlib import Path

from hermes_log import log
# ── Constants ─────────────────────────────────────────────────────────────────
LOG_FILE   = Path("/root/.hermes/logs/cut_loser.log")
CONFIG_FILE = Path(CUT_LOSER_CONFIG)
BRAIN_CMD   = "/root/.hermes/scripts/brain.py"

# ── Logging ───────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "ab_group": "B", "dry_run": False}

# ── Fire decision (random timer) ───────────────────────────────────────────────
def should_fire(ab_group: str, last_run_ts: float) -> bool:
    """Return True if enough minutes have passed since last_run_ts."""
    window = CUT_LOSER_FIRE_WINDOWS.get(ab_group, CUT_LOSER_FIRE_WINDOWS["B"])
    min_wait, max_wait = window
    jitter = random.uniform(0, 1)
    fire_interval_sec = (min_wait + (max_wait - min_wait) * jitter) * 60
    elapsed = time.time() - last_run_ts
    return elapsed >= fire_interval_sec

# ── Query open positions ────────────────────────────────────────────────────────
def get_losing_positions():
    """Return list of dicts for open positions with pnl_pct < 0."""
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                                password=BRAIN_PASSWORD, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, current_price, pnl_pct, open_time
            FROM trades
            WHERE server = 'Hermes'
              AND status = 'open'
              AND entry_price > 0
              AND current_price > 0
            ORDER BY pnl_pct ASC
        """)
        rows = cur.fetchall()
        conn.close()
        return [
            {"id": r[0], "token": r[1], "direction": r[2], "entry_price": float(r[3]),
             "current_price": float(r[4]), "pnl_pct": float(r[5]), "opened_at": r[6]}
            for r in rows
        ]
    except Exception as e:
        log(f"DB query error: {e}", "ERROR")
        return []

def filter_losing_positions(positions, min_pct=LOSS_MIN_PCT, max_pct=LOSS_MAX_PCT):
    """Compute live pnl_pct from entry_price vs current_price and filter to loss range."""
    filtered = []
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            if pos["direction"].upper() == "LONG":
                live_pnl = (pos["current_price"] - pos["entry_price"]) / pos["entry_price"] * 100
            else:
                live_pnl = (pos["entry_price"] - pos["current_price"]) / pos["entry_price"] * 100
            pos["live_pnl_pct"] = live_pnl
            # live_pnl is negative for losses; LOSS_MIN_PCT=-3.0 (catastrophic floor),
            # LOSS_MAX_PCT=-0.5 (threshold). Cut positions where:
            #   live_pnl <= -0.5  (loss worse than -0.5%) AND
            #   live_pnl >= -3.0  (not worse than -3%, not catastrophic)
            # Note: min_pct=-3.0 > max_pct=-0.5 on the number line (less negative).
            # Use explicit operators to avoid Python chained-comparison pitfall:
            #   a <= b <= c  ==  (a <= b) and (b <= c)  — fails here because -0.35 <= -0.5 is False.
            if (live_pnl <= max_pct) and (live_pnl >= min_pct):
                filtered.append(pos)
    return filtered

# ── Select positions to close (skip bottom SKIP_BOTTOM_PCT worst losers) ───────
def select_positions(positions, max_close=CUT_LOSER_MAX_CLOSE, skip_bottom_pct=SKIP_BOTTOM_PCT):
    if not positions:
        return []

    # Skip bottom losers (let them recover or get stopped out by ATR)
    skip_count = max(0, int(len(positions) * skip_bottom_pct / 100))
    candidates = positions[skip_count:]
    if not candidates:
        return []

    count = random.randint(1, min(max_close, len(candidates)))
    return random.sample(candidates, count)

# ── Close a position via brain.py + HL mirror ──────────────────────────────────
def close_position(trade_id: int, token: str, direction: str, pnl_pct: float, current_price: float, dry_run: bool):
    if dry_run:
        log(f"[DRY RUN] Would close id={trade_id} {token} {direction} @ {pnl_pct:.2f}% loss", "WARN")
        return True

    # Step 1: Close the HL position FIRST (prevents guardian from creating duplicate orphan trade)
    hl_fill_price = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import is_live_trading_enabled, close_position
        if is_live_trading_enabled():
            result = close_position(token.upper())
            if result.get("success"):
                log(f"  HL close OK: {token} (realized_pnl={result.get('hl_realized_pnl', 'N/A')})", "PASS")
                # Extract actual fill price from HL response
                try:
                    statuses = result.get("result", {}).get("response", {}).get("data", {}).get("statuses", [])
                    for s in statuses:
                        filled = s.get("filled", {})
                        avg_px = filled.get("avgPx")
                        if avg_px:
                            hl_fill_price = float(avg_px)
                            log(f"  HL fill price: ${hl_fill_price:.6f}", "INFO")
                            break
                except Exception:
                    pass
            else:
                log(f"  HL close failed for {token}: {result.get('error', 'unknown')} — will still close DB", "WARN")
        else:
            log(f"  HL close skipped for {token} (paper mode — no real HL position)", "INFO")
    except Exception as e:
        log(f"  HL close error for {token}: {e} — will still close DB", "WARN")

    # Step 2: Update the paper DB (brain.py handles this)
    # Use HL fill price if available, otherwise fall back to current market price
    exit_price = f"{hl_fill_price:.8f}" if hl_fill_price else f"{current_price:.8f}"
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"cut-loser({pnl_pct:.2f}%)",
           "--close-reason", "cut-loser",
           "--skip-hl"]
    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"Closed id={trade_id} {token} {direction} — {pnl_pct:.2f}% loss", "INFO")
            return True
        else:
            log(f"Close failed for id={trade_id} {token}: {result.stderr.strip()[:120]}", "ERROR")
            return False
    except Exception as e:
        log(f"Close error for id={trade_id} {token}: {e}", "ERROR")
        return False

# ── Load / save last run timestamp ─────────────────────────────────────────────
def get_last_run_ts():
    ts_file = Path(CUT_LOSER_LAST)
    try:
        with open(ts_file) as f:
            return json.load(f).get("ts", 0.0)
    except Exception:
        return 0.0

def save_last_run_ts():
    ts_file = Path(CUT_LOSER_LAST)
    with open(ts_file, "w") as f:
        json.dump({"ts": time.time()}, f)

# ── Main ───────────────────────────────────────────────────────────────────────
def run(dry_run=False):
    if not CUT_LOSER_ENABLED:
        log("disabled via CUT_LOSER_ENABLED — exiting")
        return

    cfg = load_config()

    if not cfg.get("enabled", True):
        log("disabled — exiting")
        return

    ab_group = cfg.get("ab_group", "B")
    last_ts  = get_last_run_ts()

    if not should_fire(ab_group, last_ts):
        log(f"Group {ab_group} — not time to fire yet (elapsed={time.time()-last_ts:.0f}s)")
        return

    log(f"Firing — group {ab_group}, loss range [{cfg.get('loss_min_pct', LOSS_MIN_PCT)} to {cfg.get('loss_max_pct', LOSS_MAX_PCT)}%]")

    positions = get_losing_positions()
    log(f"Found {len(positions)} open positions (computing live pnl...)")

    min_pct = cfg.get("loss_min_pct", LOSS_MIN_PCT)
    max_pct = cfg.get("loss_max_pct", LOSS_MAX_PCT)
    in_range = filter_losing_positions(positions, min_pct, max_pct)
    log(f"  {len(in_range)} positions in loss range [{min_pct} to {max_pct}%]")

    to_close = select_positions(
        in_range,
        max_close=cfg.get("max_closes_per_wake", CUT_LOSER_MAX_CLOSE),
        skip_bottom_pct=cfg.get("skip_bottom_pct", SKIP_BOTTOM_PCT)
    )

    if not to_close:
        log("No positions selected for close — letting them recover")
        save_last_run_ts()
        return

    for pos in to_close:
        close_position(pos["id"], pos["token"], pos["direction"],
                       pos.get("live_pnl_pct", pos["pnl_pct"]),
                       pos["current_price"],
                       dry_run or cfg.get("dry_run", False))

    save_last_run_ts()

# ── CLI ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cut Loser")
    parser.add_argument("--dry-run", action="store_true", help="Preview closes without executing")
    args = parser.parse_args()

    run(dry_run=args.dry_run)