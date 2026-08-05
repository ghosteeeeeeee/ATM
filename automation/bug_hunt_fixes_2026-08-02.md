# Bug Hunter Fix Audit — 2026-08-02 23:45 UTC

## Verdict: All fixes correct. No critical bugs found.

---

## Fix-by-Fix Audit

### 1. `hermes_constants.py` — Frozen params + NEVER_REENABLE
| Check | Result |
|-------|--------|
| ATR_SL_MIN_INIT = 0.020 | VERIFIED |
| TRAILING 0.0025/0.0050 | VERIFIED |
| SIGNAL_FILTER_SPEED_MIN = 45 | VERIFIED |
| ACCEL_300_MINUS_ENABLED = False | VERIFIED |
| NEVER_REENABLE includes ACCEL_300_MINUS | VERIFIED |
| **freeze guard blocks writes until 2026-08-04** | VERIFIED |

**Minor note:** ATR_SL_MIN (floor for established trades) remains 0.8% separate from INIT 2.0%. Existing positions show eff_sl=0.8% — this is correct by design.

### 2. `decider_run.py` — SpeedTracker speed unification
| Check | Result |
|-------|--------|
| _ctx_gate_get_speed uses SpeedTracker | VERIFIED |
| Empty cache → returns None (safe fallback) | VERIFIED |
| Refilled cache → real percentile | VERIFIED |
| No more is_stale→0 mapping | VERIFIED |

**MEDIUM:** If SpeedTracker cache is empty (before update() runs), ctx gate returns None → treated as unknown, no skip triggered. In practice hotset path always calls update() first. Acceptable.

### 3. `hl-sync-guardian.py` — close_position_hl + stale markers
| Check | Result |
|-------|--------|
| SDK None = already flat → success | VERIFIED |
| Retry once on real failure | VERIFIED |
| Flat-check after exception | VERIFIED |
| Stale marker age expiry (30min) | VERIFIED |
| Step6 pending_retry on fail | VERIFIED |
| Cleared stuck markers (JUP/GALA/ME/XMR) | VERIFIED |

**MEDIUM:** close_position_hl can make up to 3 user_state() API calls + 2 market_close per close. Retry sleep (5+10=15s) keeps within HL rate limits. Acceptable.

### 4. `param_auto_tuner.py` — CEO freeze hard-guard
| Check | Result |
|-------|--------|
| Frozen keys detected and skipped | VERIFIED |
| Returns empty applied list | VERIFIED |
| Blocks even if timer re-enabled | VERIFIED |

### 5. `auto_1hr_prompt.md` — Freeze instruction
| Check | Result |
|-------|--------|
| Lists frozen keys | VERIFIED |
| Freeze until date noted | VERIFIED |

### 6. `run_ceo.sh` — Updated health assumptions
| Check | Result |
|-------|--------|
| No old kill switch assumptions | VERIFIED |
| Pipeline timer ≠ service active check documented | VERIFIED |

### 7. Systemd fixes
| Check | Result |
|-------|--------|
| hermes-metrics.service Restart in [Service] | VERIFIED |
| hermes-signal-purge OnCalendar=hourly | VERIFIED |
| Timers disabled (auto-1hr, param-tuner) | VERIFIED |

### 8. guardian-closing-markers.json
| Check | Result |
|-------|--------|
| Cleared stuck tokens | VERIFIED |
| File has correct {tokens, saved_at} shape | VERIFIED |

---

## Design Observations (not bugs)

| Item | Severity | Note |
|------|----------|------|
| NEVER_REENABLE only blocks rotator | INFO | decay_detector is one-way (disable only), by design |
| ATR_SL_MIN floor ≠ INIT | INFO | Floor 0.8% for established trades, INIT 2.0% for new entries |
| Pipeline Type=simple + 60s timer | INFO | 18s execution, 42s margin — safe |
| Speed empty cache race | LOW | ctx gate returns None → no skip, no false positive |
| 8 LLM jobs on port 4099 | MED | port collision risk (pre-existing) |
| signal_rotator still running 4h | MED | can flip non-frozen flags (pre-existing) |

---

## Conclusion

**All 8 fixes are correct and safe.** No regressions introduced. No critical bugs found.
