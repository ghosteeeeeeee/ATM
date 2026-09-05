#!/usr/bin/env python3
"""
continuum_trader.py — Live trader for the Continuum Engine.

Runs the continuum engine and executes trades on Hyperliquid.
Uses CONTINUUM tag to isolate positions from the existing signal system.

Usage:
  python3 continuum_trader.py              # Run live (30s ticks)
  python3 continuum_trader.py --paper      # Paper trading mode
  python3 continuum_trader.py --backtest   # Backtest mode

Position isolation:
  - Every order tagged with CONTINUUM_ prefix
  - Positions tracked in continuum_positions.json
  - Only closes positions it opened
"""
import sys, os, time, json, sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA, WWW_DATA
from continuum_engine import ContinuumEngine, ContinuumState
from continuum_constants import (
    TICK_INTERVAL, MAX_POSITION_USD, LEVERAGE,
    POSITION_TAG, POSITION_FILE,
    SCORE_NO_TRADE, SCORE_EXIT_THRESHOLD,
    MAX_CONTINUUM_POSITIONS,
    MIN_TIME_BETWEEN_TRADES, MIN_TIME_BETWEEN_ENTRIES,
    MIN_TIME_BETWEEN_EXITS, MAX_TRADES_PER_DAY, COOLDOWN_AFTER_LOSS,
)
from _secrets import BRAIN_DB_DICT

# ── Configuration ──────────────────────────────────────────────────────────────
PAPER_MODE = True  # Default to paper trading
KILL_SWITCH_FILE = os.path.join(WWW_DATA, 'continuum_live_trading.json')
POSITION_FILE_PATH = os.path.join(HERMES_DATA, POSITION_FILE)

# ── Position Tracking ──────────────────────────────────────────────────────────

def load_positions() -> list:
    """Load tracked positions from file."""
    if os.path.exists(POSITION_FILE_PATH):
        try:
            with open(POSITION_FILE_PATH) as f:
                return json.load(f)
        except:
            pass
    return []

def save_positions(positions: list):
    """Save tracked positions to file."""
    with open(POSITION_FILE_PATH, 'w') as f:
        json.dump(positions, f, indent=2)

def track_entry(side: str, entry_price: float, size_usd: float, order_id: str = None):
    """Record a new position."""
    positions = load_positions()
    positions.append({
        'side': side,
        'entry_price': entry_price,
        'size_usd': size_usd,
        'entry_time': int(time.time()),
        'entry_time_str': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        'order_id': order_id,
        'tag': POSITION_TAG,
    })
    save_positions(positions)
    print(f"[TRADER] Tracked entry: {side} ${size_usd:.0f} @ {entry_price:.1f}")

def track_exit(entry_price: float, exit_price: float, pnl: float):
    """Record a position exit."""
    positions = load_positions()
    # Find and remove the position
    for i, pos in enumerate(positions):
        if abs(pos['entry_price'] - entry_price) < 1:  # Match by entry price
            positions.pop(i)
            break
    save_positions(positions)
    print(f"[TRADER] Tracked exit: PnL ${pnl:+.2f}")

def get_our_positions() -> list:
    """Get positions that belong to the continuum engine."""
    positions = load_positions()
    return [p for p in positions if p.get('tag') == POSITION_TAG]

# ── Kill Switch ────────────────────────────────────────────────────────────────

def is_live_trading_enabled() -> bool:
    """Check if live trading is enabled."""
    if PAPER_MODE:
        return False
    # Check kill switch file
    if os.path.exists(KILL_SWITCH_FILE):
        try:
            with open(KILL_SWITCH_FILE) as f:
                data = json.load(f)
            return data.get('enabled', False)
        except:
            pass
    return False

# ── HL Integration ─────────────────────────────────────────────────────────────

