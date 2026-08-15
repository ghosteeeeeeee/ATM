# Signal Performance Report
**Period:** Last 6h | 24h  
**Generated:** 2026-08-15 ~04:10 UTC

---

## System Summary
| Metric | 24h |
|--------|-----|
| Total Trades | 73 |
| Overall WR | 46.6% |
| Total PnL | -$0.72 |
| Signal Inversions | 0 |

---

## KILLED (executed this session)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No new kills needed |

All losers from previous reports already terminated:
- mover+ (MOMENTUM_LEADERBOARD_PLUS_ENABLED=False, killed 2026-08-15)
- wave_catcher all variants (WAVE_CATCHER_ENABLED=False, killed 2026-08-16)
- range_breakout_short (killed 2026-08-15)

---

## BOOSTED (executed this session)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No boosts — system at -0.72 PnL, wrong time |

---

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| range_finder+ | LONG | 33.3% | -$0.14 | 9 | WATCH — re-enabled 2026-08-15 for testing, monitoring |
| wave_catcher- | SHORT | 25.0% | -$0.09 | 4 | DEAD — master kill active, settling trades |
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 | DEAD — master kill active, settling trades |
| r2-trend-long4 | LONG | 33.3% | -$0.11 | 3 | WATCH — needs 5+ trades for threshold |
| mover+ | LONG | 16.7% | -$0.16 | 6 | DEAD — killed 2026-08-15 |

---

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long1 | LONG | 66.7% | +$0.08 | 3 | ACTIVE — needs more trades |
| r2-trend-long2 | LONG | 60.0% | +$0.01 | 15 | ACTIVE — solid performer |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 | DEAD — master kill, but SHORT was profitable |
| r2-trend-long3 | LONG | 62.5% | -$0.04 | 8 | MIXED — high WR but losses > wins |

---

## Key Observations

1. **R2-trend family is the best performer** — r2-trend-long1/2/3 all have 60%+ WR. The r2-trend-long3 negative PnL is from 2 ATR SL hits (-$0.18) offsetting 6 profit-monster exits (+$0.14).

2. **Most 24h losses are settling trades** from already-killed signals (wave_catcher, mover+). The kill switches worked — no new entries after kill timestamps.

3. **range_finder+ is the only active concern** — re-enabled for testing 2026-08-15, currently 33.3% WR with 9 trades. Mostly small losses from profit-monster-trail exits. Worth monitoring for another 24h before deciding.

4. **profit-monster-trail is the dominant close reason** — many exits are small-profit or flat, which is good risk management but contributes to negative PnL when losses are larger than wins.

5. **No signal inversions detected** — all trades match expected direction.

---

## Action Items
- [ ] Monitor range_finder+ for 24h — if WR stays <35%, kill it
- [ ] Track r2-trend-long3 — high WR but negative PnL needs investigation (ATR SL too tight?)
- [ ] No immediate kills or boosts warranted — system is in cleanup mode from previous session's mass kills
