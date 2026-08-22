#!/usr/bin/env python3
"""
Cut Loser v2 — Two-tier loss cutting + trailing loss. Mirror of profit_monster.py.

Tier 1 (Quick Cut): Lower loss range, fires frequently. Catches small losses fast.
Tier 2 (Deep Cut):  Higher loss range, fires less frequently. Handles bigger bleeds.
Trailing Loss:       Track worst point, cut if recovery fails.

All params tunable via hermes_constants.py (CL_TIER1_*, CL_TIER2_*, CL_TRAIL_*).
"""
from paths import *
from hermes_constants import (
    CUT_LOSER_ENABLED,
    CL_TIER1_MIN_PCT, CL_TIER1_MAX_PCT, CL_TIER1_MAX_CLOSE, CL_TIER1_SKIP_BOTTOM_PCT, CL_TIER1_FIRE_WINDOWS,
    CL_TIER2_MIN_PCT, CL_TIER2_MAX_PCT, CL_TIER2_MAX_CLOSE, CL_TIER2_SKIP_BOTTOM_PCT, CL_TIER2_FIRE_WINDOWS,
    CL_TRAIL_ENABLED, CL_TRAIL_ACTIVATE_PCT, CL_TRAIL_RECOVER_PCT, CL_TRAIL_MIN_HOLD, CL_TRAIL_FIRE_WINDOWS,
    CL_MAE_GUARD_ENABLED, CL_MAE_GUARD_THRESHOLD,
    PROFIT_MONSTER_BYPASS_SIGNALS,
)
import sys, os, json, time, random, argparse
from datetime import datetime
from pathlib import Path

from hermes_log import log
from hermes_file_lock import FileLock

# ── Constants ────────────────────────────────────────────────────────────────
LOG_FILE          = Path("/root/.hermes/logs/cut_loser.log")
CONFIG_FILE       = Path(CUT_LOSER_CONFIG)
BRAIN_CMD         = "/root/.hermes/scripts/brain.py"
GUARDIAN_LOCK     = '/tmp/hermes-guardian.lock'

# ── Config ───────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "ab_group": "B", "dry_run": False}


def should_fire(ab_group: str, last_run_ts: float, fire_windows: dict) -> bool:
    """Return True if enough minutes have passed since last_run_ts."""
    window = fire_windows.get(ab_group, fire_windows.get("B", (5, 10)))
    min_wait, max_wait = window
    jitter = random.uniform(0, 1)
    fire_interval_sec = (min_wait + (max_wait - min_wait) * jitter) * 60
    elapsed = time.time() - last_run_ts
    return elapsed >= fire_interval_sec


# ── DB Queries ───────────────────────────────────────────────────────────────
def get_losing_positions():
    """Return all open Hermes positions ordered by pnl_pct ASC (worst losers first)."""
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                                password=BRAIN_PASSWORD, connect_timeout=10)
        try:
            cur = conn.cursor()
            # Build NOT LIKE conditions for bypass signals
            bypass_clauses = ""
            params = []
            if PROFIT_MONSTER_BYPASS_SIGNALS:
                or_parts = ["signal LIKE %s"] * len(PROFIT_MONSTER_BYPASS_SIGNALS)
                bypass_clauses = "AND NOT (" + " OR ".join(or_parts) + ")"
                params = [f"%{s}%" for s in PROFIT_MONSTER_BYPASS_SIGNALS]
            cur.execute(f"""
                SELECT id, token, direction, entry_price, current_price, pnl_pct, open_time
                FROM trades
                WHERE server = 'Hermes' AND status = 'open'
                  AND entry_price > 0 AND current_price > 0
                  {bypass_clauses}
                ORDER BY pnl_pct ASC
            """, params)
            rows = cur.fetchall()
            return [
                {"id": r[0], "token": r[1], "direction": r[2], "entry_price": float(r[3]),
                 "current_price": float(r[4]), "pnl_pct": float(r[5]), "opened_at": r[6]}
                for r in rows
            ]
        finally:
            conn.close()
    except Exception as e:
        log(f"DB query error: {e}", "ERROR")
        return []


