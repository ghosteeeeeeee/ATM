# bug_hunter Re-Audit — 2026-10-10 15:15–15:35 UTC

**4-day post-fix health check** (fixes landed 2026-10-05/06; audited against HEAD `59c1b244`).

## VERDICT: DEGRADED

No regressions in the Oct 5/6 session fixes — all 8 verified intact in live HEAD, and both delegated fixes (Fix 1, W1) are implemented and firing. Pipeline is mechanically healthy (0 tracebacks, 0 DB locks, all timers firing). "DEGRADED" not "HEALTHY" for three reasons: (1) hard_max_loss is still the #1 bleed at 41.6% of all closes since Oct 6 despite the leverage-aware fix; (2) candle quality measurably degraded since last audit (64.6% real OHLC vs 88.8%) with the aggregator still running past its planned deletion; (3) 7d performance flipped back negative (−$1.38) and post-fix WR is 36.4%.

---

## 1. Session Fixes — Still Intact? → **PASS (8/8)**

All verified present in current HEAD (`59c1b244`), not just in git history:

| # | Fix | Location (HEAD) | Status |
|---|-----|-----------------|--------|
| 1 | `_aggregate_1m.py` INSERT OR IGNORE for closed candles | `_aggregate_1m.py:148` (comment :141 "FIX 2026-10-05") | ✅ INTACT |
| 2 | MIN_BARS_FOR_CLOSED = 3 | `_aggregate_1m.py:29,127` (commit e9a299ca) | ✅ INTACT |
| 3 | price_collector SLOW_SEED_TOKENS_PER_RUN = 10, 15m in TF list | `price_collector.py:63-64` (`SLOW_SEED_TFS` has 15m; 1m deliberately dropped, BUG-048) | ✅ INTACT (superseded by fast-1m loop, see §4) |
| 4 | `_cont_bullish` accepts ema AT | `signal_compactor.py:2682-2683` (`('ABOVE','AT')`) | ✅ INTACT (commit 114c1897) |
| 5 | `_cont_bearish` accepts ema BELOW,AT (Fix 2) | `signal_compactor.py:2674-2676` (`('BELOW','AT')`) | ✅ INTACT (commit db49a5d7) |
| 6 | SHORT-RSI-FLOOR bear override present | `signal_compactor.py:3722-3736` | ✅ PRESENT (widened further — see §3/W1) |
| 7 | `decider_run.py` `signal_type=` keyword (not `signal=`) | `decider_run.py:1668` `get_sl_multiplier_v2(atr_pct, signal_type=_vol_source)` | ✅ INTACT (commit e3be90aa). Note: `decider_run.py:1648` `should_trade_v2(token, signal=...)` is CORRECT — `should_trade_v2(signal=None)` is that function's real signature (`volatility_gate_v2.py:716`). Not a regression. |
| 8 | 1m RSI fallback at exec time | `decider_run.py:1925-1931` ("FIX 2026-10-06: fall back to 1m RSI when 5m stale") + `rsi_utils.compute_rsi_1m` | ✅ INTACT (commit e8757b7e) |
| 9 | chop_detector bullish phases include DECLINING (Fix 3) | `chop_detector.py:529-533` ("FIX 2026-10-06: DECLINING included") | ✅ INTACT |

## 2. Fix 1 (Penalty-Gated Execution) → **PASS — IMPLEMENTED, LIVE, WORKING**

- Implemented in commit `a3183aea` ("Fix 1 penalty-gated execution shipped (CEO-approved)"), code at `decider_run.py:3355-3376`:
  - `confidence = confidence * max(penalty_product, 0.3)` with penalty_product merged from hotset.json (`:3344-3352`),
  - re-check vs `MIN_EXEC_CONFIDENCE` (50) AFTER multiplication (`:3371-3376`), marking SKIPPED.
- **Live evidence**: 3,608 `[PENALTY-GATE]` and 2,627 `[PENALTY-BLOCK]` events in the current pipeline.log. Latest: `APT LONG conf 87 × 0.529 → 46.0% → BLOCKED`.
- **CEO amendment (2026-10-09)**: `hl_copy` sources EXEMPT from the penalty gate (rationale: 75%+ WR quality filter applied upstream; old penalty history poisons new qualified signals). Rationale is documented, but note this is a carve-out that removes gating for one source family — worth monitoring hl_copy cohort separately.
- SCORE-FLOOR (compactor side) still firing: 14 events per 2,000 log lines, every minute for heavily-penalized stuck signals (AVAX/ALT SHORT, product ~0.05 floored to 0.3). BUG-12 (rr_mult exemption) is implemented: `signal_compactor.py:2056-2080` `final = score * max(other_product, 0.3) * rr_mult`.

## 3. W1 (ema AT in compactor bear overrides) → **WARN — addressed, but WIDER than specified**

