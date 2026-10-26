# Bug-Hunter RE-Verdict — 2026-10-25 Shadow Final Corrected Report

**File verified:** `/root/.hermes/reports/20261025-shadow-final-corrected.md` (255 lines)
**DB verified against:** `/root/.hermes/brain/shadow_trades.db` (live query, 2026-10-25)
**Previous verdict:** 6/7 PASS, 1 FAIL (Fix 4: naive t-statistic absent)

=== BUG-HUNTER RE-VERDICT ===

## Fix 4 (naive t-statistic): PASS

Evidence:
1. **§1 Overall Stats table shows BOTH** — line 29: `| Naive t-statistic | -11.70 |` and line 30: `| **Cluster-robust t** | **-10.75** (2,703 clusters) |`. ✅
2. **§2 Direction table shows BOTH columns** — line 39 header: `| Direction | N | WR% | Net Total | Avg | t_naive | t_cluster | MFE/MAE |`; SHORT row `-7.30 / -7.03`, LONG row `-9.55 / -9.24`. ✅
3. **Methodology explains the difference** — lines 211–212 define both formulas (`t = mean / (std / sqrt(n))` vs per-cluster-means t-test), and line 217 has a dedicated **"Naive vs Cluster-Robust"** paragraph explaining independence assumption, timestamp correlation, and why cluster is more conservative. ✅
4. **Naive t = -11.70 present** — lines 29 and 217. Independently reproduced from DB: fresh gate-passed naive t = **-11.73** (n=8,755, mean=-0.08998%, sd=0.7177%) — matches within data drift (report was written at n=8,702; +53 rows have closed since). The formula in Methodology is exactly what produces this value (pop. gate-passed n checks: sqrt(8702) × -0.090/0.718 = -11.69). ✅
5. **Other tables** — §3 (signals), §4 (engines), §5 (tokens), §6 (gates) show `t_cluster` only, and §7 (RR) has no t-stats. This is ACCEPTABLE: the report explicitly defines significance as `|t_cluster| > 2.0` (line 213), naive t is documented with formula in Methodology, and the headline + direction tables (the only places the naive/cluster contrast matters for the report's claims) show both. Adding naive t per subgroup would be redundant and systematically more significant (misleading). No other table is required to show both.

## Minor 6 (gate footnote): PASS

Evidence: §6 line 144: `*Note: Gate table shows n>=30 rows only. EXEC-BLOCK (16 rows) and SKIP (1 row) omitted. Total gate-blocked = 11,596.*` — covers both the n>=30 filter AND the EXEC-BLOCK omission. Internally consistent: the 8 displayed gate rows sum to 11,579; 11,579 + 16 (EXEC-BLOCK) + 1 (SKIP) = 11,596. ✅

## Minor 7 (MFE/MAE data): PASS

Evidence (live DB query): `mfe_pct` populated in **20,383 rows**, `mae_pct` populated in **20,383 rows** (meets the 20,383+ requirement exactly); all 20,383 also have `net_pnl_pct`. `mfe_4h` non-NULL = **0 rows** — confirms the report's "dead columns" claim (line 224). 1 row has net but no MFE yet (20,384 net vs 20,383 mfe) — trivial, one newly-closed trade. ✅

## Overall: PASS

## Issues Found

1. **[MEDIUM — new finding, conclusion-neutral] §2 per-direction `t_naive` values do not reproduce from the DB.** Recomputed with the report's own Methodology formula (`t = mean/(std/sqrt(n))`) on gate-passed rows per direction: fresh = **SHORT -5.56, LONG -11.32**, but report shows **SHORT -7.30, LONG -9.55**. Also tested and did not match: all-closed (-10.09/-18.80), pooled-std (-5.17/-12.44), dedup-by-timestamp (-5.93/-7.29), daily-means (-1.50/-2.47), gross PnL (+9.92/-1.12), cluster keys `recorded_at`. Data drift cannot explain it (implied SHORT sd 0.474 vs actual 0.667 — impossible from +24 rows). NOTE: the **headline** naive t (-11.70) DOES reproduce (-11.73 fresh), and the direction *conclusions* are unchanged (both directions significantly negative either way), so Fix 4's presence requirement stands → PASS. Suggested fix: recompute §2 t_naive from gate-passed rows (SHORT ≈ -5.6, LONG ≈ -11.3) or document what population produced -7.30/-9.55.
2. **[INFO — expected drift] Report counts are as-of-write snapshots.** Live DB now shows 22,067 total / 20,384 net-PnL / 8,755 gate-passed vs report's 22,024 / 20,298 / 8,702 (DB mtime 21:23 Oct 25; shadow collection continues). Report's "20,298 rows updated" (Fix 1) and cluster count (2,703 vs fresh 2,720) are stale-but-correct-at-write-time. Not a defect.
3. **[INFO] §2/§1 cluster t reproduce within drift:** fresh cluster-robust t = **-10.72** (2,720 clusters) vs report -10.75 (2,703); direction cluster fresh SHORT -7.21 / LONG -9.01 vs report -7.03 / -9.24. All well within drift of 53 new rows.

**Verdict: Fix 4 now PASSES (was FAIL). Minors 6 and 7 PASS. Overall PASS — 1 medium residual issue (§2 t_naive reproducibility) that does not change any conclusion in the report.**
