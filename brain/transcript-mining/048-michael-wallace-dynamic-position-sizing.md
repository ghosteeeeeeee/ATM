# Transcript Mining Report

**Source**: 048 - Michael Wallace - Dynamic Position Sizing Like You Havent Seen Before.md  
**Date**: 2026-11-08  
**Author**: Michael Wallace (Wallace Investments) on The Algorithmic Advantage podcast  
**Lineage**: Larry Williams (*Definitive Guide to Futures Trading Vol. 2*, money management chapter) → Ralph Vince (Optimal F) → Ed Thorp (blackjack → hedge funds)

## TL;DR

- **Money management beats system quality.** Williams' slow-grind proof: identical pork-belly trades — system alone LOST money, same trades + money management MADE money. The system is just the seed; sizing creates the win.
- **The Pendulum Effect**: a system normally at 60% WR operating at 20-30% over its last 10 trades (esp. 3-4 losses in a row) has elevated odds of mean-reverting → **size UP on loss streaks, not equity highs.** First win after a drought is statistically larger (rubber-band effect).
- **Never size up because you made money** — "you'll trade your largest position at your worst drawdown and lose it twice as fast." Size by *probability of the next trade*, never by account equity. (Blackjack logic: increase when cards are better, decrease when worse.)
- **Drawdown-based sizing**: increase at historical drawdowns, revert to base at equity highs. Bounded, probability-conditioned — NOT raw martingale (host explicitly flags the quant criticism).
- **Consistency > headline returns**: clients accept 30% with near-zero drawdown over 200% with 40% DD. Short drawdowns (2-3 days) are the standout feature; Thorp lost 3 months in 20 years.
- **Stand aside on black swans** (~5% discretionary overlay), stop trading when beyond historical norms. Short-term (day–3day) is random; long-term has drift — two different philosophies.

## Ideas

### 1. Pendulum Effect — size up after loss streaks (OPPOSITE of our loss cooldowns)
- **What**: When a system with known 60% WR operates at ≤30% over its last 10 trades + 3 losses in a row, odds of mean-reversion rise → that's the signal to start/size UP. Backtested by Wallace on 30 years of data. Bonus: first win after drought is statistically much larger.
- **Why Hermes**: We run the **exact opposite**: `LOSS_COOLDOWN` (20→90min escalating block after consecutive losses) and `DIRECTIONAL_OUTCOME` weather vane (3/5 losses → 0.7 penalty + direction lock). Both assume loss streaks predict MORE losses. Williams' data says the reverse *at the system level*. **Critical distinction**: our cooldowns are per-token/per-direction (local), his pendulum is per-system (global) — they may both be right at different scopes. This is a testable tension, not a freebie.
- **Where**: `scripts/signal_compactor.py` scoring + a shadow counterfactual measuring: trades taken DURING our cooldown windows vs their forward returns. If the pendulum holds locally too, cooldowns are burning our best entries.
- **Effort**: medium (shadow counterfactual first)
- **Priority**: worth it — as a **shadow analysis**, never a direct flip (martingale-adjacent; host flagged quant criticism explicitly)

### 2. Size by next-trade probability, not equity (anti-Kelly-timing)
- **What**: Explicit rule — position size increases because ODDS improved (loss streak, drawdown, high-probability setup), never because the account grew. Never increase at equity highs.
- **Why Hermes**: Our `KELLY_ENABLED=False` sizing (when it activates) scales with bankroll — exactly what Wallace says fails. `FAVORITES_SIZE_MULT=1.5` sizes favorites bigger — that's odds-based (validated ✓). `DRAWDOWN_TIER` REDUCES size at drawdown — Wallace INCREASES at drawdown. But ours is account-level risk control (heat limit) and his is strategy-level edge-flooding; both defensible at their own scope. Worth a written clarification of *which* level each rule operates at.
- **Where**: `brain/SOPs.md` sizing-philosophy section + future Kelly activation review.
- **Effort**: trivial (documentation)
- **Priority**: quick win

