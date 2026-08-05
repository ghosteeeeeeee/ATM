---
name: full-review
description: "Run complete Hermes review: git commit+package, fire code reviewer subagent against full codebase, save report to brain. Run after significant changes."
category: trading
tags: [hermes, review, quality, git, code-review]
author: T
created: 2026-04-01
---

# Full Review — Hermes Trading System

End-to-end review workflow: git commit → package archive → fire code reviewer subagent → save report.

## Prerequisites
- Working dir: `/root/.hermes`
- Git at commit `40566e4` or later
- Git archives at `/var/www/git/`

## Step 1 — Commit + Package Git (update-git)

```bash
cd /root/.hermes
git add -A
git status --short
git commit -m "your commit message"
COMMIT=$(git rev-parse --short HEAD)
TS=$(date +"%Y%m%d-%H%M")
FULL_ZIP="ATM-Hermes-${TS}-full-${COMMIT}.zip"

# Build full zip
git archive --prefix=hermes/ HEAD | gzip > /tmp/${FULL_ZIP}
cp /tmp/${FULL_ZIP} /var/www/git/
chmod 644 /var/www/git/${FULL_ZIP}

# Build fix zip from last commit
LAST_FULL=$(ls /var/www/git/ATM-Hermes-*-full-*.zip 2>/dev/null | sort | tail -2 | head -1)
if [ -n "$LAST_FULL" ]; then
    LAST_COMMIT=$(echo $LAST_FULL | grep -o '[0-9a-f]\{7\}' | head -1)
    CHANGED_FILES=$(git diff --name-only ${LAST_COMMIT}..HEAD 2>/dev/null)
    if [ -n "$CHANGED_FILES" ]; then
        mkdir -p /tmp/hermes-fix/
        for f in $CHANGED_FILES; do [ -f "$f" ] && mkdir -p /tmp/hermes-fix/$(dirname $f) && cp -r "$f" /tmp/hermes-fix/"$f"; done
        (cd /tmp && tar czf ATM-Hermes-${TS}-fix-${COMMIT}.tar.gz hermes-fix/ && rm -rf hermes-fix/)
        cp /tmp/ATM-Hermes-${TS}-fix-${COMMIT}.tar.gz /var/www/git/
    fi
fi
```

Update `/var/www/git/index.html` with new commit. The page is simple — insert new table row at top, update download button hrefs.

## Step 2 — Fire Code Reviewer Subagent

```python
delegate_task(
    goal="""You are Code Reviewer — expert code review specialist for the Hermes cryptocurrency trading system.

Review these files:
- /root/.hermes/scripts/signal_gen.py
- /root/.hermes/scripts/position_manager.py
- /root/.hermes/scripts/hermes-trades-api.py
- /root/.hermes/scripts/brain.py
- /root/.hermes/scripts/signal_schema.py
- /root/.hermes/scripts/ai-decider.py
- /root/.hermes/scripts/decider-run.py

Known issues to investigate:
- guardian_missing (22 trades 0s life)
- orphan_recovery (13 trades)
- hl_position_missing (9 trades)

Return COMPLETE report with these sections:
## Blockers (CRITICAL)
## Suggestions
## Nits
## Known Bug Deep Dive
## A/B Test Issues
## Summary and Next Steps (top 5 actions)

Read the actual code. Return full report in one shot.""",
    context="Hermes git repo: /root/.hermes (commit 40566e4). Brain DB: PostgreSQL brain@localhost/brain. Signals DB: /root/.hermes/data/signals_hermes_runtime.db. Git download: /var/www/git/ATM-Hermes-20260401-0511-full-40566e4.zip",
    toolsets=["terminal", "file"],
    max_iterations=200,
)
```

## Step 3 — Save Report to Brain

After subagent returns, save the report to `review_reports` table in signals DB.

## Key Findings From 2026-04-01 Review

Top 3 blockers:
1. **Dual guardian reconciliation** — `hl-sync-guardian.py` AND `position_manager.refresh_current_prices` both reconcile HL↔DB independently. Remove lines 882-944 from position_manager.py. Make guardian the SOLE reconciliation authority.
2. **SQL injection in record_closed_trade** (hl-sync-guardian.py:275-284) — f-string interpolation instead of parameterized queries. Use `%s` placeholders throughout.
3. **SHORT trailing activation bug** (position_manager.py:1055-1062) — `abs(pnl_pct)` for SHORTs activates trailing on LOSS instead of profit. Remove `abs()` wrapper.

Top 5 suggestions:
1. Move all JSON state (signal_cooldowns, loss_cooldowns, trailing_stops, recent_trades) to PostgreSQL
2. Add LIMIT 2000 to price history query (signal_schema.py:593-605)
3. Add epsilon-greedy to A/B variant selection (10% random, 90% weighted)
4. Add failure counters to silent exception handlers
5. Clear _signal_streak_cache in signal_gen.py run() loop
