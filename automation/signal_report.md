# Signal Performance Report
**Generated:** 2026-10-24 07:45 UTC | **Period:** Last 6h + 24h

**24h totals:** 18 closed trades | net PnL +$0.06
**6h totals:** 1 closed trade | net PnL +$0.01

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met boost criteria |

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% | -0.14 | 1 | Watch — n=1, no action |
| ai-trader-pending | SHORT | 0.0% | -0.08 | 1 | Watch — manual trade, not a signal issue |
| volume-buildup- | SHORT | 55.6% | -0.07 | 9 | Watch — WR fine, small avg loss; one hard_max_loss (-0.17) and two cut/hard SLs dragged it negative |
| pump-chain+ | LONG | 50.0% | -0.06 | 2 | Watch — n=2, needs more data |
| ai-trader-pending | LONG | 0.0% | -0.02 | 1 | Watch — manual |
| r2v2-long9 | LONG | 0.0% | -0.01 | 1 | Watch — n=1 |

**72h context (for early-warning, not kill basis):** bb-bounce-v2-long+ 44.4% WR / -$0.30 (9 trades), pump-chain+ 25% WR / -$0.22 (4 trades), continuation+ 50% / -$0.18 (4 trades). None yet meet the 24h kill bar, but bb-bounce-v2-long+ and pump-chain+ deserve scrutiny at next run.

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 100.0% | +0.34 | 1 | Enabled — single trade |
| warrior-sr-confirm- | SHORT | 100.0% | +0.09 | 1 | Enabled — single trade |
| r2v2-long4 | LONG | 100.0% | +0.01 | 1 | Enabled — single trade |

**volume-buildup- SHORT** is the only multi-trade signal with decent WR (55.6%, 9 trades) but net -$0.07 — fails boost criterion (needs PnL > +$0.05). Keep enabled; performance is borderline-acceptable.

---

## ISSUES

- **No signal inversions (24h).** All long/short labels match direction.
- **Volume is very thin** — only 18 closed trades in 24h, 1 in last 6h. Statistical confidence is low across the board; almost every signal has n≤2. No aggressive tuning warranted this cycle.
- **Regime check (volume-buildup-, all-history):** EXTREME 6 trades / 66.7% WR / +$0.02; NORMAL 17 trades / 52.9% WR / -$0.08. No regime has ≥55% WR with enough sample to justify a regime gate change now — left untouched.
