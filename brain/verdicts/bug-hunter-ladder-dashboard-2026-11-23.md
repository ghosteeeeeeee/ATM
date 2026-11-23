# bug_hunter verdict — Ladder dashboard full verification (API + page + wiring) 2026-11-23

**Verifier:** bug_hunter (agent-1, delegated by lead) · 2026-11-23 04:20–04:45 UTC
**Scope:** ladder_api.py / web/ladder.html / nginx+systemd wiring / fresh-air deep run / hourly mission / regressions.
**Shipped state pinned at verification time:**
- `web/ladder.html` = HEAD `e974c725` (675 lines, 33 290 B), deployed copy byte-identical (`diff` clean, md5 `3a8be1f4…`).
- `scripts/ladder_api.py` = 453 lines, working-tree clean.
- **Page churn note:** the page was edited 6× during this verification (`da52f8b0` 03:40 → `f260aff2` 03:49 → `705df680` 03:52 → `078f1542` 04:10 → `e974c725` 04:14). All harness results below were re-run against the **current** script (extraction md5 == deployed md5 at run time).
**Harnesses (all in /tmp, SELECTs + mocks only, zero production writes):** `h_ind.py` (independent indicator recompute), `h_err.py` (22 checks: Decimal live-shape + error paths + atomicity), `page_harness.mjs` + `page_tests.js` (61 checks, instrumented DOM/canvas, two-phase reload). **ONE sanctioned live run:** `python3 scripts/auto_trader.py` → rc=0.

---

## Verdict table

| Scope | Verdict | Evidence |
|---|---|---|
| **A** ladder API | **PASS with 1 HIGH + 1 MEDIUM finding** | indicator math exact (after shipped rounding) at k=0, shift-test 0 hits at ±1..3; alignment proven both directions; Decimal walk clean (22/22); atomic write sound; rung filter exact; **(Aiii) forming-15m-bar = LIVE-PROVEN (HIGH, root cause reaches signal readers)**; candles.db failure = crash-stale (MEDIUM) |
| **B** page | **PASS with 1 MEDIUM finding** | 61/61 harness checks green (yRange, x-map+RGAP, rung filter, volume band, EMA chip, 4 idxForTime edges, crosshair, constant-series guard, toggle+reload, priceMode, 180-bar render); div 48/48; `node --check` OK; **zero external URLs**; parity both directions empty; renderRungs price=null throws (MEDIUM) |
| **C** wiring | **PASS with 1 LOW finding** | 3 locations resolve 200 / deny-default `/`→404; units repo==/etc, enabled, last runs rc=0, no failures after 02:48; perms 644×3; AGENTS row in HEAD; **cadence silently changed 60s→15s while descriptions still say 60s (LOW)** |
| **D** fresh-air run | **PASS — ruling = KEEP, no code edits, nothing pending** | verbatim ruling below; deep run edited only brief/decision/report-section/ceo_report (c593907f); parallel dir-matrix commits fully separated |
| **E** hourly mission | **PASS — chain alive and consistent (5 claimed = 5 artifacts)** | sleep armed (fires 05:30:50 UTC), state done=5/24, five committed trading-log artifacts; INFO: orphaned stray sleeps |
| **F** regression | **PASS** | py_compile 7/7; pending-machine ALL groups; manual-exit 20/20; both deep selfchecks PASS; live run_cycle rc=0; 0 Tracebacks (pipeline total, watchdog since 03:00, ladder unit since 02:48); git: zero cross-contamination |

---

## A(ii) — Alignment proof (the worst-class bug check)

**Claim: `bars[-192:]` and `ind arrays[-192:]` index-align, and EMA/cont/z align by bucket. PROVEN.**

Structural: `main()` (ladder_api.py:418–424) builds `_full = candles(312)` (indices 0..311), computes `_ind_full = indicators(_full)` where every array is length 312 with `arr[i] ↔ _full[i]` by construction (rsi/macd/adx/atr all `[None]*n` filled in lockstep — :208–211), then takes `_bars = _full[-192:]` (indices 120..311) and `_ind = v[-len(_bars):]` → indices 120..311. Same slice window on both sides ⇒ aligned by construction; the empirical test below proves the construction holds at runtime.

**Empirical (`/tmp/bh/h_ind.py`):** snapshot ladder.json (ts 1795405904) → re-read the identical 312-bar input from candles.db (`ts <= snap_last`, read-only) → **independent from-scratch implementation** (own structure: array-of-TR/DM first, then smoothing; Wilder RSI/ATR/ADX, seed-at-first-close MACD, SMA-seeded EMA200) → element-wise diff against the shipped arrays, matched **by absolute bar ts** (not by position), plus a ±3-bar shift test.

| series | n | mismatches after shipped rounding | max abs diff (pre-round) | shift-test hits shipped[i]==ref[i+k] for k=−3..+3 |
|---|---|---|---|---|
| rsi (3dp) | 192 | **1** (index 191 only — see drift note) | 7.18e-4 | **k=0: 191/192; every k≠0: 0** |
| macd (2dp) | 192 | **1** (index 191 only) | 1.944 (index191) | **k=0: 191/192; every k≠0: 0** |
| adx (3dp) | 192 | **0** | 4.98e-4 | **k=0: 192/192; k≠0: 0** |
| atr (2dp) | 192 | **0** | 4.97e-3 | **k=0: 192/192; k≠0: 0** |
| ema200 (2dp) | 192 | **1** (index 191 only) | 0.243 (index191) | **k=0: 191/192; k≠0: 0** |
| cont / z (3dp) | 192 | **1 / 1** (index 191 only) | bucket recompute | **k=0: 191/192; k≠0: 0** |

