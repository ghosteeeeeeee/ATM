# BRIEF: BTC −7.78% mega-crash — 11 shorts made NOTHING (T: "where are the shorts?!") (2026-11-13)

## T's words (verbatim intent)
"We're twiddling our thumbs, BTC has been vrashing since 19:00 11th Nov. What the hell is our
system waiting for??? Where are the shorts — we couldn't have asked for a better shorting
opportunity (ignore manuals and pending trades). Please get your act together. Totally losing
faith in you and that you can figure this whole trading thing out. Could have made a killing
shorting this market, oh well..."
→ Maximum-frustration escalation: the biggest dump in the record window, and the system's
output was ~nothing. Needs full crash-window attribution + the "why didn't the shorts pay"
answer + what changes NOW.

## Parent's verified diagnosis (trust — spot-check)
**BTC since 11-11 19:00Z: 74,493 → 68,700 = −7.78%, low 68,700 (395 5m bars, still at lows).**
- **Fills since crash start (excl manual/pending): 12 — 11 SHORT (72.7% WR, net **−$0.17**)
  + 1 LONG (+$0.03).** So unlike the 11-08 storm (zero shorts), we DID short — and still
  made nothing. 0 open now.
- **580 SHORT signals EXPIRED since crash start. Death reasons:** compaction_stale 189 ·
  **short-rsi-hard-floor 153** (flip1 expired+re-shadowed, bar11-17) ·
  **short-regime-gate 71** (A1 exempt = SHADOW, `SHORT_REGIME_EXEMPT_ENFORCE=False`, bar11-17) ·
  pump-chain-short-high 60 (KEEP, net-saving) · oversold-knife 39 (protected) ·
  combo stale 34 · single-type confluence 17 · rr-engine 12.
- Wall of blocks in the window (log census): CONTINUUM-BLOCK 4,503 · SHORT-RSI-HARD-FLOOR 1,778 ·
  SHORT-REGIME-GATE 1,569 · SHORT-NEUTRAL 1,257 · LONG-NEUTRAL(+CHOP) 2,862 · VOL-FLOOR 970 ·
  EXEC-BLOCK 951 · OVERSOLD-SHORT 799.
- DailyFillCap: engaged during parts of the crash (15/15, fee-net −0.31); NOW released
  (fee-net **+0.15**, opens16 — sawtooth working; tower fill_cap verified).
- Storm waiver: NO-CONVERT (11-08 ruling) — logged WOULD-PASS on 11-12 (shadow only).
  linreg-fade storm shadow: only 7 lines (CRV/ACE 11-10) — extended to 12-01 as DATA-STARVED
  (audit #250). Storm waiver extended to 11-19 (bar NOT met at deadline).
- Registry state: only `winner-cell-size-125` past deadline (11-10, default REVERT MULT=1.0).
  FOUR DECISION-DUE items from the 11-12 packets are due 11-13 00:00 (pump-chain+-weight-kill,
  vb-high-clonehunt, bbsqueeze-chop-exempt, linreg-fade-fill-funnel) — defaults fire at the
  08:15 run unless dispositioned first.
- bear-single-source: WAIT disposition stands, deadline 11-17 (amended bar: original limbs +
  ex-best-day ≥ +$1.00).

## The three questions (all pre-registered context exists — extend, don't re-derive)
1. **The "11 shorts at 72.7% WR = −$0.17" anatomy.** WR was RIGHT; money wasn't made.
   Where did it go: payoff (avg win size vs fee $0.012), exit paths (atr_sl/HML on the
   shorts?), entry timing (shorting into already-fallen legs), sizing (11 small notionals)?
   Decompose every one of the 11 fills: entry, exit reason, gross, fee, net. This is the
   single most important table in the brief — a −7.78% crash where our correct-direction
   73% WR shorts net ≈ $0 is the核心 mystery.
2. **The pincer, third data point:** floor killed 153 + regime-gate shadow-killed 71 during
   the best short tape ever (prior data: 11-08 storm 489 floor-blocks; BANANA rationale
   documented; A1/flip1 bars both 11-17). Rule: accelerate either bar read with the crash
   evidence now (the verdict's speed mandate), or hold to11-17 with the answer for why
   dump-shorts must wait 4 more days. Also: pump-chain-short-high 60 + oversold-knife 39 —
   confirm KEEP (protected/data-backed) rather than re-litigate.
3. **compaction_stale 189** — previously ruled FORBIDDEN to relax (7d −$31.55) — confirm
   that ruling holds even in a mega-crash, or carve an exception? (That ruling's evidence
   was range-bound; a −7.78% trend day may be a different population — if you see it that
   way, say what bar distinguishes them.)
## Also rule
4. The four DECISION-DUE defaults firing 08:15 today + winner-cell overdue (default REVERT
   MULT=1.0): disposition each or confirm defaults fire.
5. Deliver: ranked execute-now actions (with exact flags/sites), what stays shadow (bars
   moved or held), and what T should see in the logs during the NEXT dump leg as proof the
   system "asked for" that opportunity.
Constraints: no blanket kills, protected flags, net-of-fees, token-day dedup, flag polarity,
speed mandate, fold framework (fold averted; fee-net now +0.15 — first greenish signal in days).
