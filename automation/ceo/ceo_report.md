## CEO Report — 2026-10-04 MoE Panel Decisions

### Verified Numbers (PG `brain`, status='closed', run this session)
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 30d | 966 | **-$2.22** | 51.4% |
| 7d | 200 | +$1.95 | 52.0% |
| 24h | 34 | +$1.15 | 58.8% |
| LONG 30d | 598 | **+$1.90** | 52.5% |
| SHORT 30d | 368 | **-$4.12** | 49.7% |

**SHORT RSI bands 30d (entry_rsi_14):** RSI<40 **86T -$5.04 32.6%WR** | RSI>=40 70T -$0.60 51.4% | NULL 212T +$1.52 56.1%
**SHORT regime x RSI 30d:** EXTREME RSI>=40 **40T +$0.98 62.5%WR** (only positive SHORT cell) | EXTREME RSI<40 60T -$3.02 36.7% | NORMAL RSI>=40 9T -$0.87 22% | HIGH RSI>=40 20T -$0.73 40% | EXTREME SHORT all-band **-$0.91** (MoE "+$4.71 EXTREME" is all-directions; LONG EXTREME is +$5.38)
**Exits 30d:** profit-monster* **307T +$18.83 82.1%** (only big winner) | cut-loser* 91T -$12.64 | atr_sl* 367T -$5.42 | hard_max_loss* 33T -$4.35 | hard_sl 46T -$3.24 | rr_engine* 59T -$1.38
**Regimes 30d:** EXTREME +$4.47 | FLAT +$0.66 | NULL +$0.08 | HIGH -$2.94 | NORMAL -$4.49
**Flags verified:** STANDALONE_BYPASS 123 entries / 115 unique | RR_ENGINE_SHADOW=True FORCE=False | CONFLUENCE_REQUIRED=True | SHORT_RSI_FLOOR=40 HARD_FLOOR=25 CEILING=65 HARD_CEILING=75
**Post-fix (Oct 3):** SHORT entry_rsi_14<40 only pump-chain- 5T **+$0.05** — exec-RSI floor (bf96d7cd) live today; 30d -$5.04 is pre-fix history. **Caveat:** entry_rsi_14 is detection-time, not exec-time (DRIFT-002). Oct 3 SHORT still entered with stored RSI 13-42 — either drift or a bypass path. Audit required before claiming the leak is closed.
**15m scanner:** `scripts/15m_regime_scanner.py` is a **5m scanner** (CANDLE_TF=5m, candles_5m, Binance interval=5m), thresholds slope_pct>0.35 per 5m candle with n=16 — noisy, NEUTRAL-biased. Misnamed, not "4h thresholds" as MoE claimed. Still a real defect.
**Fees:** `fees` column is JSON text; samples show ~$0.005-0.02/trade. pnl_usdt vs fees.net_pnl inconsistent — accounting gap confirmed, not the primary bleed.
**System state:** bollinger window ENDED 21:55 UTC Oct 3; volume-breakout boost 1.15→1.25 already applied 22:11 by auto_1hr. Config changes allowed now.

---

### Decision 1 — SHORT Entry Model: **A (follow the data)**

**A — SHORT only where edge exists, not during falls.**

Precise model:
1. **Block all SHORT with execution-time RSI < 40** (all paths, no bear override, fail-closed on stale candles).
2. **Primary habitat: EXTREME vol + RSI>=40** — only positive SHORT cell (40T +$0.98 62.5%WR).
3. **NEUTRAL SHORT stays blocked** (SHORT_NEUTRAL_BLOCK already on).
4. **NORMAL/HIGH SHORT:** block unless RSI>=40 AND quality gates pass — those cells still bleed.

**Rejected B** (keep SHORTing dumps): oversold SHORT is the entire net loss (-$5.04 vs month -$2.22).
**Rejected C** as stated: "bottoms in other regimes" = RSI<40 = losing everywhere (32.6%WR). EXTREME oversold also loses (-$3.02). MoE's "wave bottoms 94%WR" **not reproducible in DB** — rejected.

**Philosophy amendment (Decision 4 = A):** "Every pump is a LONG opportunity. Every dump is a SHORT opportunity **only when not oversold (exec RSI>=40)** — we short structure after the move, not into the bottom. Every trade *targets* a winner via profit-monster-trail; losers are cut." Keeps both-directions spirit; conditions it on edge.

**Metric before → target:** SHORT 30d -$4.12/49.7% → SHORT 7d ≥ $0 / ≥52% by 2026-10-07. Expected: close remaining oversold paths → +$3-5/30d if leak fully closed.

