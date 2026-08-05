---
name: hl-trading-debug
description: Debug Hyperliquid trading operations — position sync failures, rate limits, price data gaps, phantom trades, ghost trades (add_orphan_trade silent failure), and PnL sync discrepancies.
triggers:
  - "position not syncing"
  - "rate limit 429"
  - "phantom trade"
  - "PnL inflated deflated discrepancy HL vs local DB"
  - "profits inflated losses deflated notional mismatch"
  - "sub-10 second close"
  - "false guardian_tp on profitable position"
  - "guardian_tp on exit below entry"
  - "signal quality pnl mismatch — shows LOSS but HL profited"
  - "stale pnl_pct used for signal quality instead of hype_realized_pnl_usdt"
  - "mirror_close backfill pnl not used by _record_signal_outcome"
  - "false loss cooldown set from stale data"
  - "NOT_HOTSET on signal-driven trade"
  - "ADA MET ORDI duplicate open/close pairs in HL — 3 trades in 7 min = pending retry never cleared + Step 6 failure path saved to pending_retry + pending retry ran before orphan set built; 10 compounding _CLOSED_HL_COINS bugs found and fixed 2026-06-12; _CLOSED_HL_COINS invariants: every _clear_pending_retry must also add to _CLOSED_HL_COINS; see references/guardian-duplicate-orphan-trades-2026-06-12.md"
  - "ai-engineer subagent finds bugs that don't exist — ALWAYS verify with grep+py_compile"
  - "ai-engineer phantom detection fix FAILS — LIMIT 1 without direction finds guardian_orphan trades and masks phantom"
  - "PHANTOM_CLOSE backfill never fires — _get_hl_exit_price never returns 0, so exit_price=0 condition is always false"
  - "STALE_ROTATION stale pnl_pct — rotation uses pre-close pnl instead of actual close pnl"
  - "STALE_ROTATION no loss cooldown — losing stale trades can re-enter immediately"
  - "STALE_ROTATION reconciled token not cleared — re-reconciliation blocked after rotation"
  - "ai-engineer 2026-06-12 first pass: 566s, no timeout; position_manager.py timed out at 600s (had to verify manually in main session); always verify ai-engineer findings in main session — grep+py_compile+read_file"
  - "ai-engineer 2026-06-12 second pass (20-min timeout): STILL timed out at 600s despite allocation; did not receive results; manual audit done in main session instead; files >2000 lines need targeted reads only via subagent, not full-file audit"
  - "ai-engineer 2026-06-12 THIRD pass (20-min timeout): again timed out at 600s; all three passes timed out at 600s regardless of allocation; always do the audit directly in main session for files >2000 lines; use execute_code for targeted searches, not subagent full-file reads"
  - "ai-engineer Bug 5 (paper flag) was WRONG — paper = not is_live_trading_enabled() is CORRECT logic"
  - "FIXED (2026-06-12 first pass): duplicate orphan trades — ADA 3x, MET 2x in 7 min; 10 compounding bugs: (A) pending retry never cleared on Step 6 success, (B) Step 6 failure saved to pending_retry, (C) pending retry ran before orphan set built, (D) _check_hard_stops didn't add to _CLOSED_HL_COINS, (E) pending retry used mid price instead of HL fill, (F-H) 6 more _CLOSED_HL_COINS missing-add sites; audit found 1 CRASH (self-introduced: int(curr_price) as timestamp), 2 HIGH, 7 MEDIUM"
  - "FIXED (2026-06-12 second pass): 2 more bugs found in manual audit: (Bug A) close_ok NameError CRASH — self-introduced by first-pass patch; orphan Row dedup path referenced close_ok outside its assignment scope; fixed by initializing close_ok=False before if-else block; (Bug K) pending_gone leak — _clear_pending_retry was inside if trade_id: block, leaked when no reconciled trade_id existed; infinite retry loop; fixed by moving _clear_pending_retry outside if block"
  - "ai-engineer 2026-06-12: hl-sync-guardian.py audit returned in 566s (no timeout); position_manager.py timed out at 600s (had to verify manually in main session); always verify ai-engineer findings in main session — grep+py_compile+read_file"
  - "mirror_close raises RuntimeError when LIVE_TRADING_ENABLED=False — orphan HL position on rollback after DB INSERT failure; FIX: use close_position (no gate)"
  - "FIXED (2026-06-12 third session): PHANTOM_CLOSE backfill (G4) — _retry_phantom_close_fills() SELECT and UPDATE both had 'AND exit_price=0' condition; _get_hl_exit_price NEVER returns 0 (it returns fallback price or current market price as last resort), so this condition was always false — no PHANTOM_CLOSE trade could ever be backfilled; removed exit_price=0 from both WHERE clauses"
  - "FIXED (2026-06-12 third session): CASCADE_FLIP hard-SL close (G5) — direct SQL UPDATE at line 1476 bypassed _close_paper_trade_db; missing: (1) _record_loss_cooldown — losing token could re-enter immediately, (2) _clear_reconciled_token — new position blocked from re-reconciling, (3) pnl_pct/pnl_usdt left NULL in DB; fix: call _close_paper_trade_db(trade_id, token, flip_exit_px, 'CASCADE_FLIP') then do targeted UPDATE for flip_variant only (since _close_paper_trade_db doesn't handle it)"
  - "FIXED (2026-06-12 third session): STALE_ROTATION rate_data possibly unbound — 'rate_data = {}' was inside the try block; if os.path.exists(rate_file) raised any exception, rate_data was never assigned; subsequent _update_rate() call would NameError; fix: move rate_data={} before the try block"
  - "All SQL param counts verified correct: unprotectable UPDATE (7), breach UPDATE (9), _close_paper_trade_db (8), _close_orphan_paper_trade_by_id (8) — all confirmed in main session"
  - "local DB missing trades that HL shows — 2 AAVE trades locally but 4 on HL, 1 AVNT locally but 4 on HL; guardian self-close fills not recorded in DB; HL shows close, local DB shows nothing"
  - "HL fill schema 'side' field: LONG closes have side='A' dir='Close Long'; SHORT closes have side='B' dir='Close Short'; using side=='B' as close-fill filter silently drops ALL LONG closes — same root cause bug appears in 4 locations across 3 files; fix: use 'Close' in str(f.get('dir', ''))"
  - "fill filter 'side == B' bug — 4 locations: hl-sync-guardian.py:881 (_poll_close_fills_once), hl-sync-guardian.py:509 (phantom backfill), backfill_hl_pnl.py:52+119, backfill_orphan_hl_prices.py:71-72; all fixed 2026-06-10; same bug was fixed in _close_paper_trade_db line 2523 on 2026-04-19 but the other locations were missed"
  - "guardian Path B orphan INSERT silently dies on duplicate key — ON CONFLICT DO NOTHING RETURNING id fix; 3-branch fallback (INSERT won, INSERT lost, genuine gap); nextval for unique trade_id"
  - "hype_cache entry_px stale — causes entry_price mismatch; guardian writes wrong hl_entry_price; always sync hl_entry_price from HL even when entry_price delta < 0.1%"
  - "sync_pnl_from_hype crash on float-str — prices dict had string values; explicit float() coercion on prices.get() result"
  - "guardian orphan creation dead code — continue at ~line 1199 makes orphan creation code unreachable; PEOPLE trade @ 17:34 came from brain.py hotset pipeline, not guardian orphan path"
  - "_poll_open_fill_once added but not yet wired into orphan creation; pending fix: remove unreachable continue + wire HL open fill fetch"
  - "FIXED (2026-06-11): _poll_open_fill_once() now wired into all 4 orphan paths; uses actual HL open fill price (wavg from 5-min window) instead of stale /info entry_px; 4 paths: reconciled_id path (line ~1139), dup_row path (line ~1177), orphan creation path (line ~1247), _close_orphan_paper_trade_by_id call (line ~1283)"
  - "FIXED (2026-06-11): remove unreachable continue at ~line 1199; orphan creation block now reachable for fresh HL positions with no prior reconciled state and no DB record; AAVE @ 15:40 and AVNT @ 13:44/14:14 were casualties of the dead continue"
  - "FIXED (2026-06-11): all 4 orphan paths now write BOTH entry_price AND hl_entry_price to DB; previously reconciled_id and dup_row paths only wrote entry_price, leaving hl_entry_price stale"
  - "FIXED (2026-06-11): _close_orphan_paper_trade_by_id call uses hl_entry (actual fill price) not entry_px (/info estimate) for notional calculation; int(lev) coercion added to fix float→int type mismatch in add_orphan_trade call"
  - "FIXED (2026-06-11): trade_id possibly unbound Pyright warning — checkpoint block referenced trade_id before add_orphan_trade call; moved checkpoint to after add_orphan_trade where trade_id is guaranteed defined"
  - "FIXED (2026-06-11): reconcile_hype_to_paper entry delta check (0.1%) still gates entry_price writes, but hl_entry_price is ALWAYS written regardless of entry_price delta — needed because hype_cache entry_px can match DB (both wrong) and skip the entry_price update while hl_entry_price still needs correcting"
  - "ai-engineer subagent correctly identified dead code (2026-06-13) — subagent said breach check at lines ~3143-3159 was unreachable after v1 fix; verified in main session — subagent was RIGHT; ai-engineer DOES find real bugs, don't dismiss findings without verification; always verify with read_file + python3 -m py_compile"
  - "FIXED (2026-06-12): close_position(token) uses default slippage=0.02 (2%) in 5 locations; guardian CLOSE_SLIPPAGE=0.005 (0.5%) should be used everywhere; affected: _check_hard_stops line 1743, _attempt_flip_position lines 1394/1399, stale-rotation line 1599, _rotate_stale_positions line 1996; close_position_hl (line 794) correctly uses CLOSE_SLIPPAGE; the imported close_position from hyperliquid_exchange.py defaults to 2% for emergency closes but guardian's 0.5% is the right target for normal operation"
  - "FIXED (2026-06-12): _close_orphan_paper_trade_by_id lev=1 shadow bug — local lev=1 at line 2676 shadowed the function parameter; when amount_usdt_override was provided (orphan path), elif branch was skipped and lev stayed 1 instead of int(lev) from hl_pos; fix: removed lev=1, parameter value is correct for orphan path"
  - "FIXED (2026-06-12): 'pos_data' in dir() idiom wrong — line 1282; pos_data is for-loop variable, always in scope; direct reference is safer; fix: _sz = float(pos_data.get('size', 0))"
  - "FIXED (2026-06-12): stale self-close branch undefined variables — refactoring entry_delta/direction_changed into explicit branches initially used new_sl/new_tp (defined inside original if block); fix: use record['sl_price'] and record['tp_price'] directly (already loaded at line 3062)"
  - "FIXED (2026-06-12): _check_hard_stops missing _CLOSED_HL_COINS.add() — line 3147 used _CLOSED_HL_COINS.add(coin) without .upper(), so _sweep_blocklist_trades (which uses .upper()) couldn't find it → token treated as still open → _attempt_flip_position fires → creates new orphan; fix: add .upper() to _CLOSED_HL_COINS.add(coin)"
  - "FIXED (2026-06-12): stale-marker cleanup doesn't clear pending retry — lines ~3646-3652; when token falls out of HL (close succeeded but marker not cleared), stale-marker cleanup clears the closing marker but NOT the pending retry file → next cycle re-loads pending retry → attempts close_position_hl on non-existent position → 429 → orphan chain continues; fix: stale-marker cleanup also calls _clear_pending_retry([tok])"
  - "FIXED (2026-06-12): pending retry doesn't check HL before close_position_hl — lines ~4217-4237; pending retry block runs before hl_pos is fetched in main loop; attempts close_position_hl on tokens whose closes failed without checking if still in HL; non-existent position → 429 → same token stays in pending retry forever; fix: inline get_open_hype_positions_curl() to filter into pending_in_hl vs pending_gone; only call close_position_hl on pending_in_hl"
  - "ai-engineer audit 2026-06-12: 566s, no timeout; verified all 11 session fixes; found 2 new bugs (1 real, 1 false positive); Bug B (_sweep_blocklist_trades missing _save_closed_set) was FALSE POSITIVE — _save_closed_set() IS called at line 2893; Bug A (close_position slippage) was REAL — all 5 calls fixed to use CLOSE_SLIPPAGE; good delegation hygiene: specific line ranges + trade timeline + DB schema = no timeout"
  - "ai-engineer subagent correctly identified: dup_row path uses stale entry_px for hl_entry_price — FIXED: added _poll_open_fill_once to dup_row path, now writes both entry_price and hl_entry_price"
  - "guardian_orphan INSERT duplicate-key (2026-06-11) — Path B orphan INSERT at ~line 3717 now uses ON CONFLICT DO NOTHING RETURNING id; 100+ occurrences across all coins May-June 2026; symptom: HL close SUCCEEDS but DB record never written; except block only logged+slept, never closed the orphan"
  - "SELF-CLOSE stale TP/SL v1 fix WAS WRONG (2026-06-13) — restructure had `if record: compute fresh + continue` (skip breach) and `else: compute fresh + continue` (skip breach); breach check code at lines ~3143-3159 became UNREACHABLE dead code; UNPROTECTABLE coins would NEVER be closed by guardian; verified by ai-engineer subagent; fixed in v2: check breach FIRST (using stored TP/SL), then ALWAYS refresh TP/SL every cycle, then fire if breached — both fresh SL/TP compute AND breach fire execute in same cycle"
  - "false guardian_tp on profitable position — guardian_tp fired but price was below entry (loss), not above (profit); tp_price was stale from a prior market regime stored in tpsl_self_close; stale detection only refreshed on entry_delta > 0.001%; always refresh TP/SL every cycle for UNPROTECTABLE coins; see references/guardian-self-close-stale-tp-sl-2026-06-13.md"
  - "_check_stale_rotation updated_at string crash (2026-06-13) — `speed_data['updated_at']` returned string from JSON; `_time.time() - string` raised `TypeError: unsupported operand type(s) for -: 'float' and 'str'`; fix: `float(speed_data['updated_at'])` with try/except; crash was caught by outer try/except so guardian survived but PnL sync failed every cycle"
  - "sync_pnl_from_hype traceback logging (2026-06-13) — `log(f'  sync_pnl_from_hype failed: {e}')` only showed the error message, not the location; adding `traceback.format_exc()` to the FAIL log revealed the actual crash site in 1 cycle; always add full traceback to exception handlers when the error message is insufficient to locate the crash"
  - "guardian_tp on exit below entry — trade closed at loss but guardian_tp reason written; stored tp_price in tpsl_self_close was below entry price for a LONG; stale TP from previous position's market regime"
  - "stale-refresh race (2026-06-11) — _check_hard_stops stale refresh now checks BOTH entry price delta AND direction change; stale LONG→SHORT flip was refreshing wrong-direction SL/TP; AVNT 13:44 and 14:14 SHORT opens MISSING from DB (same bug)"
  - "prices.json STRING values — prices.json stores all values as JSON strings (e.g. '0.024830' not 0.024830); when passed to compute_live_pnl(entry_price_hl, prices.get(token), direction), causes 'unsupported operand type(s) for -: float and str'; always cast via float(prices.get(token)) before pnl_utils"
  - "AAVE double-orphan same day (2026-06-11) — AAVE orphan at 15:40: guardian closed @ 63.57 HL, INSERT failed duplicate-key (Path B except block silent); AAVE reappeared at 16:01 via signal_gen, proper open/close recorded id=11804; AAVE also orphan at 06-10 08:59 (prior day, INSERT failed same way); root: Path B except block dies silently instead of finding+closing existing record"
  - "guardian Path A vs Path B orphan handling — Path A (add_orphan_trade at ~line 745): INSERT...WHERE NOT EXISTS — race is handled (fetchone()==None = skip, use existing); Path B (~line 3717): plain INSERT with no conflict guard — race hits duplicate key, except block only logs+sleeps, NO fallthrough to find+close; ALL 100+ duplicate-key failures were Path B; fix: ON CONFLICT DO NOTHING RETURNING id + 3-branch logic (INSERT won, INSERT lost, genuine gap)"
  - "guardian_orphan INSERT hardcoded trade_id = lev*1000000 — collides with sequence-generated ids (id=10214=ASTER=5*1000000+5000000??); actually the collision mechanism is the race condition, not this formula; nextval('trades_id_seq') used in third-branch fallback to guarantee uniqueness"
  - "calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt — 0.0 is falsy → PnL inflated ~5x for small positions; FIX: is not None check"
  - "amount_usdt = float(row['amount_usdt'] or DEFAULT_TRADE_SIZE_USDT) — 0.0 falsy for fee base in position_manager.py:883 and :1096; FIX: is not None check"
  - "hl-sync-guardian.py:696 — parts[5] falsy in get_db_open_trades: 'if parts[5]' treats '0' as falsy → phantom $50; FIX: 'parts[5] is not None and parts[5] != \"\"'"
  - "hl-sync-guardian.py:2610,2694,2696 — _close_orphan_paper_trade_by_id amount_usdt and calc_notional 0.0 falsy; FIX: is not None check"
  - "hl-sync-guardian.py:696 — get_db_open_trades() parts[5] falsy for amount_usdt in pipe parser; FIX: is not None check"
  - "hl-sync-guardian.py guardian_orphan INSERT (no-DB-record path) — FIXED 2026-05-20: hl_notional_usdt column ADDED to INSERT; amount_usdt set to computed hl_notional (not $50 placeholder); hl_notional = abs(sz × entry_px_raw) from HL position data; all 4 call sites to _close_orphan_paper_trade_by_id now pass amount_usdt_override"
  - "_close_orphan_paper_trade_by_id function signature — FIXED 2026-05-20: added amount_usdt_override=None kwarg; all 4 call sites now pass actual HL notional via this param; DRY check at top of function returns True in dry mode"
  - "position_manager.py:883-884 and :1102-1103 — amount_usdt and calc_notional 0.0 falsy bug; FIXED 2026-05-20: is not None check on both amount_usdt and hl_notional_usdt; guardian orphan close path uses actual HL sz × entry_px via amount_usdt_override"
  - "LIVE_TRADING_ENABLED=False — kill switch is working; raise to True to resume live trading"
  - "mirror_open returns signal-level notional_usdt (~$10) instead of actual HL fill notional (~$7); DB gets wrong hl_notional_usdt → PnL denominators systematically off; FIX: compute actual notional from entry fill sz × fill_price"
  - "mirror_open_batch result dict missing notional_usdt, total_sz, hl_entry_price — guardian can't store actual HL notional in DB"
  - "hyperliquid_exchange.py:913 _poll_close_fills_once uses side=='B' filter — misses ALL LONG close fills (Close Long = side='A'); identical bug already fixed in hl-sync-guardian.py:2569 but still present here in hypex itself; FIX: filter on 'dir' containing 'Close'"
  - "brain.py close_trade() fallback PnL — OLD: ((exit - entry) * calc_notional * lev / entry) effectively doubled leverage (calc_notional already includes leverage); FIXED 2026-05-20: use compute_close_pnl which multiplies unleveraged pnl_pct by calc_notional only"
  - "sync_pnl_from_hype() — OLD: if unrealized_pnl != 0: skip ALL updates (price+PnL) for breakeven positions → stale current_price for entire cycle; FIXED 2026-05-20: always writes prices/PnL regardless of breakeven"
  - "sync_pnl_from_hype fails with 'name compute_live_pnl is not defined' — missing import in hl-sync-guardian.py; pnl_utils compute_close_pnl was imported but compute_live_pnl was not; FIX: add compute_live_pnl to the pnl_utils import line; verify with python3 -m py_compile after fix; symptom: every sync cycle logs [FAIL] sync_pnl_from_hype but positions still sync correctly (unrealized_pnl passes, only pnl_pct is broken)"
  - "close_position_hl error dict treated as success (2026-06-19) — HL API returns {'status': 'err' 'User or API Wallet does not exist'} but close_position_hl returns True because it hits the 'unexpected result structure' branch at line ~817; ONDO and MORPHO June 18 closes were silently ignored; FIXED: added status=='err' check before statuses parsing; guardian restarted with fix"
  - "UNI NOT_HOTSET orphan close (2026-06-19) — Trade #2 (UNI SHORT @ 3.0254) closes via guardian_sl; Trade #1 (UNI SHORT @ 3.0462) is orphan recovery created BEFORE Trade #2 close filled; when Trade #2 fill arrives, Trade #1 orphan has no signal; Missing (DB-only) path closes it as NOT_HOTSET instead of preserving original atr_sl_hit; root: guardian orphan_recovery trades have no signal stored; fix: when closing Missing paper-only trades, use the HL fill's close reason (atr_sl_hit) not hot-set check"
  - "Secrets file confusion — THREE wallet files: (1) /root/.hermes/.secrets.local = CURRENT working wallet (0x8507BEE..., SIGNING_KEY present); (2) ~/.secrets/hyperliquid-main.json = OLD revoked wallet (0x5AB4AC..., HL_API_KEY+HL_API_SECRET); (3) ~/.secrets/hyperliquid-wallet.json = THIRD wallet (0xFf47..., different private key); Only .secrets.local is read by hyperliquid_exchange.py; hyperliquid-main.json was read by a script that parsed JSON before .secrets.local format was standardized; .secrets.local is the SOLE source of truth; NEVER update .secrets.local from hyperliquid-main.json"
  - "MET duplicate open (2026-06-19) — market_close returned immediately with ok (order submitted, not filled); 6 polls over 30s found no fill; orphan path triggered next cycle and created new DB record #12018; closing marker cleared before fill confirmed; root: close_position_hl returns before fill, fill polling is separate loop; see references/metr-duplicate-open-2026-06-19.md"
  - "HL wallet does not exist — 'User or API Wallet 0x... does not exist'; OLD PROBLEM (June 18): hyperliquid_exchange.py hardcoded SIGNING_WALLET_ADDRESS=0x5AB4AC... (revoked), filter excluded HL_SIGNING_KEY so _SIGNING_KEY was empty; CURRENT STATE (June 19): .secrets.local has working wallet 0x8507BEE... and matching SIGNING_KEY; PEOPLES opened successfully with 0x8507...; .secrets.local is the source of truth, NOT ~/.secrets/hyperliquid-main.json (that file has the OLD revoked wallet 0x5AB4...); fix: hyperliquid_exchange.py already fixed to load from .secrets.local; verify with: python3 -c 'from hyperliquid_exchange import get_wallet; print(get_wallet().address)'"
  - ".secrets.local CORRECT wallet — guardian shows 'Wallet does not exist' for old wallet 0x5AB4... (REVOKED June 18); .secrets.local at /root/.hermes/.secrets.local has SIGNING_WALLET_ADDRESS=0x8507BEE... which IS the actual HL wallet (confirmed: PEOPLES opened with it June 19); hyperliquid_exchange.py reads only from /root/.hermes/.secrets.local; .secrets.local also MISSING HL_SIGNING_KEY (filtered out at line 24); fix: remove SIGNING_WALLET_ADDRESS from filter + change hardcoded fallback to globals().get(); DO NOT update .secrets.local from ~/.secrets/hyperliquid-main.json (that has the OLD revoked wallet 0x5AB4...); verify current wallet: python3 -c 'from hyperliquid_exchange import get_wallet; print(get_wallet().address)'"
  - "brain.py RC=1 with empty stderr — actual error is in stdout (print result dict), not stderr capture; check journal for 'brain.py RC=1' and look at stdout line before it"
  - "pipeline running but hot-set empty AND brain.py RC=1 every cycle — check if HL wallet was revoked (mirror_open fails silently with success=False dict); guardian also shows 'HL returned empty' when wallet doesn't exist; verify: python3 -c 'from hyperliquid_exchange import mirror_open; print(mirror_open(\"ONDO\",\"SHORT\",0.35,5))'"
  - "brain.py mirror_open RC=1 FAILED: stderr=(empty) — error dict is in stdout before the FAIL line; grep journal for 'stdout=' to see the actual HL API error; most common: 'Wallet does not exist' or 'Insufficient margin'"
  - "all mirror_open calls failing simultaneously — test directly: python3 -c 'from hyperliquid_exchange import mirror_open; print(mirror_open(\"ONDO\",\"SHORT\",0.35,5))'"
  - "HL API returns empty positions every cycle since X date — check guardian log: 'HL returned empty after 4 retries'; wallet revocation + API key mismatch; see references/hl-wallet-revoked-2026-06-18.md"
  - "HL SDK IndexError PERMANENT FIX (2026-05-30): Patch info.py line 48 — add `if base >= len(spot_meta['tokens']) or quote >= len(spot_meta['tokens']): continue` before `tokens[base]` access; skips malformed @367 entry (token idx 479 >= tokens len 464); apply once, survives restarts; verify with python3 -c 'from hyperliquid.exchange import Exchange; ...'"
  - "HL SDK: clearinghouse_state DOES NOT EXIST on patched Info class — use user_state() instead; clearinghouse_state returns 422 to plain requests (needs SDK session); user_state works via SDK path after info.py patch"
  - "HL nonce endpoint (2026-05-30) — POST /info with {'type':'nonce'} returns 422 to plain requests.post() even with Content-Type: application/json header; SDK's API.post() session works because it sends additional headers or encoding; Trading blocked until resolved or SDK locally patched"
  - "prices.json STRING values — prices.json stores all values as JSON strings (e.g. '0.024830' not 0.024830); when passed to compute_live_pnl(entry_price_hl, prices.get(token), direction), the string causes 'unsupported operand type(s) for -: float and str' in sync_pnl_from_hype; ALWAYS cast via float(prices.get(token)) before passing to pnl_utils functions"
  - "sync_pnl_from_hype float-str error FIXED (2026-05-30): explicit float() coercion on entry_price_hl and curr_price_hl before compute_live_pnl call; hl-sync-guardian.py line ~1485; guardian must be restarted to pick up the fix"
  - "mirror_open discards entry fill realized_pnl from mirror_get_entry_fill — never returned to caller even though it's computed"
  - "ai-engineer position_manager audit compared archive files instead of live file; live file has MAX_LEVERAGE=5 correctly"
  - "ai-engineer subagent TIME OUT at 600s AND at 1200s (20 min) — every subagent in 2026-05-20 session timed out; subagent in 2026-06-12 session ALSO timed out at 1200s for hl-sync-guardian.py (4359→4240 lines) and position_manager.py; ALWAYS do the audit directly in main session for files >800 lines; verify bug claims with grep+py_compile in main session before implementing; set 15-minute timeout explicitly for future ai-engineer audits"
  - "ai-engineer 2026-06-12 third-party external audit (skillsmp.com): returned in ~339 chars with 8 bug claims; manual verification found 7 FALSE POSITIVES and 1 TRUE BUG (range(3)→range(6) timeout fix); ALWAYS verify external audit claims the same way: grep+py_compile+read_file in main session regardless of source"
  - "FIXED (2026-06-12): _poll_close_fills range(3)→range(6) — two locations: _poll_hl_fills_for_close line 932 and _get_hl_exit_price line 986; extended from 3×5s=15s to 6×5s=30s to handle HL API latency spikes during high-load periods; 15s was causing premature 'no fills found' and orphan trades for positions that were actually closing successfully"
  - "FIXED (2026-06-12): Bug A — close_ok NameError CRASH (self-introduced by first-pass patch restructuring); orphan dedup path referenced close_ok outside the if-else block where it was only assigned; fixed by initializing close_ok=False before the if-else; symptom: NameError crash when orphan trade already in _CLOSED_THIS_CYCLE"
  - "FIXED (2026-06-12): Bug K — pending_gone infinite retry leak; _clear_pending_retry was inside `if trade_id:` block so when no reconciled trade_id existed, pending retry was NEVER cleared → infinite retry loop every cycle; fixed by moving _clear_pending_retry outside the if block (always clears regardless of trade_id)"
  - "External audit FALSE POSITIVES (2026-06-12, all verified in main session): (1) Race-condition DB update — NOT A BUG, all paths use single atomic UPDATE with status+guardian_closed in one statement; (2) Continue after orphan trade update — NOT A BUG, already fixed with full close logic before continue; (3) Missing is_guardian_close — NOT A BUG, already set at lines 2627+2745; (4) Pre-check omission — NOT A BUG, duplicate guard at lines 1163-1216; (5) SQL injection in ai_decider.py — NOT A BUG, all f-string queries use parameterized ? placeholders, placeholders variable only contains ? chars; (6) Duplicate-signal GROUP BY — NOT A BUG, GROUP BY combo_key already exists at signal_compactor.py:433; (7) Missing confidence floor — NOT A BUG, signal_compactor enforces confidence>=60 at line 440"
  - "ai_decider.py SQL injection claim (external audit) — FALSE POSITIVE; all 4 f-string execute() calls use parameterized ? placeholders; placeholders = ','.join(['?' for _ in open_tokens]) only produces ? chars; no string concatenation of user data into SQL"
  - "brain.py:337 — _get_trade_size_usdt hardcoded 50.0 instead of DEFAULT_TRADE_SIZE_USDT; FIX: use constant"
  - "brain.py add_trade() — no HL_MIN_NOTIONAL_USDT check before mirror_open; tiny signal ($1-5) reaches HL and fails; FIX: check effective_amount < HL_MIN_NOTIONAL_USDT ($11) before mirror_open"
  - "brain.py add_trade(): is_live_trading_enabled() gate returns None BEFORE any DB INSERT — blocks paper trades too when LIVE_TRADING_ENABLED=False. Unlike the _params mismatch (IndexError at query exec), this gate fires at line ~405 and exits with RC=1 before the INSERT is even built. Symptom: no PostgreSQL records for either open or closed trades; HL fills confirmed but no DB entry. Fix: paper trades must pass the gate — restructure is_live_trading_enabled() to return True when paper=True, or move paper bypass above the gate."
  - "brain.py mirror_open FAIL → DB INSERT still commits — DOT SHORT (trade #10226): mirror_open returned {'success': False, 'message': 'Insufficient margin to place order. asset=48'}; brain.py inserted trade #10226 into DB anyway (INSERT succeeded); guardian orphan detection ran 15s later and closed DB record; position manager ran next cycle and also closed it. FIX: after mirror_open fails, ROLLBACK the DB record using trade_id or re-raise and let exception handler rollback. Never leave a phantom DB record when HL has no position. See references/brain-mirror-open-fail-db-insert-2026-05-21.md"
  - "decider_run reads DB APPROVED but signal_compactor writes NONE — get_approved_signals() returns 0 while hotset.json has 10 entries; PRESERVE path bypasses PENDING→APPROVED transition; _enrich_and_write_signals() writes hotset.json without creating APPROVED DB rows; fix: upsert APPROVED row for each hotset_final entry in _enrich_and_write_signals()"
  - "DOT SHORT SL=1.2084 vs ATR_SL_MAX_INIT=0.9% — mathematically impossible"
  - "ICP SHORT SL=2.5175 doesn't match forward ATR computation from entry"
  - "price went up but atr_sl_hit triggered — mirror close misattribution"
  - "ICP SHORT SL=2.5175 matches ATR_K_NORMAL_VOL=1.25 (not current 0.75) — constants were different at execution time"
  - "ICP atr_sl_hit close reason is a misattribution — HYPE Mirror CLOSED SHORT triggered the exit, price went UP not down to SL"
  - "MIN_SL_INIT floor 0.7% applies too aggressively to low-ATR tokens (0.62%)"
  - "ICP SHORT closed 3s after open — not a bug — genuine SL hit after immediate adverse move"
  - "DOT SHORT closed 3s after open — not a bug — price moved against SHORT immediately"
  - "MORPHO SHORT #10430 closed 3s after open 2026-05-22 — User EXPECTS this to be a bug. T explicitly said 'the audit.log showed 7 seconds so it is a bug'. Prior session doc said 'not a bug' but T disagrees. The actual data: entry=$1.9448, SL=$1.9133 (1.62% below), exit=$1.9447 (price WENT DOWN in favor of SHORT by $0.0001). Trade closed +$0.00/+0.005%. The 3s gap = guardian opens, position_manager closes in its fast inner loop (separate process). BUT: price at close was $1.9447 — nowhere near SL $1.9133. The 'not a bug' doc assumed price moved adversely, but price moved favorably. Root hypothesis: check_atr_tp_sl_hits uses STALE current_price (pre-entry price ~$1.94 from before the trade opened, not the actual HL fill price $1.9448). A $0.0001 adverse move in the stale price may have crossed a stale/zero SL. DIAGNOSTIC REQUIRED: pull current_price from position_manager's position record at exact close_time — was it the stale pre-entry price?"
  - "rapid close <10s after open — run timing diagnostic; PostgreSQL timestamps are the source of truth"
  - "atr_sl_hit on favorable price move = BUG until proven otherwise — if price moved IN YOUR FAVOR and trade still closed with atr_sl_hit, the current_price used in the check was likely stale/wrong"
  - "MORPHO SHORT #10430 closed +$0.00 in 3s with price WENT DOWN in favor of SHORT — atr_sl_hit was a false misattribution"
  - "sub-10s atr false close (2026-06-01) — 26 trades; root cause: sync_pnl_from_hype CRASHES before updating current_price → entire Step 5 loop aborts, no positions get current_price updates → all have stale prices → check_atr_tp_sl_hits() reads stale → false atr_sl_hit; FIX: per-position try/except in sync_pnl_from_hype loop so one bad position doesn't crash ALL positions; also trace actual string source (prices dict may contain strings from prices.json); guardian restart needed after per-position fix; see references/sub-10s-atr-false-close-2026-06-01.md"
  - "sub-10s SIGNAL QUALITY BUG (2026-06-04) — AXS SHORT: Signal Quality showed pnl=-0.01% LOSS (conf=91) but HL mirror_close returned +1.18% profit (pnl_usdt=+$0.1297); cooldown was set from WRONG data; root: _record_signal_outcome in close_paper_position uses pnl_pct from DB (stale at that point) BEFORE mirror_close backfills hype_realized_pnl_usdt 12s later; signal quality log fired at line 1160 with stale pnl_pct; mirror_close at 1166 writes hype_realized_pnl_usdt but no signal quality correction; also _record_ab_close at 1158 uses stale pnl_usdt for win/loss determination even when hype_realized_pnl_usdt (ground truth) is available; see references/signal-quality-stale-pnl-2026-06-04.md"
  - "false loss cooldown from stale pnl_pct — _record_signal_outcome uses stale DB pnl_pct (current_price reverted to entry by time of processing) instead of hype_realized_pnl_usdt ground truth from mirror_close; same bug affects _record_ab_close win/loss classification; all sub-10s closes with profitable HL outcomes are misclassified as LOSS; cooldown streak corrupted; fix: use hype_realized_pnl_usdt when available, fall back to DB pnl_pct only when not set"
  - "guardian sync_pnl_from_hype crash on type mismatch — 'unsupported operand type(s) for -: float and str' in compute_live_pnl; entry_price or curr_price stored as string in PostgreSQL; guardian never syncs HL realized PnL to DB; all positions fall back to stale pnl_pct; per-position try/except needed so one corrupt record doesn't crash entire sync cycle"
  - "sub-10s closes — two distinct patterns: (1) guardian_orphan — 6-7s closes via guardian orphan sweep (ETH, AAVE, GALA, AVAX in May); (2) atr_sl_hit — 3-7s closes via position_manager check_atr_tp_sl_hits → close_paper_position → mirror_close; pattern (2) is majority of recent sub-10s; AXS SHORT June 4 closed in 12s with +1.18% HL profit but Signal Quality logged -0.01% LOSS"
  - "position_manager.check_atr_tp_sl_hits() RACE CONDITION with guardian orphan close (2026-06-01) — guardian writes closing marker before market_close, but position_manager had NO check for that marker; both could close the same token simultaneously; FIX (2026-06-01): added _is_closing_marker_active(token) guard in check_atr_tp_sl_hits() — skips ATR check if guardian is mid-close on that token; uses FileLock + guardian-closing-markers.json (same file guardian writes); see references/guardian-position-manager-race-2026-06-01.md"
  - "ai-engineer subagent CLAIMED 'float(row[\"f\"] or 0) at line 1485' — VERIFIED WRONG by main session: that pattern does not exist anywhere in hl-sync-guardian.py; the explicit float() coercion at lines 1485-1486 IS present and correct; real crash source is elsewhere (prices dict containing strings); ALWAYS verify subagent bug claims with grep+read in main session before passing to T"
  - "Issue #1 (2026-06-01 verified): _load_closing_markers() in hl-sync-guardian.py:395-402 has NO FileLock around its read — race condition: if guardian is mid-write (lock held, JSON half-flushed), reads get corrupt JSON; _save_closing_marker() (line 368) and _clear_closing_marker() (line 383) both call _load_closing_markers() WITHOUT holding the lock first (they acquire lock only for the write); _is_closing_marker_active() in hl-sync-guardian.py:404-406 also reads without lock; position_manager.py:367-375 has its own version that IS locked — but callers using hl-sync-guardian's version get the race; FIX: wrap read in _load_closing_markers() itself with FileLock('guardian_closing')"
  - "Issue #2 (2026-06-01 verified): hl-sync-guardian.py:1476 — curr_price_hl = float(pos_data.get('currentPrice', prices.get(token, entry)) or prices.get(token, entry) or entry); currentPrice from HL can be 'NaN', null, or non-numeric string; float('NaN') raises ValueError and crashes entire sync_pnl_from_hype loop; lines 1485-1486 (defensive float() calls) are AFTER the crash point and never execute; one bad position crashes ALL positions in the cycle; FIX: wrap currentPrice extraction in safe float converter with fallback before the float() call"
  - "guardian-closing-markers.json path: /root/.hermes/data/guardian-closing-markers.json — written by _save_closing_marker() before market_close; now also read by position_manager._is_closing_marker_active() as race-condition guard"
  - "record_closed_trade DUPLICATE UUID (2026-06-01) — existing_id passed but ignored; str(uuid4()) always generated → unique constraint violation on guardian_orphan path; fix: use existing_id when provided instead of generating new UUID"
  - "atr_sl_hit on favorable price move = BUG until proven otherwise — if price moved IN YOUR FAVOR and trade still closed with atr_sl_hit, the current_price used in the check was likely stale/wrong"
  - "MORPHO at ~$1.94 with 5x leverage: MIN_ATR_PCT=0.50% floor = $0.0097 minimum SL width; yet trade closed in 3s with only $0.0001 adverse move; if this pattern repeats on other low-ATR tokens, investigate whether ATR SL is computed correctly at signal time vs at position_manager's ATR update cycle"
  - "atr_sl_hit vs guardian_sl — atr_sl_hit comes from position_manager.check_atr_tp_sl_hits; guardian_sl comes from guardian _check_and_close_breached_trades"
  - "guardian log empty for ICP close timestamp — position_manager closed trade before guardian cycle ran"
  - "candles.db empty for ICP/DOT — cannot verify ATR values — ATR computed from HL API"
  - "brain.py INSERT fix VERIFIED 2026-05-20: 5 live trades confirmed in PostgreSQL (ids 10220-10224: ANIME, AAVE, ADA, ASTER, BSV); sync-guardian reports zero orphans, zero missing; Position Manager confirms 5 open; _col_map debug fires on each INSERT; confirmed: trade_id=10219 inserted and SELECT verified all columns correct"
  - "SELF-CLOSE stale TP/SL false guardian_tp/guardian_sl (2026-06-13) — stale detection only refreshed when entry_delta > 0.001% or direction changed; if new position entry ≈ old stored entry (entry_delta ≈ 0), stale TP/SL used for breach check; MORPHO guardian_tp at 1.9821 when tp_price was 1.9399 from Apr-28 (below entry for LONG, so ANY price movement triggered TP); AAVE guardian_sl when old SL=64.18 (above entry for SHORT) was written into new position; AVNT guardian_sl same pattern; FIX: restructure SELF-CLOSE — breach check FIRST using stored TP/SL, then ALWAYS refresh TP/SL every cycle via _upsert_self_close; never skip refresh based on entry_delta; see references/guardian-self-close-stale-tp-sl-2026-06-13.md"
  - "SELF-CLOSE breach check became dead code (2026-06-13) — original restructure had if record: compute fresh + continue (skip breach); else: compute fresh + continue (skip breach); breach check code at lines ~3143-3159 was never reached; correct restructure: check breach FIRST (using stored TP/SL), then ALWAYS compute fresh TP/SL and upsert, then fire if breached; both fresh SL/TP compute AND breach fire must execute in same cycle"
  - "sync_pnl_from_hype unrealizedPnl string crash (2026-06-13) — HL returns unrealizedPnl as numeric string (e.g. '123.45'); float() crashes with 'unsupported operand type(s) for -: float and str'; defensive try/except needed on unrealizedPnl extraction; also on entryPrice and currentPrice fields; also wrap compute_live_pnl call in try/except"
  - "guardian pkill multiple PIDs — ps aux | grep hl-sync-guardian returns MULTIPLE PIDs (old pre-fix process + new post-fix process both running); must kill ALL PIDs: pkill -9 -f hl-sync-guardian; single PID kill leaves old process running causing [FATAL] Guardian already running; always pkill when restarting guardian"
  - "MORPHO guardian_tp false breach + phantom close (2026-06-18) — guardian restart after crash (Jun 15 04:06, 16885 restart attempts) left stale TP in tpsl_self_close; breach check fired using stale TP; close_position_hl called with REVOKED WALLET but DB trade still closed; next cycle created orphan trade; two bugs: (1) post-restart TP/SL warmup missing — refresh all UNPROTECTABLE values before first breach check; (2) close_position_hl result handler may check wrong success field — API returned error dict but DB close still fired; grep 'if success' around self-close result handler to verify the success boolean is correctly extracted from the return dict"
  - "guardian close_position_hl success field extraction — close_position_hl returns a dict with 'ok' boolean; if result handler does 'success = result' instead of 'success = result.get(\"ok\")' then 'if success:' is always True for a non-empty dict regardless of HL API failure; grep for 'close_position_hl' and 'success' in hl-sync-guardian.py self-close block"
  - "MORPHO SHORT open since 2026-06-18 17:40 — guardian sees breach, calls close_position_hl, API returns 'User or API Wallet 0x... does not exist', guardian logs [PASS] and treats close as successful; position left open on HL; guardian closing marker NOT set; guardian reconciles position back into DB every cycle; position bleeds for days at 5x leverage; error dict treated as success; API key revoked June 18; see references/guardian-silent-hl-failure-2026-06-18.md"
  - "accel-300 fires SHORT when price is above EMA300 — SKY SHORT fired at price=0.0573 while SKY was +0.82% above EMA300; accel_300.py reads price_history from signals_hermes.db; SKY had a 33-min data gap (22:50–23:23 UTC 2026-06-18); accel-300 computed phantom negative gap_pct from stale data; signal passed confluence gate (2 unique types); TP/SL also wrong: guardian computed TP=1.926 vs correct TP=1.884; see references/accel-300-counter-regime-2026-06-18.md"
  - "guardian closing marker set but position not closed — MORPHO guardian-closing-markers.json shows MORPHO started 2026-06-18 17:41:34; marker was set but market_close failed silently; marker never cleared; position never closes; guardian reconciles same position back every 60s; symptom: [SELF-CLOSE] MORPHO SL=X TP=Y (no breach, px=Z) every cycle but position never actually closes"
  - "duplicate guardian orphan created when original close fill never confirms — MET SHORT #12017 close ordered, 6 polls no fill, next cycle created #12018 duplicate; UNI SHORT: Trade #1 closes via orphan recovery, Trade #2 (same coin) orphan recovery has no signal and closes as NOT_HOTSET instead of preserving original atr_sl_hit; guardian orphan path must preserve original signal, and Missing paper-only close must not check hot-set"
  - "UNI NOT_HOTSET — orphan recovery closes with wrong reason; see references/uni-not-hotset-orphan-signal-loss-2026-06-19.md"
