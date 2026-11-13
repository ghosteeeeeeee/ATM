# BUG-HUNTER VERDICT — 2026-11-13 calendar staleness

=== BUG-HUNTER VERDICT ===
Diagnosis: CORRECT

Evidence:
- Registry = `data/shadow_disposition.json`, rendered by `scripts/shadow_disposition.py`
  into `automation/ceo/control_tower.md` (+ report + kanban). Daily timer
  `hermes-shadow-disposition.timer` active (next 2026-11-13 08:15 UTC) — confirmed via
  `systemctl list-timers`.
- Staleness window proven from git: commit `62e8b702` (brain_auditor #252, render
  2026-11-12T12:54:57) contains `## 🟠 DUE ≤24h (4)` listing
  `pump-chain-plus-weight-kill-review` (11-13) — the 4 items. They were closed by
  brain_auditor #253 at 00:47–00:49 on 11-13 (kanban TEAM UPDATES + registry
  `status=done`), but no render happened until the manual run 11-13 04:16 → the tower
  sat ~15.5h showing 4 already-closed items as DUE ≤24h. Exactly the claimed symptom.
- Footer cannot see the drift, and in fact is even weaker than claimed: the `stale`
  flag (`shadow_disposition.py:864`) is `NOW - prev_tower_mtime > 26h` — an age check
  on the *previous render*, not a registry-vs-tower comparison; the displayed
  "registry mtime" is captured at render time (`:1013`). Either way it reads FRESH
  until a render happens. (Diagnosis direction correct; mechanism stated slightly
  imprecisely.)
- Secondary context confirmed: journal shows `Nov 12 08:15:00 … WARN: control tower
  render failed: 'tuple' object has no attribute 'get'` (run still issued its 4
  packets + report). Fixed by #252 at 12:53 (script mtime 2026-11-12 12:53; comment
  at `:984` documents the undated-tuple root cause).

Fix part 1 (manual re-render 11-13 04:16): PASS
- Kanban header `## shadow_disposition run 2026-11-13T04:16:25 (13 action(s))` = 13
  DECISION DUE lines, all with deadline `2026-11-14T00:00:00Z`. Tower regenerated
  (47 open / 60 done / 107 entries) — matches claim. rc=0 (report+tower+state all
  written).
- Dedupe holds for the 08:15 run: all 13 ids carry
  `due_warned == "2026-11-14T00:00:00Z"` in `data/shadow_disposition_state.json`
  (verified programmatically, 0 mismatches). Two subsequent runs (path-triggered
  04:17 and my independent rename test 04:21) both logged `0 action(s) issued`.
- Packet text accurate: emitted 04:16 on 11-13 against a 11-14T00:00Z deadline =
  19.7h remaining → "within 24h" correct.

Fix part 2 (path unit, no loop): PASS
- `config/hermes-shadow-disposition.path` identical to
  `/etc/systemd/system/hermes-shadow-disposition.path`; commit `45d7ae51`
  (16 insertions, only that file). Unit `enabled` + `active (waiting)`;
  directives `PathChanged=`/`PathModified=`/`Unit=` valid; `WantedBy=multi-user.target`.
  Timer also `enabled`. Both activate the **same** service unit → systemd job queue
  serializes; no two concurrent executions via systemd; a trigger arriving while the
  service runs is queued/coalesced into one follow-up run that re-reads the registry
  (no lost update).
- No loop: the script writes only `_save(STATE)` (`:806`), `REPORT` (`:811`), tower
  tmp (`:1019`) and kanban append (`:788`). `REGISTRY` appears only as `_load` /
  `getmtime`. Repo-wide grep: no `json.dump`/`open(...,'w')` to the registry from any
  script; other referencing files (position_manager, decider_run, tpsl_utils,
  shadow_tag_join, signal_compactor, control_tower_api, trial_monitor, hermes_constants)
  are comment/read-only. `shadow_disposition.py`'s only subprocesses are
  `systemctl is-active`, `grep`, and `shadow_trader.py <report flag>` (read-only
  reports) — no adjudication path. paths.py import has no side effects.
- Empirical: rename-replace of the registry (atomic `mv`, not in-place write) at
  04:21:48 → service ran same second, `0 action(s)`, state/kanban byte-identical,
  tower regenerated. Exactly 2 systemd runs since 04:15 (04:17 path test + 04:21) —
  zero self-retriggering.

Packet spam check: PASS
All kanban line types are state-gated (`pending_state`, applied only after a
successful append — `:785-803`): DECISION DUE (`due_warned` per deadline), DEFAULT
FIRES (`default_fired_for` per deadline), LOOKAHEAD (`_tower.lookahead_fired_for` per
ISO week), zero-event AUTO-KILL (`zerokill_fired` once), REGRESSION
(`regression_fired_for` per signature — re-fires only on a changed signature),
THRESHOLD (`threshold_fired`, deliberately re-armed when the bar reads not-breached),
AUTO-FLIP (`auto_flip_fired`, opt-in; no entry carries `auto_flip_flag` today).
Kanban header only written when ≥1 line (0 empty "(0 action)" headers in file). No
packet type re-fires on every trigger.

