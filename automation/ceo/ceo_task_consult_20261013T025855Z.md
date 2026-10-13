# CONSULT RUN 20261013T025855Z (UTC)

You are running a BOUNDED, READ-ONLY consult. Base persona/rules follow after this block.

## HARD LIMITS (this run)
- **BUDGET: ~3 minutes. Do not exceed a few file/DB reads.**
- **READ-ONLY. Do NOT edit ANY file. Do NOT change params, flags, or blacklists.**
- Do NOT develop signals. Do NOT tune signals. Do NOT dispatch subagents.
- Do NOT write to ceo_report.md or ceo_kanban.md — answer HERE, in this session.
- No session lock is held. If you believe an edit is needed, say so as a recommendation and stop.

## THE QUESTION
Answer the directed brief below. Verify any numbers you cite with a quick query (base prompt SQL rules apply — never trust old reports). Give a clear VERDICT (approve/reject/modify + rationale). If the brief asks for a review, lead with the verdict, then the reasons.

--- BRIEF ---
# CEO Consult — deep runs keep DYING (not timing out). How do we resolve it?

**Mode:** consult (read-only opinion). Do NOT edit anything. Answer on stdout.

## The reframe you need before answering

The original complaint was "deep runs time out." I have now pulled the evidence from
`logs/ceo/`, and **the dominant killer is NOT the 1800s budget.** Of 12 deep runs:

| Run | Span | Outcome | Killer |
|---|---|---|---|
| 172817Z | 15s | `0` (false success) | **opencode PERMISSION-REJECT `/tmp/*`** |
| 192508Z | 1617s | `incomplete rc=124` | genuine budget exhaustion (investigation ate it) |
| 205810Z | 49s | `ok rc=0` | completed |
| 232327Z | 1301s | `ok rc=0` | completed |
| **000026Z** | **557s** | NO `.exit` | **opencode PERMISSION-REJECT `/var/tmp/*`** |
| others (5) | — | NO `.exit` / rc=143 | SIGTERM — mostly MY OWN test kills, not real failures |

The two most important runs both died from the same thing: **opencode auto-rejects
`external_directory` reads on `/tmp/*` and `/var/tmp/*`. The session dies instantly on the
rejected tool call.** No timeout. No `.exit` written (the classify line never runs because
the process tree is killed, not `timeout`-ed).

The irony, which is also the lesson: run **000026Z died while TESTING the `/var/tmp` ban.**
The CEO wrote a test that tried to create a file under `/var/tmp` to prove the ban works —
and opencode killed the session for touching `/var/tmp`. Read the tail of
`logs/ceo/deep-20261013T000026Z.jsonl`: the CEO's own comment says "wait, we shouldn't
touch /tmp or /var/tmp", but the bash heredoc had already been submitted as one tool call
and the literal path string in it triggered the reject.

So the runner's `/tmp`+`/var/tmp` ban — which WE added to protect the session — is now
colliding with opencode's OWN `/tmp`+`/var/tmp` ban, and opencode's version kills the
session outright rather than failing a single call.

## Relevant facts

- `~/.opencode/opencode.json` currently has NO `permission` block. Binary strings show the
  schema supports `permission: { edit, bash, external_directory, webfetch }` with
  `allow|ask|deny`.
- The `/tmp`+`/var/tmp` reads come from BOTH the runner scripts (ban on brief paths) AND
  from the CEO's own test scaffolding when it verifies those bans.
- Only ONE run (192508Z) actually hit the budget, spending 1617s on investigation before
  dying pre-dispatch. That is a real but SECONDARY problem.
- Consult (read-only, 300s, no lock, no report write) and `--wait` (600s foreground) shipped
  2026-10-13 and are untested in anger.

## What I need from you (opinion only, be specific)

1. **Should we add a `permission` block to `~/.opencode/opencode.json` allowing
   `external_directory` for `/tmp` and `/var/tmp`?** If yes, give the exact JSON. Consider:
   our runner already bans `/tmp` briefs itself, so does allowing the read at the opencode
   layer actually remove protection, or just move it? Is there a narrower form (allow only
   `/root/.hermes/**`, deny elsewhere)?
2. **Should the prompt instead forbid the CEO from EVER emitting `/tmp` or `/var/tmp` in a
   bash command — including in comments and test scaffolding?** That is a prompt fix, not a
   config fix. Which layer is correct, or both?
3. **How should a CEO self-test a `/tmp` ban without touching `/tmp`?** Give a concrete
   alternative (e.g. test the canonicalization logic via a stub, or test with a repo path
   and assert it is NOT rejected rather than proving a rejection).
4. **The budget problem (192508Z):** still worth fixing separately, or does solving the
   permission-kill make it moot? Be honest about whether 1800s is enough for
   investigate+decide+checkpoint+dispatch.
5. **Is there a systemic SIGTERM source we should worry about**, or are those kills
   attributable to my own testing? Say what you would check to distinguish.

Give me your recommendation with the exact change you would make at each layer. Do not
implement — I will.
--- END BRIEF ---

## OUTPUT
Print your answer to this session (stdout). Do NOT append to any report file. Max ~400 words unless the brief demands more detail.
