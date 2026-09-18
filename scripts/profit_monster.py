#!/usr/bin/env python3
"""
Profit Monster — Two-tier take-profit system.

Tier 1 (Quick Scalp): Lower profit range, fires frequently. Grabs small wins fast.
Tier 2 (Runner): Higher profit range, fires less frequently. Lets winners run longer.

Each tier has independent profit range, fire window, and max-close settings.
All params tunable via hermes_constants.py (PM_TIER1_*, PM_TIER2_*, PM_*).
"""
from paths import *
from hermes_constants import (
    PM_TIER1_MIN_PCT, PM_TIER1_MAX_PCT, PM_TIER1_MAX_CLOSE, PM_TIER1_SKIP_TOP_PCT, PM_TIER1_FIRE_WINDOWS,
    PM_TIER2_MIN_PCT, PM_TIER2_MAX_PCT, PM_TIER2_MAX_CLOSE, PM_TIER2_SKIP_TOP_PCT, PM_TIER2_FIRE_WINDOWS,
    PM_TRAIL_ENABLED, PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_DISTANCE_PCT, PM_TRAIL_MIN_HOLD, PM_TRAIL_FIRE_WINDOWS,
    PM_TRAIL_TIERS,
    PM_DRY_RUN, PM_DEFAULT_NOTIONAL, PROFIT_MONSTER_BYPASS_SIGNALS, PM_TRAIL_BYPASS_SIGNALS, PM_TIER_BYPASS_SIGNALS,
    SPIDER_ENABLED, SPIDER_REGIME, SPIDER_CONFIDENCE_MIN,
    SPIDER_TRAIL_ACTIVATE_PCT, SPIDER_TRAIL_DISTANCE_PCT,
    SPIDER_T1_MIN_PCT, SPIDER_T1_MAX_PCT, SPIDER_MAX_HOLD_MINUTES,
)
# FIX: constants are in decimal (0.006=0.60%) but live_pnl_pct is in percent (0.01=0.01%)
# Convert to percent so comparisons are correct: pnl(%) >= ACTIVATE(%)
PM_TRAIL_ACTIVATE_PCT *= 100
PM_TRAIL_DISTANCE_PCT *= 100
PM_TRAIL_TIERS = [(min_p * 100, dist * 100) for min_p, dist in PM_TRAIL_TIERS]  # convert to percent
import sys, os, json, time, random, argparse
from datetime import datetime
from pathlib import Path

from hermes_log import log
from hermes_file_lock import FileLock

# ── Constants ────────────────────────────────────────────────────────────────
LOG_FILE          = Path("/root/.hermes/logs/profit_monster.log")
CONFIG_FILE       = Path(PROFIT_MONSTER_CONFIG)
BRAIN_CMD         = "/root/.hermes/scripts/brain.py"
GUARDIAN_LOCK     = '/tmp/hermes-guardian.lock'  # noqa: F811 — used by external callers

# ── Config ───────────────────────────────────────────────────────────────────
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "ab_group": "A", "dry_run": False}


def should_fire(ab_group: str, last_run_ts: float, fire_windows: dict) -> bool:
    """Return True if enough minutes have passed since last_run_ts."""
    window = fire_windows.get(ab_group, fire_windows.get("B", (5, 10)))
    min_wait, max_wait = window
    jitter = random.uniform(0, 1)
    fire_interval_sec = (min_wait + (max_wait - min_wait) * jitter) * 60
    elapsed = time.time() - last_run_ts
    return elapsed >= fire_interval_sec


def get_spider_active() -> bool:
    """Check if spider-profit should be active (NEUTRAL regime with sufficient confidence)."""
    if not SPIDER_ENABLED:
        return False
    try:
        import json as _json
        regime_file = Path("/var/www/hermes/data/regime_15m.json")
        data = _json.loads(regime_file.read_text())
        overall = data.get("aggregate", {}).get("overall", "")
        return overall == SPIDER_REGIME
    except Exception:
        return False


