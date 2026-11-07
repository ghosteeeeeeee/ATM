# BRIEF: T — "dead in the water + skeptical none of the 100 coins moved" (2026-11-06, ceo-comm long timeout)

## T's words (verbatim intent)
"Looks like the 'guy who trades' is on vacation or something — we're dead in the water. The system
better be ready to spring when volatility returns. BUT: **I am very skeptical that none of the other
100 coins we track had pumps/dumps while we were just waiting.**"

→ Two deliverables: (1) the definitive MOVER-COVERAGE census — for every coin that actually moved,
where did it die (no signal / gated / unfilled / filled); (2) a VOL-RETURN READINESS checklist —
when volatility springs back, does anything auto-widen, or does the system stay clamped?

## Parent's fresh mover census (2026-11-06 21:56Z, trust — spot-check only)
**BTC 6h: −0.06% (flat). Universe24h: 183 coins tracked, 107 moved ≥3% net or ≥6% range.**
Outcome of all 107 movers (signals = runtime DB last24h; fills = PG opens last24h):
- **49 movers: ZERO signals** (detector never fired — includes ETHFI blacklist, but also
  STABLE −8.1%, 0G +7.0, MEGA +6.9, GRIFFAIN +6.8, ZEC +6.5, DASH +5.6, TIA +5.3, PNUT +5.2,
  HEMI +4.9, APEX −4.8, KAITO +4.7 …)
- **51 movers: signals born but ZERO fills** (dominant deaths: vol-gate-override-0.0, pump-chain-long-high,
  compaction_stale_10min, single-type confluence)
- **Only 7 of 107 had ≥1 fill** — total fills across ALL movers in 24h = **7**
- Top examples: W +9.4% (3 signals, 0 fills, vol-gate-0.0), ACE +7.5% (18 signals, 0 fills,
  pump-chain-long-high), ARB +5.9% (14 signals, 0 fills, compaction-stale), CRV +5.0% (11 sig, 1 fill)
→ T's skepticism is CONFIRMED: the system saw 100+ movers and engaged 7 times.

## Context (prior verdicts in force — do not re-derive)
- Continuous-trading verdict (consult 20261106T035547Z): mandate approved as design principle;
  "more fills" rejected as metric; targets flat 3-6 / trending 10-15 / violent 15-25 fills/day
  conditional on trailing WR≥60%; brake not binding; ONE layer to give = bear single-type SHORT
  (bar 11-10). Compaction-stale relax FORBIDDEN (7d −$31.55). ETHFI blacklisted both dirs (T decision pending).
- New shadows live: [BTC-CHOP-STANDALONE-SHADOW] + [SETUP-RECALL-SHADOW] (11-17 bars).
- Fold line 11-07: cum fee-net −$0.37 vs −$1.50 → currently averts.
- Coverage audits landed: momentum-cache PASS (65/65 fresh), candle-collector FIXED (110/110).
- Cap C jup 1/6h, Cap D 15/day (self-releasing), LONG-bypass SHORT_BIAS block, ceiling 75 — all live.
- Hotset holds 2 entries (jup-dominant under Cap C); scored[:10] never fills.

## Questions to answer
1. **The 49 zero-signal movers — decompose definitively:** for each, which applies:
   (a) blacklisted (both dirs / one dir), (b) not in detector universe (new listing, missing
   candles/pairs, token list lag), (c) detector params missed it (what move pattern would have
   fired — momentum? volume? z-score? each detector's coverage), (d) born-but-unrecorded.
   Give the count per bucket + the FIX per bucket (unblock list for T, universe-sync, param gap).
2. **The 51 gated movers — which gates are correct vs wrong:** per-gate tally on the gated-51 with
   the existing fwd-counterfactual where available (token-day dedup); name any gate that is
   repeatedly killing +3% movers with negative counterfactual (= wrong) vs protective (= right).
3. **Spring-readiness checklist:** when volatility returns, what happens automatically vs stays
   clamped? Specifically: Cap D (self-releases on green ✓), Cap C (jup-only — does hotset
   diversity return?), bear-single-source (bar 11-10 — is it ready for the next dump?), storm
   waiver (streak was reset — packets?), the pincer (floor vs structure — anything that widens
   in EXTREME/HIGH vol by design?), hotset 2-entry state (why so empty — is the ranking
   starving in flat tape?). Rank what must be pre-positioned BEFORE the next violent tape.
4. **Is there a vol-response design gap?** Does ANY config auto-widen admission when vol spikes
   (storm machinery is confluence-only; vol-gate HIGH allowlist exists for bb-squeeze) — or is the
   system structurally narrow in exactly the moments T wants it to spring? If gap: propose the
   minimal vol-triggered relaxation with bars (no blanket kills).
5. Deliver: mover-coverage fix list (ranked, dated, gated) + spring-readiness table
   (mechanism → ready/not → action → date). Read-only — recommendations only.
Constraints: no blanket kills; proven-protective gates stay; flag polarity; token-day dedup;
net-of-fees; shadow→enforce unless overwhelming; speed mandate in force.
