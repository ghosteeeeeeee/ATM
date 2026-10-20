# CEO Brief: BTC Bullish Breakout, Signals Flowing, But Only 1 Trade Open

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-19 20:50 UTC
**Priority:** HIGH — T is frustrated, system is throttled

## TLDR

T's report: "BTC just broke out bullish, we've got signals coming in, and we're sitting with 1 system trade open. We're not going to get anywhere this way."

**The data confirms the frustration:**

1. **BTC broke out bullish** — price above EMA300, momentum positive
2. **Signals are flowing** — 850+ signals detected in 24h
3. **Only 1 system trade open** — the compactor/hotset/decider funnel is eating almost everything
4. **7d WR 34.0%** (68/200) — stuck below 35% guardrail threshold
5. **Guardrail at 50% size** — reduces PnL per win, slower WR recovery

## Current State (Verified)

- **24h:** 17 trades, 8W, −$0.38, 47.1% WR
- **7d:** 200 trades, 68W, −$4.01, 34.0% WR
- **Open positions:** 1 (system trade)
- **Hotset:** 84 non-empty writes today (NOT empty — audit corrected earlier false claim)
- **Compactor:** runs every minute, queries 3-5 combo_keys/cycle, writes 0-1 tokens to hotset
- **Decider:** 142 EXEC attempts today, 17 trades in PostgreSQL

## The Bottleneck (From Independent Audit)

Gate kill census (2026-10-19, full day):
```
936 CONFLUENCE-GATE-BLOCK    ← #1 (ichimoku single-source: 123 signals that can never pass)
848 SHORT-RSI-HARD-FLOOR     ← #2 (reverted 35→45 on Oct 18)
695 PUMP-CHAIN-SHORT-HIGH    ← #3 (pump-chain- SHORT blocked in HIGH)
636 VOL-GATE-BYPASS          ← #4 (pump-chain- SHORT blocked in EXTREME)
535 CONTINUUM-BLOCK          ← #5 (BTC bearish structure blocks LONG)
 50 SHORT-REGIME-GATE        ← minor killer
```

**Root cause:** ~38% of signals structurally unpassable + 20-gate stack tightened 3x Oct 16-18 + cross-layer gate/RSI inconsistencies wasting ~70 executions/day.

## What T Wants

T wants the system to take advantage of the bullish breakout. Right now, the gates are too tight and the system is sitting on its hands while BTC moves.

## CEO Decision Needed

### The core tension:
- **T wants more trades** — bullish breakout, signals flowing, system idle
- **Guardrail is at 50% size** — WR 34% < 35% threshold
- **Gates are eating 99% of signals** — some by design, some by bug

### Options:

**Option A: Loosen the #1 gate (CONFLUENCE-GATE-BLOCK)**
- 123 ichimoku signals/24h can never pass alone
- Add 'ichimoku' to STANDALONE_BYPASS_SIGNALS (if backtest supports)
- Or stop the emitter producing single-source ichimoku
- Risk: reduces signal quality (confluence = confirmation)

**Option B: Loosen the #2 gate (SHORT-RSI-HARD-FLOOR)**
- Reverted 35→45 on Oct 18 (commit f635705c)
- Now #2 killer at 848/day
- Revert back to 35? Or find middle ground at 40?
- Risk: re-introduces the bleed the revert was designed to stop

**Option C: Fix the cross-layer bugs first**
- Compactor/decider vol-gate mismatch wastes ~70 executions/day
- Three RSI sources flip outcomes on same token within minutes
- Fix these before loosening any gates
- Risk: takes time, doesn't address T's immediate frustration

**Option D: Emergency override — loosen all gates temporarily**
- T directive: "BTC just broke out bullish"
- Temporarily disable: CONFLUENCE-GATE for standalone bypass, SHORT-RSI-FLOOR back to 35, SHORT_MIDBAND off
- Re-evaluate in 24h
- Risk: could re-introduce bleed, but T wants action NOW

### My recommendation:

**Option D (emergency override) + Option C (fix bugs in parallel)**

T is right — we're not going to get anywhere sitting on our hands during a bullish breakout. The gates were tightened 3x in 72 hours without joint evaluation. Loosen them temporarily, let the system trade, collect data, then re-tighten based on evidence.

But also fix the cross-layer bugs (vol-gate mismatch, RSI divergence) so we're not wasting 70 executions/day on signals that can never execute.

## Protected Flags

13/13 INTACT. No config changed in this brief.