def filter_by_pnl(positions, min_pct, max_pct):
    """Filter positions to those within loss range.
    
    min_pct is more negative (floor), max_pct is less negative (ceiling).
    Example: T1 range is min_pct=-1.0, max_pct=-0.3
    """
    from pnl_utils import compute_live_pnl
    filtered = []
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            live_pnl = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])
            pos["live_pnl_pct"] = live_pnl
            # min_pct is more negative, max_pct is less negative
            # e.g. T1: min=-1.0, max=-0.3 → cut if -1.0 <= pnl <= -0.3
            if min_pct <= live_pnl <= max_pct:
                filtered.append(pos)
    return filtered


def select_positions(positions, max_close, skip_bottom_pct, trail_state=None):
    """Select positions to close: skip worst losers + trailed, pick random subset."""
    if not positions:
        return []
    # Skip bottom worst losers (let them recover or hit ATR SL)
    skip_count = max(0, int(len(positions) * skip_bottom_pct / 100))
    candidates = positions[skip_count:]
    # Skip trades being trailed (trail tier handles those)
    if trail_state:
        trailed_ids = set(trail_state.keys())
        candidates = [p for p in candidates if str(p["id"]) not in trailed_ids]
    if not candidates:
        return []
    count = random.randint(1, min(max_close, len(candidates)))
    return random.sample(candidates, count)


# ── Safety Checks ────────────────────────────────────────────────────────────
def is_position_on_hl(token: str) -> bool:
    """Check if token still has an open position on HL."""
    try:
        from hyperliquid_exchange import get_exchange, MAIN_ACCOUNT_ADDRESS
        ex = get_exchange()
        addr = getattr(ex, 'account_address', None) or MAIN_ACCOUNT_ADDRESS
        state = ex.info.user_state(addr)
        for p in state.get('assetPositions', []) or []:
            item = p.get('position') or {}
            if item.get('coin') == token.upper() and abs(float(item.get('szi') or 0)) > 0:
                return True
        return False
    except Exception as e:
        log(f"HL check failed for {token}: {e} — skipping", "WARN")
        return False


def is_token_being_closed_by_guardian(token: str) -> bool:
    """Check if guardian closing markers include this token."""
    try:
        markers_path = Path("/root/.hermes/data/guardian-closing-markers.json")
        data = json.loads(markers_path.read_text())
        markers = data.get('tokens', {}) if isinstance(data, dict) else data
        return token.upper() in {k.upper() for k in markers.keys()}
    except Exception:
        return False


def is_token_being_closed_by_profit_monster(token: str) -> bool:
    """Check if profit_monster is currently closing this token."""
    try:
        trail_path = Path("/root/.hermes/data/profit_monster_trail_state.json")
        state = json.loads(trail_path.read_text())
        return token.upper() in {v.get('token', '').upper() for v in state.values()}
    except Exception:
        return False


