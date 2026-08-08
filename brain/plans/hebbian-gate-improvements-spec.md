# Hebbian Gate Improvements — Spec

## Context

The Hebbian autonomous gate is live with Phase 1+2. Current state:
- Token-specific data n>=5 for auto-approve/reject (very strict — only 4 auto-decisions in 7d test)
- Exit-profit/SL ratio for confidence adjustment
- Combo-part WR for multi-signal enrichment
- 85% WR achievable with n>=3 (20 trades) vs 75% with n>=5 (4 trades)

Goal: Increase auto-decision rate while maintaining >70% WR on auto-decisions.

---

## Improvement 1: Tiered Min-N by Confidence

**Problem:** n>=5 is too strict — only 4 auto-decisions. n>=3 gives 85% WR on 20 trades but is blanket-applied.

**Solution:** Two tiers based on exit-quality confidence:

| Tier | Min N | Exit Quality Required | Expected WR |
|---|---|---|---|
| High-confidence | 3 | exit_profit ratio > 10.0 | 85%+ |
| Standard | 5 | exit_profit ratio > 2.0 | 75%+ |

**Implementation:**
```python
# In context_gate, autonomous gate section:
is_high_confidence = (exit_quality and exit_quality['ratio'] > 10.0 and exit_quality['profit_n'] >= 3)
min_n = 3 if is_high_confidence else HEBBIAN_AUTO_MIN_N  # 5

if is_token_specific and n >= min_n:
    # auto-approve/reject logic
```

**Constants:**
```python
HEBBIAN_AUTO_MIN_N_STANDARD = 5    # normal threshold
HEBBIAN_AUTO_MIN_N_HIGH_CONF = 3   # high-confidence threshold (exit_profit ratio > 10)
HEBBIAN_HIGH_CONF_EXIT_RATIO = 10.0
```

**Risk:** Low — high-confidence tier only fires when exit_profit data is overwhelming.

---

## Improvement 2: Token Overall WR Boost

**Problem:** No data on token-level performance. A token with 88% overall WR (LTC) should get a confidence boost even without token-specific signal data.

**Solution:** Look up token's aggregate WR from Hebbian synapses. Apply as secondary boost/penalty.

**Implementation:**
- New method: `HebbianEngine.token_overall_wr(token)` — looks up `(token, exit_profit)` weight vs `(token, exit_sl)` weight to estimate token-level WR
- Or simpler: look up synapse weight for `(token, 'exit_profit')` — high weight = token historically exits profitably

```python
# In hebbian_trade_boost, after main lookup:
token_eq = engine.exit_quality_score(token)  # uses token↔exit_profit synapse
token_wr_boost = 0
if token_eq['profit_n'] >= 5:
    if token_eq['ratio'] > 3.0:
        token_wr_boost = 3  # token historically profitable
    elif token_eq['ratio'] < 0.5:
        token_wr_boost = -3  # token historically loses
```

**Constants:**
```python
HEBBIAN_TOKEN_WR_BOOST = 3           # ±3 confidence based on token history
HEBBIAN_TOKEN_WR_MIN_N = 5           # minimum exit events for token-level estimate
HEBBIAN_TOKEN_WR_RATIO_HIGH = 3.0    # profit/SL ratio threshold for boost
HEBBIAN_TOKEN_WR_RATIO_LOW = 0.5     # profit/SL ratio threshold for penalty
```

**Risk:** Low — secondary signal, applied as confidence adjustment only.

---

## Improvement 3: Direction+Signal Aggregate Fallback

**Problem:** When no token-specific data exists, Hebbian returns nothing. But aggregate data exists (e.g., `LONG hzscore+,return_exhaustion_long` at 81% WR, n=15).

**Solution:** Use direction+signal aggregate as soft fallback for confidence adjustment (NOT for auto-approve/reject).

**Implementation:**
```python
# In hebbian_trade_boost, fallback chain:
result = engine.wr_estimate(token, signal)  # token-specific first
is_token_specific = True
if not result:
    direction = 'LONG' if '+' in signal else 'SHORT'
    result = engine.wr_estimate(direction, signal)  # aggregate fallback
    is_token_specific = False
```

Already implemented! But the aggregate data is only used for soft boost/penalty (n>=3 threshold), not auto-decide. This is correct — aggregate data shouldn't auto-approve.

**Change:** Lower the soft-boost threshold for aggregate data from n>=3 to n>=10 (more data = more trust).

