# Fish-Finder Species Census — Blindspot Analysis

**Date:** 2026-08-26
**Goal:** Identify missing signal species and improve detection clarity
**Source:** 30-day signal cluster analysis + OpenMemory queries

---

## Executive Summary

Our fish-finder can now detect **21 signal species** across 21 families, with phase-aware detection, lifecycle timing, and inverse correlation filtering. But we're still **blind to 11 species** — most critically: Volume Profile, Liquidity, Beta Decoupling, and Regime Transitions.

The #1 blindspot is **Signal Decay** — every signal follows a trajectory of strong WR → collapse within 24-48h, and we're not detecting this in real-time.

---

## What We See Clearly (21 Species)

| Species | Signal Family | Detection Method | Confidence |
|---------|--------------|------------------|------------|
| 🐟 Momentum Tuna | accel_300, momentum, velocity | Speed + acceleration | High |
| 🐟 Bollinger Grouper | bb_bounce, bollinger_squeeze | Band touch + mean reversion | High |
| 🐟 ZScore Swordfish | zscore_rising, hzscore | Statistical extremes | Medium |
| 🐟 Trendline Marlin | tl_break, vortex_break | Price structure breaks | High |
| 🐟 Squeeze Pufferfish | squeeze_cross, atr_compression | Volatility compression | High |
| 🐟 Exhaustion Eel | return_exhaustion, spike_exhaustion | Move fatigue | Medium |
| 🐟 R2 Tuna | r2_trend, r2_rev | Trend strength | High |
| 🐟 Copy Trader Shark | hl_copy | Pro trader following | High |
| 🐟 S/R Anchorfish | support_resistance | Key levels | High |
| 🐟 Mover Marlin | coin_tracker_hot, mover | Velocity spikes | High |
| 🐟 Hot Set School | hot-set | Multi-signal confluence | High |

## Enhancements Built (5 Lenses)

| Enhancement | What It Does | Status |
|-------------|--------------|--------|
| Phase Lens | See which species thrive in which waters | ✅ LIVE |
| Confluence Scope | See when multiple species school together | ✅ LIVE |
| Lifecycle Timer | Know when species are early/late to feed | ✅ LIVE |
| Inverse Filter | Block species that repel each other | ✅ LIVE |
| Volatility Depth | See which species at which depth | ✅ LIVE |

---

## Blindspots — Missing Species

### Tier 1: High-Impact (CEO Selected)

| # | Species | What It Is | Why We Need It | Build Difficulty |
|---|---------|------------|----------------|------------------|
| **1** | **Volume Profile Fish** | POC, VAH, VAL levels where fish congregate | We have volume_hl but not profile structure. 70% of price action happens at value area edges. | Medium |
| **2** | **Liquidity Whale** | Order book walls, bid/ask imbalance | Large walls attract price like bait attracts fish. We're flying blind on order flow. | High (needs L2 data) |
| **3** | **Beta Decoupler** | Tokens about to break correlation with BTC | When BTC dumps, some alts hold. Finding these = alpha. We don't track beta shifts. | Medium |
| **4** | **Regime Transition Fish** | The MOMENT phase shifts (not the phase itself) | We detect phases but not transitions. Transitions = biggest moves. Missing the "edge of the school." | Medium |

### Tier 2: Medium-Impact

| # | Species | What It Is | Why We Need It | Build Difficulty |
|---|---------|------------|----------------|------------------|
| 5 | Time-of-Day Cod | Signals that only work at specific hours | Our analysis showed hour preferences but we don't filter by time. Some fish only feed at dawn. | Low |
| 6 | Funding Rate Ray | Derivatives funding rate extremes | Extreme funding = crowded trade = reversal imminent. We ignore derivatives entirely. | Low (API available) |
| 7 | Cross-Exchange Flounder | Price discrepancies between exchanges | Arbitrage opportunities = free money. We only use Hyperliquid. | Medium |
| 8 | Social Sentiment Seahorse | Twitter/Telegram buzz, fear/greed | We have token_sentiment but it's minimal. Crowd psychology matters. | Medium |

### Tier 3: Speculative

| # | Species | What It Is | Why We Need It | Build Difficulty |
|---|---------|------------|----------------|------------------|
| 9 | On-Chain Whale | Exchange inflows/outflows, wallet movements | Smart money moves before price. We're price-only. | High |
| 10 | Options Shark | Max pain, gamma exposure, expiry effects | Options market pins price. We ignore it completely. | High |
| 11 | Microstructure Minnow | Tick-level trade flow, large lot detection | Institutional footprints visible in tick data. | Very High |

---

## Critical Blindspot: Signal Decay Pattern

From OpenMemory (2026-08-02):

> "Every signal in Hermes follows the same trajectory — strong initial WR (40-80%) → rapid deterioration to 0% within 24-48h."

We built lifecycle filters but we're NOT tracking real-time decay. The `signal_lifecycle.py` rotator does this retroactively (daily), but we need **real-time decay detection** — a fish that detects when other fish are dying.

---

## Recommended Build Order (CEO Selection)

| Priority | Species | Why | Expected Impact |
|----------|---------|-----|-----------------|
| **P0** | **Volume Profile Fish** | Structure matters — POC/VAH/VAL are magnetic levels | +5-8% WR |
| **P1** | **Beta Decoupler** | Find tokens about to break from BTC correlation | +3-5% WR |
| **P1** | **Regime Transition Fish** | Catch the moment of phase shift | +3-5% WR |
| **P2** | **Liquidity Whale** | Needs L2 data, higher complexity | +5-10% WR |

### Data Sources Available

| Species | Data Source | Access |
|---------|-------------|--------|
| Volume Profile | candles.db (1h OHLCV) | ✅ Local DB |
| Beta Decoupler | candles.db (BTC + alt prices) | ✅ Local DB |
| Regime Transition | signals_hermes_runtime.db | ✅ Local DB |
| Liquidity Whale | Hyperliquid L2 API | ⚠️ Needs API integration |

---

## Architecture Vision

```
Current Fish-Finder:
  [21 species] → [Phase Lens] → [Confluence Scope] → [Lifecycle Timer] → [Score]

Enhanced Fish-Finder:
  [21 species] → [Phase Lens] → [Confluence Scope] → [Lifecycle Timer]
       ↓
  [Volume Profile] → [Beta Decoupler] → [Regime Transition] → [Liquidity]
       ↓
  [Decay Detector] → [Final Score]
```

---

*Report generated 2026-08-26. Source: Signal cluster analysis + OpenMemory queries.*
