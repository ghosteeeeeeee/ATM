# Independent Audit: momentum_state loser claim (2026-10-08)

**Verdict: PARTIAL (numbers reproduce; the pattern and the proposed fix do NOT hold)**

## Reproduction (close_time, jsonb _signal_metadata->>'momentum_state', pnl_usdt, 14d)
| Bucket | Claimed | Reproduced |
|---|---|---|
| LONG falling | 27T 48.1% -$0.62 | 27T 48.1% SUM -$0.62 ✓ |
| LONG flat | 65T 53.8% +$1.63 | 65T 53.8% SUM +$1.63 ✓ |
| LONG rising | 129T 56.6% +$2.00 | 131T 57.3% SUM +$2.27 (minor; 14.25d window gives 132T/56.8%/$1.99) |
| SHORT falling | 48T 43.8% -$0.49 | 48T 43.8% SUM -$0.49 ✓ |
| SHORT flat | 15T 40.0% -$0.77 | 15T 40.0% SUM -$0.77 ✓ |
| SHORT rising | 10T 50.0% -$0.21 | 10T 50.0% SUM -$0.21 ✓ |

**Critical: claimed $ figures are bucket TOTALS, not per-trade averages.** LONG falling avg = -$0.023/trade.

## Significance (14d)
- LONG falling vs rising WR: z-test p=0.386, Fisher p=0.403; PnL Welch p=0.164 — NOT significant
- SHORT flat vs falling: p=0.798/1.000; vs rising: p=0.622 — NOT significant
- Wilson CI: LONG falling [30.7%, 66.0%] vs LONG rising [48.7%, 65.4%] — overlap
- Power: need ~462T/bucket to detect 48.1% vs 57.3% (have 27); ~388T for SHORT (have 15)

## Out-of-sample
- **7d: pattern REVERSES** — LONG falling 11T, 63.6% WR (best LONG bucket). SHORT flat only 4T.
- **30d: pattern VANISHES** — LONG falling 78T 48.7% vs rising 284T 51.4% (p=0.674). SHORT flat 100T **51.0% WR — profitable**, while SHORT *falling* is the worst SHORT bucket (-$2.20/178T). The proposed SHORT-flat block targets the wrong bucket at 30d.

## Confounders
- LONG falling 14d loss = rs-structural signals (14T, 4W, -$0.66). Mean-reversion LONG falling (doji/bounce/oversold): 7T, **6W, +$0.23** — blanket block kills winners (doji-bottom-long 4/4W).
- Time concentration: 22/27 LONG-falling trades in one week (Sep 28); 15T in Sep 28–30 alone.
- momentum_state is NOT uniform: computed per-signal with different lookbacks/thresholds (oversold_bounce own lookback, pullback_entry 5-bar ±0.1%, pump_chain reads PG). signal_compactor uses MAX(momentum_state) across merged combos = alphabetical bias ('rising' > 'flat' > 'falling').

## Existing implementations (do not re-propose)
- OSCILLATOR_MULTS already penalizes wave_phase 'falling' zones 0.6–0.8x (live 2026-10-01)
- pump_chain_v5 already blocks LONG when momentum_state='flat'
- pullback_entry already blocks SHORT flat+falling and LONG rising+flat
- oversold_bounce REQUIRES falling/flat LONG — direct collision with proposed block
- BTC chop gate + TREND-ALIGN already penalize misaligned momentum

## Filter effect in-sample (14d)
Block LONG-falling + SHORT-flat: removes 42T (45.2% WR, -$1.39) → 254T 53.5% +$3.20. Directionally positive in-sample but rests on p≈0.4 noise, reverses at 7d, and kills +$0.23 of mean-reversion winners.
