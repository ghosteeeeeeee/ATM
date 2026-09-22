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

# Mode: "recommend" or "autopilot"
# After 48h from deployment, change to "autopilot"
WATCHDOG_MODE = "recommend"

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
                   current_price, mfe_pct, mae_pct
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
                   open_time, close_time, pnl_usdt, signal,
                   _signal_metadata, regime,
                   amount_usdt, leverage
            FROM trades
            WHERE close_time IS NOT NULL
              AND exit_price IS NOT NULL AND exit_price != 0
            ORDER BY close_time DESC
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


def collect_btc_regime():
    """Read current BTC regime from multiple sources."""
    regime = {
        "btc_15m": None,
        "btc_4h": None,
        "continuum": None,
        "volatility": None
    }

    # BTC 15m regime from regime_15m.json (per-token regimes)
    regime_15m_path = os.path.join(WWW_DATA, "regime_15m.json")
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
                "auto_executable": WATCHDOG_MODE == "autopilot"
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
                    "auto_executable": WATCHDOG_MODE == "autopilot"
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
                    "auto_executable": WATCHDOG_MODE == "autopilot"
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
                "auto_executable": WATCHDOG_MODE == "autopilot"
            })

    return steers


def analyze_stale_trades(open_trades):
    """Flag trades that have been open too long."""
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
        direction = trade.get("direction", "?")

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
                    "auto_executable": WATCHDOG_MODE == "autopilot"
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
    """Analyze recent closed trades for patterns."""
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
        steers.append({
            "severity": "urgent",
            "category": "health",
            "title": f"Losing streak: {loss_count}/{total} recent trades lost",
            "detail": f"Win rate {wr:.0f}% over last {total} trades. "
                      f"Total PnL: {total_pnl:+.2f} USDT. Something is wrong.",
            "auto_executable": False
        })

    # Pattern: wrong direction
    wrong_side = 0
    for t in losses:
        sig = t.get("signal_name", "")
        direction = (t.get("direction") or "").lower()
        # If loss is > 2%, likely wrong direction
        pnl = t.get("pnl_usdt", 0) or 0
        entry = float(t.get("entry_price") or 0)
        if entry > 0 and abs(float(pnl)) / entry > 0.02:
            wrong_side += 1

    if wrong_side >= 3:
        steers.append({
            "severity": "warning",
            "category": "health",
            "title": f"{wrong_side} recent losses look like wrong-side trades",
            "detail": "Multiple large losses suggest we're fading momentum. "
                      "Check if signals are aligned with trend.",
            "auto_executable": False
        })

    # Pattern: specific signal losing
    sig_losses = {}
    for t in losses:
        sig = t.get("signal_name", "unknown")
        if sig not in sig_losses:
            sig_losses[sig] = {"count": 0, "total_loss": 0}
        sig_losses[sig]["count"] += 1
        sig_losses[sig]["total_loss"] += t.get("pnl_usdt", 0) or 0

    for sig, data in sig_losses.items():
        if data["count"] >= 3:
            steers.append({
                "severity": "warning",
                "category": "health",
                "title": f"Signal '{sig}' losing streak: {data['count']} losses",
                "detail": f"Total loss: {data['total_loss']:+.2f} USDT. "
                          f"Consider disabling or tuning this signal.",
                "auto_executable": False
            })

    return steers


def analyze_signal_quality(signal_perf, btc_regime):
    """Check which signals are performing well/poorly right now."""
    steers = []

    btc_trend = btc_regime.get("continuum") or btc_regime.get("btc_4h", "unknown")

    for sig, perf in signal_perf.items():
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

def collect_all():
    """Collect all data sources."""
    log("=== Data Collection ===")
    data = {
        "timestamp": now.isoformat(),
        "open_trades": collect_open_trades(),
        "recent_closed": collect_recent_closed(20),
        "btc_regime": collect_btc_regime(),
        "coin_tracker": collect_coin_tracker(),
        "pipeline_status": collect_pipeline_status(),
        "signal_performance": collect_signal_performance(),
    }
    log(f"Collection complete: {len(data['open_trades'])} open, "
        f"{len(data['recent_closed'])} recent, "
        f"{len(data['signal_performance'])} signals")
    return data


def analyze_all(data):
    """Run all analysis engines."""
    log("=== Analysis ===")
    steers = []

    steers.extend(analyze_regime_alignment(data["open_trades"], data["btc_regime"]))
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

    output = {
        "timestamp": now.isoformat(),
        "mode": WATCHDOG_MODE,
        "portfolio_health": health,
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
        "pipeline_status": data.get("pipeline_status", {}),
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
    recs = {
        "timestamp": now.isoformat(),
        "steers": steers,
        "portfolio_health": output["portfolio_health"],
        "regime": output["regime_summary"],
        "open_count": len(output["open_trades"]),
    }
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
            action["auto_executed"] = WATCHDOG_MODE == "autopilot"
            actions.append(action)

        atomic_write_json(ACTIONS_LOG, {"actions": actions})
        log(f"Logged {len(auto_actions)} actions to {ACTIONS_LOG}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Trade Watchdog")
    parser.add_argument("--collect", action="store_true", help="Collect data only")
    parser.add_argument("--analyze", action="store_true", help="Analyze only (requires collected data)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze but don't write outputs")
    args = parser.parse_args()

    log("Trade Watchdog starting...")

    data = collect_all()

    if args.collect:
        # Save raw data for later analysis
        raw_path = os.path.join(DATA_DIR, "watchdog_raw.json")
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        log(f"Saved raw data to {raw_path}")
        return

    steers = analyze_all(data)
    output = build_output(data, steers)
    write_outputs(output, steers, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print(f"Trade Watchdog — {output['portfolio_health'].upper()}")
    print(f"Open: {len(output['open_trades'])} trades | "
          f"Unrealized: {output['portfolio_summary']['total_unrealized_pnl']:+.2f} USDT")
    print(f"Steers: {len(steers)} "
          f"({sum(1 for s in steers if s['severity']=='urgent')} urgent)")
    print("=" * 60)

    for steer in steers:
        icon = {"urgent": "🔴", "warning": "🟡", "info": "🟢"}.get(steer["severity"], "⚪")
        print(f"  {icon} [{steer['category']}] {steer['title']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
