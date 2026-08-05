# ai-engineer Session — Hebbian Plan Audit, 2026-06-24

## Session Context

T asked for a second audit of `/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24.md`
(post-audit v2). The plan proposed fixes for a Hebbian memory DB that had 144 nodes / 602
synapses dominated by trade-decision co-occurrence pollution.

Two parallel subagent audits were dispatched: 266s + 171s, 18 API calls total. Every "missing"
or "wrong" claim was verified by main-session grep/sqlite3/python before being reported to T.

## The Critical Lesson (most important finding of this session)

**Subagent correctly flagged `hebbian_learner.py` as a "parallel pollution source" because
it had its own `infer_label()` and `extract_concepts()` at lines 37 and 52. The subagent's
recommendation: delete the file as dead code.**

**T pushed back:** "I'm not following, it is what we are trying to improve isn't it? it isn't
called anywhere because it has not been properly implemented."

T was right. Reading the actual 182 lines showed `hebbian_learner.py` is the **brain-md seeder**
— scans `brain/*.md` files (TASKS.md, PROJECTS.md, trading.md, lessons.md) for co-occurring
concepts and seeds the network from T's documented knowledge. It is NOT a parallel extractor
competing with `hebbian_entity_extractor.py`. It's a complementary data source that was never
wired to any timer/cron — hence "not called anywhere." The reason it has its own `infer_label`
is because it predates `hebbian_entity_extractor.py` and they share vocabularies but never
got refactored to share code.

The right answer was **refactor and integrate**, not delete.

**Root cause of the subagent error:** pattern-matching on "has its own infer_label" without
understanding the file's actual purpose. The subagent saw "duplicate function definitions" and
concluded "dead code, remove." But the duplicate definitions were a code-quality problem (DRY
violation), not a runtime problem (the file does useful work even though nothing calls it).

**Rule for main session:**
1. When a subagent flags an orphan file as "delete this dead code," **read the file in main
   session before relaying the recommendation to T.** The subagent may be right (truly dead
   code) or wrong (waiting to be wired up).
2. The signal to look for: an orphan file with a clear docstring describing a real purpose,
   but no callers. That's "unfinished feature," not "dead code."
3. The signal that it's truly dead: orphan file with no clear purpose in the docstring,
   imports that don't match the rest of the codebase, or functions that return None / pass.

## Subagent Findings — All Verified Correct

Both subagents (one focused on the plan's stated fixes, one looking for what was missed)
reached the same conclusions on most items. Differences were complementary, not contradictory.

**Subagent 1 (266s, 11 API calls) caught:**
- Fix 1 verification assertion too lenient (`> 50` passes on 50-fallback)
- Fix 2 line ranges off-by-one (342-345 not 343-345, 210-214 not 210-213)
- Fix 4 `bug_fix` heuristic AND-condition broken (most bug reports miss it)
- Fix 6 duplicates existing skill content
- **CRITICAL: `request_dump_*.json` contains Bearer/sk- API keys** — distill script must strip
- `weight >= 5.0` threshold unreachable for weeks post-reset
- No SOUL.md backup before Fix 6
- hebbian_learner.py parallel-pollution false positive (the lesson above)

**Subagent 2 (171s, 7 API calls) caught:**
- Same line-range off-by-ones
- Same API-key secret leak
- **CRITICAL: `request_dump_*.json` schema transform missing from Fix 5 spec** — without
  `d['request']['body']['messages']` instead of `d['messages']`, 17% of files produce zero
  summaries. Plan said "handles BOTH file types" but didn't describe the transform.
- Stale docstrings at `hebbian_session_learner.py:8` and `hebbian_seed_sessions.py:1-9`
  still mention `decisions.jsonl` after Fix 2 deletion
- Fix 1 → Fix 3 critical dependency not in v2's "Critical order dependencies" list

## Verification Discipline (worked well)

Every "missing" or "wrong" claim from the subagents was verified by main-session grep/sqlite3/
python before being incorporated into the v3 plan. Pattern:

```bash
# 1. Subagent claims X is missing — grep directly
grep -rn "X" /root/.hermes/ --include="*.py" --include="*.service" --include="*.timer" 2>/dev/null

# 2. Subagent claims Y schema is wrong — verify with sqlite3
sqlite3 /root/.hermes/data/signals_hermes.db ".schema ohlcv_1m"
sqlite3 /root/.hermes/data/signals_hermes.db "SELECT COUNT(DISTINCT token) FROM ohlcv_1m"

# 3. Subagent claims Z file has property W — read the actual file
# (this is the step that caught the hebbian_learner.py false positive)

# 4. Subagent claims line range is X-Y — read that range in the actual file
sed -n 'X,Yp' /root/.hermes/scripts/file.py
```

**One subagent claim turned out to be partially wrong:**
Subagent 2 said `request_dump_*.json` body "requires `json.loads(d['request']['body'])` first
because the body field is a stringified JSON blob." Verified directly: the body is a **dict**,
not a string. The transform is simple dict navigation (`d['request']['body']['messages']`),
not double-parsing. R10 was real but the subagent overstated the severity. This is a
legitimate subagent failure mode: **subagents sometimes add complexity to a finding to make
it sound more dramatic.** Always verify the actual data shape.

## T's Communication Style Lesson

T said: "I rarely use all caps, when I do it is usually a coin name that I am drawing your
attention to."

This is a **design constraint** for any system that filters ALL_CAPS text in Hermes:
- T uses all-caps as a deliberate signal channel for coin tickers he wants attention drawn to
- A strict `lt == "token"` gate on ALL_CAPS extraction is correct under this assumption
- Acronyms (API/SQL/JSON) stay in the stopword set
- The only loss is brand-new HL listings referenced before candle data lands (rare,
  self-correcting on next module import)

This generalizes beyond the Hebbian system. Any recall/extraction logic that touches
ALL_CAPS words should default to the strict-token-only filter and let the user explicitly
add new acronyms to a stopword exemption list if needed.

## Files Touched

- **Read:** `/root/.hermes/scripts/hebbian_engine.py`, `hebbian_entity_extractor.py`,
  `hebbian_seed_sessions.py`, `hebbian_session_learner.py`, `hebbian_learner.py` (the
  false-positive case), SOUL.md, associative-recall SKILL.md
- **Modified:** `/root/.hermes/scripts/hebbian_entity_extractor.py` (Fix 1 — HL_COINS
  loader, infer_label check, ALL_CAPS filter)
- **Plan updated:** `/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24-v3.md`
  (998 lines, v2 was 480)

## Plan Evolution

- v1 → v2: single audit caught 5 silent bugs
- v2 → v3: dual audit + main-session verification caught 7 corrections + 7 missing risks +
  the hebbian_learner.py refactor (turned a "delete" recommendation into a 175-line Fix 1b)
- **Total findings: 11 corrections, 11 risks, 1 architectural pivot**

## Delegation Hygiene That Worked

- **Specific checklist items, not "audit this"** — 8 items capped, 8-10 max per the
  pattern documented in the parent SKILL.md
- **Pre-verified file paths and line counts in main session** before delegating
- **Background dispatched, main session kept working** — both delegations ran in parallel
- **All "missing" claims re-verified in main session** before incorporating
- **First delegation result was lost** (process list empty when I checked) — second
  delegation was redundant but completed anyway. Lesson: the dispatch tool's "process list"
  doesn't track subagents the same way it tracks `terminal` background processes. Subagents
  write results to `/tmp/hermes-results/` which the main session doesn't see until the
  async completion message arrives.