- **Conventions:** shipped is Wilder for RSI/ATR/ADX (self-consistent; my ref used the same Wilder smoothing and matched exactly after the shipped's own rounding), MACD seeded at first close (both conventions — seed-at-first and TA-lib SMA-seed — differ from shipped by the same ≤0.005 rounding noise at displayed bars; seed effect is nil after 120 warmup bars), EMA200 = SMA200 seed + k=2/201 (identical window, exact). RSI zero-loss branch differs (shipped :227 uses ratio 100 → 99.01 when al=0; mine → 100) — unreachable on BTC 15m data (needs 14 straight up-bars); INFO only.
- **The single mismatch at index 191 (last bar) is the Aiii fingerprint, not an alignment error:** the last bar's row was *mutated after the snapshot* (stale-partial → final; see Aiii). rsi/macd/ema200/cont/z depend on close/ticks → drift; **atr/adx (high/low/prev-close based) still matched exactly** — exactly the signature of a data change at one bar, not a shift. A shift would mismatch everywhere (and indeed every k≠0 scored 0).
- **Warmup sufficiency:** a 600-bar-window cross-check (different seed point) converged to the shipped values (rsi ≤3.4e-3 at the very first displayed bar, decaying to rounding; macd ≤0.09 → 0; adx ≤0.042; atr 15/192 at rounding boundary) — the 120-bar pad (:419) absorbs all four warmups.
- **EMA200 bucket alignment:** `by_ts[ts − ts%900]` vs `b['t']` — 192/192 non-null ⇒ every chart ts is 900-aligned (verified independently: `ts%900==0` for the last 50 rows) and every bucket hit. **cont/z:** 191/192 bucket-exact (last-bar entry mutated post-snapshot — continuum history rewrites, not an alignment bug).
- **cur vs array:** rsi/macd/adx/atr `cur` == array last (to the shown precision) ✓; `cur.cont`/`cur.z` are the **live** newest tick (may sit in the forming bucket) while the array is closed-bar-aligned — by design, chip leads the line. INFO.

---

## A(iii) — The forming-15m-bar call: **CONFIRMED LIVE (HIGH, root cause)**

**Answer: YES — the seeder marks the CURRENT 15m bar `is_closed=1`, and today it fed the chart a bar presented as closed while (a) forming and (b) later ended-but-stale.**

**Live evidence chain (today, all SELECTs/reads):**
1. `03:41:11` — BTC row `ts=1795404600` (window 03:30–03:45) = `is_closed=0`, volume 0.0 (aggregator dev row, price_collector.py:785–789).
2. Between `03:41:11` and `03:45:00` a slow-seeder fetch ran (`[candle_seed] Seeded 10/10` every ~45 s; BTC rotates every ~13 min) and wrote **mid-window kline data with `is_closed=1`** (`_store_candles`, price_collector.py:191–197: upsert sets `is_closed=1` unconditionally; the dev row's volume=0 satisfies the `WHERE volume=0` guard). The aggregator's dev-writer then skips it forever (`if exists[0]==1: continue`, :783–784) and its closed-fill never overwrites (guard `WHERE table.volume = 0`, :718–726 — volume≠0).
3. `03:51:44` — **the ladder feed's LAST candle** was that bar: `{'t':1795404600, o:61437.73, h:61695.52, l:61248.46, c:61320.31, v:364.95}` — window had **ended at 03:45**, yet the stored close/volume were a pre-close snapshot. DB later (03:56 fetch) shows the truth: `c:61295.91, v:401.29`. The bar's close moved **−$24.40** and volume +36.3 after the feed had presented it as closed.
4. Runs at 03:42–03:44 (before 03:45) also included it as the last "closed" candle **while still forming** (partial OHLC + partial volume).

**Impact:** (i) the chart's final candle has wrong OHLC/volume — partial during the forming window, then stale-frozen until the next BTC fetch (≤~13 min after close); (ii) **the last indicator values are computed on that bar** (rsi/macd/atr/ema200/cont/z all shifted at index 191 — measured in Aii); (iii) the bar **repaints** (close −24.4, vol +36.3 observed); (iv) `closes_per_day`/windows unaffected (close_time-based) but any consumer reading "latest closed 15m close" gets a lie.

**Root cause (one line):** `price_collector._store_candles` (price_collector.py:191–197) writes `is_closed=1` for every fetched kline with **no `ts < floor(now/900)` guard** — same class as F-2 (bug-hunter-major-break-redesign-2026-11-22.md:336), which fixed only the **confirm read** (`trade_watchdog.py:1475–1478`, `ts < floor(now/60)` — closed at :453), never the **writer**. Secondary unguarded writer: `fetch_hl_volume.store_candles` (fetch_hl_volume.py:141–145) INSERTs without the `is_closed` column → column `DEFAULT 1` (price_collector.py:83) also closes the forming bar.

**One-line fix (as briefed):** in `_store_candles`, `is_closed = 1 if cd['ts'] < (int(time.time()) // TF_SEC) * TF_SEC else 0` (TF per interval; mirror for fetch_hl_volume's INSERT). Ladder-side hardening (defense only, not root): `AND ts < (strftime('%s','now')/900)*900` in ladder_api.py:41–42.

**Severity: HIGH (root cause), because it is not ladder-local.** Unguarded `is_closed=1 … ORDER BY ts DESC` readers feeding **signal math**:
- `signal_compactor.py:1344,1566,1602,3295,3334,3483,3634` — latest-close velocity/SMA (`_bgc_vel = closes[-1] vs closes[-6]`) on a partial/stale bar;
- `scripts/signals/mtf_macd.py:103–107`, `hzscore.py:90–94`, `accel_300_v2/v3_long.py`, `ema300_breakthrough.py`, `range_breakout_short.py`, `squeeze_breakout.py` — 0 ts-guards (grep).
Guarded exceptions: `trade_watchdog.py:1475–1478` (1m confirm, F-2) and `dir_matrix.py:225–236` — whose own docstring already states *"the API seeder marks the FORMING candle is_closed=1 (review HIGH-1)"* (the parallel session hit the same class and defended its own fetch). Ladder-only impact alone would be MEDIUM; the shared root puts it at HIGH.

---

## A(iv) — PG Decimal/bytes/DateTime walk: **CLEAN (22/22)**

Live-shaped mock (`psycopg2`-shaped rows with `Decimal` everywhere, `datetime` open/close, `bytes` fees, `None` fees/exit) through `stats()` **and** `chart_trades()` → `json.dumps` OK, no `error` key:
- open rows float-converted: `[{id:17059, entry:62000.7, sl:62500.25, pnl_pct:-0.77, amt:11.2}]` ✓ (the `float(o[5] or 0)` fix at ladder_api.py:191 holds);
- `recent`: `ts` isoformat str, `ts_epoch` float, `mfe` float, `hold` int ✓; `_net_of` handles fees-blob str **and** bytes **and** None (falls back to `pnl`) ✓; `n/net/wr/windows/weighted/mfe_split` all plain numbers ✓;
- `chart_trades`: open row emits `exit:null, close_ts:null`, `open_ts` float ✓.
- **No other unconverted Decimal/bytes/DateTime found** — every field of the feed was walked (rungs come from JSON; candles are float()-ed at :47–49; ema200/cont/z rounded floats).
- **Historical proof the class was real:** journal shows ladder-api **5 crash events 02:43:30–02:47:09** (`TypeError: Object of type Decimal is not JSON serializable` at `json.dump`, exactly the open-rows path) right after #17058 opened 02:42:36 → fixed by `0eac6b3c` 02:47 → **0 failures since 02:48**.

## A(v) — Error paths & atomicity

| failure | behavior | verdict |
|---|---|---|
| **candles.db missing/corrupt** | `candles()` (ladder_api.py:36–46) raises `sqlite3.OperationalError` → `main()` **crashes** → no write → **stale JSON** (harness-confirmed: raise + OUT untouched) | **MEDIUM finding** (crash, not degraded) |
| PG down | `stats()` catches → `{"error": …}`, feed written, candles/rungs intact | degraded-but-valid ✓ |
| continuum file missing | caught (:407–408) → cont/z null + `cur.cont:null`, feed written | degraded-but-valid ✓ |
| prices.json missing | `live_price()` → `price:null`, feed written | degraded-but-valid ✓ (but see B — page then throws in renderRungs) |
| `indicators()` n<32 | early return **without `cur`** (:213) → `main()` :437 `feed['ind']['cur']['cont']` → KeyError → crash | LOW (unreachable: 8 639 closed bars exist) |
| **atomic write** | `tmp = OUT + '.tmp'` (:443) = **same directory → same filesystem**; `json.dump` completes **before** `os.replace` (:444–446) — a crash mid-dump leaves a partial `.tmp`, `OUT` untouched (simulated ✓); no tmp residue on success ✓; final mode 644 (umask) | PASS |

## A(vi) — Trades window (48 h) vs chart (48 h): **client-safe**

- API: `open_time > now−48h` (:305), no close-time filter. Chart: 192×15 m, first bar ∈ (now−48 h 15 m, now−47 h 45 m].
- **close after the last bar:** `idxForTime` (ladder.html:456–460) loops to the last index → **clamped** to bar 191 ✓ (harness: `last+99999 → 191`).
- **trade older than the first bar:** returns −1 → `drawTrades` **drops** it (`if(i1<0) return;` :465) — no crash, marker silently absent. Structurally reachable for trades opened in the ≤15 min before the first bar (window boundary mismatch); **current feed: 0 trades outside [first, last]** (min open = first+547 s; max close < last bar end) ✓.
- open trade (no close): entry marker only, no connector/exit arc ✓; entry+exit same bar: same index, both drawn ✓ — all four edges harness-verified (19 entries/18 arcs with the injected set).

## A(vii) — Rung consumed-filter: **correct vs monitor taxonomy**

- ladder_api.py:63–65: default `'UNFIRED'`, excludes exactly `('fired','error')`.
- Monitor's written statuses (trade_watchdog.py): `triggered` :2046, `retested` :1723/1732, `first_break` :1843/1867, terminal `fired|rejected|error` :2197–2206, `error` :2255. `rejected` is **retryable** by design (:2177–2186 comment: "Status 'rejected' keeps the rung alive") → correctly **included** ✓.
- Shipped snapshot: 82 BTC orders − 58 consumed = **24 expected = 24 in feed, id-set exact, no consumed leaked, sorted by trig** ✓ (states: 21 UNFIRED + 3 retested).
- INFO: transient `triggered` (in-flight execution) is included (not in the brief's enumerated lists — semantically "not yet consumed", consistent) but renders as `unfired` (ladder.html:271 else-branch) — cosmetic mislabel; `first_break`/`rejected` also get the dim `unfired` CSS class (text correct).

---

## Scope B — page verification (harness: 61 checks, 2 phases, 0 fail)

| check | result |
|---|---|
| yRange auto vs full | auto = candles ±8 % pad only; full includes far rung trig + SLs ✓ |
| candle x-mapping (RGAP=105) | 8/8 time-grid x positions = `8+(i+0.5)·(1000−8−74−105)/192` exactly ✓ (both charts + both crosshair handlers use the same step) |
| rung y-mapping + in-range filter | auto: 9/9 in-range chips, far rung filtered (injected trig=chi+5000 absent) ✓; full: 26/26 ✓; SL ticks range-guarded ✓ |
| volume band | bars = count of non-zero-v volumes (zero-vol skipped) ✓; max height == `vband=(440−32)·0.20=81.6` (vmax-scaled) ✓; bars end exactly at `H−P.b` ✓ |
| EMA200 | series stroked + chip `EMA200` at `dataR+6=827` ✓; array 192/192 non-null ✓ |
| idxForTime edges | first-bar→0, beyond-window→191 (clamp), older-than-first→−1 (drop), same-bar entry/exit→same index — no throw ✓; marker counts 19/18 as predicted ✓ |
| crosshair sync | main→ind: vertical line at x(idx) + hoverIdx set ✓; ind→main: redraw happens but **main draw() renders no hover line** (asymmetric; `draw` body contains no `hoverIdx`) → LOW |
| constant series guard | `hi===lo` constant rsi → skipped, no stroke, no div-by-zero ✓; all-null cont skipped ✓; empty `z=[]` no-throw ✓ |
| toggle persistence | `toggleInd` → localStorage round-trip ✓; **reload phase**: `rsi:false` restored, **new key `z` (absent from stored payload) defaults visible**, unknown `bogus_key` ignored** ✓ |
| IND_KEYS ↔ feed parity | see table below — both directions empty ✓ |
| priceMode (CANDLES/LINE) | default candles (192 bodies) → btn-line: 0 bodies + white close-line stroked + storage `ladder_price_mode` ✓ → btn-candles back ✓ → **reload restores LINE** ✓ |
| non-192 counts | renders with 180 bars (no hardcoded bar count anywhere in the page — all `c.length`) ✓ |
| div balance / syntax | `<div>` 48/48, all other tags balanced ✓; `node --check` OK ✓ |

### B(v) — IND_KEYS ↔ feed-key parity table (both directions)

| direction | keys | result |
|---|---|---|
| feed `ind` keys (minus `cur`) | `rsi, macd, adx, atr, cont, z` | — |
| `IND_KEYS` (ladder.html:181) | `rsi, macd, adx, atr, cont, z` | — |
| **feed key missing from IND_KEYS** (would be INVISIBLE on the pane) | **∅** | PASS |
| **IND_KEYS key missing from feed** (permanent gap) | **∅** | PASS |
| `ema200` | top-level (drawn on the price chart, not the ind pane) — correctly not in IND_KEYS ✓ | PASS |
| `cur` | currents dict, not a series — correctly not in IND_KEYS ✓ | PASS |

### B(ii) LOCAL claim: **CONFIRMED zero external references**

`grep -E 'https?://|src=|@import|cdn|fonts\.|url\(|href="//|src="//'` over `web/ladder.html` → **NONE**; same over `scripts/ladder_api.py` (`requests|urllib|urlopen|http`) → **NONE** (stdlib + local DBs only). `'JetBrains Mono'` is a font-*family* name only (falls back to `ui-monospace`) — no @font-face/import.
**B(iii)** favicon: `<link rel="icon" type="image/png" href="/btc-favicon.png">` (ladder.html:7) → served 200, file `/var/www/hermes/btc-favicon.png` 644, in repo (`web/btc-favicon.png` tracked) ✓.

---

## Scope C — wiring

- **nginx** (`/etc/nginx/sites-enabled/trading`): `location = /ladder.html` (:18), `= /btc-favicon.png` (:19), `= /data/ladder.json` (:20) — all **exact-match** (precedence over `location /`), deny-default `location / { return 404; }` (:151). Live: **200 / 200 / 200**, `/` → **404** ✓. `nginx -t` OK.
- **timer**: `config/hermes-ladder-api.{service,timer}` tracked in git **and** byte-identical to `/etc/systemd/system/` (`diff` clean for both) ✓; `enabled` + `active` ✓; last runs `Deactivated successfully` (rc=0), **0 unit failures since 02:48** ✓.
- **cadence — FINDING (LOW):** repo `/etc` both now say `OnUnitActiveSec=**15sec**` (changed in `f260aff2` 03:49 — an unrelated "right-edge gap + badge fix" commit, not mentioned in its message; `/etc` mtime 03:47:51, daemon-reloaded; live triggers confirmed **15 s apart** at 04:33). But the unit **Description still says "every 60s"**, `AGENTS.md:281` says "60s API", `ladder_api.py:10` says "(60s)". The brief's expected 60 s cadence is no longer what ships.
- **perms:** page 644, icon 644, JSON 644 (fresh, age 15.6 s at check) ✓ — the 644 lesson holds.
- **AGENTS.md** Ladder row present at :281 **and committed** (`git show HEAD:AGENTS.md` matches) ✓.

---

## Scope D — fresh-air deep run `20261123T002156Z`

### Ruling (verbatim from `automation/ceo/checkpoints/20261123T002156Z-report-section.md`)

> **Decision: (a) KEEP the fresh-air continuation rungs as-is.** No code change, no edit dispatch — re-evaluate at the scheduled 2026-11-29 7-day gate.

Supporting evidence lines (verbatim): *"True `entry_style=continuation` class = n=2, both winners: #17007 +$0.20 (mfe_exit +8.6%), #17015 +$0.09 (HL_CLOSED) — net **+$0.29**. The brief misattributed #17004 (−$0.15…) and #17008 (−$0.12…) to this class"*; *"**Zero fills yet under E1** … deciding (b)/(c) now = deciding on zero post-fix data"*; *"**Work items dispatched: None** — option (a) is a no-code decision; dispatching edits would reverse yesterday's ruling without evidence."*; metric checkpoint table targets the 2026-11-29 gate (continuation fills under E1, never-ran share <15 %, never-ran net ≥ −$0.50, (c) counterfactual tagging).

### Edits / attribution
- Deep run wrote **only**: `automation/ceo/checkpoints/20261123T002156Z-decision.md` (00:35) + `…-report-section.md` (00:36) (both under `checkpoints/` — **gitignored**, `.gitignore:49`) and the lead's commit **`c593907f` 00:37** touching exactly `automation/ceo/2026-11-23_fresh-air-rungs-decision.md` + `automation/ceo/ceo_report.md`. **No code files** (mtime scan 00:20–00:40 over scripts/web/config/brain: only those 3 docs).
- **Parallel session separated:** dir-matrix work = `beebe19c` 00:57 (spec), `664076ec` 03:01 (review), `7dacab98` 03:23 (`scripts/dir_matrix.py` + result-1), `eabb973a` 03:44 (result-3) — **none touch my dashboard set** (scan: zero hits for ladder_api/ladder.html/continuum_api/favicon/config/AGENTS). My set: the `dashboards: ladder …` commits (`5bd77e66, d6f7432a, 465c6792, 2a3bf1cf, 05b363c6, 0eac6b3c, 1fbf8020, 7aca79ff, 333f6ad0, da52f8b0, f260aff2, 705df680, 078f1542, e974c725`) + `config/hermes-ladder-api.*` + AGENTS row. `b675ab52` (continuum_score signals) is a third workstream — also no overlap. **No cross-contamination either direction.**
- **Implemented or pending?** Fully implemented *as a decision* — option (a) is a no-code ruling, so there is nothing to ship; the only open item is the **2026-11-29 re-evaluation** (scheduled in the state file's `scheduled_briefs`) plus the deep run's three logged sideways finds (watchdog:1711 comment inaccuracy, margin-heat fold-in B not yet exercised, disk 88 % WARN). **Not pending on the lead.**

---

## Scope E — hourly check-in mission: **CHAIN ALIVE, state consistent**

- **Sleep armed:** yes — `bash -c "…update state…; sleep 3600 && echo HOURLY CHECK-IN DUE…"` PID 1368364/1368376, started **04:30:50 UTC**, child of `node /usr/bin/dsh web` (the live session) → fires **05:30:50**; `next_due_epoch=1795411851` (+3 000 s from check) — **in the future, consistent with the armed sleep** ✓. Re-arm after each check-in confirmed (state write + new sleep in the same job).
- **done vs artifacts:** `done=5/24` ↔ **5 committed analysis artifacts**: `1afe886c` 23:55, `950878f9` 00:55, `c3bec795` 01:57, `ea1e20e0` 02:58, `f93e432a` 03:54/03:58 (message prefix "Analysis: hourly trade log" — the reason a naive `--grep="hourly analysis"` misses it). Each adds the ~32-line block to `automation/trading_log.md` ✓. When the brief was written (done=4): **4 artifacts existed for 4 check-ins** — consistent, no phantom count.
- Honest caveats: (i) the 03:26 wake was **brief-only** (fill-quality deep launch; `done` correctly stayed 4 — it did not claim an analysis); (ii) the 04:26/04:30 wake wrote state (`done=5`, `agent_7_pending` dispatch) **without a 6th trading-log entry** — it counted/acknowledged the 03:58 artifact; if the protocol requires an entry *every* wake, that wake logged a dispatch instead (no uncommitted `trading_log.md` changes → no lost artifact); (iii) INFO: two orphaned `sleep 3600` strays (started 03:34:55, reparented to `cups-browsed`, dead stdout) — they cannot deliver a wake, no double-check-in risk, and have exited.

---

## Scope F — regression

| item | result |
|---|---|
| py_compile ladder_api, continuum_api, trade_watchdog, auto_trader, brain, position_manager, hyperliquid_exchange | **7/7 OK** |
| `analysis/test_pending_machine.py` (all groups) | **ALL PENDING-MACHINE TESTS PASS**, rc=0 (groups through 11 incl. D3 heat + E1 helper) |
| `analysis/test_manual_exit_manager.py` | **20 passed, 0 failed**, rc=0 |
| `automation/ceo/checkpoints/selfcheck_20261122T220223Z_{e1,exit}.py` | **both PASS** rc=0 ("SELFCHECK PASS: E1 momentum gate + D3 heat margin"; "RESULT: PASS") |
| **ONE live run_cycle** `python3 scripts/auto_trader.py` | **rc=0**. Exact summary: `enabled:true, mode:live, decision:"BRACKET", scores{long:25, short:−15, regime:"CHOP"}, price:61086.0, shadow_armed:[], live_armed:[], armed_detail:[], hypotheticals:0, stats{n:58, wins:26, wr:44.8, pnl_usdt:0.775, avg_pnl_pct:0.219, avg_planned_rr:2.95, avg_real_rr:1.79}, by_regime CHOP n=58 +0.775, by_direction long 25/36.0 % +0.064 · short 33/51.5 % +0.711, recent_decisions 6× (latest 04:35:33 BRACKET @61086), self_tuning_log size_mult 0.55→0.61 (old events), no self-tune this cycle` |
| **Book at run time** | **open trades: 0** (PG `status='open'` → 0 rows). The #17058-class rows are now all closed: **#17058** SHORT ai-trader-pending 02:42:36→03:05:38, `manual_sl_hit`, −$0.20; **#17059** LONG 03:23:21→**04:30:56**, `manual_sl_hit`, −$0.11 (closed 4 min before the run — that's why `stats.open=[]` in the live feed). Armed rung book: 82 BTC orders, 58 consumed, **24 planned rungs** on the ladder. |
| Tracebacks since 03:00 | `pipeline.log`: **0** (file total 0); `trade-watchdog.log`: **0**; `hermes-ladder-api.service` journal since 03:00: **0** (unit's last failure 02:47:09, pre-fix) |
| git scope | my 7 files all tracked at HEAD; **zero parallel commits touching them; zero of mine touching theirs** (per-commit name scan) |

---

## Findings register

| # | Sev | Where | What |
|---|---|---|---|
| F-1 | **HIGH** | `price_collector.py:191–197` (+`fetch_hl_volume.py:141–145`, `price_collector.py:783–784`) | **Forming 15m bar marked `is_closed=1`** — live-proven today (Aiii): feed last candle presented closed while forming and again ended-with-stale-OHLC (c 61320.31→61295.91, v 364.95→401.29). Ladder impact = wrong last candle + skewed last indicators + repaint; **root cause is shared**: unguarded `is_closed=1 … ORDER BY ts DESC` readers in `signal_compactor.py:1344,1566,1602,3295,3334,3483,3634` and ≥6 `scripts/signals/*` files feed signal math on a partial/stale bar. F-2 fixed only the confirm **read** (`trade_watchdog.py:1475–1478`). **Fix:** `is_closed = 1 if ts < floor(now/TF)` in `_store_candles` (+ mirror in fetch_hl_volume); ladder hardening `AND ts < floor(now/900)` at `ladder_api.py:41`. |
| F-2 | **MEDIUM** | `ladder_api.py:36–46, 444–446` | candles.db failure → `main()` raises → **stale JSON** (crash not degraded). Reachable class, historically realized: 5 crash events 02:43:30–02:47:09 (Decimal, same crash-then-stale pattern) until `0eac6b3c`. PG/continuum/prices failures degrade correctly. **Fix:** wrap `main()` body in try/except → log + skip write (or emit last-known-good + `degraded` flag). |
| F-3 | **MEDIUM** | `ladder.html:268,273` (renderRungs) | `DATA.price=null` **and** rungs>0 → `dist.toFixed` TypeError → `load()`'s catch aborts the whole render pipeline → chart/stats freeze + "feed ERROR" for as long as prices.json is down. Harness-proven (`price_null_render: THROWS`). **Fix:** `` `${dist==null?'—':(dist>=0?'+':'')+dist.toFixed(2)+'%'}` ``. |
| F-4 | **LOW** | `config/hermes-ladder-api.timer:6` (= `/etc`, reloaded) | Cadence silently changed **60s→15s** inside unrelated commit `f260aff2`; live triggers confirmed 15 s. Unit Description ("every 60s"), `AGENTS.md:281` ("60s API"), `ladder_api.py:10` ("(60s)") all stale; commit message doesn't mention it. Load is fine (page polls 30 s); docs/description must be reconciled (or the change ratified). |
| F-5 | **LOW** | `ladder_api.py:213` vs `:437` | `indicators()` n<32 early-return omits `cur` → `main()` KeyError → crash. Unreachable today (8 639 bars) — add `'cur': {...None}` to the early return. |
| F-6 | **LOW** | `ladder.html:308–445` (draw) vs `:624` | Crosshair sync is one-way visually: hovering the ind chart calls `draw()` but `draw()` never reads `hoverIdx` → **main chart shows no hover line** (redraw-only). |
| F-7 | **LOW** | `ladder.html:456–465` + `ladder_api.py:305` | `idxForTime` **drops** (returns −1) trades older than the first bar instead of clamping to 0 — structurally possible for trades opened in the ≤15 min before the chart window start (window-boundary mismatch); no crash, marker silently absent. Current feed: none out of window. |
| F-8 | **INFO** | `ladder.html:433` | Auto-range hides the live price line when price exits the 8 %-padded candle range — more likely once F-1 is fixed (last bar then up to 15 min stale). |
| F-9 | INFO | `ladder_api.py:63–65`, `trade_watchdog.py:2046`, `ladder.html:271` | Transient `triggered` state included by the filter and rendered as `unfired`; default `'UNFIRED'` uppercase vs monitor lowercase (handled by else-branch). Taxonomy otherwise exact (fired/error out; rejected/first_break/retested/unfired in). |
| F-10 | INFO | `ladder_api.py:6,35,292` | Stale docstrings: "last 180", `candles(n=180)` unused default, "180×15m (45h)" — actual `_N=192` / 48 h. No code impact (page has zero hardcoded bar counts — 180-bar render tested). |
| F-11 | INFO | hourly chain | Orphaned stray `sleep 3600`s (03:34:55, reparented to cups-browsed, dead stdout) — no double-delivery; only the dsh-web-child chain is live. |
| F-12 | INFO | `ladder.html:243` | `set('s-wr', …, s.net)` colors the **win-rate** cell by **net** — likely intentional, flagging in case it was meant to be `s.wr`. |

---

## Overall verdict

**PASS WITH FINDINGS — ship-worthy as a dashboard; one HIGH (F-1) belongs to the seeder, not the ladder, and should be fixed at the writer before the next bug_hunter pass.**

Everything the brief asked to prove, proved: **(Aii)** alignment proven (exact after shipped rounding at k=0, zero shift hits at ±1..3, EMA/cont/z bucket-aligned, warmup sufficient); **(Aiii)** the forming-15m bar **is** presented as closed — live-proven today with a named one-line fix and a severity raised to HIGH because the same lie feeds signal_compactor and 6 signal files; **(Aiv)** no unconverted Decimal/bytes/DateTime anywhere (live-shaped 22/22) — and the historical 02:43 crash confirms the fixed path was the real one; **(Av)** atomic write sound, one crash path (candles.db) named; **(Avi)** client-safe edges; **(Avii)** rung filter exact; **(B)** 61/61 harness checks, parity table empty both directions, LOCAL claim confirmed, favicon/div/`node --check` clean; **(C)** all three locations resolve, units synced, perms 644 — with the 60→15 s silent cadence change called out; **(D)** fresh-air ruling = **KEEP as-is, no code, nothing pending on the lead**; **(E)** mission chain alive, 5 = 5 consistent; **(F)** all suites green, one live run_cycle rc=0, logs clean, git scope uncontaminated.

**Recommended order:** F-1 (seeder `is_closed` guard — one line, fixes ladder + signal readers together) → F-2 (crash→degraded) → F-3 (price=null render) → F-4 docs/cadence reconcile → F-5..F-12 as touch-ups.

---

# ACCEPTANCE ROUND — fix commit `b2a0be36` (6 files) · verified 2026-11-23 05:03–05:40 UTC

**Verdict: CONDITIONAL PASS — the 15m core of F-1 and F-2/F-3/F-4/F-5/F-6/F-7/F-9 are verified closed, but the F-1 sites deviate from the prescription in three ways (DELTA A/B/C) plus one cosmetic (D). NOT appending a clean PASS: three deltas need one more small fix.**

## What is verified closed (all independently re-run, not taken on trust)

| finding | evidence |
|---|---|
| **F-1 site (a)** `price_collector._store_candles` | per-row flag `1 if r[1] < int(time.time()//900)*900 else 0` bound as the 8th parameter; `ON CONFLICT … SET … is_closed=excluded.is_closed` (`price_collector.py:191–207`). Controlled tmp-DB tests (`/tmp/bh/h_f1.py`): forming bar → **flag0 + real volume kept**; completed-bar fetch → **flag1**; stale flag0 on a closed row → **corrected to 1 on re-fetch** ✓ |
| **F-1 site (b)** `fetch_hl_volume.store_candles` | explicit `is_closed` column in the INSERT (no more column-`DEFAULT 1`), same floor rule (`fetch_hl_volume.py:138–149`) ✓ |
| **F-1 site (c)** ladder read belt | `candles()` now `AND ts < int(time.time()//900)*900` (`ladder_api.py:40–47`); live feed's last bar genuinely pre-floor (checked at 05:15 and 05:36) ✓ |
| **one live tick — honest flag** | samples 05:11 / 05:36: BTC forming 15m bar `is_closed=0`; **ANY-token forming bars flagged closed right now: 15m = 0, 1m = 0**; completed bars flip to 1 (04:45 flag0 at 05:11 → flag1 by 05:15 via the close+15min fill). The F-1 lie is gone for the current window, all tokens ✓ |
| **dev-writer flag consistency** | `_aggregate_tf`'s "window already closed" skip (`price_collector.py:783–784`) leaves the forming bar flag0 in the controlled test ✓ — but it wipes **volume** (DELTA C below) |
| **F-2** | `candles()` wrapped → `_feed_err` + `error` field + `candles=[]` + `ind.cur` present (`ladder_api.py:426–434`); `/tmp/bh/h_err.py` **24/24** (degraded feed: `error='candles:OperationalError'`, candles=[], cur all-None, stats+rungs intact); **degraded page end-to-end**: load() no-throw, badge stays an age (not feed ERROR), rungs table + stats + price placeholder all render (page harness) ✓ |
| **F-3** | `dist==null?'—':…` (`ladder.html:274`) — harness: `renderRungs(price=null)` no throw, em-dash rendered ✓ |
| **F-4** | all three texts now 15s: timer Description (repo **and** `/etc` — `diff` clean), `AGENTS.md:281`, `ladder_api.py:10`; live cadence 15s ✓ |
| **F-5** | n<32 early return carries `'cur'` all-None (`ladder_api.py:216–220`) ✓ |
| **F-6** | `draw()` reads `hoverIdx` and strokes the vertical `rgba(79,195,247,.35)` (`ladder.html:433–441`); harness asserts the stroke present after hover ✓ (style is `.35/[2,3]` vs the pane's `.55/[3,3]` — cosmetic difference, same family) |
| **F-7** | opened-before-window trade: exit arc drawn + connector from `P.l`; both-outside trade skipped — harness arc count 17 = 16 baseline + 1 (exit), both-out contributes 0 ✓ |
| **F-9** | `stateTag==='triggered'` → `tag trig` accent class + `.tag.trig` CSS ✓ (harness asserts `tag trig` + `>triggered<`) |
| **F-8/F-10/F-11/F-12** | accepted no-code, as noted ✓ |
| regressions re-run | py_compile **9/9** (incl. price_collector, fetch_hl_volume); `test_pending_machine` **ALL PASS**; `test_manual_exit_manager` **20/20**; `node --check` on the current script OK; page **200**; deployed == repo; feed healthy (192 candles, `ind.cur` present, `error:null`); round-1 selfchecks stand (b2a0be36 does not touch their files) |

## DELTAS — why this is not a clean PASS

### DELTA A — HIGH — the flat 900 s floor is not per-interval (money-path reads go stale)
`price_collector.py:198` computes `_now_floor = int(time.time() // 900) * 900` **inside the multi-interval `_store_candles`** (and `fetch_hl_volume.py:~141` mirrors it) — my prescription was *"TF per interval"*. Consequence for 1m/5m: a **closed** bar whose `ts` is inside the current 15m window is flagged **0**.
- Controlled proof (`h_f1.py`): a 1m bar 5 min old at now=F900+10min → `is_closed=0`.
- **Live proof:** `closed 1m bars (ts<floor60, ≥floor900) wrongly flagged 0: 11` at 05:11; **watchdog-confirm-equivalent read age 12.5 min (05:11) and 8.0 min (05:36)** — pre-fix the F-2 ts-guard gave ≤1 min old closes; the read oscillates 0→16 min within every 15m window.
- Readers now fed up-to-16-min-stale 1m closes: `trade_watchdog.py:1136` (BTC latest close), `:1475` (E1 confirm), `:1644` (rung cross — the F-2 ruling says this must be the freshest), `decider_run.py:6240/6501/6505/6544/6548`, `contrarian_monitor.py:41`, `verify_ema300_dip_buyer.py:22`.
- **Fix (one line, both sites):** `_tf = {'1m':60,'5m':300,'15m':900,'1h':3600,'4h':14400}[interval]; _now_floor = int(time.time() // _tf) * _tf`.

### DELTA B — MEDIUM (residual, not a regression) — the F-1 class survives for 1h/4h
Same flat floor: the **forming hourly bar** is flagged 1 from `:15` after each hour boundary until `:00` — **45 of every 60 minutes** (controlled proof: at hh:20 the forming bar stores `is_closed=1`; 4h analogously ~3h45/4h). Pre-fix it was always-1, so this is a partial fix, not a regression — but the HIGH's root is only closed for 15m (and 5m forming is correctly 0; 5m/1h/4h recent-closed rows are affected as in A). Unguarded 1h/4h readers: `mtf_macd.py:103`, `hzscore.py:90`, `ema300_breakthrough`, regime scanners. The **same per-interval floor fix closes A and B together**.

### DELTA C — MEDIUM (new) — the dev-writer wipes the seeder's real volume once the flags are honest
The "window already closed" skip (`price_collector.py:783–784`) protects only `flag1` rows — it was accidentally also protecting **volume**, because the old lie kept the forming bar at flag1. With honest flags the forming bar is flag0, so the dev-writer's `INSERT OR REPLACE … volume=0` now overwrites the seeder's real kline **on every aggregator run (~45 s)**.
- Controlled proof (`h_f1.py`, isolated tmp DBs): forming bar `(0, 123.4)` → after `_aggregate_tf` → **`(0, 0.0)`** — volume wiped.
- **Live proof:** the newest **5 ladder-eligible BTC bars have volume 0.0** (`[0,0,0,0,0, 117.9, 401.3, 798.1, 233.3, 138.4]` at 05:36) — bars serve volume=0 from close until the next seeder fetch (BTC slow-seed cadence ≈2 h under the 4h-fresh skip; the close+15 min fill also writes vol0). This re-opens the 2026-10-05 "zero-volume 15m candles break volume signals" class, bounded by the fetch cadence; the ladder's volume histogram is empty for the newest bars (visible in the live feed).
- **Fix (two lines):** in the dev-writer loop `SELECT is_closed, volume …; if exists and (exists[0] == 1 or exists[1]): continue` — i.e. never overwrite a row that already carries real volume (gap-fill only, which was the BUG-048 intent).

### DELTA D — LOW — F-7 comment vs code
`drawTrades`'s comment says *"skip the entry triangle"* for an opened-before-window trade, but the triangle block is unconditional: it draws at `px=P.l` at the **exit's** y with the B/S letter (harness: **17** entry markers where a skip would give 16). Cosmetic (the marker sits on the axis at the wrong price); either guard it with `if(i1>=0)` or fix the comment.

### INFO — the chart's right edge moved back ~15–30 min (by design of honest flags)
Closed bars only gain `is_closed=1` at the fill (**close + 15 min**) or the next seeder fetch (≤~2 h), so the ladder's newest candle is now the bar that closed up to ~15–30 min ago (live: 05:11 → newest eligible was 04:30/04:45; 05:36 → 05:00 while 05:15 was still flag0). Pre-fix the right edge showed the *forming* bar (fresh but wrong); now it is *correct but late*. If the CEO wants a fresher right edge, the options are: run the fill at close (clock permitting), fetch BTC more often, or have the ladder accept `ts+900 <= now` rows carrying a `tick_agg` provenance — not recommended without C fixed first.

## Acceptance call
- **15m root cause (F-1 core): CLOSED and live-proven** — no forming bar (15m or 1m, any token) is flagged closed; the belt holds; completed bars flip to 1.
- **F-2…F-9: CLOSED** (page harness 66+7 checks green, h_err 24/24, suites green).
- **Three deltas remain:** **A** (per-interval floor — HIGH, one line × 2 files), **B** (same line covers it — MEDIUM), **C** (dev-writer volume guard — MEDIUM, two lines), **D** (cosmetic, one `if` or a comment fix).
- **Final PASS withheld until A+B+C land** (D at the lead's discretion). Re-verification is cheap: re-run `/tmp/bh/h_f1.py` (expects DELTA A/B/C gone), the page harness, and one live flag sample.

---

# FINAL PASS — fix commit `d562e7a2` (3 files) · verified 2026-11-23 05:50–05:55 UTC

**Verdict: PASS — all three deltas + D closed, independently re-verified. This closes the verify-everything round.**

## Delta re-verification (my harnesses, re-run against this commit — not taken on trust)

| delta | code | controlled (`/tmp/bh/h_f1.py`) | live |
|---|---|---|---|
| **A** per-interval floor (1m/5m) | `price_collector.py:198–205` `{1m:60,5m:300,15m:900,1h:3600,4h:14400}[interval]`; `fetch_hl_volume.py:143–145` its own `{1m,5m,15m}` keys (matches its table map — no KeyError path) | **closed 1m bar (ts=F900+5min @ now=F900+10min) → `is_closed=1`** ✓ | closed-1m-bars wrongly flag0: **0** (was 11 at 05:11); **watchdog 1m read age 1.6 min** (was 8.0–12.5) — F-2-era freshness restored ✓ |
| **B** forming 1h/4h | same line covers it | **forming 1h at hh:20 → `is_closed=0`** ✓ | forming 1h (05:00) flag **0** at 05:52 (flat-900 would have flagged it 1 since 05:15) ✓ |
| **C** dev-writer gap-fill | `price_collector.py:797–806`: `SELECT is_closed, volume …; if exists and (exists[0]==1 or (exists[1] or 0) > 0): continue` | forming bar `(0, 123.4)` → after `_aggregate_tf` → **`(0, 123.4)` — volume preserved** ✓ (`PASS=6 FAIL=0`) | forming 15m flag0 ✓; newest bars' vol0 is pre-fix residue, heals retroactively at the next BTC seeder fetch (`excluded.volume>0` update) |
| **D** gated entry triangle | `ladder.html:494–511` `if(i1>=0){ … ctx.restore(); }` — save/restore paired inside the gate, no state leak | — | page harness: **`f7_entry_markers = 16`** (was 17) — pre-window trade draws exit arc + left-edge connector alone, matching the comment ✓ |

**`h_f1.py` → PASS=6 FAIL=0** (forming15m→flag0+volume · completed→flag1 · stale corrected · dev-writer keeps flag0+volume · fill heal→flag1 · closed1m→1 · forming1h→0).

## Full battery re-run (all green)

- `h_f1.py` **6/0** · `h_err.py` **24/24** (F-2 degraded feed + atomicity) · page harness **PHASE1 66/0 + PHASE2 7/0** (incl. F-3 no-throw, F-6 hover stroke, F-9 trig tag, parity ∅/∅, priceMode reload)
- py_compile **9/9** · `test_pending_machine` **ALL PASS** · `test_manual_exit_manager` **20/20**
- `node --check` OK · page **HTTP 200** · deployed == repo (`diff` clean) · ladder unit **0 failures since 05:03** · feed age 9.1s, 192 candles, `error:null`, last bar genuinely pre-floor
- **core invariant holds live:** any-token forming bars flagged closed — **15m = 0, 1m = 0** (the F-1 lie has no instances anywhere in the DB right now)

## Notes (non-blocking, honest residue)

1. **Retroactive heal pending:** the newest ~6 ladder-eligible BTC bars still carry `volume=0` — wiped before `d562e7a2` landed; they correct at the next BTC seeder fetch (≤~2 h under the 4h-fresh skip). The mechanism that caused it is closed (controlled test), so no new wipes occur.
2. **Closed hourly bar (04:00) reads flag0** until its next seeder rewrite — the per-interval floor changed the flag direction for already-stored rows; this is the *safe* direction (closed-bar-flagged-open → under-report, never a forming-bar lie) and heals on rewrite.
3. Cosmetic: the main-chart hover stroke is `.35/[2,3]` vs the pane's `.55/[3,3]` (F-6) — same family, intentionally dimmer; no action.

## Round summary (three commits, all verified)

- **Round 1** `f95994e0` verdict: PASS WITH FINDINGS — 1 HIGH (F-1 forming-bar), 2 MEDIUM (F-2 crash-stale, F-3 price-null), LOWs/INFOs; indicator math + alignment proven exact; wiring green; fresh-air ruling = KEEP; mission chain alive 5=5; regression clean.
- **Round 2** `b2a0be36` → acceptance `f8047a01`: CONDITIONAL PASS — F-1 15m core + F-2…F-9 closed; named deltas A (HIGH, money-path stale 1m reads), B (MEDIUM, 1h/4h residual), C (MEDIUM, dev-writer volume wipe), D (LOW, comment-vs-code).
- **Round 3** `d562e7a2` → **this section: FINAL PASS.** Every finding from the verify-everything pass is closed and independently re-verified; no open findings remain on the ladder dashboard (API, page, wiring) or its shared seeder root cause.
