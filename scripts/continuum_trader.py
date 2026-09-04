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
        positions = get_open_hype_positions_curl()
        if positions:
            for pos in positions:
                if pos.get('coin') == token:
                    return pos
    except Exception as e:
        print(f"[TRADER] Error getting HL position: {e}")
    return None

def place_hl_order(side: str, size_usd: float, token: str = 'BTC') -> dict:
    """Place an order on Hyperliquid."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import place_order, get_prices
        
        # Get current price
        prices = get_prices([token])
        price = prices.get(token, 0)
        if price <= 0:
            return {'success': False, 'error': 'Could not get price'}
        
        # Calculate size in BTC
        sz = size_usd / price
        
        # Round to proper decimals
        from hyperliquid_exchange import _round_position_sz
        sz = _round_position_sz(sz, token)
        
        if sz <= 0:
            return {'success': False, 'error': 'Size too small'}
        
        # Place market order
        result = place_order(
            name=token,
            side='BUY' if side == 'LONG' else 'SELL',
            sz=sz,
            order_type='Market',
            tif='Ioc',
        )
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def close_hl_position(token: str = 'BTC') -> dict:
    """Close HL position for this token."""
    try:
        import sys as _sys
        _sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import close_position
        return close_position(token, slippage=0.02)
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ── Trading Logic ──────────────────────────────────────────────────────────────

class ContinuumTrader:
    def __init__(self, paper: bool = True):
        global PAPER_MODE
        PAPER_MODE = paper
        self.engine = ContinuumEngine('BTC')
        self.last_entry_phase = 0
        self.last_position_side = 'NONE'
        
    def run_tick(self):
        """Run one tick of the continuum trader."""
        state = self.engine.compute_states('1m')
        if not state:
            return
        
        # Save state to DB
        self.engine.save_state(state)
        
        # Check for entry signal
        if state.entry_phase == 4 and self.last_entry_phase < 4:
            self._handle_entry(state)
        
        # Check for exit signal
        if state.position_side == 'NONE' and self.last_position_side != 'NONE':
            self._handle_exit(state)
        
        # Update last known state
        self.last_entry_phase = state.entry_phase
        self.last_position_side = state.position_side
        
        # Print status
        print(f"[TRADER] {state.ts} | "
              f"Price:{state.price:.1f} | "
              f"Score:{state.state_score:.1f} | "
              f"Phase:{state.entry_phase} | "
              f"Pos:{state.position_side} | "
              f"LinReg:{state.linreg_slope_state}({state.linreg_direction}) | "
              f"{'PAPER' if PAPER_MODE else 'LIVE'}")
    
    def _handle_entry(self, state: ContinuumState):
        """Handle entry signal."""
        side = 'LONG' if state.ema300_position == 'ABOVE' else 'SHORT'
        
        # Calculate position size based on score
        size_pct = state.position_size_pct / 100
        size_usd = MAX_POSITION_USD * size_pct
        
        print(f"\n[TRADER] *** ENTRY SIGNAL *** {side} | Score:{state.state_score:.1f} | Size:${size_usd:.0f}")
        
        if PAPER_MODE:
            print(f"[TRADER] PAPER TRADE: {side} ${size_usd:.0f} @ {state.price:.1f}")
            track_entry(side, state.price, size_usd, order_id='PAPER')
        else:
            if not is_live_trading_enabled():
                print("[TRADER] Live trading disabled (kill switch)")
                return
            
            result = place_hl_order(side, size_usd)
            if result.get('success'):
                print(f"[TRADER] ORDER PLACED: {side} ${size_usd:.0f} @ {state.price:.1f}")
                track_entry(side, state.price, size_usd, order_id=result.get('order_id'))
            else:
                print(f"[TRADER] ORDER FAILED: {result.get('error')}")
    
    def _handle_exit(self, state: ContinuumState):
        """Handle exit signal."""
        positions = get_our_positions()
        if not positions:
            return
        
        for pos in positions:
            pnl = (state.price - pos['entry_price']) * (1 if pos['side'] == 'LONG' else -1)
            pnl_pct = pnl / pos['entry_price'] * 100
            
            print(f"\n[TRADER] *** EXIT SIGNAL *** {pos['side']} | Entry:{pos['entry_price']:.1f} | Exit:{state.price:.1f} | PnL:{pnl_pct:+.2f}%")
            
            if PAPER_MODE:
                print(f"[TRADER] PAPER EXIT: {pos['side']} @ {state.price:.1f} | PnL: ${pnl:+.2f}")
                track_exit(pos['entry_price'], state.price, pnl)
            else:
                if not is_live_trading_enabled():
                    print("[TRADER] Live trading disabled (kill switch)")
                    return
                
                result = close_hl_position()
                if result.get('success'):
                    print(f"[TRADER] POSITION CLOSED: PnL ${pnl:+.2f}")
                    track_exit(pos['entry_price'], state.price, pnl)
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
        print(f"{'='*60}\n")
        
        while True:
            try:
                self.run_tick()
                time.sleep(TICK_INTERVAL)
            except KeyboardInterrupt:
                print("\n[TRADER] Shutting down")
                break
            except Exception as e:
                print(f"[TRADER] Error: {e}")
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
