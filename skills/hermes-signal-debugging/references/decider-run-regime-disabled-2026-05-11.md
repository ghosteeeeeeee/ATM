# Decider-Run Regime Filter Disabled — 2026-05-11

## What Happened

1m linear regression regime check in decider_run was blocking all signal flow.

**Two regimes checked at execution time:**

### Counter-trend trap guard (lines 1689–1701)
Called `_get_regime_1m(token)` → passed result to `_check_counter_trend_trap()`. Blocked signals that were counter-trend per 1m LR. The 1m LR on 100 candles is extremely volatile — a shallow 1m downtrend produces `SHORT_BIAS` on nearly every token, causing the trap to fire on all LONG signals.

### Main regime filter (lines 1703–1751)
Full regime check using 1m LR:
- `is_delisted` block — legitimate safety check, kept
- `NOT_IN_JSON` blindspot block
- NEUTRAL regime with conf > 60% → de-escalate (soft skip)
- counter-regime → penalty: `min(int(regime_conf * 0.15), 15)` pts subtracted from confidence

**Penalty example:** at 80% regime conf, penalty = 12pts. A 78% signal drops to 66% — still above the 50% threshold. But combined with other gates, this was pushing marginal signals below the line.

## Why It Was Wrong

1m LR on 100 candles is **too noisy for execution gating**. The regime is meant to capture multi-hour trend direction, but a 100-candle 1m window is ~1.7 hours. Even in a ranging market, small price movements within the window produce large slopes.

Result: nearly ALL tokens showed `SHORT_BIAS` during what was actually a neutral market. LONG signals were being penalized or blocked as "counter-regime" when the regime reading was just noise.

The **WR gate is the correct execution filter** — it uses real trade history (PostgreSQL `brain.trades`), not a computed proxy. The regime filter was adding confusion on top of it.

## What Was Disabled

```python
# ── Counter-trend trap guard — DISABLED 2026-05-11 ─────────────────
# _exec_regime, _exec_regime_conf = _get_regime_1m(token)
# trap_blocked, trap_reason = _check_counter_trend_trap(...)
# if trap_blocked: ... continue

# ── Regime filter for approved signals — DISABLED 2026-05-11 ───────────
# (entire block commented out)
```

**What remains active:**
- `is_delisted` check (was inside the regime block, now standalone)
- WR gate: `if wr < 50 and wr_count >= 3` — correct, uses real trade history
- Loss cooldown check
- Price sanity, already-open, guardian closing race guard
- Surfing gate (survival_rounds)
- OC signal block

## Key Files

| File | Line | What |
|------|------|------|
| decider_run.py | 1689–1701 | Counter-trend trap guard (commented out) |
| decider_run.py | 1703–1751 | Full regime filter block (commented out) |
| decider_run.py | 1799 | WR gate: `wr < 50 and wr_count >= 3` |
| signal_compactor.py | 635 | regime used in compaction (still uses 5m) |

## Historical PostgreSQL WR Data (as of 2026-05-11)

Tokens in hot-set with WR from PostgreSQL `brain.trades` (7-day window):

| Token | WR% | Trades | Status |
|-------|-----|--------|--------|
| AVAX | **0%** | 3 | WR-blocked |
| AVNT | **33%** | 3 | WR-blocked |
| FET | **43%** | 7 | WR-blocked |
| BERA | fallback | 0 | WR gate passes (count=0) |
| CAKE | fallback | 0 | WR gate passes |
| ADA | **33%** | 3 | WR-blocked (but 0 in PostgreSQL) |
| BSV | **33%** | 3 | WR-blocked |
| BRETT | **46%** | 13 | borderline — passes with 50% fallback |
| CHIP | fallback | 0 | WR gate passes |
| EIGEN | **33%** | 3 | WR-blocked |

Note: PostgreSQL connection failing means `_get_direction_wr` returns `(50.0, 0)` for tokens with no history. The 0-count bypass means new tokens can enter. But stale WR data for AVAX/AVNT/FET is real and correct — those directions are genuinely poor.

## Diagnostic Commands

```bash
# Check PostgreSQL WR for hot-set tokens
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, direction, COUNT(*) as total, SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins \
   FROM trades WHERE close_time > NOW() - INTERVAL '7 days' \
   AND token IN ('AVAX','AVNT','FET','BRETT','CAKE','ADA','BSV','BERA','CHIP','EIGEN') \
   GROUP BY token, direction ORDER BY token, direction;"

# Check decider_run execution for all signals
journalctl --since "5 minutes ago" --no-pager | grep "\[DECIDER-LOOP\]"

# Check WR gate SKIPs
journalctl --since "10 minutes ago" --no-pager | grep "WR=.*direction paused"
```

## Related

- `references/hotset-approved-disconnect-2026-05-11.md` — hot-set vs APPROVED divergence
- `references/pipeline-timing-2026-05-06.md` — signals_runner background fork architecture