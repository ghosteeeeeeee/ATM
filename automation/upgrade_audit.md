# Upgrade Audit Trail

## Plan: 2026-08-12_directional-outcome-tracker-spec.md
- **Date scanned:** 2026-08-13 04:30
- **Core request:** Real-time regime shift detector using trade outcomes as leading indicator
- **Difficulty:** Level 2
- **Value:** HIGH
- **Status:** PARTIALLY IMPLEMENTED — Component 1 (Signal Gate) live, Component 2 (Position Shield) unblocked but pending
- **Reason:** Component 1 fully functional with hysteresis, velocity tiers, integral, Direction Lock. Component 2 needs TPSL integration — deferred.

## Plan: 2026-08-13_progressive-context-shaping-spec.md
- **Date scanned:** 2026-08-13 04:30
- **Core request:** Structured agent state between sessions via CURRENT.md
- **Difficulty:** Level 2
- **Value:** MEDIUM
- **Status:** PARTIALLY IMPLEMENTED — CURRENT.md created, agent prompt wiring pending
- **Reason:** CURRENT.md exists and is used. Orchestrator/CEO prompt wiring requires prompt file changes — deferred.

## Plan: 2026-08-13_weather-vane-v2-spec.md
- **Date scanned:** 2026-08-13 04:30
- **Core request:** Autopilot-inspired improvements: hysteresis, derivative, integral, direction lock
- **Difficulty:** Level 1-2
- **Value:** HIGH
- **Status:** ✅ FULLY IMPLEMENTED — hysteresis, velocity tiers, integral, off-course alarm, Direction Lock all live
- **Reason:** Direction Lock implemented 2026-08-13. After catastrophic loss (4+/5), direction locked for 30min — no unsuppression during lock.

## Plan: 2026-08-13_weather-vane-v3-spec.md
- **Date scanned:** 2026-08-13 04:30
- **Core request:** Z-Score + Acceleration alignment filter (surfing.md quadrants)
- **Difficulty:** Level 2
- **Value:** HIGH (52pt WR gap between best/worst quadrants)
- **Status:** ✅ ALREADY IMPLEMENTED — hard block in decider_run.py:766-770
- **Reason:** Spec proposed soft penalty in signal_compactor, but decider_run.py already has hard block (SKIP) for misaligned quadrants. Hard block is strictly better — why penalize 23.8% WR when you can block it entirely.

## Plan: 2026-08-15_weather-vane-v4-tide-detection.md
- **Date scanned:** 2026-08-13 04:30
- **Core request:** BTC 3h momentum as fastest lagging indicator for tide detection
- **Difficulty:** Level 2
- **Value:** HIGH (70.6% WR on SHORT when BTC falling)
- **Status:** ✅ IMPLEMENTED — get_tide_penalty() in signal_compactor.py
- **Reason:** BTC 3h momentum + SHORT WR confirmation. Bearish tide: BTC falling + SHORT WR>55% → suppress LONG. Bullish tide: BTC rising + SHORT WR<45% → suppress SHORT.

## Plan: 2026-08-15_weather-vane-v5-volatility-floor.md
- **Date scanned:** 2026-08-14 15:03
- **Core request:** Filter out low-volatility entries (no energy = no trade)
- **Difficulty:** Level 1
- **Value:** HIGH ($1.79/14d SHORT savings, 74% WR on kept trades)
- **Status:** ❌ NOT IMPLEMENTED
- **Reason:** Backtested and validated. Simple single-function addition. Lowest-hanging fruit.
