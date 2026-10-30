# CONSULT: pump-lane counterpart — LONG starvation during pumps (T: "done with excuses")

**Budget ~25 min; print by ~minute 18. Under T's standing delegation ("If the ceo has
signed off on it, proceed") your label IS the go — we implement the moment you answer.**

## Context (no framing, numbers only)

T opened two manual longs himself after the pipeline failed to (BTC #16538, ENS #16539,
both precheck FAIL: RSI ~75 ceiling). The storm round solved the DUMP side
(confluence storm-waiver, packets 2/3). The PUMP side has no lane. Today's kill census
(3h window, tombstones + logs, verified):

| Gate | n | Claimed basis |
|---|---|---|
| PUMP-CHAIN-RSI-MAX | 108 | 23.5% WR at RSI≥70/14d |
| LONG-RSI-CEILING (75) | 102 | chase-extended |
| CTX-GATE similar-setup hard (n=6-8 WR 12-17%) | ~19 | <30% bar |
| SPIKE-FILTER LONG (bearish-candle) | 23 | direction mirror |
| PUMP-CHAIN-HIGH | 20 | HIGH 35.7% WR |
| plain stale (never gated/approved) | 61 | ??? — second autopsy below |
| fills | 2 pump-chain+ (CAKE open +0.59, FARTCOIN −0.86) + manual ×2 |

## Questions

1. **Verdict: is the RSI-ceiling pair (PUMP-CHAIN-RSI-MAX≥70 + LONG-RSI-CEILING>75)
   exactly right, or does it need the mirror of the storm ruling?** Counterfactual you
   can demand or we run: replay today's 210 ceiling-killed LONGs (±0.4% touch + walk,
   RSI≥35-honesty style cut with a HIGH-side cut instead — e.g. only entries with
   RSI 70-79, not 85+). If the replay is positive → scoped pilot candidate (e.g.,
   fresh-momentum LONGs 70-75 only, size-dampened, shadow-first, one bar). If
   negative → the ceiling stands and today's miss is the cost of the rule, said once.
2. **The 61 no-reason expiries:** they never hit any gate and never got approved —
   diagnose root (confluence never arrived? hotset 0/3 slots held by dead low-score
   candidates AERO72/IMX47? rate-limit? compaction race). Rule the fix.
3. **BUG-070 context:** brain was discarding all decider size multipliers (winner-cell
   1.25 dead in the money path) — fixed, gates running. Anything else in the
   claim-vs-behavior class you can see from your vantage — call it.
4. Deliver labels for immediate implementation under T's standing delegation.

## Guardrails
No blanket kills. Protected flags/knife/trial stand. Evidence first, labels second.
