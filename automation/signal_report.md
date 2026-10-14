# Signal Performance Report
**Generated:** 2026-10-14 06:00 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3,087+ | **WR:** 51.3%
- **Date range:** 2026-07-29 → 2026-10-14

---

## KILLED (executed — verified today)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 0.0% | -$0.46 | 5 (24h) | `DOJI_BOTTOM_ENABLED=False` — verified line 4359. Kills from SEI/IMX/TURBO/ME hard_max_loss + atr_sl_hit. HIGH regime 83% WR kept via regime gate; EXTREME already blocked. |
| hmacd_mtf-+ | LONG | 20.0% | -$0.33 | 5 (24h) | `HMACD_MTF_PLUS_ENABLED=False` — verified line 2730. ALL regimes <50% WR (EXTREME 33%, HIGH 0%, FLAT 0%, NORMAL 50% but -$0.11). |

---

## BOOSTED (executed)

None — no signal met WR > 55% with 5+ trades and PnL > $0.05 in 24h.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 0.0% | -$0.25 | 4 (24h) | HIGH regime blocked (0.0 override). EXTREME 52% WR +$3.17 kept. 24h losers are HIGH trades — already gated. |
| ai-trader+ | LONG | 0.0% | -$0.15 | 3 (24h) | Under 5T threshold. All regimes near break-even. Watch. |
| bb-bounce-v2-long+ | LONG | 40.0% | -$0.11 | 5 (24h) | Tuning candidate (30-40% WR, 5+ trades). Small loss. FLAT habitat protected. |
| pump-chain- | SHORT | 30.0% | -$0.02 | 20 (24h) | Tuning candidate. Basically flat. RSI floors + HIGH block already in place. |
| hmacd_mtf-- | SHORT | 25.0% | -$0.19 | 4 (lifetime) | Under 5T threshold. Same losing profile as killed sibling. Watch — next kill candidate if it fires more. |

---

## WINNERS

None with sufficient sample in 24h window.

---

## ISSUES

- **Inversions:** 0 found (checked signal LIKE '%long%' AND direction='SHORT' and vice versa).
- **hmacd_mtf source naming:** `hmacd_mtf-+` uses `-` base with `+` direction suffix — confusing but correct per mtf_macd.py:465 (`source = f'hmacd_mtf-{hmacd_char}'`). Not a bug.
- **Both kills already executed earlier today** — DOJI_BOTTOM_ENABLED and HMACD_MTF_PLUS_ENABLED verified False in hermes_constants.py. No duplicate action needed.