### 3. Drawdown duration as a first-class metric
- **What**: Wallace's standout stat isn't DD depth — it's DD *duration* (2-3 days max, rarely weeks). Long drifting drawdowns destroy psychology and client relationships; clients trade 200%-with-40%-DD for 30%-with-no-DD.
- **Why Hermes**: We track DD depth (`DRAWDOWN_TIER_1/2_PCT`) but not DD duration per signal source or account. A source in a 3-day shallow DD is healthy; one in a 30-day shallow bleed is decaying — **duration separates regime-quiet from decay**, which is exactly what kill lines (item I, shadow-authorized) and the freq-deviation monitor (H, live) need as an additional limb.
- **Where**: `token_performance_monitor.py` or kill-line registry — add days-in-current-DD alongside depth.
- **Effort**: small
- **Priority**: worth it (feeds the already-authorized I shadow)

### 4. Stand-aside on chaotic events (black swan gate)
- **What**: ~5% discretionary overlay: stand aside on pandemics/black-swan events; stop trading when results exceed historical norms (1 trade beyond max). "Standing aside is the best risk aversion there is." Ironically his systems did BETTER in 2008/2020 (more weakness = more signals).
- **Why Hermes**: We have EXTREME phase + regime scanners + storm filters — partially covered. What we don't have: a *time-based* abnormality gate (e.g., volatility or loss rate exceeding historical max → halt-and-assess). Closest is `DIRECTIONAL_OUTCOME_LOCK` (30min) — much shorter than the weeks-scale events he means.
- **Where**: Would be a shadow-first gate in `hermes_constants.py` flags... but see Skip: our existing regime/phase layers may already cover this; audit before building.
- **Effort**: audit first (small), build only if gap real
- **Priority**: future

### 5. Low-frequency selectivity benchmark
- **What**: 30 systems, 2 markets, **2-3 trades per month**, daily bars (buy close/sell next close). Extreme selectivity + 89% backtested accuracy since 1993.
- **Why Hermes**: We run 60+ signal sources at high frequency. This is a data point for the exposure-adjusted-return thesis (Connors video): 20-30% time-in-market with high WR can beat constant exposure. Not a template to copy (crypto ≠ daily futures) but reinforces the exposure metric already queued (item D).
- **Where**: Reinforces existing queued work; no new build.
- **Effort**: none
- **Priority**: skip (already covered by D)

### 6. Host's 3-stage trader development (context)
- **What**: Stage 1 = indicator rabbit holes; Stage 2 = quantitative, limited by tools; Stage 3 = position sizing/capital management can transform poor strategies into profitable ones.
- **Why Hermes**: We're at stage 2-3 — the mined-ideas batch (locked test, neighbor test, kill lines) IS stage 3 work. Validates the current roadmap. No new action.
- **Effort**: none
- **Priority**: skip (philosophy)

## Quick Wins (do today)

1. **Sizing-philosophy note in SOPs** — write down which sizing rules are odds-based (FAVORITES_SIZE_MULT, future Kelly) vs equity/account-risk-based (DRAWDOWN_TIER, heat limit), and the Wallace warning: never grow size on equity highs alone.
2. **DD-duration query** — one SQL pass: per signal source, current drawdown depth + duration. Establishes the baseline metric for idea 3 and feeds kill lines.

## Worth Discussing

1. **Pendulum counterfactual** — measure forward returns of trades our LOSS_COOLDOWN/DIRECTIONAL_OUTCOME windows blocked. Shadow analysis; if blocked trades outperform, the cooldowns are inverted at local scope. Requires care: our cooldowns were tuned on our own data (and per THE PATTERN, needs independent verification before believing any result).
2. **DD-duration limb for kill lines** — extend item I's pre-registered bar with a duration component before I ships.

## Skip

- **Martingale/doubling** — host explicitly warns; quants reject non-independent sizing. Our bounded heat limits stay.
- **Return stacking / margin hedging** — equities+futures structure, not applicable to our single crypto account.
- **Roulette claims** — unverifiable, irrelevant.
- **Buying 10%-corrections on margin (actionable advice)** — long-only ETF investing advice, not for Hermes.

## Conflicts to Note (honesty)

The video's two core prescriptions **conflict with live Hermes mechanisms**:
1. Pendulum (size up after losses) vs `LOSS_COOLDOWN` + `DIRECTIONAL_OUTCOME` (penalize after losses).
2. Size up at drawdown vs `DRAWDOWN_TIER` (size down at drawdown).

Neither is a bug — they operate at different scopes (strategy-level vs account-level) and our versions were data-tuned. But the tension must be documented, and the pendulum limb deserves a shadow counterfactual before we keep assuming loss streaks = bad.
