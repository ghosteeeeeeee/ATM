# BRIEF: T — "BTC is pumping, get the long WR back up and book serious profit!" (2026-11-16)

## T's words (verbatim intent)
"BTC is pumping, lots of signals flowing in, time to get that long winrate back up, and book
some serious profit. We can do this — we used to be able to ride trends really well, let's do it!"
→ Optimistic directional push: a bounce/pump is on, signals ARE flowing, and he wants the
long side to actually PAY this time (long WR is the known weakness). Convert his read into
the fastest legitimate path to booked long profit.

## Parent's fresh data (PG + local candles, 2026-11-16 14:40Z — trust, spot-check)
- **Tape:** BTC 24h 64,488 → 64,819 (+0.51%) — a bounce off the post-mega-crash lows
  (11-13 was 68,883 → then down to ~64.5k). 12h −0.88%, high 65,209 → so the "pump" is an
  intraday/bounce read, choppy in the last half-day. T's chart sees the pump; the 12h
  aggregate still reads red — that tension (bounce vs downtrend) is question 1.
- **Flow:** signals alive (376 EXPIRED/6h — **194 LONG**, 182 SHORT; 20 LONG PENDING;
  4 APPROVED, 1 EXECUTED/6h) — the compaction/hotset race still eats most births,
  longs especially.
- **Fills:** last8h closed = 1 LONG +$0.12; 1 LONG open; last6h opens = 2 LONG + 1 SHORT.
  Long WR remains the goal metric failing (non-jup fleet WR 51-52% vs ≥55% target).
- **State of the stack (all adjudicated — registry 119 entries, ZERO past-deadline open):**
  stop-tighten-enforce-eval **KEEP ENFORCE (all3 bars MET 11-14)** · slippage-column
  **SHIPPED 11-16** (the CF-trust blocker — now fixed) · winner-cell-150 KILL/moot ·
  floor-admit route CLOSED (floor stays) · pc- fade DEMOTED11-13 (CONTRARIAN_LIVE=False,
  bar breached: WR 64.6→52.9, live cohort net0) · amplifier REVERT EXECUTED #258 ·
  brake+visibility live (fee-net released) · disk84% (18G free, was90%).

## Questions to rule
1. **Is THIS pump a trend or a bounce?** Run the trend stack (structure engine, ADX/ATR
   lifecycle incl. rule1 ADX→0 = new-trend-birth, chop-flip counter since11-15, continuum)
   and give the direction call T is asking to ride — plus where the trend INVALIDATES.
   Per trust protocol: TREND regime = score outranks reads; CHOP = live reads outrank score.
2. **What is eating the 194 long expirations per 6h** — decomposition of long deaths in the
   bounce window (compaction_stale vs gates: neutral-chop, long-ceiling, confluence, RR,
   execution/hotset). Which single layer, if relieved under DATA, would put the most QUALITY
   longs on the tape? (Yesterday's verdict already ruled compaction no-relax — confirm it
   holds for bounce tape or name the distinguishing test.)
3. **The long-WR fix, concretely:** the payoff work (stop-tighten KEEP-enforced, slippage
   column shipped, win-capture bar due) targets loss size; what targets LONG WIN RATE
   (entry quality: the 45-60 band problem, ceiling interactions, hotset timing)? Ranked
   actions with bars — live-now vs shadow, each with revert.
4. **"Book serious profit":** at current size ($11-19 notional, ~$4 effective) what does a
   SUCCESSFUL bounce-ride actually book (expected $ at realistic WR and holds)? Be honest
   about the size ceiling again — and state what notional would make "serious" real, since
   T has never answered the notional question (mega-crash verdict item5, still open).
5. Deliver: direction call + invalidation level, ranked execute-now list (exact flags/sites),
   what stays shadow with bars/dates, and the log proofs T should see within 24h if the
   long book is actually working.
Constraints: no blanket kills, protected flags, net-of-fees, token-day dedup, flag polarity,
speed mandate, fold framework intact. Read-only — recommendations only.

## APPENDIX — your previous run TIMED OUT (rc=124:82 queries, ZERO verdict text). Pre-seeded
## below. HARD RULE: ≤10 confirmatory queries, then WRITE THE VERDICT.

### Trend stack (parent ran auto_analysis + adx_atr_analysis, 14:42Z — trust)
- price 64,303 · **regime CHOP (7 flips/24h)** → per trust protocol: live reads outrank score,
  halve trend-input points.
- Structure: 1m UPTREND [HH HL] SH=64,304 SL=64,156 · 5m DOWNTREND [LH LL] ·
  **15m COMPRESSION [LH HL] SH=65,173 SL=64,329 (the coil)** · 1h UPTREND [HH HL] SH=65,696
  SL=64,014 · 4h DOWNTREND.
- ADX/ATR lifecycle: 1m ADX47.5 TREND FADING · 5m ADX26.1 PEAKED 6b ago (rule2 pending) ·
  **15m EXHAUSTION** (rule2: peak21b ago + new major low after peak → move usually over) ·
  **1h DUAL-PEAK CLIMAX (ATR953 & ADX57.8 peaked1 bar apart, confirmed by new major low)** ·
  **4h DUAL-PEAK CLIMAX (ATR1529 & ADX64.1, awaiting post-peak extreme)**.
  COMBINED: trendless-none, exhaustion [15m,1h], dual-peak [1h,4h].
→ The lifecycle read says the bounce is EXHAUSTED/CLIMAXED on15m-4h with a15m coil —
T's "pump" may be the bounce INTO the coil before resolution. Rule honestly: does the1m/1h
UPTREND + coil break UP have legs (rule1 ADX→0 zones), or does exhaustion+4h downtrend
dominate? Give the direction + invalidation either way.

### Long-death decomposition (last24h, LONG, EXPIRED/SKIPPED — trust)
compaction_stale **184** · pump-chain-long-high **105** · long-neutral-chop54 ·
single-type confluence52 · pump-chain-rsi-max-long46 · long-high-70 44 ·
APPROVED-fell-out-of-hotset42 · long-midband34 · long-rsi-ceiling33 · combo-stale32 ·
rr-engine25 · vol-gate-override18. Only **3 APPROVED longs/24h**.
→ compaction+hotset mechanics = 258/665 (39%); real gates = the rest (pc+-family alone =205).
NOTE: `pump-chain-long-high` (105) + `long-high-70` (44) are ceiling/chase protections —
check whether they're correctly rejecting overbought longs or starving the bounce's best entries
(fwd-counterfactual, token-day dedup — the standing rule).

### State (registry119, ZERO overdue; LOOKAHEAD W47 = **41 items due ≤7d**)
11-14 batch all adjudicated: stop-tighten KEEP-ENFORCE (3/3 bars) · slippage-column SHIPPED
11-16 · winner-cell-150 killed-moot · floor-admit route CLOSED · amplifier REVERTED #258 ·
pc- fade DEMOTED (CONTRARIAN_LIVE=False) · disk84% · brake released (fee-net green).
Open for T from prior verdicts: **notional question (never answered)** + fade veto window
(auditor flagged CEO veto on the demote).