---

# HL Trading Debug — Umbrella Skill

Comprehensive debugging guide for Hyperliquid trading issues in Hermes. Covers position sync, API rate limits, fill caching, price data gaps, and guardian close loops.

## Quick Diagnosis

Run the 3-way simultaneous query to compare all position sources at once:

```python
import sqlite3, psycopg2, json, sys
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl
from _secrets import BRAIN_DB_DICT

hl = {t: d for t, d in get_open_hype_positions_curl().items()}
hl_open = set(hl.keys())

conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
cur_pg = conn_pg.cursor()
cur_pg.execute("SELECT token, direction, status FROM trades WHERE status='open'")
pg_open = {r[0]: r[1] for r in cur_pg.fetchall()}
pg_set = set(pg_open.keys())

conn_sql = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c_sql = conn_sql.cursor()
c_sql.execute('SELECT token, direction FROM signals WHERE decision="EXECUTED"')
executed = {(r[0], r[1]) for r in c_sql.fetchall()}

print("In HL but NOT in PG:", hl_open - pg_set)
print("In PG but NOT in HL:", pg_set - hl_open)
for tok in pg_set & hl_open:
    if (tok, pg_open[tok]) not in executed:
        print(f"PG+HL open but NO EXECUTED signal: {tok}")
```

## ai-engineer Subagent — Always Verify Before Implementing

