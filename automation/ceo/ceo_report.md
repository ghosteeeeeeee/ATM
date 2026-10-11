# CEO Report — 2026-10-11 (Spec Review: Combo-First Reputation System)

## VERDICT: APPROVE with 3 mandatory modifications

---

## Decisions

### 1. Combo penalty aggressiveness: **AGGRESSIVE (0.5x/0.3x) — APPROVED as specced**
Rationale: PG 30d shows real bleeding combos at n≥5 (pump-chain-v5 LONG 33.3% −$0.42, trend_purity+ LONG 36.4% −$0.90, open-skies+ LONG 33.3% −$0.40). n≥5 threshold is the sample guard — conservative 0.7x/0.5x would be noise-level and not fix the "bonus-only" problem. Note: Hebbian trade_log is sparse (3,393 unique combos / 5,555 rows ≈ 1.6 trades/combo), so most combos will sit at NEW 1.0x; penalties only fire on the few with real history. That is correct behavior.

### 2. New combos: **NEUTRAL 1.0x — APPROVED as specced**
Rationale: 0.9x penalizes before evidence exists — violates "if you can't measure it, don't change it." With Hebbian sparsity (~1.6 trades/combo), most combos ARE new; a blanket 0.9x would tax the entire unproven universe and slow signal development. Neutral 1.0x + shadow-mode evaluation (per Step 4 workflow) is the right path.

### 3. HALL-SHAME block: **CONVERT to 0.3x multiplier, keep combo-override — APPROVED**
Rationale: hard block (score→0.0) at coin WR<55%/15+ trades is the JUP bug — kills valid combos. New logic: block becomes 0.3x multiplier (equivalent to "Bad coin" tier); proven combo (WR≥60%, 3+ trades) overrides to full strength. This preserves suppression of shame coins without categorical kills. Coin-level remains the weaker fallback per the tier design.

### 4. Overall spec: **APPROVE** with modifications below.

---

## Mandatory Modifications (before implementation)

| # | Modification | Why |
|---|-------------|-----|
| M1 | **Pin Hebbian DB path to `brain/associative_memory.db`, NOT `data/associative_memory.db`** — the data/ copy is a **0-byte stub** | Verified: `data/associative_memory.db` = 0 bytes; real DB (4.7MB, 5,555 trade_log rows) is in brain/. Spec's Phase 1 must use the brain/ path or primary data source is empty. |
| M2 | **Filter test tokens out of trade_log queries** — `TEST_TTOK_B/TEST_TSIG_B` rows exist (9 rows, 0% WR) | Verified in trade_log. Without exclusion, TEST rows pollute combo WR stats and could theoretically fire penalties on test data. Add `token NOT LIKE 'TEST%'` guard in reputation.py queries. |
| M3 | **Phase 1 must land with `reputation.py` in shadow-only mode (log multiplier, don't apply) for 48h** before Phase 2 replaces live `_get_leaderboard_mult`/`_get_combo_mult`/HALL-SHAME | Combo penalties are NEW behavior (currently bonus-only). A bug in tier logic would suppress live trades across the book. Shadow 48h = measure before applying. Standard repo pattern. |

## Sideways findings (fold into implementation, already in spec)
- `hall_of_fame` dead data — use it or stop computing (spec line 136)
- Hebbian circuit breaker blind: 0/200 outcomes filled (spec line 137)
- `entry_gates.hebbian_gate()` dead code (spec line 138)
- `tp_bonus_mult` 1.50 vs 1.75 inconsistency (spec line 139)
- HoS threshold mismatch: block at WR<55%, list classifies at WR<45% (spec line 20) — reconcile in constants move

## Protected flags
No trading config changed this run. CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED, ROTATOR_PROTECTED_FLAGS, CEO_PROTECTED_FLAGS all INTACT (spec review only — no code touched).

## Next
- Delegate Phase 1 (`scripts/reputation.py` + constants) to bug_hunter with M1/M2/M3 embedded
- Shadow-mode 48h review checkpoint: **2026-10-13**
