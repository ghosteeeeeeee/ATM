# Signal Performance Report — 2026-10-13 17:10 UTC

Period: Last 6h | 24h | DB-verified (PostgreSQL brain, 52 closed trades in 24h)

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| hmacd_mtf-+ | LONG | 20.0% | -$0.33 | 5 (24h) | HMACD_MTF_PLUS_ENABLED = False. Lifetime 8T 25%WR -$0.46. ALL regimes <50% WR (EXTREME 33%, HIGH 0%, FLAT 0%, NORMAL 50% but -$0.11) → blanket kill. |

## KILLED (pre-existing today, verified)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 0.0% | -$0.46 | 5 (24h) | DOJI_BOTTOM_ENABLED=False (auto_1hr 2026-10-13). ⚠️ See issues — regime check says HIGH 71.4% WR. |
| oversold-bounce+ | LONG | 0.0% | -$0.33 | 3 (24h) | OVERSOLD_BOUNCE_ENABLED=False (auto_1hr 2026-10-13). Regime check: no regime ≥55% WR (EXTREME 25%, HIGH 50%) → blanket kill correct. |

## BOOSTED (executed)

None. No signal met boost criteria (WR >55%, 5+ trades, PnL >$0.05 in 24h). Best performers were 1-2 trade samples (continuum-trend+ 2T 100% +$0.08, r2v2-long9 1T +$0.12) — insufficient sample.

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 30.8% | -$0.16 | 13 (24h) | 6h worse: 18.2% -$0.38. All 24h trades EXTREME. HIGH already blocked; EXTREME block REVERTED by CEO ("every dump is a SHORT") — standing by CEO decision. NORMAL 75% WR +$0.53 lifetime. |
| pump-chain+ | LONG | 30.0% | -$0.03 | 10 (24h) | EXTREME lifetime 46.4% WR +$3.28 — profitable signal, chop week. RSI_MAX=70 soak (brain_auditor today). Monitor. |
| volume-breakout-long+ | LONG | 0.0% | -$0.21 | 3 (24h) | Lifetime 48.7% WR +$2.32. 30d all RSI bands positive. Noise, not signal. |
| ai-trader+ | LONG | 0.0% | -$0.17 | 3 (24h) | Lifetime 50% WR -$0.12. Below kill thresholds. |
| hmacd_mtf-- | SHORT | 0.0% | — | 0 (24h) | Lifetime 4T 25%WR -$0.19. Below trade thresholds, monitor. |
| oversold-bounce+ | LONG | 0.0% | -$0.33 | 3 (24h) | Already killed today (see above). Regimes confirm. |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long9 | LONG | 100% | +$0.12 | 1 (24h) | Small sample. |
| continuum-trend+ | LONG | 100% | +$0.08 | 2 (24h) | Small sample. |
| hl_copy_trader | LONG | 50% | +$0.07 | 2 (24h) | Quality-filter re-enable (CEO 2026-10-08). |

## ISSUES

- **⚠️ doji-bottom-long blanket kill may be wrong regime call (for CEO):** auto_1hr killed it today (0/5 24h -$0.46) but lifetime regime split: HIGH 14T 71.4% WR +$0.68, NORMAL 8T 50% WR +$0.12, EXTREME 3T 0% WR -$0.25. Signal WINS in HIGH. Kill comment says "re-enable only with CEO approval + regime check" — regime check done: recommend re-enable with EXTREME-only block (volatility_gate_v2 0.0x multiplier), NOT full kill. CEO decision required.
- No direction inversions found in 24h (checked signal vs direction mismatches — clean).
- pump-chain SHORT book correlated (brain_auditor flagged 3 open SHORTs earlier — watch).
- hmacd_mtf-+ kill: signals fire via signals_runner loading hermes_constants fresh each run — no pipeline restart needed (timer-based, not daemon).
