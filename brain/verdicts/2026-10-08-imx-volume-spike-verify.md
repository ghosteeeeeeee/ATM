# Independent Verdict — IMX SHORT trade & pump-chain volume-spike filter claims

**Auditor:** independent (fresh read of source data; no trust in prior analyses — all numbers below come from code I ran)
**Date:** 2026-10-08
**Data sources:**
- PostgreSQL brain DB — `trades WHERE signal LIKE 'pump-chain%' AND direction='SHORT'` → **141 trades** (140 pre-IMX + IMX id=15985)
- `/root/.hermes/data/candles.db` — `candles_1m` and `candles_5m` for per-trade metric computation
- Methodology cross-validation: my computation on the pre-IMX 140-trade set reproduces the 2026-10-07 rise_1m audit *exactly* (27 blocked, 9W +$0.44, 15L −$2.30, 3 scratches, blocked sum −$1.86, kept +$1.57, baseline −$0.29) — so my pipeline and the canonical `rise_1m` definition agree.

**Metric definitions I used (explicit, since claims are definition-sensitive):**
- `rise_1m` = consecutive rising 1m closes walking backwards from the most recent candle with `ts <= open_time` (canonical convention)
- `vol_spike_1m` = volume of reference 1m candle / mean of prior N candles (N=20/60; reference = entry candle or last-closed candle)
- `vol_spike_5m` = volume of the 5m candle containing entry / mean of prior 20 5m candles (reproduces the "57x" claim exactly — see below)
- `rise_from_low` = (reference close − min low of prior window) / min low, windows 10/20/30/60 min, both last-closed and entry-candle variants
- Winners pnl>0, Losers pnl<0, Scratches pnl=0. Dataset: **71W 62L 8Z, total PnL −$0.52** (WR 50.4%)

---

## The IMX trade (verified from source)

| Field | Value |
|---|---|
| id / token | 15985 / IMX, SHORT, signal `pump-chain-` |
| Signal created | ~13:42:17 (metadata staleness 4.22 min, price_at_signal **$0.17469**) |
| Entry | **2026-10-08 13:46:30 @ $0.17711** |
| Exit | 13:53:43 @ $0.17895, **−$0.23 (−5.19% at 5x)**, exit_reason `hard_max_loss`, held 7.2 min |
| Volatility regime | EXTREME |
| 1m candle 13:45 | open 0.17440 → close 0.17620, **volume 287,518.08** |
| 1m candle 13:46 (entry) | volume 234,509.9 |
| Post-entry peak | 0.17865 recorded highest; 1m data shows 0.1798 by 14:00 — price kept rising **+1.5% after entry** |

---

## Claim-by-claim

### Claim 1 — "IMX SHORT entered at top of massive buying spike: volume 287,518 at 13:45 (57x normal), price rose +2.6% from $0.1741 to $0.1786"

**Verdict: PARTIAL**
**Evidence:**
- Volume **287,518.08 at 13:45** ✓ EXACT match to raw candle.
- **"57x normal" ✓ reproduces exactly** — but only under a **5m-candle definition**: 5m candle 13:45 (vol 827,105) / mean of prior 20 5m candles (14,436) = **57.3x**. (On 1m candles the true spike is even bigger: 74x–133x vs baselines of 10–360 candles. So 57x is if anything conservative.)
- "+2.6% from $0.1741 to $0.1786" is arithmetically true (2.59%), but **both endpoints are misleading**: $0.1741 is the 13:42 close (before the spike) and $0.1786 is the 13:53 **close after the entry/exit**. The rise from $0.1741 to the actual **entry price $0.17711 was +1.73%**, not 2.6%.
- **"Entered at top" is FALSE.** Entry was 1.5% below the subsequent peak (0.1798 at 14:00); recorded highest_price 0.17865; the short was underwater within minutes and hard-stopped. The entry was mid-spike, not the top.
- Root-cause nuance the claim misses: the signal fired **pre-spike** (~13:42 @ $0.17469) and was **executed 4.2 min later at $0.17711, +1.4% higher, after the spike had already started**. This is a stale-signal execution problem, not "shorting the top."