```python
# Existing soft boost/penalty — adjust thresholds:
if not is_token_specific and n >= 10 and wr_est >= HEBBIAN_BOOST_WR:
    # aggregate data, higher threshold
    return ('WARN', ..., -HEBBIAN_BOOST_AMOUNT)
```

**Constants:** No new constants — reuse existing `HEBBIAN_BOOST_WR`, `HEBBIAN_BOOST_MIN_N`.

**Risk:** Very low — confidence adjustment only, no auto-decisions.

---

## Improvement 4: Exit-SL Auto-Reject Threshold

**Problem:** Auto-reject requires WR <= 30% AND exit_sl dominant. But some signals have high exit_sl ratio even with moderate WR (e.g., 45% WR but 90% of exits are SL).

**Solution:** Pure exit_sl ratio threshold — if exit_sl dominates heavily, auto-reject regardless of WR.

**Implementation:**
```python
# In context_gate, autonomous gate section:
if is_token_specific and exit_quality:
    eq = exit_quality
    if eq['sl_n'] >= 5 and eq['ratio'] < 0.2:  # SL exits 5x more than profit
        log(f'  [HEBBIAN-GATE] AUTO-REJECT: exit_sl dominant (ratio={eq["ratio"]:.2f})')
        return ('SKIP', f'hebbian auto-reject: SL dominant (ratio={eq["ratio"]:.2f})', 0)
```

**Constants:**
```python
HEBBIAN_EXIT_SL_AUTO_REJECT_RATIO = 0.2   # profit/SL ratio below this → auto-reject
HEBBIAN_EXIT_SL_AUTO_REJECT_MIN_N = 5     # minimum SL exits for this rule
```

**Risk:** Medium — aggressive filter. Only fires when SL data is overwhelming.

---

## Improvement 5: Circuit Breaker Tracking

**Problem:** No feedback loop — if Hebbian auto-decisions start failing, there's no automatic recovery.

**Solution:** Track auto-decision accuracy. If it drops below threshold, disable gate temporarily.

**Implementation:**
- New file: `/root/.hermes/data/hebbian_gate_stats.json`
- Structure: `{"auto_decisions": [{"ts": ..., "token": ..., "signal": ..., "decision": ..., "actual_win": bool}], "disabled_until": None}`
- On each auto-decision: append outcome
- On gate check: if last 50 auto-decisions have WR < 45%, set `disabled_until` = now + 1 hour
- When `disabled_until` is set and not expired → skip autonomous gate, escalate all to LLM

```python
# In context_gate, before autonomous gate:
gate_stats = _load_gate_stats()
if gate_stats.get('disabled_until'):
    from datetime import datetime, timezone
    if datetime.now(timezone.utc).isoformat() < gate_stats['disabled_until']:
        log(f'  [HEBBIAN-GATE] DISABLED (circuit breaker active)')
        # skip autonomous gate, fall through to LLM
    else:
        gate_stats['disabled_until'] = None
        _save_gate_stats(gate_stats)

# After auto-decision:
outcome = {'ts': now_iso, 'token': token, 'signal': source, 'decision': decision, 'actual_win': None}
# ... later when trade closes:
# Update outcome with actual_win, check circuit breaker
```

**Constants:**
```python
HEBBIAN_CIRCUIT_BREAKER_WR = 0.45        # minimum WR over last 50 auto-decisions
HEBBIAN_CIRCUIT_BREAKER_N = 50           # window size
HEBBIAN_CIRCUIT_BREAKER_COOLDOWN_SEC = 3600  # 1 hour cooldown when tripped
```

**Risk:** Very low — safety mechanism only.

---

## Implementation Order

| # | Improvement | Impact | Effort | Risk |
|---|---|---|---|---|
| 1 | Tiered min-n | HIGH — 5x more auto-decisions | Trivial | Low |
| 2 | Token overall WR | MEDIUM — better confidence | Small | Low |
| 5 | Circuit breaker | MEDIUM — safety net | Small | Very low |
| 4 | Exit-sl auto-reject | MEDIUM — catch dangerous signals | Small | Medium |
| 3 | Direction+signal fallback | LOW — already mostly done | Trivial | Very low |

**Recommended:** Implement 1 → 2 → 5 → 4 in order. Skip 3 (already implemented).

---

## Expected Impact

| Metric | Current | After All Improvements |
|---|---|---|
| Auto-decisions per 333 trades | 4 (1.2%) | ~25-30 (7-9%) |
| Auto-decision WR | 75% | 80-85% |
| LLM calls reduced | 0% | 7-9% |
| Circuit breaker trips | none | 0 (safety only) |
