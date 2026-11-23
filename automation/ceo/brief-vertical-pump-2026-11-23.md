# BRIEF: T — "BTC vertical mode, alts pumping, we should be trading NOW" (2026-11-23)

## T's words (verbatim intent)
"BTC is possibly in 'straight up' vertical mode (like we've discussed might happen before),
alts are pumping too (CHIP, DOGE), **we should be taking trades right now. We are here for
the volatility, it is here, let's get rolling.**"
→ Urgency: the pump is LIVE. Attribution of any idleness + the ranked list that legitimately
opens the taps in THIS tape. T has now asked for trades in three consecutive messages
(crypto-shorts 11-20, pump-long-push 11-16, this) — the pattern of "volatility here, system
still" is his repeated frustration.

## Parent's verified data (2026-11-23 14:49Z — trust, spot-check)
- **BTC +3.08%/8h (61,450→63,343), +3.01% of that in the last 3h** (high 64,281) — vertical
  confirmed. BTC 1h move **+5.11%** (pump-side of every band).
- **Alts (8h):** APEX +19.5 · CHIP +12.5 · INJ +12.3 · ALGO +11.7 · ZEC +11.3 · POPCAT +9.6 ·
  PENGU +9.2 · KAS/ENA/USELESS +9.0 · SUI +8.9. (Parent's first mover query returned [] —
  self-inflicted threshold bug: >=100 bars required vs 96 max in 8h; corrected >=80 → table
  above. DOGE: not in top-12, spot-check its actual move.)
- **Fills: 8 LONG opens/8h (net −$0.01), 2 open (ai-trader-auto LONG ×2)** — SOMETHING is trading.
- **DailyFillCap ENGAGED since 14:48: 16/15 opens, fee-net −$0.54, 821 blocked today
  (446 true events)** — the brake is HOLDING candidates DURING the vertical move, and −0.54 is
  just past the never-answered margin option (−0.50): T said "margin or leave" → never answered
  → now blocking his own "get rolling."
- **combo_keys: 15–19 per 5-min window "not executed"** (log lines 14:47–14:49) — the exec
  layer is receiving ready combos and not filling them (hotset? exec-block? attribution owed).
- R2 DD tier ACTIVE (size_multiplier 0.25 written 01:36Z) — floor-eaten for floored trades
  (median $11.10), −50% only above ~$44 base. Confirm it interferes with nothing at current sizes.
- Recent restores: pump_chain_v6 short-only (dump side, for EXTREME SHORT — not this pump) ·
  bare pc+ trades EXTREME unaided but `PUMP_CHAIN_LONG_HIGH_BLOCK` blocks pc+ in HIGH —
  actual regime NOW = spot-check (classify_volatility: ATR% <1.5 = HIGH, >=1.5 = EXTREME).

## Questions to rule (urgently — this tape is moving)
1. **Attribution RIGHT NOW:** decompose what's holding fills in the current window: (a) brake
   446 true events held at −0.54 (how many QUALIFIED longs among them), (b) combo 15–19/5min
   not executed — which layer eats them (hotset rotation? exec-block? fill-cap cascade),
   (c) vol-regime blocks: is BTC/alt regime HIGH (pc+ LONG blocked via :3684) vs EXTREME
   (allowed)? Name each owner with counts, like the bounce-attribution method.
2. **What legitimately opens the taps NOW (ranked, each with revert):**
   a. **The brake margin — put it back to T in one line** (the −0.50 option would have
   released it at −0.54... state precisely: would it release now or not; T owes the word).
   b. Pump-side long coverage in THIS regime: btc-pump-rider+ (boosted 1.3 — firing?),
   volume-breakout-long+, pc+ if regime is EXTREME vs HIGH — if HIGH blocks pc+ while a
   +5%/1h vertical pump runs, is THAT block correct by its own data (HIGH pc+ measured where?)
   or a stale-justified kill? Only move it if the bar supports it — but RULE on it.
   c. Combo-not-executed (item 1b fix): if it's a defect (double-open guard? hotset pin
   OFF? fill cap cascade), fix directly per Bug-Fix-Rule; if by-design, say which rule.
   d. Anything else in the current stack that's holding qualified entries against T's
   standing "every pump is a LONG opportunity" doctrine — with numbers.
3. **R2-tier interplay:** confirm 0.25× + floored sizes = no material interference with
   getting trades on now (and what happens if the pump wants size above $44 — is that a
   feature or a surprise?).
4. **Deliver:** the attribution table, the ranked opens-now list (fastest first), and the
   proof lines T should see within the hour if "rolling" actually happened (EXEC lines,
   brake RELEASED, combo fills).
Constraints: no blanket kills, protected flags, net-of-fees, token-day dedup, flag polarity,
speed mandate, fold/circuit-breaker intact. Read-only — rulings + ranked list only.