**Confidence: HIGH**

### Claim 2 — "Losers avg vol_spike=1.4x, Winners avg=0.5x"

**Verdict: PARTIAL (direction correct, numbers not reproducible)**
**Evidence (my computations over the 141 trades):**

| vol_spike definition | winners avg | losers avg |
|---|---|---|
| entry 1m candle / prior-20 avg | 0.22x | 2.17x |
| entry 1m candle / prior-60 avg | 0.40x | 4.34x |
| last-closed 1m / prior-20 | 0.89x | 16.77x |
| last-closed 1m / prior-60 | 1.83x | 12.25x |
| entry 5m candle / prior-20 5m (n=13 usable) | 0.79x | 8.09x |
| entry 1m / day-so-far avg | 0.89x (n=3) | 8.89x (n=8) |

- **No definition yields 1.4x / 0.5x.** The claimed values are not reproducible from source data under any natural definition I tested (the 1.4x losers avg is mathematically impossible for definitions where IMX itself is 14x–128x unless IMX was excluded or a different dataset was used).
- The **direction is robustly true**: losers' entry-candle volume massively exceeds winners' under every definition (2x–70x gaps).

**Confidence: HIGH** (on non-reproduction and direction)

### Claim 3 — "vol_spike > 2x filter: kills 0 wins, catches 1 loss, net=+$0.23"

**Verdict: AGREE (numbers reproduce) — with two material caveats**
**Evidence:**
- 1m entry-candle definition (windows 20 and 60 both): blocked = **1 trade = IMX only**, kills 0 wins, catches 1 loss, net delta **+$0.23** ✓ EXACT.
- Under the analyst's *own* 5m definition (the one giving claim 1's 57x): blocked = **2** (IMX 57.3x **and APT 2026-10-07 13:41, −$0.10, 2.4x**), kills 0 wins, catches 2 losses, net **+$0.33** — filter is *better* than claimed, but the claim's "1 loss, +$0.23" only reproduces on the 1m definition.
- **Caveat 1 (redundancy):** IMX already has `rise_1m = 2` and is blocked by the `rise_1m >= 2` filter. The 1m vol_spike>2 filter **adds ZERO trades** beyond rise_1m>=2. (The 5m variant adds only APT −$0.10 — the same trade the rise_from_low filter adds.)
- **Caveat 2:** 128 of 141 trades have zero-volume 5m candles (illiquid tokens), so any 5m-based filter is computable for only 13/141 trades from our DB — it cannot be the basis of a general filter.

**Confidence: HIGH**

### Claim 4 — "rise_from_low > 1.5% filter: kills 0 wins, catches 1 loss, net=+$0.23"

**Verdict: PARTIAL**
**Evidence:**
- Last-closed-candle measurement: **IMX rise_from_low = 1.44% (< 1.5%) — IMX is NOT caught.** The filter instead catches APT (Oct 7, −$0.10, 1.94%) only: kills 0 wins, catches 1 loss, net **+$0.10**.
- Entry-candle measurement: IMX = 2.01%, APT = 1.88% → catches **both**, kills 0 wins, catches 2 losses, net **+$0.33**.
- The claimed "1 loss (IMX), net=+$0.23" matches **neither** natural definition; it requires a threshold of ≈1.95–2.0% or mixed measurement.
- Window-sensitive: the 60-min-window version kills 3 wins (net +$0.81, WR effect worse). The clean "0 wins killed" property holds only for 10/20-min windows.

**Confidence: HIGH**

### Claim 5 — "rise_1m >= 2 is still the best: 18 losses caught, 9 wins killed, net=+$1.86"