- Fixed in commit `a7484cbc` (2026-10-09) at both sites:
  - SHORT-RSI-FLOOR: `signal_compactor.py:3726-3729` — `_rsf_bearish = (_rsf_linreg in ('LEAN_BEAR','BEAR'))`
  - PUMP-CHAIN-SHORT-RSI-MIN: `signal_compactor.py:2991-2994` — same.
- **The ema condition was removed entirely, not widened to `('BELOW','AT')`.** Only BTC linreg bearishness (fresh <10 min) is required to bypass the oversold-SHORT blocks. Comment says "ema=AT is also bearish (at resistance)" but code dropped ema altogether.
- Practical effect so far (post-Oct-9 cohort, n=7 SHORTs, +$0.07): includes 1 SHORT entered at stored RSI 6.2 (pump-chain-v6 combo, −$0.02) — the BANANA falling-knife pattern (shorting extreme oversold) is structurally possible again. Small n, small damage, but this is the exact failure mode AGENTS.md warns about.
- Also note `SHORT_RSI_HARD_FLOOR = 45` (`hermes_constants.py:883`) is commented "No bearish override" — yet oversold SHORTs still executed post-fix (RSI 6.2 trade), so either the hard floor wasn't reached at exec time (DRIFT-E meta-vs-stored RSI) or a bypass path exists. Worth a targeted look by signal_analyst.

## 4. Candle Quality — Degradation? → **WARN — YES, degraded; known migration incomplete**

Measured directly from `data/candles.db`:

| Window | Total 1m | Real OHLC (H>L) | Volume>0 | Flat (O=H=L=C) |
|--------|----------|-----------------|----------|----------------|
| Last 30 min | 4,450 | **65.2%** | **85.8%** | 34.8% |
| Last 24 h | 252,473 | **64.6%** | **85.0%** | — |
| Last audit baseline | — | 88.8% | 95.9% | — |

Degradation is REAL and sustained (not a 30-min blip), but it is **highly concentrated**:
- Majors are perfect: BTC/ETH/BNB/NEAR/PUMP/SAND all **100% real OHLC** (fast-1m loop covers them).
- A tail of ~12+ alt tokens is near-fully flat: SOPH 2.5%, ANIME 3.6%, FOGO 5.7%, TNSR 6.7%, POLYX 7.6%, ENS 8.0%, PNUT 8.8%, BANANA 9.1% real — all with **is_closed=1** flat volume=0 candles.

Root cause: `hermes-1m-candle.service` (the tick aggregator `_aggregate_1m.py`) is **still scheduled and running every minute** — it gap-fills flat closed candles (≥3 same-price ticks passes MIN_BARS=3) for tokens the fast-1m loop hasn't reached yet (60 of 178 tokens per run, ~6-min full rotation). INSERT OR IGNORE protects real candles from being overwritten, but the aggregator still writes first for tail tokens. This matches the CEO's own BUG-048 diagnosis (kanban 2026-10-09 22:30: "aggregator stays dead... DELEGATE bug_hunter: fast 1m loop + 48h soak then DELETE aggregator + prune stuck rows; metric checkpoint Oct 12: alt RSI p90 staleness <180s"). **The deletion has not happened yet** — aggregator memory footprint is 1.3 GB scanning a 13.4M-row price_history per token per minute.
- price_collector service: healthy. 0 "database is locked" errors in journalctl (24h) and 0 in pipeline.log (20k lines). Candles advancing normally (5m/15m/1h/4h last-closed windows all current).
- Risk note: flat candles have zero range → ATR/BB-width computed on affected tokens are wrong (understated). RSI (close-based) is roughly OK but stale (~155s ticks). Since ATR feeds SL/TP and the hard_max_loss threshold, tail-token trades ride on degraded structure data until the aggregator is deleted.

## 5. hard_max_loss Bleed — Still #1? → **WARN — YES, still #1; leverage fix implemented, bleed persists**

- Since Oct 6 (postgres `brain`): **32 trades, −$3.79**, avg pnl −3.04% account, avg leverage 3.9 → **41.6% of ALL closed trades** exit via hard_max_loss. Next-worst exit (atr_sl_hit) is −$0.50. Unambiguously the top bleed.
- Persistent, not a spike: −$1.43 (Oct 5), −$0.96, −$0.61, −$0.74, −$0.58, −$0.90 (Oct 10) ≈ **−$0.87/day every day**.
- **The leverage-aware fix IS implemented** (`position_manager.py:3432-3459`): `HARD_MAX_LOSS_PCT = CUT_LOSER_PNL_HERMES / leverage` (CEO 2026-10-07, commit aed0aa36 per kanban; pre-fix was 58T −$8.11), plus D3 trail-min-gap floor (−0.60% price) and ATR widening. Live fires confirm it: `WCT LONG −0.89% [>−0.841% @ lev 3.0 atr=1.68]` — threshold correctly scales with leverage and ATR.
- Diagnosis: the exit is doing its job (capping); the problem is **entry quality** — 6.4 trades/day open and immediately go against. Thresholds fire at −0.67% to −0.89% price (−2% to −2.7% account at lev 3) — very tight, meaning entries have almost no immediate edge. Loosening HML (already done: −1.50%→−2.00% account, commit 7fc1ffda) trades bleed for depth; the fix belongs upstream at entry gates, not in HML.

