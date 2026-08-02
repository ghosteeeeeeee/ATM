# Spec: Hard vs Soft Guardrail Reframing

**Date:** 2026-07-28
**Status:** SPEC — awaiting review
**Inspiration:** AIS Agents podcast — "hard guardrails (physically can't do X) vs soft guardrails (told not to but has access)"

---

## Problem

The context gate currently has two layers:
1. **Rule-based gate** (hard) — deterministic SKIP blocks the trade. Reliable.
2. **LLM gate** (soft pretending to be hard) — returns GO/SKIP. Can block trades.

The LLM gate is unreliable by nature (hallucination, timeout, wrong judgment). Giving it hard veto power over live money is dangerous. The podcast's insight: **soft guardrails can be overridden by human error or LLM error; hard guardrails physically prevent the action.**

Current LLM behavior:
- SKIP → blocks trade (acts as hard guardrail, but it's a soft method)
- GO → allows trade (no effect)
- Timeout → fail-open (allows trade)

---

## Solution

Reframe the LLM as **advisory only** — it can reduce confidence, never block outright.

### Guardrail Hierarchy

| Layer | Type | Action | Can Block? |
|-------|------|--------|:----------:|
| Blacklist, dead-hours, phase filter | **Hard** | SKIP → code blocks | YES |
| Rule-based context gate (speed, z, ranging) | **Hard** | SKIP → code blocks | YES |
| Coin history gate (<50% WR) | **Hard** | SKIP → code blocks | YES |
| LLM context gate | **Soft** | SKIP → confidence penalty | NO |
| Confidence threshold check | **Hard** | conf < MIN → code blocks | YES |
| Loss cooldown | **Hard** | SKIP → code blocks | YES |

### Change

`llm_context_gate()` currently returns `('SKIP', reason)` which blocks the trade.
New behavior: LLM SKIP → `('WARN', reason)` which reduces confidence by 15 points.
The existing confidence threshold check (hard guardrail at `MIN_EXEC_CONFIDENCE`) then blocks if confidence drops too low.

### Flow

```
Signal → Hard filters → Rule-based gate → LLM gate → Confidence check → Execute
         (block)        (block)           (penalize)  (block if too low)
```

### Why This Is Better

1. **LLM can't kill a strong trade** — a high-confidence trade survives even if LLM says SKIP (penalty just reduces it, might still be above threshold)
2. **LLM can rescue a marginal trade** — if LLM says GO, no penalty applied
3. **Hard guardrails still protect** — the threshold check is deterministic
4. **Simpler mental model** — humans (and T) know that rule-based = wall, LLM = advisor

### Implementation

In `decider_run.py`, `context_gate()` function:

```python
def context_gate(token, direction, source, sig, confidence):
    """Two-layer gate. Returns (adjusted_confidence, skip_reason_or_none)."""
    if not CONTEXT_GATE_ENABLED:
        return confidence, None

    verdict, ctx = rule_based_context_gate(token, direction, source, sig)

    if verdict == 'SKIP':
        return confidence, ctx  # hard block

    if verdict == 'GO':
        return confidence, None  # pass

    # AMBIGUOUS → LLM advisory (soft)
    llm_verdict, _ = llm_context_gate(token, direction, source, sig, ctx)
    if llm_verdict == 'SKIP':
        adjusted = confidence - CONTEXT_GATE_LLM_PENALTY
        log(f'  [CTX-GATE] LLM advisory SKIP → conf {confidence:.0f}% → {adjusted:.0f}%')
        return adjusted, None  # not blocked, just penalized

    return confidence, None
```

### New Constants (hermes_constants.py)

```python
CONTEXT_GATE_LLM_PENALTY = 15  # confidence points deducted when LLM says SKIP
```

### What Changes

| File | Change |
|------|--------|
| `decider_run.py` | `context_gate()` returns `(conf, reason)` instead of `(verdict, reason)`. Caller checks `if reason: skip` and uses `conf` for threshold. |
| `hermes_constants.py` | Add `CONTEXT_GATE_LLM_PENALTY = 15` |
| AGENTS.md | Update context gate section: "LLM = soft guardrail (advisory), rule-based = hard guardrail (blocking)" |

### Risk

- LOW — LLM was already fail-open. This makes it even safer by never letting LLM block directly.
- If LLM is wrong (says SKIP on a good trade), the trade still fires if confidence stays above threshold.
- If LLM is right (says SKIP on a bad trade), confidence penalty drops it below threshold → blocked by hard guardrail.

### Migration

The caller site in `decider_run.py` currently does:
```python
ctx_verdict, ctx_reason = context_gate(token, direction, source, sig)
if ctx_verdict == 'SKIP':
    ...skip...
```

New caller:
```python
adjusted_conf, ctx_reason = context_gate(token, direction, source, sig, confidence)
if ctx_reason:
    ...skip...
confidence = adjusted_conf  # use penalized confidence for threshold check
```