#!/usr/bin/env python3
"""
Trade Watchdog — Autonomous trade monitor and steer engine.
Runs every 30 minutes. Checks open trades against market conditions.
Produces steers: profit locks, regime alerts, stale trade flags, opportunity gaps.
Phase 1: Recommendation only. Phase 2: Auto-execution.

Usage:
    python3 scripts/trade_watchdog.py              # Full run (collect + analyze + output)
    python3 scripts/trade_watchdog.py --collect     # Collect data only
    python3 scripts/trade_watchdog.py --analyze     # Analyze collected data
    python3 scripts/trade_watchdog.py --dry-run     # Analyze but don't write outputs
"""

import sys
import os
import json
import time
import math
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add scripts dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *

# --- Configuration ---
STEER_OUTPUT = os.path.join(WWW_DATA, "watchdog.json")
ACTIONS_LOG = os.path.join(WWW_DATA, "watchdog_actions.json")
RECOMMEND_OUTPUT = os.path.join(HERMES_DATA, "watchdog_recommendations.json")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = HERMES_DATA
LOGS_DIR = HERMES_LOG_DIR

# Price alerts — levels in JSON config (CEO-editable, no code change needed).
# Fires once per crossing; re-arms when price returns past the rearm level.
PRICE_ALERT_CONFIG = os.path.join(HERMES_DATA, "watchdog_price_alerts.json")
PRICE_ALERT_STATE = os.path.join(HERMES_DATA, "watchdog_price_alerts_state.json")

# Pending (conditional) entries — internal stop-limit simulation. The watchdog
# monitors trigger_price each cycle; on cross it alerts (steer) AND executes
# via brain.py trade add (regular path, NO --manual → vacation pause still
# gates). One-shot: fires once, never re-arms. CEO-editable JSON.
PENDING_ORDERS_CONFIG = os.path.join(HERMES_DATA, "pending_orders.json")
PENDING_ORDERS_STATE = os.path.join(HERMES_DATA, "pending_orders_state.json")
# Execution context — set in main() before analyze_all. False in recommend mode
# or --dry-run: triggers still emit steers (visibility) but do NOT persist
# 'triggered' state, so the order stays armed for when autopilot can execute
# (bug_hunter: recommend/dry-run used to burn one-shot orders silently).
PENDING_ORDERS_CAN_PERSIST = True

# Thresholds
PROFIT_LOCK_BREAKEVEN_PCT = 2.0    # Move stop to breakeven at +2%
PROFIT_LOCK_TRAIL_PCT = 5.0        # Trail stop at +5%
PROFIT_LOCK_TRAIL_DISTANCE = 3.0   # Trail 3% below current price
STALE_TRADE_WARNING_HOURS = 4      # Warn after 4 hours
STALE_TRADE_CRITICAL_HOURS = 8     # Critical after 8 hours
CLUSTER_WINDOW_MINUTES = 30        # Trades within 30 min = cluster
MAX_SAME_COIN_TRADES = 2           # Max trades on same coin
MAX_SAME_DIRECTION = 3             # Max trades in same direction
MFE_GIVEBACK_URGENT_PCT = 5.0      # Gave back 5%+ of MFE = urgent
MFE_GIVEBACK_WARNING_PCT = 3.0     # Gave back 3%+ of MFE = warning
# brain_auditor #289: losing-streak self-diagnosis (steer-001). mfe_pct is in
# PERCENT units in PG (0.40 = 0.40%), matching the pm trail-activation band.
STEER_ARMED_MFE_PCT = 0.40         # >= this at exit = trade armed (trail band)
STEER_NEVER_ARMED_SHARE = 0.60     # majority of losses below arm = chop cohort

# Mode: "recommend" or "autopilot"
# Auto-switches after DEPLOY_TIME + AUTOPILOT_DELAY_HOURS
AUTOPILOT_DELAY_HOURS = 48
DEPLOY_TIME_FILE = os.path.join(HERMES_DATA, "watchdog_deploy_time.json")

# ponytail: killed-signal steer filter (DRIFT-W1) — historical closes from
# disabled signals still emit false "losing streak" steers. Map trade signal
# names → live hermes_constants flags. Extend when new kills land.
_SIGNAL_FLAG_MAP = (
    ('trend-ride', 'TREND_RIDE_LONG_ENABLED'),
    ('trend_ride', 'TREND_RIDE_LONG_ENABLED'),
    ('mover+', 'MOVER_PLUS_ENABLED'),
    ('mover-', 'MOVER_MINUS_ENABLED'),
    ('mtf-regime-trend+', 'MTF_REGIME_TREND_PLUS_ENABLED'),
    ('mtf-regime-trend-', 'MTF_REGIME_TREND_MINUS_ENABLED'),
    ('mtf_regime_trend+', 'MTF_REGIME_TREND_PLUS_ENABLED'),
    ('mtf_regime_trend-', 'MTF_REGIME_TREND_MINUS_ENABLED'),
    ('accel-300+', 'ACCEL_300_PLUS_ENABLED'),
    ('accel-300-', 'ACCEL_300_MINUS_ENABLED'),
    ('accel_300+', 'ACCEL_300_PLUS_ENABLED'),
    ('accel_300-', 'ACCEL_300_MINUS_ENABLED'),
    ('wave-catcher', 'WAVE_CATCHER_ENABLED'),
    ('wave_catcher', 'WAVE_CATCHER_ENABLED'),
    ('coin-tracker-hot', 'COIN_TRACKER_HOT_ENABLED'),
    ('coin_tracker_hot', 'COIN_TRACKER_HOT_ENABLED'),
    ('vel-hermes', 'VEL_HERMES_ENABLED'),
    ('vel_hermes', 'VEL_HERMES_ENABLED'),
    ('pump-catcher', 'PUMP_CATCHER_ENABLED'),
    ('pump_catcher', 'PUMP_CATCHER_ENABLED'),
    ('pattern-wolf', 'PATTERN_WOLF_ENABLED'),
    ('pattern_wolf', 'PATTERN_WOLF_ENABLED'),
    # Killed Oct 2026 — kept in map so historical closes stop emitting steers
    ('doji-bottom-long', 'DOJI_BOTTOM_ENABLED'),
    ('volume-buildup+', 'VOLUME_BUILDUP_PLUS_ENABLED'),
    ('volume-breakout-long', 'VOLUME_BREAKOUT_PLUS_ENABLED'),
    ('volume-breakout-short', 'VOLUME_BREAKOUT_MINUS_ENABLED'),
    ('oversold-bounce', 'OVERSOLD_BOUNCE_ENABLED'),
    ('hmacd_mtf-+', 'HMACD_MTF_MINUS_ENABLED'),
    ('hmacd_mtf+', 'HMACD_MTF_PLUS_ENABLED'),
    ('hmacd_mtf-', 'HMACD_MTF_MINUS_ENABLED'),
    ('pump-chain-v5', 'PUMP_CHAIN_V5_ENABLED'),
    ('trend-purity', 'TREND_PURITY_ENABLED'),
    ('trend_purity', 'TREND_PURITY_ENABLED'),
)


def _signal_is_disabled(sig: str) -> bool:
    """True when trade signal name maps to a False *_ENABLED flag in constants."""
    if not sig:
        return False
    s = sig.lower()
    try:
        import hermes_constants as hc
        for frag, flag in _SIGNAL_FLAG_MAP:
            if frag in s:
                if getattr(hc, flag, True) is False:
                    return True
        return False
    except Exception:
        return False
AUTO_EXECUTABLE_CATEGORIES = {"profit_lock", "pending_order"}  # Only these actions auto-execute


def get_watchdog_mode():
    """Determine current mode: recommend for first 48h, then autopilot.
    Env var WATCHDOG_MODE overrides (for emergency manual control).
    """
    # Env var override takes precedence
    env_mode = os.environ.get("WATCHDOG_MODE")
    if env_mode in ("recommend", "autopilot"):
        log(f"Mode override from env: {env_mode}")
        return env_mode, datetime.now(timezone.utc), 0

    now_utc = datetime.now(timezone.utc)

    # Check/create deploy time marker
    if os.path.exists(DEPLOY_TIME_FILE):
        try:
            with open(DEPLOY_TIME_FILE) as f:
                data = json.load(f)
            deploy_str = data.get("deploy_time")
            if deploy_str:
                deploy_time = datetime.fromisoformat(deploy_str.replace("Z", "+00:00"))
                elapsed = (now_utc - deploy_time).total_seconds() / 3600
                if elapsed >= AUTOPILOT_DELAY_HOURS:
                    return "autopilot", deploy_time, elapsed
                return "recommend", deploy_time, elapsed
        except Exception:
            pass

    # First run — record deploy time
    deploy_time = now_utc
    try:
        atomic_write_json(DEPLOY_TIME_FILE, {
            "deploy_time": deploy_time.isoformat(),
            "note": f"Autopilot engages after {AUTOPILOT_DELAY_HOURS}h"
        })
    except Exception:
        pass
    return "recommend", deploy_time, 0

# ============================================================
# HELPERS
# ============================================================

def default_serial(obj):
    """Handle Decimal, datetime, etc for JSON serialization."""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


now = datetime.now(timezone.utc)