## 6. SHORT WR 26.3% — Why So Low? → **WARN — low WR is structural; payoffs cover it (for now)**

- Since Oct 6: SHORT 19T **+$0.31 net, 26.3% WR** — confirmed reproducible.
- **Yes, wins are bigger than losses**: avg win **+$0.33** vs avg loss **−$0.10** (3.3:1 payoff). 5 wins pay for 14 losses. This is a legit asymmetry profile (likely ATR trailing on dumps), not luck-free money, but it IS net positive.
- Entry RSI: overall SHORT avg 34.5; pump-chain- (14T, +$0.54, 28.6% WR) avg entry RSI **29.6** — systematically deep-oversold entries, enabled by the W1 bear override (§3). One entry at RSI 6.2.
- Signal breakdown since Oct 6: pump-chain- 14T +$0.54 | hmacd_mtf-- 3T −$0.07 | ai-trader-,hmacd_mtf-- 1T −$0.14 | pump-chain-v6 combo 1T −$0.02.
- Post-Oct-9 (W1 widened) SHORT cohort: 7T +$0.07 — RSI<25 band 1T −$0.02 (0% WR), 35-45 band 1T +$0.37 (the one winner carried the cohort). The oversold-bypass is not paying for itself yet.

## 7. New Signals — Identified → **PASS**

