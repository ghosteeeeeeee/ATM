## CEO Report — 2026-08-10 SL vs Cut-Loser Analysis

### Key Insight

The user identified a critical interaction between SL and cut_loser:

**Current parameters:**
- SL: 1.2% from entry (ATR_SL_MIN = 0.012)
- cut_loser: -2.0% PnL (CUT_LOSER_PNL = -2.0)
- Leverage: 5x

**With 5x leverage:**
- cut_loser triggers at: -2.0% PnL = **0.4% price drop**
- SL triggers at: **1.2% price drop**

**Conclusion:** cut_loser is TIGHTER than SL for losing trades.

### Data Evidence

**7-day atr_sl_hit exits (138 trades):**
- Average PnL: -0.55% (-$0.06/trade)
- Most exits cluster at -0.3% to -0.8% PnL
- **0% win rate** on SL exits (all losses)

**7-day cut_loser exits (29 trades):**
- Average PnL: -0.35% (-$0.04/trade)
- Cuts at -0.1% to -0.9% PnL
- **Tighter than SL** for most losing trades

**Key finding:** cut_loser already exits trades BEFORE they reach the 1.2% SL. The SL is redundant for losing trades.

### Implications

1. **SL is redundant for losing trades** — cut_loser closes them first
2. **Only V-shaped recovery works** — price must drop, cut_loser closes, then price recovers
3. **Any pullback = closed by cut_loser** — no room for trades to recover
4. **1.2% SL is wasted risk** — we're exposed to 1.2% drop but cut_loser kicks in at 0.4%

### CEO Decision Needed

Should we:
1. **Tighten SL to match cut_loser** — set SL at 0.4% (matches cut_loser threshold)
2. **Widen cut_loser to match SL** — set cut_loser at -6.0% PnL (1.2% price drop with 5x)
3. **Remove SL for losing trades** — let cut_loser handle all loss exits
4. **Keep current setup** — SL for profit protection, cut_loser as backup

The user's point: "is there a point having the SL so far for losing trades?" — if cut_loser will close them anyway, the wide SL is just exposing us to unnecessary risk.

### Recommendation

**Option 1: Tighten SL to 0.5%** — This matches the cut_loser threshold more closely and reduces maximum loss per trade. The 1.2% SL was widened from 0.8% on Aug 7 because 29/48 SL hits were noise — but cut_loser already handles the tighter exits.

**Expected impact:**
- Fewer trades reaching 1.2% SL (cut_loser catches them first)
- Tighter max loss per trade (0.5% vs 1.2%)
- Better risk/reward ratio

### CEO Decision — 2026-08-10

**Decision: Option 1 — Tighten SL to 0.5%**

Rationale:
- cut_loser fires at 0.4% price drop (5x leverage, -2.0% PnL)
- SL at 1.2% is 3x wider — dead weight for losing trades
- Tightening to 0.5% creates a natural backup: cut_loser catches first, SL catches if cut_loser misses
- Reduces max loss per trade from 1.2% to 0.5% (58% reduction)
- Data: 138 SL exits avg -0.55% PnL — trades hitting SL are already deep losers

**Changes:**
- ATR_SL_MIN: 0.012 → 0.005 (0.5%)
- ATR_SL_MAX: 0.025 → 0.010 (1.0% cap, still room for high-vol tokens)
- ATR_SL_MIN_INIT: 0.012 → 0.005 (matches ATR_SL_MIN)
- ATR_SL_MAX_INIT: 0.025 → 0.010 (matches ATR_SL_MAX)
- SL_PCT_FALLBACK: 0.012 → 0.005 (matches ATR_SL_MIN)
- STOP_LOSS_DEFAULT: 0.012 → 0.005 (matches ATR_SL_MIN)
- TP_PCT_FALLBACK: 0.024 → 0.010 (keep 2:1 R:R with new SL)

**Expected impact:**
- SL becomes backup to cut_loser (not redundant)
- Max loss per trade drops 58%
- Trades that would have hit 1.2% SL now cut at 0.5% or by cut_loser first

**Risk:** Trades that recover from -0.5% to breakeven will get stopped. But cut_loser data shows most losers don't recover — avg exit -0.35% PnL.

### Verification
- System on 15-day green streak
- 7d: 382T +$0.40 (52.9% WR)
- Both LONG and SHORT profitable
- Stars intact: bb_bounce+,hzscore+ LONG, bb_bounce+,range_finder+ LONG, bb-bounce-short,hzscore- SHORT
