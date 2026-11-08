# Transcript Mining Report

**Source**: How To Actually Build an AI Trading Bot With Claude 3 Hour Course.md  
**Date**: 2026-11-08  
**Author**: Brendan (ex-investment banking, UCLA math/econ, builds Claude trading systems for clients)

## TL;DR

- **The ALPHA framework**: Architecture → Logic → Proof → Harness → Adapt. Most trading bot tutorials stop at Harness; Adapt (when to kill/rotate strategies) is where systems survive long-term.
- **The 7-gate funnel** is the most actionable methodology in the video: cost → next-open fills → recent data → locked test → return/drawdown → trade count → neighbor test. 44 ideas → 7 survivors.
- **We are likely overfitting.** Hermes tunes constants (ATR_SL, thresholds) directly on recent data with no locked test and no neighbor checks. This is mistakes #1 and #2 in his top-10 list.
- **Kill lines pre-committed before losing money**: auto-remove a strategy at 2× its worst tested drawdown. Removal reasons are written down in advance so you never decide while losing.
- **Paper-vs-backtest reconciliation** with gap categorization (fills/timing/data/rounding/limits/rules) — we don't do this, and it would catch live-vs-signal drift.

## The ALPHA Framework

| Letter | Content | Hermes mapping |
|--------|---------|----------------|
| **A**rchitecture | Prompts vs skills vs schedules; bot vs system | We have skills + systemd timers ✓ |
| **L**ogic | Data, asset study, regimes, rules that can be tested | Regime scanners ✓, signal files ✓ |
| **P**roof | Testing methodology — the heart of the course | ⚠️ **Biggest gap** |
| **H**arness | Broker, schedule, safety, automation ladder | Kill switch + pipeline ✓ |
| **A**dapt | Kill, rotate, review — strategy lifecycle | ⚠️ **Second gap** |

## Ideas

### 1. Locked Test Protocol (out-of-sample we don't have)
- **What**: Split data — tune on 2022-2024, then run ONCE on 2025+ data the strategy has never seen. If it fails, go back to ideas — never tweak the rule and re-run (that converts test data into training data).
- **Why Hermes**: We tune ATR_SL_MIN, SIGNAL_FILTER thresholds, phase k-multipliers directly on recent trade data, then judge them on the same data. Our "30-trade multi-token validation" for trailing SL (2026-08-14) used the same window for tuning and evaluation. We have no locked test.
- **Where**: New `scripts/backtest_split.py` + discipline in every signal-tuning session. ADBE: any threshold change must be validated on a time window not used to derive it.
- **Effort**: medium
- **Priority**: **must-have**

### 2. Neighbor Test (robustness check)
- **What**: After tuning a parameter, test ±steps around it. If 200-day MA works but 199/201/250 collapse, it's luck (spike), not an edge (hill). A real edge looks like a hill — neighbors also work.
- **Why Hermes**: We tune ATR_SL_MIN=1.2% (was 1.0%), ATR_TP_K_MULT=2.0 (tried 2.5, reverted), SIGNAL_FILTER_SPEED_MIN=40 (was 30). Did we ever check 1.1%/1.3%? 2.2? 35? Our constant history in `hermes_constants.py` reads like isolated spikes, not hills.
- **Where**: Add neighbor sweep to `signal-lab`/`signal-backtest` skills as a mandatory step.
- **Effort**: small (harness exists, add sweep)
- **Priority**: **must-have**

### 3. Test the Backtester First (planted edge)
- **What**: Before trusting backtest results, feed synthetic prices with a known planted edge (e.g., +1% after each signal). Engine must report ~1% minus costs. If not, the engine has a bug.
- **Why Hermes**: Our backtests go through signal-lab but I don't know of a synthetic-data engine validation. A bug in fill logic or cost accounting silently inflates every result.
- **Where**: `scripts/signal_backtest*.py` — add a `--self-test` mode with synthetic prices.
- **Effort**: small
- **Priority**: worth it

### 4. Kill Lines (pre-committed strategy removal)
- **What**: Each strategy gets a kill line = 2× its worst drawdown in testing, written down BEFORE live trading. Cross it → auto-off, sell next open, alert. Core gets alert-only (1.5× threshold), never auto-removed.
- **Why Hermes**: We auto-blacklist tokens at 35% WR / 5 trades / 7d and have DRAWDOWN_TIER circuit breakers. But per-signal kill lines based on *tested* drawdown don't exist. Our decay detector is WR-based, not drawdown-based. The "pre-committed" aspect is the key innovation — reasons written before losing money.
- **Where**: `hermes_constants.py` + `token_performance_monitor.py` — per-signal-source max drawdown limits.
- **Effort**: medium
- **Priority**: worth it

### 5. Trade-Frequency Deviation Check
- **What**: After 3 months live, if a strategy trades <½ or >2× its backtest frequency, flag for review. Market regime changed under it.
- **Why Hermes**: Directly connects to the exposure metric from the Connors video. We could track per-signal-source trades/hour vs its historical baseline. A signal that stops firing (or fires constantly) is a leading indicator of decay or a bug.
- **Where**: `token_performance_monitor.py` or a new signal health check.
- **Effort**: small
- **Priority**: **must-have** (pairs with exposure tracking)

