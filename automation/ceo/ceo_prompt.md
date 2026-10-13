# ⛔ STOP — YOU ARE USING THE DEAD ceo-comm PATTERN

**This file exists only to fail loudly.** It is not the CEO. It has no persona, no
protected-flags context, and no rules. If you are reading this, you invoked the CEO the
OLD way — piping this file into `opencode run` — which was retired on **2026-10-12**.

Any "CEO" answer you were about to get would be from a nameless session with **no
protected-flags context**, free to edit `hermes_constants.py` and live-trading files
without the rules that stop it. Do not proceed. Do not re-run this.

## Use one of these instead (all current as of 2026-10-13)

```bash
# 1. Quick question / "review this plan" — read-only opinion, ~5 min, in-process
/root/.hermes/automation/ceo/run_ceo_consult.sh /path/to/brief.md

# 2. Status check — read-only, ~3 min, in-process
/root/.hermes/automation/ceo/run_ceo.sh

# 3. Decision + implementation — detached, takes the session lock
/root/.hermes/automation/ceo/run_ceo_deep.sh /path/to/brief.md
/root/.hermes/automation/ceo/run_ceo_deep.sh --wait /path/to/brief.md   # foreground, 600s

# 4. Monday panel
/root/.hermes/automation/ceo/run_ceo_moe.sh
```

Put your brief **inside the repo** (e.g. `automation/ceo/my_question.md`), never in a
system temp dir.

## Two things that will kill your session outright

1. **A bare system-temp-dir path in ANY bash command** — even a quoted grep pattern or a
   comment. opencode requests parent-directory approval for every absolute path it finds,
   gets no interactive answer, and kills the session. No checkpoint, no `.exit`, work gone.
2. **Piping any prompt file into `opencode run`** — that is what put you here. Only the
   four runners above assemble a prompt correctly.

Read `/root/.config/opencode/skills/ceo-comm/SKILL.md` for the current interface.
