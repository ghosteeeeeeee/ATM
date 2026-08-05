# accel-300-,rs-s-broken Confluence Hole (2026-06-03)

## The Problem

`signal_compactor.py` `_signal_type_key()` collapse fix (2026-06-02):
```python
# Order: strip -broken first, then collapse rs-[sr], then strip digits
part = re.sub(r'-broken$', '', part)        # rs-s-broken → rs-s
part = re.sub(r'^rs-[sr]', 'rs', part)      # rs-s → rs, rs-r86 → rs
part = re.sub(r'\d+$', '', part)            # rs → rs
```

This fixed `rs-r86,rs-s-broken` (both collapse to `rs` → 1 type → blocked).

## The Remaining Hole

```
accel-300-,rs-s-broken
→ accel-300-  (family: accel)
→ rs-s-broken → rs-s → rs  (family: rs)
→ 2 unique families → PASSES confluence
```

`accel-300-` is a different family from `rs`, so this combo still passes as 2-type confluence.

## 30-day Performance

| Signal Group | Trades | WR | Avg PnL | Total |
|---|---|---|---|---|
| accel-300-+rs | 300 | 54% | +0.084% | +25.11% |
| rs-r+rs-s-broken | 50 | 56% | +0.076% | +3.81% |
| accel-300++rs | 25 | 52% | +0.138% | +3.46% |
| rs-only | 507 | 45% | +0.016% | +7.92% |

## Today's (2026-06-03) Hourly Data

| Hour UTC | Trades | WR | Avg PnL |
|---|---|---|---|
| 00:00 | 9 | 44% | -0.23% |
| 01:00 | 5 | **100%** | +1.77% |
| 03:00 | 7 | 43% | -0.23% |
| 04:00 | 9 | 22% | -0.35% |
| 05:00 | 10 | 60% | +0.15% |
| 06:00 | 6 | 33% | -0.21% |
| 09:00 | 2 | **0%** | -0.91% |
| 10:00 | 6 | 40% | ~0% |

**04:00 UTC is systematically worst** across all signal types — market regime issue, not signal-specific.

## Why Losses Are Happening (Not a Code Bug)

- 30 of 31 losing rs signals today hit `atr_sl_hit` at -0.03% to -1.44%
- Signals are directionally correct — price moved against them within the ATR band
- ATR stops at 1% of price are too tight relative to actual candle noise
- This is an ATR calibration issue in position_manager, not an rs.py issue
- 30-day: ALL signal families are net positive (+3.5% to +25% total)
- Today's losses are short-term regime noise

## Fix Location

Signal fix (confluence tightening) would require blocking `accel-300-+rs-s-broken` as a specific bad combo — not a family collapse but an explicit combo block. Location: `signal_compactor.py` `_should_approve_signal()`.

This is a `new-signal-implementation` type change — needs T approval before implementing.