Deadlines recomputed (independently, status=open, as of 2026-11-13T04:24Z):
- OVERDUE: **none**. The known claim "1 overdue (winner-cell-size-125, constants
  still 1.25)" is **superseded**: entry is now `status=done` (done_at 2026-11-13,
  disposition "REVERT EXECUTED 1.25→1.0, default packet fired 11-10 08:15, 92h
  overdue") and `scripts/hermes_constants.py:1174` now reads
  `WINNER_CELL_SIZE_MULT = 1.0` (commit `60347085`, CEO 20261113T040327Z). The claim
  was true pre-04:03 on 11-13, false now.
- DUE ≤24h: **13**, all deadline `2026-11-14T00:00:00Z` — matches claim exactly:
  mfe-cut-arm-be, amplify-winner-cell-mult-150, amplify-jup-short-walk,
  atrtrail-clip-12, stop-tighten-enforce-eval, amplify-stop-tighten-probe-080,
  amplify-bbsqueeze-warrior-uninert, amplify-bbsqueeze-neutral-exempt,
  amplify-prearm-breakeven-lock, amplify-bbsqueeze-module-rsi-reband,
  amplify-winner-cell-drop-pcplus, stop-tighten-slippage-column,
  amplify-tat-neverarmed-age-widen.
- 4 formerly-due 11-13 items all `status=done` ✓: pump-chain-plus-weight-kill-review,
  amplify-vb-high-short-clonehunt, amplify-bbsqueeze-chop-exempt,
  linreg-fade-fill-funnel (all closed by #253).
- Counts: 47 open / 60 done / 107 total; every open entry has a parseable deadline.

Footer honesty: PASS (with residual, see missed issues)
- After the fix, footer reads FRESH and it is now truthful in practice: registry
  writes re-render within seconds (measured <1s), so registry mtime ≈ tower mtime
  (`control_tower.json`: registry 04:21:48.34 / tower 04:21:48.53,
  `tower_stale: False`). Write-while-running is covered by systemd's queued start
  job (one follow-up run). Remaining structural caveat below.

Path unit config correctness: PASS
- Directives valid, enabled at boot, installed file identical to repo, daemon-reloaded
  (unit active). Runs the same root service the timer already ran — no new privilege
  or policy surface; the only new input is a data file the script only reads.

Missed issues (all minor):
1. **LOW — footer freshness is structurally self-referential.** `stale` is a 26h
   age-check on the previous render, and the displayed registry mtime is render-time.
   Correctness now depends entirely on the path unit staying enabled; if it is ever
   disabled/daemon-reload skipped, the footer again claims FRESH for up to 26h. Web
   `control_tower.json.tower_stale` has the same 26h blind spot — though the web
   *calendar* is registry-derived per 60s tick and was never stale. Cheap hardening:
   flag `registry_mtime > tower_mtime + ε` in `control_tower_api.py`.
2. **LOW — no flock in `shadow_disposition.py`.** systemd serializes timer/path
   triggers, but a *manual* `python3 scripts/shadow_disposition.py` concurrent with a
   triggered run can race the read-then-write dedupe and double-emit one packet.
   Window is seconds; pid-unique tmp keeps files uncorrupted. Add flock if manual
   runs become routine.
3. **TRIVIAL — tower header still says "(daily 08:15)"**; it now also renders on
   registry change. Cosmetic text only.
4. **TRIVIAL — report hides already-warned due items**: the `DECISION DUE` report line
   is only appended inside the dedupe branch (`:735-742`), so a deduped run's report
   shows 0 "DECISION DUE" lines even when 13 are due (the OPEN header lines still
   carry the deadlines). A reader of `shadow_disposition_report.md` alone could think
   nothing is due.
5. **INFO — the web control tower was never stale** (registry-derived per tick), and
   `trial_monitor.sh` output is accurate (rc=0; explicitly labels
   `brain/trial_tracking_dashboard.md` archived 2026-10-31 and points at the tower).
   LOOKAHEAD cadence on schedule: last fired 2026-11-09 = Monday = first day of ISO
   W46 (verified `date(2026,11,9).isocalendar() == (2026,46,1)`); next fires on the
   first run ≥2026-11-16 (W47), which the path unit/timer will both cover.
6. **INFO — known-claim drift**: "1 overdue + constants still 1.25" was superseded at
   2026-11-13 04:03 by the executed revert (see above). Any downstream consumer of
   that claim should re-read the registry.

Overall: PASS
