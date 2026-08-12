#!/usr/bin/env python3
"""
backtest_scaling.py — Test scaling strategies on AVNT price action.
Compares current fixed-stop approach vs book-based scaling.
"""
import sys
sys.path.insert(0, '/root/.hermes/scripts')

from paths import CANDLES_DB
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional

# ── Test Parameters ──────────────────────────────────────────────────────────
TOKEN = 'AVNT'
ATR_MULTIPLE = 1.5
SCALE_OUT_LEVELS = [1.5, 3.0]  # ATR multiples
SCALE_OUT_SIZES = [0.33, 0.33]
LATE_ENTRY_MAX_MOVE_PCT = 0.005  # 0.5%
LATE_ENTRY_LOOKBACK_MINUTES = 15

@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float

@dataclass
class TradeResult:
    entry_price: float
    exit_price: float
    pnl_pct: float
    pnl_usdt: float
    hold_minutes: int
    close_reason: str
    scale_outs: int

def get_candles(token: str, start_ts: int, end_ts: int) -> List[Candle]:
    """Get 5m candles for backtesting."""
    conn = sqlite3.connect(CANDLES_DB)
    c = conn.cursor()
    c.execute('''
        SELECT ts, open, high, low, close 
        FROM candles_5m 
        WHERE token = ? AND ts BETWEEN ? AND ?
        ORDER BY ts
    ''', (token, start_ts, end_ts))
    rows = c.fetchall()
    conn.close()
    return [Candle(r[0], r[1], r[2], r[3], r[4]) for r in rows]

