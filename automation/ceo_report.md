## CEO Report — 2026-08-08

### Decision: PROCEED with modifications

The plan is sound. Target 7-9% auto-decisions at 80%+ WR is realistic — not too aggressive, not too conservative. Here's my read:

---

### 1. Target Assessment

**7-9% at 80%+ WR is right.** Here's why:
- Current 1.2% auto-decision rate is a safety problem, not a feature — almost every trade escalates to LLM, meaning the Hebbian gate is effectively decorative.
- n=3 with high-confidence filter (exit_profit ratio > 10) gives 85% WR on 20 trades — that's the proof point.
- Going beyond 9% auto-decisions too quickly would be reckless. 80%+ WR on auto-decisions is the floor, not the target.

**Recommendation:** Target 80-85% WR, not just 80%. The tiered approach naturally achieves this — high-confidence tier fires at 85%, standard at 75%. Weighted average lands at 80%+.

---

### 2. Risks Being Missed

**A. Exit-profit ratio > 10.0 may be survivorship-biased.** If a token had 10 exits with ratio > 10, those might all be from a trending period. The token could reverse. Improvement 2 (token WR boost) partially addresses this, but we should consider a **time decay** — recent exits weighted more than old ones. This is a v2 concern, not a blocker.

**B. Improvement 4 (exit-sl auto-reject at ratio < 0.2) has a hidden failure mode.** A token with 5 SL exits and 1 profit (ratio 0.2) gets auto-rejected — but if those 5 SLs were from a single bad regime, we're throwing away a token that's actually fine in current conditions. **Mitigation:** Add a regime check — only auto-reject if SL dominance persists across regime changes. Or keep the existing WR-based reject as primary, and make exit-sl a secondary veto only.

**C. Circuit breaker cooldown of 1 hour is too short.** If the gate trips, it's because data quality is bad. 1 hour later, the same bad data is still there. **Recommendation:** Start with 4-hour cooldown, or require N=10 new token-specific data points before re-enabling.

---

### 3. Priority Reorder

The plan recommends 1 → 2 → 5 → 4. I agree with a small tweak:

| Order | Improvement | Rationale |
|-------|------------|-----------|
| 1 | Tiered min-n | Highest impact, lowest risk. Ship first. |
| 2 | Token WR boost | Complements #1 — together they're the core improvement. |
| 4 | Exit-sl auto-reject | **Move before circuit breaker.** If auto-reject works, the circuit breaker may never need to fire. Better to prevent bad decisions than to detect them after. |
| 5 | Circuit breaker | Safety net, last. |
| 3 | Direction+signal fallback | Skip — already implemented. No work needed. |

---

### 4. Additional Improvements to Consider

**A. Auto-decision logging for audit.** Every auto-decision (approve/reject) should log to a JSON file with: token, signal, decision, WR estimate, n, exit_quality, timestamp. This lets us review gate accuracy weekly without DB queries. Improvement 5 partially covers this but only tracks outcomes — we need the decision context too.

**B. Confidence floor for auto-approve.** The current plan auto-approves when WR >= 60% AND n >= min_n. But 60% WR with low confidence adj could still be risky. **Add:** total_conf_adj must be >= 0 for auto-approve (already in the code at line 1165: `exit_boost >= 0`). Good — this is already handled. No change needed.

**C. Graduated auto-approve thresholds by confidence tier.** Instead of binary (approve/reject), consider:
- WR >= 80% + n >= 3 → auto-approve (high confidence)
- WR >= 65% + n >= 5 → auto-approve (standard)
- WR >= 50% + n >= 10 → auto-approve (low confidence, small position)

This gives more granularity. But it's v2 — the tiered min-n in Improvement 1 already captures most of this.

---

### 5. Final Verdict

**Proceed as-is with one modification:** increase circuit breaker cooldown from 1 hour to 4 hours, and move Improvement 4 before Improvement 5.

The plan is well-researched, the numbers check out (n=3 at 85% WR is from real data), and the risk profile is acceptable. The biggest risk is doing nothing — the Hebbian gate is currently dead weight at 1.2% auto-decisions.

**Ship order:** 1 → 2 → 4 → 5. Skip 3.

---

### Verification Plan

After implementation:
1. Run 48-hour observation period — track auto-decision count and WR
2. If auto-decisions > 5% and WR > 80% → expand to 10% target
3. If WR drops below 70% → circuit breaker should catch it; investigate root cause
4. Weekly review of auto-decision audit log
