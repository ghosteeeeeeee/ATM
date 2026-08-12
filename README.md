# ATM — AI Trading Machine

> **Hyperliquid momentum-based algorithmic trading system**
> 544 tokens monitored · 55+ signal types · Paper & live modes · Kill switch safety

[![Pipeline Architecture](docs/pipeline-diagram.png)](docs/pipeline-diagram.png)

---

## Live Dashboard

[![Trades Dashboard](docs/trades_dashboard.png)](docs/trades_dashboard.png)

[![Coin Tracker](docs/coin_tracker.png)](docs/coin_tracker.png)

---

## System Overview

ATM is an event-driven trading system that continuously monitors cryptocurrency markets, identifies momentum-based trading opportunities using technical indicators (RSI, MACD, z-score velocity, percentile rank), and executes trades on Hyperliquid exchange.

---

## Full Pipeline (7 Phases)

```mermaid
flowchart TD
    subgraph PHASE0["PHASE 0: MARKET DATA (1 min timer)"]
        HL[HL allMids API<br/>542 tokens] --> HC[hype_cache.py<br/>hl_cache.json]
        HC --> SQLite[(SQLite<br/>price_history<br/>latest_prices)]
        SQLite --> Candles[(candles.db<br/>1m/5m/15m/1h/4h)]
    end

    subgraph PHASE1["PHASE 1: SIGNAL GENERATION (1 min)"]
        Candles --> SR[signals_runner.py<br/>55+ signal scripts]
        SR --> SigDB[(signals_hermes_runtime.db<br/>decision=PENDING)]
    end

    subgraph PHASE2["PHASE 2: SIGNAL COMPACTION"]
        SigDB --> SC[signal_compactor.py]
        SC --> |"1. Expire stale (>10m)"| SC
        SC --> |"2. Group by combo_key"| SC
        SC --> |"3. Pre-filter"| SC
        SC --> |"4. Score + rank top 10"| SC
        SC --> |"5. Safety filters"| SC
        SC --> HS[(hotset.json<br/>top 10 APPROVED)]
    end

    subgraph PHASE2_5["PHASE 2.5: SIGNAL ANALYST"]
        HS --> SA[signal_analyst.py<br/>Quality 0-100]
        SA --> |"Score >= 60"| HS2[(hotset.json<br/>adjusted confidence)]
    end

    subgraph PHASE3["PHASE 3: TRADE DECISION"]
        HS2 --> DR[decider_run.py]
        DR --> |"Eligibility checks"| DR
        DR --> |"Signal inversion"| DR
        DR --> |"Z-score freshness"| DR

        DR --> CG

        subgraph CONTEXT_GATE["CONTEXT GATE (5 layers)"]
            L1["L1: Rule-based gate<br/>Speed, momentum, RSI, z-score"]
            L2["L2: Similar setup lookup<br/>PostgreSQL historical WR"]
            L3["L3: Token sentiment<br/>Hebbian Phase 3a"]
            L4["L4: Hebbian gate<br/>Token-signal WR weights"]
            L5["L5: LLM gate<br/>MiniMax-M3<br/>(GO/WARN/NAY)"]

            L1 --> L2 --> L3 --> L4 --> L5
        end

        CG{Context Gate}
        CG -->|PASS| EX[execute_trade]
        CG -->|SKIP/WARN| SKIP[Signal skipped]

        EX --> |"Atomic signal claim"| BRAIN[brain.py]
        BRAIN --> HL_API[HL API<br/>mirror_open]
    end

    subgraph PHASE4["PHASE 4: POSITION MANAGEMENT (1 min)"]
        HL_API --> PM[position_manager.py]
        PM --> ATR[tpsl_utils.py<br/>ATR SL/TP compute]
        ATR --> |"ATR SL hit"| CLOSE_SL[Close via HL]
        ATR --> |"ATR TP hit"| CLOSE_TP[Close via HL]
        ATR --> |"Trailing stop<br/>activate +0.30%<br/>trail 0.30%"| ATR
        PM --> |"Stale winner (>0.6%, 60m+)"| CLOSE_STALE[Close]
        PM --> |"Stale loser (<-0.6%, 8m+)"| CUT_STALE[Cut]
    end

    subgraph PHASE5["PHASE 5: PROFIT MONSTER (timer)"]
        PMPositions[Open positions] --> PM2[profit_monster.py]
        PM2 --> T1["TIER 1: Quick Scalp<br/>0.5-2.0% profit<br/>max 2/wake"]
        PM2 --> T2["TIER 2: Runner<br/>2.0-5.0% profit<br/>max 1/wake"]
        T1 --> CLOSE_PM[Close via HL]
        T2 --> CLOSE_PM
        PM2 --> |"Trailing: +0.40% act<br/>0.25% trail"| PM2
    end

    subgraph PHASE6["PHASE 6: CUT LOSER (timer)"]
        PMPositions --> CL[cut_loser.py]
        CL --> CT1["TIER 1: Quick Cut<br/>-0.75% to -1.0%"]
        CL --> CT2["TIER 2: Deep Cut<br/>-1.0% to -3.0%"]
        CT1 --> CUT[Cut via HL]
        CT2 --> CUT
        CL --> |"Trailing loss:<br/>track worst, cut on<br/>recovery fail"| CL
    end

    subgraph PHASE7["PHASE 7: GUARDIAN (60s timer)"]
        HL_ACTUAL[HL Actual Positions] --> GUARD[hl-sync-guardian.py]
        GUARD --> |"Orphan detection"| GUARD
        GUARD --> |"HL sync reconcile"| GUARD
        GUARD --> |"Loss cooldowns"| GUARD
        GUARD --> |"Self-close orphans"| GUARD_CLOSE[Close via HL]
    end

    style PHASE0 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE1 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE2 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE2_5 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE3 fill:#1a1a2e,stroke:#16213e,color:#fff
    style CONTEXT_GATE fill:#0f3460,stroke:#533483,color:#fff
    style PHASE4 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE5 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE6 fill:#1a1a2e,stroke:#16213e,color:#fff
    style PHASE7 fill:#1a1a2e,stroke:#16213e,color:#fff
    style CG fill:#e94560,stroke:#533483,color:#fff
    style SKIP fill:#666,stroke:#333,color:#fff
```

