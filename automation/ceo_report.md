# CEO Report — 2026-08-06 05:00 UTC

## System Health
- Pipeline: **active** ✅
- HL-Sync Guardian: **active** ✅
- All timers operational (19 timers active)
- Open positions: **0** (no open trades)

## 24h Performance (42 trades total)
| Signal | Trades | WR | PnL | Status |
|--------|--------|-----|------|--------|
| tl_break_long | 14 | 100% | +$1.81 | 🟢 BEST |
| vel-hermes- | 46 | 39.1% | +$0.47 | ⚠️ Should be disabled |
| zscore-rising+ | 8 | 62.5% | +$0.23 | OK |
| tl_break_short | 5 | 80% | +$0.22 | OK |
| bb_bounce | 17 | 47.1% | -$0.34 | 🔴 URGENT |
| decider | 9 | 0% | -$0.18 | 🔴 URGENT |

**Net 24h: -$0.17** (near breakeven)

## CRITICAL FINDINGS

### 1. bb_bounce RE-ENABLED — ROOT CAUSE FOUND
`hermes_constants.py:876` shows `BB_BOUNCE_ENABLED = True` with comment "re-enabled 2026-08-06 — 55.6% WR last 24h, confluence signal". **bb_bounce is NOT in NEVER_REENABLE_FLAGS** (line 656-670). Someone re-enabled it despite 3 days of URGENT flags. This is the 18 trades/24h bug.

**FIX:** Set `BB_BOUNCE_ENABLED = False` + add `'BB_BOUNCE_ENABLED'` to NEVER_REENABLE_FLAGS.

### 2. decider STILL FIRING (9 trades)
It IS in NEVER_REENABLE_FLAGS (line 669) but still generating trades. Bug — investigate signal registration.

### 3. vel-hermes- STILL FIRING (46 trades)
`VEL_HERMES_ENABLED = False` at line 674 but fires anyway. Likely registered in signals_runner with its own enable check bypassed.

## CEO DECISIONS

- [ ] **URGENT:** Disable bb_bounce permanently + add to NEVER_REENABLE_FLAGS
- [ ] **URGENT:** Investigate decider/vel-hermes- firing despite flags (bug_hunter)
- [ ] CONTINUE monitoring tl_break_long (100% WR, +$1.81, protected)
- [ ] CONTINUE monitoring hzscore+ confluence (100% WR on combo signals)
- [ ] MONITOR zscore-rising (35.5% WR SHORT, 62.5% WR LONG — mixed)

## Delegation
| Task | Owner | Priority |
|------|-------|----------|
| bb_bounce permanent kill | self_learner | URGENT |
| decider/vel-hermes- leak | bug_hunter | HIGH |
| tl_break_long protection | CEO | MONITOR |
