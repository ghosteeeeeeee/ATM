# BRIEF: Centralized control tower for shadows + trials + calendar (T request 2026-10-31)

## T's ask (verbatim intent)
"Do we have a centralized spot for all the shadow data and the trials currently running etc.
I like this calendar idea, more of that so stuff actually gets done."
→ He wants ONE place that answers "what is running, what does it need to decide, and when"
— and the calendar must DRIVE action, not be passive decoration. Standing delegation:
if you sign off, we build it immediately (no further T approval needed).

## What exists today (fragmented, verified 2026-10-31)
1. **`data/shadow_disposition.json`** — THE registry. 47 entries (25 open / 22 done).
   Fields: id, stream, kind, disposition, status, started, deadline, threshold,
   default_action, evidence, owner, notes (+ done_at, revert, threshold_eval on some).
   Runner: `scripts/shadow_disposition.py` (daily 08:15) — deadline packets to
   ceo_kanban, 24h default-action clock, zero-event auto-KILL, per-entry threshold_evals
   (e.g. coupled-SL breach already tripped: worst HML exit −7.10% < −6.5 limit).
   Renders `automation/ceo/shadow_disposition_report.md` (41 lines, status+deadline+source rows).
2. **`brain/trial_tracking_dashboard.md`** — hand-maintained trial tracker, **last edited
   10-27 (4 days stale)**, already disagrees with reality (says "registry: 37" vs 47 now).
   Tracks: wider-SL trial (FAILING, 32.7% vs 55% bar), extended-time exits (FAILING, −16.9pp),
   CONTRARIAN-LIVE (0 real trades yet), coupled-SL trial, etc.
3. **`scripts/trial_monitor.sh`** — manual CLI status dump (wider/time trials, contrarian
   lines, upcoming deadlines). Not scheduled anywhere.
4. **Calendar dates live everywhere else**: registry deadlines (11-02/03/05/06/07/09/10/12),
   AGENTS.md reminders table, briefs, 2000-char kanban lines, my session notes.
   Nothing renders them date-ordered.

## The gaps (why T asked)
- **Two sources of truth** (registry vs hand dashboard) that already disagree → rot guaranteed.
- **No date-ordered calendar**: "what fires in the next 14 days" requires reading 3 files.
- **No n-vs-bar progress**: report shows row counts; most entries print "(no parseable
  source)" — you cannot see "storm packet 1/3" or "gate-shadow 52k rows vs bar n≥X".
- **Nothing surfaces due work into the execution loop** except kanban packets buried in
  an append-only log of 2000-char lines.
- Trials (wider-SL, extended-time, coupled-SL, size-reduce 1.0x, waiver experiments,
  AMPLIFY mandate) are tracked in ≥3 places with different freshness.

## What we want from you (decide, be concrete)
1. **Single artifact**: one canonical file (or web page) that renders ALL of:
   (a) running shadows/trials with status, bar, progress-vs-bar, deadline, owner;
   (b) a date-ordered calendar of the next ~14 days of decision dates;
   (c) DONE/reverted history (from registry, collapsed).
   Where does it live and in what format — auto-generated Markdown (like the 08:15 report),
   a web dashboard (existing nginx pattern: `web/*.html` + `scripts/*_api.py` + timer),
   or both with Markdown canonical?
2. **Schema**: does `shadow_disposition.json` need new fields (e.g. `bar_now`/`bar_target`
   or an evaluator hook per entry so progress renders live), who owns maintaining them,
   and what is the minimal change that stops the hand dashboard from being needed at all?
3. **Generation + freshness**: extend `scripts/shadow_disposition.py` (already scheduled
   08:15) vs a new `scripts/control_tower.py` + timer. Must be idempotent, zero trading
   behavior, no hermes_constants edits, systemd timer (no cron), and must not go stale
   the way trial_tracking_dashboard.md did (what is the anti-staleness rule?).
4. **Calendar-drives-action**: how do due items reach the loop that ACTS — surface
   "DUE within 24h / DUE this week" lines into the auto_1hr prompt, the daily disposition,
   and/or a dedicated kanban section with an explicit owner? Propose the exact wiring so
   a date passing with no decision is IMPOSSIBLE to miss (today a missed deadline only
   fires via the 24h default-action packet).
5. **Trials**: where should running trials canonically live (registry entries of kind
   `trial` vs a separate trials section), and what kills the hand-maintained
   `brain/trial_tracking_dashboard.md` (archive it, or keep it as generated output only)?
6. **Scope call**: what should NOT go into the tower (keep it lean — T reads it daily
   while on vacation).

## Constraints
- Zero trading behavior; no hermes_constants.py edits; no new API calls (local DBs/files only).
- Must work unattended (T on vacation since 10-16) and survive pipeline restarts.
- Build convention: script + timer + docs; immediate commit + push via push_gh.py;
  mandatory subagent code review + bug_hunter after build (standing rule).
- Existing strengths to reuse, not duplicate: shadow_disposition.py runner semantics
  (deadline/default_action/threshold_eval/zero-event), the 08:15 report, trial_monitor.sh
  queries, nginx dashboard pattern.

## Deliverable we will execute on your sign-off
A concrete build spec: file paths, JSON schema deltas (if any), script/timer names,
prompt files to touch for the action-wiring, archive plan for the hand dashboard,
and a "day in the life" of the tower (what T sees each morning and what the system
does automatically when a date arrives).
