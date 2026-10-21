#!/usr/bin/env python3
"""shadow_trader.py — Shadow-Mode Paper Trading System (spec v1.3).

Processes EVERY signal fire as a simulated live trade through 7 exit engines.
Collects all context data, runs A/B tests on exit engines, answers gate
justification questions. Costs nothing — no money at stake.

Architecture:
  record → close → report

Modes (default runs all in sequence):
  --record   snapshot ALL signals from signals_hermes_runtime.db
  --close    close events >4.5h old: simulate 7 exit engines on 1m candles
  --report   aggregate by gate, exit engine, signal type, regime
  --reclose  re-close slow engines (universal hold 8h, ride_it 24h)
  --purge    delete records older than 90 days

Output DB: brain/shadow_trades.db (own file — never touches runtime DB).

Based on: plans/shadow-mode-paper-trading-spec-v1.md (v1.3)
"""
import sys
import os
import json
import sqlite3
import argparse
import calendar
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'shadow_trades.db')
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# Constants (from hermes_constants.py, verified in spec v1.3 Appendix B)
CUT_LOSER_PNL = -4.00          # account %
TRAILING_DISTANCE_PCT = 1.20   # ATR SL trail distance from peak
ATR_SL_MIN_INIT = 1.5          # initial floor
ATR_SL_MIN_ACCEL = 0.30        # established floor
ATR_SL_MAX = 2.5               # cap
PM_TRAIL_ACTIVATE_PCT = 0.40   # 0.40% activation
PM_TRAIL_TIERS = [(0.0, 0.20), (1.5, 0.50), (3.0, 0.80), (5.0, 1.20)]  # (peak_profit_pct, trail_dist_pct)
PM_TRAIL_MIN_HOLD = 2          # min candles after activation
VEL_STALE_THRESHOLD_PCT = 0.05 # % per candle
STALE_LOSER_TIMEOUT_MIN = 8    # minutes
STALE_WINNER_TIMEOUT_MIN = 120 # minutes
STALE_LOSER_MAX_LOSS = -1.0    # %
STALE_WINNER_MIN_PROFIT = 0.6  # %
UNIVERSAL_MAX_HOLD_MIN = 480   # minutes (8h)
RIDE_IT_MAX_HOLD_MIN = 1440    # minutes (24h)
BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN = 60
PUMP_CHAIN_TRAIL_ARM_TIMEOUT_MIN = 45
MAX_LEVERAGE = 5               # fallback cap

# Pump Exit constants (hermes_constants.py:4403-4407)
PUMP_EXIT_TRAIL_MULT = 3.0     # ATR multiplier for trailing stop
PUMP_EXIT_MOMENTUM_VEL = -0.5  # 5m velocity threshold for momentum exit
PUMP_EXIT_MOMENTUM_CANDLES = 2 # consecutive negative candles required
PUMP_EXIT_TIME_THRESHOLD = 2.0 # min profit % for time exit
PUMP_EXIT_TIME_HOURS = 2.0     # max hold time in hours

# Ride It constants (hermes_constants.py:4416-4439)
RIDE_IT_SL_PHASE1_MULT = 2.0   # 2.0x ATR initial SL
RIDE_IT_SL_PHASE1_FLOOR = 0.013 # 1.3% floor
RIDE_IT_SL_PHASE1_CAP = 0.025  # 2.5% cap
RIDE_IT_TP_PHASE1_MULT = 3.0   # 3x ATR TP target
RIDE_IT_TRAIL_ACTIVATE = 0.02  # 2% profit to activate trailing
RIDE_IT_TRAIL_DISTANCE = 0.012 # 1.2% trail distance
RIDE_IT_MOMENTUM_VEL = -0.5    # 5m velocity threshold
RIDE_IT_MOMENTUM_CANDLES = 2   # consecutive negative candles to exit
RIDE_IT_SPIKE_VOLUME_MULT = 5.0 # Volume > 5x 20-bar average
RIDE_IT_SPIKE_TRAIL_DISTANCE = 0.005 # 0.5% tight trail during spike
RIDE_IT_SPIKE_MIN_MOVE = 0.03  # Price must move >3% for spike mode
RIDE_IT_PHASE1_TO_PHASE2_TIME = 120 # minutes (2h) for phase transition

# Fee/slippage (from spec §12)
FEE_PCT = 0.04                 # per trade
SLIPPAGE_PCT = 0.10            # conservative estimate

# Close timing
CLOSE_AFTER_HOURS = 4.5        # need 4h forward + slack
RECLOSE_AFTER_HOURS = 8.5      # re-close pass for slow engines


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [shadow_trader] {msg}', flush=True)