- **r2v2-long8** = `scripts/signals/r2_trend_v2_long.py` (source prefix `r2v2-long{N}`, variant 8, `R2_TREND_V2_LONG_ENABLED = True`). R² Trend Confirmation v2: OLS regression on 1m candles; fires LONG when R² ≥ threshold, slope > 0, price above the regression line (plus slope/speed/RSI/BB/acel filters). History: 2T since Oct 6 — BABY +$0.03, WCT −$0.11 (the WCT trade hit hard_max_loss at −0.89% @ lev 3 and closed 15:16; it is no longer open).
- **ai-trader+** = `scripts/signals/ai_trader_signal.py` (`AI_TRADER_ENABLED = True`). The Trade Watchdog (external opencode agent, every 30 min) picks ONE coin hourly → writes `ai_trader_state.json` → this signal re-emits via `add_signal()` so the normal pipeline (compactor→hotset→guardian) handles execution. `ai-trader+` = LONG, `ai-trader-` = SHORT. History since Oct 6: 5T — 4 LONG wins +$0.20 (100% WR, hence the brief's stat), 1 SHORT loss −$0.14. n=5, not yet a track record.

## 8. Live Pipeline Health → **PASS**

- `Traceback|ERROR|CRASH`: **0** in last 200 lines and **0** in last 20,000 lines. **0** "database is locked" anywhere.
- Compaction cycles: 9 in the last hour (1-min timer nominal). Hotset writing normally (latest: ETH:LONG hmacd_mtf-+ conf 81 score 109, 1 token).
- Recent EXECs flowing (ETH hmacd_mtf-+, ZORA bb-squeeze+ every minute — both currently blocked/re-executing cycle; note ZORA is executing despite the CEO commit saying "ZORA stays blocked (35%)" — the REGIME_CONF_HIGH_MULT 0.70 lift now admits it at conf 150. That is the documented intent of 3ad6f87b, but ZORA's 35% all-time WR was the stated reason to keep it out — monitor the revert trigger).
- Transient WCT orphan race (15:17-15:22): position manager closed WCT via hard_max_loss while guardian briefly saw it as an HL orphan; guardian ran a market close, fill confirmed, PnL backfilled (−$0.107), stale marker cleared at 15:22. Self-resolved, no double-close, no leaked position. 0 open positions in DB now.
- Side observation: EXEC confidences can exceed 100% (ETH conf=156%, ZORA conf=150%) — confidence is unbounded above (confluence stacking). The penalty gate still scales it proportionally so gating logic is unaffected, but >100% values are meaningless for the MIN_EXEC_CONFIDENCE comparison headroom and make logs hard to read. Cosmetic; suggest a cap or log normalization.

## 9. Constants Drift → **PASS — all legitimate, documented CEO decisions with revert triggers**

`git log --since 2026-10-06 -- scripts/hermes_constants.py` — every change matches a CEO kanban entry with data backing and an explicit revert trigger:

| Change | Commit | Kanban rationale | Revert trigger |
|--------|--------|------------------|----------------|
| REGIME_CONF_HIGH_MULT 0.50→0.70 | 3ad6f87b | Sep 26 "dead zone" data stale; last 14d HIGH 52.0% WR; bb-squeeze+ HIGH 61.5% WR | 7d HIGH WR <45% or PnL worse than −$2/7d |
| LONG momentum override 1.0%→0.75% | d336a338 | 21d cohort data; delta 0.75-vs-1.0 = $0.08 = noise; anti-churn freeze | n≥10 cohort WR<40% or PnL<−$1.00/14d → revert to 1.5% (not 1.0%); no edit before Oct 24 |
| VOLUME_BREAKOUT_PLUS re-enabled | 764a5ad9 | chop losses were regime issue; RSI ceiling 85 in place | monitor 7d |
| VOLUME_BREAKOUT_LONG_RSI_CEILING 95→85 | 20c0afb7 | bleed starts at RSI 80 (BABY@81.82 → HML) | revert to 95 if 80-85 band proves profitable |
| LONG_RSI_CEILING 85→75 | c22f7407 | meta-RSI 30d: 75-80 band −$0.45 | — |
| hard_max_loss −1.50%→−2.00% account | 7fc1ffda | magnitude fix follow-through | — |

Protected flags verified intact: `LIVE_TRADING_ENABLED = True`, runtime kill switch `/var/www/hermes/data/hype_live_trading.json` = `{"live_trading": true}`, `STANDALONE_BYPASS_SIGNALS` present, R2/AI-TRADER enables true. No unauthorized edits found.

## 10. Overall System Assessment → **Net positive post-fixes, but oscillating around breakeven**

Performance windows (postgres `brain`, verified by direct query):

| Window | Trades | Net PnL | WR |
|--------|--------|---------|-----|
| Since Oct 6 fixes | 77 | **+$0.29** | 36.4% |
| Today (Oct 10, partial) | 22 | −$0.09 | 50.0% |
| 7d | 156 | **−$1.38** | 46.8% |
| 14d | 344 | +$1.16 | 49.7% |
| 30d | 801 | −$3.30 | 48.6% |

- Post-fix cohort is net POSITIVE but on a 36.4% WR — the system is surviving on payoff asymmetry (SHORTs 3.3:1, LONGs 1.5:1), not on win rate. One bad asymmetry week and it flips.
- 7d flipped negative (−$1.38) vs the Oct 9 kanban reading (+$0.29) mostly via window churn (Oct 2 positive days rolling out) plus the −$0.39 from Oct 9 late + Oct 10 — daily PnL since Oct 6: −0.54, +0.50, +0.72, −0.30, −0.09. Oscillation around zero, no trend.
- Trending toward profitability? Not demonstrably. It stopped bleeding hard (the catastrophic days are gone) but has not established a positive daily run rate.

**Top 3 remaining issues:**
1. **hard_max_loss = 41.6% of closes, −$3.79 since Oct 6 (−$0.87/day, every day).** The leverage-aware exit works; the entries are the problem. Highest-leverage action: entry-quality gates on the signals feeding HML (pump-chain± at avg lev 4-5 with near-zero immediate edge).
2. **Candle quality degraded to 64.6%/85.0% (real OHLC/volume) and the aggregator is still running.** BUG-048's "delete aggregator after 48h soak" (committed Oct 9 22:30) is now overdue; tail tokens (SOPH/ANIME/FOGO/TNSR/POLYX/ENS/PNUT/BANANA) are ~97% flat closed candles feeding wrong ATR/BB into SL/TP for any trade on them. Checkpoint Oct 12 (alt RSI p90 staleness <180s) should not be judged before deletion + stuck-row prune.
3. **W1's oversold-SHORT bypass is wider than intended and 36.4% post-fix WR is fragile.** The ema condition was removed entirely; SHORT entries at RSI 6-30 are possible again with only BTC linreg bearishness as the gate. The cohort is currently net positive only because one +$0.37 win carried it. Recommend: restore an ema floor (BELOW/AT) or add a hard RSI<25 block that no bear override can bypass (the BANANA lesson), and reconcile with SHORT_RSI_HARD_FLOOR's "no override" claim.

**Fix 1 status: IMPLEMENTED and LIVE** (commit a3183aea + hl_copy exemption amendment) — no longer open.

---
*All numbers in this report were produced by direct queries (psql on `brain`, sqlite on `candles.db`, greps on live logs) during 15:15-15:35 UTC 2026-10-10. Note: the brief's "76 trades today" is actually the since-Oct-6 cohort (77T by close of this audit); actual Oct 10 closes = 22.*