# ── DB Queries ───────────────────────────────────────────────────────────────
def get_all_open_positions():
    """Return all open Hermes positions from DB."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                                password=BRAIN_PASSWORD, connect_timeout=10)
        cur = conn.cursor()
        # Build NOT LIKE conditions for bypass signals
        bypass_clauses = ""
        params = []
        if PROFIT_MONSTER_BYPASS_SIGNALS:
            or_parts = ["signal LIKE %s"] * len(PROFIT_MONSTER_BYPASS_SIGNALS)
            bypass_clauses = "AND NOT (" + " OR ".join(or_parts) + ")"
            params = [f"%{s}%" for s in PROFIT_MONSTER_BYPASS_SIGNALS]
        cur.execute(f"""
            SELECT id, token, direction, entry_price, current_price, pnl_pct, open_time, signal
            FROM trades
            WHERE server = 'Hermes' AND status = 'open'
              AND entry_price > 0 AND current_price > 0
              {bypass_clauses}
            ORDER BY pnl_pct DESC
        """, params)
        rows = cur.fetchall()
        return [
            {"id": r[0], "token": r[1], "direction": r[2], "entry_price": float(r[3]),
             "current_price": float(r[4]), "pnl_pct": float(r[5]), "opened_at": r[6],
             "signal": r[7] or ""}
            for r in rows
        ]
    except Exception as e:
        log(f"DB query error: {e}", "ERROR")
        return []
    finally:
        if conn:
            try: conn.close()
            except: pass


def filter_by_pnl(positions, min_pct, max_pct):
    """Filter positions to those within pnl_pct range."""
    from pnl_utils import compute_live_pnl
    filtered = []
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            live_pnl = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])
            pos["live_pnl_pct"] = live_pnl
            if min_pct <= live_pnl <= max_pct:
                filtered.append(pos)
    return filtered


def select_positions(positions, max_close, skip_top_pct, trail_state=None):
    """Select positions to close: skip top profitable + trailed, pick random subset."""
    if not positions:
        return []
    skip_count = max(0, int(len(positions) * skip_top_pct / 100))
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


# ── Close Position ───────────────────────────────────────────────────────────
def close_position(trade_id, token, direction, pnl_pct, current_price, dry_run, tier):
    """Close a position on HL then update DB. Returns True on success."""
    if dry_run:
        log(f"[DRY RUN] [{tier}] Would close {token} {direction} @ {pnl_pct:.2f}% profit", "WARN")
        return True

    if is_token_being_closed_by_guardian(token):
        log(f"  [{tier}] Guardian closing marker for {token} — skipping", "WARN")
        return False
    # Sniper mutual exclusion — don't close if sniper is handling it
    try:
        from sniper_exit import is_token_being_closed_by_sniper
        if is_token_being_closed_by_sniper(token):
            log(f"  [{tier}] Sniper closing {token} — skipping", "WARN")
            return False
    except ImportError:
        pass
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
    # After successful close, position SHOULD be gone from HL (that's the goal)
    if hl_fill_price is None and not is_position_on_hl(token):
        log(f"  [{tier}] {token} gone from HL during close (no fill price) — skipping DB write", "WARN")
        return False

    # Update DB
    exit_price = f"{hl_fill_price:.8f}" if hl_fill_price else f"{current_price:.8f}"
    cmd = [sys.executable, BRAIN_CMD, "trade", "close", str(trade_id), exit_price,
           "--notes", f"profit-monster-{tier}({pnl_pct:.2f}%)",
           "--close-reason", f"profit-monster-{tier}",
           "--exit-conditions", f"profit-monster-{tier}({pnl_pct:.2f}%)",
           "--skip-hl"]
    try:
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"  [{tier}] Closed id={trade_id} {token} {direction} — {pnl_pct:.2f}% profit", "INFO")
            # Record to signal_outcomes for WR tracking
            try:
                from signal_schema import record_signal_outcome
                actual_pnl_pct = float(pnl_pct or 0)
                # Fetch amount_usdt (margin) for PnL calc — NOT hl_notional_usdt
                # (hl_notional_usdt is actual fill notional which varies; amount_usdt
                #  is the margin we risk per trade, matching dashboard convention)
                notional = PM_DEFAULT_NOTIONAL
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
                        else:
                            _signal_type = 'unknown'
                            _confidence = 80
                    finally:
                        try: _conn.close()
                        except: pass
                except Exception:
                    _signal_type = 'unknown'
                    _confidence = 80
                # PnL = pnl% × margin (matches dashboard convention)
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


# ── Tier Runner ──────────────────────────────────────────────────────────────
def run_tier(tier_name, min_pct, max_pct, max_close, skip_top_pct, fire_windows, positions, dry_run, trail_state=None):
    """Run one tier: check fire timing, filter positions, close picks."""
    ts_file = Path(f"/root/.hermes/data/profit_monster_{tier_name}.json")
    try:
        last_ts = json.loads(ts_file.read_text()).get("ts", 0.0)
    except Exception:
        last_ts = 0.0

    ab_group = load_config().get("ab_group", "A")
    if not should_fire(ab_group, last_ts, fire_windows):
        elapsed = time.time() - last_ts
        log(f"  [{tier_name}] Not time to fire (elapsed={elapsed:.0f}s)")
        return 0

    in_range = filter_by_pnl(positions, min_pct, max_pct)

    # Skip signals in PM_TIER_BYPASS (ride ATR SL/TP only)
    in_range = [p for p in in_range if not any(s in (p.get("signal", "") or "") for s in PM_TIER_BYPASS_SIGNALS)]

    log(f"  [{tier_name}] {len(in_range)} positions in [{min_pct}-{max_pct}%]")

    if not in_range:
        ts_file.write_text(json.dumps({"ts": time.time()}))
        return 0

    picks = select_positions(in_range, max_close, skip_top_pct, trail_state)
    if not picks:
        log(f"  [{tier_name}] No positions selected — letting winners run")
        ts_file.write_text(json.dumps({"ts": time.time()}))
        return 0

    closed = 0
    for pos in picks:
        tier_label = f"T{tier_name[-1]}"  # T1 or T2
        ok = close_position(pos["id"], pos["token"], pos["direction"],
                            pos.get("live_pnl_pct", pos["pnl_pct"]),
                            pos["current_price"], dry_run, tier_label)
        if ok:
            closed += 1

    ts_file.write_text(json.dumps({"ts": time.time()}))
    return closed


# ── Trailing Profit Tier ─────────────────────────────────────────────────────
_TRAIL_STATE_FILE = Path("/root/.hermes/data/profit_monster_trail_state.json")

def _load_trail_state():
    """Load trailing state: {trade_id: {peak_pnl, activated_at, token}}"""
    try:
        return json.loads(_TRAIL_STATE_FILE.read_text())
    except Exception:
        return {}

def _save_trail_state(state):
    _TRAIL_STATE_FILE.write_text(json.dumps(state, indent=2))

def _trail_distance_for_peak(peak_pnl_pct):
    """Return trail distance for current peak profit using tier system.
    Tiers loosen as profit grows — last matching tier wins (highest applicable)."""
    dist = PM_TRAIL_TIERS[0][1]  # default to first tier
    for min_profit, d in PM_TRAIL_TIERS:
        if peak_pnl_pct >= min_profit:
            dist = d
    return dist


def run_trail(positions, dry_run):
    """Trailing profit tier: mark trades in profit, trail peak, exit on weakness.

    Logic:
    1. When trade hits PM_TRAIL_ACTIVATE_PCT → mark as trailing, record peak
    2. On each check: if current_pnl < peak - trail_distance(peak) → exit
    3. Trail distance loosens as profit grows (tiered system)
    """
    if not PM_TRAIL_ENABLED:
        return 0

    ab_group = load_config().get("ab_group", "A")
    window = PM_TRAIL_FIRE_WINDOWS.get(ab_group, (0.5, 1))
    # Use same fire timing as Tier 1 (fastest)
    ts_file = Path("/root/.hermes/data/profit_monster_trail.json")
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

        # Skip trail for signals in PM_TRAIL_BYPASS (still get T1/T2)
        signal = pos.get("signal", "")
        if any(s in signal for s in PM_TRAIL_BYPASS_SIGNALS):
            # Remove from trail state if it was previously trailing
            if tid in state:
                log(f"  [TRAIL] {pos['token']} bypassed (signal={signal}) — removing from trail state")
                del state[tid]
            continue

        if tid in state:
            # ── Already trailing ──────────────────────────────────────────
            trail = state[tid]

            # Update peak first (need current peak for floor calc)
            if pnl > trail["peak_pnl"]:
                trail["peak_pnl"] = pnl
                trail["peak_time"] = now

            # Check minimum hold time
            if now - trail["activated_at"] < PM_TRAIL_MIN_HOLD * 60:
                continue

            # Exit if current price dropped trail distance from peak
            # Trail distance loosens as profit grows (tiered system)
            trail_dist = _trail_distance_for_peak(trail["peak_pnl"])
            trail_floor = trail["peak_pnl"] - trail_dist
            # ponytail: removed breakeven guard — was capping avg PM_TRAIL exit at 0.24%
            # despite 0.40% activation. Trades peaked 0.50-0.60% then exited at 0.0%.
            # Now exits at trail_floor, letting R:R improve.
            if pnl <= trail_floor:
                log(f"  [TRAIL] {pos['token']} trailing exit: peak={trail['peak_pnl']:.2f}% "
                    f"current={pnl:.2f}% floor={trail_floor:.2f}% dist={trail_dist:.2f}%")
                ok = close_position(pos["id"], pos["token"], pos["direction"],
                                    pnl, pos["current_price"], dry_run, "trail")
                if ok:
                    closed += 1
                del state[tid]
            # ponytail: removed "clear on drop below activation" — was causing race
            # condition where fast crashes (1.18% peak → -0.78% ATR_SL in <30s)
            # cleared trail state before breakeven guard could exit at 0.0%.
            # 43 ATR_SL trades/48h had avg MFE 1.18% — should have been trailed.

        else:
            # ── New candidate: just entered profit zone ───────────────────
            if pnl >= PM_TRAIL_ACTIVATE_PCT:
                # Check minimum hold time since trade opened
                try:
                    opened = datetime.fromisoformat(pos["opened_at"])
                    hold_min = (datetime.now() - opened).total_seconds() / 60
                except Exception:
                    hold_min = 999

                if hold_min >= PM_TRAIL_MIN_HOLD:
                    state[tid] = {
                        "peak_pnl": pnl,
                        "activated_at": now,
                        "peak_time": now,
                        "token": pos["token"],
                    }
                    log(f"  [TRAIL] {pos['token']} activated: pnl={pnl:.2f}% "
                        f"peak={pnl:.2f}% trail_floor={pnl - _trail_distance_for_peak(pnl):.2f}%")

    _save_trail_state(state)
    ts_file.write_text(json.dumps({"ts": time.time()}))
    return closed


# ── Main ─────────────────────────────────────────────────────────────────────
def run(dry_run=False):
    cfg = load_config()
    if not cfg.get("enabled", True):
        log("Disabled — exiting")
        return

    effective_dry_run = dry_run or cfg.get("dry_run", False) or PM_DRY_RUN
    ab_group = cfg.get("ab_group", "A")

    # Spider-profit: check regime and override params if active
    spider_active = get_spider_active()
    if spider_active:
        log(f"Spider-profit ACTIVE — NEUTRAL regime, tighter thresholds")
        global PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_DISTANCE_PCT, PM_TIER1_MIN_PCT, PM_TIER1_MAX_PCT, PM_TRAIL_TIERS
        PM_TRAIL_ACTIVATE_PCT = SPIDER_TRAIL_ACTIVATE_PCT * 100
        PM_TRAIL_DISTANCE_PCT = SPIDER_TRAIL_DISTANCE_PCT * 100
        PM_TIER1_MIN_PCT = SPIDER_T1_MIN_PCT
        PM_TIER1_MAX_PCT = SPIDER_T1_MAX_PCT
        # Tighter trail tiers for flat markets
        PM_TRAIL_TIERS = [
            (0.0,   0.1),   # 0%–1.5%: 0.10% trail (spider — very tight)
            (0.015, 0.3),   # 1.5%–3.0%: 0.30% trail
            (0.030, 0.5),   # 3.0%+: 0.50% trail
        ]

    log(f"Firing — group {ab_group}" + (" [DRY RUN]" if effective_dry_run else "") + (" [SPIDER]" if spider_active else ""))

    positions = get_all_open_positions()
    log(f"Found {len(positions)} open positions")

    if not positions:
        return

    # Refresh current_price from live allMids (DB price can be up to 60s stale)
    try:
        import hype_cache as hc
        mids = hc.get_allMids()
        for pos in positions:
            token = pos["token"].upper()
            if token in mids:
                pos["current_price"] = float(mids[token])
    except Exception as e:
        log(f"Failed to refresh mids: {e}", "WARN")

    # Compute live PnL for all positions (needed by trail tier)
    from pnl_utils import compute_live_pnl
    for pos in positions:
        if pos["entry_price"] > 0 and pos["current_price"] > 0:
            pos["live_pnl_pct"] = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])

    # Tier T: Trailing profit (runs first — catches early profit and trails)
    trail_closed = run_trail(positions, effective_dry_run)

    # Load trail state for T1/T2 to skip trailed trades
    trail_state = _load_trail_state() if PM_TRAIL_ENABLED else {}

    # Tier 1: Quick scalp
    t1_closed = run_tier("tier1", PM_TIER1_MIN_PCT, PM_TIER1_MAX_PCT,
                         PM_TIER1_MAX_CLOSE, PM_TIER1_SKIP_TOP_PCT,
                         PM_TIER1_FIRE_WINDOWS, positions, effective_dry_run, trail_state)

    # Tier 2: Runner (re-check positions after tier 1 closes)
    if t1_closed > 0:
        positions = get_all_open_positions()
        # Refresh prices + PnL for re-fetched positions (same as initial load)
        try:
            import hype_cache as hc
            mids = hc.get_allMids()
            for pos in positions:
                token = pos["token"].upper()
                if token in mids:
                    pos["current_price"] = float(mids[token])
        except Exception as e:
            log(f"Failed to refresh mids for T2: {e}", "WARN")
        for pos in positions:
            if pos["entry_price"] > 0 and pos["current_price"] > 0:
                pos["live_pnl_pct"] = compute_live_pnl(pos["entry_price"], pos["current_price"], pos["direction"])
    t2_closed = run_tier("tier2", PM_TIER2_MIN_PCT, PM_TIER2_MAX_PCT,
                         PM_TIER2_MAX_CLOSE, PM_TIER2_SKIP_TOP_PCT,
                         PM_TIER2_FIRE_WINDOWS, positions, effective_dry_run, trail_state)

    total = t1_closed + t2_closed
    if total > 0:
        log(f"Total closed: {total} (T1={t1_closed}, T2={t2_closed})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profit Monster — Two-tier take-profit")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