**ai-engineer subagent reliability for hl-sync-guardian.py varies.** Times out at 600s for files >2000 lines. Does find real bugs but also reports false positives. In 2026-06-13 session, subagent CORRECTLY identified that v1 SELF-CLOSE fix made breach check dead code — a finding I initially dismissed and had to verify independently. Always verify subagent findings with `python3 -m py_compile` + targeted `read_file` before implementing. Set 15-min timeout explicitly.

## 2026-06-12 Session False Positives

### hl-sync-guardian.py Audit — 2026-06-12
Told to audit hl-sync-guardian.py (4359 lines at session start → 4236 lines after fixes) with 12 pre-applied session fixes. Specific line ranges + DB schema provided. First pass: 566s, no timeout. Second pass at 20 min: timed out, did NOT receive results. Manual audit done in main session instead.

| Bug Claimed | Reality |
|-------------|---------|
| Bug B: `_sweep_blocklist_trades` missing `_save_closed_set()` | **FALSE POSITIVE** — `_save_closed_set()` IS called at line 2893; subagent misread the indentation/flow |
| Bug 5 (paper flag in brain.py) | **FALSE POSITIVE from 2026-05-20 session** — `paper = not is_live_trading_enabled()` IS correct logic |

### position_manager.py Audit — 2026-06-12
Timed out at 600s (returned only 341 chars). Did NOT receive results. Manual verification done in main session instead.

