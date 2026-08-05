# Additional Triggers — 2026-05-07 Session

These triggers were too many to fit in SKILL.md after the 2026-05-07 updates.

## New Session Triggers

Add to the SKILL.md triggers list:

```yaml
  - "pct-hermes fires alone no combo"
  - "confidence formula capped wrong"
  - "signals never combine window too tight"
```

## Key Session Learnings for Future Sessions

1. **Always check if signal generation timestamps align** before assuming signals can combine
2. **Confidence formulas need to be rechecked** when thresholds change — new ranges may hit old caps
3. **avg_pnl >= 0** is the right filter for standalone signals, not WR >= 40
4. **Window timing** matters as much as signal quality for combo formation
5. **accel-300 is the LONG crown jewel** but has been silent since 2026-05-07 — investigate first
