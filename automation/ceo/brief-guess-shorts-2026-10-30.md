# CONSULT: "btc dropping like a rock, guess how many shorts were taken?"

**Budget ~30 min; print by ~minute 22. Grounding is verified below. The machinery you
labeled last night had its first real test tonight and produced [fills: zero]. Deliverable:
(1) the answer to T's question with the autopsy of WHY each layer didn't fire, (2) rulings
on the three defects this exposes, (3) whether the shadow-to-enforce pacing survives
contact with nightly dumps. No comfort.**

## T's message (verbatim, 2026-10-30 ~00:58 UTC)

> "btc dropping like a rock, guess how many shorts were taken?"

## Verified grounding (re-verify; correct me plainly)

**Market:** BTC −2.37%/3h (79,033 → 77,160, low **76,844**); rolling-60m right now −0.95%.

**The answer: ZERO shorts since the dump began.** Last short fill = CRV **+6.87%** at
10-29 20:12. Since: only a COMP LONG (21:16, −0.19). 0 open positions.
24h shorts: NXPC −3.65, YGG +1.12, **BTC continuum-osc −7.32**, CRV +6.87.

**Storm timeline (rolling-60m, the shipped detector) — it ARMED TWICE:**
- 20:58–21:08 (yesterday's dump): −2.51% min
- **00:18–00:38 (tonight's dump): −1.99/−2.17/−1.55% — armed for ~20 min**

**What each layer did:**
1. `[STORM-CONFL-WAIVER-SHADOW]` WOULD-PASS lines: **0, ever** — even inside the armed window.
2. `[STORM-READINESS]` packets from auto_1hr: **0, ever** (its 00:41 run landed right at
   the −1.55→−1.47 boundary — need to know whether the section ran and skipped, or never ran).
3. Blocking census since 23:00: **26 plain `compaction_stale_10min`** · 16 short-rsi-hard-floor
   · **14 confluence single-type (SHORT_BIAS — the exact lane the waiver shadows)** ·
   6 oversold-knife · **6 rep-low-reputation** (our new truth) · 2 rr-engine-hard-block ·
   1 pump-chain-short-high.
4. Observability gap in what we shipped: the helper only logs "not stormy enough" (band),
   ALL-3 PASS, and ERROR — **a candidate that fails (ii) RSI or (iii) sibling DURING an
   armed window logs nothing.** So "0 would-pass" is currently unfalsifiable from logs.

## Questions — answer each, then rule

1. **The autopsy:** during the armed window 00:18–00:38, which single-type SHORT
   candidates hit the confluence gate, and which condition (ii/iii) killed each? (Query
   tombstones in-window + candle RSI at their timestamps; add the missing mid-condition
   debug path as part of your fix list.)
2. **Packet defect:** why did auto_1hr's first real storm test (00:41, rolling ≈ −1.5)
   emit no packet — borderline threshold, section not executed by the agent, or wrong
   computation? The ≥3-packet enforce bar cannot START if packets never emit. Fix rule now.
3. **The pacing question (the real one for T):** dumps are coming nightly. The waiver is
   shadow; shadow takes no trades. Under the current bar (≥3 consecutive storm packets →
   enforce, deadline 11-12) how many nights is that from tonight? Is there a faster
   honest path — e.g., count tonight + yesterday as packets retroactively (both windows
   qualify; counterfactual replay per window available), or move enforce up with the
   already-strong evidence (+$8.31 + 65.6% combined + knife-authority RSI)? Or is
   shadow-through-11-12 the price of not repeating BUG-068-class mistakes? Rule it.
4. **Counterfactual tonight:** replay the 00:18–00:38 blocked cohort (RSI≥35 honesty
   cut, walk + touch) — what did ZERO shorts cost this drop, same method as yesterday
   (+$8.31 basis)?
5. **Defects to fix (labels):** (a) missing mid-condition debug logging; (b) packet
   emission path; (c) anything the autopsy adds. Include the fix's verification bar.
6. **What NOT to touch** (knife<35 global — the 16 hard-floor/6 knife blocks may be
   correct in a crash; HIGH block; fade RC1 stack; protected flags; trial pair).

## Guardrails
READ-ONLY round; T's "proceed" pattern applies post-verdict. Plain answer to T first:
the count, then why, then what changes.
