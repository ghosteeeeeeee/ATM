# RS Signal Backtest Tiers — Key Findings (2026-05-05)

## backtest_rs_tiers.py
**Location:** `/root/.hermes/scripts/backtest_rs_tiers.py`
**Purpose:** Enhanced RS signal quality analysis — touch count tiers, bounce confirmation, ATR distance bands, recently-broken level filter, direction breakdown, and combined filter combos.
**Test scope:** 859 RS signals across BTC, ETH, SOL, AVAX, LINK, ARB, APT, DOT — 4700 candles each.

---

## Finding #1 — Recently Broken Level is the #1 Differentiator

**The single most important RS quality filter.**

```
recently_broken : n=598  WR=27.4%  PnL=-0.010%
level_intact    : n=261  WR=42.5%  PnL=+0.049%
```

**15-point win rate difference.** If a level was crossed in the last 20 candles, it should NOT be traded.

**Implementation:** Add `_level_recently_broken` check in `rs_signals.py`. For each swing level found, scan the last 20 candles — if price crossed that level within 20 candles, skip the level entirely.

---

## Finding #2 — ATR Distance 0.3-0.6 Band is a Trap

```
atr_dist 0.0-0.3 : n=446  WR=32.7%  PnL=+0.030%  ← best
atr_dist 0.3-0.6 : n=143  WR=30.1%  PnL=-0.095%  ← WORST band
atr_dist 0.6-0.9 : n=152  WR=32.9%  PnL=+0.067%
atr_dist 0.9-1.2 : n=118  WR=30.5%  PnL=-0.025%
```

The 0.3-0.6 ATR band produces **negative average PnL** — price is close enough to feel the level but not AT the level. This is the danger zone.

**Filter rule:** Reject signals where `0.3 < atr_dist < 0.6`. Either require `atr_dist < 0.3` OR `atr_dist > 0.6`.

---

## Finding #3 — Touch Count Tier Results (Surprising)

```
low (<10)     : n=  13  WR=38.5%  ← small sample, best WR
mid (10-49)   : n= 101  WR=28.7%  ← WORST tier
high (50-199) : n= 334  WR=34.4%  ← best clean tier
vhigh (200+)  : n= 411  WR=30.7%  ← worse than high
```

The mid-tier (10-49 touches) significantly underperforms. Very high touch counts (200+) don't add value over the high tier (50-199).

**Implication:** Raising the RS touch minimum from 2 → 5 would eliminate the worst-performing tier (mid). Raising to 50 would keep only the best-performing tier.

---

## Finding #4 — Bounce Confirmation is Marginal

```
bounce_confirmed : n=635  WR=33.7%  PnL=+0.004%
no_bounce       : n=224  WR=27.2%  PnL=+0.022%
```

Only a 6.5-point WR difference. Not a strong filter in isolation. Bounce confirmation alone does not robustly separate winners from losers.

---

## Finding #5 — Combined Filters Define the Ideal RS Signal

```
touch>=10 + intact              : n=252  WR=42.9%  PnL=+0.051%
touch>=50 + bounce + intact     : n=157  WR=44.6%  PnL=+0.080%  ← gold standard
touch>=50 + bounce + intact + atr: n=106  WR=44.3%  PnL=+0.034%
```

The combination of `touch>=50 + bounce + intact` (no recently broken) produces a 44.6% WR — a 12-point improvement over the overall 32% WR.

---

## Finding #6 — SHORT Outperforms LONG for RS Signals

```
LONG  : n=617  WR=29.8%  PnL=+0.010%
SHORT : n=242  WR=37.6%  PnL=+0.003%
```

RS-based SHORT signals have a 7.8-point WR advantage over LONG. RS signals are better at identifying resistance breaks than support bounces.

---

## Priority Implementation Order

1. **Reject recently-broken levels** — highest impact (15-point WR gain)
2. **Add ATR distance filter (ban 0.3-0.6 band)** — removes negative PnL band
3. **Raise RS touch minimum to 5** — eliminates the worst-performing mid tier
4. **Use combined filter: touch>=50 + intact** — targets 42.9%+ WR

---

## Backtest Methodology Notes

- Forward window: 15 candles (15 min for 1m data)
- `recently_broken` definition: price crossed the level within last 20 candles
- `bounce_confirmed`: price bounced from the level in the last 5 candles
- `atr_dist`: `|level - current_price| / ATR_14`
- Source format: `rs-s####` (support) or `rs-r####` (resistance), where `####` = sum of touches across clustered levels
