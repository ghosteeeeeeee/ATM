# CEO Brief: Vacation Mode 7-Day Review — Shadow Data Collected but Not Used

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-23 18:30 UTC
**Priority:** HIGH — T is frustrated that shadow data isn't driving improvements

## TLDR

T's complaint: "We're generating 100x more stats from shadow-mode, but winrate and profitability barely changed."

**The data confirms this:**
- 7d WR: 33.8% → 35.2% (+1.4pp) — marginal improvement
- 7d PnL: -$4.13 → -$2.77 (+$1.36) — still losing money
- Shadow data: 18,751 expiry events, 29,559 gate events, 35MB shadow_trades — **collected but not acted on**
- Brain_auditor ran 102 times, most entries say "0 config changes (vacation file true)"

**The paradox:** Vacation mode was supposed to protect us while we collected data. But the "no_enforcement_flips, no_constants_change" rules are now **preventing us from acting on the data we collected**.

## Current State

| Metric | Oct 16 (start) | Oct 23 (now) | Change |
|--------|----------------|--------------|--------|
| 7d WR | 33.8% | 35.2% | +1.4pp |
| 7d PnL | -$4.13 | -$2.77 | +$1.36 |
| 24h WR | 23.5% | 42.1% | +18.6pp |
| 24h PnL | -$0.96 | -$0.36 | +$0.60 |
| Size reduce | 0.3x | 0.5x | lifted |
| Open positions | 0 | 1 | trading |
| Shadow events | 0 | 48,310 | collected |

## The Shadow Data Problem

### What Was Collected

| Shadow DB | Events | Purpose |
|-----------|--------|---------|
| `expiry_shadow.db` | 18,751 | Forward returns for EXPIRED/SKIPPED signals |
| `gate_shadow.db` | 29,559 | Per-gate shadow WR |
| `shadow_trades.db` | 35MB | Exit engine simulation (spec v1.3 built) |
| `t5_shadow.db` | 7.5MB | WOULD_TRADE/WOULD_SKIP vs live WR |
| `temporal_confluence_shadow.db` | 24KB | Temporal confluence counterfactual |

### What Was Done With It

**Almost nothing.** The brain_auditor has run 102 times since vacation started. Most entries say:

> "0 config changes (vacation file true 14th run)"
> "0 constants changes (vacation file true 9th run)"
> "0 config changes (vacation 14th run)"

The auditor is analyzing data but **not making changes** because vacation mode says "shadow_first, no_enforcement_flips, no_constants_change".

### Actionable Insights Found but Not Shipped

The auditor HAS found actionable insights, but held back:

1. **RSI<45 SHORT bear-structure exemption** — shipped as CEO unclog flip (Oct 22)
2. **volume-buildup- in HIGH/EXTREME** — shipped as CEO unclog flip (Oct 22)
3. **Waiver expiry gate** — shipped (Oct 23)
4. **CONF_FILTER toothless on STANDALONE_BYPASS** — shadow shipped, not enforced
5. **BTC-regime habitat map** — RANGING-class only profitable regime (p≤0.0005), but "KEEP OFF (comment only)"
6. **Within-slot conf throttle** — 30d fk 6.7% +1.98, but "MONITOR" not shipped

**The pattern:** Auditor finds insight → says "vacation mode, no changes" → insight sits unused.

## The Paradox

T's directive was: "collect data → use data to improve → system gets better."

What actually happened: "collect data → auditor analyzes → auditor says 'vacation mode, no changes' → data unused → system stagnant."

**The guardrail that was supposed to protect us is now preventing improvement.**

## CEO Decision Needed

### Question 1: Should we lift vacation mode restrictions?

**Option A: Lift "no_constants_change" rule**
- Allow auditor to make config changes based on shadow data
- Keep guardrails (size reduce, pause thresholds) active
- Risk: auditor might make bad changes without CEO review

**Option B: Keep restrictions, but add CEO review queue**
- Auditor proposes changes, CEO approves/rejects
- Slower but safer
- Risk: CEO bottleneck, changes delayed

**Option C: Keep restrictions as-is**
- Continue collecting data, wait for vacation to end
- Risk: another week of stagnation

### Question 2: Should we act on the shadow data now?

The shadow data has answers to:
- "Which gates are blocking winners?" (gate_shadow: 29,559 events)
- "Which signals work in which regimes?" (expiry_shadow: 18,751 events)
- "Which exit engines work best?" (shadow_trades: 35MB)

**Should we run the analysis and ship the top 3 improvements?**

### Question 3: Should we ship shadow-mode spec v1.3?

The spec is ready (v1.3, all 22 findings fixed). It would:
- Simulate exit engines on every signal fire
- Collect A/B data for exit engine optimization
- Answer "would this blocked trade have won?"

**Should we build it now, or wait until vacation ends?**

## My Recommendation

**Lift the "no_constants_change" restriction, but keep guardrails active.**

Rationale:
1. We've collected 48,310 shadow events — enough to act on
2. The auditor has found multiple actionable insights
3. The guardrails (size reduce, pause thresholds) are still protecting us
4. Another week of stagnation won't help

**Ship the top 3 improvements from shadow data:**
1. BTC-regime habitat map (RANGING-class only profitable)
2. Within-slot conf throttle (30d fk 6.7% +1.98)
3. CONF_FILTER enforcement on STANDALONE_BYPASS path

**Build shadow-mode spec v1.3** to collect exit engine A/B data.

## Protected Flags

13/13 INTACT. No config changed in this brief.