### 6. Paper-vs-Backtest Reconciliation with Gap Categories
- **What**: Line up every live trade vs backtest side by side. Classify each gap into: fills, timing, data, rounding, limits, rules. One plain line per gap.
- **Why Hermes**: We have a known signal-detection-vs-execution-timing gap (CFX RSI example in AGENTS.md) but no systematic reconciliation. Classifying live-vs-expected gaps would catch drift like the v2 filter staleness bug — where conditions at execution ≠ conditions at detection.
- **Where**: New `scripts/reconcile_live_vs_signal.py` — compare `_signal_metadata` conditions at detection vs trade state at open.
- **Effort**: medium
- **Priority**: worth it

### 7. The Rule-Change Loop (no edits from recent results)
- **What**: Only path for a change: idea → same gates as new strategies → paper for weeks → switch on. "No rule changes because of a bad week." A change counts as a new idea: tested, logged, old version keeps trading until new one earns the swap.
- **Why Hermes**: Our ATR_SL widenings (1.0→1.2, 2.5→3.0) were made from 48h analysis — essentially reacting to a bad stretch. This discipline would have forced a proper backtest first. The `automatic-implementation` skill (shadow→enforce) is the right mechanism; the missing piece is the gates document.
- **Where**: `brain/SOPs.md` — formalize the change loop.
- **Effort**: small (documentation)
- **Priority**: **must-have**

### 8. Scheduled Claude Review (weekly/monthly/quarterly)
- **What**: Weekly: read logs, reconciliation, errors, kill-line distance. Monthly: each strategy gets keep/watch/review/out status vs its own testing baseline. Quarterly: re-run selection routine, propose swaps, WAIT for yes. Claude fixes code but NEVER changes rules.
- **Why Hermes**: We have post-change/bug-hunter verification but no scheduled tiered review. Monthly per-signal-source status (keep/watch/review/out) would formalize what's currently ad-hoc blacklist edits.
- **Where**: New systemd timer + `brain/reviews/` (follow our systemd-not-cron rule).
- **Effort**: medium
- **Priority**: worth it

### 9. Automation Ladder (alerts → approve → auto)
- **What**: Three levels of autonomy. Start at alerts (bot computes, you place), then approve (bot waits for yes), then full auto. Never jump to full.
- **Why Hermes**: We went paper → live with kill switch. The missing rung: we don't have an "approve" mode where signals are computed but require confirmation. Might be worth having for new signal sources during their first week (pairs with shadow mode).
- **Where**: `signal_schema.py` / decider — per-source `mode: alert|approve|auto`.
- **Effort**: medium
- **Priority**: future (shadow mode partially covers this)

### 10. Costs Scale with Frequency
- **What**: 0.05% each way sounds tiny: 5 trades/yr = 0.5% cost, 250 trades/yr = 25%/yr. Intraday needs bigger cost assumptions + more safety checks (feed drop → stop trading, alert).
- **Why Hermes**: We trade intraday on Hyperliquid with funding + fees. Do our backtests account for realistic total cost including funding rates and slippage? Worth verifying. Also: feed-drop safety check (candles stale > CANDLES_STALENESS_SEC exists ✓ but is it enforced at execution?).
- **Where**: Verify cost model in signal-backtest skills.
- **Effort**: small (audit)
- **Priority**: worth it

## Quick Wins (do today)

1. **Neighbor sweep discipline** — pick 3 recently tuned constants (ATR_SL_MIN, SIGNAL_FILTER_SPEED_MIN, ATR_TP_K_MULT), run ±2 steps on historical data, check for hill vs spike.
2. **Trade-frequency baseline** — record trades/hour per signal source now; alert on deviation from baseline.

## Worth Discussing

1. **Locked test protocol** — biggest structural gap. Needs a decision: what time window is locked, and a rule that we look at it once.
2. **Kill lines per signal source** — pre-committed drawdown limits beyond WR-based blacklisting.
3. **Reconciliation script** — catch detection-vs-execution drift systematically.

## Skip

- **Broker switching content** (Alpaca/IBKR/Schwab) — we're on Hyperliquid, already settled.
- **Options section** — out of scope for Hermes.
- **Fed statement AI layer** — crypto doesn't have Fed statements driving directly (macro does, but our regime scanners cover it).
- **Fully-AI-trades** — he agrees: untestable. Our deterministic compactor + bounded LLM gate is the right call (vindicates our design).

## The 10 Mistakes (mapped to Hermes)

| # | Mistake | Hermes exposure |
|---|---------|-----------------|
| 1 | Tuning until backtest looks perfect | 🔴 **High** — constants tuned on same data |
| 2 | Peeking at locked test | 🔴 **No locked test exists** |
| 3 | Look-ahead bias | 🟢 We detect at close, execute later (gap documented) |
| 4 | Forgetting costs | 🟡 Need to verify funding/slippage in backtests |
| 5 | Trusting unchecked backtester | 🟡 No planted-edge self-test |
| 6 | Small samples | 🟡 KELLY_MIN_TRADES=50 exists; signal tuning often uses 30 |
| 7 | Survivorship bias | 🟡 Token universe churns; delisted coins drop out |
| 8 | Fully AI trades | 🟢 Deterministic compactor, bounded LLM gate |
| 9 | Going too big too soon | 🟢 Paper first, kill switch, small sizing |
| 10 | Quitting after bad week | 🟡 ATR_SL widened after 48h losing stretch |
