# Hebbian Enhancement Spec — Reduce LLM Reliance

## Context

The Hebbian system now has richer data (combo synapses, exit tiers, leverage tiers, hour tiers) from 3115 backfilled trades. Current decision flow:

```
signal → context_gate → rule-based checks → Hebbian boost/penalty → LLM (always called if ambiguous)
```

LLM is called on every ambiguous trade (~30-40% of trades). This is slow, expensive, and the LLM sometimes makes bad calls (FLIP was disabled because it inverted 31% of trades to wrong direction).

## Proposal: Hebbian as Autonomous Gate

Make Hebbian a standalone gate that can approve/reject trades WITHOUT LLM involvement. LLM becomes a fallback for truly uncertain cases only.

### Current Flow
```
signal → rules → Hebbian (boost/penalty only) → LLM (always if ambiguous) → decision
```

### Proposed Flow
```
signal → rules → Hebbian (autonomous gate) → decision
                  ↓ if Hebbian confident (high data, clear pattern)
                  ↓ if Hebbian uncertain (low data, conflicting signals)
                    → LLM (rare fallback)
```

## 5 Enhancements to Enable This

### 1. Exit-Quality Score (before trade entry)
Look up `(signal, exit_profit)` vs `(signal, exit_sl)` synapse weights.

- High `exit_profit` weight → signal historically exits profitably → boost
- High `exit_sl` weight → signal historically hits SL → penalize
- **Can reject trades autonomously** if exit_sl dominance is strong enough

### 2. Combo-Aware WR
Look up `(token, combo_part1)` and `(token, combo_part2)` individually.

- If both parts have high WR → combo likely good (even if combo itself is untested)
- If one part has low WR → combo risky
- **Improves WR estimates** for multi-signal setups

### 3. Leverage-Aware Approval
Look up `(token, lev_mid)` vs `(token, lev_low)` synapse weights.

- If `lev_low` >> `lev_mid` → suggest lower leverage
- **Can auto-adjust leverage** without LLM

### 4. Hour-Aware Entry Timing
Look up `(signal, hour_us_open)` etc.

- If signal has high WR during specific hours → only fire then
- **Can time-gate signals** without LLM

### 5. Confidence Thresholds
Define when Hebbian is "confident enough" to decide alone:

| Condition | Hebbian Decision |
|---|---|
| WR est >= 60% AND n >= 5 AND exit_profit dominant | AUTO-APPROVE (boost confidence) |
| WR est <= 30% AND n >= 5 AND exit_sl dominant | AUTO-REJECT (penalize or block) |
| WR est 30-60% OR n < 5 OR conflicting exit data | ESCALATE TO LLM |
| No Hebbian data for this token/signal | ESCALATE TO LLM |

## Implementation Plan

### Phase 1: Enrich hebbian_trade_boost() (low effort, high impact)
- Add exit_quality lookup: `(signal, exit_profit)` weight
- Add combo_part lookups: `(token, part1)`, `(token, part2)`
- Pass richer data to context_gate

### Phase 2: Hebbian Autonomous Gate (medium effort)
- New function: `hebbian_autonomous_gate(token, signal, direction)`
- Returns: `('AUTO_GO', confidence_boost)`, `('AUTO_NAY', reason)`, or `('ESCALATE', None)`
- Called BEFORE LLM in context_gate
- If Hebbian is confident → skip LLM entirely

### Phase 3: Reduce LLM Calls (depends on Phase 2)
- Track % of trades that Hebbian handles autonomously
- Target: 60-70% of trades decided by Hebbian alone
- LLM only for: new tokens (no history), conflicting signals, extreme market conditions

## Expected Impact

| Metric | Current | With Hebbian Gate |
|---|---|---|
| LLM calls per day | ~30-40 | ~10-15 |
| Avg decision latency | 5-15s (LLM) | <1s (Hebbian) |
| Decision quality | LLM sometimes wrong | Hebbian data-driven |
| Cost | LLM tokens per trade | Zero for Hebbian decisions |

## Files to Change

- `hebbian_engine.py` — new `hebbian_autonomous_gate()` function
- `decider_run.py` — integrate Hebbian gate before LLM in `context_gate()`
- `hermes_constants.py` — threshold constants for autonomous decisions
