# Guardian Exit Routing — The Custom Exit Problem

## The Architecture Problem

The Guardian's ATR trailing stop is **stateless with respect to entry signal source**:

```
signal fires → guardian opens position → guardian's OWN ATR trailing stop runs independently forever
                                                          ↑ doesn't know which signal opened the trade
```

Every position gets the same ATR(14)×1.5 trailing stop, regardless of:
- Which signal opened it
- What timeframe the signal operated on
- Whether the signal has its own preferred exit logic

**Result:** Custom-entry signals with custom exits (Guppy, mean-reversion, scalping patterns) cannot plug into the existing system cleanly — the Guardian's one-size-fits-all exit runs in parallel and overrides.

---

## Concrete Example: Guppy with Fast-Group Exit

```
Guppy fires LONG @ 100
  → Guardian opens position
  → Guardian's ATR(14)×1.5 trailing stop kicks in @ 98
  → Price: 100 → 97 → 105 → 96 → 94
  → Guardian's ATR stop fires @ 96 (trailing locked at 98-1.5*ATR)
  → Guppy's fast-group exit would have fired @ 99.5 (correct "book profit fast" exit)

Loss: 4% instead of 0.5%
```

The Guardian's stop is 8× looser because it was designed for swing trades, not Guppy's short-horizon signals.

---

## Four Solution Paths

### Option A: Guardian Exit Override (recommended for cleanest implementation)

Modify the Guardian to:
1. Track `signal_source` on open positions (add a column or tag)
2. Maintain a lookup table: `signal_source → acceptable exit signals`
3. For positions opened by `guppy+`, accept `guppy_exit` signals and ignore standard ATR trailing
4. Optionally keep ATR stop as a hard cap (never close below this price)

**Minimum Guardian change:**
```python
# In guardian's exit evaluation loop
for pos in open_positions:
    entry_signal = pos.get('signal_source', 'generic')
    if entry_signal == 'guppy':
        # Skip standard ATR trailing — only close on guppy_exit signal
        if has_guppy_exit_signal(pos['token'], pos['direction']):
            close_position(pos)
        continue
    # Standard ATR trailing for all other signals
    evaluate_atr_trailing_stop(pos)
```

**Pros:** Clean separation, Guppy owns its exits
**Cons:** Requires Guardian modification (non-trivial, must coordinate with T)

---

### Option B: Guppy Exit as Separate Signal, Guardian Accepts It

The Guppy scanner runs continuously even after entry. When the fast group flips, it fires `guppy_exit_long` or `guppy_exit_short` signal. The Guardian is modified to accept `guppy_exit` as a valid close trigger for Guppy positions (matching by token + direction).

**Same Guardian modification as Option A** — the Guardian needs to know which position was opened by which signal.

**Pros:** Guppy exit goes through the standard signal pipeline
**Cons:** Same Guardian modification required

---

### Option C: Separate Sub-Account / Wrapper

Route Guppy entries through a **separate wallet or sub-account** that doesn't use the Guardian's ATR trailing at all. A custom wrapper script manages Guppy exits directly via Hyperliquid API.

**Pros:** No Guardian modification needed, complete isolation
**Cons:** More complex operational overhead (multiple wallets, double-entry risk)

---

### Option D: Tighten Standard ATR Params for Short-Horizon Signals

If the Guardian checked the `timeframe` or `hold_expected` field on the signal and applied different ATR multipliers:
- 1m signals: ATR×0.75 (tighter stop, "book profit fast")
- 5m signals: ATR×1.5 (standard)
- 1h+ signals: ATR×2.0 (looser for swings)

**Pros:** Minimal Guardian change, approximates Guppy's preferred exit
**Cons:** A hack — not a real solution, assumes 1m = short-horizon which isn't always true

---

## Which Path to Take

**For Guppy specifically:** Option A/B combined:
1. Guardian tracks `signal_source` on positions
2. Guppy fires entry (`guppy_long`) and exit (`guppy_exit_long`) signals
3. Guardian has a hardcoded rule: `guppy_exit` closes `guppy` positions
4. Guardian keeps a floor stop (ATR×1.0 or fixed 2%) as worst-case protection

**This is a medium-complexity Guardian modification.** The key question is whether the Guardian currently stores the entry signal source at all — if not, that column needs to be added.

---

## How to Check If Guardian Stores Entry Signal

Look at the PostgreSQL `trades` table or wherever the Guardian tracks open positions:

```sql
\d trades  -- describe table schema
SELECT signal_source FROM trades WHERE status='open' LIMIT 5;
```

If `signal_source` column doesn't exist, Option A/B requires a schema migration first.

---

## Implication for All Custom-Exit Signals

Any signal that needs its own exit logic (not just entry) faces this problem. The Guppy case is the most concrete example, but the same issue applies to:
- Mean-reversion signals (need quick XB/UL exits)
- Scalping signals (tight stops, fast exits)
- Any signal with a `hold_bars` or expected duration significantly different from "standard swing"

**Design principle:** The current system is **entry-centric** (signals only fire at entry, Guardian handles all exits). Adding exit-routing capability is the missing piece for more sophisticated signal types.
