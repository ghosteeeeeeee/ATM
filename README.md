# ATM — AI Trading Machine

> **Hyperliquid momentum-based algorithmic trading system**
> 544 tokens monitored · 55+ signal types · Paper & live modes · Kill switch safety

---

## Live Dashboard

[![Trades Dashboard](docs/trades_dashboard.png)](docs/trades_dashboard.png)

[![Coin Tracker](docs/coin_tracker.png)](docs/coin_tracker.png)

---

## System Overview

ATM is an event-driven trading system that continuously monitors cryptocurrency markets, identifies momentum-based trading opportunities using technical indicators (RSI, MACD, z-score velocity, percentile rank), and executes trades on Hyperliquid exchange.

---

## Full Pipeline

```mermaid
flowchart LR
    classDef data fill:#1f6feb,stroke:#58a6ff,color:#fff
    classDef db fill:#a371f7,stroke:#d2a8ff,color:#fff
    classDef proc fill:#21262d,stroke:#8b949e,color:#c9d1d9
    classDef gate fill:#da3633,stroke:#f85149,color:#fff,stroke-width:2px
    classDef exit fill:#238636,stroke:#3fb950,color:#fff
    classDef skip fill:#30363d,stroke:#484f58,color:#8b949e
    classDef signal fill:#1c2333,stroke:#58a6ff,color:#79c0ff
    classDef layer fill:#1c1c2e,stroke:#8b949e,color:#c9d1d9

    subgraph INGEST["  INGEST  "]
        direction TB
        HL["<b>HL allMids</b><br/>542 token prices"]:::data
        CACHE["<b>hype_cache</b><br/>hl_cache.json"]:::proc
        DB1[(<b>candles.db</b><br/>1m 5m 15m 1h 4h)]:::db
        HL --> CACHE --> DB1
    end

    subgraph SIGNALS["  SIGNALS  "]
        direction TB
        SIG["<b>signals_runner</b><br/>55+ scripts"]:::proc
        S1["<b>macd_accel</b><br/>per-token 1m MACD"]:::signal
        S2["<b>hh_hl_choch</b><br/>HH/HL + Change of Character"]:::signal
        S3["<b>hzscore</b><br/>multi-TF z-score"]:::signal
        S4["<b>bb_bounce</b><br/>Bollinger Band"]:::signal
        S5["<b>momentum</b><br/>pct-hermes + accel"]:::signal
        SIGDB[(<b>signals DB</b><br/>decision=PENDING)]:::db
        SIG --> S1
        S1 --> S2 --> S3 --> S4 --> S5 --> SIGDB
    end

    subgraph FILTER["  FILTER  "]
        direction TB
        COMPACT["<b>signal_compactor</b><br/>expire · group · blacklist<br/>score · rank top 10"]:::proc
        ANALYST["<b>signal_analyst</b><br/>trend 0-30 · RSI 0-20<br/>WR 0-25 · time 0-10<br/>blacklist 0-15 · pass ≥60"]:::proc
        HS[(<b>hotset.json</b><br/>top 10 APPROVED)]:::db
        COMPACT --> ANALYST --> HS
    end

    subgraph DECIDE["  DECIDE  "]
        direction TB
        DECIDER["<b>decider_run</b><br/>eligibility · inversion<br/>z-score freshness"]:::proc
        L1["<b>L1 Rule-based</b><br/>speed · momentum · RSI"]:::layer
        L2["<b>L2 Similar setup</b><br/>hist WR <30% = SKIP"]:::layer
        L3["<b>L3 Token sentiment</b><br/>≤ -0.7 = SKIP"]:::layer
        L4["<b>L4 Hebbian gate</b><br/>score ≥0.65 = approve"]:::layer
        L5["<b>L5 LLM gate</b><br/>MiniMax-M3"]:::layer
        GATE{"<b>GO?</b>"}:::gate
        BRAIN["<b>brain.py</b><br/>atomic claim · HL API"]:::exit
        SKIP["SKIP"]:::skip
        DECIDER --> L1 --> L2 --> L3 --> L4 --> L5 --> GATE
        GATE -->|"PASS"| BRAIN
        GATE -->|"NAY"| SKIP
    end

    subgraph EXIT["  EXIT  "]
        direction TB
        PM["<b>position_manager</b><br/>ATR SL/TP + trailing"]:::proc
        PMDETAIL["ATR(14) tiers<br/>LOW=0.8 · NORMAL=1.0 · HIGH=0.25<br/>Trailing: +0.30% act, 0.30% trail<br/>Stale: winner ≥60m / loser ≥8m"]:::layer
        PROFIT["<b>profit_monster</b><br/>T1: 0.5-2% max 2/wake<br/>T2: 2-5% max 1/wake<br/>Trail: +0.40% act, 0.25%"]:::exit
        CUT["<b>cut_loser</b><br/>T1: -0.75% quick cut<br/>T2: -3% deep cut<br/>Trailing loss recovery"]:::exit
        GUARD["<b>guardian</b><br/>orphan detect · HL sync<br/>loss cooldowns"]:::proc
        CLOSE["<b>CLOSE</b><br/>HL market order"]:::exit
        PM --> PMDETAIL --> PROFIT --> CUT --> GUARD --> CLOSE
    end

    DB1 --> SIG
    SIGDB --> COMPACT
    HS --> DECIDER
    BRAIN --> PM
    BRAIN -.-> PROFIT
    BRAIN -.-> CUT
    BRAIN -.-> GUARD

    style INGEST fill:#0d1117,stroke:#1f6feb,stroke-width:2px,color:#58a6ff
    style SIGNALS fill:#0d1117,stroke:#a371f7,stroke-width:2px,color:#d2a8ff
    style FILTER fill:#0d1117,stroke:#8b949e,stroke-width:2px,color:#8b949e
    style DECIDE fill:#0d1117,stroke:#da3633,stroke-width:2px,color:#f85149
    style EXIT fill:#0d1117,stroke:#238636,stroke-width:2px,color:#3fb950
```

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
