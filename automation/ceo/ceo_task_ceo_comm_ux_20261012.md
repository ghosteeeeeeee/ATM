# CEO Decision Request — ceo-comm interactive-workflow friction

**Raised by:** external agent that live-tested the ceo-comm skill on 2026-10-12 (conversational use, not automation).
**Your job:** decide on each of the 4 proposed changes, then IMPLEMENT the approved ones. This is a design decision on our own tooling — no trading files involved.

## Feedback (verbatim summary)

What worked: directed brief (file in `automation/ceo/` + path arg), checkpoint-before-edit (readable mid-run), output quality (CEO's velocity verification caught 0.022% vs claimed 0.3%, and a BANANA SHORT cross-reference the tester missed).

Friction:
1. **Polling is clunky** — deep run is detached; polling loops timed out twice before the run finished.
2. **`.exit` semantics confusing** — `run_ceo.sh` (status) writes a plain rc, `run_ceo_deep.sh` writes `ok rc=0`. Two formats; tester read the docs twice to get it.
3. **Lock check blocked a first attempt** — a stale lock file existed; tester had to remove it manually.
4. **No quick-question mode** — status is read-only with a rotating question (useless for "review this plan"); deep takes 13min and dispatches subagents (overkill for an opinion).

Suggested: `--wait` on deep; standardize `.exit`; `--force` to bypass lock; a "consult" mode (read-only, takes a brief, gives an opinion, no subagent dispatch, ~5 min).

Tester's own framing: "core architecture is solid; friction is in the interactive workflow — it was designed for automation and I used it conversationally."

## Current state (verified 2026-10-12, commit 85fa3259)

- 3 runners: `run_ceo.sh` (status, read-only, in-process, 300s, writes plain numeric rc), `run_ceo_deep.sh` (decides+edits, detached, 1800s, takes session lock, accepts optional brief arg), `run_ceo_moe.sh` (Monday panel, detached, 3600s, no lock).
- Guards: `ceo_assert_prompt` (persona marker check), `ceo_assert_template` (per-run template exists), brief arg canonicalized + `/tmp` ban, all fail closed at rc=5/4.
- `.exit` for deep/moe = `<class> rc=<n>` where class ∈ ok|incomplete|failed|silent (derived from jsonl — opencode exits 0 even when the agent dies). Status = plain numeric rc.
- Known open: deep run burned all 1800s on investigation once, dying before dispatching subagents; SKILL.md does not document the brief-arg interface; SKILL.md lives OUTSIDE the git repo at /root/.config/opencode/skills/ceo-comm/.

## What I need from you

For EACH of the 4 proposals: APPROVE / REJECT / MODIFY, with rationale. Specifically:

1. `--wait` on deep — foreground mode for interactive use. Risk: a foreground 1800s+ call blocks the caller's turn; is that better than polling? Would a shorter interactive budget (e.g. 600s) plus an honest "didn't finish, checkpoint is at X" be better?
2. `.exit` standardization — should status adopt the same `class rc=N` format? That makes one contract across all three. Any downside for the systemd timer path?
3. `--force` / `--ignore-lock` to bypass the session lock — this exists to stop a CEO run editing hermes_constants.py while a HUMAN session is live. A bypass flag weakens that. Approve? If yes, what guard (e.g. only allow with a second explicit flag, or refuse if the lock owner is a human not a stale CEO run)?
4. "consult" mode — read-only, takes a brief, gives an opinion, no subagent dispatch, ~5 min. This is a 4th runner. Worth it, or should deep learn a `--consult` flag instead? Consider: does it need the session lock? Does it write to ceo_report.md or just answer?

Also decide: does the deep run's budget problem (1800s investigation, never reached dispatch) get fixed as part of this, or stays a separate item?

**Implement what you approve.** Guardrails for this task: touch ONLY `automation/ceo/*` scripts + the SKILL.md at /root/.config/opencode/skills/ceo-comm/. Do NOT touch any trading file, hermes_constants.py, or the pipeline. bash -n every script you change. If you add a flag, test it (the failure modes that bit us: relative brief paths, missing templates, persona-less prompts, /tmp bans).

Checkpoint before editing, per your own discipline. Write the decision to automation/ceo/ceo_report.md.
