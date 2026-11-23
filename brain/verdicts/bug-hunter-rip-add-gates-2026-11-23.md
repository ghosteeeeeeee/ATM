# bug_hunter verdict — rip-add band exemption (8d715762) + RIP-CLIMAX gates (bbc6c464)

Date: 2026-11-23 ~17:50 UTC · scope: exactly commits e2eb2d29, bbc6c464, 8d715762
Overall: **PASS with findings** — no HIGH; 1 MEDIUM (ATR1h DESC math), 1 LOW (dual-use flag), 1 INFO.

## Verdict table

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| A1 | direction casing at brain's check | ✅ PASS | [scripts/brain.py:474](/root/.hermes/scripts/brain.py#L474) normalizes `direction = 'LONG' if side_type == 'long' else 'SHORT'` BEFORE the band block; the check at [brain.py:501](/root/.hermes/scripts/brain.py#L501) `if band_exempt and direction == 'LONG':` is therefore **uppercase**. No reassignment of `direction` between L474 and L501 (grep of L474-502 shows only those two lines). The exemption fires. |
| A2 | payload whitelist → exec cmd | ✅ PASS | Set at [trade_watchdog.py:2149](/root/.hermes/scripts/trade_watchdog.py#L2149) (only when `_escaped`), carried in rebuilt action payload at [:2204](/root/.hermes/scripts/trade_watchdog.py#L2204), executor called with that payload at [:2872](/root/.hermes/scripts/trade_watchdog.py#L2872) (`action["order"]`), `--band-exempt` appended at [:2341](/root/.hermes/scripts/trade_watchdog.py#L2341), brain argparse [brain.py:1713](/root/.hermes/scripts/brain.py#L1713) → `band_exempt=getattr(...)` [:1810](/root/.hermes/scripts/brain.py#L1810) → param [:424](/root/.hermes/scripts/brain.py#L424). Chain complete. |
| A3 | flag absent = byte-identical old behavior | ✅ PASS | `git show 8d715762 -- scripts/brain.py`: with `band_exempt=False`, SHORT → same print + `return None`; LONG → same print + `return None` (only the shared `return None` was split into branches). Identical behavior. |
| A4 | winner-gate defer sets no flag | ✅ PASS | Flag assigned only inside the winning-open branch ([:2149](/root/.hermes/scripts/trade_watchdog.py#L2149)); the loser branch `continue`s at [:2160](/root/.hermes/scripts/trade_watchdog.py#L2160) before any assignment. Watchdog only READS `pending_orders.json` ([1640](/root/.hermes/scripts/trade_watchdog.py#L1640)) — no write-back, no cross-cycle leak of the per-cycle flag. |
| A-tests | `analysis/test_pending_machine.py` | ✅ ALL PASS | Ran: `ALL PENDING-MACHINE TESTS PASS` (incl. D2.3 flag plumbing, band predicate, winner-gate defer). |
| B1a | `analysis/test_rip_climax.py` | ✅ 7/7 | divergence, fresh rip, creek, above-peak, z-tier, revert, fail-open — all pass. |
| B1b | `px` vs `price` at call site | ✅ PASS (no NameError) | Call at [:1998](/root/.hermes/scripts/trade_watchdog.py#L1998) `_rip_climax_defer(coin, px)`; `px` assigned unconditionally at [:1739](/root/.hermes/scripts/trade_watchdog.py#L1739) per order with fallbacks [:1754](/root/.hermes/scripts/trade_watchdog.py#L1754)/[:1759](/root/.hermes/scripts/trade_watchdog.py#L1759) and `continue` at [:1761](/root/.hermes/scripts/trade_watchdog.py#L1761) if `px<=0` (non-BTC). Helper signature `(coin, price)`; body references only `price` — no bare `px`. Same loop iteration, always in scope. |
| B1c | fail-open paths | ✅ PASS | no DB/connect fail → `except` → `False,''` ([:1454-1466](/root/.hermes/scripts/trade_watchdog.py#L1454)); `<60` 1m closes / `<5` 1h bars → False; constants-exception → False. |
| B1d | REVERT RIP_RSI_TOP=0 | ✅ PASS | `top=0` → `if not (top and below and zone): return False,''` ([:1449](/root/.hermes/scripts/trade_watchdog.py#L1449)) — all three gates no-op. Test 6 proves it. |
| B1e | sqlite `mode=ro` | ✅ PASS | `file:{db}?mode=ro, uri=True` ([:1454](/root/.hermes/scripts/trade_watchdog.py#L1454)) — never creates a DB (missing file → OperationalError → fail-open). |
| B1f | connection closed all paths | ⚠️ INFO | Success path closes at [:1463](/root/.hermes/scripts/trade_watchdog.py#L1463). Exception between connect and close (e.g. missing table) skips `close()` — but CPython refcount frees the connection at function exit, so no accumulation. Not a leak per cycle in practice. |
| B1g | window arithmetic | ✅ PASS | `rsi[-min(win, len(rsi)):]` ([:1482](/root/.hermes/scripts/trade_watchdog.py#L1482)) and `px_hi` slice both correct when `len < win` (min → whole list). |
| B2 | gate placement: all fill paths converge; btc-ceo excluded | ✅ PASS | Escape ([:1903](/root/.hermes/scripts/trade_watchdog.py#L1903) `_escaped=True` → `_ps="retested"` → fall-through [:1919](/root/.hermes/scripts/trade_watchdog.py#L1919)), E1-confirm fresh cross (`elif crossed`, `_mom is True → pass`), and the continuation/reclaim path all fall through to `if crossed and (btc-auto- or serial)` [:1994](/root/.hermes/scripts/trade_watchdog.py#L1994) → climax gate [:1997-2003](/root/.hermes/scripts/trade_watchdog.py#L1997) BEFORE the stacking/winner/heat gates and before steer emission. Exclusion: `startswith('btc-auto')` at [:1997](/root/.hermes/scripts/trade_watchdog.py#L1997) — `btc-ceo-*` never calls the helper. |
| B3 | defer state neutrality | ✅ PASS | Defer = `log` + `continue` ([:2000-2002](/root/.hermes/scripts/trade_watchdog.py#L2000)); no `state[oid]` write on that path (writes are at 1828/1837 retested-touch, 1948/1972 first_break, 2225 triggered — all other branches). Rung re-evaluates next cycle. |
| B4a | zone peak = last hour's 1m closes | ✅ PASS | `peak = max(closes[-60:])` ([:1500](/root/.hermes/scripts/trade_watchdog.py#L1500)); `closes` ASC after `[::-1]` → last 60 = last hour. |
| B4b | ATR1h DESC TR pairing + window | ❌ **FAIL — MEDIUM** | See F-1 below. |
| C1 | py_compile (watchdog, brain, constants) | ✅ OK | `COMPILE_OK`. |
| C2 | `analysis/test_manual_exit_manager.py` | ✅ 20/20 | `20 passed, 0 failed`. |
| C3 | ONE live run_cycle | ✅ rc=0 | `python3 scripts/auto_trader.py` (contains `run_cycle()`) → rc=0. Exact summary: `enabled=true, mode="live", decision="BRACKET", scores={long:-40, short:0, regime:"CHOP"}, price=61424.51, stats: n=60 wins=26 wr=43.3 pnl_usdt=-0.044 avg_pnl_pct=-0.387 avg_planned_rr=2.95 avg_real_rr=1.79`; shadow_armed=[], live_armed=[]. |
| C4 | Tracebacks in shipped code since 17:00 | ✅ 0 | Scanned `logs/trade-watchdog.log` + `logs/pipeline.log` from first 17:xx timestamp: 0 tracebacks with a `/root/.hermes/scripts/*` frame. (Older/high-count Tracebacks in the watchdog log are agent heredoc experiments — `File "<stdin>"` — not shipped code.) |
| C5 | scope = only my commits' files | ✅ PASS | `git show --stat`: 8d715762 → brain.py, trade_watchdog.py, full-analysis/SKILL.md; bbc6c464 → analysis/test_rip_climax.py, hermes_constants.py, trade_watchdog.py; e2eb2d29 → 2 SKILL.md. Working-tree mods to `ladder_api.py`, `market_phase_gate.py`, bollinger candidates are **NOT touched by these three commits** — parallel work, untouched. |

## Direction-casing proof (A1)

```
brain.py:473  side_type = side_type.lower() if side_type else 'long'
brain.py:474  direction = 'LONG' if side_type == 'long' else 'SHORT'   ← normalized HERE
   ... (band block; no reassignment of direction) ...
brain.py:501  if band_exempt and direction == 'LONG':                  ← uppercase, fires
```

## `px`-scope proof (B1b)

`px` is set at trade_watchdog.py:1739 at the top of each `for order in cfg["orders"]` iteration (1702), with positive-value fallbacks and an early `continue` at 1761 when there is no price. The gate at 1998 is in the same iteration. The helper binds it to its `price` parameter and never names `px`. No NameError path — the first-version bug class is not present.

## DESC-TR pairing assessment (B4b / F-1)

Helper code ([trade_watchdog.py:1502-1505](/root/.hermes/scripts/trade_watchdog.py#L1502)):
```python
h1 = ... ORDER BY ts DESC LIMIT 30      # h1[0] = newest
for i in range(1, len(h1)):
    hi, lo, pc = h1[i][0], h1[i][1], h1[i - 1][2]   # h1[i-1] is the NEWER bar
    trs.append(...)
atr = sum(trs[-14:]) / min(14, len(trs))
```
Two defects:
1. **Prev-close inverted**: for the bar at DESC index `i` (older), its true previous close is `h1[i+1]` (older still); the code pairs it with `h1[i-1]` = the **newer** bar's close. The correct pattern exists in the same file at [:1407-1412](/root/.hermes/scripts/trade_watchdog.py#L1407) (`rows[i+1][3]`, "rows are DESC: rows[i+1] = the prior bar").
2. **Wrong 14-bar slice**: `trs` is appended newest→oldest, so `trs[-14:]` = the **older** 14 of the 30 bars (~16–30h ago), not the last 14h (`trs[:14]` would be the newest).

Measured on live candles.db (BTC, last 30 closed 1h bars, read-only): **shipped ATR = 572.3 vs correct ATR = 784.0 → −27.0%**. Decomposition: inverted pairing alone (newest-14) = 909.8 (+16% vs correct); the stale window slice pulls it down; net −27%. Direction of error: the creek zone `1×ATR1h` is ~27% **narrower** than intended → the gate **under-defers** (fails toward filling). Not a fail-open of the money path, but the protective gate is materially weaker than specified.

## Findings

| ID | Severity | Location | Finding |
|----|----------|----------|---------|
| F-1 | **MEDIUM** | [scripts/trade_watchdog.py:1502-1505](/root/.hermes/scripts/trade_watchdog.py#L1502) | RIP-CLIMAX ATR1h: TR prev-close pairing inverted (`h1[i-1]` = newer bar's close; should be the older bar, cf. correct sibling at :1407-1412) AND `trs[-14:]` selects the OLDER 14 of the 30 DESC bars instead of the newest. Net measured bias −27.0% on live BTC data → creek zone ~27% narrower → gate under-defers. Fix: pair `h1[i+1]` and take the newest 14 (mirror the 15m helper's pattern), then re-run `test_rip_climax.py`. |
| F-2 | LOW | [scripts/trade_watchdog.py:2204](/root/.hermes/scripts/trade_watchdog.py#L2204), data/pending_orders.json | `band_exempt` is a **dual-use key**: a persisted config-level flag (the documented §17 CEO-dictation pre-pass exemption, `auto_trader.py:930` + full-analysis SKILL §17) flows through the payload into brain's ceiling exemption on **any** fill of that order — not only escape-qualified ones. Two live rungs currently carry it (`btc-auto-ladder-long-1795176554` LONG@61750, `btc-auto-ladder-1795401586` SHORT@60750 — notes say "band_exempt (CEO dictation)"). Consequence: the claim "E1-only fills keep the band" holds only for orders without the config key; the SHORT knife is still protected (brain.py:501 exempts LONG only). Recommend renaming one use (e.g. `prepass_exempt`) or documenting the override. |
| F-3 | INFO | [scripts/trade_watchdog.py:1454-1466](/root/.hermes/scripts/trade_watchdog.py#L1454) | `_rip_climax_defer` doesn't `close()` the ro connection if an execute raises between connect and close; CPython refcounting frees it at function exit, so no practical accumulation. Add `finally: con.close()` if paranoid. |

## Regression summary (C)

py_compile OK · pending-machine ALL PASS · rip-climax 7/7 · manual-exit 20/20 · live run_cycle rc=0 (summary above) · 0 shipped-code tracebacks since 17:00 in pipeline/watchdog logs · scope clean (parallel modified files untouched by these commits).

**Overall verdict: PASS with findings.** No HIGH. Ship-blocking candidate is only F-1 (MEDIUM, direction = under-defer, ~27% zone shrink) — recommend the one-line pairing fix + test re-run.