**Verdict: PARTIAL (correct for the old 140-trade set; stale + framing caveats)**
**Evidence:**
- I reproduced the pre-IMX 140-set exactly: 27 blocked = **9 winners (+$0.44) + 15 real losers (−$2.30) + 3 scratches ($0.00)**, blocked sum −$1.86, kept +$1.57, baseline −$0.29. So "18 losses" = 15 losers + 3 scratches, and "+$1.86" is the **improvement delta** — the resulting book PnL is **+$1.57**.
- **Current 141-set (with IMX): blocked = 28 (9W, 16L, 3Z), net delta +$2.09, kept WR 54.9%, kept PnL +$1.57.**
- **"Still the best option" ✓ confirmed** by my sweep of every entry-time feature (vol_spike ×4 defs, rise_from_low ×8 defs, bb_position, speed_percentile, z_score, rsi_14, staleness, both directions, threshold grids): **no single feature beats rise_1m>=2 at a comparable block rate.** (speed_percentile>40.4 shows +$2.99 but only by blocking 84/141 = 60% of all trades and killing 36 winners — a blanket regime kill, not a filter.)
- Robustness (my tests): permutation p=0.0079 for the net improvement; **bootstrap 95% CI [−$1.75, +$1.91] — crosses zero**, so the *magnitude* is uncertain; time-split: first half +$0.71 (6W/6L, coin flip), second half +$1.38 (3W/10L) — edge is concentrated in recent trades.

**Confidence: HIGH**

### Claim 6 — "IMX trade has rise_1m=0, wouldn't be caught by rise_1m filter"

**Verdict: DISAGREE — factually wrong**
**Evidence:** IMX 1m closes before entry: 13:43 $0.1746 → 13:44 $0.1744 → 13:45 $0.1762 → 13:46 $0.1772 (live).
- Canonical convention (`ts <= open_time`, all candles): **rise_1m = 2** (0.1744 → 0.1762 → 0.1772).
- `ts < open_time`: still **2** (13:46:00 < 13:46:30 — the live candle is included).
- Fully-closed-only: **1**.
- **No convention gives 0.** A real-time filter at 13:46:30 (live close ≈ entry price 0.17711 > 0.1762 > 0.1744) computes **2 → IMX IS BLOCKED** by `rise_1m >= 2`.
- Consequence: the premise "rise_1m misses IMX, so we need vol_spike" **collapses** — the 1m vol_spike>2 filter adds no trade that rise_1m>=2 doesn't already catch.

**Confidence: HIGH**

---

## Recommended filter

**Keep `rise_1m >= 2` (canonical live-candle convention) as the sole block.** With IMX included it now blocks 28/141 (19.9%): kills 9 winners (+$0.44), catches 16 losers + 3 scratches (−$2.53), improving the book by **+$2.09** (−$0.52 → +$1.57, WR 50.4% → 54.9%) — and it catches the IMX trade itself.

- **Optional marginal addition:** `OR rise_from_low(10m, entry-candle) > 1.5%` → blocks 29, net **+$2.19**, kept WR 55.4% (adds only APT −$0.10).
- **Do NOT add the vol_spike > 2x filter** — it is strictly redundant (catches only IMX, already caught by rise_1m>=2); its 5m variant is uncomputable for 128/141 trades.
- **Do NOT chase speed_percentile/bb_position bulk filters** — they only outperform by blocking 30–60% of all trades (blanket kills).
- **Honesty caveats:** in-sample threshold, 28 blocked trades only, bootstrap CI on magnitude crosses zero, edge concentrated in the second half of the sample. Treat as a modest unconfirmed edge; validate on fresh out-of-trade data before trusting the magnitude.
- **IMX root cause for the pipeline:** stale signal (4.22 min) executed +1.4% above signal price after the pump began — a re-validation-at-execution gap, not a missing volume filter.

## Bottom line

The claims' *direction* is broadly right (volume spikes mark bad shorts; rise_1m>=2 is the best single filter), but the analysis that motivated the volume-spike filter rests on one factual error (**IMX rise_1m = 2, not 0**) and one misleading narrative ("entered at the top" — it entered mid-spike on a 4-minute-stale signal). The vol_spike filter adds nothing. The rise_1m filter already catches IMX, making the book +$2.09 instead of the claimed +$1.86.
