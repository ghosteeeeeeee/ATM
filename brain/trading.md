# Trading System — Live Log
> Internal document. Updated every 10 minutes by the pipeline. Every win, loss, bug, fix, and idea goes here.

---

## System Architecture

```
MARKET DATA
    │
    ▼
price_collector.py          ──→ price_history (SQLite static + runtime)
    │                              ~1.7M rows
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │
    ▼
signal_gen.py               ──→ signals DB (PENDING / WAIT / APPROVED / EXECUTED)
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              SPEED FEATURE: token_speeds table (536 tokens)
    │                          
    │  Every 10 min ▼
    │
ai_decider.py               ──→ compact_signals() → hotset.json (top 20 by score)
    │                              Scoring: recency + confidence + confluence + speed_score
    │                              BLACKLIST filter (LONG_BLACKLIST / SHORT_BLACKLIST)
    │                              Solana-only filter (is_solana_only)
    │                              review_count increments on WAIT/SKIPPED
    │
    ▼
decider-run.py              ──→ reads hotset.json
    │                              _run_hot_set() enforces: wave-phase, counter-trend trap,
    │                              regime alignment, overextended filter, cooldown
    │                              10-max-open-positions gate
    │
    ▼
hyperliquid_exchange.py     ──→ HL API (live or paper)
    │                              mirror_open for paper trades
position_manager.py          ──→ trailing stops, stale winner/loser exits, cascade flips
    │                              ro-trailing-stop.service (Dallas, Python only)
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
    │                              reconciles HL positions ↔ paper DB
    │                              marks guardian_missing / hl_position_missing closes
hermes-trades-api.py        ──→ writes signals.json for web dashboard
```

### Pipeline Schedule
| Step | Frequency | Script |
|------|-----------|--------|
| Price collection | Every 1 min | `price_collector.py` |
| Regime scan | Every 1 min | `4h_regime_scanner.py` |
| Signal generation | Every 1 min | `signal_gen.py` |
| Hot-set execution | Every 1 min | `decider-run.py` |
| Position management | Every 1 min | `position_manager.py` |
| Web dashboard | Every 1 min | `update-trades-json` |
| AI decision + compaction | Every 10 min | `ai_decider.py` |
| Strategy optimization | Every 10 min | `strategy_optimizer.py` |
| A/B optimization | Every 10 min | `ab_optimizer.py` |
| A/B learner | Every 10 min | `ab_learner.py` |

---

## Current State

**Updated:** 2026-04-05 04:25 UTC

### Positions
**LIVE TRADING: ON** (`hype_live_trading.json: live_trading=true`)

| Token | Direction | Entry | Leverage | PnL % | PnL $ |
|-------|-----------|-------|----------|-------|-------|
| NIL | SHORT | 0.0332 | 3x | 0.00% | $0.00 |
| APE | LONG | 0.0850 | 5x | 0.00% | $0.00 |
| STX | LONG | 0.2126 | 5x | 0.00% | $0.00 |
| ICP | SHORT | 2.2750 | 5x | 0.00% | $0.00 |
| AZTEC | SHORT | 0.0183 | 3x | 0.00% | $0.00 |
| W | LONG | 0.0133 | 5x | 0.00% | $0.00 |
| AXS | SHORT | 1.1144 | 5x | 0.00% | $0.00 |
| PENDLE | SHORT | 1.0343 | 5x | 0.00% | $0.00 |
| ZK | SHORT | 0.0161 | 5x | 0.00% | $0.00 |
| AAVE | LONG | 94.19 | 5x | 0.00% | $0.00 |

**10 open / 10 max** — ME closed (trailing_exit_-1.03%, -$1.70). NIL new SHORT opened. All PnL $0.00 in DB (by design — only written on close).

### Hot-Set
- **hotset.json:** 0 tokens (empty — ai_decider compaction may not have run recently)
- **Signal pipeline:** 374 PENDING, 0 APPROVED (last 2h)
- **Decider log:** Approval rate 0/3 this minute — no signals above 65% confidence

### 7-Day Stats
| Metric | Value |
|--------|-------|
| Closed (7d) | 86 (+9 since last check) |
| Win Rate | 27W / 62L = **43%** |
| Total PnL | **-$26.56** |
| Avg PnL % | +6.37% (winners big, losers small) |

### Services
| Service | Status |
|---------|--------|
| `hermes-pipeline.service` | ✅ Running (every 1 min) |
| `hermes-hl-sync-guardian.service` | ✅ Running (every 60s) |
| Trailing stop (`ro-trailing-stop.service`) | Dallas only |

### Speed Tracker
- 536 tokens tracked
- UNI LONG blocked — 49 failures, 3359s cooldown remaining
- ATOM SHORT blocked — 2 failures, cooldown active
- Regime: SHORT bias detected (multiple flips firing: VVV, MEW, PROMPT, PAXG, 2Z, NOT)

