#!/usr/bin/env python3
"""
Profit Monster — closes medium-profit positions (2-5%) at random intervals.
Loves profit. A/B testable fire intervals (10-15min vs 20-30min).
Never touches losing positions.
"""
import sys, os, json, time, random, argparse
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
PROFIT_MIN_PCT    = 2.0
PROFIT_MAX_PCT    = 5.0
MAX_CLOSE_PER_WAKE = 2
SKIP_TOP_PCT      = 20        # don't touch the top 20% most profitable
LOG_FILE          = Path("/root/.hermes/logs/profit_monster.log")
CONFIG_FILE       = Path("/root/.hermes/data/profit_monster_config.json")
BRAIN_CMD         = "/root/.hermes/scripts/brain.py"

# A/B fire windows (minutes)
FIRE_WINDOWS = {
    "A": (10, 15),   # 10-15 min
    "B": (20, 30),   # 20-30 min
}

# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] [profit-monster] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Config ───────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "ab_group": "B", "dry_run": False}

# ── Fire decision (random timer) ──────────────────────────────────────────────
def should_fire(ab_group: str, last_run_ts: float) -> bool:
    """Return True if enough minutes have passed since last_run_ts."""
    window = FIRE_WINDOWS.get(ab_group, FIRE_WINDOWS["B"])
    min_wait, max_wait = window
    # Add jitter: random within the window
    jitter = random.uniform(0, 1)
    fire_interval_sec = (min_wait + (max_wait - min_wait) * jitter) * 60
    elapsed = time.time() - last_run_ts
    return elapsed >= fire_interval_sec

# ── Query open positions in profit range ─────────────────────────────────────
def get_profitable_positions(min_pct=PROFIT_MIN_PCT, max_pct=PROFIT_MAX_PCT):
    """Return list of dicts for open positions with pnl_pct in [min_pct, max_pct]."""
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
            ORDER BY pnl_pct DESC
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


def filter_profitable_positions(positions, min_pct=PROFIT_MIN_PCT, max_pct=PROFIT_MAX_PCT):
    """Compute live pnl_pct from entry_price vs current_price and filter to range."""
    filtered = []
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            if pos["direction"].upper() == "LONG":
                live_pnl = (pos["current_price"] - pos["entry_price"]) / pos["entry_price"] * 100
            else:
                live_pnl = (pos["entry_price"] - pos["current_price"]) / pos["entry_price"] * 100
            pos["live_pnl_pct"] = live_pnl
            if min_pct <= live_pnl <= max_pct:
                filtered.append(pos)
    return filtered

# ── Select positions to close (skip top SKIP_TOP_PCT, pick 1-2 at random) ───────
def select_positions(positions, max_close=MAX_CLOSE_PER_WAKE, skip_top_pct=SKIP_TOP_PCT):
    if not positions:
        return []

    # Skip top profitable (let winners run)
    skip_count = max(1, int(len(positions) * skip_top_pct / 100))
    candidates = positions[skip_count:]
    if not candidates:
        return []

    # Randomly pick 1-2
    count = random.randint(1, min(max_close, len(candidates)))
    return random.sample(candidates, count)

# ── Close a position via brain.py ─────────────────────────────────────────────
def close_position(trade_id: int, token: str, direction: str, pnl_pct: float, current_price: float, dry_run: bool):
    if dry_run:
        log(f"[DRY RUN] Would close id={trade_id} {token} {direction} @ {pnl_pct:.2f}% profit", "WARN")
        return True

    exit_price = f"{current_price:.8f}"
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"profit-monster({pnl_pct:.2f}%)",
           "--close-reason", "profit-monster"]
    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"Closed id={trade_id} {token} {direction} — {pnl_pct:.2f}% profit", "INFO")
            return True
        else:
            log(f"Close failed for id={trade_id} {token}: {result.stderr.strip()[:120]}", "ERROR")
            return False
    except Exception as e:
        log(f"Close error for id={trade_id} {token}: {e}", "ERROR")
        return False

# ── Load / save last run timestamp ────────────────────────────────────────────
def get_last_run_ts():
    ts_file = Path("/root/.hermes/data/profit_monster_last_run.json")
    try:
        with open(ts_file) as f:
            return json.load(f).get("ts", 0.0)
    except Exception:
        return 0.0

def save_last_run_ts():
    ts_file = Path("/root/.hermes/data/profit_monster_last_run.json")
    with open(ts_file, "w") as f:
        json.dump({"ts": time.time()}, f)

# ── Main ──────────────────────────────────────────────────────────────────────
def run(dry_run=False):
    cfg = load_config()

    if not cfg.get("enabled", True):
        log("disabled — exiting")
        return

    ab_group = cfg.get("ab_group", "B")
    last_ts  = get_last_run_ts()

    if not should_fire(ab_group, last_ts):
        log(f"Group {ab_group} — not time to fire yet (elapsed={time.time()-last_ts:.0f}s)")
        return

    log(f"Firing — group {ab_group}, profit range [{cfg.get('min_profit_pct',PROFIT_MIN_PCT)}-{cfg.get('max_profit_pct',PROFIT_MAX_PCT)}%]")

    positions = get_profitable_positions()
    log(f"Found {len(positions)} open positions (computing live pnl...)")

    min_pct = cfg.get("min_profit_pct", PROFIT_MIN_PCT)
    max_pct = cfg.get("max_profit_pct", PROFIT_MAX_PCT)
    in_range = filter_profitable_positions(positions, min_pct, max_pct)
    log(f"  {len(in_range)} positions in profit range [{min_pct}-{max_pct}%]")

    to_close = select_positions(
        in_range,
        max_close=cfg.get("max_closes_per_wake", MAX_CLOSE_PER_WAKE),
        skip_top_pct=cfg.get("skip_top_pct", SKIP_TOP_PCT)
    )

    if not to_close:
        log("No positions selected for close — letting winners run")
        save_last_run_ts()
        return

    for pos in to_close:
        close_position(pos["id"], pos["token"], pos["direction"],
                       pos.get("live_pnl_pct", pos["pnl_pct"]),
                       pos["current_price"],
                       dry_run or cfg.get("dry_run", False))

    save_last_run_ts()

# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profit Monster")
    parser.add_argument("--dry-run", action="store_true", help="Preview closes without executing")
    args = parser.parse_args()

    run(dry_run=args.dry_run)