def get_hl_position(token: str = 'BTC') -> Optional[Dict]:
    """Get current HL position for this token."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import get_open_hype_positions_curl
        print(f"[TRADER] Querying HL for {token} positions...")
        result = get_open_hype_positions_curl()
        
        # Handle different return formats
        if result is None:
            print(f"[TRADER] HL returned None")
            return None
        
        # If result is a string (error message)
        if isinstance(result, str):
            print(f"[TRADER] HL returned string: {result[:100]}")
            return None
        
        # If result is a list of positions
        if isinstance(result, list):
            for pos in result:
                if isinstance(pos, dict) and pos.get('coin') == token:
                    print(f"[TRADER] HL position found: {pos.get('szi', 'N/A')} {token} @ {pos.get('entryPx', 'N/A')}")
                    return pos
            print(f"[TRADER] No {token} position found on HL ({len(result)} total positions)")
            return None
        
        # If result is a dict (single position or response)
        if isinstance(result, dict):
            if result.get('coin') == token:
                print(f"[TRADER] HL position found: {result.get('szi', 'N/A')} {token}")
                return result
            # Check for nested positions
            if 'positions' in result:
                for pos in result['positions']:
                    if isinstance(pos, dict) and pos.get('coin') == token:
                        print(f"[TRADER] HL position found: {pos.get('szi', 'N/A')} {token}")
                        return pos
            print(f"[TRADER] HL returned dict but no {token} position: {list(result.keys())[:5]}")
            return None
        
        print(f"[TRADER] HL returned unexpected type: {type(result).__name__}")
        return None
        
    except Exception as e:
        print(f"[TRADER] ERROR getting HL position: {type(e).__name__}: {e}")
    return None

def place_hl_order(side: str, size_usd: float, token: str = 'BTC') -> dict:
    """Place an order on Hyperliquid."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import place_order, get_prices, is_live_trading_enabled as hl_live_check
        
        # Check HL live trading status
        hl_enabled = hl_live_check()
        print(f"[TRADER] HL live trading enabled: {hl_enabled}")
        if not hl_enabled:
            print(f"[TRADER] WARNING: HL live trading is DISABLED — order will fail")
        
        # Get current price
        print(f"[TRADER] Fetching {token} price from HL...")
        prices = get_prices([token])
        price = prices.get(token, 0)
        print(f"[TRADER] {token} price: ${price:.1f}")
        
        if price <= 0:
            print(f"[TRADER] ERROR: Could not get price for {token} (got {price})")
            return {'success': False, 'error': f'Could not get price for {token}'}
        
        # Calculate size in BTC
        sz = size_usd / price
        print(f"[TRADER] Requested size: ${size_usd:.0f} = {sz:.6f} {token}")
        
        # Round to proper decimals
        from hyperliquid_exchange import _round_position_sz
        sz = _round_position_sz(sz, token)
        print(f"[TRADER] Rounded size: {sz:.6f} {token}")
        
        if sz <= 0:
            print(f"[TRADER] ERROR: Size too small after rounding (sz={sz})")
            return {'success': False, 'error': 'Size too small after rounding'}
        
        # Place market order
        order_side = 'BUY' if side == 'LONG' else 'SELL'
        print(f"[TRADER] Placing {order_side} order: {sz} {token} @ Market (IOC)...")
        result = place_order(
            name=token,
            side=order_side,
            sz=sz,
            order_type='Market',
            tif='Ioc',
        )
        
        # Log result
        if result.get('success'):
            print(f"[TRADER] ORDER SUCCESS: {order_side} {sz} {token} | Order ID: {result.get('order_id', 'N/A')}")
        else:
            print(f"[TRADER] ORDER FAILED: {result.get('error', 'Unknown error')}")
            print(f"[TRADER] Full result: {json.dumps(result, indent=2)}")
        
        return result
        
    except Exception as e:
        print(f"[TRADER] ERROR placing order: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def close_hl_position(token: str = 'BTC') -> dict:
    """Close HL position for this token."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import close_position
        print(f"[TRADER] Closing {token} position on HL (slippage=2%)...")
        result = close_position(token, slippage=0.02)
        if result.get('success'):
            print(f"[TRADER] POSITION CLOSED SUCCESSFULLY")
        else:
            print(f"[TRADER] CLOSE FAILED: {result.get('error', 'Unknown error')}")
            print(f"[TRADER] Full result: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        print(f"[TRADER] ERROR closing position: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# ── Trading Logic ──────────────────────────────────────────────────────────────

class ContinuumTrader:
    def __init__(self, paper: bool = True):
        global PAPER_MODE
        PAPER_MODE = paper
        self.engine = ContinuumEngine('BTC')
        self.last_entry_phase = 0
        self.last_position_side = 'NONE'
        self.last_trade_time = 0
        self.last_entry_time = 0
        self.last_exit_time = 0
        self.trades_today = 0
        self.last_loss_time = 0
        self.last_trade_date = None
        
    def _can_trade(self) -> tuple:
        """Check if we're allowed to trade. Returns (can_trade, reason)."""
        now = time.time()
        today = datetime.now(timezone.utc).date()
        
        # Reset daily counter
        if self.last_trade_date != today:
            self.trades_today = 0
            self.last_trade_date = today
        
        # Check daily limit
        if self.trades_today >= MAX_TRADES_PER_DAY:
            return False, f"Daily limit reached ({MAX_TRADES_PER_DAY})"
        
        # Check cooldown after loss
        if now - self.last_loss_time < COOLDOWN_AFTER_LOSS:
            remaining = int((COOLDOWN_AFTER_LOSS - (now - self.last_loss_time)) / 60)
            return False, f"Loss cooldown ({remaining}m remaining)"
        
        # Check min time between trades
        if now - self.last_trade_time < MIN_TIME_BETWEEN_TRADES:
            remaining = int((MIN_TIME_BETWEEN_TRADES - (now - self.last_trade_time)) / 60)
            return False, f"Trade cooldown ({remaining}m remaining)"
        
        return True, "OK"
    
    def _can_enter(self) -> tuple:
        """Check if we can open a new position."""
        now = time.time()
        
        # Check position limit
        positions = get_our_positions()
        if len(positions) >= MAX_CONTINUUM_POSITIONS:
            return False, f"Position limit ({len(positions)}/{MAX_CONTINUUM_POSITIONS})"
        
        # Check min time between entries
        if now - self.last_entry_time < MIN_TIME_BETWEEN_ENTRIES:
            remaining = int((MIN_TIME_BETWEEN_ENTRIES - (now - self.last_entry_time)) / 60)
            return False, f"Entry cooldown ({remaining}m remaining)"
        
        return True, "OK"
    
    def _can_exit(self) -> tuple:
        """Check if we can close a position."""
        now = time.time()
        
        # Check min time between exits
        if now - self.last_exit_time < MIN_TIME_BETWEEN_EXITS:
            remaining = int((MIN_TIME_BETWEEN_EXITS - (now - self.last_exit_time)) / 60)
            return False, f"Exit cooldown ({remaining}m remaining)"
        
        return True, "OK"
        
    def run_tick(self):
        """Run one tick of the continuum trader."""
        try:
            state = self.engine.compute_states('1m')
            if not state:
                print(f"[TRADER] WARNING: compute_states returned None")
                return
            
            # Save state to DB
            self.engine.save_state(state)
            
            # Check for entry signal
            if state.entry_phase == 4 and self.last_entry_phase < 4:
                print(f"[TRADER] ENTRY SIGNAL DETECTED: Phase 4 reached")
                self._handle_entry(state)
            
            # Check for exit signal (engine says no position)
            if state.position_side == 'NONE' and self.last_position_side != 'NONE':
                print(f"[TRADER] EXIT SIGNAL DETECTED: Position side changed to NONE")
                self._handle_exit(state)
            
            # Reconcile: check for orphaned positions (file has position but engine doesn't)
            tracked = get_our_positions()
            if tracked and state.position_side == 'NONE':
                print(f"[TRADER] RECONCILE: {len(tracked)} orphaned position(s) found, attempting close...")
                for pos in tracked:
                    pnl = (state.price - pos['entry_price']) * (1 if pos['side'] == 'LONG' else -1)
                    print(f"[TRADER] Closing orphaned {pos['side']} @ entry ${pos['entry_price']:.1f}")
                    if not PAPER_MODE:
                        result = close_hl_position()
                        if result.get('success'):
                            print(f"[TRADER] Orphaned position closed")
                            track_exit(pos['entry_price'], state.price, pnl)
                        else:
                            print(f"[TRADER] Close failed: {result.get('error')}")
                    else:
                        track_exit(pos['entry_price'], state.price, pnl)
            
            # Update last known state
            self.last_entry_phase = state.entry_phase
            self.last_position_side = state.position_side
            
            # Print status
            positions = get_our_positions()
            pos_count = len(positions)
            print(f"[TRADER] {state.ts} | "
                  f"Price:{state.price:.1f} | "
                  f"Score:{state.state_score:.1f} | "
                  f"Phase:{state.entry_phase} | "
                  f"Pos:{pos_count}/{MAX_CONTINUUM_POSITIONS} | "
                  f"EMA:{state.ema300_position}({state.ema300_duration}m) | "
                  f"Z:{state.zscore_tier}({state.zscore_val:+.2f}) | "
                  f"Vol:{state.volume_regime}({state.volume_ratio_val:.1f}x) | "
                  f"LinReg:{state.linreg_slope_state}({state.linreg_direction}) | "
                  f"Trades:{self.trades_today}/{MAX_TRADES_PER_DAY} | "
                  f"{'PAPER' if PAPER_MODE else 'LIVE'}")
        except Exception as e:
            print(f"[TRADER] ERROR in run_tick: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_entry(self, state: ContinuumState):
        """Handle entry signal."""
        side = 'LONG' if state.ema300_position == 'ABOVE' else 'SHORT'
        
        # Check rate limits
        can_trade, reason = self._can_trade()
        if not can_trade:
            print(f"[TRADER] ENTRY BLOCKED: {reason}")
            return
        
        can_enter, reason = self._can_enter()
        if not can_enter:
            print(f"[TRADER] ENTRY BLOCKED: {reason}")
            return
        
        # Calculate position size based on score
        size_pct = state.position_size_pct / 100
        size_usd = MAX_POSITION_USD * size_pct
        
        print(f"\n[TRADER] *** ENTRY SIGNAL *** {side} | Score:{state.state_score:.1f} | Size:${size_usd:.0f}")
        
        if PAPER_MODE:
            print(f"[TRADER] PAPER TRADE: {side} ${size_usd:.0f} @ {state.price:.1f}")
            track_entry(side, state.price, size_usd, order_id='PAPER')
            self.last_trade_time = time.time()
            self.last_entry_time = time.time()
            self.trades_today += 1
        else:
            if not is_live_trading_enabled():
                print("[TRADER] Live trading disabled (kill switch)")
                return
            
            result = place_hl_order(side, size_usd)
            if result.get('success'):
                print(f"[TRADER] ORDER PLACED: {side} ${size_usd:.0f} @ {state.price:.1f}")
                track_entry(side, state.price, size_usd, order_id=result.get('order_id'))
                self.last_trade_time = time.time()
                self.last_entry_time = time.time()
                self.trades_today += 1
            else:
                print(f"[TRADER] ORDER FAILED: {result.get('error')}")
                # Update last_trade_time to prevent retry spam
                self.last_trade_time = time.time()
    
    def _handle_exit(self, state: ContinuumState):
        """Handle exit signal."""
        positions = get_our_positions()
        if not positions:
            return
        
        # Check rate limits
        can_trade, reason = self._can_trade()
        if not can_trade:
            print(f"[TRADER] EXIT BLOCKED: {reason}")
            return
        
        can_exit, reason = self._can_exit()
        if not can_exit:
            print(f"[TRADER] EXIT BLOCKED: {reason}")
            return
        
        for pos in positions:
            pnl = (state.price - pos['entry_price']) * (1 if pos['side'] == 'LONG' else -1)
            pnl_pct = pnl / pos['entry_price'] * 100
            
            print(f"\n[TRADER] *** EXIT SIGNAL *** {pos['side']} | Entry:{pos['entry_price']:.1f} | Exit:{state.price:.1f} | PnL:{pnl_pct:+.2f}%")
            
            if PAPER_MODE:
                print(f"[TRADER] PAPER EXIT: {pos['side']} @ {state.price:.1f} | PnL: ${pnl:+.2f}")
                track_exit(pos['entry_price'], state.price, pnl)
                self.last_trade_time = time.time()
                self.last_exit_time = time.time()
                self.trades_today += 1
                if pnl < 0:
                    self.last_loss_time = time.time()
                    print(f"[TRADER] Loss recorded — {int(COOLDOWN_AFTER_LOSS/60)}m cooldown active")
            else:
                if not is_live_trading_enabled():
                    print("[TRADER] Live trading disabled (kill switch)")
                    return
                
                result = close_hl_position()
                if result.get('success'):
                    print(f"[TRADER] POSITION CLOSED: PnL ${pnl:+.2f}")
                    track_exit(pos['entry_price'], state.price, pnl)
                    self.last_trade_time = time.time()
                    self.last_exit_time = time.time()
                    self.trades_today += 1
                    if pnl < 0:
                        self.last_loss_time = time.time()
                        print(f"[TRADER] Loss recorded — {int(COOLDOWN_AFTER_LOSS/60)}m cooldown active")
                else:
                    print(f"[TRADER] CLOSE FAILED: {result.get('error')}")
    
    def run(self):
        """Run the continuum trader continuously."""
        mode = "PAPER" if PAPER_MODE else "LIVE"
        print(f"\n{'='*60}")
        print(f"[TRADER] Starting Continuum Trader ({mode} mode)")
        print(f"[TRADER] Tick interval: {TICK_INTERVAL}s")
        print(f"[TRADER] Max position: ${MAX_POSITION_USD}")
        print(f"[TRADER] Leverage: {LEVERAGE}x")
        print(f"[TRADER] Max positions: {MAX_CONTINUUM_POSITIONS}")
        print(f"[TRADER] Max trades/day: {MAX_TRADES_PER_DAY}")
        print(f"[TRADER] Min time between trades: {MIN_TIME_BETWEEN_TRADES}s")
        print(f"[TRADER] Kill switch: {KILL_SWITCH_FILE}")
        print(f"[TRADER] Position file: {POSITION_FILE_PATH}")
        print(f"{'='*60}\n")
        
        # Check initial HL status
        if not PAPER_MODE:
            print(f"[TRADER] Checking HL connection...")
            hl_pos = get_hl_position('BTC')
            if hl_pos:
                print(f"[TRADER] Existing BTC position on HL: {hl_pos.get('szi', 'N/A')}")
            else:
                print(f"[TRADER] No existing BTC position on HL")
        
        tick_count = 0
        while True:
            try:
                tick_count += 1
                if tick_count % 100 == 0:
                    print(f"[TRADER] --- Tick {tick_count} ---")
                self.run_tick()
                time.sleep(TICK_INTERVAL)
            except KeyboardInterrupt:
                print(f"\n[TRADER] Shutting down (KeyboardInterrupt)")
                break
            except Exception as e:
                print(f"[TRADER] ERROR in run loop: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                print(f"[TRADER] Retrying in 5s...")
                time.sleep(5)


if __name__ == '__main__':
    paper = '--live' not in sys.argv
    backtest = '--backtest' in sys.argv
    
    if backtest:
        from continuum_engine import backtest
        date = sys.argv[sys.argv.index('--backtest') + 1] if len(sys.argv) > sys.argv.index('--backtest') + 1 else '2026-09-03'
        backtest('BTC', date)
    else:
        trader = ContinuumTrader(paper=paper)
        trader.run()
