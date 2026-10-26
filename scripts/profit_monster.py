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
        regime_file = Path("/var/www/hermes/data/regime_5m.json")
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
        # CEO-tranche token guard (2026-10-24, #16384 merge): when a CEO-managed
        # row (ai-trader-manual/pending/auto) shares a coin with a pipeline row,
        # HL MERGES them into one position — PM closing the pipeline row closes
        # the CEO tranche too, with PM's trail instead of manual_exit_manager's
        # (the #16384 add was trailed out at PM's 0.20% 90 seconds after opening).
        # Exit authority follows the contract, not the row: skip the whole token.
        from manual_exit_manager import MANAGED_TAGS
        cur.execute(
            "SELECT DISTINCT token FROM trades WHERE server='Hermes' "
            "AND status='open' AND paper IS FALSE AND (" +
            " OR ".join(["signal LIKE %s"] * len(MANAGED_TAGS)) + ")",
            [f"%{t}%" for t in MANAGED_TAGS])
        ceo_tokens = {str(r[0]).upper() for r in cur.fetchall()}
        if ceo_tokens:
            kept = [r for r in rows if str(r[1]).upper() not in ceo_tokens]
            if len(kept) != len(rows):
                log(f"  [PM] CEO-tranche token guard: standing down on "
                    f"{sorted(ceo_tokens & {str(r[1]).upper() for r in rows})} — "
                    f"manual_exit_manager owns those exits")
                rows = kept
        # ── trail-state GC (brain_auditor #158) ──────────────────────────────
        # `rows` IS the managed-open set (open minus PROFIT_MONSTER_BYPASS minus
        # CEO-tranche). See _gc_trail_state for why orphans are dangerous.
        # This success path only — the DB-error path returns [] above and must
        # never wipe a healthy file.
        try:
            _gc_trail_state([str(r[0]) for r in rows])
        except Exception as _gc_err:
            log(f"trail-state GC error: {_gc_err}", "WARN")
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
        # FIX (2026-10-17): close gated by constant only, not pause marker —
        # protective exits must always mirror to HL or DB/HL diverge
        from hyperliquid_exchange import LIVE_TRADING_ENABLED, close_position as hl_close
        if LIVE_TRADING_ENABLED:
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
                from signal_schema import record_signal_outcome, compute_mfe_mae_from_extremes
                actual_pnl_pct = float(pnl_pct or 0)
                # Fetch amount_usdt (margin) for PnL calc — NOT hl_notional_usdt
                # (hl_notional_usdt is actual fill notional which varies; amount_usdt
                #  is the margin we risk per trade, matching dashboard convention)
                notional = PM_DEFAULT_NOTIONAL
                _entry_rsi = None  # P0: learning band source; None → band NULL
                _mfe_pct = _mae_pct = None
                try:
                    import psycopg2
                    from _secrets import BRAIN_DB_DICT
                    _conn = psycopg2.connect(**BRAIN_DB_DICT)
                    try:
                        _cur = _conn.cursor()
                        # P0: also fetch entry_rsi_14 + extremes for learning columns
                        _cur.execute(
                            "SELECT amount_usdt, signal, confidence, entry_rsi_14, "
                            "entry_price, highest_price, lowest_price, direction "
                            "FROM trades WHERE id=%s", (trade_id,))
                        _row = _cur.fetchone()
                        if _row:
                            notional = float(_row[0]) if _row[0] else 11.0
                            _signal_type = _row[1] or 'unknown'
                            _confidence = float(_row[2]) if _row[2] else 80
                            _entry_rsi = _row[3]
                            _mfe_pct, _mae_pct = compute_mfe_mae_from_extremes(
                                _row[7] or direction, _row[4], _row[5], _row[6])
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
                try:
                    from signal_schema import rsi_band_label as _rsi_band
                except ImportError:
                    _rsi_band = lambda r: None  # noqa: E731
                record_signal_outcome(
                    token=token,
                    direction=direction,
                    pnl_pct=round(actual_pnl_pct, 4),
                    pnl_usdt=round(actual_pnl_usdt, 4),
                    signal_type=_signal_type,
                    confidence=_confidence,
                    trade_id=trade_id,
                    # P0: profit-monster is the largest close family — was writing NULL
                    exit_reason=f"profit-monster-{tier}",  # matches brain CLI close-reason
                    entry_rsi_band=_rsi_band(_entry_rsi),
                    mfe_pct=_mfe_pct,
                    mae_pct=_mae_pct,
                )
            except Exception as sig_err:
                log(f"  [{tier}] Signal outcome record error: {sig_err}", "WARN")
            return True
        else:
            # FIX (2026-10-08, BUG-027 follow-up): include stdout — brain.py's
            # "✗ trade #N was not open or not found" diagnostic goes to stdout,
            # so race events were logging with empty stderr detail.
            log(f"  [{tier}] Close failed id={trade_id} {token}: rc={result.returncode} stderr={result.stderr.strip()[:100]} stdout={result.stdout.strip()[:120]}", "ERROR")
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


