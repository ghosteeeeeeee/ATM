# bug_hunter verdict — full-analysis v2 PLAN (not code)

Date: 2026-11-14 · Verifier: bug_hunter (fresh-eyes, adversarial)
Target: `/root/.hermes/brain/plans/full-analysis-v2-plan.md` (pass 1 + review pass 2, 126 lines)
Codebase: `/root/.hermes` — read-only verification. Zero production writes
(SELECTs + reads only; one live read-only run of `ai_trader_precheck.py BTC LONG`;
one frozen-cut double-run determinism spot-check). This file is the only write.

Method: plan read FIRST on its own, then every claim checked against source.
Evidence refs are `file:line`.

---

## 1. Verdict table (plan-claim → PASS/FAIL/AMBIGUOUS)

| # | Plan claim (plan lines) | Verdict | Evidence |
|---|---|---|---|
| 1a | `structure_analysis.analyze(token, tf)` yields per-TF state/tags/SH/SL/slope (L14, L112-116) | **AMBIGUOUS** | Signature exists: `structure_analysis.py:110 def analyze(token, tf)` ✓ — but it returns a **formatted display string** (or an error *string*, L113/L117), not structured fields. Structured access = `auto_analysis.structure_summary` (`auto_analysis.py:112`, dict, **no slope**) or string parsing. "Zero re-implementation" is not exact; slope has no dict source. |
| 1b | `adx_atr_analysis.lifecycle(tf, token)` = "rules 1-4 lifecycle + COMBINED" (L15) | **FAIL (rules 1-4)** / PASS (sig) | Sig matches: `adx_atr_analysis.py:110 def lifecycle(tf, token)` ✓. But docstring says "**The three rules**" (L4) and the code implements rules 1/2/3 only — **rule 4 (ADX divergence at a price extreme) has no implementation in any script** (grep `rule 4` across `scripts/*.py` = empty). COMBINED aggregation lives in `main()` (`adx_atr_analysis.py:185-189`), not importable → must be re-derived (trivial, but it is re-implementation). |
| 1c | `auto_analysis.build_decision` reuse (L13) | **PASS w/ 3 notes** | Real sig `auto_analysis.py:217: build_decision(cycle_id, open_positions, cfg, token='BTC')`. (i) **No coin-first wrapper needed** — `token=` kwarg exists; `__main__` shows `build_decision('manual', [], {'mode':'shadow','phase':0})` works with `cfg={}` defaults. (ii) Plan attributes **MTF** to build_decision — wrong: the return dict (L349-362) has no indicator table; MTF needs `auto_analysis.tf_indicators` per TF (exists, L58). (iii) When open positions are passed, `bracket=None` (L333-347, MANAGE_ONLY path) → plan's "**§12 bracket completion**" (L27) has **no source** unless the engine makes a second call with `open_positions=[]` or re-implements the inline bracket logic (L292-332). Plan doesn't address this. Also `get_open_btc` (`auto_trader.py:46`) hardcodes `token='BTC'` — engine must use its own Step-0-style unfiltered query (build_decision filters by token itself at L267 ✓). |
| 1d | `continuum_data.json` fields ema300/z/vel/accel + PIN §14 (L16) | **PASS w/ 2 caveats** | `current` keys include `ema300_position, zscore_val, velocity_val, acceleration_val, trend_quality, linreg_direction` ✓ (PIN = these + CHOP flips, all available). Caveats: (i) **BTC-only at source** — `current.token='BTC'`, history 2,879/2,879 = BTC, `continuum_api.py:29/41` hardcodes `token='BTC'` → Phase-4 `--coin ETH` would show BTC's PIN unless labeled `regime_source`. (ii) **Mid-write reads can throw**: observed a live `JSONDecodeError` while continuum-api was exporting (file rewritten in place); `auto_analysis.chop_flips_24h` swallows it → `(None,None)` → silent **STAND_DOWN**. Engine needs a read-retry. |
| 1e | `ai_trader_precheck` subprocess, PASS/FAIL both sides (L17) | **PASS w/ parsing caveat** | CLI contract `ai_trader_precheck.py:493`: `COIN DIRECTION [CONF] [SOURCE]`. Output: per-check `✅/❌` lines + final line `✅ PASS — safe to pick` / `❌ FAIL — will likely be blocked` (L510-512). **Exit code is ALWAYS 0** (verified live: `BTC LONG` → `❌ FAIL`, `exit=0`) — stdout parsing on the final line is mandatory; emoji parsing is brittle → prefer importing `precheck()` (returns `{pass: bool, checks: [...]}`, L129). Note: CONF matters (SHORT NORMAL/HIGH-vol gate needs conf≥75) — plan doesn't say what conf the advisory passes. Read-only ✓ (no writes/http). |
| 1f | brain PG "(read-only)" (L18) | **AMBIGUOUS** | Step-0 SELECTs exist verbatim (SKILL L76-88) ✓. But **every PG connect in the repo is writer-capable** (`brain.py:146`, `auto_trader.py:38`, SKILL L73); no ro-role / `default_transaction_read_only` mechanism exists anywhere (the `mode=ro` pattern is SQLite-only). "Read-only" is currently discipline, not enforcement; plan should specify an explicit ro session (e.g., `options='-c default_transaction_read_only=on'`) and a Phase-5 assertion. |
| 1g | `pending_orders.json` + state = THE BOOK (L19) | **PASS** | Config = `{"orders":[…]}` (26 orders; keys incl. coin/direction/trigger_price/sl/target/serial) ✓. State = `{id:{status}}` (44 records: 42 fired, 1 error) ✓. Unfired = `status ∉ {fired, error}` per keeper (`auto_trader.py:693`) — note **`'triggered'` counts as unfired** but the watchdog will never fire it (`trade_watchdog.py:1342`) → latent false-READY. Writers use tmp+`os.replace` under EX flock (`auto_trader.py:795-798`, `:323-327`) → lock-free reader is tear-safe ✓. |
| 2a | NEW scanner `shelves(coin)` — 1h/15m hi/lo clusters + rounds (L21) | **PASS (data) / AMBIGUOUS (spec)** | Data: 1h/15m tables present, 30d/90d coverage, `ts`+`is_closed` ✓, forming bars exist as `is_closed=0` rows (5m/15m/1h/4h) ✓. No existing rounds/cluster helper in `scripts/` (grep) → genuinely new code ✓. But **"clusters + rounds" thresholds/tie-breaks/round grid are specified nowhere** (plan or repo). |
| 2b | NEW scanner `divergence(coin)` — §3 type-1 (150 closes, 14-RSI, ±3-bar extremes) (L22) | **AMBIGUOUS → spec gap** | **No §3 type-1 detector exists in the repo.** Closest: `pattern_recognition.py:127 detect_higher_low` (different heuristic, lookback=18, no RSI), and `backtest_v4_short.py:24` imports `_check_rsi_divergence` from `signals.accel_300_v4_short` — **that import is BROKEN** (`ImportError: cannot import name '_rsi'`, verified) → dead script, no usable code. The heredoc algorithm is not persisted anywhere searchable (brain/, logs, skills, automation). The plan captures only the taxonomy ("§3 type-1"), **not the detection algorithm** — Phase 1 cannot reproduce "what the agent has been running" from the plan alone. |
| 2c | NEW scanner `adx_trendline` rule5 via `compute_adx` from backtest_trend_momentum_v3 (L23-25) | **PASS (import) / AMBIGUOUS (algorithm)** | `compute_adx` = `backtest_trend_momentum_v3.py:104`, already imported by `adx_atr_analysis.py:27` (single-source ✓), module import-safe (`__main__` guard L625) ✓. **Line-fit method (which ADX lows, how many points, regression vs 2-point), "touch" tolerance, peak-vs-cross thresholds are not specified** — SKILL rule 5 (L412-426) is example prose with tape numbers, not an algorithm. Same gap family as 2b: must be transcribed from the conversation before coding. |
| 2d | Data blockers (candles.db coverage / is_closed / forming) | **FINDING (HIGH — see F1)** | Coverage fine (1m/5m/15m ≈ 30d, 1h/4h ≈ 90d; 179-185 tokens incl. ETH: `candles_1h` ETH = 2,160 rows ✓). But **`is_closed=1` does NOT mean closed**: empirical — BTC `candles_1m` row for the *current minute* (14:40) has `is_closed=1` (volume partial), and `candles_1h` 14:00 row is `is_closed=1` at 14:40 while the hour is still forming (seeder upsert always writes `is_closed=1`, `price_collector.py:192-196`). Also stale `is_closed=0` rows exist for bars that closed in time (BTC 5m 14:35, vol=0) → "last closed bar" reads can silently skip a bar. |
| 3a | Engine writes only its JSON; no import path into keeper/watchdog execution (L30-31) | **PASS** | Engine deps = auto_analysis / structure_analysis / adx_atr_analysis / precheck(subprocess) — none write orders/stops, none import auto_trader or trade_watchdog (direction is one-way: `trade_watchdog.py:2161` imports `auto_trader.run_cycle`). precheck has no INSERT/dump/http. |
| 3b | API/dash read-only, "the API NEVER derives" (L54-55) | **PASS (as specified)** | Consistent with control-tower precedent (`control_tower_api.py:7` "read-only everywhere except its own output file"). |
| 3c | Pass-2 correction: timer-only + flock belt, watchdog-trigger removed; pass-2 supersedes pass-1 (L81-95, L91-95) | **PASS (current text) / note** | Current file state = timer only + flock ✓; consistent with L54-55. Two provenance nits: (i) pass-2 #3 corrects a pass-1 "optional post-watchdog trigger" **that no longer exists in the pass-1 text** (pass-1 was evidently edited in place) — confusing but final state is unambiguous; (ii) **pass-2 is append-only**: the pass-1 dash section L41-43 still describes the **superseded 2-state READY** ("≥1 unfired per side in reach; RED if empty"), contradicting pass-2 #4's 3-state. A builder implementing from the Dash section alone ships the wrong badge. |
| 3d | Keeper/watchdog remain the only order writers | **PASS** | `pending_orders.json` writers in code = `auto_trader._arm_real_leg` + `_ladder_keeper` only, both reached via `run_cycle` ← trade-watchdog timer (30min) + manual runs; 1-min `pending_order_monitor` executes but goes through trade_watchdog's one-shot state (double-fire-proof). Manual CEO arms are ad-hoc by design. |
| 4 | READY three-state invariant fully specified (pass-2 #4, L96-101) | **AMBIGUOUS — spec holes (see F3)** | (a) "same-side" is stated ✓, but the semantics of an **opposite-side open position** are unstated (long open → is short-side RED allowed?); (b) "within reach (3·ATR1h)" — **which ATR** unstated; must be the structure engine's 1h ATR from `structure_detail` (keeper source: `auto_trader.py:667,714-715`) or engine and keeper disagree; (c) "ITM-wait amber" is given **only in short-side form** ("price at/below the derivable floor") — long mirror ("at/above the ceiling"?), and the exact predicate ("derivable floor" = `sl1h−60`? from which module?) unstated. Cross-side non-overlap: plan names it (L29, L43) but **never says HOW it's verified** (pairwise SL vs every opposite unfired trigger? nearest only? which set?) — SKILL §12 L667-672 states the rule but the plan owns the code. Plan L43 cites "rule13 + invariant" — the invariant lives in **§12** (§13 = stop discipline) — mislabel. |
| 5a | Parity test: "every SKILL.md section/§ ↔ JSON key, both directions", scope = "OUTPUT TEMPLATE's section list (§0–14)" (L58-59, L88-90) | **FAIL as specified (see F2)** | The Output Template has **10 blocks: 0, ⚠CHOP, 1, 1b, 1c, 2, 3, 4, 5, 6** (SKILL L887-940) — there is **no §7–14** in it; §1–14 are Decision Protocol *prose rules*. "§0–14" matches neither list → the test author cannot enumerate the scope. Direction problems: dash-only JSON keys (alerts, data-age, precheck badges, distance-to-trigger, READY) have no template section → JSON→section fails as written; **§4 CONTRARIAN has no plan section** → section→JSON fails. Prose blocks (1b/1c sentences, §6 "who outranks") *can* be string keys, so mapping is possible — the scope statement must be rewritten. |
| 5b | Frozen candle-slice golden fixtures (pass-2 #1, L83-87) | **AMBIGUOUS → F1** | As-of queries are clean structurally (`ts` + `is_closed=1 AND ts<=T`), and a frozen-cut spot-check is deterministic (SKILL S/R swings on 5m BTC, T=2026-11-11: two runs identical: `[73776,73850,74150,74117,74071] / [73808,73697,73766,74038,74035]` ✓). **But** the plan's stated fixtures are "today's heredoc outputs" — those were computed live against *partial* boundary bars, while a later as-of replay reads their *final* row values (rows update in place) → the last bar(s) of the cut will not reproduce. Plan specifies no cut rule (T−1 period? row-level snapshot? regenerate expected values *from* the slice?). Also: **plan contains zero claimed numbers**, so there is nothing to spot-check against (the heredocs themselves are not persisted in the repo). |
| 6a | systemd timer pattern (L52) | **PASS** | Dozens of copyable units: `config/hermes-control-tower-api.timer` + `.service` (Type=oneshot, WorkingDirectory, OnUnitActiveSec) — same shape as ~100 installed `hermes-*.timer` ✓. Nit: **no existing timer uses `After=price-collector`** (grep empty) — harmless systemd feature, no precedent to copy. |
| 6b | nginx location pattern (L53) | **PASS w/ file-selection note** | Live `/etc/nginx/sites-enabled/trading`: 54 `location =` entries, `root /var/www/hermes`, explicit `/data/x.json` aliases with `Content-Type application/json` + `Cache-Control: no-cache` — exact pattern to copy ✓. **But** the repo copy `web/nginx-trading.conf` has **diverged/stale** (missing ~40 locations vs live); the plan doesn't name which file to edit — editing the repo copy has no effect. AGENTS convention = the live file. |
| 6c | 5min engine + 60s page poll (L49, L76) | **AMBIGUOUS — flag (see F4)** | Cadences verified: `pending_order_monitor` runs **every 1 min** (`run_pipeline.py:38` STEPS_EVERY_MIN) → fires land any minute; keeper **arms every 30 min** (hermes-trade-watchdog.timer `OnUnitActiveSec=30min` → `run_cycle` → `_ladder_keeper`). Engine snapshot every 5min + page poll 60s ⇒ **the BOOK panel can be up to ~6 min stale after a fire** (and a just-filled rung can still display READY until the next engine run). Partial mitigation exists in-plan: `data-age` badge (L35) and READY (a) open-position fallback (PG updates at fill). Plan never states the staleness bound or asks the CEO to accept it. |
| 6d | WWW_DATA write path (L31) | **PASS** | Established pattern: root-owned oneshot timers write `/var/www/hermes/data/*.json` (`control_tower_api.py:7`, continuum_api `WWW_DATA`) ✓; HTML copy `web/*.html → /var/www/hermes/` per AGENTS ✓. |
| 7 | Verdict layer = skill rules as code (L26-29) | **PARTIAL (see F5)** | Present: two-part DIRECTION+ENTRY (§1), §12 bracket completion, §14 pin/box, §13 regime-split, ride-cost, box-tax, cross-side + READY. **Omitted vs template/protocol:** §4 CONTRARIAN, §0 two-lines (invalidation/confirmation per open trade), §0 attribution ("who called it" / §9 loop), §8 trust-protocol authority annotation on DIRECTION, §4 forming-candle labeling. **Internal conflict:** box-tax detection sits in the Phase-1 verdict layer (L28) while pass-2 #6 defers its definition to Phase 3 (L110-111) — pass-2 says it supersedes conflicts but this one is left live in both places. |
| 8 | BTC-hardcoded keeper claim (pass-2 #5, L102-106) + other hidden BTC hardcodes | **PASS + extras** | Keeper: `o.get('coin')=='BTC'` ×2 readiness scans (`auto_trader.py:719,762`), arm paths hardcode `'coin':'BTC'` (:743,:778), ids `btc-auto-ladder-*` (:741,:776), docstring "BTC only" (:633). **Other hardcodes Phase 4 hits with `--coin ETH`:** `get_open_btc` `token='BTC'` (:46); `coin_whitelist ['BTC']` fallback (:33); `_arm_real_leg` `'coin':'BTC'` (:303); **continuum is BTC-only end-to-end** (export `token='BTC'`, `continuum_api.py:29/41`) → ETH PIN/ema300/z would silently show BTC data without `regime_source` labeling (build_decision's chop fallback *is* labeled, L224-228 ✓); `pending_order_monitor` entry reads `prices.json['BTC']` only (`pending_order_monitor.py:20-23`) — per-coin firing works downstream (`trade_watchdog.py:1311-1388` per-coin prices + closed-1m fallback) iff the coin is in prices.json. Clean: candles `token` ✓ (ETH present), brain `token` ✓ (Step-0 unfiltered), precheck `COIN` ✓, pending orders carry `coin` ✓ (multi-coin spin-off 2026-11-10). |
| 9a | No API budget usage in reused read paths (L11, L49) | **PASS** | `grep requests/urllib/http` empty in auto_analysis / structure_analysis / adx_atr_analysis / ai_trader_precheck; `signal_schema.price_age_minutes` (precheck path) = local sqlite (`signal_schema.py:3971`). The Binance fetcher in signal_schema (:4795) is off this path. |
| 9b | Alerts specified enough to build (L47-48) | **PARTIAL** | pin ✓ (SKILL §14 L751-771 quantified: ema300 AT + z≈0 + vel/accel≈0 + CHOP; all fields in continuum `current`); keeper-empty ✓ (book logic); structure-flip ✓ (previous engine JSON); ADX events ✓ (lifecycle state strings); fragmentation/ride-cost ✓ method in SKILL Verdict Rules L878-885 (inputs = PG exits + candle open/span low — derivable, unspecified); **box-tax ✗ definition deferred to Phase 3 while listed as Phase-1 deliverable**. |
| 10 | Completeness vs header goals + honed practices | **PARTIAL** | See missed-requirements below. Header goals (always-ready, all TFs/indicators/levels, always-long-AND-short) are covered by MTF+structure+S/R+READY. "Use all the pieces under one roof" is deliberately *not* taken literally (keeper/watchdog stay separate — covered by CEO decision REC 2 ✓). |

---

## 2. Findings (severity + refs)

### HIGH

**F1 — `is_closed=1` includes FORMING bars → golden fixtures + §4 labeling both break.**
The seeder upsert always writes `is_closed=1` (`price_collector.py:185-196`, comment: "is_closed=1 preserves the old column DEFAULT 1 semantics"), including the currently-open candle it fetches mid-period. Empirically verified: BTC `candles_1m` current-minute row (14:40:00 @ 14:40:50) = `is_closed=1` with partial volume; BTC `candles_1h` 14:00 row = `is_closed=1` at 14:40 while the hour is still forming. Consequences:
- Every reused "closed bars only" read (`structure_analysis.load_candles:40`, `adx_atr_analysis._load:39`, `auto_analysis.tf_indicators:65`, SKILL heredoc L798) **actually includes the forming bar** — the plan inherits this silently, and SKILL §4 (L535-543) *mandates* labeling forming reads "(forming)", which the plan's dash never does. Forming status must be derived from `ts + period > now`, not `is_closed`.
- Pass-2 #1's frozen fixture cannot reproduce live heredoc numbers at the cut boundary: the heredoc saw the *partial* boundary bar; the replay reads its *final* row (rows update in place). The golden test as specified fails at the boundary or forces an unstated tolerance.
- Inverse quirk: stale `is_closed=0` rows for bars that closed in time (BTC 5m 14:35 still `is_closed=0`, vol=0 at 14:40) → closed-only reads can miss the newest genuinely-closed bar (up to one extra period stale).
Fix options (plan must pick one): (a) golden cut = `ts <= T − 1 period` + regenerate expected values *from the slice* (not from the live heredoc); (b) row-level fixture snapshot of exactly the rows the heredoc consumed; (c) define forming explicitly as `ts+period>now` everywhere and label it in the dash.

**F2 — Parity test scope is self-contradictory and fails both directions as written.**
Plan L58-59 "every SKILL.md section/§ ↔ JSON key (both directions)" + pass-2 #2 "the OUTPUT TEMPLATE's section list (§0–14)". Reality (SKILL L887-940): the Output Template is **10 blocks (0, CHOP, 1, 1b, 1c, 2, 3, 4, 5, 6)**; §1–14 are Decision Protocol prose. "§0–14" exists in neither list. Direction failures: (i) dash-only keys (alerts ×6, data-age, precheck badges, distance-to-trigger, READY) have no template section; (ii) **§4 CONTRARIAN has no plan section at all** (plan covers only the divergence half of "CONTRARIAN + DIVERGENCE") — `contrarian-analysis` is a named skill component (SKILL L17) and a template block; the plan's parity test would catch it, i.e. **the plan is already known-failing against its own gate**. Rewrite scope as: the 10 template blocks (prose → string keys allowed) + an explicit allowlist of dash-only keys, and add a §4 contrarian section (reuse candidate: `contrarian_monitor.py` is *not* it — that's a shadow-outcome evaluator; the checklist lives in the contrarian-analysis skill).

### MEDIUM

**F3 — READY three-state invariant is underspecified (plan L96-101).**
Holes: (1) opposite-side open position semantics unstated (does an open LONG suppress short-side RED, or is short-RED expected/derivable-keeper behavior?); (2) **reach ATR source unnamed** — must be `structure_detail['1h']['atr']` (keeper's, `auto_trader.py:667,714-715`); if the engine uses `adx_atr_analysis`'s Wilder ATR (300 bars) or `auto_analysis.atr_pct` (percent), badges diverge from keeper behavior; (3) condition (c) given only in short-side form — long mirror + exact predicate ("derivable floor" = `sl1h − 60`, "ceiling" = `sh1h + 60`) unspecified; (4) unfired definition must replicate keeper's `_unfired` (status ∉ {fired, **error**} — `'triggered'` counts as *unfired* while the watchdog will never fire it → READY on a dead rung; decide treatment); (5) cross-side overlap check algorithm (pairwise: every short-rung SL vs every long unfired trigger and vice versa? or nearest-only?) never defined; (6) RED per-side vs global unstated; (7) plan L43 cites "rule13" for an invariant that lives in §12 (mislabel). Additionally pass-1's dash section (L41-43) still states the superseded 2-state rule — the append-only pass-2 leaves a stale spec line that contradicts #4.

**F4 — Book freshness bound unstated (plan L49, L76).**
Fires execute every 1 min (`run_pipeline.py:38`), arms every 30 min (trade-watchdog timer), engine writes every 5 min, page polls 60 s → worst case **~6 min stale book after a fire**, including a just-filled rung showing READY until the next engine run. The `data-age` badge + open-position fallback mitigate, but the plan never states the bound or flags it as a CEO decision (task asks explicitly: acceptable? → flag it; alternative excluded by the plan's own "API NEVER derives" rule).

**F5 — Verdict-layer omissions vs SKILL template/protocol (plan L26-29).**
Missing from the plan's section list: **§4 contrarian** (see F2); **§0 two-lines** — "each trade + the TWO LINES: invalidation / confirmation" (template L894-896, protocol §6 L557-563); **§0 attribution** — recent closed with "who called it" (template L896, protocol §9 L587-594); **§8 authority annotation** — DIRECTION must state "who outranks here per §8 trust protocol" (template L935); **forming labels** (§4, see F1). Also: **box-tax phase conflict** — Phase-1 verdict layer includes box-tax detection (L28) while pass-2 #6 defers its definition to Phase 3 (L110-111): either move detection to Phase 3 or spec the definition now (it is buildable today: 1h in-range% at band extreme + CHOP flips, per §14 L755-757).

**F6 — `build_decision` reuse has two unstated requirements (plan L13).**
(i) MTF table is *not* in its return — pull `tf_indicators` per TF; (ii) with real open positions passed, `bracket=None` (MANAGE_ONLY path) → §12 bracket completion needs a second call with `open_positions=[]` (side-effect-free ✓) or duplication of inline bracket code. Also `open_positions` must be engine-built (dicts with token/entry_price/current_price/direction — `get_open_btc` shape, but that helper is BTC-hardcoded).

**F7 — The three new scanners' algorithms are not in the plan (L20-25).**
Divergence: no §3 type-1 detector anywhere in the repo (broken import in `backtest_v4_short.py` proves the old one died; `pattern_recognition.detect_higher_low` is a different thing). Rule-5 line fit: SKILL prose only. Shelves cluster/round rules: unspecified. The plan says "packaged from the ad-hoc heredocs" — those heredocs are **not persisted** (searched brain/, logs, skills, automation) → Phase 1 starts with a transcription task the plan doesn't schedule, and golden fixtures for these three can't be built from the plan alone.

**F8 — "rules 1-4 lifecycle" is really rules 1-3 (plan L15).**
Rule 4 (ADX divergence at a price extreme → momentum unconfirmed) has no implementation in any script; `lifecycle()` priority chain covers 1/2/3 + running/fading only. Plan must either add "implement rule 4 as new code" to Phase 1 or correct the claim.

**F9 — PG read-only is discipline-only (plan L18).**
No read-only mechanism exists for brain PG (all connects writer-capable; `mode=ro` is SQLite-only). Specify an explicit ro session + Phase-5 assertion ("engine never opens a write transaction"), extending the plan's existing "API never writes" check (L71-72) to PG.

### LOW

- **L1** Pass-2 corrects a pass-1 clause ("optional post-watchdog trigger", L93) that no longer appears in pass-1 text — pass-1 was edited in place; final state is unambiguous (timer-only) but provenance is confusing.
- **L2** Pass-2 #6 says "16 accumulated fired/error records"; actual = **17** of 26 config orders consumed (44 state records, 27 stale ids). Count drifts hourly; housekeeping scope is real (auto-prune >7d is fine).
- **L3** nginx: live file `/etc/nginx/sites-enabled/trading` (regular file, 54 locations) vs stale repo copy `web/nginx-trading.conf` — plan/AGENTS don't warn that editing the repo copy does nothing.
- **L4** No timer currently uses `After=price-collector` — no precedent; harmless.
- **L5** `continuum_data.json` mid-write read raises `JSONDecodeError` (observed live) → `chop_flips_24h` silently returns STAND_DOWN. Engine should retry once on parse error.
- **L6** Precheck subprocess: exit code always 0 (verified) — parse stdout or import `precheck()`; pass CONF for the SHORT gate or expect conf-less FAILs.
- **L7** Price source for distance-to-trigger / data-age never named (prices.json exists, 30s refresh — trivial, just say it).
- **L8** Phase 4 omits the skill's BTC-coupling label (OWN-TREND vs BTC-DRIVEN, SKILL L45-52) and the `regime_source` labeling for continuum/PIN on non-BTC coins (build_decision provides regime_source ✓, plan doesn't mention it).
- **L9** Phase-4 pending firing depends on the coin being present in `prices.json` (`pending_order_monitor.py:20-23` BTC entry point; downstream per-coin works, `trade_watchdog.py:1311+`).
- **L10 (sideways, unrelated to plan)** `backtest_v4_short.py` is dead: `ImportError: cannot import name '_rsi' from signals.accel_300_v4_short` (verified by import). Cleanup candidate — see- something-say-something.

---

## 3. Missed requirements (CEO ask / SKILL output → not in the plan)

1. **§4 CONTRARIAN section** — output-template block + named skill component; plan covers only divergence. (parity test would fail on it)
2. **§0 two-lines per open trade** — invalidation / confirmation for every open position (template L894-896, protocol §6).
3. **§0 attribution of recent closes** — "exit reason + PnL + attribution: who called it" (template L896, protocol §9).
4. **§8 trust-protocol annotation on the verdict** — "who outranks here per regime" (template L935).
5. **Forming-candle labeling** (§4) — and the underlying data can't distinguish forming via `is_closed` (F1): needs `ts+period>now`.
6. **Dedupe-coverage display** — task names it as a honed practice; **no definition exists anywhere in SKILL.md, manual-trade-override, or the plan** (grep empty) — unverifiable from the repo; if it lives only in the conversation, the plan must capture it or drop it explicitly.
7. **Box-tax alert definition timing conflict** — Phase-1 deliverable vs Phase-3 spec (F5); resolve one way.
8. **Golden-fixture cut rule** (F1) and **parity-scope rewrite** (F2) — the plan's two anti-drift mechanisms are both currently unbuildable as written.
9. *(minor)* Key-indicator coverage: BB position, EMA200, multi-window Z (skill Components L20-22 / Key Indicators) absent from the dash's MTF table (RSI/MACD/vol/z only) — template §1 is ambiguous here; confirm intended.
10. *(minor)* Step-0 routing-bug check (`manual_*` vs `rr_engine_*` label mismatch on CEO trades, SKILL L96-114) — plan shows recent exits but no alert for it.

---

## 4. Overall verdict

**NOT build-ready as written — but close.** The architecture, reuse targets, single-writer
discipline, cadence/wiring patterns, and multi-coin hardcode inventory all check out against
the codebase (every signature claim verified; no import path from the engine into order
execution; timer/nginx/WWW_DATA patterns all exist to copy). The blockers are in the plan's
own quality gates and invariant spec, not in feasibility.

**Must change before Phase 1 starts (in order):**
1. **F1** — pick a golden-fixture cut rule and a forming-bar policy (`ts+period>now`),
   amend pass-2 #1 accordingly; add forming labels to the dash spec.
2. **F2** — rewrite the parity scope as the 10 actual output-template blocks + an explicit
   dash-only-key allowlist; add the §4 contrarian section (or explicitly descope it with a
   CEO note).
3. **F3** — READY invariant addendum: opposite-side semantics, reach-ATR source
   (`structure_detail['1h']['atr']`), long-side mirror of (c) with exact predicates,
   unfired definition (incl. `'triggered'`), pairwise overlap algorithm, per-side vs global
   RED; fix the stale pass-1 dash lines (L41-43) and the "rule13" mislabel.
4. **F7** — transcribe the divergence / shelves / rule-5 algorithms verbatim from the
   conversation into the plan (or a linked spec) — they exist nowhere in the repo.
5. **F6 + F8** — note the two build_decision requirements (MTF via tf_indicators;
   bracket-None-when-open) and either implement rule 4 or correct "rules 1-4".
6. **F5 + box-tax conflict** — add the missing template items (two-lines, attribution,
   §8 authority) and resolve box-tax Phase 1 vs 3.

Non-blocking (Phase 2-4): F4 staleness bound as an explicit CEO decision, F9 ro-PG
mechanism, L3 nginx file choice, L5 continuum read-retry, L6 precheck parse choice, L8/L9
Phase-4 labels and prices.json dependency.

*What was run: plan + SKILL (976 lines) read in full; auto_analysis/structure_analysis/
adx_atr_analysis/ai_trader_precheck/auto_trader(_ladder_keeper,_arm_real_leg,get_open_btc)/
trade_watchdog/_monitor/pending_order_monitor/price_collector/continuum_api/continuum_data
inspected; candles.db schema+coverage+forming-bar state SELECTed; precheck run once live
(read-only, exit code verified); frozen-cut determinism double-run; systemd units, nginx
live-vs-repo, git status checked. Zero production writes.*
