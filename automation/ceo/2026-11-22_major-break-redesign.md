# STRATEGY REDESIGN BRIEF — major-break entries, structure-only exits (2026-11-22)

From: lead agent. To: CEO automation (deep run — decide + edit).
Context: T's directive (verbatim essence): *"we're possibly getting wicked into
what is not actually the structural break we are looking for… relaxing the
entries a little so there is a little more confirmation and conviction… we buy
at the levels where momentum is strong and we ride the wave. MAJOR BREAKS. For
exits a similar story: wait for an ACTUAL break of structure — we are currently
going in at micro moves and getting stopped out on micro moves. If our entries
are better we can ride each wave longer and more profitably. Our long/short
levels are candidates for bounces as much as for breakouts. Price can really
only go up, down, or sideways."*

Also folds in TWO DECISIONS your previous follow-up deep
(20261121T183323Z) timed out WITHOUT writing (no decision checkpoint exists —
verified): the BE-arm threshold (A) and the heat ratio (RULINGS BELOW).

---

## EVIDENCE (all executed, last 4 days, n=75 closed, PG brain)

**The confirmation split (the whole case in three rows):**
| Entry class (MFE) | n | net | per trade |
|---|---|---|---|
| **ran ≥1.0%** | 15 | **+$2.04** | +$0.136 |
| mid 0.3–1.0% | 42 | +$0.41 | +$0.010 |
| **never <0.3%** | 18 | **−$2.59** | −$0.144 |

The entire 4-day net (−$0.135) is the never-ran population. Better entries =
the whole difference.

- **Micro-stop class:** 15/75 lost with MAE <0.5% (stopped on micro moves) ·
  18/75 never ran · 21/75 dead <20min · ~19 trades/day (the overtrading feel).
- **Exit-reason cluster:** profit-monster-trail 27 (the mirror winners) ·
  **prearm_lock 12** (the BE-locks on ~0.3% peaks = micro-locks: #17033/34/35
  pump-chain all exited at MFE 0.32-0.34, −$0.01..0.03) · manual_sl_hit 8 ·
  atr_sl_hit 6 · cut-loser 3 · hard_max_loss 4 · mfe_exit 5.
- **The ladder's own losers are all never-ran:** #17004 (MFE 0.00, 3min,
  −$0.19), #17008 (0.01, −$0.17), #17032 (0.02, −$0.14), #17052 (0.11,
  −$0.18) — wicked into non-breaks, stopped on the micro-retrace.
- **The winners all ran:** #17014 (+$0.50, MFE 1.54), #17024 (+$0.24, 2.88),
  #17016 (+$0.20, 2.75), #17007 (+$0.20, 1.38), #17049 (+$0.16, 2.95).
- Cost context (accounting reconciliation, 2026-11-22): all-time HL-verified
  net −$128.52; fee rate pre/post BUG-099 = 7.7× inflation — the cost line is
  the binding constraint, so FEWER, BETTER entries also cut the fee drag.

---

## DECISION 1 — E1: the ENTRY model (major break + momentum confirmation)

**Ruling needed:** replace the fill-on-micro-cross with **fill-on-confirmed-
momentum-at-the-level**, per T: "we buy at the levels where momentum is strong
and we ride the wave… we don't have to sit around waiting for it to come back
to that level."

Proposed mechanics (the machine change):
- At a level cross, require **displacement confirmation** before filling: the
  first CLOSED bar beyond the level must exceed it by ≥ `MOMENTUM_ATR_K` ×
  ATR(15m) (or an equivalent impulse/volume proxy — pick the proxy).
- Confirmed → **fill immediately on the break** (no retest wait — the
  confirmation substitutes for the return-to-level; this is the "don't sit
  around waiting" half).
- NOT confirmed → the rung does NOT fill and does NOT burn: it falls back to
  today's retest-wait (reclaim → re-cross) as the secondary path — so a level
  that later retests with momentum still gets its entry.
- Net effect on overtrading: strictly fewer fills (the never-ran class is
  filtered at the source); ~19/day → whatever the confirmation allows. NO
  separate daily cap proposed (T said "only slightly").
- Parameters to set: `MOMENTUM_ATR_K` (rec ~0.5), the confirmation bar (1m vs
  first closed 15m), and whether volume participates.

## DECISION 2 — E2: the EXIT model (actual structure breaks only)

**Ruling needed:** kills the micro-stop class. Evidence: 15/75 micro-stopped,
12 prearm_locks on ~0.3% peaks, the ladder's never-ran losers.

Proposed: **stops live only at actual structure** (the confirmed swings / the
1h lines / the major rounds T names) — no entry-anchored micro-locks:
- **FOLD-IN A (the timed-out Decision A — BE-arm threshold):** the corrected
  data stands (incidents #17005 +0.54% / #17013 +0.61% / #17026 +1.28% vs the
  V-class #16915 +9.96%). Given T's new "wait for an actual structure break",
  the options re-present as: (a) keep 0.40% (the cited class keeps dying), (b)
  BE-arm at ~2.5% peak (separates retest-class from V-class), (c) never arm
  for ladder trades (pure structure stops — the strictest reading of this
  directive), (d) your number. **Rec: (b) 2.5%** with (c) as the alternative
  if you read T's directive as absolute.
- **prearm_lock (the mirror's BE-lock):** 12/75 exits on ~0.3% peaks — apply
  the same peak threshold (or retire it) so micro-peaks stop locking.
- The round-anchor stays shadow (D1c stands); the structure trail governs.

## DECISION 3 — E3: DUAL-USE levels (bounce + breakout at every level)

**Ruling needed:** T: "our long/short levels are candidates for bounces as
much as for breakouts… price can really only go up, down, or sideways."
At each armed level there are exactly three outcomes: through (momentum) =
the break ride; hold + reject = the bounce (the fade the other way); nothing =
sideways (no trade). Proposed: each level carries BOTH triggers —
- **break trigger** (Decision 1's momentum-through fill), and
- **bounce trigger**: rejection at the level (price touches/fails the level and
  turns, with the rejection candle closing back inside) → fill the OPPOSITE
  side at the level with the stop beyond the level — the bounce trade.
- The momentum proxy discriminates: strong through = break; strong rejection =
  bounce; neither = no trade.
- This revives the parked D1 retest-fade ONLY as level-behavior (not the full
  fade system — D1 stays parked); sizes stay the rung sizes.

## FOLD-IN B (the timed-out Decision B — heat ratio)

The notional/equity/0.15 formula is permanently dark at this account (equity
$16.11; one $22.30 rung = heat 1.39 > 0.15 → every ladder fill defers).
Options: (a) **margin-based: Σ(amount_usdt/leverage)/equity, cap 0.15** (rec:
~2 concurrent rungs fit; the cap meaningfully bounds the stack), (b) notional
with a recalibrated cap (≥4), (c) drop the gate, (d) your ratio/cap. The
equity parse itself is FIXED (lead, nested marginSummary.accountValue).

---

## What we need back

Rulings on E1/E2/E3 + fold-ins A and B (edit the code/constants directly or
return the numbers). Compose with the standing doctrine: stay-in
(drawdown-driven exits), conviction, adds-on-winners with the D2.3 band, the
multi-touch/escape machine (E1 modifies its fill path, not its state
discipline). The lead agent implements/verifies anything you rule that this
run does not directly edit; the bug-hunter verifies the combined changeset
before any commit (the current uncommitted set = your first deep's landed
edits + lead's blocker/LOW/MEDIUM fixes, pending round-2).
