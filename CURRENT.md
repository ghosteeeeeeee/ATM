# Current State — Orchestrator Run 18:35 UTC (Fix 1 Shipped)

**Last Updated: 2026-10-06 18:35 UTC**
**Updated by: daily_orchestrator — Fix 1 penalty-gated execution implemented**

## PENALTY-GATED EXECUTION (CEO 16:40 — Fix 1 SHIPPED 18:35)

**Plan:** plans/penalty-gated-execution-2026-10-06.md. Root cause was decider_run.py:3214 raw confidence, penalty product never multiplied. Now shipped — see decisions + monitor list below.

### DECISIONS THIS RUN
1. **Fix 1 SHIPPED 18:35** — penalty-gated execution. signal_compactor writes `penalty_product` (raw 26-factor product) on hotset entries; decider_run multiplies `final_confidence × max(product, 0.3)` before MIN_EXEC_CONFIDENCE=50, with post-penalty re-check. LIVE PROOF: RESOLV LONG conf 99 × 0.294 → 29.7% → PENALTY-BLOCK 18:32:05.
2. **Fix 2 SHIPPED** — signal_compactor.py:2642 `_cont_bearish` ema `BELOW`→`BELOW,AT` (POL bear-structure LONG hole; mirror bullish AT fix).
3. **Fix 3 SHIPPED** — chop_detector.py:528 bullish phases + `DECLINING` (aligns with compactor structural-bull override; fixes "CHOP during bull" mislabel).
4. **Fix 4 DELEGATE bug_hunter** — live HL fill audit (paper DB does not corroborate dust claim).
5. **Fix 5 DEFER 48h** — PM_TRAIL_* CEO_PROTECTED untouched; wait Fix 1 blocked-vs-passed cohorts. TRAILING_ACTIVATION_PCT CEO-set Oct 1, not changed.
6. **Q4 portfolio cap — BACKTEST FIRST.** DELEGATE self_learner: max 2 alt-LONGs SHORT_BIAS or 3 same-dir/30min. No blind cap.
7. **Service timeouts FIXED 18:35** — health-monitor 300→600s, signal-reporter 900→1200s (both LLM-agent services timing out mid-run).
8. **signal_versions.json pump-chain- FIXED 18:35** — was raw list, converted to standard `{versions, current_version}` dict.

### GOALS (Oct 13 checkpoint)
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Penalty-gated blocks | RESOLV 99×0.294 blocked | cohorts tracked | 48h post Fix 1 |
| 7d PnL | −$0.66 (since 10-03) | ≥ $0 | 2026-10-10 |
| loss/win ratio | 1.35 | ≤ 1.25 | 2026-10-13 |
| SHORT 7d PnL | −$1.07 | ≥ $0 | 2026-10-07 |
| hard_max_loss 7d | −$7.99 (56T) | ≥50% cut | 2026-10-11 |

### PROTECTED FLAGS (verified intact)
CONFLUENCE_REQUIRED=True · LIVE_TRADING_ENABLED=True · PM_TRAIL_ACTIVATE_PCT=0.40 · PM_TRAIL_DISTANCE_PCT=0.20 · CUT_LOSER_PNL=-1.00 · ATR_TP_MIN=0.013 · CEO_PROTECTED_FLAGS untouched.

### DELEGATED (still open)
- **bug_hunter:** Fix 4 live Hyperliquid order fill audit (read-only; dust claim unverified in PG)
- **self_learner:** portfolio same-direction cap backtest (2 alt-LONGs SHORT_BIAS / 3 same-dir per 30min)
- **bug_hunter:** hard_max_loss leverage semantics (queue#2)
- **bug_hunter:** decider_run v1→v2 + fail-open removal (DRIFT-A)
- **signal_analyst:** hotset empty audit + ema_reclaim + coin_tracker Wyckoff
- **self_learner:** trend-ride+ n≥10 eval Oct 7
- **Disk 84%** — prune at 85–88% (DB retention is next lever; candles/coin_tracker NEVER vacuum mid-trading)

### MONITOR LIST (next 48h — UPDATED post Fix 1)
1. **Fix 1 blocked-vs-passed cohorts** (WR/PnL/win-loss) — first block logged: RESOLV conf 99×0.294→29.7%
2. PENALTY-BLOCK events (replaces SCORE-FLOOR-only tracking) — count blocks, track which signals/families
3. Fix 2/3 in production — POL-type bear LONGs and CHOP-mislabel counts
4. SHORT 7d PnL ≥$0 by Oct 7
5. hard_max_loss bleed reduction (9T −$1.09 24h, semantics with bug_hunter)
6. Disk 85%
7. HL fill audit result — escalate if dust real
8. health-monitor + signal-reporter completing within new timeouts (600s/1200s)

## Standing Decisions (do not re-litigate)
- **SIGNAL KILL POLICY:** regime-block via volatility_gate_v2 if wins in ANY regime. Blanket-kill ONLY if loses in ALL regimes.
- **SHORT ENTRY MODEL:** exec RSI>=40 all paths; EXTREME habitat; NEUTRAL blocked; HARD_FLOOR=25 no override.
- **ATR_TP_MIN=0.013** — brain_auditor approved, DO NOT REVERT.
- **EXTREME pump-chain- SHORT 0.0→1.0** — DO NOT revert.
- **RR_ENGINE_SHADOW=True** until shadow audit numbers exist.
- **STANDALONE_BYPASS shrink-to-6 REJECTED** — incremental prune only.
- **CUT_LOSER_PNL=-1.00 DO NOT CHANGE** — semantics with bug_hunter.
- **PM_TRAIL_ACTIVATE_PCT=0.40 / PM_TRAIL_DISTANCE_PCT=0.20** — CEO_PROTECTED, DO NOT CHANGE.
- **PENALTY → EXECUTION GATE:** Fix 1 SHIPPED 2026-10-06 18:35 — compactor writes `penalty_product`, decider multiplies `final_confidence × max(product, 0.3)` before MIN_EXEC_CONFIDENCE=50. Ranking floor 0.3 stays for hotset score. **LIVE:** RESOLV conf 99×0.294→29.7% blocked.
- **Portfolio caps:** backtest before live — no blind same-direction cap.
- **Fix 5 trails:** deferred 48h post Fix 1 — do not touch TRAILING_ACTIVATION_PCT until cohort data exists.
- **NEUTRAL_SNIPER_ENABLED=False** — human-disabled per T.
- **Agents commit own files only.**
- **Disk prune** when >88%. Coin_tracker/candles NEVER vacuum during trading.

## Orchestrator Report (2026-10-06 18:35 UTC)
- **Fix 1 SHIPPED** — penalty-gated execution live. First block: RESOLV LONG conf 99×0.294→29.7% PENALTY-BLOCK.
- Service timeouts fixed: health-monitor 300→600s, signal-reporter 900→1200s.
- signal_versions.json pump-chain- legacy list → standard dict.
- PG 24h: 15T 6W 8L −$0.59 | 1 open | hard_max_loss 9T −$1.09 sole bleed | atr_sl_hit 0%.
- Protected flags intact. Full detail: automation/trading_log.md.

