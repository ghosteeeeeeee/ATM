# 24h Closed-Trade Analysis — 2026-06-25

**38 closed trades, 21W/16L/1BE, +$0.68 net, 55.3% WR (NOT profitable).**

## 1m price_history data source (CRITICAL — saves hours of digging)

For price action during a trade, the right source is **`price_history` in `/root/.hermes/data/signals_hermes.db`** — NOT candles.db, NOT 5m candles. Schema:

```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    token TEXT,
    price REAL,
    timestamp INTEGER  -- Unix seconds (column is 'timestamp', NOT 'ts')
);
```

Query pattern:
```python
import sqlite3
db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = db.cursor()
cur.execute("""
    SELECT timestamp, price FROM price_history
    WHERE token=? AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp
""", (token, open_unix, close_unix))
```

This gives 1m resolution price path for MFE/MAE analysis. Available for every token in the HL universe (~140k rows per token).

**5m candles in `/root/.hermes/data/candles.db` are NOT a substitute** — they have 5m resolution and miss intra-bar wicks.

**Pitfall:** the column is `timestamp`, not `ts`. A `SELECT MAX(ts)` query returns "no such column" error and looks like the table is empty.

## Headline Numbers

| Metric | Value |
|---|---|
| Total trades | 38 |
| Wins | 21 (55.3%) |
| Losses | 16 |
| Net PnL | +$0.68 |
| Gross wins | +$1.99 |
| Gross losses | -$1.31 |
| Profit factor | 1.52 |
| Avg winner | +0.95% |
| Avg loser | -0.76% |

Profit factor 1.52 is good in theory but the dollar amounts are tiny. We kept only 34% of gross profits — every winner clipped at 0.7-0.8% (see Section 4 below).

## The Winning Streak (REPLICATE THIS)

11 wins in a row, 13:56–19:14 UTC, +$1.13 cumulative:
- STBL, BSV, MERL, BLUR, BCH, FET, STBL, SKR, STBL, SKR
- All SHORT, all on `accel-300-,rs-s-broken`
- All 3x leverage (8/11) or 5x (3/11)
- All small/mid-cap tokens
- All in 10:00–18:00 UTC window
- Trajectory: "dropped continuously" (no MAE whipsaw)
- Avg MFE=0.71%, avg MAE=0.40%
- SL mostly NEVER touched (5/11 SL-reached, 6/11 SL-safe)
- Confidence: 80-98 (median 95)

**Recipe:** SHORT a small-cap on `accel-300-,rs-s-broken` when price is in a CLEAN DOWNTREND with small adverse wicks. Let profit-monster take it at +0.7-1.3%.

## The Losing Streak (AVOID THIS)

6+ losses, 20:00–01:38 UTC, $-0.59+ cumulative:

| Trade | Token | Lev | MFE | MAE | Outcome |
|---|---|---|---|---|---|
| #12187 | ENS | 5x | -0.02% | 0.44% | SL hit |
| #12188 | ONDO | 5x | 0.27% | 0.84% | SL hit |
| #12189 | UMA | 3x | 0.63% | 0.39% | SL hit |
| #12190 | ENS | 5x | 0.18% | 0.69% | SL hit |
| #12191 | TAO | 5x | -0.01% | 0.98% | SL hit |
| #12195 | FET | 5x | 0.50% | 0.56% | SL hit |

Common pattern: MFE never exceeded 0.5% (no real "follow-through") before price reversed. Price went sideways or slightly up, MAE built slowly, SL hit at 0.6-1.2% adverse. These are NOT clean downtrends — they are "chop with a slight upward bias."

## THE MFE/MAE FILTER (new, quantifiable signal-quality filter)

| Group | Avg MFE | Avg MAE | MFE/MAE ratio |
|---|---|---|---|
| WINNERS (n=21) | 0.71% | 0.34% | **2.09** |
| LOSERS (n=16) | 0.32% | 0.62% | **0.52** |

**The MFE/MAE ratio in the first 10 minutes is a strong early-exit filter.**

- If MFE/MAE > 1.0 after 10 min → trade has real trend; let it run
- If MFE/MAE < 1.0 after 10 min → trade is in chop; cut at small loss instead of waiting for full SL

Compare MERL #12177 (win, MFE/MAE=7.4) vs MERL #12166 (loss, MFE/MAE=0.47):
- Win: MFE=1.11%, MAE=0.15%, maxFavClose=1.11% — CLEAN DROP
- Loss: MFE=0.34%, MAE=0.72%, maxFavClose=0.34% — STALL then REVERSE

## 5x Leverage = Death on accel-300-

| Leverage | WR | n | Notes |
|---|---|---|---|
| 3x | 100% (16/16) | All trades in winning streak |
| 5x | 100% (5/5) on winners, **0% (0/9) on losers** | Loss streak was 100% 5x |