# ── Close Position ───────────────────────────────────────────────────────────
def close_position(trade_id, token, direction, pnl_pct, current_price, dry_run, tier):
    """Close a position on HL then update DB. Returns True on success."""
    if dry_run:
        log(f"[DRY RUN] [{tier}] Would close {token} {direction} @ {pnl_pct:.2f}% loss", "WARN")
        return True

    if is_token_being_closed_by_guardian(token):
        log(f"  [{tier}] Guardian closing marker for {token} — skipping", "WARN")
        return False
    if is_token_being_closed_by_profit_monster(token):
        log(f"  [{tier}] Profit monster closing {token} — skipping", "WARN")
        return False
    if not is_position_on_hl(token):
        log(f"  [{tier}] {token} not on HL — already closed, skipping", "WARN")
        return False

    # Close on HL
    hl_fill_price = None
    try:
        from hyperliquid_exchange import is_live_trading_enabled, close_position as hl_close
        if is_live_trading_enabled():
            result = hl_close(token.upper())
            if result.get("success"):
                log(f"  [{tier}] HL close OK: {token}", "PASS")
                try:
                    statuses = result.get("result", {}).get("response", {}).get("data", {}).get("statuses", [])
                    for s in statuses:
                        avg_px = s.get("filled", {}).get("avgPx")
                        if avg_px:
                            hl_fill_price = float(avg_px)
                            break
                except Exception:
                    pass
            else:
                log(f"  [{tier}] HL close failed for {token}: {result.get('error', result.get('message', 'unknown'))}", "WARN")
    except Exception as e:
        log(f"  [{tier}] HL close error for {token}: {e}", "WARN")

    # Re-check HL before DB write — only if close wasn't confirmed
    if hl_fill_price is None and not is_position_on_hl(token):
        log(f"  [{tier}] {token} gone from HL during close (no fill price) — skipping DB write", "WARN")
        return False

    # Update DB
    exit_price = f"{hl_fill_price:.8f}" if hl_fill_price else f"{current_price:.8f}"
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"cut-loser-{tier}({pnl_pct:.2f}%)",
           "--close-reason", f"cut-loser-{tier}",
           "--skip-hl"]
    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"  [{tier}] Closed id={trade_id} {token} {direction} — {pnl_pct:.2f}% loss", "INFO")
            # Record to signal_outcomes for WR tracking
            try:
                from signal_schema import record_signal_outcome
                actual_pnl_pct = float(pnl_pct or 0)
                notional = 11.0
                _signal_type = 'unknown'
                _confidence = 80
                try:
                    import psycopg2
                    from _secrets import BRAIN_DB_DICT
                    _conn = psycopg2.connect(**BRAIN_DB_DICT)
                    try:
                        _cur = _conn.cursor()
                        _cur.execute("SELECT amount_usdt, signal, confidence FROM trades WHERE id=%s", (trade_id,))
                        _row = _cur.fetchone()
                        if _row:
                            notional = float(_row[0]) if _row[0] else 11.0
                            _signal_type = _row[1] or 'unknown'
                            _confidence = float(_row[2]) if _row[2] else 80
                    finally:
                        try: _conn.close()
                        except: pass
                except Exception:
                    pass
                actual_pnl_usdt = float(pnl_pct or 0) / 100 * notional
                record_signal_outcome(
                    token=token,
                    direction=direction,
                    pnl_pct=round(actual_pnl_pct, 4),
                    pnl_usdt=round(actual_pnl_usdt, 4),
                    signal_type=_signal_type,
                    confidence=_confidence,
                    trade_id=trade_id
                )
            except Exception as sig_err:
                log(f"  [{tier}] Signal outcome record error: {sig_err}", "WARN")
            return True
        else:
            log(f"  [{tier}] Close failed id={trade_id} {token}: {result.stderr.strip()[:120]}", "ERROR")
            return False
    except Exception as e:
        log(f"  [{tier}] Close error id={trade_id} {token}: {e}", "ERROR")
        return False


