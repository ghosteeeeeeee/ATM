# Signal Performance Report
**Generated:** 2026-10-02 23:15 UTC | **Period:** Last 6h + 24h
**DB:** PostgreSQL brain @ /var/run/postgresql (queried live, not from prior report)

## Overall Stats (PG-verified)
- **24h closed:** 41T | system PnL **-$0.19**
- **6h closed:** 0T (no signal with ≥2 trades)
- **Prior report (23:03) numbers were stale/wrong** — bb-squeeze+ was listed +3.28/64%WR; live DB shows **-$0.06/57.7%WR**. mtf-regime-trend+ listed as "disabled but good" — it **was killed 15:11 today** (flag re-verified False).

---

## 24h Performance (HAVING trades ≥3)

| Signal | Dir | Trades | WR | PnL | Regime split (all-time) |
|--------|-----|--------|-----|-----|-------------------------|
| mtf-regime-trend+ | LONG | 9 | 44.4% | **-$0.46** | HIGH 6T 33.3% -$0.40 · NORMAL 3T 66.7% -$0.06 |
| bb-squeeze+ | LONG | 26 | 57.7% | **-$0.06** | EXTREME 12T 50.0% -$0.15 · HIGH 11T 63.6% +$0.14 · NORMAL 3T 66.7% -$0.05 |
| bb-bounce-v3-long+ | LONG | 3 | 100% | +$0.23 | HIGH 3T 33.3% +$0.03 · NORMAL 3T 66.7% +$0.06 |

Also <3T (below thresholds): doji-bottom-long 2T +$0.12, volume-breakout-long+ 2T +$0.94.

---

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | **No new kills.** |

**mtf-regime-trend+ LONG — already dead, verified not re-enabled.**
- `MTF_REGIME_TREND_PLUS_ENABLED = False` (killed auto_1hr 2026-10-02 15:11 — 4T 0%WR -$0.70 last hour)
- Today's 9 trades (13:27–15:45) were **pre-kill** opens. 24h aggregate 44.4% WR does not reopen it.
- Does **NOT** meet kill criteria on the 24h window alone (WR 44.4% > 30%, active <24h at kill time). Kill was correct on last-hour collapse. Flag stays False. Not added to NEVER_REENABLE (first offense — auto_1hr already owns it).

---

## BOOSTED / DE-BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 57.7% | -$0.06 | 26 | **Weight 1.2 → 1.0** (boost evidence expired) |

- Boost criteria require WR>55% **AND** PnL>$0.05. bb-squeeze+ has WR but **PnL is -$0.06** — fails.
- Same-day boost (1.2x at 17:12) was based on +$0.21; window flipped negative. R:R broke: profit-monster-trail avg win +0.059 vs hard_sl/hard_max_loss losers -0.11 to -0.27.
- **REGIME BLOCK EXECUTED — bb-squeeze+ EXTREME (not blanket kill):**
  - EXTREME 12T 50%WR -$0.15 → blocked
  - HIGH 11T 63.6%WR +$0.14 → **kept** (≥55% WR regime)
  - NORMAL 3T 66.7%WR → kept (thin sample)
  - `BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED = True` in hermes_constants.py
  - Removed from v1 `volatility_gate.py` EXTREME REGIME_SIGNALS (decider_run uses v1, not v2)
  - Added `('EXTREME', 'bb-squeeze'): 0.0` to v2 SIGNAL_TYPE_OVERRIDES
  - Hard block in decider_run.py (STANDALONE_BYPASS skips signal_compactor — pump-chain pattern)
  - FAMILY_MAP: already in Squeeze family (market_phase_gate.py:63) — no change
- bb-bounce-v3-long+ 3T 100%WR +$0.23 — **no boost** (need 5+ trades). Watch.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mtf-regime-trend+ | LONG | 44.4% | -$0.46 | 9 | **KILLED 15:11** — flag False verified. HIGH regime was the bleed zone. |
| bb-squeeze+ | LONG | 57.7% | -$0.06 | 26 | ENABLED — EXTREME blocked, weight 1.0. R:R watch: hard SL losses dominate. |
| bb-squeeze+,rs-s33 | LONG | — | -$0.10 | 1 | Confluence variant, below threshold. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 100% | +$0.23 | 3 | ENABLED — sample too small to boost |
| volume-breakout-long+ | LONG | 100% | +$0.94 | 2 | ENABLED — below threshold |
| doji-bottom-long | LONG | 100% | +$0.12 | 2 | ENABLED — below threshold |

---

## SIGNAL INVERSIONS (24h)

**None.** 0 direction mismatches (long-named signal with SHORT execution or vice versa).

---

## ISSUES

1. **Prior signal_report.md (23:03) was materially wrong** — bb-squeeze+ PnL +3.28 vs live -$0.06; mtf listed as re-enable candidate when flag was already False. This run re-queried PG directly.
2. **bb-squeeze+ R:R structural problem** — 21/26 exits via profit-monster-trail (good), but 5 hard SL/max_loss exits (-$0.84 total) wipe the +$0.68 trail profit. EXTREME block addresses the worst regime; if HIGH/NORMAL hard-SL rate stays elevated, next lever is SL width or hard_max_loss threshold — not another regime kill.
3. **PostgreSQL `close_time` is `timestamp without time zone`** — passing tz-aware datetimes via psycopg2 `%s` params causes cryptic errors. Use naive UTC datetime objects for queries. (This cost this run two debugging cycles.)
4. **mtf-regime-trend- SHORT still ENABLED** — 0 trades/24h, no data. Not touched.
5. **Pipeline restart required** to load new gate code (decider_run + volatility_gate + signal_compactor).

---

## Changes Applied

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | +`BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED = True` |
| `scripts/volatility_gate.py` | bb-squeeze+ removed from EXTREME REGIME_SIGNALS |
| `scripts/volatility_gate_v2.py` | +`('EXTREME', 'bb-squeeze'): 0.0` SIGNAL_TYPE_OVERRIDES |
| `scripts/decider_run.py` | +bb-squeeze+ LONG EXTREME hard block (STANDALONE_BYPASS path) |
| `scripts/signal_compactor.py` | bb-squeeze+ weight 1.2 → 1.0 |

*Report auto-generated by signal_reporter. Next run: ~6h.*