def _gc_trail_state(kept_ids, state_file=None):
    """Drop trail-state keys whose trade_id is not in kept_ids. Returns dropped.

    Keys are only ever deleted on a PM trail exit (`del state[tid]` in
    run_trail), so every other exit path — atr_sl_hit, hard_max_loss, ugb_pt,
    trail_arm_timeout, rr_engine — orphans its key permanently. A signal PM
    briefly saw and then bypassed (2026-10-26 02:19 rogue constants edit,
    reverted 02:40) leaves a key PM can never reach again. Four consumers read
    membership as "profit_monster is actively handling this trade":
      * position_manager UGB-PT enforce -> skips the post-arm floor
        (IO #16407: 8 UGB-PT would-fire cycles skipped 02:48-03:04, closed
         atr_sl_hit -0.45% price-move = -1.25% stored pnl_pct (lev 3) instead
         of first-fire floor live +0.44%)
      * cut_loser.close_position -> stands down on the whole TOKEN
        (6 logged skips: BABY 10-15, SYRUP 10-21, CC x3 10-23 — all then hit
         -3.09 / -3.95 / -4.02% leveraged = -$0.53)
      * hl_fill_monitor copy-exit -> calls cut_loser's same token check, continues
      * sniper_exit:707 skip + :908 tier1 exclusion (winner never booked)
    Set-difference against the managed-open set is the whole rule.
    ponytail: no per-key status query; upgrade to a DB-verified purge only if
    the managed-open set ever stops being authoritative.
    """
    f = Path(state_file) if state_file else _TRAIL_STATE_FILE
    try:
        state = json.loads(f.read_text())
    except Exception:
        return 0
    kept = {str(i) for i in kept_ids}
    orphans = [k for k in state if k not in kept]
    if not orphans:
        return 0
    for k in orphans:
        del state[k]
    f.write_text(json.dumps(state, indent=2))
    log(f"  [PM] trail-state GC: dropped {len(orphans)} orphaned entries, "
        f"{len(state)} live")
    return len(orphans)

def _trail_distance_for_peak(peak_pnl_pct):
    """Return trail distance for current peak profit using tier system.
    Tiers loosen as profit grows — last matching tier wins (highest applicable)."""
    dist = PM_TRAIL_TIERS[0][1]  # default to first tier
    for min_profit, d in PM_TRAIL_TIERS:
        if peak_pnl_pct >= min_profit:
            dist = d
    return dist


# ── Durable PM-arm stamp (brain_auditor #162, zero behavior) ─────────────────
# trades.trailing_activated is an EXIT-REASON flag (PG trigger: exit_reason
# ILIKE '%trail%'), so it answers "how did it exit", not "did PM trail manage it"
# — 25/25 trail_arm_timeout rows read as armed, stop-exits read as unarmed.
# The [TRAIL] activated log lines answer it correctly but rotate/compress.
# Single atomic UPDATE into _signal_metadata; failure never blocks the trail.
_PM_ARMED_SQL = """
    UPDATE trades
    SET _signal_metadata = COALESCE(_signal_metadata, '{}'::jsonb)
        || jsonb_build_object('pm_armed_at',
            to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))
    WHERE id = %s
"""


def _stamp_pm_armed(trade_id):
    """Stamp pm_armed_at into the trade's _signal_metadata. Commits on success."""
    import psycopg2
    from _secrets import BRAIN_PASSWORD, BRAIN_HOST
    conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                            password=BRAIN_PASSWORD, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(_PM_ARMED_SQL, (int(trade_id),))
        conn.commit()
    finally:
        conn.close()


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
                    f"current={pnl:.2f}% floor={trail_floor:.2f}% dist={trail_dist:.2f}% trade_id={tid}")
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
                    # trade_id field (brain_auditor #137): KPI joins matched on
                    # token+window only — <=0.4pp over-credit from 1 overlapping
                    # same-token armed pair (pm_activation_coverage disclosure).
                    log(f"  [TRAIL] {pos['token']} activated: pnl={pnl:.2f}% "
                        f"peak={pnl:.2f}% trail_floor={pnl - _trail_distance_for_peak(pnl):.2f}% "
                        f"trade_id={tid}")
                    try:
                        _stamp_pm_armed(tid)
                    except Exception as e:
                        log(f"  [TRAIL] pm_armed_at stamp failed trade_id={tid}: {e}", "WARN")

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
        # Tighter trail tiers for flat markets. Thresholds are PERCENT, same as
        # PM_TRAIL_ACTIVATE_PCT/DISTANCE above — peak_pnl is percent (pnl_utils
        # compute_live_pnl), so decimal-style 0.015/0.030 matched EVERY peak and
        # pinned the 0.50% tier (floor below entry at arm) instead of the 0.10% tier.
        PM_TRAIL_TIERS = [
            (0.0,  0.1),   # 0%–1.5%: 0.10% trail (spider — very tight)
            (1.5,  0.3),   # 1.5%–3.0%: 0.30% trail
            (3.0,  0.5),   # 3.0%+: 0.50% trail
        ]
        # Tripwire only — never raise: an exception here stops ALL profit-monster
        # exits (tiers included) for this fire. A decimal threshold (0.015) matches
        # every percent peak and pins the loosest tier, so the floor sits below entry.
        if any(t[0] < 1.0 for t in PM_TRAIL_TIERS[1:]):
            log("SPIDER PM_TRAIL_TIERS thresholds are not in percent — trail floor will sit below entry",
                "ERROR")

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


