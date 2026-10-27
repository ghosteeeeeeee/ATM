# Trial Tracking Dashboard

**Last Updated:** 2026-10-27  
**Owner:** CEO / T  
**Purpose:** Track all active trials, deadlines, and pending implementations

---

## Active Trials

### 1. Wider SL Trial (CEO Q1)
| Field | Value |
|-------|-------|
| **Status** | 🟡 COLLECTING — FAILING threshold |
| **Started** | 2026-10-21 |
| **Deadline** | 7d / 200 trades review |
| **Constants** | CUT_LOSER=-6.00, ATR_SL_MAX=4.0, LONG only |
| **Current Data** | 3,007 rows with `exit_wider_sl_json` |
| **Current Result** | WR 40.1% → 32.7% (−7.4pp), PnL −289.9% → −605.1% |
| **Threshold** | WR ≥ 55% with ≥ 200 trades |
| **Status** | ❌ THRESHOLD NOT MET (32.7% < 55.0%) |
| **Caveat** | ATR_SL_MAX=4.0 is inert (trail band supersedes cap); effectively testing only CUT_LOSER −6.00 |
| **Action** | CEO decision needed: keep collecting, adjust, or kill |

### 2. Extended Time Exits Trial (CEO Q3)
| Field | Value |
|-------|-------|
| **Status** | 🔴 FAILING threshold |
| **Started** | 2026-10-26 |
| **Deadline** | 100 trades review |
| **Constants** | 2x arm timeout (60→120min, 45→90min), +4h universal hold (480→720min) |
| **Current Data** | 3,168 rows with `exit_extended_time_json` |
| **Current Result** | PnL −154.2% → −638.3% (−484.1%), WR 54.3% → 37.4% (−16.9pp) |
| **Threshold** | WR improvement ≥ 5.0pp with ≥ 100 trades |
| **Status** | ❌ THRESHOLD NOT MET (−16.9pp < 5.0pp) |
| **Caveat** | Comparison is apples-to-oranges (full stack vs time-only sim) |
| **Action** | CEO decision needed: keep collecting, adjust, or kill |

### 3. CONTRARIAN-LIVE (pump-chain- flip)
| Field | Value |
|-------|-------|
| **Status** | 🟢 LIVE — 0 real trades yet |
| **Shipped** | 2026-10-27 15:27Z (commit 98e9dc9b) |
| **Deadline** | 2026-11-03 (Z-FLIP conversion check) |
| **Evidence** | pump-chain- flip 64.6% n=350 (3rd reproduce) |
| **Current Data** | 0 real fade trades (23 log lines are TOK smoke tests) |
| **Watch** | First REAL fade trade = the live test |
| **Action** | Monitor for first real trade; Z-FLIP conversion check Nov 3 |

### 4. Coupled SL Trial (CUT_LOSER -6.00 / ATR 0.04)
| Field | Value |
|-------|-------|
| **Status** | 🟡 OPEN — Deadline Nov 3 |
| **Started** | 2026-10-27 (SHADOW-RECKONING round) |
| **Deadline** | 2026-11-03 |
| **Registry** | `trial-coupled-cutsloser-sl` in shadow_disposition.json |
| **Action** | Disposition due Nov 3 (+KEEP mirror) |

### 5. ICHIMOKU_LONG_BYPASS
| Field | Value |
|-------|-------|
| **Status** | 🟢 ACTIVE — Auto-revert guardrail |
| **Constants** | ICHIMOKU_LONG_BYPASS_ENABLED=True, MIN_WR=40.0, MIN_TRADES=5 |
| **Action** | Auto-reverts if WR < 40% with 5+ trades |

### 6. CONFLUENCE-EXPIRY Gate
| Field | Value |
|-------|-------|
| **Status** | 🟢 ACTIVE — Helping |
| **Data** | 12,518 blocked @48% WR (would-have-lost) |
| **Action** | Keep; proven helping |

### 7. Shadow Signals Runner
| Field | Value |
|-------|-------|
| **Status** | 🟢 ACTIVE — Stage A/C detectors |
| **Action** | Collecting data every 10min via pipeline |