---

### Decision 2 — Implementation Priority

| # | Action | Call | Reason |
|---|--------|------|--------|
| 1 | Close remaining exec-time RSI>=40 holes on ALL SHORT paths + audit bypass/fail-open | **FIRST** | Targets -$5.04 historical leak. Floor already live (bf96d7cd) but Oct 3 still shows stored RSI<40 entries — **audit, don't re-add filters**. Close: STANDALONE_BYPASS paths that skip decider_run, stale-candle fail-open, DRIFT-002 entry_rsi vs exec_rsi. |
| 2 | Fix 15m/5m regime scanner | **SECOND** | Confirmed 5m data + noisy 0.35%/candle thresholds, n=16. Retune for 5m or switch to true 15m. Regime detection quality gates every SHORT decision. |
| 3 | RR_ENGINE_SHADOW audit → then enable FORCE | **THIRD — audit first** | Do NOT blind-kill. Pull shadow-block would-have-blocked logs 7d: if would-blocks saved money without killing volume-breakout/doji winners, set FORCE=True. If thresholds would block winners, retune then enable. |
| 4 | Shrink STANDALONE_BYPASS 124→~6 | **SKIP as stated** | Confluence already expires 92.5%; shrink-to-6 freezes NEUTRAL. Instead: **incremental prune** — remove only losing signals from bypass (keep volume-breakout, doji, bb-bounce-v2, pump-chain+). |
| 5 | Gate SHORT to EXTREME vol | **DO — as RSI>=40 + EXTREME, not EXTREME-only** | EXTREME alone insufficient (oversold still -$3.02). Gate = RSI>=40 everywhere + EXTREME preferred + NORMAL/HIGH blocked unless quality. |

**Skip list:** blind RR_ENGINE force, bypass shrink-to-6, any protected-flag touch.

---

### Decision 3 — Trade Frequency: **B (fix the edge first), A as conditional follow-up**

- **B primary:** The -$5.04 oversold SHORT leak is larger than fee drag. Frequency without edge just loses slower.
- **A conditional:** After 48h post-fix SHORT data, if fee drag still dominates net (fees ~$10/30d vs PnL), raise entry bar (MIN_EXEC_CONFIDENCE, confluence quality) — cut low-quality trades, not winners.
- **Reject C (size up):** multiplies negative expectancy. Absolute PnL is tiny; sizing up a 51%WR / R:R 0.83 system is how accounts die.

**Metric:** trades/day 32 → 20-25 after quality bar IF fee/edge ratio still bad post-fix; otherwise keep frequency.

---

### Decision 4 — Philosophy: **A (modify to match reality)**

New standing philosophy:
> **Every pump is a LONG opportunity. Every dump is a SHORT opportunity — but only when entry conditions confirm edge (exec RSI>=40, regime habitat, quality gates). We do not short oversold bottoms. Every trade targets a winner via profit-monster-trail; cut losers fast.**

- **Reject B** ("keep philosophy, build systems to achieve it"): building systems to force "every dump = SHORT" means trading negative-expectancy cells = guaranteed bleed. The philosophy as absolute is what produced the -$5.04 leak.
- **A** keeps the spirit (both directions, never fade momentum into a known losing cell) and binds it to data.

AGENTS.md philosophy line will be updated to the conditioned form after T acknowledges — **not** a silent rewrite of trading doctrine.

---

### Diagnosis (MoE claims vs DB)
| MoE Claim | DB Verified | Verdict |
|-----------|-------------|---------|
| 30d -$1.90 to -$3.10, 960T, 51.9%WR | 966T **-$2.22**, 51.4% | ✓ |
| SHORT -$3.88 entire net loss | SHORT **-$4.12**, LONG +$1.90 | ✓ (SHORT worse) |
| SHORT RSI<40 n=86, 34%WR, -$5.04 | n=86, **32.6%WR, -$5.04** | ✓ exact |
| profit-monster-trail only profitable exit | +$18.83, 82.1% | ✓ |
| EXTREME only profitable regime +$4.71 | EXTREME +$4.47 all-dir; **SHORT EXTREME -$0.91** | ⚠ partial — EXTREME is LONG-driven |
| Wave bottoms 94%WR SHORT edge | RSI<40 = 32.6%WR | ✗ **rejected** |
| 15m scanner dead, 5m w/ 4h thresholds | 5m scanner, 0.35%/5m thresholds | ✓ defect, different root |
| RR_ENGINE_SHADOW logs never blocks | SHADOW=True FORCE=False | ✓ |
| STANDALONE_BYPASS 124 entries | 123 entries / 115 unique | ✓ |
| Fees gross, ~double the loss | fees JSON ~$0.01/trade; pnl vs net_pnl inconsistent | ⚠ accounting gap, not primary bleed |
| Exec-time RSI>=40 needed | Floor LIVE today (bf96d7cd); leak is pre-fix + possible drift/bypass | ✓ but **audit first** |