def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def atomic_write_json(path, data):
    """Write JSON atomically — write to .tmp then rename."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2, default=default_serial)
    os.rename(tmp_path, path)


# ============================================================
# DATA COLLECTION
# ============================================================

def get_db():
    """Get PostgreSQL connection via psql."""
    import psycopg2
    try:
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        return conn
    except Exception as e:
        log(f"PostgreSQL connection failed: {e}", "ERROR")
        return None


def collect_open_trades():
    """Get all currently open trades from PostgreSQL."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        # Get trades that are OPEN (no close_time or exit_price)
        cur.execute("""
            SELECT id, token, direction, entry_price, open_time,
                   amount_usdt, signal, _signal_metadata,
                   pnl_usdt, leverage, stop_loss, target,
                   regime, close_time, exit_price,
                   current_price, mfe_pct, mae_pct,
                   highest_price, lowest_price
            FROM trades
            WHERE close_time IS NULL
              AND (exit_price IS NULL OR exit_price = 0)
            ORDER BY open_time DESC
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        trades = []
        for row in rows:
            trade = dict(zip(cols, row))
            # Parse signal_metadata if JSON string
            if trade.get('_signal_metadata') and isinstance(trade['_signal_metadata'], str):
                try:
                    trade['_signal_metadata'] = json.loads(trade['_signal_metadata'])
                except:
                    pass
            # DRIFT-E: entry_rsi_14 column is late/wrong-TF — meta.rsi_14 is signal-time truth
            meta = trade.get('_signal_metadata')
            if isinstance(meta, dict):
                trade['meta_rsi'] = meta.get('rsi_14')
            # Normalize field names for consistency
            trade['coin'] = trade.get('token', '?')
            trade['entry_time'] = trade.get('open_time')
            trade['signal_name'] = trade.get('signal', '?')
            trade['take_profit'] = trade.get('target')
            trade['volatility_regime'] = trade.get('regime')
            trades.append(trade)

        log(f"Found {len(trades)} open trades")
        return trades
    except Exception as e:
        log(f"Error collecting open trades: {e}", "ERROR")
        return []
    finally:
        conn.close()


def collect_recent_closed(limit=20):
    """Get last N closed trades."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, exit_price,
                   open_time, close_time, pnl_usdt, pnl_pct, signal,
                   _signal_metadata, regime,
                   amount_usdt, leverage, exit_reason, mfe_pct
            FROM trades
            WHERE close_time IS NOT NULL
              AND exit_price IS NOT NULL AND exit_price != 0
            ORDER BY close_time DESC, id DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        trades = []
        for row in rows:
            trade = dict(zip(cols, row))
            if trade.get('_signal_metadata') and isinstance(trade['_signal_metadata'], str):
                try:
                    trade['_signal_metadata'] = json.loads(trade['_signal_metadata'])
                except:
                    pass
            meta = trade.get('_signal_metadata')
            if isinstance(meta, dict):
                trade['meta_rsi'] = meta.get('rsi_14')
            # Normalize
            trade['coin'] = trade.get('token', '?')
            trade['entry_time'] = trade.get('open_time')
            trade['exit_time'] = trade.get('close_time')
            trade['signal_name'] = trade.get('signal', '?')
            trade['volatility_regime'] = trade.get('regime')
            trades.append(trade)

        log(f"Collected {len(trades)} recent closed trades")
        return trades
    except Exception as e:
        log(f"Error collecting recent trades: {e}", "ERROR")
        return []
    finally:
        conn.close()


def _merge_intervals(ivs):
    """Merge overlapping (start, end) datetime intervals. Input not mutated."""
    if not ivs:
        return []
    items = sorted((s, e) for s, e in ivs if e > s)
    if not items:
        return []
    merged = [list(items[0])]
    for s, e in items[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def collect_exposure(hours=24):
    """Fraction of the last `hours` with >=1 position open (CEO exposure KPI).

    CEO must-have (session 2026-10-02 'can you use the watch (1)' + 2026-11-08
    youtube watch): "we're flying blind on how much time we're actually
    in-market". Zero-behaviour — reporting only.
    """
    conn = get_db()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        cur.execute("""
            SELECT open_time, COALESCE(close_time, %s)
            FROM trades
            WHERE open_time < %s
              AND COALESCE(close_time, %s) > %s
        """, (end, end, end, start))
        ivs = []
        for opened, closed in cur.fetchall():
            if opened is None or closed is None:
                continue
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=timezone.utc)
            if closed.tzinfo is None:
                closed = closed.replace(tzinfo=timezone.utc)
            if closed > opened:
                ivs.append((max(opened, start), min(closed, end)))
        if not ivs:
            return {"hours": hours, "in_market_pct": 0.0, "trades": 0}
        merged = _merge_intervals(ivs)
        covered = sum((e - s).total_seconds() for s, e in merged)
        pct = 100.0 * covered / (hours * 3600.0)
        return {"hours": hours, "in_market_pct": round(min(pct, 100.0), 1),
                "trades": len(ivs)}
    except Exception as e:
        log(f"Error collecting exposure: {e}", "ERROR")
        return None
    finally:
        conn.close()


def collect_btc_regime():
    """Read current BTC regime from multiple sources."""
    regime = {
        "btc_15m": None,
        "btc_4h": None,
        "continuum": None,
        "volatility": None
    }

    # BTC regime from regime_5m.json (scanner renamed output file)
    regime_15m_path = os.path.join(WWW_DATA, "regime_5m.json")
    if os.path.exists(regime_15m_path):
        try:
            with open(regime_15m_path) as f:
                data = json.load(f)
                agg = data.get("aggregate", {})
                regime["btc_15m"] = agg.get("overall", "unknown")
        except Exception:
            pass

    # BTC 4h regime from /var/www/html/regime_4h.json
    regime_4h_path = "/var/www/html/regime_4h.json"
    if os.path.exists(regime_4h_path):
        try:
            with open(regime_4h_path) as f:
                data = json.load(f)
                agg = data.get("aggregate", {})
                regime["btc_4h"] = agg.get("overall", "unknown")
        except Exception:
            pass

    # Continuum oscillator (main regime source — rich data)
    continuum_path = os.path.join(WWW_DATA, "continuum_data.json")
    if os.path.exists(continuum_path):
        try:
            with open(continuum_path) as f:
                data = json.load(f)
                current = data.get("current", {})
                regime["continuum"] = current.get("ema300_position", "unknown")
                regime["zscore_tier"] = current.get("zscore_tier", "unknown")
                regime["velocity_state"] = current.get("velocity_state", "unknown")
                regime["acceleration_state"] = current.get("acceleration_state", "unknown")
                regime["volume_regime"] = current.get("volume_regime", "unknown")
                regime["linreg_alignment"] = current.get("linreg_alignment", 0)
                regime["wyckoff_phase"] = current.get("wyckoff_phase", "unknown")
                regime["market_phase"] = current.get("market_phase", "unknown")
                regime["trend_quality"] = current.get("trend_quality", "unknown")
                # Volatility from volume_regime (no separate gate JSON)
                regime["volatility"] = current.get("volume_regime", "unknown")
        except Exception:
            pass

    # Override volatility with gate if available
    vol_path = os.path.join(HERMES_DATA, "volatility_gate_v2.json")
    if os.path.exists(vol_path):
        try:
            with open(vol_path) as f:
                data = json.load(f)
                regime["volatility"] = data.get("current_phase", "unknown")
        except Exception:
            pass

    log(f"BTC regime: 15m={regime['btc_15m']}, 4h={regime['btc_4h']}, "
        f"continuum={regime['continuum']}, vol={regime['volatility']}")
    return regime


def collect_coin_tracker():
    """Read coin tracker data for per-coin stats."""
    # Try JSON first
    ct_json_path = os.path.join(WWW_DATA, "coin_tracker_data.json")
    if os.path.exists(ct_json_path):
        try:
            with open(ct_json_path) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    return {item.get("coin", item.get("symbol", "")): item for item in data}
        except Exception:
            pass

    # Fall back to SQLite
    ct_db_path = os.path.join(HERMES_DATA, "coin_tracker.db")
    if os.path.exists(ct_db_path):
        conn = None
        try:
            import sqlite3
            conn = sqlite3.connect(ct_db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Get table names first
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]

            coins = {}
            for table in tables:
                # Validate table name to prevent injection
                if not table.isidentifier():
                    continue
                try:
                    cur.execute(f"SELECT * FROM [{table}] ORDER BY rowid DESC LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        coins[table] = dict(row)
                except Exception:
                    pass
            if coins:
                log(f"Coin tracker: loaded {len(coins)} coins from SQLite")
            return coins
        except Exception as e:
            log(f"Error reading coin tracker DB: {e}", "WARN")
        finally:
            if conn:
                conn.close()

    return {}


def collect_pipeline_status():
    """Check if pipeline is running and when it last ran."""
    status = {
        "running": False,
        "last_run": None,
        "signals_enabled": True
    }

    # Check lock file
    lock_path = "/tmp/hermes-pipeline.lock"
    if os.path.exists(lock_path):
        try:
            lock_age = time.time() - os.path.getmtime(lock_path)
            status["running"] = lock_age < 300  # Running if lock < 5 min old
        except Exception:
            pass

    # Check last pipeline log entry
    log_path = os.path.join(LOGS_DIR, "pipeline.log")
    if os.path.exists(log_path):
        try:
            # flock never updates the lock file's mtime, so lock_age alone reads
            # constant-false once the lock file exists (mtime frozen 2026-10-18).
            # Log freshness is the real liveness signal — pipeline logs every cycle.
            if time.time() - os.path.getmtime(log_path) < 300:
                status["running"] = True
            result = subprocess.run(
                ["tail", "-1", log_path],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                status["last_run"] = result.stdout.strip()[:100]
        except Exception:
            pass

    return status


def collect_signal_performance():
    """Get per-signal performance from recent trades."""
    conn = get_db()
    if not conn:
        return {}

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT signal,
                   COUNT(*) as total,
                   SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl_usdt) as total_pnl,
                   AVG(pnl_usdt) as avg_pnl
            FROM trades
            WHERE close_time IS NOT NULL
              AND close_time > NOW() - INTERVAL '14 days'
            GROUP BY signal
            ORDER BY total_pnl DESC
        """)
        rows = cur.fetchall()

        perf = {}
        for row in rows:
            sig, total, wins, total_pnl, avg_pnl = row
            if sig:
                perf[sig] = {
                    "total": total,
                    "wins": wins or 0,
                    "wr": round((wins / total * 100) if total > 0 else 0, 1),
                    "total_pnl": round(float(total_pnl or 0), 2),
                    "avg_pnl": round(float(avg_pnl or 0), 2)
                }

        log(f"Collected performance for {len(perf)} signals")
        return perf
    except Exception as e:
        log(f"Error collecting signal performance: {e}", "ERROR")
        return {}
    finally:
        conn.close()


# ============================================================
# ANALYSIS ENGINE
# ============================================================

def analyze_regime_alignment(open_trades, btc_regime):
    """Check if open trades are aligned with current BTC regime."""
    steers = []

    btc_trend = btc_regime.get("continuum") or btc_regime.get("btc_4h") or btc_regime.get("btc_15m", "unknown")

    if btc_trend == "unknown":
        return steers

    for trade in open_trades:
        direction = (trade.get("direction") or "").lower()
        coin = trade.get("coin", "?")

        # Bull regime + short = misaligned
        if btc_trend in ("bull", "expansion", "rising") and direction == "short":
            steers.append({
                "severity": "warning",
                "category": "regime",
                "title": f"{coin} SHORT in bull regime",
                "detail": f"BTC is {btc_trend} but we're short {coin}. Consider closing or hedging.",
                "trade_id": trade.get("id"),
                "auto_executable": False  # Direction changes need human
            })

        # Bear regime + long = misaligned
        if btc_trend in ("bear", "contraction", "falling") and direction == "long":
            steers.append({
                "severity": "warning",
                "category": "regime",
                "title": f"{coin} LONG in bear regime",
                "detail": f"BTC is {btc_trend} but we're long {coin}. Monitor closely.",
                "trade_id": trade.get("id"),
                "auto_executable": False
            })

    return steers


def analyze_profit_lock(open_trades):
    """Check if any trades qualify for profit lock (breakeven or trailing stop)."""
    watchdog_mode = get_watchdog_mode()[0]
    steers = []

    for trade in open_trades:
        entry = float(trade.get("entry_price") or 0)
        current = float(trade.get("current_price") or trade.get("entry_price") or 0)
        direction = (trade.get("direction") or "").lower()
        coin = trade.get("coin", "?")

        if entry <= 0 or current <= 0:
            continue

        # Calculate PnL percentage
        if direction == "long":
            pnl_pct = ((current - entry) / entry) * 100
        else:
            pnl_pct = ((entry - current) / entry) * 100

        # MFE analysis
        mfe = float(trade.get("mfe_pct") or 0)
        giveback = mfe - pnl_pct if mfe > 0 else 0

        current_sl = float(trade.get("stop_loss") or 0)

        # Trade up 5%+ → trail stop
        if pnl_pct >= PROFIT_LOCK_TRAIL_PCT:
            if direction == "long":
                new_stop = current * (1 - PROFIT_LOCK_TRAIL_DISTANCE / 100)
            else:
                new_stop = current * (1 + PROFIT_LOCK_TRAIL_DISTANCE / 100)

            # FIX (BUG-043, 2026-10-08): tighten-check — never propose a stop LOOSER
            # than the current one (e.g. tpsl already trailed tighter; executing this
            # steer would widen the stop and give back profit). LONG: new must be
            # ABOVE current_sl; SHORT: new must be BELOW current_sl.
            if current_sl > 0:
                if (direction == "long" and new_stop <= current_sl) or \
                   (direction == "short" and new_stop >= current_sl):
                    continue

            steers.append({
                "severity": "info",
                "category": "profit_lock",
                "title": f"Trail stop on {coin} — up {pnl_pct:.1f}%",
                "detail": f"MFE was {mfe:.1f}%. Current +{pnl_pct:.1f}%. "
                          f"Move stop from {current_sl:.4f} to {new_stop:.4f} to lock {pnl_pct - PROFIT_LOCK_TRAIL_DISTANCE:.1f}%.",
                "trade_id": trade.get("id"),
                "action": {
                    "type": "move_stop",
                    "symbol": coin,
                    "direction": direction,
                    "new_stop": round(new_stop, 6)
                },
                "auto_executable": watchdog_mode == "autopilot"
            })

        # Trade up 2%+ but < 5% → move to breakeven
        elif pnl_pct >= PROFIT_LOCK_BREAKEVEN_PCT:
            # Only suggest if stop is still below entry
            if direction == "long" and (current_sl < entry or current_sl == 0):
                steers.append({
                    "severity": "info",
                    "category": "profit_lock",
                    "title": f"Move {coin} stop to breakeven — up {pnl_pct:.1f}%",
                    "detail": f"Trade is +{pnl_pct:.1f}%. Lock breakeven at {entry:.4f}.",
                    "trade_id": trade.get("id"),
                    "action": {
                        "type": "move_stop",
                        "symbol": coin,
                        "direction": direction,
                        "new_stop": round(entry, 6)
                    },
                    "auto_executable": watchdog_mode == "autopilot"
                })
            elif direction == "short" and (current_sl > entry or current_sl == 0):
                steers.append({
                    "severity": "info",
                    "category": "profit_lock",
                    "title": f"Move {coin} stop to breakeven — up {pnl_pct:.1f}%",
                    "detail": f"Trade is +{pnl_pct:.1f}%. Lock breakeven at {entry:.4f}.",
                    "trade_id": trade.get("id"),
                    "action": {
                        "type": "move_stop",
                        "symbol": coin,
                        "direction": direction,
                        "new_stop": round(entry, 6)
                    },
                    "auto_executable": watchdog_mode == "autopilot"
                })

        # MFE giveback analysis
        if giveback >= MFE_GIVEBACK_URGENT_PCT:
            steers.append({
                "severity": "urgent",
                "category": "profit_lock",
                "title": f"{coin} gave back {giveback:.1f}% of MFE",
                "detail": f"MFE was {mfe:.1f}%, now +{pnl_pct:.1f}%. "
                          f"We gave back {giveback:.1f}%. Tighten immediately.",
                "trade_id": trade.get("id"),
                "auto_executable": False  # Urgent but human decides
            })
        elif giveback >= MFE_GIVEBACK_WARNING_PCT:
            steers.append({
                "severity": "warning",
                "category": "profit_lock",
                "title": f"{coin} giving back MFE ({giveback:.1f}%)",
                "detail": f"MFE was {mfe:.1f}%, now +{pnl_pct:.1f}%. Consider tightening.",
                "trade_id": trade.get("id"),
                "auto_executable": watchdog_mode == "autopilot"
            })

    return steers


def analyze_stale_trades(open_trades):
    """Flag trades that have been open too long."""
    watchdog_mode = get_watchdog_mode()[0]
    steers = []

    for trade in open_trades:
        entry_time = trade.get("entry_time")
        if not entry_time:
            continue

        if isinstance(entry_time, str):
            try:
                entry_time = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
            except:
                continue

        # Make naive datetimes timezone-aware (assume UTC)
        if isinstance(entry_time, datetime) and entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)

        hours_open = (now - entry_time).total_seconds() / 3600
        coin = trade.get("coin", "?")
        direction = (trade.get("direction") or "?").lower()  # PG stores LONG/SHORT; must lower or PnL sign inverts for LONGs

        # Get current PnL
        entry = float(trade.get("entry_price") or 0)
        current = float(trade.get("current_price") or entry)
        if entry > 0 and current > 0:
            if direction == "long":
                pnl_pct = ((current - entry) / entry) * 100
            else:
                pnl_pct = ((entry - current) / entry) * 100
        else:
            pnl_pct = 0

        if hours_open >= STALE_TRADE_CRITICAL_HOURS:
            if pnl_pct <= 0:
                steers.append({
                    "severity": "urgent",
                    "category": "stale",
                    "title": f"{coin} open {hours_open:.0f}h, losing {pnl_pct:.1f}%",
                    "detail": f"Trade open {hours_open:.0f} hours and underwater. "
                              f"Thesis may be invalid. Consider cutting.",
                    "trade_id": trade.get("id"),
                    "auto_executable": False
                })
            else:
                steers.append({
                    "severity": "warning",
                    "category": "stale",
                    "title": f"{coin} open {hours_open:.0f}h, barely profitable",
                    "detail": f"Trade open {hours_open:.0f} hours. Only +{pnl_pct:.1f}%. "
                              f"Opportunity cost — consider freeing capital.",
                    "trade_id": trade.get("id"),
                    "auto_executable": watchdog_mode == "autopilot"
                })

        elif hours_open >= STALE_TRADE_WARNING_HOURS:
            if pnl_pct <= -1:
                steers.append({
                    "severity": "warning",
                    "category": "stale",
                    "title": f"{coin} open {hours_open:.0f}h, losing",
                    "detail": f"Trade open {hours_open:.0f} hours, down {pnl_pct:.1f}%. Monitor closely.",
                    "trade_id": trade.get("id"),
                    "auto_executable": False
                })

    return steers


def analyze_trade_clusters(open_trades):
    """Detect trade clustering (opened close together, same coin, same direction)."""
    steers = []

    if len(open_trades) < 2:
        return steers

    # Sort by entry time
    timed = []
    for t in open_trades:
        et = t.get("entry_time")
        if et:
            if isinstance(et, str):
                try:
                    et = datetime.fromisoformat(et.replace("Z", "+00:00"))
                except:
                    continue
            timed.append((et, t))
    timed.sort(key=lambda x: x[0])

    # Check time clusters
    for i in range(len(timed)):
        for j in range(i+1, len(timed)):
            gap = (timed[j][0] - timed[i][0]).total_seconds() / 60
            if gap > CLUSTER_WINDOW_MINUTES:
                break
            t1, t2 = timed[i][1], timed[j][1]
            steers.append({
                "severity": "warning",
                "category": "cluster",
                "title": f"Trade cluster: {t1.get('coin')} + {t2.get('coin')}",
                "detail": f"Both opened within {gap:.0f} minutes. Correlation risk.",
                "auto_executable": False
            })

    # Check same coin
    coin_counts = {}
    for t in open_trades:
        c = t.get("coin", "?")
        coin_counts[c] = coin_counts.get(c, 0) + 1

    for coin, count in coin_counts.items():
        if count >= MAX_SAME_COIN_TRADES:
            steers.append({
                "severity": "urgent",
                "category": "cluster",
                "title": f"Over-exposed to {coin}: {count} trades",
                "detail": f"{count} open trades on {coin}. Diversify or reduce.",
                "auto_executable": False
            })

    # Check same direction
    long_count = sum(1 for t in open_trades if (t.get("direction") or "").lower() == "long")
    short_count = sum(1 for t in open_trades if (t.get("direction") or "").lower() == "short")

    if long_count >= MAX_SAME_DIRECTION:
        steers.append({
            "severity": "warning",
            "category": "cluster",
            "title": f"Portfolio heavily long ({long_count} trades)",
            "detail": f"{long_count} long positions. One BTC dump hits all of them.",
            "auto_executable": False
        })

    if short_count >= MAX_SAME_DIRECTION:
        steers.append({
            "severity": "warning",
            "category": "cluster",
            "title": f"Portfolio heavily short ({short_count} trades)",
            "detail": f"{short_count} short positions. One BTC pump hits all of them.",
            "auto_executable": False
        })

    return steers


def analyze_recent_losses(recent_trades):
    """Analyze recent closed trades for patterns.

    Contract (bug-hunter #115): recent_trades must be close_time DESC —
    the per-signal streak walk (line ~897) counts TRAILING losses from index 0.
    Sole caller: analyze_all <- collect_recent_closed (ORDER BY close_time DESC, id DESC).
    """
    steers = []

    if not recent_trades:
        return steers

    losses = [t for t in recent_trades if (t.get("pnl_usdt") or 0) < 0]
    wins = [t for t in recent_trades if (t.get("pnl_usdt") or 0) > 0]

    total = len(recent_trades)
    loss_count = len(losses)
    total_pnl = sum(t.get("pnl_usdt", 0) or 0 for t in recent_trades)

    # Overall performance
    wr = (wins.__len__() / total * 100) if total > 0 else 0

    if loss_count >= 5 and len(losses) >= total * 0.6:
        detail = (f"Win rate {wr:.0f}% over last {total} trades. "
                  f"Total PnL: {total_pnl:+.2f} USDT.")
        # brain_auditor #289: "Something is wrong" forced every run to re-derive
        # the same chop diagnosis by hand. Say what the window IS: never-armed
        # losses = chop cohort (arm/stall owns the fix), armed-then-gave-back =
        # exit/lock review. Composition only — no advice, no disable/tune.
        mfes = [float(t["mfe_pct"]) for t in losses if t.get("mfe_pct") is not None]
        if mfes:
            armed = sum(1 for m in mfes if m >= STEER_ARMED_MFE_PCT)
            never = len(mfes) - armed
            reasons = [t.get("exit_reason") or "?" for t in losses]
            mix = ", ".join(f"{r} x{reasons.count(r)}"
                            for r in sorted(set(reasons), key=reasons.count, reverse=True)[:3])
            if never >= len(mfes) * STEER_NEVER_ARMED_SHARE:
                detail += (f" {never}/{len(mfes)} losses never armed "
                           f"(MFE<{STEER_ARMED_MFE_PCT:.2f}%) = chop cohort, not wrong-side; "
                           f"arm-rate/stall stack owns the fix. Exits: {mix}.")
            elif armed >= len(mfes) * STEER_NEVER_ARMED_SHARE:
                detail += (f" {armed}/{len(mfes)} losses armed then gave back "
                           f"= exit/lock review, not entry. Exits: {mix}.")
            else:
                detail += (f" Exit mix: {mix} — neither armed-giveback nor "
                           f"never-armed dominant. Something is wrong.")
        else:
            detail += " Something is wrong."
        steers.append({
            "severity": "urgent",
            "category": "health",
            "title": f"Losing streak: {loss_count}/{total} recent trades lost",
            "detail": detail,
            "auto_executable": False
        })

    # Pattern: wrong direction
    # brain_auditor 2026-10-08: was abs(pnl_usdt)/entry_price > 0.02 — unit bug.
    # brain_auditor 2026-10-22: account% threshold was a 2nd unit bug. pnl_pct is
    # account% (price% x leverage), so EVERY designed stop at 5x (HML -4% account
    # = -0.8% price) cleared the 2% bar — detector counted the safety net as
    # wrong-side. Evidence: fired >=3 on 23/30 days; 6 consecutive audit runs
    # refuted it (17/17 24h losers recovered within -0.2% of entry in 30m of
    # 1m candles); 7d account>2% losses avg only 0.53-1.12% PRICE against.
    # Correct: price-term loss > 1.5% = real adverse move. 30d: fires on 10/384
    # losses (vs 234), >=3-cluster on exactly 1 day (Sep 24: 4 pump-chain SHORTs
    # + 1 LONG squeezed 1.5-2.0% = genuine wrong-side day).
    wrong_side = 0
    for t in losses:
        pnl_pct = t.get("pnl_pct")
        if pnl_pct is None:
            pnl = t.get("pnl_usdt", 0) or 0
            amt = float(t.get("amount_usdt") or 0)
            if amt <= 0:
                continue
            pnl_pct = (pnl / amt) * 100
        lev = float(t.get("leverage") or 0)
        if lev <= 0:
            continue  # can't normalize to price terms — skip rather than fall back to account% (the old bug)
        if abs(float(pnl_pct)) / lev > 1.5:
            wrong_side += 1

    if wrong_side >= 3:
        steers.append({
            "severity": "warning",
            "category": "health",
            "title": f"{wrong_side} recent losses moved >1.5% price against us",
            "detail": "Multiple price-term losses >1.5% (leverage-normalized) "
                      "suggest we're fading momentum. Check if signals are "
                      "aligned with trend.",
            "auto_executable": False
        })

    # Pattern: specific signal losing
    # brain_auditor 2026-10-08: only flag when the signal is NET NEGATIVE in the
    # window. Was counting raw losses — pump-chain- "7-loss streak" was actually
    # net +$0.34 over 7d (wins offset losses). Losses alone are normal variance.
    # brain_auditor #115 2026-10-24: title said "streak" but data["count"] was ALL
    # window losses — stale losses re-fired long after the streak ended
    # (volume-buildup- steer-001 emitted stale 17 audit runs). Fire on the
    # TRAILING consecutive losses only: recent_trades is close_time DESC, so walk
    # each signal's trades newest-first and stop at its first non-loss.
    sig_pnl = {}
    sig_tail_streak = {}
    sig_streak_reasons = {}
    _streak_broken = set()
    sig_losses = {}
    for t in recent_trades:
        sig = t.get("signal_name", "unknown")
        pnl = t.get("pnl_usdt", 0) or 0
        sig_pnl[sig] = sig_pnl.get(sig, 0) + pnl
        # NOTE: any pnl >= 0 breaks the streak — a breakeven prearm_lock exit
        # (+0.00/+0.01, 3 of the 10 live exits) ends it. Pre-existing streak
        # semantics, kept: the guard note is about the streak as measured.
        if sig not in _streak_broken:
            if pnl < 0:
                sig_tail_streak[sig] = sig_tail_streak.get(sig, 0) + 1
                sig_streak_reasons.setdefault(sig, []).append(t.get("exit_reason") or "?")
            else:
                _streak_broken.add(sig)
    for t in losses:
        sig = t.get("signal_name", "unknown")
        if sig not in sig_losses:
            sig_losses[sig] = {"count": 0, "total_loss": 0}
        sig_losses[sig]["count"] += 1
        sig_losses[sig]["total_loss"] += t.get("pnl_usdt", 0) or 0

    for sig, data in sig_losses.items():
        if _signal_is_disabled(sig):
            continue  # DRIFT-W1: historical losses from killed signals — not actionable
        streak = sig_tail_streak.get(sig, 0)
        if streak >= 3 and sig_pnl.get(sig, 0) < 0:
            # brain_auditor #288: prearm_lock streaks are the breakeven cap
            # (PREARM_LOCK_ENFORCE live 2026-11-20) doing its job — avg loss is
            # ~$0.01 vs $0.11 for a real stop. "Consider disabling" on that
            # streak is the wrong advice (steer-002 misread, run #288).
            reasons = sig_streak_reasons.get(sig, [])
            pl = sum(1 for r in reasons if r == "prearm_lock")
            if reasons and pl >= (len(reasons) + 1) // 2:
                advice = (f"{pl}/{len(reasons)} streak exits are prearm_lock "
                          f"breakeven caps (guard live 2026-11-20) — cap working, "
                          f"NOT a disable/tune candidate.")
            else:
                advice = "Consider disabling or tuning this signal."
            steers.append({
                "severity": "warning",
                "category": "health",
                "title": f"Signal '{sig}' losing streak: {streak} consecutive losses",
                "detail": f"Net {sig_pnl[sig]:+.2f} USDT over last {len(recent_trades)} trades "
                          f"(window losses: {data['total_loss']:+.2f}). "
                          f"{advice}",
                "auto_executable": False
            })

    return steers


def analyze_signal_quality(signal_perf, btc_regime):
    """Check which signals are performing well/poorly right now."""
    steers = []

    btc_trend = btc_regime.get("continuum") or btc_regime.get("btc_4h", "unknown")

    for sig, perf in signal_perf.items():
        if _signal_is_disabled(sig):
            continue  # DRIFT-W1: skip steers for currently-disabled signals
        # Cold signal: lots of trades, negative PnL
        if perf["total"] >= 5 and perf["total_pnl"] < -2:
            steers.append({
                "severity": "warning",
                "category": "health",
                "title": f"Signal '{sig}' is cold: {perf['total_pnl']:+.2f} USDT",
                "detail": f"{perf['total']} trades, {perf['wr']}% WR, "
                          f"{perf['total_pnl']:+.2f} USDT in last 14 days.",
                "auto_executable": False
            })

        # Hot signal: encourage
        if perf["total"] >= 3 and perf["total_pnl"] > 5 and perf["wr"] >= 55:
            steers.append({
                "severity": "info",
                "category": "opportunity",
                "title": f"Signal '{sig}' is hot: {perf['total_pnl']:+.2f} USDT",
                "detail": f"{perf['total']} trades, {perf['wr']}% WR. "
                          f"Good performer in current conditions.",
                "auto_executable": False
            })

    return steers


def analyze_coin_heat(open_trades, coin_tracker):
    """Check if we're holding coins that are losing momentum."""
    steers = []

    if not coin_tracker:
        return steers

    for trade in open_trades:
        coin = trade.get("coin", "")
        direction = (trade.get("direction") or "").lower()

        # Look up coin in tracker
        ct_data = coin_tracker.get(coin, {})
        if not ct_data:
            continue

        momentum = ct_data.get("momentum", ct_data.get("trend", "unknown"))
        change_24h = ct_data.get("change_24h", ct_data.get("pct_change_24h", 0))

        # Long on a bleeding coin
        if direction == "long" and momentum in ("bearish", "down", "falling"):
            steers.append({
                "severity": "warning",
                "category": "opportunity",
                "title": f"Long {coin} but coin is losing momentum",
                "detail": f"{coin} trend is {momentum}. Consider exit.",
                "trade_id": trade.get("id"),
                "auto_executable": False
            })

        # Short on a pumping coin
        if direction == "short" and momentum in ("bullish", "up", "rising"):
            steers.append({
                "severity": "warning",
                "category": "opportunity",
                "title": f"Short {coin} but coin is gaining momentum",
                "detail": f"{coin} trend is {momentum}. Consider exit.",
                "trade_id": trade.get("id"),
                "auto_executable": False
            })

    return steers


# ============================================================
# MAIN
# ============================================================

def collect_btc_price():
    """Current BTC price from local 1m candles DB (preferred over API per SOP).

    FIX (2026-10-17, bug_hunter): try/finally closes connection on all paths;
    rejects candles older than 5 min (stale price would fire alerts on frozen data).
    """
    import sqlite3
    conn = None
    try:
        db_path = os.path.join(HERMES_DATA, "candles.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT close, ts FROM candles_1m WHERE token='BTC' AND is_closed=1 "
                    "ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        price = float(row[0])
        # Freshness guard: reject candles older than 5 min (bug_hunter: alerts
        # firing on frozen price when price_collector timer dies)
        ts = row[1]
        try:
            ts_epoch = float(ts)
            if ts_epoch > 1e12:  # milliseconds
                ts_epoch /= 1000.0
            elif ts_epoch < 1e9:  # already too small to be a valid epoch
                ts_epoch = None
        except (TypeError, ValueError):
            ts_epoch = None
        if ts_epoch is not None and (time.time() - ts_epoch) > 300:
            log(f"BTC candle stale ({(time.time()-ts_epoch)/60:.1f}min old) — "
                f"price alerts skip this cycle", "WARN")
            return None
        # Sanity: negative/zero price = corrupt candle
        if price <= 0:
            log(f"BTC candle corrupt (close={price}) — price alerts skip", "WARN")
            return None
        return price
    except Exception as e:
        log(f"BTC price fetch failed: {e}", "WARN")
        return None
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def analyze_price_alerts(btc_price):
    """Persistent price-level alerts (CEO-configured via watchdog_price_alerts.json).

    Fires once per crossing; re-arms when price returns past the rearm level.
    Survives session restarts — runs every watchdog cycle.
    Config format: {"alerts": [{"id", "coin", "level", "direction": "above"|"below",
                                "rearm", "severity", "title", "detail"}]}

    FIX (2026-10-17, bug_hunter FAIL): every alert is validated and isolated —
    a malformed entry (non-numeric level, direction typo, rearm on wrong side of
    level, bad format placeholders, non-dict config) logs a WARN and skips that
    entry instead of crashing the whole watchdog cycle (which would kill
    profit-lock steers for open trades too).
    """
    steers = []
    if btc_price is None or not os.path.exists(PRICE_ALERT_CONFIG):
        return steers
    if btc_price <= 0:  # corrupt price — never evaluate alerts against it
        return steers
    try:
        with open(PRICE_ALERT_CONFIG) as f:
            cfg = json.load(f)
    except Exception as e:
        log(f"price alert config unreadable: {e}", "WARN")
        return steers
    # Type-check: config must be a dict with an alerts LIST (bug_hunter: a bare
    # list or string config crashed the cycle)
    if not isinstance(cfg, dict) or not isinstance(cfg.get("alerts"), list):
        log("price alert config malformed: expected {\"alerts\": [...]} — skipping", "WARN")
        return steers
    state = {}
    if os.path.exists(PRICE_ALERT_STATE):
        try:
            with open(PRICE_ALERT_STATE) as f:
                state = json.load(f)
            if not isinstance(state, dict):
                state = {}
        except Exception:
            state = {}
    changed = False
    seen_ids = set()
    for alert in cfg["alerts"]:
        # Per-alert isolation: any error in one entry skips it, never the cycle
        try:
            if not isinstance(alert, dict):
                log(f"price alert entry not a dict — skipping: {alert!r}", "WARN")
                continue
            aid = alert.get("id")
            if not aid or not isinstance(aid, str):
                log(f"price alert entry missing string id — skipping", "WARN")
                continue
            if aid in seen_ids:
                log(f"price alert duplicate id '{aid}' — second entry skipped "
                    f"(state slots must be unique)", "WARN")
                continue
            seen_ids.add(aid)
            coin = alert.get("coin", "BTC")
            if coin != "BTC":
                continue  # only BTC priced from candles_1m for now
            # Validate level: required, numeric, positive (missing level used to
            # default to 0 → 'above' fired at any price)
            level_raw = alert.get("level")
            if level_raw is None:
                log(f"price alert {aid}: missing level — skipped", "WARN")
                continue
            level = float(level_raw)
            if level <= 0:
                log(f"price alert {aid}: level {level} not positive — skipped", "WARN")
                continue
            # Validate direction: exact match only (typos used to silently
            # become 'below')
            direction = alert.get("direction")
            if direction not in ("above", "below"):
                log(f"price alert {aid}: direction {direction!r} not "
                    f"'above'/'below' — skipped", "WARN")
                continue
            # Validate rearm: if set, must be numeric and on the CORRECT side of
            # level (above→rearm<level, below→rearm>level) — inverted rearm made
            # alerts refire every other cycle inside the band
            rearm = alert.get("rearm")
            rearm_level = None
            if rearm is not None:
                try:
                    rearm_level = float(rearm)
                except (TypeError, ValueError):
                    log(f"price alert {aid}: rearm {rearm!r} not numeric — skipped", "WARN")
                    continue
                if direction == "above" and rearm_level >= level:
                    log(f"price alert {aid}: rearm {rearm_level} must be BELOW "
                        f"level {level} for 'above' — skipped", "WARN")
                    continue
                if direction == "below" and rearm_level <= level:
                    log(f"price alert {aid}: rearm {rearm_level} must be ABOVE "
                        f"level {level} for 'below' — skipped", "WARN")
                    continue
            else:
                log(f"price alert {aid}: no rearm — will fire once, never re-arm")

            prev = state.get(aid)
            fired = bool(prev.get("fired")) if isinstance(prev, dict) else False

            if fired:
                # Already alerted — check re-arm (price returned to safe side)
                if rearm_level is not None:
                    safe = (btc_price <= rearm_level) if direction == "above" \
                        else (btc_price >= rearm_level)
                    if safe:
                        state[aid] = {"fired": False, "price": btc_price, "ts": time.time()}
                        changed = True
                        log(f"price alert {aid} re-armed (BTC {btc_price:.0f} "
                            f"back past {rearm_level:.0f})")
                continue

            crossed = (btc_price >= level) if direction == "above" \
                else (btc_price <= level)
            if crossed:
                # Guard .format(): unknown placeholders / positional {} must not
                # crash the cycle — fall back to raw string
                detail_raw = alert.get("detail") or \
                    f"BTC {btc_price:.0f} crossed {direction} {level:.0f}"
                try:
                    detail = detail_raw.format(level=level, price=btc_price)
                except (KeyError, IndexError, ValueError):
                    detail = detail_raw  # bad placeholders — show raw text
                steers.append({
                    "severity": alert.get("severity", "urgent"),
                    "category": "price-alert",
                    "title": str(alert.get("title", f"Price alert {aid}")),
                    "detail": detail,
                    "trade_id": None,
                    "auto_executable": False
                })
                state[aid] = {"fired": True, "price": btc_price, "ts": time.time()}
                changed = True
                log(f"🚨 price alert {aid} FIRED: BTC {btc_price:.0f} "
                    f"crossed {direction} {level:.0f}")
        except Exception as e:
            log(f"price alert entry error (skipped, cycle continues): {e}", "WARN")
            continue

    if changed:
        try:
            atomic_write_json(PRICE_ALERT_STATE, state)
        except Exception as e:
            log(f"price alert state write failed: {e} — alert may refire "
                f"next cycle until state persists", "WARN")
    return steers


def _load_orders_state():
    """Load the one-shot state. FAIL-CLOSED (bug_hunter F1): corrupt or
    non-dict state returns None — never {} — because an empty one-shot
    memory would re-fire EVERY already-crossed order (proven double-fire).
    Callers must abort pending processing on None."""
    state = {}
    if os.path.exists(PENDING_ORDERS_STATE):
        try:
            with open(PENDING_ORDERS_STATE) as f:
                state = json.load(f)
            if not isinstance(state, dict):
                return None
        except Exception:
            return None
    return state


# ── Cross-process one-shot lock (bug_hunter F1 CRITICAL) ───────────────────
# The state file is read-modify-written by TWO processes (pipeline
# pending_order_monitor every ~1min + trade_watchdog every ~30min).
# Unlocked, a 5ms stall double-fired 6/6 in tests, and concurrent fixed-tmp
# writes corrupted the file (→ {} → one-shot wipe → re-fire). Every
# state read→write section holds this exclusive lock; the fixed .tmp in
# atomic_write_json is then safe (serialized writers).
import fcntl
_PENDING_STATE_LOCK = PENDING_ORDERS_STATE + ".lock"


def _acquire_pending_lock():
    fd = open(_PENDING_STATE_LOCK, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except Exception:
        fd.close()
        raise
    return fd


def _release_pending_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()


# E1 fill-on-confirmed-momentum (CEO ruling 2026-11-22) — helper result
# sentinels (distinct from True/False so legacy paths stay byte-identical).
_MOM_OFF = "off"      # MOMENTUM_CONFIRM_ENABLED=False → legacy behavior, no queries
_MOM_DEFER = "defer"  # ATR/candle data missing → fail-safe defer one cycle


def _momentum_close_confirmed(close, trigger_price, direction, threshold):
    """Pure E1 predicate: is the closed 1m close displaced past the level
    by >= threshold in the break direction? LONG = break-above,
    SHORT = break-below (CEO 2026-11-22)."""
    if direction == "long":
        return bool(close >= trigger_price + threshold)
    return bool(close <= trigger_price - threshold)


def _local_atr15(coin):
    """Result-3 local ATR fallback (deep ruling 2026-11-22): atr_cache's
    only writer runs AFTER a fill, so get_atr returns None while flat —
    E1 would defer every fill forever (circular dependency = dark
    ladder). Compute ATR(15m) = mean True Range of the last 14 CLOSED
    candles_15m bars (local-data-first SOP); newest closed bar older
    than 30min (close-time) → None (stale structure = no confirmation
    basis). Any failure → None (the caller defers, never blind-fills)."""
    try:
        import sqlite3 as _sq
        _c = _sq.connect(f"file:{HERMES_DATA}/candles.db?mode=ro", uri=True)
        try:
            _cur = _c.cursor()
            _cur.execute(
                "SELECT ts, high, low, close FROM candles_15m "
                "WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT 15",
                (coin,))
            rows = _cur.fetchall()
        finally:
            _c.close()
        if not rows or len(rows) < 15:
            return None
        # freshness guard: the newest CLOSED 15m bar must have closed
        # within 30min (bar open ts + 15min)
        if (time.time() - (float(rows[0][0]) + 900.0)) > 1800.0:
            return None
        trs = []
        for i in range(14):   # rows are DESC: rows[i+1] = the prior bar
            h, l, pc = (float(rows[i][1]), float(rows[i][2]),
                        float(rows[i + 1][3]))
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        atr = sum(trs) / 14.0
        return atr if (math.isfinite(atr) and atr > 0) else None
    except Exception:
        return None


def _rip_climax_defer(coin, price):
    """RIP-CLIMAX GATES (CEO formalized 2026-11-23 after the 64,603
    wick autopsy). Returns (defer, reason): a ladder rip-fill WAITS when
    the momentum context says CLIMAX, not fresh. Three trips (any =
    defer):
      (a) the RSI divergence: the 1m RSI topped >= RIP_RSI_TOP in the
          window and has since collapsed below RIP_RSI_BELOW while the
          price sits near its window high — the momentum crashed into
          the top (the 64,500 case: the 92.6 top at 13:46, then 48.6 at
          the 14:28 fill).
      (b) the creek zone: the price within RIP_PEAK_ZONE_ATR*ATR1h BELOW
          the recent peak (the max 1h high) — the Wyckoff confirmation
          level is ahead; the entry belongs to the close above it
          (leg3), not the interior.
      (c) the continuum z-tier STRONG (|z| >= 2) — the spike context.
    The rung stays armed (no state burn): the fill waits for the
    confirmation (the close above the peak), the fresh breakout (the
    price at new highs), or the cool-off (the window ages out).
    Fail-open on any data problem — the level + precheck + R:R still
    govern every fill."""
    try:
        import hermes_constants as hc
        top = float(getattr(hc, 'RIP_RSI_TOP', 90.0) or 0)
        below = float(getattr(hc, 'RIP_RSI_BELOW', 75.0) or 0)
        win = int(getattr(hc, 'RIP_RSI_WINDOW', 180) or 180)
        zone = float(getattr(hc, 'RIP_PEAK_ZONE_ATR', 1.0) or 0)
        tier_mark = str(getattr(hc, 'RIP_Z_TIER_MARK', 'STRONG') or '')
    except Exception:
        return False, ''
    if not (top and below and zone):
        return False, ''   # REVERT (RIP_RSI_TOP=0) no-ops the gates
    try:
        import sqlite3
        from paths import HERMES_DATA
        db = os.path.join(HERMES_DATA, 'candles.db')
        con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        cur = con.cursor()
        cur.execute("SELECT close FROM candles_1m WHERE token=? "
                    "AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                    (coin, max(win, 200)))
        closes = [r[0] for r in cur.fetchall()][::-1]
        cur.execute("SELECT high, low, close FROM candles_1h WHERE token=? "
                    "AND is_closed=1 ORDER BY ts DESC LIMIT 30", (coin,))
        h1 = cur.fetchall()
        con.close()
    except Exception:
        return False, ''   # no data → fail-open
    if len(closes) < 60 or len(h1) < 5:
        return False, ''
    # (a) the RSI divergence
    g, l = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        g.append(max(0.0, d)); l.append(max(0.0, -d))
    p = 14
    if len(g) < p:
        return False, ''
    ag, al = sum(g[:p]) / p, sum(l[:p]) / p
    rsi = [100.0 - 100.0 / (1 + ag / al) if al > 0 else 100.0]
    for i in range(p, len(closes)):
        ag = (ag * (p - 1) + g[i - 1]) / p
        al = (al * (p - 1) + l[i - 1]) / p
        rsi.append(100.0 - 100.0 / (1 + ag / al) if al > 0 else 100.0)
    rmax = max(rsi[-min(win, len(rsi)):])
    rnow = rsi[-1]
    px_hi = max(closes[-min(win, len(closes)):])
    # the trip = the price in the near-high band BELOW the window high
    # (the resistance holding at the climax). The price AT/ABOVE the
    # high = the fresh breakout / the leg3 — never deferred here (the
    # test-4 case: after a >=90 top, the breakout with the RSI still
    # recovering must fill).
    if (rmax >= top and rnow < below
            and px_hi * 0.995 <= price < px_hi):
        return True, (f"RSI divergence: the 1m RSI topped {rmax:.0f} "
                      f"(>= {top:.0f}) and collapsed to {rnow:.0f} "
                      f"(< {below:.0f}) while the price {price:.0f} holds "
                      f"below the window high {px_hi:.0f}")
    # (b) the creek zone (the recent peak = the last hour's 1m closes'
    # high — the closed 1h data can't see the forming bar's wick, which
    # is how 64,603 looked at fill time; the ATR1h = the TR mean of the
    # last 14 bars)
    peak = max(closes[-60:])
    trs = []
    for i in range(1, len(h1)):
        hi, lo, pc = h1[i][0], h1[i][1], h1[i - 1][2]
        trs.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    atr = sum(trs[-14:]) / min(14, len(trs)) if trs else 0
    if atr and price < peak and (peak - price) <= zone * atr:
        return True, (f"creek zone: the price {price:.0f} is within "
                      f"{zone:g}x ATR1h ({atr:.0f}) below the recent peak "
                      f"{peak:.0f} — the confirmation level is ahead")
    # (c) the z-tier STRONG
    try:
        _wp = getattr(sys.modules.get('paths'), 'WWW_DATA',
                      '/var/www/hermes/data')
        with open(os.path.join(_wp, 'continuum_data.json')) as f:
            _tier = str((json.load(f).get('current') or {})
                        .get('zscore_tier', '') or '')
        if tier_mark and tier_mark in _tier.upper():
            return True, f"z-tier {_tier} (|z| >= 2) — the spike context"
    except Exception:
        pass
    return False, ''


def _momentum_confirm(oid, coin, direction, trigger_price, memo):
    """E1 momentum confirmation (CEO ruling 2026-11-22).

    A fill requires displacement: latest CLOSED 1m candle close beyond the
    level in the break direction by >= MOMENTUM_ATR_K x ATR(15m) for the
    coin (atr_cache.get_atr, dollars).

    Returns True (confirmed) / False (data present, not displaced) /
    _MOM_OFF (flag off → caller keeps today's behavior, NO queries) /
    _MOM_DEFER (ATR or candle data missing → caller defers one cycle,
    never blind-fills).

    Lazy: at most one query set per oid per cycle (memo), only called when
    a fill is otherwise imminent.
    """
    if oid in memo:
        return memo[oid]
    res = _MOM_DEFER
    try:
        import hermes_constants as hc
        if not getattr(hc, "MOMENTUM_CONFIRM_ENABLED", True):
            res = _MOM_OFF   # legacy path — return before any data query
        else:
            k = float(getattr(hc, "MOMENTUM_ATR_K", 0.5))
            from atr_cache import get_atr
            atr = get_atr(coin, "15m")
            if atr is None or not math.isfinite(float(atr)) or float(atr) <= 0:
                # Result-3 (deep ruling): local-data-first fallback —
                # the cache is write-after-fill, so flat = None = every
                # fill deferred (circular). Compute locally, repair the
                # shared cache (best-effort), defer only if that fails.
                atr = _local_atr15(coin)
                if atr is None:
                    res = _MOM_DEFER
                else:
                    try:
                        from atr_cache import save_atr
                        save_atr(coin, atr, "15m")
                    except Exception:
                        pass   # cache repair is best-effort, never fatal
            # res starts as _MOM_DEFER — the gate must test ATR validity
            # (from either source), not res, or the candle check never runs
            if (atr is not None and math.isfinite(float(atr))
                    and float(atr) > 0):
                # latest CLOSED 1m close — exact pattern of the fallback
                # price block above (read-only local candles DB).
                # (runs only when a valid ATR exists — cache or local)
                import sqlite3 as _sq
                _c = _sq.connect(f"file:{HERMES_DATA}/candles.db?mode=ro",
                                  uri=True)
                try:
                    _cur = _c.cursor()
                    # F-2 (agent-6): the price_collector seeder writes the
                    # CURRENT minute's candle with is_closed=1 (live: 0 rows
                    # with is_closed=0 all-time) — ts < this minute's floor
                    # guarantees only ENDED bars feed the confirmation.
                    _cur.execute("SELECT close FROM candles_1m WHERE token=? "
                                 "AND is_closed=1 AND ts < ? "
                                 "ORDER BY ts DESC LIMIT 1",
                                 (coin, int(time.time() // 60 * 60)))
                    _r = _cur.fetchone()
                finally:
                    _c.close()
                if not _r:
                    res = _MOM_DEFER
                else:
                    res = _momentum_close_confirmed(
                        float(_r[0]), trigger_price, direction,
                        k * float(atr))
    except Exception:
        res = _MOM_DEFER   # any failure = fail-safe defer, never crash
    memo[oid] = res
    return res


def monitor_pending_orders(btc_price):
    """Cross-process-locked wrapper (bug_hunter F1): the pipeline's 1-min
    caller and the watchdog's 30-min caller share this state file — the
    entire read→claim→write section runs under one exclusive flock."""
    try:
        lf = _acquire_pending_lock()
    except OSError as e:
        # LOW-1 (bug_hunter): unusable lock path must degrade like the
        # corrupt-state path (fail-closed, cycle continues) — not raise
        # into the pipeline step / whole watchdog cycle.
        log(f"pending state lock unusable — cycle skipped FAIL-CLOSED: {e}",
            "ERROR")
        return []
    try:
        return _monitor_pending_orders_impl(btc_price)
    finally:
        try:
            _release_pending_lock(lf)
        except OSError:
            pass


def _monitor_pending_orders_impl(btc_price):
    """Internal stop-limit orders: monitor trigger prices, alert + execute.

    Flow: order armed in pending_orders.json → watchdog cycle detects price
    cross → URGENT steer emitted (local alert) with action payload →
    execute_safe_actions (autopilot mode ONLY) places the trade via
    brain.py trade add — the regular path, WITHOUT --manual, so the vacation
    pause still gates execution. One-shot: fires once, never re-arms.

    Config format: {"orders": [{"id", "coin", "direction": "long"|"short",
        "trigger": "above"|"below", "trigger_price", "amount_usdt", "leverage",
        "sl", "target", "confidence", "note"}]}
    """
    steers = []
    if btc_price is None or btc_price <= 0:
        return steers
    if not os.path.exists(PENDING_ORDERS_CONFIG):
        return steers
    try:
        with open(PENDING_ORDERS_CONFIG) as f:
            cfg = json.load(f)
    except Exception as e:
        log(f"pending orders config unreadable: {e}", "WARN")
        return steers
    if not isinstance(cfg, dict) or not isinstance(cfg.get("orders"), list):
        log('pending orders config malformed: expected {"orders": [...]} — skipping', "WARN")
        return steers
    # Local price map for multi-coin orders (spin-off 2026-11-10) —
    # each order compares against its OWN coin's price.
    try:
        with open(os.path.join(HERMES_DATA, 'prices.json')) as f:
            _prices = json.load(f).get('prices', {}) or {}
    except Exception:
        _prices = {}
    state = _load_orders_state()
    if state is None:
        # F1 fail-closed: one-shot memory unreadable — firing now risks
        # re-firing every crossed order. Abort; next healthy cycle recovers.
        log("pending orders state UNREADABLE (corrupt) — skipping cycle "
            "FAIL-CLOSED until a writer repairs it", "ERROR")
        return steers
    changed = False
    # F3 (agent-2): waiting-state hygiene — first_break/retested/rejected
    # never reclaimed age out after 7d and re-qualify from scratch (the
    # CONFIG order persists; only the wait-state is dropped). one-shot
    # guards (fired/error/triggered) are NEVER pruned — double-fire
    # safety stays. 71 entries were live at audit, oldest 2026-10-18.
    # Gated on CAN_PERSIST (agent-1's call): dry-run must not reset a
    # retested rung (a non-authoritative mode deciding entries) nor
    # force changed=True (a write failure then drops that cycle's steers
    # — hiding the very steers dry-run exists to show). N1: the whole
    # prune sits in try/except — a non-numeric ts (the orphan alert
    # invites hand-edits of this file) must never kill the monitor
    # cycle (armed rungs stop firing = the original incident class).
    if PENDING_ORDERS_CAN_PERSIST:
        _now = time.time()
        # N1 refinement: the age check is PER-ENTRY — one corrupt ts
        # (the orphan alert invites hand-edits) skips that entry only,
        # never the whole prune (an all-or-nothing guard would silently
        # disable hygiene after the first bad row). Candidates are
        # materialized first: deleting from state during iteration of a
        # live view would RuntimeError.
        for _pk, _pv in [(k, v) for k, v in state.items()
                         if isinstance(v, dict)
                         and v.get("status") in ("first_break", "retested",
                                                 "rejected")]:
            try:
                if (_now - float(_pv.get("ts") or 0)) <= 7 * 86400:
                    continue
            except (TypeError, ValueError):
                log(f"waiting-state {_pk}: non-numeric ts — kept (not "
                    f"prunable)", "WARN")
                continue
            del state[_pk]
            changed = True
            log(f"pending order {_pk}: waiting-state pruned after 7d "
                f"without reclaim — re-qualifies fresh (config order "
                f"persists)")
    seen_ids = set()
    serial_claimed = False   # one serial-ladder rung fires per cycle
    _mom_memo = {}           # E1: one momentum-confirm query set per oid per cycle
    for order in cfg["orders"]:
        # Per-order isolation: a malformed entry skips itself, never the cycle
        try:
            if not isinstance(order, dict):
                log(f"pending order entry not a dict — skipping: {order!r}", "WARN")
                continue
            oid = order.get("id")
            if not oid or not isinstance(oid, str):
                log("pending order missing string id — skipped", "WARN")
                continue
            if oid in seen_ids:
                log(f"pending order duplicate id '{oid}' — second entry skipped", "WARN")
                continue
            prev = state.get(oid)
            if isinstance(prev, dict) and prev.get("status") in ("triggered", "fired", "error"):
                # One-shot: already handled. But surface ORPHANED triggers —
                # 'triggered' means the emit happened and execution never
                # completed (process died mid-cycle). No staleness recovery
                # automation: a re-fire could double-trade; the CEO decides
                # by deleting the state entry to re-arm.
                if prev.get("status") == "triggered":
                    age_min = (time.time() - float(prev.get("ts") or 0)) / 60
                    if age_min > 15:
                        steers.append({
                            "severity": "urgent",
                            "category": "pending_order",
                            "title": f"ORPHANED ORDER {oid}: triggered {age_min:.0f}min ago, never executed",
                            "detail": (f"Order {oid} triggered but no trade was placed "
                                       f"(watchdog likely died mid-cycle). Delete its entry "
                                       f"in pending_orders_state.json to re-arm it."),
                            "trade_id": None,
                            "auto_executable": False,
                        })
                continue
            coin = order.get("coin", "BTC")
            # Multi-coin support (spin-off 2026-11-10): every order is
            # monitored against ITS OWN coin's local price — never BTC's.
            px = float(_prices.get(coin) or 0)
            if px <= 0:
                # prices.json covers the dashboard universe only (HYPE — the
                # jup mirror's biggest coin — is absent): fall back to the
                # coin's latest CLOSED 1m candle (local DB, data-source rule)
                try:
                    import sqlite3 as _sq
                    _c = _sq.connect(f"file:{HERMES_DATA}/candles.db?mode=ro",
                                      uri=True)
                    _cur = _c.cursor()
                    _cur.execute("SELECT close FROM candles_1m WHERE token=? "
                                 "AND is_closed=1 ORDER BY ts DESC LIMIT 1",
                                 (coin,))
                    _r = _cur.fetchone()
                    _c.close()
                    px = float(_r[0]) if _r else 0.0
                except Exception:
                    px = 0.0
            if px <= 0:
                if coin == "BTC":
                    px = btc_price          # last-resort fallback
                else:
                    log(f"pending order {oid}: no local price for {coin} — skipped", "WARN")
                    continue
            direction = order.get("direction")
            if direction not in ("long", "short"):
                log(f"pending order {oid}: direction {direction!r} not 'long'/'short' — skipped", "WARN")
                continue
            trigger = order.get("trigger")
            if trigger not in ("above", "below"):
                log(f"pending order {oid}: trigger {trigger!r} not 'above'/'below' — skipped", "WARN")
                continue
            try:
                trigger_price = float(order.get("trigger_price"))
                sl = float(order.get("sl"))
                target = float(order.get("target"))
                amount = float(order.get("amount_usdt"))
                leverage = int(order.get("leverage", 1))
                confidence = float(order.get("confidence", 65))
            except (TypeError, ValueError):
                log(f"pending order {oid}: non-numeric price/sl/target/amount/leverage/confidence — skipped", "WARN")
                continue
            # NaN/inf pass plain >0 guards — reject explicitly (bug_hunter GAP-1)
            if not all(math.isfinite(v) for v in (trigger_price, sl, target, amount, confidence)):
                log(f"pending order {oid}: non-finite value (NaN/inf) — skipped", "WARN")
                continue
            if min(trigger_price, sl, target, amount) <= 0:
                log(f"pending order {oid}: all values must be > 0 — skipped", "WARN")
                continue
            if not (1 <= leverage <= 10):
                log(f"pending order {oid}: leverage {leverage} outside 1-10 — skipped", "WARN")
                continue
            # Shape sanity: SL on loss side of trigger, target on profit side
            if direction == "long" and not (sl < trigger_price < target):
                log(f"pending order {oid}: LONG shape wrong (need sl < trigger < target) — skipped", "WARN")
                continue
            if direction == "short" and not (target < trigger_price < sl):
                log(f"pending order {oid}: SHORT shape wrong (need target < trigger < sl) — skipped", "WARN")
                continue
            # ID claimed only after FULL validation — a malformed first copy
            # must not poison a valid duplicate (bug_hunter sideways find)
            seen_ids.add(oid)
            crossed = (px >= trigger_price) if trigger == "above" \
                else (px <= trigger_price)
            # ── MULTI-TOUCH ENTRY + NO-BURN, TWO STYLES (CEO 2026-11-20):
            # RETEST style (structure rungs — the hammered-level theory):
            #   cross#1 -> first_break (NEVER fills) -> reclaim ->
            #   retested -> cross#2 = fill (the failed-retest entry, §11).
            #   rejected (brain veto) -> reclaim -> retested (no burn).
            # CONTINUATION style (fresh-air rungs, entry_style flag):
            #   fills ON CROSS — price x0.997 is AIR, there is no prior
            #   level to reclaim, so the retest-wait starves it in a
            #   rock-fall (58736: first_break 18:45, price 58162, zero
            #   fills — CEO: 'BTC falling like a rock, make this work').
            #   #17004's sin was the arbitrary 0.6% STOP, not the fill —
            #   continuation rungs carry structure stops (conviction).
            _cont = order.get("entry_style") == "continuation"
            _st_prev = state.get(oid)
            _ps = _st_prev.get("status") if isinstance(_st_prev, dict) else None
            # F-1: per-order, before ANY branch — a rung arriving at the
            # retested hook with 'retested' state from a PRIOR cycle never
            # passes the first_break branch, so an in-branch init would
            # NameError there (caught by per-order isolation = silent
            # no-fill, which is how group-1's re-cross broke again).
            _escaped = False
            if _ps == "rejected":
                if crossed:
                    continue
                if PENDING_ORDERS_CAN_PERSIST:   # F4: dry-run never mutates
                    state[oid] = {"status": "retested", "ts": time.time(),
                                  "price": trigger_price}
                    changed = True
                log(f"pending order {oid}: rejected rung retested after "
                    f"trigger reclaim (no-burn) — armed for the re-cross")
                continue
            if _ps == "first_break" and not _cont:
                if not crossed:
                    if PENDING_ORDERS_CAN_PERSIST:   # F4
                        state[oid] = {"status": "retested", "ts": time.time(),
                                      "price": trigger_price}
                        changed = True
                    log(f"pending order {oid}: level reclaimed after first "
                        f"break — armed for the re-cross (multi-touch)")
                    # E3 BOUNCE SHADOW (deep ruling 2026-11-22 — shadow
                    # only, flip to live only with CEO approval after 7d):
                    # the poke-through never confirmed AND closed back
                    # inside the level = the level REJECTED it = the
                    # bounce candidate (the opposite side at this level).
                    # Log-only; fail-off if the constant is missing.
                    # D1 retest-fade stays parked — this is level
                    # behavior only.
                    try:
                        import hermes_constants as _hc3
                        if getattr(_hc3, "BOUNCE_SHADOW_ENABLED", False):
                            _b_side = ("LONG"
                                       if str(direction).lower() == "short"
                                       else "SHORT")
                            log(f"[BOUNCE-SHADOW] would-fill {_b_side} @ "
                                f"{trigger_price:g} (rung {direction} poke "
                                f"unconfirmed + closed back inside = "
                                f"rejection), stop beyond level, size "
                                f"{order.get('amount_usdt')} USD "
                                f"{order.get('leverage')}x", "INFO")
                    except Exception:
                        pass   # shadow must never affect the fill path
                    continue
                # STRAIGHT-LINE ESCAPE (CEO takeoff thesis 2026-11-20:
                # 'when btc takes off it will prob do so in a straight
                # line, all the way back to 70k, 80k and beyond — be
                # ready'): price ran MULTI_TOUCH_ESCAPE_PCT past the level
                # WITHOUT ever reclaiming = the retest isn't coming (the
                # rare slice the ~70% retest stat leaves out). Qualify the
                # entry (retested) and fill instead of starving — the
                # 58736-class death on a one-way move, both directions.
                # E1 MOMENTUM CONFIRM (CEO 2026-11-22): checked BEFORE the
                # escape — a displaced close qualifies to fill without the
                # full 0.5% distance. Escape keeps working exactly as today
                # with NO confirmation requirement (0.5% ≈ 3.4×ATR15 — it IS
                # displacement) and needs no data, so it still fires when
                # ATR/candle data is missing (defer → escape still checked).
                _mom = _momentum_confirm(oid, coin, direction, trigger_price,
                                         _mom_memo)
                if _mom is True:
                    _ps = "retested"   # confirmed → qualify, fall through → fill
                else:
                    try:
                        import hermes_constants as hc
                        _esc = float(hc.MULTI_TOUCH_ESCAPE_PCT)
                    except Exception:
                        _esc = 0.5
                    if ((direction == "long"
                         and px >= trigger_price * (1 + _esc / 100.0)) or
                            (direction == "short"
                             and px <= trigger_price * (1 - _esc / 100.0))):
                        log(f"pending order {oid}: STRAIGHT-LINE escape "
                            f"({_esc:.2f}% past the level, no retest) — "
                            f"qualifying to fill")
                        _ps = "retested"   # fall through below → the fill
                        # F-1 (agent-6 HIGH): the escape IS the
                        # displacement (0.5% ≈ 3.4xATR15) — Hook 2's
                        # memoized re-confirm must not block it (the memo
                        # returns the same False/DEFER the escape already
                        # routed around → 'qualifying' logged every cycle,
                        # never filled).
                        _escaped = True
                    else:
                        if _mom is _MOM_DEFER:
                            log(f"pending order {oid}: momentum confirm "
                                f"data missing — fill deferred (fail-safe)",
                                "WARN")
                        continue
            if _ps == "first_break" and _cont:
                _ps = None    # legacy continuation rung (armed pre-flag)
            if _ps == "retested":
                if not crossed:
                    continue
                # cross#2 — E1 (CEO 2026-11-22): fill only on confirmed
                # displacement. Crossed but NOT confirmed → stay retested,
                # no burn (a later confirmed close fills). Escape-qualified
                # fills skip the re-confirm (F-1: the escape already proved
                # displacement by distance).
                if not _escaped:
                    _mom = _momentum_confirm(oid, coin, direction,
                                             trigger_price, _mom_memo)
                    if _mom is False:
                        continue
                    if _mom is _MOM_DEFER:
                        log(f"pending order {oid}: momentum confirm "
                            f"data missing — fill deferred (fail-safe)",
                            "WARN")
                        continue
                # True / flag-off / escape — fall through = the fill
            elif crossed:
                _mom = _momentum_confirm(oid, coin, direction, trigger_price,
                                         _mom_memo)
                if not _cont:
                    if _mom is True:
                        pass   # E1 confirmed fresh cross → fill (the
                               # confirmation substitutes for the retest wait)
                    else:
                        # not confirmed / flag off → today's behavior exactly
                        # (first_break, no fill); data missing → defer log
                        # too (treated as not-confirmed, state still advances
                        # so the escape below stays reachable).
                        if _mom is _MOM_DEFER:
                            log(f"pending order {oid}: momentum confirm "
                                f"data missing — fill deferred (fail-safe)",
                                "WARN")
                        if PENDING_ORDERS_CAN_PERSIST:   # F4
                            state[oid] = {"status": "first_break",
                                          "ts": time.time(),
                                          "price": trigger_price}
                            changed = True
                        log(f"pending order {oid}: FIRST break seen — no fill "
                            f"(multi-touch: wait for reclaim + re-cross)")
                        continue
                else:
                    # continuation + crossed — E1: fill only on confirmed
                    # displacement. Unconfirmed → state first_break (no
                    # burn: falls back to the reclaim → re-cross path; the
                    # legacy first_break→None line above keeps it retrying).
                    if _mom is True or _mom is _MOM_OFF:
                        pass   # confirmed / legacy flag-off → fall through = fill
                    else:
                        if _mom is _MOM_DEFER:
                            log(f"pending order {oid}: momentum confirm "
                                f"data missing — fill deferred (fail-safe)",
                                "WARN")
                        else:
                            log(f"pending order {oid}: continuation cross "
                                f"unconfirmed (displacement < K×ATR) — "
                                f"falls back to retest-wait")
                        if PENDING_ORDERS_CAN_PERSIST:   # F4
                            state[oid] = {"status": "first_break",
                                          "ts": time.time(),
                                          "price": trigger_price}
                            changed = True
                        continue
                # crossed + confirmed → fall through = the fill
            if crossed and (str(oid).startswith("btc-auto-")
                            or order.get("serial") is True):
                # DIRECTION-AWARE STACKING (CEO 2026-11-21: 'if it fires
                # and another btc trade is open, will it add to the
                # position? it should, same for the long side'). The old
                # stay-until-flat guard (2026-11-10 lesson: two AUTO
                # shorts fired 1min apart → 2× exposure stopped −3.80%×2
                # on one spike) is overridden for SAME-direction adds:
                #   flat            → fire (as always)
                #   same direction  → FIRE AS ADD (the CEO add path)
                #   opposite dir    → still waits (netting would close a
                #                      live trade = violates the stay-in
                #                      doctrine; no accidental flips)
                # RIP-CLIMAX GATES (CEO formalized 2026-11-23): the
                # ladder rip-fill defers when the momentum context says
                # climax — the rung stays armed, the fill waits for the
                # confirmation (the close above the peak = leg3), the
                # fresh breakout, or the cool-off. btc-ceo hand-arms are
                # out of scope (T's explicit orders).
                if str(order.get('id', '')).startswith('btc-auto'):
                    _defer, _why = _rip_climax_defer(coin, px)
                    if _defer:
                        log(f"pending order {oid}: RIP-CLIMAX defer — "
                            f"{_why}; rung stays armed (the fill waits "
                            f"for the confirmation/cool-off)", "INFO")
                        continue
                # Throttle: serial one-rung-per-cycle below keeps adds to
                # one per cycle even on a straight slice.
                try:
                    import psycopg2
                    from _secrets import BRAIN_PASSWORD, BRAIN_HOST
                    _c = psycopg2.connect(host=BRAIN_HOST, dbname="brain",
                                          user="postgres",
                                          password=BRAIN_PASSWORD,
                                          connect_timeout=5)
                    _cur = _c.cursor()
                    # F-2 (agent-9): LIMIT 1 without ORDER BY sampled a
                    # nondeterministic leg when stacked same-direction
                    # rows exist — the gate could see a winning row and
                    # approve an add to a net-underwater stack. id ASC =
                    # the LEADING row = the original trade (the CEO's
                    # 'we are in a trade and it is winning' question).
                    _cur.execute(
                        "SELECT id, direction, pnl_pct FROM trades WHERE "
                        "token=%s AND status='open' ORDER BY id ASC "
                        "LIMIT 1", (coin,))
                    _open = _cur.fetchone()
                    # F-3 (agent-3): MAX_OPEN_POSITIONS exists but nothing
                    # read it on this path — the keeper self-replenishes
                    # rungs, so the add count was bounded only by margin.
                    # Enforce the constant as the aggregate stack cap.
                    _cur.execute(
                        "SELECT COUNT(*) FROM trades WHERE token=%s AND "
                        "status='open'", (coin,))
                    _open_count = int(_cur.fetchone()[0] or 0)
                    # D3 heat numerator (all open rows, all coins —
                    # portfolio heat, not per-coin): MARGIN basis as of
                    # 2026-11-22 — amount_usdt IS notional
                    # (hyperliquid_exchange:854), so divide by leverage.
                    # The notional form bound at ONE open position (dark
                    # ladder): heat read 0.70 vs cap 0.15 with a single
                    # 11.10×10 row → HEAT-DEFER on every fill (28×/day
                    # verified). Revert = restore SUM(amount_usdt).
                    _cur.execute(
                        "SELECT COALESCE(SUM(amount_usdt/NULLIF(leverage,0)),0) "
                        "FROM trades WHERE status='open'")
                    _heat_margin = float(_cur.fetchone()[0] or 0)
                    _cur.close()
                    _c.close()
                except Exception as _qerr:
                    # F-1 (agent-3): a DB error must NOT blind-fire. The
                    # widened --force belt turned the old fail-open (dup
                    # REJECT = safe) into a blind add / NETTING fill if
                    # brain's DB is up while ours is down. Defer one
                    # cycle instead — a 60s hiccup costs nothing.
                    log(f"pending order {oid}: open-position query "
                        f"failed ({type(_qerr).__name__}) — deferring one "
                        f"cycle (fail-safe, no blind add)", "WARN")
                    continue
                try:
                    _max_open = int(
                        __import__("hermes_constants").MAX_OPEN_POSITIONS)
                except Exception:
                    _max_open = 6
                if _open_count >= _max_open > 0:
                    log(f"pending order {oid}: {_open_count} {coin} rows "
                        f"open >= MAX_OPEN_POSITIONS({_max_open}) — add "
                        f"deferred (F-3 aggregate cap)", "INFO")
                    continue
                # D3 HEAT GATE (CEO deep-run 2026-11-21 ruling GO; formula
                # re-based to MARGIN 2026-11-22): heat = Σ open
                # (amount_usdt/leverage) / account_value — the notional form
                # bound at ONE open position (dark ladder: 0.70 vs 0.15 cap
                # with a single row), so the numerator is margin now (revert
                # = restore SUM(amount_usdt)). Cap = MAX_PORTFOLIO_HEAT (0.15
                # — unchanged, its FIRST reader). Ladder auto-fills only
                # (btc-auto-*); hand-arms bypass (the DailyFillCap-manual
                # pattern). DEFER on breach AND on any equity-read failure
                # (fail-safe — no blind add). Heat logs every evaluation for
                # calibration (the ruling's metric: calibrate the cap if it
                # binds >2×/day).
                if str(oid).startswith("btc-auto-"):
                    try:
                        from hermes_constants import MAX_PORTFOLIO_HEAT
                        from hyperliquid_exchange import get_account_value_curl
                        _eq = get_account_value_curl()
                        if isinstance(_eq, dict):
                            _eqv = float(_eq.get("account_value") or 0)
                        else:
                            _eqv = float(_eq or 0)
                        _heat = (_heat_margin / _eqv) if _eqv > 0 else None
                        log(f"pending order {oid}: heat="
                            f"{_heat if _heat is None else round(_heat, 4)} "
                            f"(margin={_heat_margin:.2f} equity={_eqv:.2f} "
                            f"cap={MAX_PORTFOLIO_HEAT}) D3 calibration", "INFO")
                        if _heat is None:
                            log(f"pending order {oid}: equity read failed — "
                                f"heat defer (fail-safe, no blind add)", "WARN")
                            continue
                        if _heat > MAX_PORTFOLIO_HEAT:
                            log(f"pending order {oid}: HEAT-DEFER heat="
                                f"{_heat:.4f} cap={MAX_PORTFOLIO_HEAT} — add "
                                f"deferred one cycle (D3)", "INFO")
                            continue
                    except Exception as _herr:
                        log(f"pending order {oid}: heat gate error "
                            f"({type(_herr).__name__}) — deferring one cycle "
                            f"(fail-safe)", "WARN")
                        continue
                if _open:
                    _open_dir = str(_open[1] or "").lower()
                    if _open_dir == str(direction or "").lower():
                        # ADD-TO-WINNERS (CEO 2026-11-23, clarified: "if
                        # we are in a trade and the trade is winning, and
                        # a rung fires — we should be adding. if a trade
                        # is losing then we shouldn't add and double
                        # down"). The open trade must be IN PROFIT
                        # (pnl_pct > 0, the open-row unleveraged
                        # price-%); underwater or unknown → defer: the
                        # rung stays armed (no state burn), fills
                        # normally once flat, or adds once green. The
                        # CEO notes the losing case is rare (a loser
                        # usually stops out before the next rung trips)
                        # — the gate is cheap and absolute.
                        try:
                            _pnl = float(_open[2] or 0)
                        except (TypeError, ValueError, IndexError):
                            _pnl = 0.0   # short/odd row = unknown → defer
                        if _pnl > 0:
                            log(f"pending order {oid}: {coin} #{_open[0]} "
                                f"{_open_dir} open and WINNING "
                                f"(pnl {_pnl:+.2f}%) — firing as ADD "
                                f"(add-to-winners, both sides)", "INFO")
                            # D2.3: the ADD carries the band flag so
                            # brain re-applies the RSI band first-entry
                            # --prearmed skips (explicit flag > implicit
                            # DB check — no race, per the ruling's
                            # evidence #8).
                            order["prearmed_add"] = True
                            # RIP-ADD EXEMPTION (CEO 2026-11-23: "as it
                            # rips through we should be adding" — the
                            # straight-up mode refuted by three band
                            # rejections at RSI 77-91 in one rip): an
                            # ESCAPE-qualified fill (0.5% straight-line =
                            # displacement proven by distance) carries
                            # band_exempt so brain skips the LONG-add
                            # RSI ceiling. The KNIFE (short <35) is never
                            # exempt — BANANA stands. Scope: the escape
                            # cycle only (_escaped is per-cycle; a later
                            # E1-only fill correctly loses the flag).
                            if _escaped:
                                order["band_exempt"] = True
                                log(f"pending order {oid}: rip-add "
                                    f"band exemption attached (escape-"
                                    f"qualified, ceiling skipped)", "INFO")
                            # fall through → steer (exec gets --force)
                        else:
                            log(f"pending order {oid}: {coin} #{_open[0]} "
                                f"{_open_dir} open NOT in profit "
                                f"(pnl {_pnl:+.2f}%) — add deferred, rung "
                                f"stays armed (no double-down on a loser)",
                                "INFO")
                            continue
                    else:
                        log(f"pending order {oid}: {coin} #{_open[0]} "
                            f"opposite {_open_dir} open — stays armed (no "
                            f"netting: stay-in doctrine)", "INFO")
                        continue
            if crossed:
                if order.get("serial") is True:
                    # ONE serial rung per cycle (ladder integrity: with all
                    # rungs crossed while flat, emission must still be
                    # sequential — else 3 rungs merge into 3x via --force).
                    # The flat-gate above sequences the REMAINING rungs
                    # across cycles (rung-after-rung as each closes).
                    if serial_claimed:
                        log(f"pending order {oid}: serial rung deferred — "
                            f"one rung per cycle", "INFO")
                        continue
                    serial_claimed = True
                note = str(order.get("note", ""))
                steers.append({
                    "severity": "urgent",
                    "category": "pending_order",
                    # :g not :.4g — 4 sig-figs rendered 81025 as '8.102e+04'
                    "title": f"PENDING ORDER {oid}: {coin} {direction.upper()} @ {trigger_price:g}",
                    "detail": (f"Trigger hit: {coin} {px:g} crossed {trigger} "
                               f"{trigger_price:g}. Executing {direction} {amount:.2f} USDT "
                               f"{leverage}x, SL {sl:g}, TP {target:g}. {note}"),
                    "trade_id": None,
                    "auto_executable": True,
                    "action": {"type": "execute_order", "order": {
                        "id": oid, "coin": coin, "direction": direction,
                        "trigger_price": trigger_price, "amount_usdt": amount,
                        "leverage": leverage, "sl": sl, "target": target,
                        "confidence": confidence,
                        "note": note,
                        # F2 (bug_hunter HIGH): the rebuilt payload DROPPED
                        # this key — the dynamic_sl bridge at the fire path
                        # never ran (live #16831 got the premature BE-LOCK).
                        # None when absent (is False check stays correct).
                        "dynamic_sl": order.get("dynamic_sl"),
                        # D2.3 (CEO deep-run 2026-11-21): the band flag —
                        # rebuilt payload must carry it or the ADD loses
                        # the gate (the F2 dropped-key class).
                        "prearmed_add": order.get("prearmed_add"),
                        "band_exempt": order.get("band_exempt"),
                        # Per-order trail profile (CEO 2026-11-09) — same
                        # bridging rule: payload carries them or they're lost.
                        "skip_be_lock": order.get("skip_be_lock"),
                        "giveback_pct": order.get("giveback_pct"),
                        "min_lock_pct": order.get("min_lock_pct"),
                    }}
                })
                if PENDING_ORDERS_CAN_PERSIST:
                    state[oid] = {"status": "triggered", "price": px, "ts": time.time()}
                    changed = True
                else:
                    # recommend/--dry-run: steer shown but order NOT burned —
                    # stays armed for autopilot
                    log(f"pending order {oid} trigger seen (recommend/dry-run — "
                        f"not persisted, order stays armed)")
        except Exception as e:
            log(f"pending order entry error (skipped, cycle continues): {e}", "WARN")
            continue
    if changed:
        try:
            atomic_write_json(PENDING_ORDERS_STATE, state)
        except Exception as e:
            # HIGH (bug_hunter): executing an unpersisted trigger = the next
            # cycle re-fires it → double trade. Drop ALL steers; the order
            # stays armed and fires cleanly once state writes work again.
            log(f"pending order state write failed: {e} — dropping "
                f"{len(steers)} steer(s) to prevent double execution", "ERROR")
            return []
    return steers


def _execute_pending_order(order):
    """Cross-process-locked wrapper (bug_hunter F1): claim→fire state
    transitions from both the pipeline and watchdog callers serialize on
    the same flock as the monitor."""
    oid = order.get("id", "?") if isinstance(order, dict) else "?"
    try:
        lf = _acquire_pending_lock()
    except OSError as e:
        # LOW-1: degrade fail-closed, never raise into the cycle
        log(f"AUTO-EXEC {oid}: lock unusable — refusing to trade FAIL-CLOSED: {e}",
            "ERROR")
        return {"type": "pending_order", "order_id": oid,
                "auto_executed": False,
                "hl_result": f"error: lock unusable ({e})"}
    try:
        return _execute_pending_order_impl(order)
    finally:
        try:
            _release_pending_lock(lf)
        except OSError:
            pass


def _execute_pending_order_impl(order):
    """Place a triggered pending order via brain.py trade add — the regular
    execution path WITHOUT --manual, so vacation pause / kill switch still gate.

    One-shot: state marked fired on success, error on failure (no auto-retry —
    double-fire risk; CEO re-arms explicitly)."""
    import subprocess
    import re as _re
    oid = order.get("id", "?")
    # F1 claim recheck (runs under the wrapper's flock): refuse to trade if
    # the one-shot memory is unreadable (fail-closed) or already consumed —
    # this is the belt to the monitor's suspenders against double-fire.
    _pre_state = _load_orders_state()
    if _pre_state is None:
        log(f"AUTO-EXEC {oid}: state unreadable (corrupt) — refusing to "
            f"trade FAIL-CLOSED", "ERROR")
        return {"type": "pending_order", "order_id": oid,
                "auto_executed": False,
                "hl_result": "error: one-shot state corrupt"}
    _prev = _pre_state.get(oid)
    if isinstance(_prev, dict) and _prev.get("status") in (
            "fired", "error", "rejected", "first_break", "retested"):
        log(f"AUTO-EXEC {oid}: already {_prev.get('status')} — one-shot "
            f"re-entry refused", "WARN")
        return {"type": "pending_order", "order_id": oid,
                "auto_executed": False,
                "hl_result": f"skipped: already {_prev.get('status')}"}
    state = _pre_state                    # same lock hold → use for the write
    try:
        # Cmd build INSIDE try — a KeyError on a bad payload must mark the
        # order error, not escape to the caller (bug_hunter LOW).
        # --force scope (2026-11-10 narrow → 2026-11-21 re-widened for
        # ladder ADDS): btc-ceo-* (CEO tranches) AND btc-auto-ladder-*
        # (the CEO add directive: 'if it fires and another btc trade is
        # open, it should add — same for the long side') get it, so
        # brain's dup-guard permits the same-direction second tranche.
        # The 2026-11-10 lesson (two auto shorts 1min apart → −3.80%×2)
        # is handled by the monitor's DIRECTION-AWARE gate above (flat /
        # same-direction add / opposite waits) + serial one-rung-per-
        # cycle — not by refusing the add. One-shot state + orphan
        # steer-only recovery still prevent double-fires; vacation/
        # kill-switch unaffected (--manual still NOT passed).
        # ponytail: direction re-check not repeated here — the steer is
        # emitted and executed within one pipeline step (seconds); a
        # position flip inside that window would net instead of add
        # (bounded: one rung size). Upgrade path: exec-side direction
        # assert if flips ever show in the log.
        # TAG-SPLIT (CEO Phase1 item3, disposition ai-trader-pending-tag-split
        # due 2026-11-24, shipped early by brain_auditor #293): btc-auto-ladder-*
        # fills tag ai-trader-auto so the auto cohort is judged separately from
        # CEO-armed btc-ceo-*/manual pendings (gate ONLY auto if <40% WR n>=30).
        # Consumers already expect the tag: auto_trader live_attribution
        # (LIKE 'ai-trader-auto%'), manual_exit_manager MANAGED_TAGS, position_manager.
        # --force scope and --prearmed behavior unchanged (id-based, not tag-based).
        _sig = ("ai-trader-auto"
                if str(order.get("id", "")).startswith("btc-auto-")
                else "ai-trader-pending")
        cmd = [
            sys.executable, os.path.join(SCRIPTS_DIR, "brain.py"),
            "trade", "add",
            str(order["coin"]), str(order["direction"]),
            f'{float(order["amount_usdt"]):.2f}', f'{float(order["trigger_price"]):.8g}',
            "--real",
            "--signal", _sig,
            "--strategy", "ai-trader",
            "--confidence", f'{float(order.get("confidence", 65)):.0f}',
            "--leverage", str(int(order["leverage"])),
            "--sl", f'{float(order["sl"]):.8g}',
            "--target", f'{float(order["target"]):.8g}',
        ]
        if str(order.get("id", "")).startswith(("btc-ceo-",
                                                "btc-auto-ladder-")):
            cmd.append("--force")
        # ALL pending orders are pre-armed structure levels (CEO 2026-11-20:
        # 'we need to catch these shorts' — the knife/floor RSI gates veto
        # every rung in a knife; the rung's own SL + serial/stacking +
        # kill-switch remain the risk controls). brain skips ONLY those
        # two RSI gates for --prearmed.
        cmd.append("--prearmed")
        if order.get("prearmed_add"):
            cmd.append("--prearmed-add")
        if order.get("band_exempt"):
            cmd.append("--band-exempt")   # rip-add: skip the ceiling only
        log(f"AUTO-EXEC pending order {oid}: {' '.join(cmd[4:])}")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                           cwd=SCRIPTS_DIR)
        out = (r.stdout or "") + (r.stderr or "")
        success = r.returncode == 0 and "✓ Added trade" in out
        trade_ref = None
        m = _re.search(r"trade #(\d+)", out)
        if m:
            trade_ref = f"#{m.group(1)}"
        # Update state: fired / rejected / error.
        # no-burn (CEO 2026-11-20 — five rungs burned through the 61500
        # break: 62017/62003/61700/61367/61212 all REJECTED by BANANA
        # knife-35/HARD_FLOOR-45 and consumed as terminal 'error'):
        # brain's explicit REJECTED = the entry gate vetoed and NOTHING
        # opened — that is not an execution failure. Status 'rejected'
        # keeps the rung alive; the monitor re-arms it once price
        # reclaims the trigger (the §11 re-cross with RSI recovered).
        # Taxonomy (F6a, intended scope): ALL pre-open brain rejections
        # — RSI knife/floor, blacklist, vacation/live-trading, delisted,
        # HL_MIN, DUPLICATE, STALE ORPHAN (F6b now carries the marker) —
        # are retryable 'rejected': rejection != failure, and each retries
        # only after a level reclaim (throttled by construction). Only
        # non-marker failures (timeout, API error, tracebacks) stay
        # terminal 'error' — no double-fire (open requires rc==0 + the
        # added-trade line; verified unreachable-by-marker).
        # Reuses `state` loaded at claim time — same lock hold, no reload
        # (F1: interleaved reloads were the race window).
        # F1 (agent-2): bare 'REJECTED' in out is demonstrably broad —
        # mirror_open FAILED-lines, tracebacks quoting a brain REJECTED
        # source line, and incidental warnings all matched. Exact marker:
        # only brain's own gate lines make a rejection retryable.
        _rejected = any(ln.startswith("[brain.py] \u274c REJECTED")
                        for ln in out.splitlines())
        state[oid] = {
            "status": ("fired" if success
                       else ("rejected" if _rejected else "error")),
            "price": order.get("trigger_price"),
            "ts": time.time(),
            "trade": trade_ref,
            "output_tail": out[-400:],
        }
        # Structure-fixed stop (CEO directive 2026-11-09, #16827 lesson):
        # orders armed with "dynamic_sl": false hand SL authority to the
        # watchdog full-analysis tweak (stop stays above break-of-structure
        # so retests don't kick the trade out before the real leg) — the
        # BE/trail stack skips these trades entirely. Flag must live in
        # manual_exit_manager's state too (keyed by TRADE id, not order id).
        # Trail-profile bridge (CEO 2026-11-09): order-config keys cross into
        # manual_exit_manager's state (keyed by TRADE id — its file is keyed
        # differently than this order-id state). dynamic_sl:false = structure-
        # fixed (watchdog tweak owns the SL); skip_be_lock/giveback_pct/
        # min_lock_pct = custom trail profile (retest-surviving riders).
        _profile = {k: order.get(k) for k in
                    ("dynamic_sl", "skip_be_lock", "giveback_pct", "min_lock_pct")
                    if order.get(k) is not None}
        if "dynamic_sl" in _profile:
            state[oid]["dynamic_sl"] = order.get("dynamic_sl")
        if _profile and trade_ref and trade_ref.lstrip('#').isdigit():
            try:
                import manual_exit_manager as _mxm_flag
                _mstate = _mxm_flag._load_state()
                _entry = _mstate.get(trade_ref.lstrip('#')) or {}
                _entry.update(_profile)
                _entry['ts'] = time.time()
                _mstate[trade_ref.lstrip('#')] = _entry
                _mxm_flag._save_state(_mstate)
                log(f"AUTO-EXEC {oid}: trail profile bridged {list(_profile)}")
            except Exception as _e:
                log(f"AUTO-EXEC {oid}: trail-profile bridge failed: {_e}",
                    "WARN")
        atomic_write_json(PENDING_ORDERS_STATE, state)
        if success:
            log(f"AUTO-EXEC pending order {oid} ✅ opened {trade_ref}", "INFO")
        else:
            log(f"AUTO-EXEC pending order {oid} ❌ FAILED (rc={r.returncode}): "
                f"{out[-300:]}", "ERROR")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "pending_order",
            "order_id": oid,
            "coin": order.get("coin"),
            "direction": order.get("direction"),
            "trigger_price": order.get("trigger_price"),
            "trade": trade_ref,
            "reason": order.get("note", ""),
            "auto_executed": success,
            "hl_result": "success" if success else f"failed rc={r.returncode}",
        }
    except Exception as e:
        log(f"AUTO-EXEC pending order {oid} exception: {e}", "ERROR")
        try:
            if state is not None:          # claim-time load, same lock hold
                state[oid] = {"status": "error", "ts": time.time(), "error": str(e)}
                atomic_write_json(PENDING_ORDERS_STATE, state)
        except Exception:
            pass
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "pending_order",
            "order_id": oid,
            "auto_executed": False,
            "hl_result": f"exception: {e}",
        }


def collect_all():
    """Collect all data sources."""
    log("=== Data Collection ===")
    db_ok = True

    open_trades = collect_open_trades()
    # If DB returned nothing AND we can connect, there are genuinely no open trades
    # If DB returned nothing because connection failed, flag it
    if not open_trades:
        conn = get_db()
        if conn is None:
            db_ok = False
        else:
            conn.close()

    recent_closed = collect_recent_closed(20)
    signal_performance = collect_signal_performance()

    data = {
        "timestamp": now.isoformat(),
        "db_healthy": db_ok,
        "open_trades": open_trades,
        "recent_closed": recent_closed,
        "btc_regime": collect_btc_regime(),
        "btc_price": collect_btc_price(),
        "coin_tracker": collect_coin_tracker(),
        "pipeline_status": collect_pipeline_status(),
        "signal_performance": signal_performance,
        "exposure": collect_exposure(24),
    }
    if not db_ok:
        log("⚠ PostgreSQL unreachable — data may be incomplete", "ERROR")
    log(f"Collection complete: {len(data['open_trades'])} open, "
        f"{len(data['recent_closed'])} recent, "
        f"{len(data['signal_performance'])} signals")
    return data


def analyze_all(data):
    """Run all analysis engines."""
    log("=== Analysis ===")
    steers = []

    steers.extend(analyze_regime_alignment(data["open_trades"], data["btc_regime"]))
    steers.extend(analyze_price_alerts(data.get("btc_price")))
    steers.extend(monitor_pending_orders(data.get("btc_price")))
    steers.extend(analyze_profit_lock(data["open_trades"]))
    steers.extend(analyze_stale_trades(data["open_trades"]))
    steers.extend(analyze_trade_clusters(data["open_trades"]))
    steers.extend(analyze_recent_losses(data["recent_closed"]))
    steers.extend(analyze_signal_quality(data["signal_performance"], data["btc_regime"]))
    steers.extend(analyze_coin_heat(data["open_trades"], data["coin_tracker"]))

    # Sort by severity
    severity_order = {"urgent": 0, "warning": 1, "info": 2}
    steers.sort(key=lambda s: severity_order.get(s.get("severity", "info"), 3))

    # Add IDs
    for i, s in enumerate(steers):
        s["id"] = f"steer-{i+1:03d}"

    log(f"Analysis complete: {len(steers)} steers "
        f"({sum(1 for s in steers if s['severity']=='urgent')} urgent, "
        f"{sum(1 for s in steers if s['severity']=='warning')} warning, "
        f"{sum(1 for s in steers if s['severity']=='info')} info)")

    return steers


def build_output(data, steers):
    """Build the final output JSON."""
    # Portfolio summary
    open_trades = data["open_trades"]
    total_unrealized = sum(float(t.get("pnl_usdt") or 0) for t in open_trades)
    long_count = sum(1 for t in open_trades if (t.get("direction") or "").lower() == "long")
    short_count = sum(1 for t in open_trades if (t.get("direction") or "").lower() == "short")

    # Portfolio health score
    urgent_count = sum(1 for s in steers if s["severity"] == "urgent")
    warning_count = sum(1 for s in steers if s["severity"] == "warning")

    if urgent_count > 0:
        health = "critical"
    elif warning_count >= 3:
        health = "warning"
    else:
        health = "good"

    btc = data["btc_regime"]

    # DB error state: if DB is down, force health to "error"
    if not data.get("db_healthy", True):
        health = "error"
        steers.insert(0, {
            "severity": "urgent",
            "category": "health",
            "title": "PostgreSQL unreachable — data may be stale",
            "detail": "Cannot read open trades or recent performance. "
                      "Dashboard may show outdated information.",
            "auto_executable": False,
            "id": "steer-000"
        })

    output = {
        "timestamp": now.isoformat(),
        "mode": "recommend",  # Updated in main() with actual mode
        "portfolio_health": health,
        "db_healthy": data.get("db_healthy", True),
        "open_trades": [],
        "steers": steers,
        "regime_summary": {k: v for k, v in btc.items() if v is not None},
        "portfolio_summary": {
            "total_open": len(open_trades),
            "total_unrealized_pnl": round(total_unrealized, 2),
            "long_count": long_count,
            "short_count": short_count,
        },
        "signal_performance": data.get("signal_performance", {}),
        "exposure": data.get("exposure"),
        "pipeline_status": data.get("pipeline_status", {}),
        # DRIFT-E-safe recent closes for the deep-analysis agent — use meta_rsi,
        # NOT trades.entry_rsi_14 (late/wrong-TF, median |diff| ~13 pts).
        "recent_closed": [
            {
                "id": t.get("id"),
                "coin": t.get("coin"),
                "direction": t.get("direction"),
                "signal": t.get("signal_name"),
                "pnl_usdt": t.get("pnl_usdt"),
                "pnl_pct": t.get("pnl_pct"),
                "meta_rsi": t.get("meta_rsi"),
                "volatility_regime": t.get("volatility_regime"),
                "leverage": t.get("leverage"),
            }
            for t in (data.get("recent_closed") or [])[:20]
        ],
    }

    # Enrich open trades with computed fields
    for trade in open_trades:
        entry = float(trade.get("entry_price") or 0)
        current = float(trade.get("current_price") or entry)
        direction = (trade.get("direction") or "").lower()

        if entry > 0 and current > 0:
            if direction == "long":
                pnl_pct = ((current - entry) / entry) * 100
            else:
                pnl_pct = ((entry - current) / entry) * 100
        else:
            pnl_pct = 0

        entry_time = trade.get("entry_time")
        hours_open = None
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                except:
                    pass
            if isinstance(entry_time, datetime):
                # Make naive datetimes timezone-aware (assume UTC)
                if entry_time.tzinfo is None:
                    entry_time = entry_time.replace(tzinfo=timezone.utc)
                hours_open = round((now - entry_time).total_seconds() / 3600, 1)

        output["open_trades"].append({
            "id": trade.get("id"),
            "coin": trade.get("coin"),
            "direction": direction,
            "entry_price": entry,
            "current_price": current,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_usdt": round(float(trade.get("pnl_usdt") or 0), 2),
            "hours_open": hours_open,
            "signal": trade.get("signal_name"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit"),
            "leverage": trade.get("leverage"),
            "meta_rsi": trade.get("meta_rsi"),
        })

    return output


def write_outputs(output, steers, dry_run=False):
    """Write output files."""
    if dry_run:
        log("Dry run — not writing outputs")
        print(json.dumps(output, indent=2, default=default_serial))
        return

    # Write main output
    os.makedirs(os.path.dirname(STEER_OUTPUT), exist_ok=True)
    atomic_write_json(STEER_OUTPUT, output)
    log(f"Wrote {STEER_OUTPUT}")

    # Write recommendations (for opencode agent to pick up)
    # Preserve any deep_analysis the agent wrote in previous run
    existing_recs = {}
    if os.path.exists(RECOMMEND_OUTPUT):
        try:
            with open(RECOMMEND_OUTPUT) as f:
                existing_recs = json.load(f)
        except Exception:
            pass

    recs = {
        "timestamp": now.isoformat(),
        "steers": steers,
        "portfolio_health": output["portfolio_health"],
        "regime": output["regime_summary"],
        "open_count": len(output["open_trades"]),
    }
    # Carry forward agent's analysis if it exists and is less than 1 hour old
    if existing_recs.get("deep_analysis") and existing_recs.get("agent_timestamp"):
        try:
            agent_ts = datetime.fromisoformat(existing_recs["agent_timestamp"].replace("Z", "+00:00"))
            if agent_ts.tzinfo is None:
                agent_ts = agent_ts.replace(tzinfo=timezone.utc)
            age_min = (datetime.now(timezone.utc) - agent_ts).total_seconds() / 60
            if age_min < 60:
                recs["deep_analysis"] = existing_recs["deep_analysis"]
                recs["agent_timestamp"] = existing_recs["agent_timestamp"]
                recs["regime_context"] = existing_recs.get("regime_context", "")
                recs["pattern_alerts"] = existing_recs.get("pattern_alerts", "")
                log(f"Preserved agent analysis from {age_min:.0f} min ago")
        except Exception:
            pass

    os.makedirs(os.path.dirname(RECOMMEND_OUTPUT), exist_ok=True)
    atomic_write_json(RECOMMEND_OUTPUT, recs)
    log(f"Wrote {RECOMMEND_OUTPUT}")

    # Append to actions log (if any auto-executed)
    auto_actions = [s for s in steers if s.get("action") and s.get("auto_executable")]
    if auto_actions:
        actions = []
        if os.path.exists(ACTIONS_LOG):
            try:
                with open(ACTIONS_LOG) as f:
                    existing = json.load(f)
                    actions = existing.get("actions", [])[-100:]  # Keep last 100
            except:
                pass

        for s in auto_actions:
            action = s.get("action", {})
            action["timestamp"] = now.isoformat()
            action["reason"] = s.get("detail", "")
            action["auto_executed"] = bool(s.get("auto_executable"))
            actions.append(action)

        atomic_write_json(ACTIONS_LOG, {"actions": actions})
        log(f"Logged {len(auto_actions)} actions to {ACTIONS_LOG}")


def execute_safe_actions(steers, watchdog_mode):
    """Execute auto-executable steers (profit locks only in autopilot mode)."""
    if watchdog_mode != "autopilot":
        return []

    executed = []
    for steer in steers:
        if not steer.get("auto_executable"):
            continue
        if steer.get("category") not in AUTO_EXECUTABLE_CATEGORIES:
            continue

        action = steer.get("action", {})
        if not action:
            continue

        action_type = action.get("type")
        symbol = action.get("symbol")
        new_stop = action.get("new_stop")
        trade_id = steer.get("trade_id")

        if action_type == "move_stop" and symbol and new_stop:
            # CEO trades: manual_exit_manager owns their stops. Moving the HL
            # stop here without the DB counterpart (adjust_stop_loss is
            # paper=TRUE only) = DB/exchange divergence + a third actor on a
            # CEO stop (bug_hunter 2026-10-22 #3). Skip managed signals.
            _skip_ceo_stop = False
            _skip_xmirror = False
            _skip_reason = ''
            if not trade_id:
                # FIX (bug_hunter LOW 5): a steer without trade_id bypassed
                # the entire verification guard and moved HL stops blind —
                # the one remaining fail-open. Can't verify the trade →
                # don't act on it.
                _skip_xmirror = True
                _skip_reason = 'no trade_id — cannot verify trade'
            if trade_id:
                try:
                    import manual_exit_manager as _mxmw
                    _conn_ms = get_db()
                    if not _conn_ms:
                        # FIX (bug_hunter round-5 MED-LOW): get_db() SWALLOWS
                        # connect errors and returns None — the old
                        # `if _conn_ms:` silently skipped verification, letting
                        # the steer proceed to replace_sl BLIND during a PG
                        # outage (their harness F1: replace_sl called 1x).
                        # Raise → routes to the existing fail-closed except
                        # (reason 'verify failed (DB error)').
                        raise RuntimeError('get_db() returned None — PG unreachable')
                    if _conn_ms:
                        _cur_ms = _conn_ms.cursor()
                        _cur_ms.execute("SELECT signal, _signal_metadata FROM trades WHERE id=%s", (trade_id,))
                        _row_ms = _cur_ms.fetchone()
                        _cur_ms.close()
                        _conn_ms.close()
                        if _row_ms and _mxmw.is_managed_signal(_row_ms[0]):
                            _skip_ceo_stop = True
                        # T1 EXACT MIRROR (bug_hunter MED): autopilot must not
                        # place HL stops on a trade whose pro exit governs —
                        # the mirror guard NULLs levels, which made the +2%
                        # breakeven branch fire MORE often (current_sl==0).
                        if _row_ms:
                            try:
                                from trust_tiers import is_exact_mirror_trade as _tw_ixm
                                if _tw_ixm({'signal': _row_ms[0],
                                            '_signal_metadata': _row_ms[1]}):
                                    _skip_xmirror = True
                                    _skip_reason = ("T1 exact mirror — pro exit governs")
                            except Exception:
                                # can't verify tier → don't act on HL (fail-closed)
                                _skip_xmirror = True
                                _skip_reason = 'tier unverifiable (verify error)'
                        else:
                            # no row → can't rule out an exact-mirror trade
                            _skip_xmirror = True
                            _skip_reason = 'trade row missing (cannot verify)'
                except Exception:
                    # DB/verify failure: fail-CLOSED — acting blind with HL
                    # stops is worse than skipping one adjustment (bug_hunter
                    # round-3 LOW: old fail-open could stop a mirror trade)
                    _skip_xmirror = True
                    _skip_reason = 'verify failed (DB error)'
            # FIX (bug_hunter LOW 6): attribution — the CEO branch wins when
            # BOTH flags are set (previously a CEO skip was logged/audited as
            # 'T1 exact mirror'). Outcomes are identical skips; labels now
            # match reality via the precise _skip_reason.
            if not _skip_ceo_stop and _skip_xmirror:
                log(f"AUTO-EXEC: SKIP {symbol} stop move — {_skip_reason}", "INFO")
                executed.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "move_stop",
                    "symbol": symbol,
                    "new_stop": new_stop,
                    "reason": f"skipped: {_skip_reason}",
                    "auto_executed": False,
                    "hl_result": "skipped"
                })
                continue
            if _skip_ceo_stop:
                log(f"AUTO-EXEC: SKIP {symbol} stop move — CEO trade "
                    f"(manual_exit_manager owns its stop)", "INFO")
                executed.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "move_stop",
                    "symbol": symbol,
                    "new_stop": new_stop,
                    "reason": "skipped: CEO trade, manual exit system owns stop",
                    "auto_executed": False,
                    "hl_result": "skipped"
                })
                continue
            log(f"AUTO-EXEC: Moving {symbol} stop to {new_stop} — {steer.get('detail', '')}")
            try:
                # FIX (BUG-042, 2026-10-08): HL FIRST, DB only on HL success. The old
                # order wrote the brain DB unconditionally BEFORE the HL attempt and
                # never rolled back — every failed HL move left DB and exchange stops
                # diverging (live evidence: CRV 2026-10-08 00:49 & 01:19 both failed
                # with float(None) while the DB had already been updated).
                from hyperliquid_exchange import replace_sl
                direction = action.get("direction", "long")
                result = replace_sl(symbol, direction, float(new_stop))

                if result.get("success"):
                    # DB write AFTER confirmed HL success
                    sys.path.insert(0, SCRIPTS_DIR)
                    from position_manager import adjust_stop_loss
                    if trade_id:
                        adjust_stop_loss(trade_id, new_stop)
                    log(f"AUTO-EXEC: {symbol} stop moved to {new_stop} ✅")
                    executed.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "move_stop",
                        "symbol": symbol,
                        "direction": direction,
                        "new_stop": new_stop,
                        "reason": steer.get("detail", ""),
                        "auto_executed": True,
                        "hl_result": "success"
                    })
                else:
                    err = result.get("error", "unknown")
                    log(f"AUTO-EXEC: {symbol} stop move FAILED: {err} ❌", "ERROR")
                    executed.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "type": "move_stop",
                        "symbol": symbol,
                        "new_stop": new_stop,
                        "reason": steer.get("detail", ""),
                        "auto_executed": False,
                        "hl_result": f"failed: {err}"
                    })
            except Exception as e:
                log(f"AUTO-EXEC: {symbol} error: {e}", "ERROR")
                executed.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "move_stop",
                    "symbol": symbol,
                    "new_stop": new_stop,
                    "reason": steer.get("detail", ""),
                    "auto_executed": False,
                    "hl_result": f"error: {e}"
                })

        elif action_type == "execute_order" and action.get("order"):
            # Pending (conditional) entry — trigger hit, place via brain.py.
            # try/except mirrors move_stop: one bad payload must not abort
            # remaining auto-executions in the batch (bug_hunter LOW).
            try:
                result = _execute_pending_order(action["order"])
                if result:
                    executed.append(result)
            except Exception as e:
                log(f"AUTO-EXEC pending_order error: {e}", "ERROR")
                executed.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "pending_order",
                    "order_id": action["order"].get("id", "?"),
                    "auto_executed": False,
                    "hl_result": f"error: {e}",
                })

    return executed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Trade Watchdog")
    parser.add_argument("--collect", action="store_true", help="Collect data only")
    parser.add_argument("--analyze", action="store_true", help="Analyze only (requires collected data)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze but don't write outputs")
    parser.add_argument("--selfcheck", action="store_true",
                        help="Run interval-merge + streak-advice self-checks and exit (no DB, no writes)")
    args = parser.parse_args()

    if args.selfcheck:
        t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        def h(x):
            return t0 + timedelta(hours=x)
        # overlap merges to one 4h block from 0..4
        m = _merge_intervals([(h(0), h(2)), (h(1), h(4))])
        assert m == [(h(0), h(4))], m
        # disjoint stay separate, covered = 2h of 6h window
        m = _merge_intervals([(h(0), h(1)), (h(3), h(4))])
        assert len(m) == 2 and sum((e - s).total_seconds() for s, e in m) == 7200, m
        # empty / zero-length inputs
        assert _merge_intervals([]) == []
        assert _merge_intervals([(h(2), h(2))]) == []
        # abutting intervals (s == prev end) merge — one continuous block
        assert _merge_intervals([(h(0), h(1)), (h(1), h(2))]) == [(h(0), h(2))]
        print("selfcheck PASS: 5 interval-merge cases")
        _selfcheck_streak_advice()
        return

    # Determine mode (recommend → autopilot after 48h)
    watchdog_mode, deploy_time, elapsed_hrs = get_watchdog_mode()
    remaining = max(0, AUTOPILOT_DELAY_HOURS - elapsed_hrs)
    log(f"Trade Watchdog starting... mode={watchdog_mode} "
        f"(deployed {elapsed_hrs:.1f}h ago, autopilot in {remaining:.1f}h)")

    data = collect_all()

    if args.collect:
        # Save raw data for later analysis
        raw_path = os.path.join(DATA_DIR, "watchdog_raw.json")
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        log(f"Saved raw data to {raw_path}")
        return

    # Pending orders: only persist one-shot state when execution can actually
    # follow (autopilot, not dry-run) — recommend/dry-run must not burn orders
    global PENDING_ORDERS_CAN_PERSIST
    PENDING_ORDERS_CAN_PERSIST = (watchdog_mode == "autopilot" and not args.dry_run)

    steers = analyze_all(data)

    # Autonomous BTC loop (spec v2, phase 0): shadow cycle journals decisions
    # + tracks hypotheticals — zero live effect. Never breaks the watchdog:
    # any failure logs and continues.
    auto_trader_summary = None
    try:
        from auto_trader import run_cycle as _auto_run_cycle
        auto_trader_summary = _auto_run_cycle()
    except Exception as e:
        log(f"auto_trader cycle failed (watchdog continues): {e}", "WARN")

    output = build_output(data, steers)
    if auto_trader_summary is not None:
        output["auto_trader"] = auto_trader_summary
    output["mode"] = watchdog_mode
    output["deploy_time"] = deploy_time.isoformat()
    output["autopilot_in_hours"] = round(remaining, 1)
    write_outputs(output, steers, dry_run=args.dry_run)

    # Execute safe actions if in autopilot mode
    executed = []
    if watchdog_mode == "autopilot" and not args.dry_run:
        log("=== Auto-Executing Safe Actions ===")
        executed = execute_safe_actions(steers, watchdog_mode)
        if executed:
            # Append to actions log
            existing_actions = []
            if os.path.exists(ACTIONS_LOG):
                try:
                    with open(ACTIONS_LOG) as f:
                        existing_actions = json.load(f).get("actions", [])[-100:]
                except Exception:
                    pass
            existing_actions.extend(executed)
            atomic_write_json(ACTIONS_LOG, {"actions": existing_actions})
            log(f"Executed {len(executed)} actions")

    # Summary
    print("\n" + "=" * 60)
    print(f"Trade Watchdog — {output['portfolio_health'].upper()} [{watchdog_mode.upper()}]")
    print(f"Open: {len(output['open_trades'])} trades | "
          f"Unrealized: {output['portfolio_summary']['total_unrealized_pnl']:+.2f} USDT")
    print(f"Steers: {len(steers)} "
          f"({sum(1 for s in steers if s['severity']=='urgent')} urgent)")
    if executed:
        print(f"Auto-executed: {len(executed)} actions")
    if watchdog_mode == "recommend":
        print(f"⏰ Autopilot in {remaining:.1f} hours")
    print("=" * 60)

    for steer in steers:
        icon = {"urgent": "🔴", "warning": "🟡", "info": "🟢"}.get(steer["severity"], "⚪")
        print(f"  {icon} [{steer['category']}] {steer['title']}")

    print("=" * 60)