### 8. CONF_FLOOR=30
| Field | Value |
|-------|-------|
| **Status** | ✅ SHIPPED (Oct 23) |
| **Action** | Monitor fkB (follow-on) |

---

## Deadlines Calendar

| Date | Item | Type | Status |
|------|------|------|--------|
| **2026-11-01** | Self-healing SKIP verify | Check | ⏳ Pending |
| **2026-11-01** | coin_regime trial | Trial | ⏳ Pending |
| **2026-11-03** | Coupled SL trial disposition | Trial verdict | ⏳ Pending |
| **2026-11-03** | eval-midband-long-4564 | Evaluation | ⏳ Pending |
| **2026-11-03** | Z-FLIP conversion check | Check | ⏳ Pending |
| **2026-11-03** | shadow_disposition weekly (13 open) | Review | ⏳ Pending |
| **2026-11-03** | shadow-trader-bypass review | Review | ⏳ Pending |
| **2026-11-03** | relative-regime review | Review | ⏳ Pending |
| **2026-11-03** | vb- WR recovery check | Check | ⏳ Pending |
| **2026-11-15** | floor trial (2,239 rows) | Trial | ⏳ Pending |
| **2026-11-15** | wyckoff trial (345 rows) | Trial | ⏳ Pending |
| **2026-11-03** | Escalation #17 auto-close | Auto | ⏳ Pending |

---

## Expired / No Implementation

### ⚠️ Trials with Data but No Decision

1. **Wider SL Trial** — 3,007 rows, FAILING threshold (31% WR vs 55% needed)
   - **Issue:** ATR_SL_MAX=4.0 is inert; only CUT_LOSER −6.00 is being tested
   - **Action:** CEO decision needed

2. **RR Engine** — ORPHANED (no owner)
   - **Issue:** rr_sl_hit accounts for 9.8% of exits with 0% WR (definitional)
   - **Action:** Needs owner or formal retirement

3. **oscillator_shadow** — FROZEN fossil (archived)
   - **Action:** No action needed (intentionally archived)

### ⚠️ PAST DEADLINE

1. **CONF_FLOOR fkB** — CEO queue item, no deadline set
   - **Action:** CEO decision needed

2. **bb-bounce TAT flip** — CEO queue item, no deadline set
   - **Action:** CEO decision needed

3. **MFE-CUT enforcement** — CEO queue item, no deadline set
   - **Action:** CEO decision needed

---

## Monitoring Commands

```bash
# Wider SL trial report
python3 scripts/shadow_trader.py --report-wider

# Extended time trial report
python3 scripts/shadow_trader.py --report-time

# Full shadow report
python3 scripts/shadow_trader.py --report

# Gate impact
python3 scripts/shadow_trader.py --report | grep -A5 "GATE JUSTIFICATION"

# Contrarian live status
grep "CONTRARIAN-LIVE" logs/decider*.log | tail -20

# Check shadow disposition
cat automation/ceo/shadow_disposition_report.md
```

---

## Key Metrics to Watch

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Wider SL WR | 32.7% | ≥55% | ❌ |
| Extended Time trades | 3,168 | ≥100 | ✅ |
| Extended Time WR delta | −16.9pp | ≥+5pp | ❌ |
| CONTRARIAN-LIVE real trades | 0 | ≥1 | ⏳ |
| Coupled SL data | collecting | Nov 3 | ⏳ |
| CONFLUENCE-EXPIRY blocked | 12,793 | keep | ✅ |

---

## Next Actions

1. **CEO decision on Wider SL trial** — threshold not met (32.7% vs 55%), ATR_SL_MAX inert
2. **CEO decision on Extended Time trial** — threshold not met (−16.9pp vs +5pp), apples-to-oranges comparison
3. **Watch for first CONTRARIAN-LIVE real trade** — 0 so far
4. **Nov 3 batch** — coupled SL disposition, midband eval, Z-FLIP, shadow_disposition weekly, rr-engine-shadow, chase-ratio, relative-regime
5. **Nov 10 batch** — gate-shadow, expiry-t5-shadow, mfe-cut-arm-be, ichimoku-dampen-flooradmit
6. **CEO queue** — CONF_FLOOR fkB, bb-bounce TAT flip, MFE-CUT enforcement