### Root Cause
The system's own philosophy forced SHORT entries into oversold cells where edge does not exist. Filters existed at detection but exec-time enforcement was incomplete until today; STANDALONE_BYPASS still lets some paths skip gates; regime detection (5m misnamed scanner) is noisy. LONG is already profitable. The fix is entry-model discipline, not more signals or more size.

### Fix Applied (this run)
- **0 trading config changes** — this run is decision + delegation only.
- Decisions written: SHORT model A, priority 1-5 with skip list, frequency B, philosophy A.
- Delegations queued (kanban).

### Verification / Next Run
1. bug_hunter: audit SHORT exec-RSI paths — bypass, fail-open on stale candles, DRIFT-002. Report which Oct 3 stored-RSI<40 trades bypassed the floor.
2. self_learner: after audit, confirm ZERO new SHORT entries with exec RSI<40 over 48h (query exec RSI, not entry_rsi_14).
3. signal_analyst: retune 15m/5m scanner thresholds; build EXTREME+RSI>=40 SHORT habitat params into signal_regime_memory.json.
4. bug_hunter: RR_ENGINE shadow-block would-have-blocked analysis 7d → recommend FORCE on/off with numbers.
5. Metric checkpoint 2026-10-07: SHORT 7d ≥ $0, oversold SHORT entries = 0.

Protected flags untouched: CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED, ROTATOR_PROTECTED_FLAGS, CEO_PROTECTED_FLAGS.

## CEO Report — 2026-10-04 01:55 UTC

### Diagnosis
PG-verified: 24h **33T +$0.84 57.6%** | 7d **201T +$2.00 52.2%** | 30d **959T -$1.72 51.7%** (improved +$0.50 from -$2.22). LONG 7d +$3.38/147T carries system. SHORT 7d **-$1.38/54T**, SHORT 30d **-$4.02/367T** — entire net loss. SHORT 30d by entry_rsi_14: RSI<25 = 24T -$2.86 8.3%WR (catastrophic), RSI>=50 = 34T +$0.17 55.9%, NULL = 211T +$1.62 56.4%. Regime 100% NEUTRAL. hard_max_loss family 48h ~18T ~-$3.11 dominant bleed. Daily trend improving: Sep 29 -$1.13 → Oct 2 +$0.73 → Oct 3 +$1.15. Open: 2 LONG (ENS -0.47%, CHIP -0.01%).

### Root Cause
SHORT bleed = oversold entries (RSI<40 = -$5.04 across 86T). IO pump-chain- SHORT at RSI=13.46 (Oct 3 21:17) bypassed floor via exec-RSI audit holes. bug_hunter landed **b960ffe8** 00:38 UTC: Hole 1 continuum_trader direct-HL orders skipped all RSI checks; Hole 2 decider_run swallowed exceptions (silent fail-open). Both fail-closed now. Pipeline restarted 01:50 — fix LIVE.

### Fix Applied
**0 trading config changes** (standing: floor live, SHORT model A, monitor windows, protected flags). **Verified b960ffe8 loaded** (pipeline restart 01:50). **Regime memory updated** (data/signal_regime_memory.json snapshot 01:55). **CURRENT.md refreshed** — removed stale accel_300_v3_long monitor (already ENABLED=False Oct 3). io bypass root-caused to pre-fix holes.

### Verification
- 0 oversold SHORT entries post b960ffe8 (1 SHORT since floor = IO pre-fix).
- Pipeline active, 01:50 start, continuum_trader 01:28 (post-fix).
- volume-breakout boost 1.25 live; 7d 5T +$1.85 80%WR; post-boost sample too small (1 closed, pre-boost open).
- Goals: SHORT 7d ≥$0 by Oct 7; oversold SHORT = 0 in 48h; 7d PnL +$2.00→+$3.00.
- Delegated: self_learner (48h oversold-SHORT verify), bug_hunter (RR_ENGINE shadow → FORCE), signal_analyst (scanner retune, ema_reclaim, coin_tracker).
