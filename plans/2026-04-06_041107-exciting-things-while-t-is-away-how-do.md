# Self-Initiative Mode — Exciting Things While T Is Away

## Goal

Autonomously detect when T has been away for >20 minutes and start working on projects from the PM system (PROJECTS.md, TASKS.md). Do useful research, analysis, building — without disrupting live trading. Keep working for 8+ hours if T is away. Become smarter, make the system smarter.

---

## Context / Assumptions

- T trades from Tokyo/Dallas with Hyperliquid (real money, 10-20X leverage)
- Pipeline runs every 10 minutes, guardian every 60 seconds
- PM files: PROJECTS.md, TASKS.md, DECISIONS.md, trading.md
- Current hot-set: 20 tokens, 10/10 positions typically full
- **Rate limit: 1500 prompts / 5 hours** — generous, can run background research freely
- Tokyo server (10.60.72.219) is ASLEEP — SQLite-only mode

**Core constraint:** Don't fire new live trades while T is away. Paper trading / signal development only.

---

## Core Rules (updated per T's feedback)

1. **Keep working if T is away 8+ hours** — he'll be back, don't stop
2. **Training is good** — become smarter, make the system smarter
3. **If urgent found — handle it smartly** — flag in trading.md, continue working
4. **If system jeopardized — pause** — stop self-init, alert T on return
5. **Don't break anything** — no changes to live trading flags, execution, leverage

---

## How It Works

### 1. Away Detection

Background cron job runs every 5 minutes:

```python
# ~/.hermes/scripts/away_detector.py
import json, os, time

AWAY_FILE = '/root/.hermes/data/last_user_message_at.json'
AWAY_THRESHOLD_MINUTES = 20

def is_t_away():
    if not os.path.exists(AWAY_FILE):
        return False
    with open(AWAY_FILE) as f:
        ts = json.load(f).get('timestamp', 0)
    return (time.time() - ts) > (AWAY_THRESHOLD_MINUTES * 60)
```

- `last_user_message_at.json` updated on every user message
- Cron: `*/5 * * * * /root/.hermes/scripts/away_detector.py >> /root/.hermes/logs/away_detector.log 2>&1`

### 2. Project Selection

Read PROJECTS.md and TASKS.md. Pick highest-priority item that:
- Has no blockers (not blocked on T)
- Is not already in progress
- Is "Agent-owned" or "TBD"

Priority order:
1. 🚧 IN PROGRESS items (continue them)
2. Queued items with "Agent" owner
3. Signal quality improvements, backtesting, analysis
4. System health checks (WASP-style)
5. ML/training work (fine-tune signal models, regime detection)

### 3. Work Mode

Run as a background subagent with a clear goal from the PM files.

**Allowed while T is away:**
- Research: signal DB patterns, WR by token/timeframe/regime, flooding analysis
- Backtesting: historical simulations
- Dashboards: new HTML/JS visualizations
- Pipeline improvements: non-trade-executing changes
- Signal quality: low-confidence signal analysis
- PM file maintenance: update progress, log decisions
- ML/training: fine-tune signal weighting, regime detection models, backtesting

**NOT allowed while T is away:**
- Fire new trades (live or paper)
- Change `_FLIP_SIGNALS`, `hype_live_trading.json`, leverage
- Touch max positions or live execution flags
- Anything that could break the live pipeline

**If system jeopardized:** Stop immediately, log what happened, flag for T review.

### 4. Reporting

Append to trading.md on every self-init run:

```
## SELF-INIT RUN — YYYY-MM-DD HH:MM UTC
Work done: [what was accomplished]
Findings: [key discoveries]
PM files updated: [what changed]
Token budget used: [estimate]
Ready for T review: [items needing decision]
```

When T returns: brief summary at top of next response.

---

## Implementation Steps

### Phase 1: Detection (implement now)
### Phase 1: Detection ✅ IMPLEMENTED
- [x] `last_user_message_at.json` — seeded with current timestamp
- [x] `away_detector.py` — detects away state, checks pipeline health, picks task
- [x] Cron: `*/5 * * * * /usr/bin/python3 /root/.hermes/scripts/away_detector.py`
- [x] Log: `/root/.hermes/logs/away_detector.log`

### Phase 2: Self-Initiative Trigger ✅ IMPLEMENTED
- [x] `away_detector.py` checks PM files when T is away
- [x] Debounce: don't re-run if last run < 2h ago
- [x] Task selection from TASKS.md (agent-owned, unblocked, highest priority)
4. Track last self-init run timestamp

### Phase 3: Smarter Selection (future)

1. Track what was already worked on (don't repeat failed approaches)
2. Score tasks by: urgency × effort × expected impact × "excitement factor"
3. Auto-detect when T is away for 8+ hours → switch to marathon mode (no 3-run cap)

### Phase 4: Return Detection + Smart Urgency

1. On first message after absence, brief summary at top
2. If self-init found something urgent → include "⚠️ URGENT" flag at top of next response
3. "Urgent" = potential system break, data corruption, signal anomaly, WR collapse

---

## Files to Create / Change

| File | Action |
|------|--------|
| `data/last_user_message_at.json` | Create — tracks last message timestamp |
| `scripts/away_detector.py` | Create — away detection + task spawning, single-instance lock |
| `logs/away_detector.lock` | Lock file — prevents concurrent runs |
| `brain/trading.md` | Append — self-init run reports |
| `brain/PROJECTS.md` | Update — if self-init made progress |
| `brain/DECISIONS.md` | Update — log findings/decided items |
| `SOUL.md` | Update — add self-initiative mode |
| Cron | Add `away_detector.py` every 5 min |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Token budget blowout | 1500/5h is generous — watch it, don't abuse |
| Interferes with live trading | Explicit: no trade execution changes allowed |
| T returns to confusing state | Clear logging in trading.md with SELF-INIT header |
| Self-init picks wrong task | Debounce + skip if system already healthy |
| System resource drain | Lightweight scripts only, no heavy training without T review |

---

## Why This Is Exciting

First self-init run priorities (highest impact, zero risk):

1. **Signal flooding analysis** — 282 low-confidence signals flagged. Why? Are they noise or hidden signal?
2. **WR by regime analysis** — Does SHORT regime actually produce SHORT wins?
3. **Hot-set quality audit** — Are top-20 tokens actually tradeable?
4. **Cascade flip effectiveness** — Are the new thresholds (ARM=-0.25%, TRIGGER=-0.50%) firing correctly?
5. **Dashboard upgrade** — Add live PnL, WR tracker, regime indicator to signals.html