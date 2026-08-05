# WR Filter — Per-Coin Win Rate Gate at Signal_compactor Level

## The Problem: WR Feedback Loop

Tokens with a losing history in PostgreSQL `brain.trades` create a feedback loop:

```
signal_compactor approves ASTER LONG → decider_run executes → HL trade loses → PostgreSQL WR drops
                                                   ↑                                                           ↓
                              ASTER LONG APPROVED again next cycle ← blocked by WR gate at decider_run
```

**Result**: signal_compactor keeps selecting the same bad tokens → they get approved → WR gate blocks them → signal_compactor re-selects them next cycle. The system spins on the same losers forever.

## Root Cause Location

- `decider_run.py:1785-1789` — WR gate only exists HERE (execution-time)
- `signal_compactor.py` — had NO token-level WR check before 2026-05-11

The WR gate was applied too late. Tokens were already approved and hot-set entries were already built before the WR filter could block them.

## The Fix: Per-Coin WR Filter in signal_compactor.py

Two locations needed the same fix:

### 1. Main hot-set builder loop (line ~945)
```python
wr, wr_count = _get_token_wr(tkn, direction)
if wr < 50 and wr_count >= 3:
    log(f"  🚫 [HOTSET-FILTER] {tkn}: {direction} blocked — WR={wr:.0f}% ({wr_count} trades)")
    continue
```

### 2. `_filter_safe_prev_hotset` preservation pass (line ~1373)
```python
wr, wr_count = _get_token_wr(tok, direction)
if wr < 50 and wr_count >= 3:
    continue  # skip — don't preserve bad tokens across cycles
```

## The `_get_token_wr` Cache Function

```python
_dir_wr_cache = {}    # (token, direction) -> (wr, count, timestamp)
_DIR_WR_CACHE_TTL = 300  # 5 min cache

def _get_token_wr(token: str, direction: str) -> tuple:
    key = (token.upper(), direction.upper())
    now = time.time()
    if key in _dir_wr_cache:
        cached_wr, cached_count, cached_at = _dir_wr_cache[key]
        if now - cached_at < _DIR_WR_CACHE_TTL:
            return cached_wr, cached_count
    # PostgreSQL query — 7 day window, status='closed', token + direction
    total = row[0] or 0
    wins = row[1] or 0
    if total == 0:
        wr = 50.0  # neutral — no history
    elif total < 3:
        wr = 50.0  # need 3 trades to judge
    else:
        wr = round((wins / total) * 100, 1)
    _dir_wr_cache[key] = (wr, total, now)
    return wr, total
```

## Why ETHFI Had 15 Trades with 46.7% WR

ETHFI wasn't broken by the WR logic — it was generating micro-trades at an alarming rate:
- 15 trades in ~22 hours (May 10-11)
- Many closed in 4-12 seconds (e.g., +$0.02, -$0.33, -$0.19)
- The system kept firing LONG on ETHFI because signal_compactor didn't know it was a documented loser
- Each trade was ~$0.02-$2.03 — tiny wins and losses that individually closed fast

Signal generation was producing `accel_300_long` at 80% confidence for ETHFI every minute → approved → executed → tiny loss → repeated. The WR gate at decider_run blocked it, but signal_compactor kept feeding it.

## The Two-Layer Architecture Bug (Pre-Fix)

Signal_compactor's cosig-gate uses **signal-type WR** (e.g., `accel-300+` alone = ~40% WR), not **token-level WR**. So it approved tokens that were individually broken, and the WR gate at decider_run had to clean up the mess.

After the fix: tokens with <50% WR and ≥3 trades never enter the hot-set from signal_compactor. The WR gate at decider_run becomes redundant (but stays for defense-in-depth).

## Key Lesson

**Filter at signal generation, not at execution.** The WR gate in decider_run was the right idea but the wrong place — by the time a token reaches decider_run, signal_compactor has already built hot-set entries and approved signals for it. The feedback loop is broken at the source.

## Related Files
- `signal_compactor.py` — `_get_token_wr()`, main hot-set builder loop, `_filter_safe_prev_hotset`
- `decider_run.py` — `_get_direction_wr()` (still present for defense-in-depth)
- PostgreSQL `brain.trades` — authoritative WR source

## Monitoring Commands
```bash
# Check which tokens are currently blocked by WR filter
cd /root/.hermes/scripts && python3 signal_compactor.py --dry 2>&1 | grep "HOTSET-FILTER.*WR="

# Check PostgreSQL WR for all traded tokens
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, direction, COUNT(*) as trades, ROUND(SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as wr_pct FROM trades WHERE close_time >= NOW() - INTERVAL '7 days' GROUP BY token, direction ORDER BY wr_pct;"

# Check tokens with zero history (pass WR filter by default)
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT DISTINCT token FROM trades;"  # compare against signal universe
```