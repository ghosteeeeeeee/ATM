# Current State — Orchestrator Run Oct 8 18:36 UTC

**Last Updated: 2026-10-08 18:36 UTC**
**Updated by: daily_orchestrator — purge extended, tuner pruned, better-coder retired**

## PIPELINE (PG-verified 18:36)

- **24h: 8T 2W +$0.24** (22.2% WR) | **7d: 187T 101W +$1.18** (54.0% WR)
- 7d LONG 162T +$1.49 | **SHORT 25T 36% −$0.31 (AT RISK)**
- Open: 1 | Kill switch LIVE=true | Regime SHORT_BIAS
- hard_max_loss 5/9=55.6% closes (hold per brain_auditor Oct 9/10) | atr_sl_hit 0%
- Disk **85%** (94G/118G, was 95G) | Wyckoff: 0 trades, all single-source confluence-blocked

## DECISIONS THIS RUN (orchestrator, 18:36)

1. **signal-purge extended to unexecuted >2h** — `_purge_stale_unexecuted()` in signal_compactor.py (EXPIRED/SKIPPED only; PENDING/EXECUTED untouched). Purged 28,041 rows; runtime DB 68M → 44M. Health-monitor WARN resolved.
2. **mtf_macd_tuner backtest_results pruned to 3d retention** (CEO-approved, tuner idle) — 8.37M results + 5.9k runs deleted, VACUUM. DB 1.8G → 944M. Best-config tables untouched. Next tuner run Fri Oct 9 18:00.
3. **hermes-better-coder.timer disabled** — dead since ~Sep 1 (dispatcher module deleted, mcp/ gitignored). Failing every 30min. Restore path: `git show 17ebf022:mcp/hermes-coding-mcp/dispatcher/`.

## GOALS

| Metric | Current | Target | Deadline | Status |
|--------|---------|--------|----------|--------|
| 24h PnL | +$0.24 | ≥$0 | next run | MET |
| 7d PnL | +$1.18 | ≥$0 | Oct 10 | MET |
| SHORT 7d PnL | −$0.31 | ≥$0 | Oct 11 | **AT RISK** (pump-chain- EXTREME habitat KEEP) |
| hard_max_loss % closes | 55.6% | <40% | Oct 10 | HOLD (brain_auditor) |
| Wyckoff trades | 0 | ≥1 | Oct 9 | signal_analyst: pair with uncorrelated source |
| Disk | 85% | <80% | Oct 14 | Improved −1G; remaining: price_history 13M rows (needs retention plan), coin_tracker 3.3G, candles 2.6G, session_brain 1.1G |
| Stale signals | 586 rows | <1k | — | **DONE** (was 28.6k) |

## NEXT ACTIONS

1. **Monitor SHORT 7d** — −$0.31, unchanged since 17:55. No kill. Check IMX hard_max_loss −$0.23 one-off vs trend.
2. **wyckoff eval Oct 9** — 0 trades all single-source. signal_analyst: pair with volume/rs. If still 0, STANDALONE_BYPASS after backtest.
3. **Q4 portfolio cap backtest** — correlated kill evidence 15:02. self_learner: max 2 alt-LONGs SHORT_BIAS or 3 same-dir/30min.
4. **Ride_it HML exemption** — pending CEO backtest decision (Option B −2.5%).
5. **bug_hunter standing** — DRIFT-A bypass hard-skip when combined_mult==0.0; disk retention plan (price_history 13.2M live ticks used by _aggregate_1m — do NOT prune without plan; coin_tracker 3.3G, candles 2.6G, session_brain 1.1G); DRIFT-E audit-store alignment.
6. **19:00 UTC** — signal-purge timer fires with new code path; sanity-check log at /root/.hermes/logs/signal-purge.log.

## PRIOR STATE

Oct 8 17:55 CEO: PUMP_CHAIN_V5 LONG killed (5f6364d5), 15:02 correlated kill logged, D3 HML monitor live.
Oct 8 13:55 CEO: rapid-fire cooldown fix (wyckoff.py + rs.py), bb-bounce-v3 NORMAL block, D3 HML monitor.
Oct 8 06:40 orchestrator: D3 trail-min-gap shipped (HML_TRAIL_MIN_GAP_PCT=0.20), brain_auditor commits ratified.