def _selfcheck_streak_advice():
    """Fixtures for the prearm_lock streak-advice branch (brain_auditor #288).

    Run: python3 scripts/trade_watchdog.py --selfcheck
    Mutation guards: (d) kills a 'pl >= len (100% prearm)' regression,
    (e) kills counting reasons OUTSIDE the trailing-streak walk.
    """
    import inspect

    # LOW-1 guard: the SELECT must carry exit_reason or live degrades to "?"
    assert "exit_reason" in inspect.getsource(collect_recent_closed)
    # #289: steer-001 composition needs mfe_pct or the chop/giveback branches
    # silently degrade to "Something is wrong"
    assert "mfe_pct" in inspect.getsource(collect_recent_closed)

    def _t(sig, pnl, reason, mfe=None):
        return {"signal_name": sig, "pnl_usdt": pnl, "pnl_pct": pnl, "exit_reason": reason,
                "amount_usdt": 10.0, "leverage": 5, "mfe_pct": mfe}

    # (a) all-prearm streak -> guard note, no disable advice
    prearm = [_t("pump-chain+", -0.01, "prearm_lock") for _ in range(4)]
    prearm.append(_t("other-sig", +0.05, "profit-monster-trail"))
    steers = analyze_recent_losses(prearm)
    sig = [s for s in steers if s["title"].startswith("Signal 'pump-chain+'")]
    assert len(sig) == 1, sig
    assert "prearm_lock breakeven caps" in sig[0]["detail"], sig[0]["detail"]
    assert "Consider disabling" not in sig[0]["detail"], sig[0]["detail"]

    # (b) real stop-loss streak -> original disable advice kept
    stops = [_t("r2v2-long3", -0.10, "hard_max_loss") for _ in range(4)]
    stops.append(_t("other-sig", +0.05, "profit-monster-trail"))
    steers = analyze_recent_losses(stops)
    sig = [s for s in steers if s["title"].startswith("Signal 'r2v2-long3'")]
    assert len(sig) == 1, sig
    assert "Consider disabling or tuning this signal." in sig[0]["detail"], sig[0]["detail"]
    assert "prearm_lock" not in sig[0]["detail"], sig[0]["detail"]

    # (c) mixed streak, minority prearm -> disable advice kept
    mixed = [_t("atr-trend+", -0.08, "atr_sl_hit"),
             _t("atr-trend+", -0.09, "atr_sl_hit"),
             _t("atr-trend+", -0.01, "prearm_lock"),
             _t("other-sig", +0.05, "profit-monster-trail")]
    steers = analyze_recent_losses(mixed)
    sig = [s for s in steers if s["title"].startswith("Signal 'atr-trend+'")]
    assert len(sig) == 1, sig
    assert "Consider disabling" in sig[0]["detail"], sig[0]["detail"]

    # (d) MAJORITY not all: 3 prearm + 1 stop -> guard note (a 100%-prearm
    #     threshold mutation must fail here)
    maj = [_t("bb-squeeze+", -0.01, "prearm_lock"),
           _t("bb-squeeze+", -0.01, "prearm_lock"),
           _t("bb-squeeze+", -0.02, "prearm_lock"),
           _t("bb-squeeze+", -0.11, "hard_max_loss"),
           _t("other-sig", +0.05, "profit-monster-trail")]
    steers = analyze_recent_losses(maj)
    sig = [s for s in steers if s["title"].startswith("Signal 'bb-squeeze+'")]
    assert len(sig) == 1, sig
    assert "prearm_lock breakeven caps" in sig[0]["detail"], sig[0]["detail"]

    # (e) TRAILING-only reasons: 3 newest prearm, then a win, then 5 OLDER
    #     stops — reasons must ignore the pre-win stops (a move of the append
    #     outside the _streak_broken guard must fail here: 3/8 -> disable)
    trail = [_t("jup_yolo_mirrored", -0.01, "prearm_lock"),
             _t("jup_yolo_mirrored", -0.01, "prearm_lock"),
             _t("jup_yolo_mirrored", -0.01, "prearm_lock"),
             _t("jup_yolo_mirrored", +0.05, "profit-monster-trail"),
             ] + [_t("jup_yolo_mirrored", -0.10, "hard_max_loss") for _ in range(5)]
    steers = analyze_recent_losses(trail)
    sig = [s for s in steers if s["title"].startswith("Signal 'jup_yolo_mirrored'")]
    assert len(sig) == 1, sig
    assert "prearm_lock breakeven caps" in sig[0]["detail"], sig[0]["detail"]
    assert "Consider disabling" not in sig[0]["detail"], sig[0]["detail"]

    # (f) #289: never-armed majority -> chop-cohort diagnosis replaces
    #     "Something is wrong" (a deletion of the composition block must fail here)
    chop = [_t("atr-trend-", -0.05, "atr_sl_hit", mfe=0.10) for _ in range(5)] + \
           [_t("atr-trend-", -0.02, "hard_max_loss", mfe=0.15) for _ in range(2)] + \
           [_t("other-sig", +0.05, "profit-monster-trail", mfe=1.2)]
    steers = analyze_recent_losses(chop)
    st = [s for s in steers if s["title"].startswith("Losing streak")]
    assert len(st) == 1, st
    assert "chop cohort, not wrong-side" in st[0]["detail"], st[0]["detail"]
    assert "never armed" in st[0]["detail"], st[0]["detail"]
    assert "Something is wrong" not in st[0]["detail"], st[0]["detail"]

    # (g) armed-giveback majority -> exit/lock review branch
    give = [_t("jup_yolo_mirrored", -0.09, "atr_sl_hit", mfe=0.62) for _ in range(5)] + \
           [_t("jup_yolo_mirrored", -0.07, "hard_max_loss", mfe=0.45) for _ in range(2)] + \
           [_t("other-sig", +0.05, "profit-monster-trail", mfe=1.0)]
    steers = analyze_recent_losses(give)
    st = [s for s in steers if s["title"].startswith("Losing streak")]
    assert len(st) == 1, st
    assert "armed then gave back" in st[0]["detail"], st[0]["detail"]
    assert "exit/lock review" in st[0]["detail"], st[0]["detail"]

    # (h) neither majority (4 never / 4 armed of 8) -> mixed keeps the alarm
    mixm = [_t("x", -0.05, "atr_sl_hit", mfe=0.10) for _ in range(4)] + \
           [_t("x", -0.05, "atr_sl_hit", mfe=0.90) for _ in range(4)] + \
           [_t("y", +0.05, "profit-monster-trail", mfe=1.0) for _ in range(2)]
    steers = analyze_recent_losses(mixm)
    st = [s for s in steers if s["title"].startswith("Losing streak")]
    assert len(st) == 1, st
    assert "Something is wrong" in st[0]["detail"], st[0]["detail"]

    # (i) no mfe data at all -> old behavior preserved verbatim
    nomfe = [_t("z", -0.05, "hard_max_loss") for _ in range(6)] + \
            [_t("z", +0.05, "profit-monster-trail") for _ in range(3)]
    steers = analyze_recent_losses(nomfe)
    st = [s for s in steers if s["title"].startswith("Losing streak")]
    assert len(st) == 1, st
    assert "Something is wrong" in st[0]["detail"], st[0]["detail"]

    print("SELFCHECK PASS: interval-merge 5 + streak-advice 9 fixtures (a-i)")


if __name__ == "__main__":
    main()
