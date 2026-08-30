# Signal Performance Report
**Generated:** 2026-08-30 17:10 UTC | **Period:** Last 6h + 24h

---

## 6h Performance

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-short | SHORT | 3 | 33.3% | -$0.20 |
| macd-div- | SHORT | 1 | 0.0% | -$0.16 |
| ichimoku+,rs-s30 | LONG | 1 | 0.0% | -$0.14 |
| ichimoku-,rs-r82 | SHORT | 1 | 0.0% | -$0.10 |
| r2-trend-long4,rs-s122 | LONG | 1 | 100% | +$0.01 |
| ichimoku+,rs-s144 | LONG | 1 | 100% | +$0.01 |
| bb-bounce-long+,engulfing+ | LONG | 1 | 100% | +$0.07 |
| bb-bounce-long+,rs-s54 | LONG | 1 | 100% | +$0.08 |
| engulfing+,rs-s90 | LONG | 1 | 100% | +$0.11 |

---

## 24h Performance

| Signal | Dir | Trades | WR | PnL | Note |
|--------|-----|--------|-----|-----|------|
| macd-div- | SHORT | 3 | 33.3% | -$0.17 | 3T, needs more data |
| bb-bounce-short | SHORT | 16 | 56.3% | -$0.16 | R:R=0.57 (avg win $0.048, avg loss $0.084) |
| confluence-,ichimoku- | SHORT | 2 | 50.0% | -$0.10 | 2T, needs more data |
| ichimoku-,rs-r82 | SHORT | 1 | 0.0% | -$0.10 | 1T only |
| engulfing+,rs-s90 | LONG | 1 | 100% | +$0.11 | |
| bb-bounce-long+,rs-s54 | LONG | 1 | 100% | +$0.08 | |
| bb-bounce-long+,engulfing+ | LONG | 1 | 100% | +$0.07 | |

---

## KILLED (executed this cycle)

None. No signals met kill criteria (WR <30% with 5+ trades, 24h).

---

## BOOSTED (executed this cycle)

None. No signals met boost criteria (WR >55%, 5+ trades, positive PnL).

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| macd-div- | SHORT | 33.3% | -$0.17 | 3 | Watch — below30% WR but only 3T |
| bb-bounce-short | SHORT | 56.3% | -$0.16 | 16 | Watch — good WR but R:R=0.57, losses outsize wins |
| confluence-,ichimoku- | SHORT | 50.0% | -$0.10 | 2 | Watch — tiny sample |

---

## WINNERS

None with meaningful volume. All winning signals had 1-2 trades in24h.

---

## ISSUES

1. **bb-bounce-short R:R problem:** 56.3% WR but avg win $0.048 vs avg loss $0.084 (R:R 0.57). Needs ~60% WR to break even at this R:R. Structural problem — losses are 1.75x wins.

2. **Signal proliferation:** 18 unique signal+direction combos in 24h for 36 closed trades = 2 trades/signal avg. Too many signals diluting data. Hard to evaluate any single signal statistically.

3. **ACCEL_300_BREAKOUT_ENABLED = True** (line1282) but listed in NEVER_REENABLE_FLAGS (line1150). Conflict — no trades in 7d. Consider disabling.

4. **3 open trades** — ATOM, ETC, IO. All LONG.

5. **No inversions detected.**
