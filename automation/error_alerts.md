## Error Alerts — 2026-08-09 18:40 UTC
- **[WARN]** (1x): `[PHANTOM-DBG] ASTER LONG: TIGHT SL DETECTED sl=0.602210 entry=0.602220 dist=0.002%` — SL distance too tight, phantom trade risk. Needs param review.
- **[WARN]** (1x): `hermes-hl-volume: 429 rate limit` — Hyperliquid API rate limited, transient. Will recover.
- **[WARN]** (1x): `hermes-git-release: status=1/FAILURE` — Backup failing for 2+ hours. Needs investigation.

## Error Alerts — 2026-08-09 20:40 UTC
- **[CRITICAL]** (60x in last 3h, 1x/min): `signal_compactor NameError: RANGE_BREAKOUT_PLUS_ENABLED is not defined` — Root cause: `signal_schema.py:is_component_disabled()` import block missing 3 range_breakout constants. FIXED by adding `RANGE_BREAKOUT_ENABLED, RANGE_BREAKOUT_PLUS_ENABLED, RANGE_BREAKOUT_MINUS_ENABLED` to import at line 1888. Verified with direct run — compactor now completes cleanly (cycle=16305, 0 hotset).
