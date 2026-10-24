# CEO Brief: Shadow-Mode Analysis — Recommendations Requested

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-24 13:50 UTC
**Priority:** HIGH — T requested CEO recommendations based on shadow data

## TLDR

Shadow-mode analysis complete (17,321 signals). Three critical findings:

1. **All gates are HELPING** — removing all gates would add ~$1,172 in losses
2. **Entries are the problem** — ALL SL levels show negative avg PnL (even 50% SL = -0.224%)
3. **Disabled signals are mostly worse** — 16 shadow-bypass signals show same or worse performance

**The core problem:** The exits work. The gates work. The entries don't. The signals that pass all gates still lose money on average.

## Current State

| Metric | Value |
|--------|-------|
| 24h trades | 14 |
| 24h WR | **57.1%** |
| 24h PnL | **+$0.25** (first positive!) |
| 7d trades | 121 |
| 7d WR | **40.5%** |
| 7d PnL | -$1.16 |

## Shadow Data Key Findings

### 1. All Gates Are HELPING

| Gate | Blocked | Would Win | Avg PnL | Verdict |
|------|---------|-----------|---------|---------|
| CONFLUENCE-EXPIRY | 9,637 | 48% | -0.11 | ✅ HELPING |
| CTX-GATE | 641 | 50% | -0.09 | ✅ HELPING |
| BTC-CRASH | 105 | 26% | -0.39 | ✅ STRONGLY HELPING |
| EXEC-BLOCK | 13 | 8% | -0.49 | ✅ STRONGLY HELPING |

**Removing all gates would add ~10,654 trades that lose -0.11 each = -$1,172 in losses.**

### 2. Entries Are the Problem (SL Sweep)

| SL Level | WR | Stopped | Avg PnL |
|----------|-----|---------|---------|
| 0.50% | 27.1% | 70% | -0.009% |
| 1.00% | 35.8% | 58% | -0.110% |
| 2.00% | 42.9% | 44% | -0.347% |
| 5.00% | 47.8% | 4% | -0.302% |
| 50.00% | 48.5% | 0% | -0.224% |

**Even with no stop-loss (50%), avg trade loses -0.224%.** The signals have negative expectancy before any filtering.

### 3. Disabled Signals Are Mostly Worse

| Signal | Trades | WR | Avg PnL | Total PnL | Why Disabled |
|--------|--------|-----|---------|-----------|--------------|
| ichimoku- | 1,591 | 61.1% | -0.109 | -$173.2 | SHORT-REGIME-GATE |
| ichimoku+ | 828 | 45.9% | -0.174 | -$144.1 | CONFLUENCE-GATE |
| volume-breakout-long+ | 182 | 22.5% | -0.339 | -$61.8 | KILLED Oct 13 |
| doji-bottom-long | 202 | 46.5% | -0.322 | -$65.0 | Needs different exit |
| bb-squeeze- | 165 | 50.9% | -0.198 | -$30.3 | SHORT side killed |
| open-skies+ | 22 | **13.6%** | -0.432 | -$9.5 | NEVER_REENABLE |

**Even the best disabled signal (ichimoku- at 61.1% WR) loses money** because avg win < avg loss.

### 4. Direction Matters: SHORT Beats LONG

| Direction | Trades | WR | Avg PnL |
|-----------|--------|-----|---------|
| SHORT | 10,089 | **52.3%** | -0.065 |
| LONG | 6,730 | 42.4% | -0.193 |

**SHORT is 10pp better than LONG.**

### 5. Only 4 Signals Positive (n≥20)

| Signal | Trades | WR | Avg PnL | Total |
|--------|--------|-----|---------|-------|
| volume_breakout_short | 123 | 39.8% | **+0.143** | +$17.5 |
| hl_copy_minus | 20 | 55.0% | +0.128 | +$2.6 |
| ai-trader | 39 | 48.7% | +0.051 | +$2.0 |
| grind_breakout_short | 79 | 41.8% | +0.001 | +$0.1 |

### 6. pump-chain Is #1 Bleeder

| Signal | Trades | WR | Avg PnL | Total |
|--------|--------|-----|---------|-------|
| pump-chain | 3,834 | 31.7% | -0.125 | **-$442.2** |
| squeeze_cross | 3,553 | 59.0% | -0.090 | -$295.4 |
| volume_buildup_short | 1,235 | 56.2% | -0.119 | -$146.8 |

### 7. Exit Engine A/B

| Engine | Trades | WR | Total PnL | Verdict |
|--------|--------|-----|-----------|---------|
| PM Trail | 6,141 | 100% | **+$2,266** | 🏆 BEST |
| ATR | 3,175 | 46% | +$262 | ✅ GOOD |
| rr_engine | 1,466 | 19% | **-$544** | ❌ BIG LOSER |
| hard_max | 4,095 | 0% | **-$3,863** | ❌ BIGGEST (by design) |

## CEO Recommendations Requested

### Question 1: Should we bias toward SHORT?

SHORT is 10pp better than LONG. Should we:
- (A) Reduce LONG exposure (fewer LONG signals admitted)
- (B) Increase SHORT exposure (more SHORT signals admitted)
- (C) Keep balanced

### Question 2: Should we disable pump-chain?

pump-chain is #1 bleeder: 3,834T, 31.7% WR, -$442.2. Should we:
- (A) Disable entirely
- (B) Tighten filters (higher conf threshold, regime restrictions)
- (C) Keep as-is (it provides signal diversity)

### Question 3: Should we focus on the 4 positive signals?

Only volume_breakout_short, hl_copy_minus, ai-trader, grind_breakout_short are positive with n≥20. Should we:
- (A) Boost these signals (higher size, priority execution)
- (B) Disable everything else (trade only these 4)
- (C) Keep current allocation

### Question 4: Should we investigate RR Engine?

rr_engine is a big loser: -$544 total, 19% WR. Should we:
- (A) Disable entirely
- (B) Re-tune parameters
- (C) Keep as-is (it's a small portion of trades)

### Question 5: What's the path to positive expectancy?

The core problem is entries have negative expectancy. What's the CEO's recommendation?
- (A) Build new signals with positive expectancy (spec v1.3 shadow engine)
- (B) Tighten existing signals (higher conf, stricter filters)
- (C) Accept current performance and optimize exits further

## Protected Flags

13/13 INTACT. No config changed in this brief.
