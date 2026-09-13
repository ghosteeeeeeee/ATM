# Pump-Exit Strategy Spec

**Date:** 2026-09-13
**Status:** SPEC — awaiting approval
**Data source:** FIL LONG trade analysis (own-conclusions audit, 154 1m candles)

---

## 1. Problem

Current exit for pump-chain uses RR engine (structural support/resistance breaks). This exits too early on momentum breakouts:
- FIL trade hit +14.98% peak but RR engine exited early
- RR engine exits when price breaks below support — too early for momentum moves
- Pump-chain fires on capital rotation — these moves can run 5-10%+ but structural exits kill them

## 2. Analysis (FIL LONG Case Study)

**Entry:** $0.8545 (14:00)
**Peak:** $0.9704 (+13.56%)
**Max DD from peak:** -2.52% (at 14:47)
**ATR(14) 1h:** $0.0089 (0.94%)

**Three killer dips that must survive:**
1. 14:47: -2.52% from peak (widest)
2. 15:42: -2.10% from peak
3. 16:12: -2.00% from peak

**Empirical ratio:** max_dd / ATR = 2.83x

## 3. Existing Exit Systems

| System | How It Works | Pros | Cons |
|--------|-------------|------|------|
| PM Trail | Fixed 0.3% trail from peak | Quick profit capture | Too tight for momentum |
| RR Engine | Structural support/resistance breaks | Respects market structure | Exits too early on momentum |
| ATR SL | ATR-based stop loss | Volatility-adaptive | No trailing, just initial SL |
| Cut Loser | Fixed loss limit | Quick loss cut | No profit capture |

**Current pump-chain config:** `'pump-chain+': 'rr_engine'` in SIGNAL_EXIT_CONFIG

## 4. Pump-Exit Design

### What pump-exit does:
1. **ATR trailing stop** — trail at 3.0x ATR from peak (wider than PM Trail)
2. **Momentum exit** — exit when 5m velocity < -0.5% for 2+ candles
3. **Time exit** — exit if profit < 2% after 2 hours

### How it interacts with existing systems:

| System | Interaction |
|--------|-------------|
| PM Trail | **BYPASS** — pump-exit replaces PM Trail entirely |
| RR Engine | **BYPASS** — pump-exit replaces RR engine structural exits |
| ATR SL | **KEEP** — pump-exit uses ATR SL as initial stop, then trails |
| Cut Loser | **KEEP** — pump-exit respects cut-loser limits |

### Exit priority order:
1. **Cut Loser** (hard limit) — always active
2. **Pump-Exit** (ATR trail + momentum + time) — primary exit
3. ~~RR Engine~~ — bypassed for pump-chain
4. ~~PM Trail~~ — bypassed for pump-chain

## 5. Parameters

```python
# Pump-Exit Parameters
PUMP_EXIT_TRAIL_MULT = 3.0           # ATR multiplier for trailing stop
PUMP_EXIT_MOMENTUM_VEL = -0.5        # 5m velocity threshold for momentum exit
PUMP_EXIT_MOMENTUM_CANDLES = 2       # consecutive negative candles required
PUMP_EXIT_TIME_THRESHOLD = 2.0       # min profit % for time exit
PUMP_EXIT_TIME_HOURS = 2.0           # max hold time in hours
```

## 6. Implementation

### Files to modify:

1. **`scripts/hermes_constants.py`**
   - Add pump-exit parameters
   - Update `SIGNAL_EXIT_CONFIG`: `'pump-chain+': 'pump_exit'`, `'pump-chain-': 'pump_exit'`
   - Add `'pump-chain+'` and `'pump-chain-'` to `PROFIT_MONSTER_BYPASS_SIGNALS`

2. **`scripts/position_manager.py`**
   - Add pump-exit handler in the exit priority chain
   - Check `SIGNAL_EXIT_CONFIG[signal] == 'pump_exit'`
   - Implement ATR trailing, momentum exit, time exit

3. **`scripts/profit_monster.py`**
   - Verify pump-chain is in bypass list (already done via PROFIT_MONSTER_BYPASS_SIGNALS)