def compute_atr(candles: List[Candle], period: int = 14) -> float:
    """Simple ATR calculation."""
    if len(candles) < period + 1:
        return 0.001  # fallback
    
    trs = []
    for i in range(1, len(candles)):
        high = candles[i].high
        low = candles[i].low
        prev_close = candles[i-1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    
    # Use last period TRs
    recent_trs = trs[-period:]
    return sum(recent_trs) / len(recent_trs)

def test_fixed_stop(candles: List[Candle], entry_idx: int, entry_price: float) -> TradeResult:
    """Test current fixed 0.60% trailing stop."""
    trail_dist = 0.006  # 0.60%
    highest = entry_price
    sl = entry_price * (1 - trail_dist)
    
    for i in range(entry_idx + 1, len(candles)):
        candle = candles[i]
        
        # Update highest and trail
        if candle.high > highest:
            highest = candle.high
            new_sl = highest * (1 - trail_dist)
            sl = max(sl, new_sl)  # one-way: only go up
        
        # Check stop hit
        if candle.low <= sl:
            exit_price = sl
            pnl_pct = (exit_price - entry_price) / entry_price
            hold_minutes = (candle.ts - candles[entry_idx].ts) // 60000
            return TradeResult(
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct,
                pnl_usdt=pnl_pct * 11.0,  # $11 position
                hold_minutes=hold_minutes,
                close_reason='atr_sl_hit',
                scale_outs=0
            )
    
    # Not stopped out — exit at last candle
    exit_price = candles[-1].close
    pnl_pct = (exit_price - entry_price) / entry_price
    hold_minutes = (candles[-1].ts - candles[entry_idx].ts) // 60000
    return TradeResult(
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_pct=pnl_pct,
        pnl_usdt=pnl_pct * 11.0,
        hold_minutes=hold_minutes,
        close_reason='open',
        scale_outs=0
    )

def test_atr_trail(candles: List[Candle], entry_idx: int, entry_price: float) -> TradeResult:
    """Test ATR-based trailing stop."""
    atr = compute_atr(candles[:entry_idx+1])
    trail_dist = ATR_MULTIPLE * atr / entry_price
    trail_dist = max(trail_dist, 0.01)  # minimum 1%
    trail_dist = min(trail_dist, 0.03)  # maximum 3%
    
    highest = entry_price
    sl = entry_price * (1 - trail_dist)
    
    for i in range(entry_idx + 1, len(candles)):
        candle = candles[i]
        
        # Update highest and trail
        if candle.high > highest:
            highest = candle.high
            new_sl = highest * (1 - trail_dist)
            sl = max(sl, new_sl)
        
        # Check stop hit
        if candle.low <= sl:
            exit_price = sl
            pnl_pct = (exit_price - entry_price) / entry_price
            hold_minutes = (candle.ts - candles[entry_idx].ts) // 60000
            return TradeResult(
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct,
                pnl_usdt=pnl_pct * 11.0,
                hold_minutes=hold_minutes,
                close_reason='atr_trail',
                scale_outs=0
            )
    
    exit_price = candles[-1].close
    pnl_pct = (exit_price - entry_price) / entry_price
    hold_minutes = (candles[-1].ts - candles[entry_idx].ts) // 60000
    return TradeResult(
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_pct=pnl_pct,
        pnl_usdt=pnl_pct * 11.0,
        hold_minutes=hold_minutes,
        close_reason='open',
        scale_outs=0
    )

def test_scale_out(candles: List[Candle], entry_idx: int, entry_price: float) -> TradeResult:
    """Test scale out with ATR trailing."""
    atr = compute_atr(candles[:entry_idx+1])
    
    tp1 = entry_price + SCALE_OUT_LEVELS[0] * atr
    tp2 = entry_price + SCALE_OUT_LEVELS[1] * atr
    
    trail_dist = ATR_MULTIPLE * atr / entry_price
    trail_dist = max(trail_dist, 0.01)
    trail_dist = min(trail_dist, 0.03)
    
    highest = entry_price
    sl = entry_price * (1 - trail_dist)
    remaining = 1.0
    total_pnl = 0.0
    scale_outs = 0
    tp1_hit = False
    tp2_hit = False
    
    for i in range(entry_idx + 1, len(candles)):
        candle = candles[i]
        
        # Update highest and trail
        if candle.high > highest:
            highest = candle.high
            new_sl = highest * (1 - trail_dist)
            sl = max(sl, new_sl)
        
        # Check TP1
        if not tp1_hit and candle.high >= tp1:
            # Close 33%
            profit_lock = (tp1 - entry_price) / entry_price * SCALE_OUT_SIZES[0]
            total_pnl += profit_lock
            remaining -= SCALE_OUT_SIZES[0]
            tp1_hit = True
            scale_outs += 1
            # Move SL to breakeven
            sl = max(sl, entry_price)
        
        # Check TP2
        if tp1_hit and not tp2_hit and candle.high >= tp2:
            # Close another 33%
            profit_lock = (tp2 - entry_price) / entry_price * SCALE_OUT_SIZES[1]
            total_pnl += profit_lock
            remaining -= SCALE_OUT_SIZES[1]
            tp2_hit = True
            scale_outs += 1
        
        # Check stop hit
        if candle.low <= sl:
            # Close remaining at SL
            if remaining > 0:
                pnl_on_remaining = (sl - entry_price) / entry_price * remaining
                total_pnl += pnl_on_remaining
            hold_minutes = (candle.ts - candles[entry_idx].ts) // 60000
            return TradeResult(
                entry_price=entry_price,
                exit_price=sl,
                pnl_pct=total_pnl,
                pnl_usdt=total_pnl * 11.0,
                hold_minutes=hold_minutes,
                close_reason='scale_out_trail',
                scale_outs=scale_outs
            )
    
    # Not stopped out
    if remaining > 0:
        pnl_on_remaining = (candles[-1].close - entry_price) / entry_price * remaining
        total_pnl += pnl_on_remaining
    hold_minutes = (candles[-1].ts - candles[entry_idx].ts) // 60000
    return TradeResult(
        entry_price=entry_price,
        exit_price=candles[-1].close,
        pnl_pct=total_pnl,
        pnl_usdt=total_pnl * 11.0,
        hold_minutes=hold_minutes,
        close_reason='open',
        scale_outs=scale_outs
    )

def check_late_entry(candles: List[Candle], signal_idx: int) -> bool:
    """Check if price already moved too much before signal."""
    if signal_idx < LATE_ENTRY_LOOKBACK_MINUTES // 5:
        return False  # not enough history
    
    lookback_idx = signal_idx - (LATE_ENTRY_LOOKBACK_MINUTES // 5)
    old_price = candles[lookback_idx].close
    new_price = candles[signal_idx].close
    
    if old_price <= 0:
        return False
    
    move_pct = abs(new_price - old_price) / old_price
    return move_pct > LATE_ENTRY_MAX_MOVE_PCT

def main():
    # AVNT trade period: Aug 12, 2026 01:00 - 04:30
    # Convert to timestamps (seconds, not ms)
    start_dt = datetime(2026, 8, 12, 1, 0)
    end_dt = datetime(2026, 8, 12, 4, 30)
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())
    
    candles = get_candles(TOKEN, start_ts, end_ts)
    if not candles:
        print("No candles found!")
        return
    
    print(f"\n{'='*60}")
    print(f"AVNT Backtest: {len(candles)} candles from {start_dt} to {end_dt}")
    print(f"{'='*60}\n")
    
    # Trade 1: Entry at 01:27 (idx ~6)
    trade1_idx = 6
    trade1_entry = 0.0941
    
    # Trade 2: Entry at 03:26 (idx ~30)
    trade2_idx = 30
    trade2_entry = 0.094306
    
    print("─" * 60)
    print("TRADE 1: Entry at 01:27, price 0.0941")
    print("─" * 60)
    
    r1_fixed = test_fixed_stop(candles, trade1_idx, trade1_entry)
    r1_atr = test_atr_trail(candles, trade1_idx, trade1_entry)
    r1_scale = test_scale_out(candles, trade1_idx, trade1_entry)
    
    print(f"  Fixed Stop (0.60%):  PnL={r1_fixed.pnl_pct*100:.2f}%  ${r1_fixed.pnl_usdt:.4f}  reason={r1_fixed.close_reason}")
    print(f"  ATR Trail (1.5x):    PnL={r1_atr.pnl_pct*100:.2f}%  ${r1_atr.pnl_usdt:.4f}  reason={r1_atr.close_reason}")
    print(f"  Scale Out:           PnL={r1_scale.pnl_pct*100:.2f}%  ${r1_scale.pnl_usdt:.4f}  reason={r1_scale.close_reason}  outs={r1_scale.scale_outs}")
    
    print()
    print("─" * 60)
    print("TRADE 2: Entry at 03:26, price 0.094306")
    print("─" * 60)
    
    # Check late entry
    is_late = check_late_entry(candles, trade2_idx)
    print(f"  Late entry filter: {'SKIP (price moved too much)' if is_late else 'PASS'}")
    
    r2_fixed = test_fixed_stop(candles, trade2_idx, trade2_entry)
    r2_atr = test_atr_trail(candles, trade2_idx, trade2_entry)
    r2_scale = test_scale_out(candles, trade2_idx, trade2_entry)
    
    print(f"  Fixed Stop (0.60%):  PnL={r2_fixed.pnl_pct*100:.2f}%  ${r2_fixed.pnl_usdt:.4f}  reason={r2_fixed.close_reason}")
    print(f"  ATR Trail (1.5x):    PnL={r2_atr.pnl_pct*100:.2f}%  ${r2_atr.pnl_usdt:.4f}  reason={r2_atr.close_reason}")
    print(f"  Scale Out:           PnL={r2_scale.pnl_pct*100:.2f}%  ${r2_scale.pnl_usdt:.4f}  reason={r2_scale.close_reason}  outs={r2_scale.scale_outs}")
    
    print()
    print("─" * 60)
    print("COMBINED RESULTS (Trade 1 + Trade 2)")
    print("─" * 60)
    
    # If late filter skips trade 2, only count trade 1
    if is_late:
        print("  With late entry filter: Trade 2 SKIPPED")
        print(f"    Total PnL (Fixed):   ${r1_fixed.pnl_usdt:.4f}")
        print(f"    Total PnL (ATR):     ${r1_atr.pnl_usdt:.4f}")
        print(f"    Total PnL (Scale):   ${r1_scale.pnl_usdt:.4f}")
    else:
        print(f"    Total PnL (Fixed):   ${r1_fixed.pnl_usdt + r2_fixed.pnl_usdt:.4f}")
        print(f"    Total PnL (ATR):     ${r1_atr.pnl_usdt + r2_atr.pnl_usdt:.4f}")
        print(f"    Total PnL (Scale):   ${r1_scale.pnl_usdt + r2_scale.pnl_usdt:.4f}")

if __name__ == '__main__':
    main()