### Key Lesson
- 1200s timeout (20 min) still not enough for large files (~4331 lines)
- Parallel subagent batches work (2 of 3 returned), but position_manager timed out at 600s despite 1200s allocation
- For files >2000 lines: verify ai-engineer findings manually OR do targeted reads only, never full-file audit via subagent
- The subagent DOES find real bugs (Bug A slippage was real) but also reports false positives — always grep+py_compile in main session

## 2026-06-12 — Real Bugs Found by ai-engineer

All verified in main session before implementing:

| Bug | Severity | Verification |
|-----|----------|-------------|
| `close_position` uses 2% default slippage instead of `CLOSE_SLIPPAGE=0.5%` | MEDIUM | **REAL** — 5 call sites confirmed; fixed all 5 |
| `_poll_hl_fills_for_close` called with `int(curr_price)` (market price as timestamp!) | CRASH | **REAL** — introduced in this session's own patch; fixed immediately |
| `pending_gone` path clears pending retry without `_CLOSED_HL_COINS` | HIGH | **REAL** — Step 11 could double-close |
| Step 6 failure path doesn't add to `_CLOSED_HL_COINS` | HIGH | **REAL** — Step 11 could double-close |
| Multiple Step 6 sub-paths missing `_CLOSED_HL_COINS.add()` | MEDIUM | **REAL** — 3 paths fixed |
| Stale marker cleanup missing `_CLOSED_HL_COINS` | MEDIUM | **REAL** — fixed |
| `_check_hard_stops` failure path missing `_CLOSED_HL_COINS` | MEDIUM | **REAL** — fixed |
| HL API failure early-return doesn't clear `_CLOSED_HL_COINS` | MEDIUM | **REAL** — stale tokens from prior cycle |
| `_clear_pending_retry` read-modify-write not atomic | MEDIUM | **REAL** — created `_load_pending_retry_unlocked()` |
| `_record_loss_cooldown` inside try block | MEDIUM | **REAL** — moved before try block |
| Pending retry success/no-trade_id paths missing `_CLOSED_HL_COINS` | MEDIUM | **REAL** — fixed both paths |