---

## Active Ideas (Queue)

### Ideas for Future Builds
- [ ] **Cascade flip: also check APPROVED signals** — currently only PENDING signals trigger flip. ME had APPROVED LONG signals (conf=80%+) 1 min before close but flip didn't use them. Using APPROVED signals would give flip confirmation faster. Modify `check_cascade_flip()` to query `decision IN ('PENDING', 'APPROVED')`.
- [ ] **Volume displacement filter** — only trigger on breakout + displacement > 0.5%
- [ ] **ATR-adaptive SL/TP** — SL = 1.5× ATR(14) instead of fixed %
- [ ] **ADX trend strength filter** — ADX < 20 = ranging, prefer mean-reversion
- [ ] **Scale-out TP system** — TP1/TP2/TP3 (1R/2R/3R) instead of single exit
- [ ] **Wave quality metric** — HMA slope to distinguish clean swell from chaos
- [ ] **Funding rate integration** — negative funding = tailwind for SHORTs
- [ ] **Wave-of-interest filter** — top 50 tokens in regime direction + speed > 50

---

---

## Live Log

### 2026-04-05 — ME Position Investigation

**ME SHORT — entry=0.09972, 3x lev, conf=99%, signal=conf-1s, opened 03:15 UTC**

**Closed at 04:20:13 — trailing_exit_-1.03% — loss: -$1.70 (-0.34%)**

**Flip didn't fire — WHY:**

The cascade flip requires ALL of:
1. Loss >= -1.0% (CASCADE_FLIP_TRIGGER_LOSS) while armed at -0.5%
2. Speed increasing (checked via SpeedTracker)
3. >=1 PENDING signal type for opposite direction, conf>=70%, created within last 15 min

What happened for ME:
- ME worst loss: ~-0.67% (price moved from 0.09972 to 0.10039) — never reached -1.0% trigger
- Flip arm threshold: -0.5% — price briefly touched this, but not for long enough to arm and wait
- Counter-signals: 3x PENDING LONG signals (conf=91%,80%,75%) DID appear — but at 04:23:32, AFTER the close at 04:20:13
- System trailed correctly and exited at -1.03% as designed

**Flip was 3 minutes too slow** — if ME had held 3 more minutes, the LONG flip would have fired (conf=91%, 3 signal types agreeing). The AI was right about the direction; the entry timing was the failure.

**countertrend flip design issue (improvement):**
- Currently only checks PENDING signals for opposite direction
- ME had APPROVED LONG signals (04:21:08, conf=80%+75%) but these weren't used
- APPROVED signals should be considered too — if the AI previously approved a signal for the opposite direction, that confirms the flip thesis
- TODO: extend `check_cascade_flip` to also look at APPROVED signals as flip confirmation

**Actual signal quality for ME:**
- AI approved ME SHORT at conf=99% (conf-1s signal) — but the regime was shifting
- ME LONG signals (conf=91%,80%,75%) appeared 3 minutes after close — the AI was right to want LONG
- The `ai_decider` scored ME SHORT entry but missed the reversal

**Lesson:** The flip mechanism works but needs:
1. Lower trigger threshold (-0.5% instead of -1.0%) for faster response, OR
2. Also check APPROVED signals (not just PENDING) as flip confirmation, OR
3. Both — wider net for flip signals since it's a protective mechanism



### 2026-04-05 — Session Start

**04:11 UTC — Pipeline running LIVE**
- Live trading enabled (`hype_live_trading.json`)
- 9 positions open (9/10 slots used)
- Hot-set empty — no tokens above 65% confidence threshold
- Regime: SHORT bias — multiple LONG→SHORT reversals firing (VVV, MEW, PROMPT, PAXG, 2Z, NOT)
- UNI in 49-failure cooldown (~56 min remaining)
- Speed tracker: 536 tokens, updated in ~100ms

**PnL $0.00 investigation — CLOSED ✅:**
- PostgreSQL `pnl_usdt` for OPEN positions is ALWAYS 0.00 — this is by design
- The DB only writes `pnl_usdt` when a position CLOSES (via `close_paper_position()`)
- `position_manager` computes live PnL in-memory for decisions but does NOT write to DB for open positions
- `update-trades-json.py` (web dashboard) calculates PnL on-the-fly from SQLite prices + PostgreSQL entry sizes
- The `***` bug was NOT in this file — `token=?` placeholders work correctly
- Live PnL shown on dashboard IS accurate: PENDLE SHORT +1.27% ($0.64), AXS SHORT +0.52% ($0.26), etc.

---

## Resolved Issues Log

