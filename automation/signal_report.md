# Signal Performance Report
**Generated:** 2026-08-25 11:02 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,417 | **WR:** 48.7% | **PnL:** -69.02%
- **Date range:** 2026-07-29 → 2026-08-25

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb_bounce+ | LONG | 6 | 33.3% | -3.43 | 17 | 70.6% | +1.17 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| ct-hot+ | LONG | — | —% | — | 5 | 0.0% | -6.24 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| macd-div- | SHORT | 9 | 44.4% | -4.75 | ❓ | Borderline |
| hl_copy_trader | LONG | 10 | 50.0% | -3.40 | ❓ | Borderline |
| tl_break_short | SHORT | 7 | 42.9% | -3.04 | ENABLED | Borderline |
| bb-bounce-short,confluence- | SHORT | 2 | 50.0% | -0.73 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] ct-hot+ LONG** — WR=0.0%, PnL=-6.24% over 5 trades (24h).
2. **[WATCH] macd-div- SHORT** — WR=44.4%, PnL=-4.75% over 9 trades. Monitor next cycle.
3. **[WATCH] hl_copy_trader LONG** — WR=50.0%, PnL=-3.40% over 10 trades. Monitor next cycle.
4. **[WATCH] tl_break_short SHORT** — WR=42.9%, PnL=-3.04% over 7 trades. Monitor next cycle.
5. **[WATCH] bb-bounce-short,confluence- SHORT** — WR=50.0%, PnL=-0.73% over 2 trades. Monitor next cycle.
6. **[KEEP] 1 winning combos** — bb_bounce+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-25 | 1350ec3 | scripts: widen ATR_SL_MIN 1.2%→1.5% — reduce atr_sl_hit domi... |
| 2026-08-25 | 0db8082 | Daily trading system update (2026-08-25) |
| 2026-08-25 | 5ba6408 | auto_1hr: no changes 2026-08-25 04:05 UTC - 2T last hour pro... |
| 2026-08-25 | a10a912 | fix: add bb-bounce-short to standalone bypass list |
| 2026-08-25 | 30f5e90 | fix: raise slope threshold 0.01%→0.05% to unblock SHORT sign... |
| 2026-08-24 | c13d20c | signals: kill ct-hot- SHORT — 0% WR, 6T, -$0.34. NEVER_REENA... |
| 2026-08-24 | 1197fc3 | config: remove ME from FAVORITES (33.3% WR) |
| 2026-08-24 | a7d428a | tl_break: add extension filter, fix inverted RSI, blacklist ... |
| 2026-08-24 | 6eea1b0 | CEO run 250: system slightly red, recommend T disable ct-hot... |
| 2026-08-24 | fba21a5 | signals: add RSI 5m guard to macd-div SHORT |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*