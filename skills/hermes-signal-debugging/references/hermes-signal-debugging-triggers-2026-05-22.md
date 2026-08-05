# hermes-signal-debugging — Updated Triggers
**Skill:** hermes-signal-debugging
**Date:** 2026-05-22
**Purpose:** Incremental update to SKILL.md triggers — added new zscore_pump findings from 2026-05-22 session.

---

## New / Updated Triggers (add to SKILL.md triggers section)

```yaml
# ADDITIONS from 2026-05-22 session:
- "zscore-pump fires LONG at local bottom before +2% rally — signal fires wrong direction at extreme z"  # refs: zscore-pump-reversal-improvement-2026-05-22.md
- "divergence check doesn't catch spike-and-collapse — bars_since_peak starts at 0, signal fires before rejection"
- "zscore_pump momentum philosophy conflicts with mean-reversion trading — flip direction at |z| > 3.0"
- "FET 01:16 z=+4.581 spike — single bar extreme then collapses, signal fires at peak not after"
- "zscore_pump blocks LONG signals for tokens with open positions — but open position direction was wrong"
```

## Patch for SKILL.md (triggers section)

Replace section:
```yaml
- "zscore-pump+ every combo loses"
```
With:
```yaml
- "zscore-pump+ every combo loses"
- "zscore-pump fires LONG at local bottom before +2% rally — signal fires wrong direction at extreme z"  # refs: zscore-pump-reversal-improvement-2026-05-22.md
- "divergence check doesn't catch spike-and-collapse — bars_since_peak starts at 0, signal fires before rejection"
- "zscore_pump momentum philosophy conflicts with mean-reversion trading — flip direction at |z| > 3.0"
- "FET 01:16 z=+4.581 spike — single bar extreme then collapses, signal fires at peak not after"
```

## Why This Wasn't Already in the Skill

The `hermes-signal-debugging` skill already had `reversal trap` triggers from the 2026-05-21 session. The 2026-05-22 session deepened the analysis specifically for zscore_pump — finding that the root cause is the signal's momentum philosophy conflicting with our mean-reversion approach, and that the divergence check has a timing flaw (bars_since_peak=0 at firing).

This is a more specific root cause than the generic "reversal trap" trigger implies. A curator reviewing this skill should fold the 2026-05-22 findings into the existing `reversal trap` trigger as an expanded note, so the skill distinguishes:
1. Generic reversal trap (any signal — trailing too tight, nadir anchor off-entry)
2. zscore_pump-specific reversal trap (momentum philosophy fires wrong direction at extreme z, divergence check timing bug)

The reference file `zscore-pump-reversal-improvement-2026-05-22.md` has the full technical details.