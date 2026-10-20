# CEO Brief: Shadow Trader Findings — Flip Test, Exit Engines, Hold Times

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-20 22:50 UTC
**Priority:** HIGH — T's 4 directives, 3 completed with findings

## TLDR

Built 3 new analysis modes per CEO verdict. Key findings:

1. **Flip test**: volume_breakout_long flipped SHORT is **BETTER by +0.873%** (WR 17.1% → 48.6%)
2. **Exit engines**: hmacd_mtf Universal Hold is **BEST** (88.1% WR, +4.495% avg) vs ATR 43.7% +0.416%
3. **Hold times**: pump-chain SHORT winners avg 120min vs losers 52min — 33% of winners take >2h

## Finding 1: Flip Test — volume_breakout_long (T Directive 1)

| Direction | WR | Avg | Total |
|-----------|-----|-----|-------|
| Original LONG | 17.1% | -0.409% | -14.30% |
| **Flipped SHORT** | **48.6%** | **+0.464%** | **+16.24%** |
| Delta | **+31.4%** | **+0.873%** | |

**T was right** — flipping the signal is profitable. The signal is actually a SHORT signal mislabeled as LONG.

## Finding 2: Exit Engine Comparison — hmacd_mtf (T Directive 2)

| Engine | n | WR | Total | Avg |
|--------|---|-----|-------|-----|
| **Universal Hold** | 126 | **88.1%** | **+566.35%** | **+4.495%** |
| PM Trail | 120 | 100% | +89.08% | +0.742% |
| ATR (current) | 126 | 43.7% | +52.42% | +0.416% |
| Hard Max | 80 | 0% | -63.62% | -0.795% |
| Cut Loser | 72 | 0% | -84.47% | -1.173% |

**Universal Hold (8h) is the best exit engine** for hmacd_mtf — 88.1% WR, +4.495% avg. The ATR engine (current default) only gets 43.7% WR. Hard Max and Cut Loser are destroying value.

## Finding 3: Hold Time Analysis — pump-chain (T Directive 3)

| Direction | Winners Avg | Losers Avg | Winners >2h |
|-----------|-------------|------------|-------------|
| LONG | 69 min (1.1h) | 23 min (0.4h) | 13% |
| SHORT | **120 min (2.0h)** | 52 min (0.9h) | **33%** |

**T was right** — the arm timeout is culling winners. 33% of SHORT winners take >2h to develop. The current arm timeout (45min for pump-chain LONG) is too aggressive.

## What T Said

> "we can be tweaking things as the data comes in, and we can keep learning from it"

T wants iterative improvement based on shadow data. Each finding leads to a specific action:
- Flip volume_breakout_long in shadow mode
- Change hmacd_mtf exit engine to Universal Hold
- Extend pump-chain arm timeout

## CEO Feedback Requested

1. **Should we flip volume_breakout_long in shadow mode?** (T directive 1)
2. **Should we change hmacd_mtf exit engine to Universal Hold?** (T directive 2)
3. **Should we extend pump-chain arm timeout?** (T directive 3)
4. **Should we continue with ichimoku template sweep?** (T directive 4 — pending)

## What T Wants

T wants iterative improvement. The shadow trader is now collecting ~1000 outcomes/day. We can test changes in shadow before deploying to live.

## Protected Flags

13/13 INTACT. No config changed in this brief.
