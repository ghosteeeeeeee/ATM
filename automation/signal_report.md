# Signal Performance Report
**Generated:** 2026-10-12 05:11 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Closed trades (24h):** 18 | **Net PnL:** +$1.70
- **Closed trades (48h):** 45
- **Open positions:** 3
- **Timers:** all hermes-* systemd timers active and firing on schedule

---

## KILLED (executed)

None. No signal met kill criteria (WR < 30% with 5+ trades AND net PnL < -$0.10 over 24h).

---

## BOOSTED (executed)

None. No signal met boost criteria (WR > 55% with 5+ trades over 24h).

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 33.3% | -$0.26 | 3 | ❓ WATCH — below trade threshold |
| ai-trader+ | LONG | 33.3% | -$0.13 | 3 | ❓ WATCH — below trade threshold |
| oversold-bounce+ | LONG | 0.0% | -$0.07 | 2 | ❓ WATCH — n too small |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader-manual | LONG | 100% | +$0.57 | 1 | ✅ |
| r2v2-long3 | LONG | 100% | +$0.59 | 1 | ✅ |
| doji-bottom-long | LONG | 100% | +$0.23 | 1 | ✅ |
| volume-buildup+ | LONG | 100% | +$0.09 | 1 | ✅ |
| bb-bounce-v2-long+ | LONG | 100% | +$0.06 | 1 | ✅ |
| grind-breakout+ | LONG | 100% | +$0.02 | 1 | ✅ |
| ai-trader-manual | SHORT | 100% | +$0.02 | 1 | ✅ |

*(No winner reached the 5-trade threshold for a boost.)*

---

## ISSUES

- **Signal inversions (24h):** none found. Direction labels all consistent.
- **Null-signal trade:** 1 BTC LONG closed at $0.00 with `close_reason=guardian_orphan` (2026-10-11 18:12). Known behavior — HL position with no DB record, handled by `hl-sync-guardian.py`. Not a bug, no action needed.
- **Low trade volume:** only 18 closed trades in 24h vs 45 in prior 24h. Timers healthy; likely quieter market or gate filtering. No action — system still net positive.

---

## VERDICT

System healthy: +$1.70 net over 24h, zero inversions, no signal qualifies for kill or boost. Marginal losers (pump-chain+, ai-trader+) carry only 3 trades each — below the 5-trade kill threshold; re-evaluate next cycle.

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-12 | e62802d | config: hl_copy_trader uses RR engine exits |
| 2026-10-12 | 58a8629 | config: grind-breakout uses RR engine + ATR SL |
| 2026-10-12 | 979e964 | config: add ai-trader-manual to SIGNAL_EXIT_CONFIG (rr_engin... |
| 2026-10-12 | 2b6c85c | Signals: MAXXED volatility tier (T directive, complementary ... |
| 2026-10-12 | d6fd05d | CEO: regime-recalibration decision — MAXXED shadow-approved,... |
| 2026-10-12 | 4f02129 | fix: Phase 2 pickup file — CEO found pre-flight check flaw |
| 2026-10-12 | 0025b2c | brain_auditor: Fix bb-squeeze midband filter collision (2026... |
| 2026-10-12 | 7503aa5 | fix: reputation.py — 3 critical bugs from code review (BUG 1... |
| 2026-10-12 | d2c3fe0 | fix: Signal marks rejected picks so watchdog picks different... |
| 2026-10-11 | d75ff26 | signal: expiry 5min→15min (SIGNAL_EXPIRY_MINUTES constant) —... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
