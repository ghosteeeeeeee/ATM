# Plan: Make CONTEXT.md Work Per-Call

## Problem
During sessions, I drift off-topic or revisit resolved issues. CONTEXT.md exists but:
- It's 3 days stale (last updated April 5)
- I'm not using it as a per-turn anchor
- I don't have file paths embedded, so I go hunting for things we've already located
- No "current focus" section to keep me grounded mid-session

---

## Root Cause
1. CONTEXT.md written at session end only → goes stale fast
2. No per-turn reminder to read it
3. No "current focus" or "done/closed" sections
4. No file path anchors — I'm wasting time finding files we've already found

---

## Proposed Solution

### 1. Restructure CONTEXT.md — Two Zones

```
# CONTEXT.md — Hermes ATM

## File Anchors (permanent — never stale)
[/root/.hermes/brain/trading.md]     — live trading log, PnL, positions
[/root/.hermes/brain/TASKS.md]       — open todos
[/root/.hermes/brain/PROJECTS.md]    — long-term projects
[/root/.hermes/brain/DECISIONS.md]   — decisions made & why
[/root/.hermes/ATM/trades.html]      — trades dashboard
[/root/.hermes/ATM/ai-decider.py]    — signal decision logic
[/root/.hermes/ATM/guardian.py]     — order execution
[/root/.hermes/ATM/approved-signals.json] — approved signals feed
[/root/.hermes/ATM/hype_live_trading.json] — LIVE TRADING KILLSWITCH
[/root/.hermes/data/signals_hermes_runtime.db] — signal SQLite DB
[/root/.hermes/data/hl_fills_*_raw.csv] — HL fill history

## Quick Status (dynamic — updated every 30 min by cron)
WIN RATE:  46% (7d) | PNL: -$23.50 (7d) | POSITIONS: 8 open (all SHORT)
LIVE TRADING: ON/OFF | REGIME: SHORT | PIPELINE: RUNNING ✅

## Active / In-Flight (what we're working on RIGHT NOW)
- [TBD each session — filled at session start]

## Current Session Focus (1-3 bullets max)
- [What T asked me to do right now]

## Decided / Closed (what's DONE — don't revisit without asking)
- [Completed items from this session]

## Critical Flags
- hype_live_trading.json = KILLSWITCH (must be false to block real orders)
- [Bugs fixed, regime decisions, etc.]

*Updated: YYYY-MM-DD HHMM UTC*
```

### 2. Auto-Refresh via context-compactor Cron

The `context-compactor` cron already runs every 30 min. Currently it updates stats. We need it to also update the **Quick Status** and **Critical Flags** sections of CONTEXT.md in-place (sed/patch, not full rewrite).

**What to auto-update every 30 min:**
- Win rate, PnL, position count (from trades.json or DB)
- Pipeline status (is hermes-pipeline running?)
- Live trading flag state
- Any WASP errors or warnings
- Freshness check: if Updated timestamp is >2h old, add a ⚠️ STALE flag

**What stays manual (session wrap only):**
- Current Session Focus
- Decided / Closed
- Active / In-Flight

### 3. SOUL.md — Per-Turn Context Hook

**Replace/append in SOUL.md:**
```
## Context Anchor
At the START of every session AND after >5 min idle:
  1. cat /root/.hermes/CONTEXT.md
  2. Note: Current Session Focus, Decided/Closed, Critical Flags
  3. Check TASKS.md: grep -n "\- \[ \]" /root/.hermes/brain/TASKS.md
  4. If the user's request matches something in Decided/Closed → 
     "We already resolved that. Still on [current focus]?"
  5. If the request is a pivot → confirm: "Shifting to [X]. Current focus was [Y]. OK?"
```

### 4. Session Kickoff — One Line

At the start of each session (or when T returns):
- Read CONTEXT.md silently
- Open with: "Ready. Session focus: [X]. [Any stale flags?]"

### 5. End-of-Session Write (hermes-session-wrap skill)

On session wrap, update CONTEXT.md:
- Move completed items → Decided / Closed
- Refresh Current Session Focus
- Update timestamp

---

## Implementation Steps

| Step | What | File(s) |
|------|------|---------|
| 1 | Refactor CONTEXT.md with new structure | `/root/.hermes/CONTEXT.md` |
| 2 | Patch context-compactor cron to patch Quick Status + Critical Flags in-place | `context-compactor` script |
| 3 | Add SOUL.md "Context Anchor" section | `SOUL.md` |
| 4 | Update hermes-session-wrap skill to refresh CONTEXT.md sections | skill |
| 5 | Write current session state to CONTEXT.md right now | `/root/.hermes/CONTEXT.md` |

---

## Validation
- [ ] `grep -n "Updated:" /root/.hermes/CONTEXT.md` shows today
- [ ] Next idle return: I open with session focus without being prompted
- [ ] Requests to revisit closed items → redirect, not re-do
- [ ] File anchors visible in CONTEXT.md — I stop searching for paths

---

## Open Questions
- Should Decided/Closed persist across sessions or clear at session start?
  → **Recommend: persist**, so I can reference resolved issues across days
- Any other files to add to File Anchors?
