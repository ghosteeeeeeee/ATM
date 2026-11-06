# BRIEF: T — "We need to be TRADING!!" — autonomous system must engage continuously (2026-11-06)

## T's words (both messages, verbatim intent)
1. "No new trades in a while, signals coming in, shadow data being generated. Sure market is flat etc. — some coins have to have pumped/dumped while we're waiting for the market to decide."
2. "Present your findings to the CEO with this addendum: **We're making an AUTONOMOUS trading system — taking long breaks is not the point of it. It should be finding moves CONTINUOUSLY. We have 100 coins, 100 signals, thousands of closed trades and shadow data. We need to be trading!!**"

→ The mandate: continuous engagement across the universe is the DESIGN GOAL, not optional. Idle hours are a defect. He wants a plan that makes the system trade continuously — without re-opening the protections that data justified. This is a design ruling, not a status read.

## Parent's fill-starvation diagnosis (verified 2026-11-06 03:43Z — trust, spot-check)
- **Last fill 11-05 23:00; 0 open positions; 2 fills/12h.** Brake (DAILY_FILL_CAP) released 11-05 07:13 — NOT binding now. Cap C jup 1/6h binding but minor.
- **Signals arrive: 523/12h (469 EXPIRED, 43 SKIPPED, 9 PENDING, 2 APPROVED). 7d: 2,451 compaction-stale expiries alone.**
- **Coins moved and we saw them:** MERL +14.7% (3 signals), FOGO −8.8% (20 signals), ARB +7.5% (14), WLFI +7.2%, **ETHFI +6.9% (ZERO signals)**.
- **Death buckets (12h):** compaction/hotset race = 205/469 (44%: stale-10min 106, fell-out-of-hotset 52, merge-window-lapsed 47) · real gates ~260 (FOGO dump-shorts → single-type confluence + maxxed; pump-longs → pump-chain-rsi-max/chase; crash-gate, RR-engine, floors, neutral-chop) · detector blind spots (ETHFI 0, MERL sparse).
- **Stability check on the compaction bucket (the pattern-rule applied BEFORE reporting):** 12h counterfactual looked +$10.80 net (77 deduped, 61% win) → **24h −$12.07 (n=200) · 7d −$31.55 (n=2,010, avg −0.03%/signal)**. One-window bounce luck; admitting compaction-stale flow would LOSE money (stale = move already happened = chase). Do NOT relax compaction on the 12h number.
- **Pincer (11-05):** crash day → BANANA floor blocked 812 short attempts (RSI<45) while bear structure blocked longs — the system structurally sat out the exact tape. Plus LONG-bypass block + fill-cap + amplifier now shape flow.
- **Context:** fee economics (0.09% RT) = the reason the 15/day brake exists; 8 red days → first green 11-05 (+$0.17, n=6, throttle-assisted); fold-line 11-07 currently averts (cum −$0.37 vs −$1.50).

## Standing constraints (do not violate)
No blanket kills / no time-of-day blocks (route via regime+vol gates); protected flags; flag polarity rules; net-of-fees everywhere; token-day dedup for fwd means; proven-protective gates stay (floor-45, pc-high net-saving, RR-engine, chase protections); prior verdicts: admission funnel NOT working (longs 4.3x), compaction bucket NOT a leak (7d data), bear-single-source NOT-YET (n=8→~11-11), BANANA tension on record.

## What to rule — the continuous-engagement design
1. **Where did throughput go, layer by layer, and which layer should give?** Fill rate went ~40/day → 4/day. Decompose today's flow loss into: compaction top-10 ranking (is the hotset the true bottleneck — 10 slots vs 100 coins?), admission gates, exec/hotset filter, chase/floor protections, brake (released), Cap C (minor). Name the ONE layer whose change buys the most fills per day with the least EV cost.
2. **The continuous-trading target:** what fills/day SHOULD a 100-coin autonomous system produce in (a) flat tape, (b) trending tape, (c) violent tape — net-of-fees positive at current size? Give the target as a number and the flow architecture to reach it (e.g. hotset size 10→N? per-coin slots? signal-priority queue? re-entry cadence? detector coverage for blind spots like ETHFI?).
3. **Detector coverage gaps:** ETHFI +6.9% produced ZERO signals; MERL +14.7% only 3. Which detectors cover which move types, and what is missing (momentum? volume? new listing?) — the momentum-cache-regime-coverage audit is due TODAY (11-06): fold its answer in if it landed, or order it now.
4. **Admission relaxations that are DATA-READY vs not:** bear-single-source (n=8, ~11-11 — early pull?), single-type confluence eating dump-shorts, SHORT-REGIME score-kill (A1 shadow, 268 lines/6 tok-days), anything new. Name which can go live THIS WEEK under the speed mandate and with what revert, vs what must wait for its bar.
5. **The throttle conflict:** T's mandate (trade continuously) vs the fill-cap/fee-economics brake (15/day while red). Does the brake need re-scoping (e.g. exempt high-conviction setups? raise cap? time-box?) — or does "continuous" mean MORE fills only when EV-positive, with the answer being BETTER signal quality at the same cadence? Rule explicitly — T must be able to tell "we are trading continuously" from "we are idling by choice".
6. **Reconcile with the fold line (11-07):** does the continuous-engagement mandate change the fold criteria (e.g. add a fills/day floor as a co-equal metric), or does profitability remain the only judge?
7. Deliver: a FLOW RECOVERY PLAN with ranked, dated, gated actions (immediate-this-week vs bars), each with the exact file/flag/hotset parameter, the target fills/day by tape regime, and what T should see in the logs within 24h as proof of continuous engagement.

Constraints as always: no blanket kills; protections with negative data stay; shadow→enforce unless overwhelming; code review + bug_hunter gates; registry/calendar tracking. Read-only this run — recommendations only.
