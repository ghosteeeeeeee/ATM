# Transcript Mining Report

**Source**: Wall St Trader Youve Been Lied To About Trading I Built A 10Yr Track Record To P.md  
**Date**: 2026-11-08  
**Author**: Michael Wallace (guest, ex-Merrill/Lehman, traded alongside Soros/PTJ desks) — "Titans of Tomorrow" podcast  
**Credits**: Larry Williams — *The Definitive Guide to Futures Trading Vol. 2* (1989), money management chapter; Edward O. Thorp — *Beat the Dealer* / *Beat the Market*

## TL;DR

- **Core thesis**: short-term trading = gambling (randomness has trends — a system winning 6 months can be pure noise). Accept it, then apply *gambling* strategy: bet more when odds favor you, less when they don't (MIT card-counting logic).
- His stack of **4 biases per trade**: (1) structural long-term up bias, (2) short-term weakness mean-reversion bias, (3) historical streak bound (SPY max 7 down days in 33 yrs → enter at 4), (4) first-win-after-streak is *larger* than normal (rubber band). Only trade when all line up.
- **Fractional Martingale**: enter after 4 down days, +50% size after each subsequent loss day — the win pays for all prior losses → 90% "win rate". No stops (1-day horizon, "end-of-the-world stop" only), exit next close, long-only, never trail after the win.
- Track record: CPA-audited, no losing futures month 2023→present (~46 months); 2023 +66%, 2024 +51%, 2025 +48%; Sharpe ~2; admits 7–8% intra-trade drawdown.
- **"No discretion": computer gives signals from hundreds of price patterns; he executes. "If I add discretion, I'll lose."**

## Ideas

### 1. Streak Analysis: does LOSS_COOLDOWN help or hurt us?
- **What**: His edge premise is bounded streaks (max 7 down days in 33 years). The testable core: after N consecutive losses on a signal source, is next-trade WR better or worse? Also: what IS our max consecutive-loss streak per source/token — is it bounded like SPY's 7?
- **Why Hermes**: We run LOSS_COOLDOWN (20min→90min exponential) on consecutive losses — built on the assumption streaks predict more losses. Wallace claims the opposite conditional (odds IMPROVE after streaks because of structural bias). One of us is wrong for our data. Direct test feeds a calibration ruling on LOSS_COOLDOWN_BASE/MAX (values need T — analysis first).
- **Where**: PostgreSQL query + analysis script; informs `hermes_constants.py` LOSS_COOLDOWN_* (T-gated).
- **Effort**: small (read-only SQL analysis)
- **Priority**: **quick win** — but must follow THE PATTERN (n, p-values, OOS, reproduce cmd)

### 2. First-Win-After-Streak Size Effect (rubber band)
- **What**: Claim — after multiple consecutive losses, the eventual win is statistically LARGER than a normal win. He uses it to justify Martingale sizing.
- **Why Hermes**: If true, our streak-based responses (cooldown, DRAWDOWN tier size *reduction*) are fighting the effect. Test: MFE/R:R of first win after ≥2 consecutive source losses vs baseline win MFE. Pairs directly with idea 1 (run together).
- **Where**: Same analysis as #1 — one script, two questions.
- **Effort**: small
- **Priority**: **quick win**

### 3. Event-Completion Exits for Mean-Reversion Signals
- **What**: Exit when the statistical window that defined the edge RESOLVES (his: next close), not when price says so. Key quote: after the predicted win day arrives, "my odds have just plummeted" if you stay in — you've met your statistical mean; trailing past it degrades the edge.
- **Why Hermes**: Our mean-reversion signals (bb_bounce, return_exhaustion, zscore_rising, r2_rev family) hold with price-based exits (SL/TP/trail). Their edge thesis is a reversion event — once reverted, the odds rationale expires but we hold hoping for more (trail can keep us in a decayed setup). Candidate: horizon/event-based exit for pure mean-reversion sources — exit when z-score normalizes or the reversion candle completes, regardless of trail state.
- **Where**: New signal family flag in `scripts/signals/` (mean-reversion sources) + exit clause in `tpsl_utils.py` / position_manager. Needs analysis of our own MFE-past-reversion first.
- **Effort**: medium
- **Priority**: worth discussing (analysis first: does MFE stall after reversion completes?)

### 4. Formal Randomness Null Test per Signal Source
- **What**: His central claim — most "winning systems" are indistinguishable from randomness (coin flips produce trends; a daily flip needs *years* to revert to mean). Edward Thorp: read *Beat the Dealer*/*Beat the Market*.
- **Why Hermes**: We gate on WR thresholds (35% blacklist, SIGNAL_QUALITY) but a stricter framing: per-source binomial test of observed WR vs null, with streak-calibrated confidence — "is this source distinguishable from a coin at all?" The winrate-calculator skill may already approximate this; check before building (repo rule: search before building).
- **Where**: `skills/.../winrate-calculator` or signal-quality gate — check existing first.
- **Effort**: small (likely reuse)
- **Priority**: worth discussing

### 5. Vindications (no action — validates our design)
- **No discretion / computer executes** → our deterministic signal_compactor + bounded LLM context gate is the same doctrine.
- **Stack 3–4 biases before entry** → our confluence gate (2+ source types) + regime + speed/z alignment is exactly this.
- **"95% lose, so 95% of what you're taught is wrong"** → our THE PATTERN discipline (verify against data, not teachings).
- **Focus markets you know deeply** → FAVORITES/token-performance/blacklists = knowing our tokens' personalities.

## Quick Wins (do today)

1. **Combined streak analysis** (ideas 1+2 in one read-only script): per top signal sources — max consecutive losses, WR after 1st/2nd/3rd loss, first-win-after-streak MFE vs baseline. Reproduce cmd + n + p-values mandatory (THE PATTERN). Output: does our LOSS_COOLDOWN direction have data behind it?

## Worth Discussing

2. **Event-completion exits** for mean-reversion sources — analysis of MFE-past-reversion before any exit-logic change.
3. **Null test per source** — but check winrate-calculator skill first for existing coverage.

## Skip

- **Fractional Martingale sizing** — DANGER: works only while streak records hold; the first record streak (day 8) is ruin, and crypto streaks are unbounded (no structural 33-yr series to bound them). Our entire size architecture (DRAWDOWN tiers, KELLY quarter-fraction, heat limits) reduces after losses by design. Keep. His WR=90% is also an artifact of basket accounting (one win closes a losing sequence) — not comparable to our per-trade WR.
- **Long-only / never short** — stock-market-specific bias. Hermes philosophy is explicitly both directions with momentum.
- **QQQ 10%-correction margin investing** — long-term stocks, out of scope.
- **No-stop / 1-day horizon** — depends on T+1 close exits with no gap risk tolerance; our HL perps + ATR SL architecture already differs appropriately.

## Known flaw to remember (streak reasoning)

"Max 7 down days in 33 years" is an **in-sample max, not a bound** — Martingale works until the first day that exceeds the record, which by definition never appeared in the sample. His own admission (7–8% intra-trade DD, "we will have losing months eventually") confirms the tail is unmanaged. Any streak-based idea we adopt must use our own measured streak distribution with tail headroom — never a historical max as a hard floor.