## Verification Protocol
Before acting on ANY ai-engineer finding:
1. grep for the exact variable/function in the ACTUAL deployed file at `/root/.hermes/scripts/`
2. python3 -m py_compile on the file
3. Read the specific lines cited to confirm the bug description matches reality
4. Check if the "fix" makes the bug better or introduces a new problem

## Phantom EXECUTED Signal (signal marked EXECUTED, no trade on HL or in PostgreSQL)

**Symptom**: `signals.json` shows `decision=EXECUTED` for a token, but no corresponding trade in PostgreSQL and no position on HL.

**Root cause cascade (ALL FIXED 2026-05-20)**:

1. `is_live_trading_enabled()` returned `hermes_constants.LIVE_TRADING_ENABLED` (False) — brain.py rejected trade but decider_run marked signal EXECUTED anyway
2. decider_run marks signal EXECUTED before brain.py runs — rollback fires but matches nothing when sig_id=None
3. phantom detection `LIMIT 1` without direction filter found guardian_orphan open trades and masked phantom
4. DRY mode orphan INSERT bypass — phantom DB records during dry runs
5. sig_id=None race — two concurrent decider_run processes both claim via token+direction fallback, one gets phantom executed

**Recovery**: compactor's next purge cycle restores phantom signals to PENDING automatically.

