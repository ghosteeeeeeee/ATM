#!/usr/bin/env python3
"""Synthetic unit tests for the 3 new shadow_trader exit engines (commit bff34851).

Verifies: direction handling, trail SL calc, momentum exit, time exit,
phase logic, edge cases, and divergences vs live implementations
(position_manager.py pump exit, ride_it_exit.py, risk_reward_engine.py manage_exit).

Run: python3 brain/verdicts/exit_engines_synthetic_test_2026-10-21.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))

import shadow_trader as st

BASE_TS = 1_700_000_000
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'} — {name}" + (f" [{detail}]" if detail else ""))


def cnd(o, h, l, c, i=0):
    """(ts, o, h, l, c) tuple at minute i."""
    return (BASE_TS + i * 60, o, h, l, c)


print("\n=== T1: Pump Exit LONG — accel-floor inversion (expect trail 3x ATR, not 0.3% stop) ===")
# atr_pct=2.0 → intended trail = 6% from peak. Single 0.5% dip at candle 5.
cs = [cnd(100, 100, 100, 100, i) for i in range(5)]
cs.append(cnd(100, 100, 99.5, 100, 5))          # dip -0.5%
cs += [cnd(100, 100, 100, 100, i) for i in range(6, 10)]
r = st._simulate_pump_exit(100, 'LONG', cs, 2.0)
print(f"    result: {r}")
check("T1a fires as pump_exit_trail", r and r['fired'] and r['exit_type'] == 'pump_exit_trail')
check("T1b exit at accel floor (-0.30%) — INVERTED vs live", r and abs(r['pnl_pct'] - (-0.30)) < 0.01,
      f"pnl={r['pnl_pct']:.4f} (live would NOT fire: 6% trail untouched, no momentum, no 2h)")
check("T1c live-faithful behavior would be fired=False", r and r['fired'] is True,
      "documents divergence: live min()-clamps trail to entry-0.3% (cap), shadow max()-forces SL to entry-0.3%")

print("\n=== T2: Pump Exit SHORT — ceiling inversion ===")
cs = [cnd(100, 100, 100, 100, i) for i in range(3)]
cs.append(cnd(100, 100.4, 100, 100.2, 3))       # rally through entry+0.3%
r = st._simulate_pump_exit(100, 'SHORT', cs, 2.0)
print(f"    result: {r}")
check("T2a SHORT direction pnl correct", r and abs(r['pnl_pct'] - (100 / 100.3 - 1) * 100) < 0.01,
      f"pnl={r['pnl_pct']:.4f}")
check("T2b exits at entry+0.3% (intended trail = trough+6% → no exit)", r and r['fired'])

print("\n=== T3: Pump Exit time exit — exits WINNERS at 2h (live exits LOSERS: dead_money) ===")
# Steady climb 0.03%/min; trail (0.15% with atr=0.05) never touched, momentum all-positive.
cs = [cnd(100 + 0.03 * i, 100 + 0.03 * i, 100 + 0.03 * i, 100 + 0.03 * i, i) for i in range(130)]
r = st._simulate_pump_exit(100, 'LONG', cs, 0.05)
print(f"    result: {r}")
check("T3a fires pump_exit_time at hold>=2h", r and r['fired'] and r['exit_type'] == 'pump_exit_time',
      f"hold={r['hold_minutes']:.0f}m")
check("T3b fired only when pnl >= +2% (shadow semantics)", r and r['pnl_pct'] >= 2.0,
      f"pnl={r['pnl_pct']:+.2f} — live dead_money fires only when profit < 2% + velocity fading")

print("\n=== T4: Pump Exit momentum — correct window + reset ===")
def climb():
    out = [cnd(100, 100, 100, 100, 0)]
    for i in range(1, 41):
        out.append(cnd(100 + 0.1 * i, 100 + 0.1 * i, 100 + 0.1 * (i - 1), 100 + 0.1 * i, i))
    return out

# 4a: two consecutive -0.6% candles AFTER rally → fires momentum
cs = climb()
cs.append(cnd(104.0, 104.0, 103.38, 103.38, 41))   # -0.596%
cs.append(cnd(103.38, 103.38, 102.77, 102.77, 42)) # -0.590%
r = st._simulate_pump_exit(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T4a fires pump_exit_momentum on 2 consecutive qualifying candles", r and r['exit_type'] == 'pump_exit_momentum')
check("T4b exit at candle index 42 (hold 42m) — window correct, no off-by-one", r and abs(r['hold_minutes'] - 42) < 0.01,
      f"hold={r['hold_minutes']:.0f}")

# 4b: only ONE qualifying candle (truncated) → must NOT fire
cs2 = climb() + [cnd(104.0, 104.0, 103.38, 103.38, 41)]
r = st._simulate_pump_exit(100, 'LONG', cs2, 1.0)
check("T4c single negative candle does NOT fire", r and r['fired'] is False)

# 4c: big -3% single candle then flat → reset works, no momentum fire
cs3 = climb()
cs3.append(cnd(104.0, 104.0, 100.92, 100.92, 41))  # -2.96% single candle
cs3.append(cnd(100.92, 100.92, 100.92, 100.92, 42))
r = st._simulate_pump_exit(100, 'LONG', cs3, 1.0)
print(f"    result: {r}")
check("T4d momentum counter resets (1 big drop + flat ≠ 2 consecutive)", r and r['fired'] is False)

print("\n=== T5: Edge cases ===")
check("T5a empty candles → None (pump)", st._simulate_pump_exit(100, 'LONG', [], 1.0) is None)
check("T5b empty candles → None (ride_it)", st._simulate_ride_it(100, 'LONG', [], 1.0) is None)
check("T5c empty candles → None (rr)", st._simulate_rr_engine(100, 'LONG', [], 1.0) is None)
check("T5d atr_pct=None → None (all three)",
      st._simulate_pump_exit(100, 'LONG', [cnd(100, 100, 100, 100, 0)], None) is None
      and st._simulate_ride_it(100, 'LONG', [cnd(100, 100, 100, 100, 0)], None) is None
      and st._simulate_rr_engine(100, 'LONG', [cnd(100, 100, 100, 100, 0)], None) is None)
try:
    r = st._simulate_pump_exit(100, 'LONG', [cnd(100, 100, 100, 100, 0)], 1.0)
    check("T5e single candle no IndexError, fired=False", r and r['fired'] is False)
except Exception as e:
    check("T5e single candle no IndexError, fired=False", False, repr(e))
try:
    # prev_close=0 guarded by `if prev_c > 0` — should not crash
    cs = [cnd(100, 100, 100, 100, 0), cnd(100, 100, 100, 0, 1), cnd(0, 0, 0, 0, 2)]
    st._simulate_pump_exit(100, 'LONG', cs, 1.0)
    check("T5f zero close guarded, no crash", True)
except ZeroDivisionError:
    check("T5f zero close guarded, no crash", False, "ZeroDivisionError on entry_price=0 path")
except Exception as e:
    check("T5f zero close guarded, no crash", False, repr(e))
try:
    cs = [cnd(100, 100, 100, 100, i) for i in range(5)]
    st._simulate_pump_exit(0, 'LONG', cs, 1.0)
    check("T5g entry_price=0 safe", True)
except ZeroDivisionError:
    check("T5g entry_price=0 safe", False, "ZeroDivisionError (pump time-exit computes pnl every candle)")

print("\n=== T6: Ride It — momentum runs DURING phase 1 (live: phase 2 only) ===")
# atr=1.0 → sl=2.0% (floor 1.3 cap 2.5), tp=3.0%. Drop starts at minute 5 (< 120m).
cs = [cnd(100, 100, 100, 100, i) for i in range(5)]
cs.append(cnd(100, 100, 99.4, 99.4, 5))     # -0.6%
cs.append(cnd(99.4, 99.4, 98.81, 98.81, 6)) # -0.59%
r = st._simulate_ride_it(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T6a fires ride_it_momentum at hold=6m (phase 1)", r and r['exit_type'] == 'ride_it_momentum'
      and r['hold_minutes'] < 120, f"hold={r['hold_minutes']:.0f}m")
check("T6b fired at a LOSS (live gates momentum on profit > 1%)", r and r['pnl_pct'] < 0,
      f"pnl={r['pnl_pct']:+.2f} — live ride_it_exit.py:383 holds unless profit>1% and hold>=2h")

print("\n=== T7: Ride It — momentum in phase 2 at a loss (live would hold) ===")
cs = [cnd(99.5, 99.5, 99.5, 99.5, i) for i in range(120)]
cs.append(cnd(99.5, 99.5, 98.9, 98.9, 120))   # phase 2 starts (hold=120m)
cs.append(cnd(98.9, 98.9, 98.31, 98.31, 121)) # -0.6%
r = st._simulate_ride_it(99.5, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T7a phase-1 SL/TP not checked after 120m", r and r['exit_type'] == 'ride_it_momentum')
check("T7b fires at -1.2% loss (live: profit gate holds)", r and r['pnl_pct'] < 0, f"pnl={r['pnl_pct']:+.2f}")

print("\n=== T8: Ride It — phase-1 SL floor/cap + TP (TP does not exist live) ===")
# floor: atr=0.5 → sl_pct = max(1.0, 1.3) = 1.3
cs = [cnd(100, 100, 100, 100, 0), cnd(100, 100, 98.6, 99.5, 1)]
r = st._simulate_ride_it(100, 'LONG', cs, 0.5)
check("T8a floor 1.3% applied", r and r['exit_type'] == 'ride_it_sl' and abs(r['pnl_pct'] - (-1.3)) < 0.01,
      f"pnl={r['pnl_pct']:.3f}")
# cap: atr=2.0 → sl_pct = min(4.0, 2.5) = 2.5
cs = [cnd(100, 100, 100, 100, 0), cnd(100, 100, 97.4, 99.5, 1)]
r = st._simulate_ride_it(100, 'LONG', cs, 2.0)
check("T8b cap 2.5% applied", r and r['exit_type'] == 'ride_it_sl' and abs(r['pnl_pct'] - (-2.5)) < 0.01,
      f"pnl={r['pnl_pct']:.3f}")
# TP: atr=0.5 → tp = 1.5%
cs = [cnd(100, 100, 100, 100, 0), cnd(100, 101.6, 100.2, 101.6, 1)]
r = st._simulate_ride_it(100, 'LONG', cs, 0.5)
check("T8c ride_it_tp fires at 3x ATR (+1.5%)", r and r['exit_type'] == 'ride_it_tp' and abs(r['pnl_pct'] - 1.5) < 0.01,
      "DIVERGENCE: RIDE_IT_TP_PHASE1_MULT imported but never used in ride_it_exit.py — live has NO TP")

print("\n=== T9: Ride It — max hold at 1440m ===")
cs = [cnd(100, 100, 100, 100, i) for i in range(1441)]
r = st._simulate_ride_it(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T9a ride_it_max_hold at exactly 1440m", r and r['exit_type'] == 'ride_it_max_hold'
      and abs(r['hold_minutes'] - 1440) < 0.01, f"hold={r['hold_minutes']:.0f}")

print("\n=== T10: Ride It — trail activates during PHASE 1 (live: phase 2 only) ===")
# profit reaches +2.1% at minute 60 (inside phase 1), then drops → shadow trail-fires inside phase 1
cs = []
for i in range(61):
    p = 100 + 0.035 * i           # +2.1% at i=60 → trail_active flips on during phase 1
    cs.append(cnd(p, p, p - 0.01, p, i))
# peak 102.1 → trail = 102.1*0.988 = 100.875; candle 61 wicks to 100.5
cs.append(cnd(102.1, 102.1, 100.5, 100.6, 61))
r = st._simulate_ride_it(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T10 trail fires at hold=61m (phase 1) once pnl>=2%", r and r['exit_type'] == 'ride_it_trail'
      and r['hold_minutes'] < 120, f"hold={r['hold_minutes']:.0f}m pnl={r['pnl_pct']:+.2f} — live phase 1 has NO trailing")

print("\n=== T11: RR engine — missing ATR_SL_MIN_ACCEL cap (live caps trail at entry-0.3%) ===")
# atr=1.0 → sl=0.8%, tp=1.6%, trail=0.6%. Rally to 100.4 then pullback to 99.75.
cs = [cnd(100, 100, 100, 100, 0),
      cnd(100, 100.4, 100.0, 100.4, 1),
      cnd(100.4, 100.4, 99.75, 99.8, 2)]
r = st._simulate_rr_engine(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T11a shadow exits at SL ABOVE entry-0.3% (99.7)", r and r['fired'] and r['exit_price'] > 99.7,
      f"exit={r['exit_price']:.4f} pnl={r['pnl_pct']:+.4f} — live manage_exit:1355 clamps trail to 99.7 → NO exit")
check("T11b mislabeled: trail-caused exit reported as rr_sl_hit", r and r['exit_type'] == 'rr_sl_hit',
      "exit_type only distinguishes rr_trail_hit when SL > entry (in profit)")

print("\n=== T12: RR engine — TP exists in shadow, NOT in live manage_exit ===")
cs = [cnd(100, 100, 100, 100, 0),
      cnd(101.15, 101.7, 101.2, 101.7, 1)]
r = st._simulate_rr_engine(100, 'LONG', cs, 1.0)
print(f"    result: {r}")
check("T12 rr_tp_hit fires at 1.6x ATR", r and r['exit_type'] == 'rr_tp_hit' and abs(r['pnl_pct'] - 1.6) < 0.02,
      "DIVERGENCE: risk_reward_engine Rule 2 (TP) REMOVED — live RR has no fixed TP")

print("\n=== T13: RR engine — SHORT direction ===")
cs = [cnd(100, 100, 100, 100, 0),
      cnd(100, 100.9, 100.0, 100.5, 1)]
r = st._simulate_rr_engine(100, 'SHORT', cs, 1.0)
print(f"    result: {r}")
check("T13a SHORT SL above entry, pnl formula correct",
      r and r['exit_price'] >= 100 and abs(r['pnl_pct'] - (100 / 100.6 - 1) * 100) < 0.01,
      f"exit={r['exit_price']:.4f} pnl={r['pnl_pct']:+.4f}")

print("\n=== T14: RR engine — SL floor/cap absent (live: min(ATR_SL_MIN=1.5%, 2xATR) floor, 2.5% cap) ===")
# atr=0.4 → shadow: sl=0.32%, trail=0.24% → effective SL 99.76 (-0.24%)
# live: floor = min(1.5%, 2*0.4%=0.8%) = 0.8% → SL = 99.2 → low of 99.6 does NOT exit
cs = [cnd(100, 100, 100, 100, 0), cnd(100, 100, 99.6, 99.9, 1)]
r = st._simulate_rr_engine(100, 'LONG', cs, 0.4)
print(f"    result: {r}")
check("T14 shadow exits at -0.24% (live would HOLD at -0.8% SL)", r and r['fired']
      and abs(r['pnl_pct'] - (-0.24)) < 0.01,
      "shadow RR has no ATR_SL_MIN floor — low-ATR tokens stop out on noise")

print("\n" + "=" * 60)
print(f"TOTAL: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print(f"  - {f}")
sys.exit(1 if FAIL else 0)
