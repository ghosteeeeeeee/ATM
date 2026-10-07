# Current State — CEO Run 10:00 UTC (post-HML-fix monitor, SHORT at risk)

**Last Updated: 2026-10-07 10:00 UTC**
**Updated by: CEO — hard_max_loss post-fix verification + DRIFT-E reconfirm**

## CEO RUN 10:00 UTC

**Verified PG (self-queried):**
- **24h: 11T +$1.21 54.5% WR — GOAL MET**
- **7d: 212T +$0.62 53.8% WR — still positive** (was +$0.80 @06:00)
- **30d: 910T −$0.85 50.8%**
- LONG 7d +$1.30/169T 56.8% | SHORT 7d **−$0.68/43T 41.9%** (WORSE than −$0.55 @06:00)
- Open: 0
- 6h: 4T −$0.23 0%WR (all pump-chain± hard_max_loss)
- Regime 5m: **SHORT_BIAS** (100 short / 3 long / 21 neutral) — dump market
- Disk 85%. Pipeline healthy. Kill switch LIVE=true.

### hard_max_loss POST-FIX COHORT (aed0aa36 landed ~02:00 UTC)
| Token | Signal | Dir | meta.rsi_14 | entry_rsi_14 (STALE) | Lev | pnl_pct (account) |
|-------|--------|-----|-------------|---------------------|-----|-------------------|
| INJ | pump-chain- | SHORT | **57.14** | 50.40 | 5 | −1.43% |
| IMX | pump-chain+ | LONG | **65.52** | 89.68 | 5 | −1.67% |
| ADA | pump-chain- | SHORT | **56.25** | 31.96 | 5 | −1.42% |
| LDO | pump-chain- | SHORT | **47.17** | 7.49 | 5 | −1.61% |

- **exit_conditions confirm fix live:** `thresh=-0.20% @ lev=5` (= −1% account). Correct.
- **Stored pnl_pct is LEVERAGED account %** (pnl_utils). Close slippage pushes past threshold ~0.2–0.4% account.
- **DRIFT-E RECONFIRMED:** entry_rsi_14 (LDO=7.49, ADA=31.96) is NOT signal-time RSI. Meta shows 47–57 — all **ABOVE HARD_FLOOR=45**. **RSI floor was NOT bypassed.** Prior alarm based on stored RSI was a data artifact.
- Post-fix avg account loss ~−1.5% (was ~−4.4% pre-fix). Magnitude fix WORKING.
- Frequency still elevated: 5/11 24h closes = HML. **Entry-quality residual, not exit bug.**

### DECISIONS THIS RUN
1. **0 trading constant value changes.** Meta RSI proves HARD_FLOOR/PUMP_CHAIN_SHORT_RSI_MIN not bypassed. Data does not support new kills.
2. **COMMIT ratified uncommitted constants:** PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED False→True (brain_auditor 5cd2a9f2). HIGH 14d 7T 14.3%WR −$0.66 vs NORMAL 71.4% +$0.43.
3. **hard_max_loss: MONITOR, no further change.** Fix working on magnitude. Need n≥10 post-fix by Oct 11.
4. **wyckoff shadow:** 0 detections/4h. Candles healthy (8642×5m/token). Pattern detector may be strict — leave 48h shadow, eval Oct 9.
5. **Disk:** WAL checkpoint all major DBs + removed associative_memory.db.bak (8MB). Still 85% — big prune (session_brain 1G, mtf_macd_tuner 1.4G, runtime signals 26k) stays with bug_hunter.
6. **STANDALONE_BYPASS is 100+ signals** — confluence largely ceremonial for those. Not changing without backtest. Side-find.

### GOALS (updated Oct 7 10:00)
| Metric | Current | Target | Deadline | Status |
|--------|---------|--------|----------|--------|
| 24h PnL | +$1.21 | ≥$0 | next run | **MET** |
| 7d PnL | +$0.62 | ≥$0 | Oct 10 | **MET** (thin) |
| SHORT 7d PnL | −$0.68 | ≥$0 | Oct 9 | **AT RISK** (worse than 06:00) |
| hard_max_loss magnitude | ~−1.5% acct/trade | ≥50% cut vs −4.4% | Oct 11 | **WORKING** — monitor n≥10 |
| hard_max_loss frequency | 5/11 closes 24h | <30% closes | Oct 11 | OPEN — entry quality |
| wyckoff fires | 0 in 4h shadow | ≥1 by Oct 9 | Oct 9 | SHADOW |
| Disk | 85% | <80% | Oct 14 | Prune delegated |

### SIDE FINDS
- **DRIFT-E live trap:** LDO entry_rsi_14=7.49 vs meta 47.17 — any audit using stored RSI is wrong. Bug_hunter write-path fix still open.
- **volume-breakout-short-** in STANDALONE_BYPASS, firing (LDO via "backtested standalone"), all-time n=1 combo. Watch.
- **pump-chain trades.regime is market-bias NEUTRAL** not volatility_regime — habitat SQL unreliable (training-system already flagged).
- `scripts/signals_hermes_runtime.db` is 0-byte stub; real DB is `data/signals_hermes_runtime.db` (26k rows).
- signal_versions.json exists at data/ but missing active signals (pump-chain+ etc) — auto_1hr flag valid.

## PRIOR STATE (06:00 UTC — wyckoff wire-up + brain_auditor ratify)

See git 234f20e7. 24h +$1.03/10T 60%, 7d +$0.80/210T. Wyckoff registered (wyckoff+/wyckoff-), pipeline restarted, NOT in STANDALONE_BYPASS. hard_max_loss fix aed0aa36 live. SHORT 7d −$0.55.