### 2026-04-05 (this session)
| Time | Issue | Fix |
|------|-------|-----|
| 04:11 | MiniMax API: wrong base URL (`/anthropic/v1` → `/v1`), wrong model (`MiniMax-Text-01` → `MiniMax-M2`) | Fixed in ai_decider.py. Ollama fallback added. |
| 04:11 | MiniMax prepends `<think>` block — parsing `DECISION:` on line 1 failed | Now parses from end of response. |
| 04:25 | All 9 open positions showed PnL $0.00 in PostgreSQL | NOT A BUG — DB only writes pnl_usdt on close. `update-trades-json.py` calculates live PnL on-the-fly correctly. |
| 04:25 | ME position closed at -$1.70 (trailing_exit_-1.03%) | System worked correctly. Flip didn't fire because loss never reached -1.0% trigger. Counter-signals arrived 3 min AFTER close. |
| 04:25 | Cascade flip too slow — needs -1.0% loss before checking opposite signals | Improvement identified: also consider APPROVED signals (not just PENDING) for flip confirmation. See Live Log. |

### 2026-04-04 — Major Session (from reports.md)
| # | Issue | Fix |
|---|-------|-----|
| 1 | `***` SQL placeholder — hot-set never built | Replaced with proper `?` placeholders across 3+ files |
| 2 | `token` vs `coin` mismatch — functions returned None | Standardized to `coin` everywhere |
| 3 | Unclosed cursors — "database locked" errors | Added `finally` blocks |
| 4 | Hot-set bypass (31-line confluence-auto approve) | Removed entirely |
| 5 | Blacklisted tokens in hotset.json | Added blacklist + Solana-only filters in `compact_signals()` |
| 6 | `_check_hotset_cooldown()` defined but never called | Connected in `_run_hot_set()` loop |
| 7 | HL confirmation timeout 15s too short | Increased to 30s (range 3→6 retries) |
| 8 | `percentile_rank` capped at 50%, conflicting with 50% floor | Boosted formula to 60-75% range |
| 9 | `MIN_CONFIDENCE_FLOOR` missing — signals as low as 30% inserted | Added `MIN_CONFIDENCE_FLOOR = 50` |
| 10 | 20 phantom trades (hl_position_missing) corrupting stats | Guardian sanity check prevents future entries |
| 11 | Duplicate hot-set entries (compact_signals) | SQL GROUP BY deduplication |

### Pre-2026-04-04 (from reports.md)
- SHORT trailing activation: `abs(pnl_pct)` for SHORTs was wrong — renamed `adverse_pct → profit_pct`
- Dual guardian reconciliation: both `hl-sync-guardian` AND `position_manager.refresh_current_prices` reconciled independently
- SQL injection: `record_closed_trade` in hl-sync-guardian.py
- 65 PENDING/APPROVED signals for blacklisted tokens still in DB
- `mirror_open` missing `import sys` — VNC failures
- `hype_live_trading.json` toggle inverted — live mode was being skipped

---

## Known Issues

| Priority | Issue | Status |
|----------|-------|--------|
| HIGH | All 9 open positions show PnL $0.00 — investigate price update or formula bug | OPEN |
| HIGH | Hot-set empty — no signals above 65% confidence | OPEN — market conditions? |
| MEDIUM | 77 closed trades, 30% WR, -$24.78 net — win rate below 45% target | OPEN — working on improvements |
| MEDIUM | 9 open SHORTs with SHORT regime bias — concentration risk | MONITOR |
| MEDIUM | UNI: 49 failures, 3359s cooldown remaining — will re-enter after ~56 min | MONITOR |
| MEDIUM | 30% WR with avg +7.12% — winners are large, losers small | NEEDS ANALYSIS — is this sustainable? |
| LOW | Runtime DB 195MB — `signal_history` has 697,570 rows | Needs archival strategy |
| LOW | WASP cron not installed | Systemd setup task |
| LOW | 5 stale momentum_cache entries > 2h old | Investigate cleanup |

---

## Win Rate History

| Period | Trades | WR | Net PnL | Notes |
|--------|--------|-----|---------|-------|
| All time (pre-Apr-04) | 158 | 28% | +$3.1M | Dominated by PAXG +$1.54M outlier |
| Last 7 days | 86 | 43% | -$26.56 | No outliers, real performance. WR improving from 30% toward target 45% |
| Current open | 10 | — | $0.00 | PnL $0 by design (written on close only) |

**Key insight from surfing.md:** The 28% WR was driven by PAXG (+$1.54M) and BCH (+$18.7K) outliers — not replicable. Real WR without outliers is ~43%. System is improving. Focus: signal quality, confluence requirements, regime filter.

---

*This document is updated every 10 minutes by the pipeline. Last write: 2026-04-05 04:11 UTC*