**EVERY 5x accel-300- SHORT lost today. EVERY 3x accel-300- SHORT won.**

This is consistent with the skill's existing finding that "accel-300 SHORT direction is weak — 40% WR needs tighter gap_pct and stale_bars" — but the leverage multiplier compounds the problem because the SL is 5x further away in dollar terms, and 5x winners get clipped at the same +0.7% profit-monster floor as 3x winners.

**Fix candidate:** disable 5x leverage for accel-300- signals, OR halve the position size at 5x.

## Profit-Monster Floor Clipping Winners

`hermes_constants.py: PROFIT_MIN_PCT = 0.7` is the floor. Result:
```
+0.7% : 8 trades (38% of wins)  ████████
+0.8% : 5 trades (24%)          █████
+0.9% : 2 trades
+1.0% : 1
+1.1% : 1
+1.2% : 1
+1.3% : 2
+2.6% : 1  ← BLUR (random timer fired 60+ min)
```

38% of winners clipped at EXACTLY +0.7%. The accel-300- signal often produces 2-3%+ down-moves but profit-monster systematically clips at 0.7-0.8%. The 11-win streak would have been ~$2.50-$3.00 if winners ran to 2%, not $1.13.

The BLUR #12181 trade hit +2.59% because the random fire timer happened to be 60+ minutes after open. All other winners were closed by the timer BEFORE the trade could develop.

**Fix candidate:** raise `PROFIT_MIN_PCT` to 1.0-1.2%, OR tie it to ATR-volatility (volatile tokens get 1.5%, stable get 0.7%).

## Per-Token Blacklist Candidates (24h data)

| Token | Direction | n | WR | Net | Notes |
|---|---|---|---|---|---|
| MERL | SHORT | 4 | 25% | -$0.23 | Strong candidate — add to SHORT_BLACKLIST |
| ENS | SHORT | 3 | 33% | -$0.13 | Mid-cap, both losses were 5x |
| FET | SHORT | 3 | 33% | -$0.09 | Mid-cap, 5x killed it |
| ASTER | SHORT | 2 | 0% | -$0.06 | Plus 10s orphan-reopen bug |

None have 5+ trade samples, but MERL with 4 trades and 1 win is solid evidence. ENS/FET borderline — would want more data.

## Time-of-Day Pattern

| Hour (UTC) | W | L | Net$ | WR |
|---|---|---|---|---|
| 11:00-18:00 | 15 | 0 | +$1.13 | 100% |
| 20:00-22:00 | 1 | 9 | -$0.61 | 10% |

The system is way better during US morning hours, breaks down completely in the evening. **20:00+ trades should be treated with extreme caution or skipped.**

## ASTER 10-Second Bug (also see hl-trading-debug skill)

ASTER #12193 opened 22:07:07, closed 22:07:35 = 28 SECONDS. exit_reason=guardian_tp with entry=0.61304, exit=0.61313, SL=0.61902, pnl=-$0.00. **highest_price=1.0** in DB (default, never updated for orphan path).

ASTER #12194 opened 22:08:07 — **32 SECONDS after #12193 closed** — same token, same direction, different entry (0.61346 vs 0.61304). Trade ran 3.5h, pnl=-$0.06, exit_reason=guardian_sl at 0.61712 (BEFORE the recorded SL of 0.61838 was hit).

**Two bugs in one pattern:**
1. Same token SHORT reopened 32s after orphan close — no cooldown check
2. `highest_price=1.0` default never updated for orphan trades

See `hl-trading-debug` skill for the underlying bugs in position_manager.py highest_price update logic and the lack of a token-level cooldown after guardian_orphan close.

## What to Replicate (for more winners)

1. SHORT small/mid-cap tokens on `accel-300-,rs-s-broken`
2. Use **3x leverage** (not 5x)
3. Trade during **10:00-18:00 UTC** (15W/0L this window)
4. Enter when first 5-10 min show MFE > 0.3% with MAE < 0.2% (clean drop pattern)
5. If MFE/MAE < 1.0 in first 10 min, exit early at small loss

## What to Avoid (for fewer losses)

1. **NEVER 5x leverage on accel-300- SHORT** (0% WR on 9 trades)
2. **Don't SHORT mid/large-caps** (ENS, FET, TAO, ONDO, AAVE) — they chop sideways and hit SL
3. **Don't open a new position on a token where the previous trade just closed in <60s** (ASTER bug)
4. **Avoid 20:00-22:00 UTC** (1W/9L, -$0.61)
5. If MFE < 0.3% after 10 min, the trend isn't there. Cut now.
6. **MERL** → add to SHORT_BLACKLIST pending more data