## Guardian Orphan Close — Proper Fix Sequence (2026-05-20 session)

**Context:** `_close_orphan_paper_trade_by_id` at line 2575 accepts `trade_id, token, direction, entry_px, lev, reason`. When called for orphans with no DB record, it creates a guardian_orphan paper trade with `DEFAULT_TRADE_SIZE_USDT = $50` (hardcoded at line 3767), causing ~5x PnL inflation for $10 actual HL positions.

**Fix sequence (step-by-step, NO replace_all)**:

1. **Modify function signature** at line 2575 — add `amount_usdt_override=None` parameter
2. **Modify function body** — where it does `amount_usdt = DEFAULT_TRADE_SIZE_USDT` (line ~2694), use `amount_usdt_override if amount_usdt_override is not None else DEFAULT_TRADE_SIZE_USDT`
3. **Update caller at line ~3630** — `close_ok = _close_orphan_paper_trade_by_id(..., amount_usdt_override=computed_notional)`
4. **Update caller at line ~3673** — same, pass `amount_usdt_override=computed_notional`
5. **Update caller at line ~4058** — same
6. **Guardian orphan no-DB path** (lines ~3753-3768): add `hl_notional_usdt` column to INSERT using `abs(sz × entry_px)` from HL position data; set `amount_usdt` to computed `hl_notional` (not $50 placeholder)
7. **Stale marker cleanup** — MUST be after `hl_pos` fetch, not before. If before, rate-limited HL (empty dict) causes all markers to be incorrectly cleared as stale, orphan close never runs, markers persist forever. Move to line ~3563 (after Step 1 HL fetch).