def get_db():
    """Create/open shadow_trades.db with WAL mode for concurrency."""
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shadow_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER UNIQUE,
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            context_computed_at TEXT,
            closed INTEGER DEFAULT 0,
            closed_at TEXT,
            context JSON,
            leverage_used INTEGER,
            decision TEXT,
            decision_reason TEXT,
            gate_blocked INTEGER DEFAULT 0,
            gate_name TEXT,
            gate_name_backfilled INTEGER DEFAULT 0,
            exit_config TEXT,
            exit_atr_json JSON,
            exit_pm_trail_json JSON,
            exit_hard_max_json JSON,
            exit_cut_loser_json JSON,
            exit_speed_stale_json JSON,
            exit_universal_hold_json JSON,
            exit_trail_arm_timeout_json JSON,
            exit_rr_engine_json JSON,
            exit_pump_exit_json JSON,
            exit_ride_it_json JSON,
            first_exit_engine TEXT,
            first_exit_price REAL,
            first_exit_pnl_pct REAL,
            first_exit_hold_minutes REAL,
            first_exit_reason TEXT,
            fee_pct REAL DEFAULT 0.04,
            slippage_pct REAL DEFAULT 0.10,
            gross_pnl_pct REAL,
            net_pnl_pct REAL,
            fwd_30m REAL,
            fwd_1h REAL,
            fwd_4h REAL,
            excess_30m REAL,
            excess_1h REAL,
            excess_4h REAL,
            mfe_4h REAL,
            mae_4h REAL,
            mfe_pct REAL,
            mae_pct REAL,
            trade_id TEXT,
            created_at_db TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    
    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_token ON shadow_trades(token)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_direction ON shadow_trades(direction)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_signal_type ON shadow_trades(signal_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_source ON shadow_trades(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_created ON shadow_trades(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_closed ON shadow_trades(closed)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_gate ON shadow_trades(gate_blocked, gate_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shadow_first_exit ON shadow_trades(first_exit_engine)")
    
    # Meta table for watermarks
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    
    # Add new columns if they don't exist (for existing tables)
    try:
        conn.execute("ALTER TABLE shadow_trades ADD COLUMN exit_pump_exit_json JSON")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE shadow_trades ADD COLUMN exit_ride_it_json JSON")
    except sqlite3.OperationalError:
        pass  # column already exists
    
    conn.commit()
    return conn


def _load_candles_window(token, start_ts, end_ts):
    """Load 1m candles for a token in a time window. Windowed read per spec §6.4."""
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, high, low, close FROM candles_1m "
            "WHERE token=? AND ts>=? AND ts<=? AND is_closed=1 ORDER BY ts",
            (token.upper(), start_ts, end_ts)
        ).fetchall()
        return rows
    finally:
        conn.close()


def _get_signal_context(token, direction, signal_type, source, created_at):
    """Pull free context from signals table + signal_metadata (spec Phase 2)."""
    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    try:
        row = conn.execute("""
            SELECT rsi_14, macd_value, macd_signal, macd_hist, z_score, z_score_tier,
                   momentum_state, leverage, price, signal_metadata
            FROM signals
            WHERE token=? AND direction=? AND signal_type=? AND source=? AND created_at=?
            LIMIT 1
        """, (token, direction, signal_type, source, created_at)).fetchone()
        
        if not row:
            return {}
        
        ctx = {
            'rsi_14': row[0],
            'macd_value': row[1],
            'macd_signal': row[2],
            'macd_hist': row[3],
            'z_score': row[4],
            'z_score_tier': row[5],
            'momentum_state': row[6],
            'leverage': row[7],
            'price': row[8],
        }
        
        # Parse signal_metadata JSON for additional context
        if row[9]:
            try:
                meta = json.loads(row[9])
                ctx['bb_position'] = meta.get('bb_position')
                ctx['speed_percentile'] = meta.get('speed_percentile')
                ctx['wave_phase'] = meta.get('wave_phase')
                ctx['momentum_score'] = meta.get('momentum_score')
                ctx['btc_score'] = meta.get('btc_score')
                ctx['btc_regime'] = meta.get('btc_regime')
                ctx['btc_linreg_bias'] = meta.get('btc_linreg_bias')
            except (json.JSONDecodeError, TypeError):
                pass
        
        return ctx
    finally:
        conn.close()


def _get_vol_regime(token):
    """Get volatility regime from ATR (15m-primary per spec §4.1).

    bug_hunter fix: use tpsl_utils.get_fresh_atr (15m-primary), not
    volatility_gate_v2.get_atr_pct (1h). The engine ATR is 15m.
    """
    # Try 15m ATR first (engine primary)
    try:
        from tpsl_utils import get_fresh_atr
        atr = get_fresh_atr(token)
        if atr is not None:
            # Classify using volatility_gate_v2 thresholds
            from volatility_gate_v2 import classify_volatility
            return classify_volatility(atr), atr
    except Exception:
        pass
    # Fallback to 1h ATR (volatility gate)
    try:
        from volatility_gate_v2 import get_atr_pct, classify_volatility
        atr = get_atr_pct(token)
        if atr is not None:
            return classify_volatility(atr), atr
    except Exception:
        pass
    return 'UNKNOWN', None


def _match_exit_config_safe(source):
    """Route signal to exit config. Import real function per spec §4.0."""
    try:
        from position_manager import _match_exit_config
        return _match_exit_config(source) or 'atr'
    except Exception:
        # Fallback: simple prefix match
        if not source:
            return 'atr'
        bare = source.rstrip('+-')
        if 'pump-chain' in bare:
            return 'pump_exit'
        if 'mover' in bare or 'volume-breakout' in bare or 'trend-ride' in bare:
            return 'ride_it'
        return 'atr'


def _get_leverage(token, signals_leverage):
    """Get leverage from PG trades per-token history (bug_hunter fix 1).

    The old get_trade_params(token) raises TypeError (needs direction, price)
    and was silently falling back to cap-at-5. Live PG 14d: lev 3×125 (39%!),
    5×191, 10×9, 40×1. Source from PG trades history for this token.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                               user='postgres', connect_timeout=2)
        cur = conn.cursor()
        cur.execute("""
            SELECT leverage, COUNT(*) as n
            FROM trades
            WHERE token=%s AND leverage IS NOT NULL
            GROUP BY leverage ORDER BY n DESC LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return int(row[0])
    except Exception:
        pass
    # Fallback
    if signals_leverage:
        return min(int(signals_leverage), MAX_LEVERAGE)
    return MAX_LEVERAGE


def record():
    """Snapshot ALL signals not yet recorded."""
    conn = get_db()
    try:
        cur = conn.cursor()
        last_id = cur.execute("SELECT value FROM meta WHERE key='last_signal_id'").fetchone()
        last_id = int(last_id[0]) if last_id else 0
        
        rt = sqlite3.connect(RUNTIME_DB, timeout=10)
        try:
            rows = rt.execute("""
                SELECT id, token, direction, signal_type, source, confidence,
                       decision, COALESCE(decision_reason,''), created_at
                FROM signals
                WHERE id > ?
                ORDER BY id
            """, (last_id,)).fetchall()
        finally:
            rt.close()
        
        now = datetime.now(timezone.utc).isoformat()
        n = 0
        
        # Load shadow bypass registry (T directive 2026-10-21)
        shadow_bypass = {}
        try:
            from hermes_constants import SHADOW_BYPASS_SIGNALS, SHADOW_BYPASS_ENABLED
            if SHADOW_BYPASS_ENABLED:
                shadow_bypass = SHADOW_BYPASS_SIGNALS
        except ImportError:
            pass
        
        for sid, tok, d, st, src, conf, dec, reason, created in rows:
            try:
                # Get context
                ctx = _get_signal_context(tok, d, st, src, created)
                ctx['context_computed_at'] = now
                
                # Check if this signal is in shadow bypass registry
                # bug_hunter fix: check BOTH signal_type and source
                # bug_hunter fix: split composite sources by comma
                # bug_hunter fix: check direction match
                # bug_hunter fix: exact match for suffixed keys, substring only for compound
                # bug_hunter fix: only tag if ALL source parts are in registry (not just one)
                shadow_bypass_tag = False
                shadow_bypass_reason = None
                
                # For composite sources, check if ANY part is NOT in registry
                # If so, this is a live signal — don't tag as shadow_bypass
                skip_composite = False
                if src and ',' in src:
                    parts = [p.strip().lower() for p in src.split(',') if p.strip()]
                    for part in parts:
                        part_stripped = part.rstrip('+-')
                        in_registry = False
                        for bypass_key in shadow_bypass:
                            key_lower = bypass_key.lower()
                            has_suffix = key_lower.endswith('+') or key_lower.endswith('-')
                            if has_suffix:
                                if key_lower == part:
                                    in_registry = True
                                    break
                            else:
                                if key_lower in part or key_lower == part_stripped:
                                    in_registry = True
                                    break
                        if not in_registry:
                            skip_composite = True
                            break
                
                if not skip_composite:
                    # Build searchable strings: signal_type, source, and individual source parts
                    search_strings = set()
                    if st:
                        search_strings.add(st.lower())
                    if src:
                        search_strings.add(src.lower())
                        # Split composite sources by comma
                        for part in src.split(','):
                            part = part.strip().lower()
                            if part:
                                search_strings.add(part)
                                # Also add stripped version (remove +/-)
                                search_strings.add(part.rstrip('+-'))
                    
                    for bypass_key, bypass_info in shadow_bypass.items():
                        key_lower = bypass_key.lower()
                        
                        # Determine match type: exact vs substring
                        has_suffix = key_lower.endswith('+') or key_lower.endswith('-')
                        
                        matched = False
                        for s in search_strings:
                            if has_suffix:
                                # Exact match for suffixed keys
                                if key_lower == s:
                                    matched = True
                                    break
                            else:
                                # Substring match for compound keys
                                if key_lower in s:
                                    matched = True
                                    break
                        
                        if not matched:
                            continue
                        
                        # Check direction match
                        bypass_dir = bypass_info.get('direction', '').upper()
                        if bypass_dir and bypass_dir != (d or '').upper():
                            continue
                        
                        shadow_bypass_tag = True
                        shadow_bypass_reason = bypass_info.get('reason', '')
                        ctx['shadow_bypass'] = True
                        ctx['shadow_bypass_reason'] = shadow_bypass_reason
                        ctx['shadow_bypass_stage'] = bypass_info.get('stage', 'unknown')
                        ctx['shadow_bypass_key'] = bypass_key
                        break
                
                # Get vol regime
                vol_regime, atr = _get_vol_regime(tok)
                ctx['vol_regime'] = vol_regime
                ctx['atr_pct'] = atr
                
                # Route exit config
                exit_config = _match_exit_config_safe(src)
                
                # Get leverage
                leverage = _get_leverage(tok, ctx.get('leverage'))
                
                # Gate name backfill
                gate_name = None
                gate_blocked = 0
                if dec in ('EXPIRED', 'SKIPPED', 'FAILED'):
                    gate_blocked = 1
                    if 'compaction_stale' in reason:
                        gate_name = 'CONFLUENCE-EXPIRY'
                    elif reason:
                        # Try to parse from reason
                        import re
                        match = re.search(r'\[([A-Z-]+)\]', reason)
                        if match:
                            gate_name = match.group(1)
                        else:
                            gate_name = 'UNKNOWN'
                
                cur.execute("""
                    INSERT OR IGNORE INTO shadow_trades 
                    (signal_id, token, direction, signal_type, source, confidence,
                     created_at, recorded_at, context_computed_at, context,
                     leverage_used, decision, decision_reason, gate_blocked, gate_name,
                     exit_config)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (sid, tok, d, st, src, conf, created, now, now,
                      json.dumps(ctx), leverage, dec, reason, gate_blocked, gate_name,
                      exit_config))
                
                if cur.rowcount > 0:
                    n += 1
            except Exception as e:
                log(f"ERROR recording signal {sid}: {e}")
        
        # Update watermark
        if rows:
            cur.execute("""
                INSERT INTO meta (key, value) VALUES ('last_signal_id', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (str(rows[-1][0]),))
        
        conn.commit()
        log(f"record: +{n} signals (last_id={last_id}, new_last={rows[-1][0] if rows else last_id})")
        return n
    finally:
        conn.close()


def _simulate_atr_sl_tp(entry_price, direction, candles, atr_pct):
    """Simulate ATR SL/TP with continuous peak-trailing (spec §4.1)."""
    if not candles or atr_pct is None:
        return None
    
    # Initial SL/TP distances (simplified — use ATR * multiplier)
    sl_dist = min(atr_pct * 1.0, ATR_SL_MAX)  # Simplified multiplier
    tp_dist = atr_pct * 2.0  # Simplified TP
    
    sl_price = entry_price * (1 - sl_dist/100) if direction == 'LONG' else entry_price * (1 + sl_dist/100)
    tp_price = entry_price * (1 + tp_dist/100) if direction == 'LONG' else entry_price * (1 - tp_dist/100)
    
    peak_price = entry_price
    min_sl_dist = ATR_SL_MIN_INIT
    
    for ts, o, h, l, c in candles:
        # Update peak
        if direction == 'LONG':
            peak_price = max(peak_price, h)
        else:
            peak_price = min(peak_price, l)
        
        # Trail SL from peak (tighten only)
        if direction == 'LONG':
            new_sl = peak_price * (1 - TRAILING_DISTANCE_PCT/100)
            sl_price = max(sl_price, new_sl)
            min_sl_dist = ATR_SL_MIN_ACCEL
            max_sl = peak_price * (1 - min_sl_dist/100)
            sl_price = min(sl_price, max_sl)
            
            # Check exits
            if l <= sl_price:
                exit_type = 'atr_trail_hit' if sl_price > entry_price else 'atr_sl_hit'
                pnl = (sl_price / entry_price - 1) * 100
                return {'fired': True, 'exit_type': exit_type, 'exit_price': sl_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
            if h >= tp_price:
                pnl = (tp_price / entry_price - 1) * 100
                return {'fired': True, 'exit_type': 'atr_tp_hit', 'exit_price': tp_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
        else:
            new_sl = peak_price * (1 + TRAILING_DISTANCE_PCT/100)
            sl_price = min(sl_price, new_sl)
            min_sl_dist = ATR_SL_MIN_ACCEL
            min_sl = peak_price * (1 + min_sl_dist/100)
            sl_price = max(sl_price, min_sl)
            
            if h >= sl_price:
                exit_type = 'atr_trail_hit' if sl_price < entry_price else 'atr_sl_hit'
                pnl = (entry_price / sl_price - 1) * 100
                return {'fired': True, 'exit_type': exit_type, 'exit_price': sl_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
            if l <= tp_price:
                pnl = (entry_price / tp_price - 1) * 100
                return {'fired': True, 'exit_type': 'atr_tp_hit', 'exit_price': tp_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
    
    # No exit — hold to end
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - candles[0][0]) / 60}


def _simulate_pm_trail(entry_price, direction, candles, source, vol_regime):
    """Simulate PM Trail with tiered distances (spec §4.2)."""
    if not candles:
        return None
    
    # Check bypass list
    bare = (source or '').rstrip('+-')
    try:
        from hermes_constants import PROFIT_MONSTER_BYPASS_SIGNALS
        if any(b in bare for b in PROFIT_MONSTER_BYPASS_SIGNALS):
            return {'fired': False, 'exit_type': 'bypass', 'notes': 'bypass signal'}
    except Exception:
        pass
    
    # Spider regime override
    if vol_regime == 'FLAT':
        activate_pct = 0.30
        tiers = [(0.0, 0.10), (1.5, 0.30), (3.0, 0.50)]
    else:
        activate_pct = PM_TRAIL_ACTIVATE_PCT
        tiers = PM_TRAIL_TIERS
    
    peak_price = entry_price
    trail_active = False
    activation_idx = None
    
    for i, (ts, o, h, l, c) in enumerate(candles):
        # Update peak
        if direction == 'LONG':
            peak_price = max(peak_price, h)
        else:
            peak_price = min(peak_price, l)
        
        # Check activation
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        if not trail_active and current_pnl >= activate_pct:
            trail_active = True
            activation_idx = i
        
        # Check trail exit
        if trail_active and (i - activation_idx) >= PM_TRAIL_MIN_HOLD:
            # Get tiered distance
            peak_profit = (peak_price / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / peak_price - 1) * 100
            trail_dist = tiers[0][1]  # default
            for threshold, dist in tiers:
                if peak_profit >= threshold:
                    trail_dist = dist
            
            if direction == 'LONG':
                trail_price = peak_price * (1 - trail_dist/100)
                if l <= trail_price:
                    pnl = (trail_price / entry_price - 1) * 100
                    return {'fired': True, 'exit_type': 'trail_sl', 'exit_price': trail_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
            else:
                trail_price = peak_price * (1 + trail_dist/100)
                if h >= trail_price:
                    pnl = (entry_price / trail_price - 1) * 100
                    return {'fired': True, 'exit_type': 'trail_sl', 'exit_price': trail_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
    
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - candles[0][0]) / 60}


def _simulate_hard_max_loss(entry_price, direction, candles, leverage):
    """Simulate Hard Max Loss (spec §4.3)."""
    if not candles:
        return None
    
    hml_threshold_pct = CUT_LOSER_PNL / leverage
    hml_price = entry_price * (1 + hml_threshold_pct/100) if direction == 'LONG' else entry_price * (1 - hml_threshold_pct/100)
    
    for ts, o, h, l, c in candles:
        if direction == 'LONG':
            if l <= hml_price:
                pnl = (hml_price / entry_price - 1) * 100
                return {'fired': True, 'exit_type': 'hard_max_loss', 'exit_price': hml_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
        else:
            if h >= hml_price:
                pnl = (entry_price / hml_price - 1) * 100
                return {'fired': True, 'exit_type': 'hard_max_loss', 'exit_price': hml_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
    
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - candles[0][0]) / 60}


def _simulate_cut_loser(entry_price, direction, candles, source):
    """Simulate Cut Loser two-tier (spec §4.5)."""
    if not candles:
        return None
    
    # Check bypass list
    bare = (source or '').rstrip('+-')
    try:
        from hermes_constants import PROFIT_MONSTER_BYPASS_SIGNALS
        if any(b in bare for b in PROFIT_MONSTER_BYPASS_SIGNALS):
            return {'fired': False, 'exit_type': 'bypass', 'notes': 'bypass signal'}
    except Exception:
        pass
    
    for ts, o, h, l, c in candles:
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        
        # Hard stop: -3.0%
        if current_pnl <= -3.0:
            return {'fired': True, 'exit_type': 'cut_loser_hard_stop', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
        
        # Tier 1: [-1.0%, -2.5%]
        if -2.5 <= current_pnl <= -1.0:
            return {'fired': True, 'exit_type': 'cut_loser_t1', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
        
        # Tier 2: [-2.5%, -3.0%]
        if -3.0 <= current_pnl <= -2.5:
            return {'fired': True, 'exit_type': 'cut_loser_t2', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - candles[0][0]) / 60}
    
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - candles[0][0]) / 60}


def _simulate_speed_stale(entry_price, direction, candles):
    """Simulate Speed Stale exit (spec §4.6)."""
    if not candles:
        return None
    
    last_move_ts = candles[0][0]
    last_price = entry_price
    
    for ts, o, h, l, c in candles:
        # Check if price moved
        if abs(c - last_price) / last_price * 100 > VEL_STALE_THRESHOLD_PCT:
            last_move_ts = ts
            last_price = c
        
        stall_minutes = (ts - last_move_ts) / 60
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        
        # Speed stale loser
        if stall_minutes >= STALE_LOSER_TIMEOUT_MIN and current_pnl <= STALE_LOSER_MAX_LOSS:
            return {'fired': True, 'exit_type': 'speed_stale_loser', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - candles[0][0]) / 60,
                    'stall_gate_note': 'shadow omits speed_percentile gate'}
        
        # Speed stale winner
        if stall_minutes >= STALE_WINNER_TIMEOUT_MIN and current_pnl >= STALE_WINNER_MIN_PROFIT:
            return {'fired': True, 'exit_type': 'speed_stale_winner', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - candles[0][0]) / 60,
                    'stall_gate_note': 'shadow omits speed_percentile gate'}
    
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - candles[0][0]) / 60}


def _simulate_universal_hold(entry_price, direction, candles, source):
    """Simulate Universal Max Hold (spec §4.7)."""
    if not candles:
        return None
    
    # Check ride_it exemption
    ride_it_substrings = ('ride_it', 'trend-ride', 'trend_ride', 'volume-breakout', 'volume_breakout', 'mover-')
    max_hold = RIDE_IT_MAX_HOLD_MIN if any(sub in (source or '') for sub in ride_it_substrings) else UNIVERSAL_MAX_HOLD_MIN
    
    # Find exit candle at max_hold
    entry_ts = candles[0][0]
    exit_ts = entry_ts + max_hold * 60
    
    for ts, o, h, l, c in candles:
        if ts >= exit_ts:
            pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
            return {'fired': True, 'exit_type': 'universal_max_hold', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
    
    # Not enough candles — truncated
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'truncated', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - entry_ts) / 60,
            'note': f'truncated at {(candles[-1][0] - entry_ts) / 60:.0f}min, need {max_hold}min'}