# ── MAE Guard ───────────────────────────────────────────────────────────────
def get_positions_for_mae_guard():
    """Return all open LONG positions with highest_price for MAE guard."""
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                                password=BRAIN_PASSWORD, connect_timeout=10)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, token, direction, entry_price, current_price, highest_price,
                       pnl_pct, open_time
                FROM trades
                WHERE server = 'Hermes' AND status = 'open'
                  AND entry_price > 0 AND current_price > 0
                  AND direction = 'LONG'
                ORDER BY open_time DESC
            """)
            rows = cur.fetchall()
            return [
                {"id": r[0], "token": r[1], "direction": r[2], "entry_price": float(r[3]),
                 "current_price": float(r[4]), "highest_price": float(r[5]) if r[5] else float(r[3]),
                 "pnl_pct": float(r[6]), "opened_at": r[7]}
                for r in rows
            ]
        finally:
            conn.close()
    except Exception as e:
        log(f"MAE guard DB query error: {e}", "ERROR")
        return []


def run_mae_guard(positions, dry_run):
    """MAE Guard — cut LONG if price drops more than threshold from peak.

    Runs every wake (no fire windows). Immediate crash protection.
    Catches mass crashes before ATR SL triggers.

    LONG only: highest_price = peak. Drop from peak = bad → cut.
    SHORT excluded: highest_price = worst point. Drop from peak = recovery.
    """
    if not CL_MAE_GUARD_ENABLED:
        return 0

    closed = 0
    for pos in positions:
        highest = pos.get("highest_price", 0)
        current = pos["current_price"]
        entry = pos["entry_price"]
        direction = pos["direction"]

        if highest <= 0 or current <= 0:
            continue

        # LONG only: MAE from peak = how far price has dropped from highest
        if direction == "LONG":
            mae_from_peak = (highest - current) / highest
        else:
            # SHORT: lowest_price tracks trough; skip — different logic needed
            continue

        if mae_from_peak >= CL_MAE_GUARD_THRESHOLD:
            # Price dropped threshold% from peak — cut immediately
            from pnl_utils import compute_live_pnl
            live_pnl = compute_live_pnl(entry, current, direction)

            log(f"  [MAE-GUARD] {pos['token']} triggered: "
                f"peak=${highest:.6f} current=${current:.6f} "
                f"drop={mae_from_peak*100:.2f}% > {CL_MAE_GUARD_THRESHOLD*100:.1f}% "
                f"pnl={live_pnl:+.2f}%")

            ok = close_position(pos["id"], pos["token"], direction,
                                live_pnl, current, dry_run, "MAE-GUARD")
            if ok:
                closed += 1

    return closed


# ── Tier Runner ──────────────────────────────────────────────────────────────
def run_tier(tier_name, min_pct, max_pct, max_close, skip_bottom_pct, fire_windows, positions, dry_run, trail_state=None):
    """Run one tier: check fire timing, filter positions, close picks."""
    ts_file = Path(f"/root/.hermes/data/cut_loser_{tier_name}.json")
    try:
        last_ts = json.loads(ts_file.read_text()).get("ts", 0.0)
    except Exception:
        last_ts = 0.0

    ab_group = load_config().get("ab_group", "B")
    if not should_fire(ab_group, last_ts, fire_windows):
        elapsed = time.time() - last_ts
        log(f"  [{tier_name}] Not time to fire (elapsed={elapsed:.0f}s)")
        return 0

    in_range = filter_by_pnl(positions, min_pct, max_pct)
    log(f"  [{tier_name}] {len(in_range)} positions in [{min_pct}-{max_pct}%]")

    if not in_range:
        ts_file.write_text(json.dumps({"ts": time.time()}))
        return 0

    picks = select_positions(in_range, max_close, skip_bottom_pct, trail_state)
    if not picks:
        log(f"  [{tier_name}] No positions selected — letting losers recover")
        ts_file.write_text(json.dumps({"ts": time.time()}))
        return 0

    closed = 0
    for pos in picks:
        tier_label = f"CL-T{tier_name[-1]}"  # CL-T1 or CL-T2
        ok = close_position(pos["id"], pos["token"], pos["direction"],
                            pos.get("live_pnl_pct", pos["pnl_pct"]),
                            pos["current_price"], dry_run, tier_label)
        if ok:
            closed += 1

    ts_file.write_text(json.dumps({"ts": time.time()}))
    return closed


# ── Trailing Loss Tier ───────────────────────────────────────────────────────
_TRAIL_STATE_FILE = Path("/root/.hermes/data/cut_loser_trail_state.json")

def _load_trail_state():
    """Load trailing state: {trade_id: {worst_pnl, activated_at, token}}"""
    try:
        return json.loads(_TRAIL_STATE_FILE.read_text())
    except Exception:
        return {}

def _save_trail_state(state):
    _TRAIL_STATE_FILE.write_text(json.dumps(state, indent=2))

def run_trail(positions, dry_run):
    """Trailing loss tier: track worst point, cut when recovery threshold reached.

    Mirror of profit_monster.run_trail() but inverted:
    
    profit_monster trail:
      - Activates at +0.30% profit
      - Tracks PEAK (highest pnl)
      - Cuts when pnl drops 0.15% below peak
    
    cut_loser trail:
      - Activates at -0.30% loss
      - Tracks WORST (lowest pnl / most negative)
      - Cuts when recovery from worst reaches 0.15% (take the exit on signs of life)
    """
    if not CL_TRAIL_ENABLED:
        return 0

    ab_group = load_config().get("ab_group", "B")
    window = CL_TRAIL_FIRE_WINDOWS.get(ab_group, (0.5, 1))
    ts_file = Path("/root/.hermes/data/cut_loser_trail.json")
    try:
        last_ts = json.loads(ts_file.read_text()).get("ts", 0.0)
    except Exception:
        last_ts = 0.0

    min_wait, max_wait = window
    jitter = random.uniform(0, 1)
    fire_interval = (min_wait + (max_wait - min_wait) * jitter) * 60
    if time.time() - last_ts < fire_interval:
        return 0

    state = _load_trail_state()
    closed = 0

    for pos in positions:
        tid = str(pos["id"])
        pnl = pos.get("live_pnl_pct", pos["pnl_pct"])
        now = time.time()

        if tid in state:
            # ── Already trailing ──────────────────────────────────────────
            trail = state[tid]

            # If trade recovered above activation threshold, clear (recovered)
            if pnl > CL_TRAIL_ACTIVATE_PCT * 0.5:
                log(f"  [CL-TRAIL] {pos['token']} recovered to {pnl:.2f}% — clearing trail state")
                del state[tid]
                continue

            # Update worst (most negative = lowest pnl)
            if pnl < trail["worst_pnl"]:
                trail["worst_pnl"] = pnl
                trail["worst_time"] = now

            # Check minimum hold time
            if now - trail["activated_at"] < CL_TRAIL_MIN_HOLD * 60:
                continue

            # Cut if current pnl recovered from worst then dropped back
            # recovered = current is better (less negative) than worst by CL_TRAIL_RECOVER_PCT
            recovery = pnl - trail["worst_pnl"]  # positive if recovered
            if recovery >= CL_TRAIL_RECOVER_PCT:
                log(f"  [CL-TRAIL] {pos['token']} trailing exit: worst={trail['worst_pnl']:.2f}% "
                    f"current={pnl:.2f}% recovery={recovery:.2f}%")
                ok = close_position(pos["id"], pos["token"], pos["direction"],
                                    pnl, pos["current_price"], dry_run, "CL-trail")
                if ok:
                    closed += 1
                del state[tid]

        else:
            # ── New candidate: just entered loss zone ─────────────────────
            if pnl <= CL_TRAIL_ACTIVATE_PCT:
                # Check minimum hold time since trade opened
                try:
                    opened = datetime.fromisoformat(pos["opened_at"])
                    hold_min = (datetime.now() - opened).total_seconds() / 60
                except Exception:
                    hold_min = 999

                if hold_min >= CL_TRAIL_MIN_HOLD:
                    state[tid] = {
                        "worst_pnl": pnl,
                        "activated_at": now,
                        "worst_time": now,
                        "token": pos["token"],
                    }
                    log(f"  [CL-TRAIL] {pos['token']} activated: pnl={pnl:.2f}% "
                        f"worst={pnl:.2f}%")

    _save_trail_state(state)
    ts_file.write_text(json.dumps({"ts": time.time()}))
    return closed


# ── Main ─────────────────────────────────────────────────────────────────────
def run(dry_run=False):
    if not CUT_LOSER_ENABLED:
        log("disabled via CUT_LOSER_ENABLED — exiting")
        return

    cfg = load_config()
    if not cfg.get("enabled", True):
        log("disabled — exiting")
        return

    effective_dry_run = dry_run or cfg.get("dry_run", False)
    ab_group = cfg.get("ab_group", "B")

    log(f"Firing — group {ab_group}" + (" [DRY RUN]" if effective_dry_run else ""))

    # ── MAE Guard — runs first, immediate crash protection ──
    mae_positions = get_positions_for_mae_guard()
    log(f"MAE guard: {len(mae_positions)} positions to check")
    mae_closed = run_mae_guard(mae_positions, effective_dry_run)

    positions = get_losing_positions()
    log(f"Found {len(positions)} open positions")

    if not positions:
        if mae_closed > 0:
            log(f"Total closed: {mae_closed} (MAE guard)")
        return

    # Compute live PnL for all positions (prevents stale DB values in trail tier)
    from pnl_utils import compute_live_pnl
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            pos["live_pnl_pct"] = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])

    # Tier trail: Trailing loss (runs first — catches early losses and trails)
    trail_closed = run_trail(positions, effective_dry_run)

    # Load trail state for T1/T2 to skip trailed trades
    trail_state = _load_trail_state() if CL_TRAIL_ENABLED else {}

    # Tier 1: Quick cut
    t1_closed = run_tier("tier1", CL_TIER1_MIN_PCT, CL_TIER1_MAX_PCT,
                         CL_TIER1_MAX_CLOSE, CL_TIER1_SKIP_BOTTOM_PCT,
                         CL_TIER1_FIRE_WINDOWS, positions, effective_dry_run, trail_state)

    # Tier 2: Deep cut (re-check positions after tier 1 closes)
    if t1_closed > 0:
        positions = get_losing_positions()
    t2_closed = run_tier("tier2", CL_TIER2_MIN_PCT, CL_TIER2_MAX_PCT,
                         CL_TIER2_MAX_CLOSE, CL_TIER2_SKIP_BOTTOM_PCT,
                         CL_TIER2_FIRE_WINDOWS, positions, effective_dry_run, trail_state)

    total = mae_closed + trail_closed + t1_closed + t2_closed
    if total > 0:
        log(f"Total closed: {total} (MAE={mae_closed}, trail={trail_closed}, T1={t1_closed}, T2={t2_closed})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cut Loser v2 — Two-tier loss cutting + trailing")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()

    run(dry_run=args.dry_run)