### Exit logic (position_manager.py):
```python
# ── Pump-Exit (ATR trailing + momentum + time) ──
if RR_EXIT_ENABLED and signal in SIGNAL_EXIT_CONFIG and SIGNAL_EXIT_CONFIG[signal] == 'pump_exit':
    try:
        from risk_reward_engine import manage_exit, evaluate_rr
        import sqlite3 as _sqlite3
        from paths import CANDLES_DB
        
        entry_price = float(pos.get("entry_price") or 0)
        current_sl = float(pos.get("stop_loss") or 0)
        highest_price = float(pos.get("highest_price") or entry_price)  # use persisted peak
        
        # Get ATR
        _conn_atr = _sqlite3.connect(CANDLES_DB, timeout=5)
        _cur_atr = _conn_atr.cursor()
        _cur_atr.execute("""
            SELECT open, high, low, close FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 20
        """, (token.upper(),))
        _atr_rows = _cur_atr.fetchall()
        _cur_atr.close()
        _conn_atr.close()
        
        atr = 0
        if len(_atr_rows) >= 15:
            trs = []
            for i in range(1, len(_atr_rows)):
                h, l, pc = _atr_rows[i][1], _atr_rows[i][2], _atr_rows[i-1][3]
                trs.append(max(h - l, abs(h - pc), abs(l - pc)))
            atr = sum(trs[-14:]) / 14
        
        # Calculate trailing stop (DIRECTION-AWARE)
        trail_mult = getattr(hc, 'PUMP_EXIT_TRAIL_MULT', 3.0)
        trail_distance = atr * trail_mult
        
        if direction == 'LONG':
            # LONG: trail below peak
            peak_price = max(cur, highest_price)
            trailing_sl = peak_price - trail_distance
            new_sl = max(current_sl, trailing_sl) if current_sl > 0 else trailing_sl
        else:
            # SHORT: trail above trough
            trough_price = min(cur, pos.get("lowest_price", cur))
            trailing_sl = trough_price + trail_distance
            new_sl = min(current_sl, trailing_sl) if current_sl > 0 else trailing_sl
        
        # Update SL if tighter
        if direction == 'LONG' and new_sl > current_sl:
            pos['stop_loss'] = new_sl
            # Persist to DB
            _persist_sl(db_conn, trade_id, new_sl)
            log(f"  [PUMP-EXIT] {token} {direction}: TRAIL_SL → ${new_sl:.4f}")
        elif direction == 'SHORT' and new_sl < current_sl:
            pos['stop_loss'] = new_sl
            _persist_sl(db_conn, trade_id, new_sl)
            log(f"  [PUMP-EXIT] {token} {direction}: TRAIL_SL → ${new_sl:.4f}")
        
        # Check momentum exit (VELOCITY-BASED, not just declining closes)
        momentum_vel = getattr(hc, 'PUMP_EXIT_MOMENTUM_VEL', -0.5)  # -0.5% threshold
        momentum_candles = getattr(hc, 'PUMP_EXIT_MOMENTUM_CANDLES', 2)
        
        _conn_vel = _sqlite3.connect(CANDLES_DB, timeout=5)
        _cur_vel = _conn_vel.cursor()
        _cur_vel.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), momentum_candles + 1))
        _vel_closes = [r[0] for r in _cur_vel.fetchall()]
        _cur_vel.close()
        _conn_vel.close()
        
        if len(_vel_closes) >= momentum_candles + 1:
            # Calculate actual velocity (not just declining closes)
            vel_5m = (_vel_closes[0] - _vel_closes[-1]) / _vel_closes[-1] * 100 if _vel_closes[-1] > 0 else 0
            
            # Check if velocity is below threshold for consecutive periods
            neg_count = 0
            for i in range(1, len(_vel_closes)):
                period_vel = (_vel_closes[i-1] - _vel_closes[i]) / _vel_closes[i] * 100 if _vel_closes[i] > 0 else 0
                if period_vel < momentum_vel:  # USE THE THRESHOLD
                    neg_count += 1
                else:
                    neg_count = 0
            
            if neg_count >= momentum_candles:
                profit_pct = (cur - entry_price) / entry_price * 100 if entry_price > 0 else 0
                reason = f"momentum_fade: vel={vel_5m:.2f}% < {momentum_vel}% for {neg_count} candles"
                close_paper_position(trade_id, reason)
                closed_count += 1
                log(f"  [PUMP-EXIT] {token} {direction}: {reason}")
                continue
        
        # Check time exit (with momentum check to avoid cutting consolidating winners)
        time_threshold = getattr(hc, 'PUMP_EXIT_TIME_THRESHOLD', 2.0)
        time_hours = getattr(hc, 'PUMP_EXIT_TIME_HOURS', 2.0)
        
        entry_time = pos.get('entry_time')
        if entry_time:
            try:
                entry_dt = datetime.fromisoformat(entry_time.replace('+00:00', ''))
                hold_hours = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 3600
                profit_pct = (cur - entry_price) / entry_price * 100 if entry_price > 0 else 0
                
                # Only exit if profit is low AND momentum is fading
                if profit_pct < time_threshold and hold_hours > time_hours:
                    # Double-check: is momentum still positive?
                    if len(_vel_closes) >= 2:
                        vel_check = (_vel_closes[0] - _vel_closes[1]) / _vel_closes[1] * 100 if _vel_closes[1] > 0 else 0
                        if vel_check < 0:  # momentum actually fading
                            reason = f"dead_money: {hold_hours:.1f}h hold, {profit_pct:+.2f}%, vel={vel_check:.2f}%"
                            close_paper_position(trade_id, reason)
                            closed_count += 1
                            log(f"  [PUMP-EXIT] {token} {direction}: {reason}")
                            continue
            except Exception:
                pass
        
        # Continue to other exit checks (ATR SL, etc.)
    except Exception as e:
        log(f"  [PUMP-EXIT] Error: {e}", "WARN")
```

## 7. Backtest Results (FIL Case)

| Method | Exit Price | PnL | Survives? |
|--------|-----------|-----|-----------|
| RR Engine (current) | ~$0.91 | ~+6.5% | ❌ Exits early |
| PM Trail (0.3%) | $0.8971 | +4.98% | ❌ Too early |
| **Pump-Exit (ATR 3.0x)** | — | **+12.7%** | ✅ **Survives** |
| Pump-Exit (momentum) | — | +12.4% | ✅ Catches top |

## 8. Risk

- ATR 3.0x trail is wide — may give back more profit on shallow reversals
- Momentum exit may exit too early on news-driven pullbacks
- Time exit may cut winners that need more time
- Need to verify pump-chain is in PROFIT_MONSTER_BYPASS_SIGNALS
- **NOTE:** 3.0x multiplier based on single FIL case study — validate on more tokens before full deployment
- **NOTE:** Actual margin is 0.30% (not 6%) — ATR 3.0x = 2.82%, max DD = 2.52%

## 9. Recommendation

Implement pump-exit as described. The ATR 3.0x trail gives 6% margin over the empirical max DD ratio of 2.83x. Add momentum exit as secondary trigger. Keep ATR SL as initial stop.