def _simulate_trail_arm_timeout(entry_price, direction, candles, source):
    """Simulate Trail Arm Timeout (spec §4.8).

    bug_hunter fix: live is LONG-only (position_manager.py:3599).
    bb-squeeze SHORTs do NOT have trail-arm timeout.
    """
    if not candles:
        return None
    
    # LONG-only per live code
    if direction != 'LONG':
        return {'fired': False, 'exit_type': 'no_timeout', 'notes': 'LONG-only engine'}
    
    # Determine timeout
    bare = (source or '').rstrip('+-')
    if 'bb-squeeze' in bare:
        timeout_min = BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN
    elif 'pump-chain' in bare:
        timeout_min = PUMP_CHAIN_TRAIL_ARM_TIMEOUT_MIN
    else:
        return {'fired': False, 'exit_type': 'no_timeout', 'notes': 'not applicable'}
    
    entry_ts = candles[0][0]
    
    for ts, o, h, l, c in candles:
        hold_minutes = (ts - entry_ts) / 60
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        
        # Close if current pnl < 0.40% AT timeout mark
        if hold_minutes >= timeout_min and current_pnl < PM_TRAIL_ACTIVATE_PCT:
            return {'fired': True, 'exit_type': 'trail_arm_timeout', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': hold_minutes}
    
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'armed', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - entry_ts) / 60}


