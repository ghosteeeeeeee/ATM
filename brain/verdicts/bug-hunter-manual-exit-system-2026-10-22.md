# Bug-Hunter Verdict — NEW MANUAL EXIT SYSTEM (2026-10-22)

**Target:** `scripts/manual_exit_manager.py` (new) + `position_manager.py` guards
**Method:** Executed (monkeypatched psycopg2 / DB paths; real-DB read-only queries; fake trade_id 999999 CAS no-op)
**Harnesses:** `/tmp/mxm_verify_1.py`, `/tmp/mxm_verify_1b.py`, `/tmp/mxm_verify_2.py` (65 executed checks)

## Verdict table

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Sole-authority completeness | **FAIL (latent)** | One gap: `_collect_atr_updates` L2076 filters only `ai-trader-manual`/`ai-trader-pending` — NOT `ai-trader-auto`. Executed: auto-tag pos collected → `_persist_atr_levels` L2324 issues `UPDATE trades SET stop_loss,target`. Latent: 0 `ai-trader-auto%` trades exist ever (auto_trader still shadow). All other writers guarded/unreachable/self |
| 2 | Pump-exit gating | PASS | Matcher executed: manual→'rr_engine' (exact), pending/auto/auto-add→'rr_engine' (prefix `startswith('ai-trader-')`). None → pump_exit/ride_it |
| 3 | Ratchet correctness | PASS | 11-case matrix LONG/SHORT × below-act/in-loss/violation/equal/improvement/CAS-skip. Violation/equal → False, 0 conns. Improvement → CAS SQL `(new_sl,id,old_sl)`, pos sync, conn+cur closed. Real-DB no-op id=999999: 1 UPDATE, 0 rows, row nonexistent after |
| 4 | Same-cycle ordering | PASS | AST: trail call L3151 before hit check L3245 same iteration. Executed: hit check reads synced SL (manual_trail_hit sl=100.299); stale counterfactual differs |
| 5 | Label matrix | PASS | 17 executed cases: all 6 manual labels + rr_engine_trail_hit/atr_trail_hit/atr_sl_hit/atr_tp_hit intact for non-managed; guardian-marker skip works; entry_price-missing → conservative manual_sl_hit |
| 6 | Crash paths | PASS | None/int/dict/empty/list signals safe; missing keys/sl=0/entry=0/cur=0/garbage → False no-crash; psycopg2-import-fail & secrets-missing → WARN + False + finally no-op. Note: garbage direction falls to SHORT branch (unreachable from loop) |
| 7 | Unleveraged activation | PASS | pnl_pct=+500 w/ price<act → no trail; pnl_pct=-99 w/ price≥act → fires. update_trail never reads DB pnl |
| 8 | Comma-multi edge | PASS (latent hardening) | Substring → managed, RR excluded (guarded). BUT pump/ride exclusion is matcher-based, not is_ceo-guarded: `pump-chain+`/`volume-breakout+` comma combos WOULD leak. Empirically unreachable: 0 comma-multi manual/pending/auto trades ever; brain.py single --signal |
| 9 | Activation boundary | PASS | `profit_pct < ACT` → ≥ fires: 1000/1004, 100/100.4, 81500/81826 all fire. Sub-unit float (0.1/0.1004 → 0.003999999999999976) defers 1 tick — IEEE rounding, immaterial |
| 10 | Actor list | PASS (see notes) | Writers on CEO SL: (1) manual_exit_manager only; (2) guardian reads-only + closes (intentional); (3) trade_watchdog move_stop → HL replace_sl — exchange-side, no signal filter, DB write paper-only (divergence risk, outside PM loop); (4) decider_run SL-FIX practically unreachable (max-id SELECT of own insert) |

## Findings to fix (in priority order)
1. **MED/latent — `position_manager.py:2076`**: add `'ai-trader-auto'` or use `manual_exit_manager.is_managed_signal(_sig_chk)` so the ATR collector's exclusion set matches MANAGED_TAGS. Today's live exposure: none (0 auto trades); becomes real the moment auto_trader goes live. Also L2072 comment ("Manual trades use RR-engine structural exits") is outdated.
2. **LOW hardening — `position_manager.py:2929/3107`**: add `and not is_ceo_trade` to pump-exit and ride-it gating (currently relies on matcher resolution; comma-multi with pump_chain+/volume-breakout+ part would leak into `_persist_sl`/ride_it SL writers).
3. **LOW external — `trade_watchdog.py:1701`**: auto-exec `move_stop` calls HL `replace_sl` with no signal filter; for real CEO trades brain DB is not updated (`adjust_stop_loss` is paper=TRUE only) → exchange/DB divergence.
4. **Sideways — `position_manager.py:2829`**: `_execute_atr_bulk_updates` is CALLED but defined nowhere; flipping `ATR_HL_ORDERS_ENABLED=True` (L164) would NameError the whole manage loop.
5. **Observation — unguarded CLOSE actors on CEO trades**: wave_turn (L3279), MACD cascade flip (L3359+), cut_loser (L3506), stale_exit (L3517), weather-vane force-close + trailing_distance write (L2754/2777, flag=True). Not SL writers, but wave_turn/cascade flips are structural exits, not safety nets — tension with "managed by exactly two things".
6. **Cosmetic**: `update_trail` treats any non-'LONG' direction as SHORT (no validation); `is_managed_signal(['ai-trader-manual'])` → True via str().

**Overall: PASS for today's live population (manual/pending), with one latent contract gap (ai-trader-auto × ATR collector) that must be fixed before auto_trader leaves shadow.**
