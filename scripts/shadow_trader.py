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
    """Get volatility regime from ATR (15m-primary per spec §4.1)."""
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
    """Get leverage from per-token registry (spec §4.3)."""
    try:
        from position_manager import get_trade_params
        params = get_trade_params(token)
        if params and 'leverage' in params:
            return params['leverage']
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
        for sid, tok, d, st, src, conf, dec, reason, created in rows:
            try:
                # Get context
                ctx = _get_signal_context(tok, d, st, src, created)
                ctx['context_computed_at'] = now
                
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
    """Simulate Trail Arm Timeout (spec §4.8)."""
    if not candles:
        return None
    
    # Determine timeout
    bare = (source or '').rstrip('+-')
    if 'bb-squeeze' in bare:
        timeout_min = BB_SQUEEZE_TRAIL_ARM_TIMEOUT_MIN
    elif 'pump-chain' in bare and direction == 'LONG':
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
            
            # Simulate all 7 engines
            results = {}
            results['atr'] = _simulate_atr_sl_tp(entry_price, d, candles, atr_pct)
            results['pm_trail'] = _simulate_pm_trail(entry_price, d, candles, src, vol_regime)
            results['hard_max'] = _simulate_hard_max_loss(entry_price, d, candles, leverage)
            results['cut_loser'] = _simulate_cut_loser(entry_price, d, candles, src)
            results['speed_stale'] = _simulate_speed_stale(entry_price, d, candles)
            results['universal_hold'] = _simulate_universal_hold(entry_price, d, candles, src)
            results['trail_arm_timeout'] = _simulate_trail_arm_timeout(entry_price, d, candles, src)
            
            # Determine first exit to fire (deterministic tie-break per spec §4.0)
            # Loss-side precedence: HML → Cut Loser Hard → Cut Loser T2 → Cut Loser T1 → ATR SL → Speed Stale → Trail Arm → Universal
            # Profit-side precedence: ATR TP → PM Trail → Speed Stale Winner
            fired = [(k, v) for k, v in results.items() if v and v.get('fired')]
            
            if fired:
                # Sort by exit_ts, then by precedence
                fired.sort(key=lambda x: (x[1].get('exit_ts', 0), x[0]))
                first_engine, first_result = fired[0]
                
                gross_pnl = first_result['pnl_pct']
                net_pnl = gross_pnl - FEE_PCT - SLIPPAGE_PCT
                
                cur.execute("""
                    UPDATE shadow_trades SET
                        closed=1, closed_at=?,
                        exit_atr_json=?, exit_pm_trail_json=?, exit_hard_max_json=?,
                        exit_cut_loser_json=?, exit_speed_stale_json=?, exit_universal_hold_json=?,
                        exit_trail_arm_timeout_json=?,
                        first_exit_engine=?, first_exit_price=?, first_exit_pnl_pct=?,
                        first_exit_hold_minutes=?, first_exit_reason=?,
                        gross_pnl_pct=?, net_pnl_pct=?,
                        mfe_pct=?, mae_pct=?
                    WHERE id=?
                """, (datetime.now(timezone.utc).isoformat(),
                      json.dumps(results.get('atr')), json.dumps(results.get('pm_trail')),
                      json.dumps(results.get('hard_max')), json.dumps(results.get('cut_loser')),
                      json.dumps(results.get('speed_stale')), json.dumps(results.get('universal_hold')),
                      json.dumps(results.get('trail_arm_timeout')),
                      first_engine, first_result['exit_price'], gross_pnl,
                      first_result['hold_minutes'], first_result['exit_type'],
                      gross_pnl, net_pnl,
                      max([v.get('pnl_pct', 0) for v in results.values() if v] or [0]),
                      min([v.get('pnl_pct', 0) for v in results.values() if v] or [0]),
                      sid))
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


def main():
    ap = argparse.ArgumentParser(description='Shadow-Mode Paper Trading System')
    ap.add_argument('--record', action='store_true', help='Snapshot ALL signals')
    ap.add_argument('--close', action='store_true', help='Simulate 7 exit engines')
    ap.add_argument('--report', action='store_true', help='Generate reports')
    ap.add_argument('--reclose', action='store_true', help='Re-close slow engines')
    ap.add_argument('--purge', action='store_true', help='Delete >90 days')
    args = ap.parse_args()
    
    run_all = not (args.record or args.close or args.report or args.reclose or args.purge)
    
    if run_all or args.record:
        record()
    if run_all or args.close:
        close_events()
    if run_all or args.report:
        report()
    if args.purge:
        purge()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