> **Full text diagram:** [docs/pipeline-diagram.md](docs/pipeline-diagram.md)

---

## Architecture at a Glance

| Phase | Script | What it does | Frequency |
|-------|--------|--------------|-----------|
| **0. Data** | `price_collector.py` | Fetch 542 token prices from HL API | 1 min |
| **1. Signals** | `signals_runner.py` | Run 55+ signal scripts (RSI, MACD, etc) | 1 min |
| **2. Compact** | `signal_compactor.py` | Score, rank, dedupe → top 10 | 1 min |
| **2.5. Analyst** | `signal_analyst.py` | Quality score 0-100 | 1 min |
| **3. Decide** | `decider_run.py` | Context Gate (5 layers) → execute | 1 min |
| **4. Manage** | `position_manager.py` | ATR SL/TP, trailing stops | 1 min |
| **5. Profit** | `profit_monster.py` | Tier 1 (scalp) + Tier 2 (runner) | 1-10 min |
| **6. Cut** | `cut_loser.py` | Quick cut + deep cut | frequent |
| **7. Guardian** | `hl-sync-guardian.py` | Kill switch, HL reconciliation | 60s |

---

## Context Gate (5 Layers)

The Context Gate is the brain of the system — a 5-layer funnel that decides which signals become trades:

```
Layer 1: RULE-BASED GATE
  ├─ Speed < 20% = AMBIGUOUS
  ├─ Global filters: speed, momentum, RSI, z-score
  ├─ Strong setup (speed≥70% + z confirms) = GO (skip LLM)
  └─ Counter-trend trap detection

Layer 2: SIMILAR SETUP LOOKUP
  └─ PostgreSQL: past trades with same conditions
     WR < 30% with n>=5 = SKIP

Layer 3: TOKEN SENTIMENT
  └─ sentiment <= -0.7 = SKIP

Layer 4: HEBBIAN GATE
  ├─ Auto-approve: score >= 0.65 (WR>=60%, n>=3)
  └─ Auto-reject: score <= 0.35 (WR<=30%, n>=5)

Layer 5: LLM CONTEXT GATE (MiniMax-M3)
  └─ GO / WARN (penalty) / NAY (block)
```

---

## Kill Switch

| Mode | Behavior |
|------|----------|
| `live_trading: false` | All trades stay in paper DB (simulation only) |
| `live_trading: true` | Guardian mirrors approved trades to real HL orders |

**Guardian reconciliation** (every 60s): reads kill switch → mirrors paper positions to HL → reconciles HL ↔ paper DB → marks orphan closes.

---

## Quick Start

### Prerequisites

```bash
# System deps
apt install python3-pip sqlite3

# Python deps
pip install requests sqlite3 openai

# OpenCode (for AI-powered development)
# See: https://opencode.ai
```

### Setup

```bash
# Clone the repo
git clone https://github.com/ghosteeeeeeee/ATM.git
cd ATM

# 1. Install deps
pip install -r requirements.txt

# 2. Init DBs (auto-loads backfill from seed/)
python3 scripts/signal_schema.py

# 3. Run the pipeline
python3 scripts/price_collector.py
python3 scripts/signal_gen.py
python3 scripts/ai_decider.py
python3 scripts/decider_run.py

# 4. Start the web dashboard
python3 scripts/hermes-trades-api.py  # Runs on :8080

# 5. View trades dashboard
# Open http://localhost:12345/trades.html in browser
# Or: http://localhost:8080/trades.html
```

### Dashboard Pages

| Page | URL | Description |
|------|-----|-------------|
| `trades.html` | `:12345/trades.html` | Main trading dashboard |
| `signals.html` | `:12345/signals.html` | Live signal feed |
| `coin_tracker.html` | `:12345/coin_tracker.html` | Per-coin intelligence |

---

## Data Stores

| Store | Contents |
|-------|----------|
| `signals_hermes.db` | price_history (~2.7M rows), latest_prices, regime_log |
| `signals_hermes_runtime.db` | signals table, token_speeds (544 tokens) |
| `state.db` | General state (messages, schema_version) |
| `predictions.db` | ML predictions |
| `hype_live_trading.json` | **KILL SWITCH** — live_trading flag |
| `hotset.json` | Current hot set (top 10 signals) |

---

## Configuration

- `config/` — tokens, thresholds, regime parameters
- `.env` — API keys (not committed)
- `cron/jobs.json` — cron schedule
- `hermes_constants.py` — all system constants

---

**Last updated:** 2026-08-12