def _selfcheck() -> bool:
    """trail-state GC (orphans die, live keys survive) + pm_armed_at stamp round-trip."""
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'} {name}")
        ok = ok and bool(cond)

    with tempfile.TemporaryDirectory() as d:
        f = str(Path(d) / "ts.json")
        Path(f).write_text(json.dumps({"111": {"token": "A"}, "222": {"token": "B"}}))
        # live keys survive; orphans drop
        dropped = _gc_trail_state(["222"], f)
        check("orphans dropped, live kept", dropped == 1
              and set(json.loads(Path(f).read_text())) == {"222"})
        # empty managed set clears everything (bypassed/CEO-only book)
        check("empty managed set clears", _gc_trail_state([], f) == 1
              and json.loads(Path(f).read_text()) == {})
        # empty state, non-empty kept -> no-op, no write
        check("empty state no-op", _gc_trail_state(["999"], f) == 0)
        # unreadable file -> 0, no crash
        Path(f).write_text("{not json")
        check("unreadable file no-op", _gc_trail_state(["1"], f) == 0)
        # non-str ids are normalised
        Path(f).write_text(json.dumps({"222": {}}))
        check("int ids normalised", _gc_trail_state([222], f) == 0)

    # pm_armed_at stamp: round-trips on populated + empty metadata, keeps prior
    # keys, no-ops on missing id — all inside one transaction that ROLLS BACK.
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname="brain", user="postgres",
                                password=BRAIN_PASSWORD, connect_timeout=10)
    except Exception as e:
        print(f"  SKIP pm_armed stamp (DB unreachable: {e})")
        return ok
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, _signal_metadata FROM trades "
                        "WHERE _signal_metadata IS NOT NULL ORDER BY id DESC LIMIT 1")
            row_a = cur.fetchone()
            cur.execute("SELECT id FROM trades ORDER BY id DESC LIMIT 1")
            row_b = cur.fetchone()
            check("stamp fixtures found", row_a is not None and row_b is not None)
            if row_a is not None:
                # psycopg2 decodes jsonb -> dict
                before = row_a[1] if isinstance(row_a[1], dict) else json.loads(row_a[1])
                cur.execute(_PM_ARMED_SQL, (row_a[0],))
                check("UPDATE matched", cur.rowcount == 1)
                cur.execute("SELECT _signal_metadata FROM trades WHERE id=%s", (row_a[0],))
                after = cur.fetchone()[0]
                if not isinstance(after, dict):
                    after = json.loads(after)
                # all pre-existing keys must survive (stamp may overwrite itself)
                check("prior keys preserved",
                      all(after.get(k) == v for k, v in before.items()))
                check("pm_armed_at stamped", bool(after.get("pm_armed_at")))
            if row_b is not None:
                # NULL metadata path: COALESCE must build an object, not NULL
                cur.execute("UPDATE trades SET _signal_metadata=NULL WHERE id=%s", (row_b[0],))
                cur.execute(_PM_ARMED_SQL, (row_b[0],))
                cur.execute("SELECT _signal_metadata FROM trades WHERE id=%s", (row_b[0],))
                after_b = cur.fetchone()[0]
                if not isinstance(after_b, dict):
                    after_b = json.loads(after_b)
                check("NULL metadata -> object with stamp", bool(after_b.get("pm_armed_at")))
            cur.execute(_PM_ARMED_SQL, (-1,))
            check("missing id is a no-op", cur.rowcount == 0)
    except Exception as e:
        print(f"  FAIL pm_armed stamp ({e})")
        ok = False
    finally:
        try:
            conn.rollback()   # never persist the selfcheck writes
            conn.close()
        except Exception:
            pass
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profit Monster — Two-tier take-profit")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--selfcheck", action="store_true", help="trail-state GC self-test")
    args = parser.parse_args()
    if args.selfcheck:
        good = _selfcheck()
        print(f"SELF-CHECK {'PASS' if good else 'FAIL'}")
        raise SystemExit(0 if good else 1)
    run(dry_run=args.dry_run)