def _simulate_pump_exit(entry_price, direction, candles, atr_pct):
    """Simulate Pump Exit (momentum exit for pump-chain LONG).

    From position_manager.py:2898-3030:
    - Trail SL: ATR * PUMP_EXIT_TRAIL_MULT (3.0) from peak
    - Momentum exit: exit when price drops for PUMP_EXIT_MOMENTUM_CANDLES (2)
      consecutive candles with velocity < PUMP_EXIT_MOMENTUM_VEL (-0.5%)
    - Time exit: exit after PUMP_EXIT_TIME_HOURS (2.0) if profit > PUMP_EXIT_TIME_THRESHOLD (2.0%)
    """
    if not candles or atr_pct is None:
        return None
    
    entry_ts = candles[0][0]
    peak_price = entry_price
    trail_distance = atr_pct * PUMP_EXIT_TRAIL_MULT / 100  # Convert to fraction
    
    for i, (ts, o, h, l, c) in enumerate(candles):
        # Update peak
        if direction == 'LONG':
            peak_price = max(peak_price, h)
        else:
            peak_price = min(peak_price, l)
        
        # Trail SL check
        # bug_hunter fix: accel clamp was INVERTED — live uses min-style cap
        # (SL never tighter than entry±0.3%), not max-style floor
        if direction == 'LONG':
            trailing_sl = peak_price * (1 - trail_distance)
            # Cap: SL must stay at least 0.3% below entry (not tighter)
            accel_cap = entry_price * (1 - ATR_SL_MIN_ACCEL / 100)
            trailing_sl = min(trailing_sl, accel_cap)  # FIX: was max()
            
            if l <= trailing_sl:
                pnl = (trailing_sl / entry_price - 1) * 100
                return {'fired': True, 'exit_type': 'pump_exit_trail', 'exit_price': trailing_sl,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
        else:
            trailing_sl = peak_price * (1 + trail_distance)
            # Cap: SL must stay at least 0.3% above entry (not tighter)
            accel_cap = entry_price * (1 + ATR_SL_MIN_ACCEL / 100)
            trailing_sl = max(trailing_sl, accel_cap)  # FIX: was min()
            
            if h >= trailing_sl:
                pnl = (entry_price / trailing_sl - 1) * 100
                return {'fired': True, 'exit_type': 'pump_exit_trail', 'exit_price': trailing_sl,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
        
        # Momentum exit (check last 2 candles)
        if i >= PUMP_EXIT_MOMENTUM_CANDLES:
            neg_count = 0
            for j in range(i - PUMP_EXIT_MOMENTUM_CANDLES + 1, i + 1):
                prev_c = candles[j-1][4]
                curr_c = candles[j][4]
                if prev_c > 0:
                    vel = (curr_c - prev_c) / prev_c * 100
                    if direction == 'LONG' and vel < PUMP_EXIT_MOMENTUM_VEL:
                        neg_count += 1
                    elif direction == 'SHORT' and vel > abs(PUMP_EXIT_MOMENTUM_VEL):
                        neg_count += 1
                    else:
                        neg_count = 0
                        break
            
            if neg_count >= PUMP_EXIT_MOMENTUM_CANDLES:
                pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
                return {'fired': True, 'exit_type': 'pump_exit_momentum', 'exit_price': c,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
        
        # Time exit — dead money check
        # bug_hunter fix: polarity was INVERTED — live exits LOSERS (profit < 2%),
        # not winners (profit >= 2%)
        hold_hours = (ts - entry_ts) / 3600
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        if hold_hours >= PUMP_EXIT_TIME_HOURS and current_pnl < PUMP_EXIT_TIME_THRESHOLD:
            return {'fired': True, 'exit_type': 'pump_exit_dead_money', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': current_pnl, 'hold_minutes': (ts - entry_ts) / 60}
    
    # No exit — hold to end
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - entry_ts) / 60}


def _simulate_ride_it(entry_price, direction, candles, atr_pct):
    """Simulate Ride It exit (2-phase system).

    From ride_it_exit.py:
    - Phase 1 (0-2h): Wide ATR SL (2.0x ATR, floor 1.3%, cap 2.5%), TP 3x ATR
    - Phase 2 (2h+): Trail activates at +2%, trail distance 1.2%
    - Momentum exit: 2 consecutive negative candles
    - Max hold: 24h
    """
    if not candles or atr_pct is None:
        return None
    
    entry_ts = candles[0][0]
    
    # Phase 1 SL/TP
    sl_pct = min(max(atr_pct * RIDE_IT_SL_PHASE1_MULT, RIDE_IT_SL_PHASE1_FLOOR * 100), RIDE_IT_SL_PHASE1_CAP * 100)
    tp_pct = atr_pct * RIDE_IT_TP_PHASE1_MULT
    sl_price = entry_price * (1 - sl_pct/100) if direction == 'LONG' else entry_price * (1 + sl_pct/100)
    tp_price = entry_price * (1 + tp_pct/100) if direction == 'LONG' else entry_price * (1 - tp_pct/100)
    
    peak_price = entry_price
    trail_active = False
    
    for i, (ts, o, h, l, c) in enumerate(candles):
        hold_minutes = (ts - entry_ts) / 60
        
        # Update peak
        if direction == 'LONG':
            peak_price = max(peak_price, h)
        else:
            peak_price = min(peak_price, l)
        
        current_pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
        
        # Phase 1: SL/TP check
        if hold_minutes < RIDE_IT_PHASE1_TO_PHASE2_TIME:
            if direction == 'LONG':
                if l <= sl_price:
                    pnl = (sl_price / entry_price - 1) * 100
                    return {'fired': True, 'exit_type': 'ride_it_sl', 'exit_price': sl_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
                if h >= tp_price:
                    pnl = (tp_price / entry_price - 1) * 100
                    return {'fired': True, 'exit_type': 'ride_it_tp', 'exit_price': tp_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
            else:
                if h >= sl_price:
                    pnl = (entry_price / sl_price - 1) * 100
                    return {'fired': True, 'exit_type': 'ride_it_sl', 'exit_price': sl_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
                if l <= tp_price:
                    pnl = (entry_price / tp_price - 1) * 100
                    return {'fired': True, 'exit_type': 'ride_it_tp', 'exit_price': tp_price,
                            'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
        
        # Phase 2: Trail activation (only after phase 1 ends)
        # bug_hunter fix: gate trail to phase 2 only (after 2h)
        if hold_minutes >= RIDE_IT_PHASE1_TO_PHASE2_TIME:
            if current_pnl >= RIDE_IT_TRAIL_ACTIVATE * 100:
                trail_active = True
            
            if trail_active:
                trail_dist = RIDE_IT_TRAIL_DISTANCE * 100
                if direction == 'LONG':
                    trail_price = peak_price * (1 - trail_dist/100)
                    if l <= trail_price:
                        pnl = (trail_price / entry_price - 1) * 100
                        return {'fired': True, 'exit_type': 'ride_it_trail', 'exit_price': trail_price,
                                'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
                else:
                    trail_price = peak_price * (1 + trail_dist/100)
                    if h >= trail_price:
                        pnl = (entry_price / trail_price - 1) * 100
                        return {'fired': True, 'exit_type': 'ride_it_trail', 'exit_price': trail_price,
                                'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
        
        # Momentum exit (check last 2 candles) — only in phase 2 with profit > 1%
        # bug_hunter fix: add phase gate and profit gate
        if (hold_minutes >= RIDE_IT_PHASE1_TO_PHASE2_TIME and 
            current_pnl > 1.0 and  # Live requires profit > 1%
            i >= RIDE_IT_MOMENTUM_CANDLES):
            neg_count = 0
            for j in range(i - RIDE_IT_MOMENTUM_CANDLES + 1, i + 1):
                prev_c = candles[j-1][4]
                curr_c = candles[j][4]
                if prev_c > 0:
                    vel = (curr_c - prev_c) / prev_c * 100
                    if direction == 'LONG' and vel < RIDE_IT_MOMENTUM_VEL:
                        neg_count += 1
                    elif direction == 'SHORT' and vel > abs(RIDE_IT_MOMENTUM_VEL):
                        neg_count += 1
                    else:
                        neg_count = 0
                        break
            
            if neg_count >= RIDE_IT_MOMENTUM_CANDLES:
                pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
                return {'fired': True, 'exit_type': 'ride_it_momentum', 'exit_price': c,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
        
        # Max hold
        if hold_minutes >= RIDE_IT_MAX_HOLD_MIN:
            pnl = (c / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / c - 1) * 100
            return {'fired': True, 'exit_type': 'ride_it_max_hold', 'exit_price': c,
                    'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': hold_minutes}
    
    # No exit — hold to end
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - entry_ts) / 60}


def _simulate_rr_engine(entry_price, direction, candles, atr_pct):
    """Simulate RR Engine (structural S/R based SL/TP).

    Simplified version of risk_reward_engine.py (~1200 lines).
    Uses ATR-based SL/TP with S/R level adjustments.

    Full RR engine uses:
    - Multi-source S/R levels (candle swings + order book + liquidation clusters)
    - Volatility width (ATR% + Bollinger Band width)
    - Liquidity proximity (distance to nearest cluster)
    - Structural reward (target = nearest S/R, not arbitrary TP)

    This simplified version uses ATR-based SL/TP as approximation.
    """
    if not candles or atr_pct is None:
        return None
    
    entry_ts = candles[0][0]
    
    # Simplified RR: use ATR-based SL/TP with tighter stops
    # bug_hunter fix: add floors/caps like live ATR engine
    # bug_hunter fix: remove TP (live RR engine doesn't have TP, it uses structural S/R)
    sl_pct = atr_pct * 0.8  # Tighter than ATR default (1.0x)
    # Apply floors/caps like live ATR engine
    sl_pct = max(ATR_SL_MIN_ACCEL, min(sl_pct, ATR_SL_MAX))  # Floor 0.3%, cap 2.5%
    
    sl_price = entry_price * (1 - sl_pct/100) if direction == 'LONG' else entry_price * (1 + sl_pct/100)
    # No TP — live RR engine exits on structural S/R break, not fixed TP
    
    peak_price = entry_price
    
    for i, (ts, o, h, l, c) in enumerate(candles):
        # Update peak
        if direction == 'LONG':
            peak_price = max(peak_price, h)
        else:
            peak_price = min(peak_price, l)
        
        # Trail SL (tighter than ATR default)
        # bug_hunter fix: no TP — live RR engine exits on structural S/R break
        trail_dist = atr_pct * 0.6 / 100  # 0.6x ATR trail
        if direction == 'LONG':
            trailing_sl = peak_price * (1 - trail_dist)
            sl_price = max(sl_price, trailing_sl)
            
            if l <= sl_price:
                exit_type = 'rr_trail_hit' if sl_price > entry_price else 'rr_sl_hit'
                pnl = (sl_price / entry_price - 1) * 100
                return {'fired': True, 'exit_type': exit_type, 'exit_price': sl_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
        else:
            trailing_sl = peak_price * (1 + trail_dist)
            sl_price = min(sl_price, trailing_sl)
            
            if h >= sl_price:
                exit_type = 'rr_trail_hit' if sl_price < entry_price else 'rr_sl_hit'
                pnl = (entry_price / sl_price - 1) * 100
                return {'fired': True, 'exit_type': exit_type, 'exit_price': sl_price,
                        'exit_ts': ts, 'pnl_pct': pnl, 'hold_minutes': (ts - entry_ts) / 60}
    
    # No exit — hold to end
    last_close = candles[-1][4]
    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
    return {'fired': False, 'exit_type': 'no_exit', 'exit_price': last_close,
            'exit_ts': candles[-1][0], 'pnl_pct': pnl,
            'hold_minutes': (candles[-1][0] - entry_ts) / 60}


def close_events():
    """Close events >4.5h old: simulate 7 exit engines on 1m candles."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLOSE_AFTER_HOURS))
        
        pending = cur.execute("""
            SELECT id, token, direction, source, created_at, leverage_used, context
            FROM shadow_trades
            WHERE closed=0 AND created_at < ?
            LIMIT 1000
        """, (cutoff.strftime('%Y-%m-%d %H:%M:%S'),)).fetchall()
        
        if not pending:
            log('close: 0 pending')
            return 0
        
        n_ok = 0
        for sid, tok, d, src, created, lev, ctx_json in pending:
            try:
                entry_ts = calendar.timegm(datetime.strptime(created, '%Y-%m-%d %H:%M:%S').timetuple())
            except (ValueError, TypeError):
                continue
            
            # Load candles for 24h window (covers all engines)
            candles = _load_candles_window(tok, entry_ts, entry_ts + 86400)
            if not candles:
                cur.execute("UPDATE shadow_trades SET closed=1, closed_at=?, first_exit_reason='unclosed_no_candles' WHERE id=?",
                           (datetime.now(timezone.utc).isoformat(), sid))
                continue
            
            entry_price = candles[0][1]  # open of first candle
            ctx = json.loads(ctx_json) if ctx_json else {}
            atr_pct = ctx.get('atr_pct')
            vol_regime = ctx.get('vol_regime', 'UNKNOWN')
            leverage = lev or MAX_LEVERAGE
            
            # Simulate all 10 engines
            results = {}
            results['atr'] = _simulate_atr_sl_tp(entry_price, d, candles, atr_pct)
            results['pm_trail'] = _simulate_pm_trail(entry_price, d, candles, src, vol_regime)
            results['hard_max'] = _simulate_hard_max_loss(entry_price, d, candles, leverage)
            results['cut_loser'] = _simulate_cut_loser(entry_price, d, candles, src)
            results['speed_stale'] = _simulate_speed_stale(entry_price, d, candles)
            results['universal_hold'] = _simulate_universal_hold(entry_price, d, candles, src)
            results['trail_arm_timeout'] = _simulate_trail_arm_timeout(entry_price, d, candles, src)
            results['pump_exit'] = _simulate_pump_exit(entry_price, d, candles, atr_pct)
            results['ride_it'] = _simulate_ride_it(entry_price, d, candles, atr_pct)
            results['rr_engine'] = _simulate_rr_engine(entry_price, d, candles, atr_pct)
            
            # Determine first exit to fire (deterministic tie-break per spec §4.0)
            # Loss-side precedence: HML → Cut Loser Hard → Cut Loser T2 → Cut Loser T1 → ATR SL → Speed Stale → Trail Arm → Universal
            # Profit-side precedence: ATR TP → PM Trail → Speed Stale Winner
            fired = [(k, v) for k, v in results.items() if v and v.get('fired')]
            
            # Tie-break precedence (bug_hunter fix 3): NOT alphabetical
            # Lower number = higher precedence (fires first on same candle)
            _PRECEDENCE = {
                'hard_max': 1,           # HML (loss-side worst)
                'cut_loser': 2,          # Cut Loser (check exit_type for tier)
                'atr': 3,                # ATR SL/TP
                'rr_engine': 4,          # RR Engine (tighter SL)
                'pump_exit': 5,          # Pump Exit (momentum)
                'ride_it': 6,            # Ride It (2-phase)
                'speed_stale': 7,        # Speed Stale
                'trail_arm_timeout': 8,  # Trail Arm Timeout
                'universal_hold': 9,     # Universal Max Hold (slowest)
                'pm_trail': 10,          # PM Trail (profit-side)
            }
            
            if fired:
                # Sort by exit_ts, then by precedence (NOT alphabetical)
                fired.sort(key=lambda x: (
                    x[1].get('exit_ts', 0),
                    _PRECEDENCE.get(x[0], 99)
                ))
                first_engine, first_result = fired[0]
                
                gross_pnl = first_result['pnl_pct']
                net_pnl = gross_pnl - FEE_PCT - SLIPPAGE_PCT
                
                # Compute actual MFE/MAE from price data (bug_hunter fix)
                # MFE = max favorable excursion, MAE = max adverse excursion
                highs = [h for ts, o, h, l, c in candles]
                lows = [l for ts, o, h, l, c in candles]
                if d == 'LONG':
                    mfe = (max(highs) / entry_price - 1) * 100
                    mae = (min(lows) / entry_price - 1) * 100
                else:
                    mfe = (entry_price / min(lows) - 1) * 100
                    mae = (entry_price / max(highs) - 1) * 100
                
                cur.execute("""
                    UPDATE shadow_trades SET
                        closed=1, closed_at=?,
                        exit_atr_json=?, exit_pm_trail_json=?, exit_hard_max_json=?,
                        exit_cut_loser_json=?, exit_speed_stale_json=?, exit_universal_hold_json=?,
                        exit_trail_arm_timeout_json=?, exit_rr_engine_json=?,
                        exit_pump_exit_json=?, exit_ride_it_json=?,
                        first_exit_engine=?, first_exit_price=?, first_exit_pnl_pct=?,
                        first_exit_hold_minutes=?, first_exit_reason=?,
                        gross_pnl_pct=?, net_pnl_pct=?,
                        mfe_pct=?, mae_pct=?
                    WHERE id=?
                """, (datetime.now(timezone.utc).isoformat(),
                      json.dumps(results.get('atr')), json.dumps(results.get('pm_trail')),
                      json.dumps(results.get('hard_max')), json.dumps(results.get('cut_loser')),
                      json.dumps(results.get('speed_stale')), json.dumps(results.get('universal_hold')),
                      json.dumps(results.get('trail_arm_timeout')), json.dumps(results.get('rr_engine')),
                      json.dumps(results.get('pump_exit')), json.dumps(results.get('ride_it')),
                      first_engine, first_result['exit_price'], gross_pnl,
                      first_result['hold_minutes'], first_result['exit_type'],
                      gross_pnl, net_pnl, mfe, mae, sid))
            else:
                # No engine fired — use last close
                last_close = candles[-1][4]
                pnl = (last_close / entry_price - 1) * 100 if d == 'LONG' else (entry_price / last_close - 1) * 100
                cur.execute("""
                    UPDATE shadow_trades SET closed=1, closed_at=?,
                        first_exit_engine='hold', first_exit_price=?, first_exit_pnl_pct=?,
                        first_exit_hold_minutes=?, first_exit_reason='no_exit',
                        gross_pnl_pct=?, net_pnl_pct=?
                    WHERE id=?
                """, (datetime.now(timezone.utc).isoformat(), last_close, pnl,
                      (candles[-1][0] - entry_ts) / 60, pnl, pnl - FEE_PCT - SLIPPAGE_PCT, sid))
            
            n_ok += 1
        
        conn.commit()
        log(f"close: {len(pending)} pending, {n_ok} closed")
        return n_ok
    finally:
        conn.close()


def report():
    """Generate reports: gate justification, exit engine A/B, signal quality."""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("SHADOW TRADER REPORT")
        log("═" * 60)
        
        # Summary
        total = cur.execute("SELECT COUNT(*) FROM shadow_trades").fetchone()[0]
        closed = cur.execute("SELECT COUNT(*) FROM shadow_trades WHERE closed=1").fetchone()[0]
        log(f"Total signals: {total} | Closed: {closed}")
        
        # Gate justification
        log("\n─── GATE JUSTIFICATION ───")
        rows = cur.execute("""
            SELECT gate_name, COUNT(*) as blocked,
                   SUM(CASE WHEN first_exit_pnl_pct > 0 THEN 1 ELSE 0 END) as would_win,
                   ROUND(AVG(net_pnl_pct), 2) as avg_pnl
            FROM shadow_trades
            WHERE gate_blocked=1 AND closed=1 AND gate_name IS NOT NULL
            GROUP BY gate_name ORDER BY blocked DESC LIMIT 10
        """).fetchall()
        for gate, blocked, wins, pnl in rows:
            wr = f"{wins/blocked*100:.0f}%" if blocked else "n/a"
            log(f"  {gate:30} blocked={blocked:5} would_win={wr:5} avg_pnl={pnl}")
        
        # Exit engine A/B
        log("\n─── EXIT ENGINE A/B ───")
        rows = cur.execute("""
            SELECT first_exit_engine, COUNT(*) as n,
                   ROUND(100.0*SUM(CASE WHEN first_exit_pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
                   ROUND(AVG(net_pnl_pct), 2) as avg_pnl,
                   ROUND(SUM(net_pnl_pct), 2) as total_pnl
            FROM shadow_trades
            WHERE closed=1 AND first_exit_engine IS NOT NULL
            GROUP BY first_exit_engine ORDER BY total_pnl DESC
        """).fetchall()
        for engine, n, wr, avg_pnl, total_pnl in rows:
            log(f"  {engine:25} n={n:5} WR={wr:5}% avg_pnl={avg_pnl:+.2f} total_pnl={total_pnl:+.2f}")
        
        # Signal quality by source
        log("\n─── SIGNAL QUALITY BY SOURCE (top 15) ───")
        rows = cur.execute("""
            SELECT source, COUNT(*) as n,
                   ROUND(100.0*SUM(CASE WHEN net_pnl_pct > 0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
                   ROUND(AVG(net_pnl_pct), 2) as avg_pnl
            FROM shadow_trades
            WHERE closed=1
            GROUP BY source HAVING COUNT(*) >= 5
            ORDER BY avg_pnl DESC LIMIT 15
        """).fetchall()
        for src, n, wr, avg_pnl in rows:
            log(f"  {src:30} n={n:5} WR={wr:5}% avg_pnl={avg_pnl:+.2f}")
        
        log("\n═" * 60)
    finally:
        conn.close()


def analyze_hml_thresholds():
    """Analyze HML threshold effectiveness (T directive 2026-10-20).

    Tests multiple HML thresholds to find the optimal CUT_LOSER_PNL setting.
    Simulates: what would happen if HML was at -3%, -4%, -5%, -6%, -8% account?
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("HML THRESHOLD ANALYSIS")
        log("═" * 60)
        
        # Current HML exits
        rows = cur.execute("""
            SELECT leverage_used, COUNT(*) n,
                   ROUND(AVG(net_pnl_pct),3) avg_net,
                   ROUND(AVG(first_exit_hold_minutes),0) avg_hold,
                   ROUND(AVG(mfe_pct),3) avg_mfe,
                   ROUND(AVG(mae_pct),3) avg_mae
            FROM shadow_trades 
            WHERE closed=1 AND first_exit_engine='hard_max'
            GROUP BY leverage_used ORDER BY n DESC
        """).fetchall()
        
        log("\n─── CURRENT HML EXITS BY LEVERAGE ───")
        for lev, n, avg_net, avg_hold, avg_mfe, avg_mae in rows:
            log(f"  lev={lev}: n={n}, avg_net={avg_net:+.3f}%, avg_hold={avg_hold:.0f}m, MFE={avg_mfe:+.3f}%, MAE={avg_mae:+.3f}%")
        
        # Simulate different thresholds
        log("\n─── THRESHOLD SIMULATION ───")
        log("(What if CUT_LOSER_PNL was different?)")
        log(f"  {'Threshold':>12} {'Account%':>10} {'Price%':>8} {'Would Cut':>10} {'Would Hold':>10} {'Est PnL':>10}")
        
        for account_pnl in [-3.0, -4.0, -5.0, -6.0, -8.0, -10.0]:
            for lev in [3, 5]:
                price_threshold = account_pnl / lev
                # Count HML exits that would still fire (hit threshold before recovery)
                # and those that would have been held (didn't hit threshold)
                result = cur.execute("""
                    SELECT 
                        SUM(CASE WHEN first_exit_pnl_pct <= ? THEN 1 ELSE 0 END) as would_cut,
                        SUM(CASE WHEN first_exit_pnl_pct > ? THEN 1 ELSE 0 END) as would_hold,
                        ROUND(AVG(CASE WHEN first_exit_pnl_pct > ? THEN net_pnl_pct END),3) as est_hold_pnl
                    FROM shadow_trades 
                    WHERE closed=1 AND first_exit_engine='hard_max' AND leverage_used=?
                """, (price_threshold, price_threshold, price_threshold, lev)).fetchone()
                
                if result and result[0]:
                    would_cut, would_hold, est_pnl = result
                    log(f"  {account_pnl:>8.1f}% {'lev='+str(lev):>8} {price_threshold:>7.2f}% {would_cut:>10} {would_hold:>10} {est_pnl if est_pnl else 'n/a':>10}")
        
        # Dead signals analysis
        log("\n" + "═" * 60)
        log("DEAD SIGNALS ANALYSIS (bought peak / wrong side)")
        log("═" * 60)
        
        log("\n─── WORST SIGNALS (n>=10, WR<35%) ───")
        log(f"  {'Source':35} {'Dir':5} {'n':>5} {'WR':>6} {'Avg':>8} {'MFE':>8} {'MAE':>8} {'Hold':>6}")
        rows = cur.execute("""
            SELECT source, direction, COUNT(*) n,
                   ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
                   ROUND(AVG(net_pnl_pct),3) avg_net,
                   ROUND(AVG(mfe_pct),3) avg_mfe,
                   ROUND(AVG(mae_pct),3) avg_mae,
                   ROUND(AVG(first_exit_hold_minutes),0) avg_hold
            FROM shadow_trades 
            WHERE closed=1
            GROUP BY source, direction 
            HAVING COUNT(*) >= 10 AND 100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*) < 35
            ORDER BY avg_net ASC
            LIMIT 15
        """).fetchall()
        for src, d, n, wr, avg_net, avg_mfe, avg_mae, avg_hold in rows:
            log(f"  {src:35} {d:5} {n:5} {wr:5.1f}% {avg_net:+.3f}% {avg_mfe:+.3f}% {avg_mae:+.3f}% {avg_hold:.0f}m")
        
        log("\n─── PEAK BUYERS (high MFE but negative outcome) ───")
        log("(Signals that spike up then crash down — bought the peak)")
        log(f"  {'Source':35} {'Dir':5} {'n':>5} {'WR':>6} {'Avg':>8} {'MFE':>8} {'MAE':>8} {'Giveback':>9}")
        rows = cur.execute("""
            SELECT source, direction, COUNT(*) n,
                   ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
                   ROUND(AVG(net_pnl_pct),3) avg_net,
                   ROUND(AVG(mfe_pct),3) avg_mfe,
                   ROUND(AVG(mae_pct),3) avg_mae,
                   ROUND(AVG(mfe_pct) - AVG(net_pnl_pct),3) giveback
            FROM shadow_trades 
            WHERE closed=1
            GROUP BY source, direction 
            HAVING COUNT(*) >= 10 AND AVG(mfe_pct) > 1.0 AND AVG(net_pnl_pct) < 0
            ORDER BY giveback DESC
            LIMIT 10
        """).fetchall()
        for src, d, n, wr, avg_net, avg_mfe, avg_mae, giveback in rows:
            log(f"  {src:35} {d:5} {n:5} {wr:5.1f}% {avg_net:+.3f}% {avg_mfe:+.3f}% {avg_mae:+.3f}% {giveback:+.3f}%")
        
        log("\n─── WRONG SIDE (high MAE, low MFE) ───")
        log("(Signals that immediately go against us — wrong side of trade)")
        log(f"  {'Source':35} {'Dir':5} {'n':>5} {'WR':>6} {'Avg':>8} {'MFE':>8} {'MAE':>8} {'MFE/MAE':>8}")
        rows = cur.execute("""
            SELECT source, direction, COUNT(*) n,
                   ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
                   ROUND(AVG(net_pnl_pct),3) avg_net,
                   ROUND(AVG(mfe_pct),3) avg_mfe,
                   ROUND(AVG(mae_pct),3) avg_mae,
                   ROUND(AVG(mfe_pct) / NULLIF(AVG(mae_pct), 0), 2) ratio
            FROM shadow_trades 
            WHERE closed=1
            GROUP BY source, direction 
            HAVING COUNT(*) >= 10 AND AVG(mfe_pct) < 1.0 AND AVG(mae_pct) < -2.0
            ORDER BY ratio ASC
            LIMIT 10
        """).fetchall()
        for src, d, n, wr, avg_net, avg_mfe, avg_mae, ratio in rows:
            log(f"  {src:35} {d:5} {n:5} {wr:5.1f}% {avg_net:+.3f}% {avg_mfe:+.3f}% {avg_mae:+.3f}% {ratio:.2f}")
        
        log("\n═" * 60)
    finally:
        conn.close()


def purge():
    """Delete records older than 90 days."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("DELETE FROM shadow_trades WHERE created_at < ?", (cutoff,))
        n = cur.rowcount
        conn.commit()
        log(f"purge: deleted {n} records older than 90 days")
    finally:
        conn.close()


def reclose_events():
    """Re-close slow engines (bug_hunter fix 2).

    close() marks rows closed=1 permanently on partial data. Once the
    backfill backlog drains (~3-4h), every new signal gets truncated
    slow-engine results. This re-closes rows where:
    - first_exit_engine='universal_hold' AND hold_minutes < 480 (truncated)
    - first_exit_engine='universal_hold' AND hold_minutes < 1440 (ride_it truncated)
    - first_exit_reason='unclosed_no_candles' (candles now available)
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Find rows that need re-closing
        pending = cur.execute("""
            SELECT id, token, direction, source, created_at, leverage_used, context
            FROM shadow_trades
            WHERE closed=1 AND (
                (first_exit_engine='universal_hold' AND first_exit_hold_minutes < 480)
                OR first_exit_reason='unclosed_no_candles'
            )
            AND created_at > datetime('now', '-7 days')
            LIMIT 500
        """).fetchall()
        
        if not pending:
            log('reclose: 0 pending')
            return 0
        
        n_ok = 0
        for sid, tok, d, src, created, lev, ctx_json in pending:
            try:
                entry_ts = calendar.timegm(datetime.strptime(created, '%Y-%m-%d %H:%M:%S').timetuple())
            except (ValueError, TypeError):
                continue
            
            # Load candles for full window (24h for ride_it)
            candles = _load_candles_window(tok, entry_ts, entry_ts + 86400)
            if not candles:
                continue  # still no candles
            
            entry_price = candles[0][1]
            ctx = json.loads(ctx_json) if ctx_json else {}
            atr_pct = ctx.get('atr_pct')
            vol_regime = ctx.get('vol_regime', 'UNKNOWN')
            leverage = lev or MAX_LEVERAGE
            
            # Re-simulate all 10 engines with full candle data
            results = {}
            results['atr'] = _simulate_atr_sl_tp(entry_price, d, candles, atr_pct)
            results['pm_trail'] = _simulate_pm_trail(entry_price, d, candles, src, vol_regime)
            results['hard_max'] = _simulate_hard_max_loss(entry_price, d, candles, leverage)
            results['cut_loser'] = _simulate_cut_loser(entry_price, d, candles, src)
            results['speed_stale'] = _simulate_speed_stale(entry_price, d, candles)
            results['universal_hold'] = _simulate_universal_hold(entry_price, d, candles, src)
            results['trail_arm_timeout'] = _simulate_trail_arm_timeout(entry_price, d, candles, src)
            results['pump_exit'] = _simulate_pump_exit(entry_price, d, candles, atr_pct)
            results['ride_it'] = _simulate_ride_it(entry_price, d, candles, atr_pct)
            results['rr_engine'] = _simulate_rr_engine(entry_price, d, candles, atr_pct)
            
            # Tie-break precedence (10 engines)
            _PRECEDENCE = {
                'hard_max': 1, 'cut_loser': 2, 'atr': 3, 'rr_engine': 4,
                'pump_exit': 5, 'ride_it': 6, 'speed_stale': 7,
                'trail_arm_timeout': 8, 'universal_hold': 9, 'pm_trail': 10,
            }
            fired = [(k, v) for k, v in results.items() if v and v.get('fired')]
            
            if fired:
                fired.sort(key=lambda x: (x[1].get('exit_ts', 0), _PRECEDENCE.get(x[0], 99)))
                first_engine, first_result = fired[0]
                gross_pnl = first_result['pnl_pct']
                net_pnl = gross_pnl - FEE_PCT - SLIPPAGE_PCT
                
                cur.execute("""
                    UPDATE shadow_trades SET
                        exit_atr_json=?, exit_pm_trail_json=?, exit_hard_max_json=?,
                        exit_cut_loser_json=?, exit_speed_stale_json=?, exit_universal_hold_json=?,
                        exit_trail_arm_timeout_json=?, exit_rr_engine_json=?,
                        exit_pump_exit_json=?, exit_ride_it_json=?,
                        first_exit_engine=?, first_exit_price=?, first_exit_pnl_pct=?,
                        first_exit_hold_minutes=?, first_exit_reason=?,
                        gross_pnl_pct=?, net_pnl_pct=?, updated_at=?
                    WHERE id=?
                """, (json.dumps(results.get('atr')), json.dumps(results.get('pm_trail')),
                      json.dumps(results.get('hard_max')), json.dumps(results.get('cut_loser')),
                      json.dumps(results.get('speed_stale')), json.dumps(results.get('universal_hold')),
                      json.dumps(results.get('trail_arm_timeout')), json.dumps(results.get('rr_engine')),
                      json.dumps(results.get('pump_exit')), json.dumps(results.get('ride_it')),
                      first_engine, first_result['exit_price'], gross_pnl,
                      first_result['hold_minutes'], first_result['exit_type'],
                      gross_pnl, net_pnl, datetime.now(timezone.utc).isoformat(), sid))
                n_ok += 1
        
        conn.commit()
        log(f"reclose: {len(pending)} pending, {n_ok} re-closed")
        return n_ok
    finally:
        conn.close()


def flip_test(signal_type_filter=None):
    """Flip test: simulate both original and flipped direction (T directive 1).

    For signals with low WR, test if flipping direction would be profitable.
    Simulates both directions on the same candles and compares outcomes.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("FLIP TEST — Original vs Flipped Direction")
        log("═" * 60)
        
        # Get signals to test
        if signal_type_filter:
            rows = cur.execute("""
                SELECT id, token, direction, signal_type, source, created_at, 
                       leverage_used, context, first_exit_pnl_pct
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE ?
                ORDER BY created_at DESC LIMIT 500
            """, (f'%{signal_type_filter}%',)).fetchall()
        else:
            # Default: test worst signals
            rows = cur.execute("""
                SELECT id, token, direction, signal_type, source, created_at,
                       leverage_used, context, first_exit_pnl_pct
                FROM shadow_trades 
                WHERE closed=1
                GROUP BY signal_type, direction
                HAVING COUNT(*) >= 10 AND AVG(net_pnl_pct) < -0.1
                LIMIT 10
            """).fetchall()
        
        if not rows:
            log("No signals to test")
            return
        
        # Group by signal_type
        by_type = {}
        for r in rows:
            key = (r[3], r[2])  # signal_type, direction
            if key not in by_type:
                by_type[key] = []
            by_type[key].append(r)
        
        for (sig_type, orig_dir), sig_rows in by_type.items():
            if len(sig_rows) < 5:
                continue
            
            log(f"\n─── {sig_type} {orig_dir} (n={len(sig_rows)}) ───")
            
            # Row indices: 0=id, 1=token, 2=direction, 3=signal_type, 4=source,
            # 5=created_at, 6=leverage_used, 7=context, 8=first_exit_pnl_pct
            orig_wins = sum(1 for r in sig_rows if r[8] and r[8] > 0)
            orig_total = sum(r[8] or 0 for r in sig_rows)
            orig_wr = orig_wins / len(sig_rows) * 100
            orig_avg = orig_total / len(sig_rows)
            
            # Simulate flipped direction
            flip_results = []
            for r in sig_rows:
                try:
                    entry_ts = calendar.timegm(datetime.strptime(r[5], '%Y-%m-%d %H:%M:%S').timetuple())
                except:
                    continue
                
                candles = _load_candles_window(r[1], entry_ts, entry_ts + 86400)
                if not candles:
                    continue
                
                entry_price = candles[0][1]
                ctx = json.loads(r[7]) if r[7] else {}
                atr_pct = ctx.get('atr_pct')
                leverage = r[6] or MAX_LEVERAGE
                
                # Flip direction
                flip_dir = 'SHORT' if orig_dir == 'LONG' else 'LONG'
                
                # Simulate with flipped direction
                result = _simulate_atr_sl_tp(entry_price, flip_dir, candles, atr_pct)
                if result:
                    flip_results.append(result['pnl_pct'])
            
            if flip_results:
                flip_wins = sum(1 for p in flip_results if p > 0)
                flip_total = sum(flip_results)
                flip_wr = flip_wins / len(flip_results) * 100
                flip_avg = flip_total / len(flip_results)
                
                log(f"  Original {orig_dir}: WR={orig_wr:.1f}% avg={orig_avg:+.3f}% total={orig_total:+.2f}%")
                log(f"  Flipped  {flip_dir}: WR={flip_wr:.1f}% avg={flip_avg:+.3f}% total={flip_total:+.2f}%")
                log(f"  Delta: WR={flip_wr-orig_wr:+.1f}% avg={flip_avg-orig_avg:+.3f}%")
                
                if flip_avg > orig_avg:
                    log(f"  ✅ FLIP IS BETTER by {flip_avg-orig_avg:+.3f}%")
                else:
                    log(f"  ❌ Original is better by {orig_avg-flip_avg:+.3f}%")
        
        log("\n═" * 60)
    finally:
        conn.close()


def analyze_exit_engines(signal_type_filter=None):
    """Compare exit engine outcomes for a signal type (T directive 2).

    Queries existing exit_*_json columns to see which engine would have
    been best for each signal.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("EXIT ENGINE COMPARISON")
        log("═" * 60)
        
        if signal_type_filter:
            rows = cur.execute("""
                SELECT exit_atr_json, exit_pm_trail_json, exit_hard_max_json,
                       exit_cut_loser_json, exit_speed_stale_json, exit_universal_hold_json,
                       exit_trail_arm_timeout_json
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE ?
            """, (f'%{signal_type_filter}%',)).fetchall()
        else:
            rows = cur.execute("""
                SELECT exit_atr_json, exit_pm_trail_json, exit_hard_max_json,
                       exit_cut_loser_json, exit_speed_stale_json, exit_universal_hold_json,
                       exit_trail_arm_timeout_json
                FROM shadow_trades WHERE closed=1
            """).fetchall()
        
        if not rows:
            log("No data")
            return
        
        log(f"\nTotal signals: {len(rows)}")
        
        # Parse and aggregate
        engine_stats = {}
        engine_names = ['atr', 'pm_trail', 'hard_max', 'cut_loser', 'speed_stale', 'universal_hold', 'trail_arm_timeout']
        
        for row in rows:
            for i, engine_name in enumerate(engine_names):
                if row[i]:
                    try:
                        data = json.loads(row[i])
                        if data and data.get('fired'):
                            if engine_name not in engine_stats:
                                engine_stats[engine_name] = {'n': 0, 'wins': 0, 'total_pnl': 0}
                            engine_stats[engine_name]['n'] += 1
                            pnl = data.get('pnl_pct', 0)
                            engine_stats[engine_name]['total_pnl'] += pnl
                            if pnl > 0:
                                engine_stats[engine_name]['wins'] += 1
                    except:
                        pass
        
        log(f"\n{'Engine':25} {'n':>5} {'WR':>6} {'Total':>8} {'Avg':>8}")
        log("-" * 60)
        for engine, stats in sorted(engine_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
            wr = stats['wins'] / stats['n'] * 100 if stats['n'] > 0 else 0
            avg = stats['total_pnl'] / stats['n'] if stats['n'] > 0 else 0
            log(f"  {engine:25} {stats['n']:5} {wr:5.1f}% {stats['total_pnl']:+8.2f}% {avg:+8.3f}%")
        
        log("\n═" * 60)
    finally:
        conn.close()


def analyze_hold_times(signal_type_filter=None):
    """Analyze hold time distribution for winners vs losers (T directive 3)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("HOLD TIME ANALYSIS")
        log("═" * 60)
        
        if signal_type_filter:
            rows = cur.execute("""
                SELECT direction, first_exit_pnl_pct, first_exit_hold_minutes
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE ? AND first_exit_hold_minutes IS NOT NULL
            """, (f'%{signal_type_filter}%',)).fetchall()
        else:
            rows = cur.execute("""
                SELECT direction, first_exit_pnl_pct, first_exit_hold_minutes
                FROM shadow_trades 
                WHERE closed=1 AND first_exit_hold_minutes IS NOT NULL
            """).fetchall()
        
        for d in ['LONG', 'SHORT']:
            dir_rows = [r for r in rows if r[0] == d]  # direction is index 0
            if not dir_rows:
                continue
            
            # Row indices: 0=direction, 1=first_exit_pnl_pct, 2=first_exit_hold_minutes
            winners = [r for r in dir_rows if r[1] and r[1] > 0]
            losers = [r for r in dir_rows if r[1] and r[1] <= 0]
            
            log(f"\n  {d}: n={len(dir_rows)}, winners={len(winners)}, losers={len(losers)}")
            
            if winners:
                avg_win = sum(r[2] for r in winners) / len(winners)
                log(f"    Winners avg hold: {avg_win:.0f} min ({avg_win/60:.1f}h)")
            
            if losers:
                avg_loss = sum(r[2] for r in losers) / len(losers)
                log(f"    Losers avg hold: {avg_loss:.0f} min ({avg_loss/60:.1f}h)")
            
            # Winner hold time distribution
            if winners:
                holds = sorted([r[2] for r in winners])
                log(f"    Winner hold distribution:")
                buckets = {'<30m': 0, '30-60m': 0, '1-2h': 0, '2-4h': 0, '4-8h': 0, '>8h': 0}
                for h in holds:
                    if h < 30: buckets['<30m'] += 1
                    elif h < 60: buckets['30-60m'] += 1
                    elif h < 120: buckets['1-2h'] += 1
                    elif h < 240: buckets['2-4h'] += 1
                    elif h < 480: buckets['4-8h'] += 1
                    else: buckets['>8h'] += 1
                for bucket, count in buckets.items():
                    pct = count / len(winners) * 100
                    log(f"      {bucket:8}: {count:3} ({pct:.0f}%)")
        
        log("\n═" * 60)
    finally:
        conn.close()


def sweep_arm_timeouts(signal_type_filter=None, direction_filter=None):
    """Sweep different arm timeout values to find the most profitable (T directive 3).

    Tests multiple timeout values: 30min, 45min, 60min, 90min, 120min, 180min.
    For each, simulates what would happen if the trade was closed at that time
    (if still open and pnl < activation threshold).
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("ARM TIMEOUT SWEEP")
        log("═" * 60)
        
        # Get pump-chain signals
        if signal_type_filter:
            rows = cur.execute("""
                SELECT id, token, direction, source, created_at, leverage_used, context,
                       first_exit_pnl_pct, first_exit_hold_minutes, first_exit_engine
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE ?
                ORDER BY created_at DESC LIMIT 500
            """, (f'%{signal_type_filter}%',)).fetchall()
        else:
            rows = cur.execute("""
                SELECT id, token, direction, source, created_at, leverage_used, context,
                       first_exit_pnl_pct, first_exit_hold_minutes, first_exit_engine
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE '%pump-chain%'
                ORDER BY created_at DESC LIMIT 500
            """).fetchall()
        
        if direction_filter:
            rows = [r for r in rows if r[2] == direction_filter]
        
        if not rows:
            log("No data")
            return
        
        log(f"\nTotal signals: {len(rows)}")
        
        # Test different timeout values
        timeouts = [30, 45, 60, 90, 120, 180]
        results = {t: {'n': 0, 'wins': 0, 'total_pnl': 0} for t in timeouts}
        
        for r in rows:
            try:
                entry_ts = calendar.timegm(datetime.strptime(r[4], '%Y-%m-%d %H:%M:%S').timetuple())
            except:
                continue
            
            candles = _load_candles_window(r[1], entry_ts, entry_ts + 86400)
            if not candles or len(candles) < 30:
                continue
            
            entry_price = candles[0][1]
            direction = r[2]
            
            for timeout_min in timeouts:
                # Find exit candle at timeout
                exit_ts = entry_ts + timeout_min * 60
                exit_candle = None
                for ts, o, h, l, c in candles:
                    if ts >= exit_ts:
                        exit_candle = (ts, o, h, l, c)
                        break
                
                if exit_candle:
                    exit_price = exit_candle[4]
                    pnl = (exit_price / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / exit_price - 1) * 100
                    pnl -= FEE_PCT + SLIPPAGE_PCT  # Apply costs
                    
                    results[timeout_min]['n'] += 1
                    results[timeout_min]['total_pnl'] += pnl
                    if pnl > 0:
                        results[timeout_min]['wins'] += 1
        
        # Report results
        log(f"\n{'Timeout':>10} {'n':>5} {'WR':>6} {'Total':>8} {'Avg':>8}")
        log("-" * 50)
        for timeout_min in timeouts:
            r = results[timeout_min]
            if r['n'] > 0:
                wr = r['wins'] / r['n'] * 100
                avg = r['total_pnl'] / r['n']
                log(f"  {timeout_min:>6}m {r['n']:5} {wr:5.1f}% {r['total_pnl']:+8.2f}% {avg:+8.3f}%")
        
        # Find best
        best = max(timeouts, key=lambda t: results[t]['total_pnl'] if results[t]['n'] > 0 else -999)
        if results[best]['n'] > 0:
            log(f"\n  🏆 Best timeout: {best}min (WR={results[best]['wins']/results[best]['n']*100:.1f}%, avg={results[best]['total_pnl']/results[best]['n']:+.3f}%)")
        
        log("\n═" * 60)
    finally:
        conn.close()


def sweep_hml_thresholds(signal_type_filter=None):
    """Sweep different HML thresholds to find the most profitable (T directive 1 correction).

    Tests: what if CUT_LOSER_PNL was -3%, -4%, -5%, -6%, -8%, -10%?
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("HML THRESHOLD SWEEP")
        log("═" * 60)
        
        # Get all closed signals
        rows = cur.execute("""
            SELECT id, token, direction, created_at, leverage_used, context,
                   exit_hard_max_json
            FROM shadow_trades 
            WHERE closed=1 AND exit_hard_max_json IS NOT NULL
            ORDER BY created_at DESC LIMIT 1000
        """).fetchall()
        
        if not rows:
            log("No HML data")
            return
        
        log(f"\nTotal signals with HML data: {len(rows)}")
        
        # Test different thresholds
        thresholds = [-3.0, -4.0, -5.0, -6.0, -8.0, -10.0]
        results = {t: {'n': 0, 'wins': 0, 'total_pnl': 0} for t in thresholds}
        
        for r in rows:
            try:
                entry_ts = calendar.timegm(datetime.strptime(r[3], '%Y-%m-%d %H:%M:%S').timetuple())
            except:
                continue
            
            candles = _load_candles_window(r[1], entry_ts, entry_ts + 86400)
            if not candles or len(candles) < 10:
                continue
            
            entry_price = candles[0][1]
            direction = r[2]
            leverage = r[4] or MAX_LEVERAGE
            
            for threshold in thresholds:
                # Simulate HML at this threshold
                price_threshold = threshold / leverage
                hml_price = entry_price * (1 + price_threshold/100) if direction == 'LONG' else entry_price * (1 - price_threshold/100)
                
                exited = False
                for ts, o, h, l, c in candles:
                    if direction == 'LONG' and l <= hml_price:
                        pnl = price_threshold - FEE_PCT - SLIPPAGE_PCT
                        results[threshold]['n'] += 1
                        results[threshold]['total_pnl'] += pnl
                        exited = True
                        break
                    elif direction == 'SHORT' and h >= hml_price:
                        pnl = price_threshold - FEE_PCT - SLIPPAGE_PCT
                        results[threshold]['n'] += 1
                        results[threshold]['total_pnl'] += pnl
                        exited = True
                        break
                
                if not exited:
                    # Trade didn't hit threshold — use last close
                    last_close = candles[-1][4]
                    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
                    pnl -= FEE_PCT + SLIPPAGE_PCT
                    results[threshold]['n'] += 1
                    results[threshold]['total_pnl'] += pnl
                    if pnl > 0:
                        results[threshold]['wins'] += 1
        
        # Report results
        log(f"\n{'Threshold':>10} {'Account%':>10} {'n':>5} {'WR':>6} {'Total':>8} {'Avg':>8}")
        log("-" * 60)
        for threshold in thresholds:
            r = results[threshold]
            if r['n'] > 0:
                wr = r['wins'] / r['n'] * 100
                avg = r['total_pnl'] / r['n']
                log(f"  {threshold:>8.1f}% {'lev=5':>8} {r['n']:5} {wr:5.1f}% {r['total_pnl']:+8.2f}% {avg:+8.3f}%")
        
        # Find best
        best = max(thresholds, key=lambda t: results[t]['total_pnl'] if results[t]['n'] > 0 else -999)
        if results[best]['n'] > 0:
            log(f"\n  🏆 Best threshold: {best}% account (WR={results[best]['wins']/results[best]['n']*100:.1f}%, avg={results[best]['total_pnl']/results[best]['n']:+.3f}%)")
        
        log("\n═" * 60)
    finally:
        conn.close()


def sweep_sl_levels(signal_type_filter=None, direction_filter=None):
    """Sweep different SL levels to find the most profitable (T directive 2026-10-21).

    T: "I have a feeling we're getting stopped out too soon. In shadow-mode
    can we simulate different SL levels to find the best, most profitable?"

    Tests: what if SL was 0.5%, 1.0%, 1.5%, 2.0%, 2.5%, 3.0% instead of current?
    For each SL, simulates: exit when price hits SL, else hold to end.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        
        log("═" * 60)
        log("SL LEVEL SWEEP")
        log("═" * 60)
        
        # Get signals
        if signal_type_filter:
            rows = cur.execute("""
                SELECT id, token, direction, source, created_at, context
                FROM shadow_trades 
                WHERE closed=1 AND signal_type LIKE ?
                ORDER BY created_at DESC LIMIT 500
            """, (f'%{signal_type_filter}%',)).fetchall()
        else:
            rows = cur.execute("""
                SELECT id, token, direction, source, created_at, context
                FROM shadow_trades 
                WHERE closed=1
                ORDER BY created_at DESC LIMIT 1000
            """).fetchall()
        
        if direction_filter:
            rows = [r for r in rows if r[2] == direction_filter]
        
        if not rows:
            log("No data")
            return
        
        log(f"\nTotal signals: {len(rows)}")
        
        # Test different SL levels
        # T directive: cap doesn't have to be 4%, could be 50% — find the best combos
        sl_levels = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0]
        results = {sl: {'n': 0, 'wins': 0, 'total_pnl': 0, 'stopped': 0} for sl in sl_levels}
        
        for r in rows:
            try:
                entry_ts = calendar.timegm(datetime.strptime(r[4], '%Y-%m-%d %H:%M:%S').timetuple())
            except:
                continue
            
            candles = _load_candles_window(r[1], entry_ts, entry_ts + 86400)
            if not candles or len(candles) < 10:
                continue
            
            entry_price = candles[0][1]
            direction = r[2]
            
            for sl_pct in sl_levels:
                # SL price
                sl_price = entry_price * (1 - sl_pct/100) if direction == 'LONG' else entry_price * (1 + sl_pct/100)
                
                # Simulate: exit when SL hit, else hold to end
                exited = False
                for ts, o, h, l, c in candles:
                    if direction == 'LONG' and l <= sl_price:
                        # Stopped out
                        pnl = -sl_pct - FEE_PCT - SLIPPAGE_PCT
                        results[sl_pct]['n'] += 1
                        results[sl_pct]['total_pnl'] += pnl
                        results[sl_pct]['stopped'] += 1
                        exited = True
                        break
                    elif direction == 'SHORT' and h >= sl_price:
                        pnl = -sl_pct - FEE_PCT - SLIPPAGE_PCT
                        results[sl_pct]['n'] += 1
                        results[sl_pct]['total_pnl'] += pnl
                        results[sl_pct]['stopped'] += 1
                        exited = True
                        break
                
                if not exited:
                    # Held to end
                    last_close = candles[-1][4]
                    pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
                    pnl -= FEE_PCT + SLIPPAGE_PCT
                    results[sl_pct]['n'] += 1
                    results[sl_pct]['total_pnl'] += pnl
                    if pnl > 0:
                        results[sl_pct]['wins'] += 1
        
        # Report results
        log(f"\n{'SL Level':>10} {'n':>5} {'WR':>6} {'Stopped':>8} {'Total':>8} {'Avg':>8}")
        log("-" * 60)
        for sl_pct in sl_levels:
            r = results[sl_pct]
            if r['n'] > 0:
                wr = r['wins'] / r['n'] * 100
                avg = r['total_pnl'] / r['n']
                stop_pct = r['stopped'] / r['n'] * 100
                log(f"  {sl_pct:>6.2f}% {r['n']:5} {wr:5.1f}% {stop_pct:7.0f}% {r['total_pnl']:+8.2f}% {avg:+8.3f}%")
        
        # Find best
        best = max(sl_levels, key=lambda sl: results[sl]['total_pnl'] if results[sl]['n'] > 0 else -999)
        if results[best]['n'] > 0:
            r = results[best]
            wr = r['wins'] / r['n'] * 100
            avg = r['total_pnl'] / r['n']
            log(f"\n  🏆 Best SL: {best}% (WR={wr:.1f}%, avg={avg:+.3f}%, stopped={r['stopped']}/{r['n']})")
        
        # Per-signal breakdown if signal_type_filter provided
        if signal_type_filter:
            log(f"\n--- Per-Signal SL Analysis for {signal_type_filter} ---")
            # Group by signal_type
            by_signal = {}
            for r in rows:
                st = r[3] or 'unknown'  # source is index 3
                if st not in by_signal:
                    by_signal[st] = []
                by_signal[st].append(r)
            
            for st, sig_rows in sorted(by_signal.items(), key=lambda x: -len(x[1])):
                if len(sig_rows) < 10:
                    continue
                
                # Quick analysis: find best SL for this signal
                best_sl = None
                best_pnl = -999
                for sl_pct in sl_levels:
                    total_pnl = 0
                    n = 0
                    for r in sig_rows:
                        try:
                            entry_ts = calendar.timegm(datetime.strptime(r[4], '%Y-%m-%d %H:%M:%S').timetuple())
                        except:
                            continue
                        candles = _load_candles_window(r[1], entry_ts, entry_ts + 86400)
                        if not candles or len(candles) < 10:
                            continue
                        entry_price = candles[0][1]
                        direction = r[2]
                        sl_price = entry_price * (1 - sl_pct/100) if direction == 'LONG' else entry_price * (1 + sl_pct/100)
                        
                        exited = False
                        for ts, o, h, l, c in candles:
                            if direction == 'LONG' and l <= sl_price:
                                total_pnl += -sl_pct - FEE_PCT - SLIPPAGE_PCT
                                n += 1
                                exited = True
                                break
                            elif direction == 'SHORT' and h >= sl_price:
                                total_pnl += -sl_pct - FEE_PCT - SLIPPAGE_PCT
                                n += 1
                                exited = True
                                break
                        
                        if not exited:
                            last_close = candles[-1][4]
                            pnl = (last_close / entry_price - 1) * 100 if direction == 'LONG' else (entry_price / last_close - 1) * 100
                            pnl -= FEE_PCT + SLIPPAGE_PCT
                            total_pnl += pnl
                            n += 1
                    
                    if n > 0 and total_pnl > best_pnl:
                        best_pnl = total_pnl
                        best_sl = sl_pct
                
                if best_sl:
                    log(f"  {st:35} n={len(sig_rows):4} best SL={best_sl:.2f}% (PnL={best_pnl:+.2f}%)")
        
        log("\n═" * 60)
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description='Shadow-Mode Paper Trading System')
    ap.add_argument('--record', action='store_true', help='Snapshot ALL signals')
    ap.add_argument('--close', action='store_true', help='Simulate 7 exit engines')
    ap.add_argument('--report', action='store_true', help='Generate reports')
    ap.add_argument('--reclose', action='store_true', help='Re-close slow engines')
    ap.add_argument('--purge', action='store_true', help='Delete >90 days')
    ap.add_argument('--analyze-hml', action='store_true', help='HML threshold + dead signals analysis')
    ap.add_argument('--flip-test', action='store_true', help='Test flipping signal direction')
    ap.add_argument('--flip-signal', type=str, help='Signal type to flip test')
    ap.add_argument('--analyze-exits', action='store_true', help='Compare exit engine outcomes')
    ap.add_argument('--exit-signal', type=str, help='Signal type for exit engine comparison')
    ap.add_argument('--analyze-hold', action='store_true', help='Hold time analysis')
    ap.add_argument('--hold-signal', type=str, help='Signal type for hold time analysis')
    ap.add_argument('--sweep-arm', action='store_true', help='Sweep arm timeout values')
    ap.add_argument('--sweep-signal', type=str, help='Signal type for arm timeout sweep')
    ap.add_argument('--sweep-dir', type=str, help='Direction filter for sweep')
    ap.add_argument('--sweep-hml', action='store_true', help='Sweep HML thresholds')
    ap.add_argument('--sweep-sl', action='store_true', help='Sweep SL levels')
    args = ap.parse_args()
    
    run_all = not (args.record or args.close or args.report or args.reclose or 
                   args.purge or args.analyze_hml or args.flip_test or 
                   args.analyze_exits or args.analyze_hold or args.sweep_arm or 
                   args.sweep_hml or args.sweep_sl)
    
    if run_all or args.record:
        record()
    if run_all or args.close:
        close_events()
    if args.reclose:
        reclose_events()
    if run_all or args.report:
        report()
    if args.analyze_hml:
        analyze_hml_thresholds()
    if args.flip_test:
        flip_test(args.flip_signal)
    if args.analyze_exits:
        analyze_exit_engines(args.exit_signal)
    if args.analyze_hold:
        analyze_hold_times(args.hold_signal)
    if args.sweep_arm:
        sweep_arm_timeouts(args.sweep_signal, args.sweep_dir)
    if args.sweep_hml:
        sweep_hml_thresholds()
    if args.sweep_sl:
        sweep_sl_levels(args.sweep_signal, args.sweep_dir)
    if args.purge:
        purge()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