## P&L Sync Plan (2026-05-20 — awaiting implementation)

User asked for plan before implementation. Full details in `references/pnl-sync-plan-2026-05-20.md`.

**Fix pattern** — use explicit None check everywhere:
```python
# WRONG
amount_usdt = float(row['amount_usdt'] or DEFAULT_TRADE_SIZE_USDT)
calc_notional = float(row['hl_notional_usdt']) if row['hl_notional_usdt'] else amount_usdt
# RIGHT
amount_usdt = float(row['amount_usdt']) if row['amount_usdt'] is not None else DEFAULT_TRADE_SIZE_USDT
calc_notional = float(row['hl_notional_usdt']) if row['hl_notional_usdt'] is not None else amount_usdt
```

**Files affected**: brain.py:637, brain.py:640, position_manager.py:883, position_manager.py:1096

## T's Workflow (Critical — Never Skip)

**"Only report first, let's plan, then we'll implement"** — T says this EVERY time. Pattern:
1. Investigate and report findings (facts only, no implementation)
2. Write plan document
3. WAIT for T's approval before implementing
4. Only after approval: implement

**Never jump to implementation during planning phase.** T corrects this when it happens.

**Subagent timeout:** ai-engineer subagent times out at 600s. Always verify bug claims with grep+py_compile in main session before implementing.

## Archive-Trade Idempotency (2026-05-20 verified)

**Existing archived trades are NEVER overwritten:**
- `INSERT OR IGNORE INTO trades VALUES (...)` — PRIMARY KEY `id` silently skips any existing row with the same id
- `existing_ids` set (loaded on `--apply`) provides a second skip layer before INSERT
- New trades get full signal context via `has_sig_in_pg` overlay + `row_data` mapping
- `hl_notional_usdt` added to `SQLITE_TRADE_COLS` (line 271, 99 cols total) — previously missing

## References

- `references/brain-mirror-open-fail-db-insert-2026-05-21.md` — **CRITICAL**: DOT trade #10226 phantom DB record; mirror_open FAILED with "Insufficient margin" but brain.py did not rollback DB INSERT; guardian closed phantom; position manager closed it again as atr_sl_hit. Full timeline, root cause analysis, fix required, diagnostic query.
- `references/sub-10s-atr-false-close-2026-06-01.md` — **CURRENT**: 26 sub-10s closes labeled `atr_sl_hit` but prices don't support SL breach; sync_pnl_from_hype crash on float-str leaves current_price stale; guardian restart needed; record_closed_trade duplicate UUID fix; stale-price guard in check_atr_tp_sl_hits
- `references/signal-quality-false-loss-2026-06.md` — **NEW** (companion): false LOSS recorded when HL profited; AXS SHORT +1.18% → logged as -0.01%; SUSHI SHORT -0.0724% → logged as -0.09%; _record_signal_outcome fires BEFORE mirror_close backfill; same stale-pnl pattern affects _record_ab_close; loss cooldown streak corrupted; fix: prefer hype_realized_pnl_usdt over stale DB pnl_pct
- `references/signal-quality-stale-pnl-2026-06-04.md` — **NEW**: AXS SHORT +1.18% HL profit recorded as -0.01% LOSS in Signal Quality; mirror_close backfill of hype_realized_pnl_usdt happens AFTER _record_signal_outcome fires → signal quality log uses stale PnL; loss cooldown set from wrong data; _record_ab_close also affected; fix: reorder or use hype_realized_pnl_usdt override
- `references/morpho-short-10430-rapid-close-2026-05-22.md` — ICP+DOT closed 3s after open; not a bug (genuine SL hits after immediate adverse move); `atr_sl_hit` vs `guardian_sl` attribution; atr_sl_hit on FAVORABLE price move IS A BUG (price moved down for SHORT, trade still closed with atr_sl_hit = stale-price misattribution)
- `references/pnl-5-bugs-fixed-ghost-trades-pending-2026-05-18.md`
- `references/short-sl-above-entry-bug-2026-05-15.md`
- `references/brain-params-mirror-open-2026-05-21.md`
- `references/brain-insert-43-vs-44-2026-05-20.md`
- `references/brain-insert-44-vs-44-verified-2026-05-20.md` — **CURRENT** brain.py INSERT verified fix: 44 params, 44 placeholders; trade_id=10219 confirmed; byte-level VALUES count command; live psycopg2 test — **CURRENT** brain.py INSERT: byte-level VALUES count verification, 43-vs-44 params vs placeholders, _col_map debug structure, signal_compactor.py line 843 crash, decider_run.py stderr capture
- `references/stale-marker-cleanup-order-bug-2026-05-20.md`
- `references/guardian-orphan-pnl-fix-2026-05-20.md`
- `references/phantom-trades-session-2026-05-20.md`
- `references/signal-compactor-timer-disabled-2026-05-19.md`
- `references/wave-phase-hotset-debug.md`
- `references/pnl-phantom-session-fix-2026-05-20.md`
- `references/tpsl-trailing-gate-bugs-2026-05-18.md`
- `references/phantom-executed-signal-ghost-trade-root-cause-2026-05-19.md`
- `references/brain-insert-still-failing-aster-2026-05-20.md`
- `references/hl-fill-cache.md`
- `references/guardian-self-close-dual-sl-bug-2026-05-18.md`
- `references/hl-rate-limit-debug.md`
- `references/phantom-trade-debug.md`
- `references/ai-engineer-false-positives-2026-05-20.md`
- `references/pnl-sync-plan-2026-05-20.md`
- `references/pnl-phantom-session-fix-2026-05-20.md`
- `references/phantom-executed-signal-aave-2026-05-19.md`
- `references/hl-db-insert-silent-failure.md`
- `references/brain-live-gate-blocks-paper-2026-05-20.md`
- `references/typo-crash-cascade-Faslse-2026-05-18.md`
- `references/constants-usage-audit-2026-05-20.md`
- `references/guardian-orphan-trade-id-collision-2026-05-19.md`
- `references/hl-trading-utils.md`
- `references/phantom-trade-debug.md`
- `references/brain-pnl-inflation-rollback-bugs-2026-05-20.md`
- `references/hl-sync-guardian-orphan-close-falsy-2026-05-20.md`
- `references/brain-db-insert-fail-chain-2026-05-20.md`
- `references/guardian-orphan-closing-bug-2026-05-08.md`
- `references/pump-mode-sl-staleness-bug-2026-05-17.md`
- `references/live-trading-is_live_trading_enabled-bug-2026-05-19.md`
- `references/ghost-trade-pnl-sync-2026-05-19.md`
- `references/ghost-trade-add_orphan_trade-silent-failure-2026-05-18.md`
- `references/loss-cooldown-missed-atr-sl-hit-2026-05-17.md`
- `references/mirror-close-rollback-silent-fail.md`
- `references/guardian-lock-file-2026-05-20.md`
- `references/pnl-sync-session-2026-05-19.md`
- `references/brain-step5-tp-sl-still-active-2026-05-17.md`
- `references/architecture_audit_logger-2026-05-17.md`
- `references/short-loosen-gate-bug-2026-05-18.md`
- `references/instant-reopen-cooldown-gap-2026-05-14.md`
- `references/short-atr-discrepancy-2026-05-18.md`
- `references/ghost-trade-zscore-zero-2026-05-17.md`
- `references/hl-sl-order-sources-2026-05-16.md`
- `references/phantom-executed-signal-price-zero-2026-06-18.md`
- `references/metr-duplicate-open-2026-06-19.md` — **NEW**: MET SHORT #12017/#12018 duplicate open; market_close returned before fill confirmed; 6 polls found no fill; orphan path created duplicate; close_position_hl error dict treated as success FIXED; closing marker cleared before fill confirmed; fix applied and guardian restarted
- `references/hotset-approved-desync-2026-05-21.md`
- `references/fil-short-initial-sl-bug-2026-05-15.md`
- `references/guardian-reopen-after-tp.md`
- `references/guardian-closing-marker-permanent-block-2026-05-08.md`
- `references/guardian-closing-marker-corruption-2026-05-17.md`
- `references/trades-json-server-filter-2026-05-08.md`
- `references/atom-phantom-reentry-2026-05-17.md`
- `references/sui-ghost-trade-fix-2026-05-16.md`
- `references/sui-short-5s-close-2026-05-17.md`
- `references/sui-gala-ghost-trades-2026-05-16.md`
- `references/vvv-0g-sl-wrong-atr-managed-false-2026-05-17.md`
- `references/sl-investigation-template-0g-2026-05-17.md`
- `references/atr-debug-logging-2026-05-15.md`
- `references/atr-tp-sl-authority-2026-05-15.md`
- `references/pnl-discrepancy-hl-vs-db-2026-05-18.md`
- `references/pnl-sync-implementation-2026-05-18.md`
- `references/fil-short-initial-sl-bug-2026-05-15.md`
- `references/hl-postgresql-insert-fail-chain-2026-05-08.md`
- `references/brain-insert-now-mismatch-2026-05-09.md`
- `references/short-sl-above-entry-bug-2026-05-15.md`
- `references/exclusion-filter-staleness-bug-2026-05-17.md`
- `references/cooldown-tracker-ms.md`
- `references/hermes-session-wrap.md`
- `references/hl-fill-filter-side-b-bug-2026-06-10.md` — **CURRENT**: 4 locations where `side=='B'` filter silently drops all LONG closes; HL fill schema confirmed; 2 AAVE + 2 AVNT trades missing from local DB; all 4 fixed; backfill scripts also had the same bug; same fix was applied to `_close_paper_trade_db` on 2026-04-19 but these 4 locations were missed
- `references/guardian-self-close-stale-tp-sl-2026-06-13.md` — **CURRENT**: stale TP/SL false guardian_tp/guardian_sl on UNPROTECTABLE coins (AAVE, MORPHO, AVNT, MET); stale detection only refreshed when entry_delta > 0.001% but if new entry ≈ old entry, stale TP/SL used for breach check causing false triggers; restructure: breach check FIRST using stored TP/SL, then ALWAYS refresh TP/SL every cycle; also fixes wrong denominator (entry_px vs stored_entry); guardian restart required
- `references/guardian-silent-hl-failure-2026-06-18.md` — **CURRENT**: MORPHO guardian_tp false breach + phantom close; stale TP from pre-crash tpsl_self_close triggered false breach; close_position_hl returned API error but DB trade still closed; orphan #11963 created next cycle; post-restart TP/SL warmup missing; close_position_hl success field extraction possibly wrong (full dict vs result.get("ok")); close_position_hl error dict treated as success FIXED 2026-06-19 (see metr-duplicate-open-2026-06-19.md)
- `references/stale-rotation-phantom-backfill-2026-06-12.md` — **CURRENT**: STALE_ROTATION bypassed `_close_paper_trade_db` (3 bugs: stale pnl_pct, no loss cooldown, no reconciled token clear); `rate_data` possibly unbound; PHANTOM_CLOSE backfill `exit_price=0` condition never triggered because `_get_hl_exit_price` never returns 0; all 6 bugs fixed this session
- `references/guardian-g4-g5-fixes-2026-06-12.md` — **CURRENT**: G4 (PHANTOM_CLOSE backfill) — removed `exit_price=0` from SELECT and UPDATE WHERE; G5 (CASCADE_FLIP hard-SL close) — replaced direct UPDATE with `_close_paper_trade_db` + separate flip_variant UPDATE; G6 (rate_data unbound) — moved `={}` before try block; SQL param counts verified correct; complete manual audit of lines 2116-4232 done in main session; subagent timed out for the 3rd consecutive time
- `references/external-audit-false-positives-2026-06-12.md` — **CURRENT**: 8 bug claims from external skillsmp.com audit; 7 false positives verified manually, 1 true bug (range(3)→range(6) timeout); always verify external audit claims with grep+py_compile+read_file in main session
- `references/missing-hl-trades-audit-2026-06-11.md` — **CURRENT**: audit of HL fill log vs PostgreSQL; 5 missing trades (2 AAVE, 3 AVNT); guardian_orphan INSERT duplicate-key bug; stale-refresh race bug; minor price discrepancies not bugs; database path summary (brain.trades = main writer, hyperliquid_trades = dead path)
- `references/missing-hl-trades-2026-06-11-fix.md`
- "references/guardian-orphan-4path-fix-2026-06-11.md" — **CURRENT**: 4-path orphan fix; _poll_open_fill_once wired into all paths; continue removed; all 4 paths now use actual HL fill price; ai-engineer subagent correctly identified dead code and unreachable orphan creation; verified in main session before implementing
- `references/guardian-duplicate-orphan-trades-2026-06-12.md` — **CURRENT**: first pass (10 bugs): 1 CRASH (self-introduced int(curr_price) as timestamp), 2 HIGH, 7 MEDIUM; second pass (2 bugs): Bug A (close_ok NameError CRASH — self-introduced by first-pass patch restructuring), Bug K (pending_gone infinite retry leak — _clear_pending_retry inside if trade_id: block, missed when trade_id=None); _CLOSED_HL_COINS invariants; all 12 bugs fixed hl-sync-guardian.py (4236 lines, Syntax OK)
- `references/guardian-orphan-triple-bug-2026-06-12.md` — **CURRENT**: 3 orphan bugs fixed; Bug 1 (_check_hard_stops missing _CLOSED_HL_COINS.add with .upper()); Bug 2 (stale-marker cleanup doesn't clear pending retry); Bug 3 (pending retry doesn't check HL positions before close_position_hl); all 4 _CLOSED_HL_COINS.add() sites now use .upper() consistently; inline HL check added to pending retry block; stale-marker cleanup also clears pending retry
- `references/guardian-price-mismatch-2026-06-11.md` — **CURRENT**: 3 bugs fixed, 1 pending; sync_pnl_from_hype float-str crash; Path B orphan INSERT silent death; stale self-close direction mismatch; hl_entry_price never synced from HL (partial fix); _poll_open_fill_once added but not wired; orphan creation dead code; PEOPLE/UNI price mismatch analysis; hype_cache entry_px behavior — **CURRENT**: two fixes applied to hl-sync-guardian.py; Path B orphan INSERT ON CONFLICT DO NOTHING + 3-branch logic; stale record direction mismatch check added to _check_hard_stops; detailed root cause analysis; PostgreSQL queries for diagnosis
- `references/hl-sdk-indexerror-meta-endpoint-2026-05-30.md` — **CURRENT**: HL SDK IndexError at info.py:48; meta endpoint response changed; ALL HL API communication broken; workaround using prices.json live data; verify with curl; fix options (SDK patch, bypass SDK, or await update)
- `references/pnl-utils-centralized-2026-05-20.md` — **NEW**: pnl_utils.py centralization (2026-05-20); all PnL math in one module; `unrealized_pnl != 0` guard bug fixed; local import pattern for profit_monster
- `python-gotchas/references/pnl-utils-centralization.md` — same content, class-level skill reference; use this for the general refactoring pattern (audit → create module → patch callers → verify)
- `references/config-constant-override-pitfall.md` — **Profit Monster specific**: config file overrides `hermes_constants` when keys exist; `cfg.get("min_profit_pct", PROFIT_MIN_PCT)` makes config win over constant; fix: use constants directly, not cfg.get() fallback; same pattern exists in cut_loser.py
- `references/verify-prices.md`
- `references/pump-hunter-bypass-hotset.md`
- `references/post-reboot-health-check.md`
- `references/pipeline-review.md`
- `references/archive-trades-delete-risk.md`
- `references/hermes-dual-writer-debug.md`
- `references/hermes-exit-attribution-debug.md`
- `references/hl-db-sync-debug.md`
- `references/price-history-race-2026-05-18.md`
- `references/zscore-staleness-bug.md`
- `references/hermes-constants-sync.md`
- `references/local-db-signal-fix.md`
- `references/pipeline-investigation.md`
- `references/pipeline-analyst.md`
- `references/prompt-training.md`
