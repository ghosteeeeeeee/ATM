---
name: associative-recall
description: Query and write to Hermes's Hebbian associative memory network (SQLite at /root/.hermes/brain/associative_memory.db). Use when you want to recall prior context for a concept, file, coin, skill, or project — and when finishing meaningful work that should be remembered across sessions.
---

# Associative Recall — Hebbian Memory Network

This skill covers the *current* state of Hermes's Hebbian memory, not the aspirational state. The network exists, it works, and it has known bugs that bias its recall. Read this whole file before trusting any recall result.

## Network state (as of 2026-06-24, post-Fix 1+1b+2)

- DB: `/root/.hermes/brain/associative_memory.db` (SQLite, WAL)
- 989 nodes / 13,506 synapses (post brain-md reseed via Fix 1b)
- Schema: `concept_nodes` (id, name, label_type, created_at, last_seen) + `synapse_weights` (concept_a_id, concept_b_id, weight 0.5-100, co_occurrences, last_updated)
- Engine: `/root/.hermes/scripts/hebbian_engine.py`
- **Fix 1 applied**: `HL_COINS` (104 live coins) loaded from `signals_hermes.db.ohlcv_1m.token`; `infer_label` and `extract_entities` now filter ALL_CAPS to require `lt == "token"` (no more random uppercase → token pollution)
- **Fix 1b applied**: `hebbian_learner.py` refactored — now imports `infer_label` + `HL_COINS` from `hebbian_entity_extractor.py` (single source of truth), uses markdown-specific extractor (30-concept cap per file), priority script list replaces dead hardcoded paths (`signal_gen.py`, `ai_decider.py` excluded; `signal_compactor.py` is LIVE — see Naming Convention pitfall below)
- **Fix 2 applied**: `seed_decisions_log()` and `learn_from_decisions_log()` fully DELETED from `hebbian_seed_sessions.py` and `hebbian_session_learner.py` (function bodies removed, not stubbed; call sites removed; docstrings updated). The trade-decision pollution source is gone — but the DB still contains its residue until Fix 3 wipes + reseeds.
- Decay timer: `hermes-hebbian-decay.timer` (currently DISABLED — must be enabled for ongoing maintenance)
- Session learner timer: `hermes-session-learner.timer` (currently DISABLED)
- Brain-seeder timer: `hermes-brain-seeder.timer` (NEW — not yet created, will run `hebbian_learner.py --since 168h` weekly on Sundays 03:00 UTC)

## Known biases in the current network

These are real bugs, not theoretical concerns — verify before relying on recall.

### 1. Trade-decision pollution (RESIDUE from pre-Fix-2 bug)

**Status (2026-06-24, post-Fix 2)**: the pollution SOURCE is removed (`seed_decisions_log` and `learn_from_decisions_log` deleted from `hebbian_seed_sessions.py` and `hebbian_session_learner.py` — function bodies gone, not stubbed). No new pollution will be added. However, the existing DB still contains thousands of pre-Fix-2 polluted edges:
- `SKIPPED <-> NEUTRAL`: 1066 fires
- `HOT_APPROVED <-> LONG_BIAS`: 2434 fires
- `LONG_BIAS <-> GALA`: 239 fires
- `LONG_BIAS <-> ZEC`: 413 fires

**Symptom (until Fix 3 wipes the DB)**: recall on any token (e.g. `ETH`, `BTC`) may still return `LONG_BIAS/SHORT_BIAS/NEUTRAL/HOT_APPROVED/APPROVED/SKIPPED/WAIT` from the old polluted edges, drowning out the new clean associations from Fix 1b's reseed.

**Resolution**: Fix 3 (backup + spot-check + `clear_all` + reseed) removes the residue. Until then, restrict recall queries to file/skill/concept labels or apply a post-filter that drops edges where one endpoint is `decision` or `regime`.

**Lesson for future audits**: a function whose only job is creating pollution should be DELETED entirely (body + signature + call sites), not stubbed with `return 0` or `NotImplementedError`. A stub still appears in `hasattr()` and `dir()` checks, and a future patch might accidentally re-call it. The grep verification is: `grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/*.py | grep -v .bak` should return empty.

### 2. ALL_CAPS entity extractor matches random text

`hebbian_entity_extractor.py` uses `\b([A-Z]{2,8})\b` to find tokens. This catches `2Z`, `ME`, `IP`, `GAS`, `DASH`, `MAV` — random uppercase words — and labels them as "token". The actual HL coin universe should be the only source of token labels. Until that's fixed, recall on a real coin like `XLM` competes with garbage nodes.

### 3. Duplicate extractors across 4 files

`infer_label` and `extract_entities` / `extract_concepts` are reimplemented (with subtle differences) in:
- `/root/.hermes/scripts/hebbian_learner.py`
- `/root/.hermes/scripts/hebbian_seed_sessions.py`
- `/root/.hermes/scripts/hebbian_entity_extractor.py`
- `/root/.hermes/scripts/hebbian_session_learner.py`

Each ships its own `KNOWN_TOKENS` / `KNOWN_SKILLS` / `infer_label` block. New coin entries must be added in all four places to actually take effect.

### 4. Timers disabled

`hermes-hebbian-decay.timer` and `hermes-session-learner.timer` are loaded but not enabled. Network is static — no decay, no new learning from new sessions. If you want ongoing maintenance, enable both:
```bash
systemctl --user enable --now hermes-hebbian-decay.timer
systemctl --user enable --now hermes-session-learner.timer
```

### 5. "9,705 sessions → 1.04M pairs" claim in PROJECTS.md is false

Either the seeder never ran, or it ran and the DB got wiped/rebuilt since. Actual current state is 144 nodes. Don't trust claims in PROJECTS.md about Hebbian state without verifying.

## Session file locations and the prompt-injection trap

Session dumps live at `/root/.hermes/sessions/` (NOT `/root/.hermes/brain/` — that's where the SQLite DB lives):

- `request_dump_*.json` (844 files): raw HTTP request bodies including `Authorization: Bearer *** headers and `sk-...` API keys
- `session_*.json` (4,007 files): full session records with `system_prompt` field containing the entire 38,830-char SOUL.md

When backfilling or extracting from these files:

1. **Skip the `system_prompt` field** in `session_*.json` during entity extraction. Including it would create 4,007 duplicate co-occurrences of every concept in SOUL.md and pollute the graph with boilerplate.
2. **Strip API keys** before persisting any extracted text. Use regex `sk-[a-zA-Z0-9-]{20,}` and `Bearer [^\s"]+`. Don't include raw `request.headers` in extracted text — only `request.body.messages[*].content` is safe.
3. **Don't include raw `Authorization` headers** in any `summary` or text field that ends up in the DB.

## Sibling extractor file (hebbian_learner.py) — RESOLVED via Fix 1b

`/root/.hermes/scripts/hebbian_learner.py` was a SIBLING to `hebbian_entity_extractor.py` with its own:
- `infer_label()` 
- `extract_concepts()` (markdown-specific, NOT the same as `extract_entities` for chat text)
- `normalize_concept()`
- `seed_from_file()`

**Status as of 2026-06-24**: Fix 1b landed. `hebbian_learner.py` now imports `infer_label` and `HL_COINS` from `hebbian_entity_extractor.py` (single source of truth for vocabularies) but keeps its own `extract_concepts` (markdown-specific — see Concept Extractor Explosion pitfall below) and `normalize_concept` (handles markdown-specific whitespace/quote stripping).

**Naming convention for trading scripts** (caught by audit 2026-06-24): the convention is `signal_<topic>.py` — `signal_compactor.py`, `accel_300.py`, etc. are all LIVE. Only `signal_gen.py` and `ai_decider.py` are truly defunct. **Always verify a script is actually defunct before adding to a DEAD list** — don't rely on memory/SOUL.md labels alone. `grep -L <dead_script_name>` for current callers.

## SOUL.md edits always need a backup

Any edit to `/root/.hermes/SOUL.md` (the live agent system prompt) should be preceded by:
```bash
cp /root/.hermes/SOUL.md /root/.hermes/SOUL.md.bak-$(date +%Y-%m-%d)
```
The plan's backup of `associative_memory.db` does NOT cover SOUL.md — manual rollback is required if a section edit breaks the agent's self-model.

## Existing "When to recall" trigger table is duplicated

The trigger table content lives in `/root/.hermes/skills/associative-recall/SKILL.md` line ~62 (`## When to recall (prompt-injection triggers)`). When updating SOUL.md to add recall guidance, **point to the skill rather than duplicating the table** — otherwise the two will drift.

## Visible-mode weight threshold must be reachable

Current DB stats (post-bug): MAX weight = 99.5 (decay-multiplied, not co-occurrence count), AVG = 34.1, COUNT = 602. After a full wipe + reseed the DB starts at weight 1.0 per synapse and reaches 5.0 only after 4+ co-occurrences. **A `weight >= 5.0` threshold for visible recall is unreachable for weeks post-reset.** Use `>= 2.0` for the first 30 days, or drop the threshold and just surface the top-1 association if any exist.

## Session dump backfill defaults

The plan's `hebbian_session_distill.py` (when written) should default to:
- Process all 4,851 files in a single nohup'd run (5-15 min)
- Use heuristic-only summaries (no LLM) for deterministic, fast, offline-capable backfill
- Idempotency via `session_summaries.session_id UNIQUE` + `INSERT OR REPLACE` (schema-enforced)
- Discussion type heuristic: drop AND-conditions on `bug_fix` — most bug reports describe the problem without stating the fix in the same opening line

## When to recall (prompt-injection triggers)

The SOUL.md memory block tells you to recall proactively. Specific triggers:

| T's message contains | Recall these concepts |
|---|---|
| Session-start (any topic) | `trading`, `signal_compactor`, `Tokyo` (broad entry points) |
| Coin ticker (e.g. `XLM`, `ETH`, `SOL`) | that ticker |
| `.py` filename (e.g. `signal_compactor.py`) | filename with and without `.py` |
| "the X bug", "X is broken", "X issue" | `X` |
| "what did we do", "remind me" | concepts from message |

**Skip recall** for: greetings, status checks, smoke tests, "show me stats", pure commands.

## Recall command surface

### Engine CLI
```bash
python3 /root/.hermes/scripts/hebbian_engine.py recall <concept> [k]
python3 /root/.hermes/scripts/hebbian_engine.py stats
python3 /root/.hermes/scripts/hebbian_engine.py decay
python3 /root/.hermes/scripts/hebbian_engine.py clear_all    # wipes DB
```

### MCP tools (preferred when available)
- `mcp_hermes_coding_mcp_hebbian_recall(concept, k)` — returns ranked associations
- `mcp_hermes_coding_mcp_hebbian_learn(a, b)` — record a co-occurrence
- `mcp_hermes_coding_mcp_hebbian_stats()` — network stats

Use MCP when the tooling allows it; falls back to CLI.

### Session learner
```bash
python3 /root/.hermes/scripts/hebbian_session_learner.py [days_back]
python3 /root/.hermes/scripts/hebbian_session_learner.py --dry-run
```

## How to surface recall results (visible mode)

Per T's preference, recall should be **visible**, not silent. Format:
- "I recall we discussed X in a prior session — Y."
- "[Recall] signal_compactor.py was last touched 2026-06-23: accel_300 wrong-direction bug fix."

Only surface when associations are meaningful (weight >= ~5.0, not noise). Don't fabricate recall that isn't there.

## When to write to the graph

Trigger `hebbian_learn` or run the session learner when:

| Event | Action |
|---|---|
| Bug fix completed | Learn pair: `bug:subject` <-> `file:script.py` |
| Plan / decision made | Learn pair: `decision:topic` <-> relevant files/concepts |
| File modified | Learn pair: `file:script.py` <-> `change:<type>` |
| New lesson learned | Learn pair: `lesson:topic` <-> affected files/systems |
| Coin-specific discussion | Learn pair: `token:COIN` <-> discussion topic |

**Do NOT learn**:
- Routine commands ("show me stats", "run smoke test")
- Per-trade decisions (use separate trade brain)
- Repeated boilerplate (capped by weight ceiling anyway)
- Failed/empty turns

## Pitfalls (real ones from past sessions)

1. **Don't trust recall on coin tickers in the current state** — the trade-log pollution drowns out everything else. Either fix the extractor + reseed, or restrict recall queries to file/skill/concept labels (not token labels).
2. **Don't add a coin to only one KNOWN_TOKENS list** — there are 4 of them. Add to all.
3. **Don't call `clear_all` without backing up first** — `cp associative_memory.db associative_memory.db.bak-YYYY-MM-DD`.
4. **Don't enable both timers without first fixing the decision-log pollution** — otherwise decay never catches up with new noise being added.
5. **Don't assume label_type distribution is balanced** — the current graph is 137/144 tokens, 4 decisions, 3 regimes. No file/skill/project labels exist. Anything inferred from label_type stats is misleading.
6. **Don't use the `decisions.jsonl` co-occurrence fires as a "signal of activity"** — they fire on every trade cycle (5,086 entries in current log) regardless of whether there was real conversation.
7. **Concept Extractor Explosion (caught 2026-06-24 Fix 1b)**: when a markdown seeder uses `extract_entities` (tuned for chat text with CamelCase, AT_MENTIONS, all-caps coins), it finds 200+ concepts per markdown doc. Then `seed_from_file` does all-pairs `learn_pair()` which is O(n²) — 200 concepts = 19,900 pairs per file. Run timed out at 180s after 6 files generating 95K synapses. **Fix**: use a markdown-specific extractor capped at 30 concepts per file (435 pairs max), with patterns limited to headers, inline code, bold, file paths, and all-caps-coins-only. Extractors tuned for chat text are not interchangeable with markdown content.
8. **`normalize_concept` regexes must NOT strip underscores** (caught 2026-06-24 Fix 1b): `re.sub(r'[`*_~<>]', '', name)` looks harmless but turns `/root/.hermes/scripts/signal_compactor.py` into `/root/.hermes/scripts/signalcompactor.py`. Underscores are part of every Python file path (`signal_compactor`, `hl-sync-guardian`, `accel_300`, etc.). When you later recall by exact filename, the node is missing because the underscore was stripped. **Fix**: exclude `_` from the strip pattern, or use a path-aware normalize that preserves filename structure.
9. **T's all-caps communication style** (caught 2026-06-24): when T writes something in ALL CAPS, he is drawing attention to a coin ticker (BTC, ETH, XLM, etc.). Non-coin all-caps (FOMC, SEC, etc.) are noise. The strict `if lt == "token"` gate in the ALL_CAPS regex is correct under this assumption — it filters noise while preserving signal. Don't loosen this filter without checking with T first.
10. **Greedy regex captures code as concepts** (caught 2026-06-24 Fix 1b): `\*\*([^*]+)\*\*` (bold text regex) and `/root/\.hermes/[^\s]*\.(?:py|json|...)` (file path regex) both have greedy `[^*]+` / `[^\s]*` quantifiers that capture huge multi-line code blocks when markdown content contains `**...code...**` wrapping or `path/.something` mid-sentence. The DB ended up with a node containing the entire `hl-sync-guardian.py` body. **Fix**: bound with `{2,60}` char limits, exclude `=`, `{`, `(`, `*` from content, and require paths to end in a recognizable extension (`.py|.json|.md|.db|.log`).
11. **`clear_all` is a Python API only, not a CLI subcommand** (caught 2026-06-24 Fix 1b): `python3 hebbian_engine.py clear_all` returns "Unknown command". You must call it from Python: `python3 -c "from hebbian_engine import HebbianEngine; e = HebbianEngine(); e.clear_all()"`. Useful for resetting the DB between test runs of the seeder without leaving 95K-synapse garbage behind.
12. **Audit subagents misclassify sibling files as "parallel pollution sources"** (caught 2026-06-24): when a subagent sees two files with similar function definitions (e.g. `infer_label()` in both `hebbian_entity_extractor.py` and `hebbian_learner.py`), it can flag the second as redundant or polluting WITHOUT verifying what the second file actually does. `hebbian_learner.py` is the brain-md seeder (markdown docs → co-occurrences from `brain/*.md`, `skills/*/SKILL.md`, and trading scripts) — fundamentally different from `hebbian_entity_extractor.py` which extracts from chat text. **Verification before accepting the audit**: `read_file` the actual function bodies and the docstrings, and check the FILE-LEVEL docstring to see what the file's purpose is. A subagent that says "file X is duplicate of file Y" should be backed by a grep showing the same imports + same callers + same downstream usage — none of which was true here.
13. **Delete pollution sources completely, don't stub them** (learned 2026-06-24 Fix 2): when removing a polluting function, deleting the function body (keeping the signature) creates a footgun — `hasattr()` still returns True, `dir()` still lists it, and a future patch may accidentally re-call it. The first attempt at Fix 2 left `def learn_from_decisions_log(): return 0` as a stub; the second pass removed the function entirely (body + signature + call sites + comments). **Verification**: `grep -rn "<func_name>" /root/.hermes/scripts/*.py | grep -v .bak` should be EMPTY (not just match the def line with a stub body). If the grep returns anything in non-backup files, the deletion is incomplete.
14. **T's naming convention for trading scripts** (verified 2026-06-24): the convention is `signal_<topic>.py` — `signal_compactor.py`, `signal_run.py`, `accel_300_signals.py` are all LIVE. Only `signal_gen.py` and `ai_decider.py` are truly defunct (replaced by `signal_compactor.py`). Before adding ANY script to a DEAD/DEFUNCT exclusion list, verify with `ls -la /root/.hermes/scripts/<name>.py` and grep for actual imports (`grep -rn "from <module>\|import <module>" /root/.hermes/ --include="*.py"`). Don't trust SOUL.md or memory labels alone — they can be stale or wrong about which scripts are alive.

## Verification recipe

After any change to extractors/seeders, run this and check the result makes sense:

```bash
# 1. Stats sanity
python3 /root/.hermes/scripts/hebbian_engine.py stats

# 2. Recall on real concepts should return useful stuff
python3 /root/.hermes/scripts/hebbian_engine.py recall signal_compactor
python3 /root/.hermes/scripts/hebbian_engine.py recall XLM
python3 /root/.hermes/scripts/hebbian_engine.py recall Tokyo

# 3. Recall should NOT return only regime/decision noise
python3 /root/.hermes/scripts/hebbian_engine.py recall ETH
# If this returns only LONG_BIAS/HOT_APPROVED/etc., the graph is still polluted.

# 4. Label distribution should include file/skill/concept, not be dominated by token/decision/regime
sqlite3 /root/.hermes/brain/associative_memory.db \
  "SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type ORDER BY 2 DESC;"
```

## Related files

- `/root/.hermes/scripts/hebbian_engine.py` — core engine
- `/root/.hermes/scripts/hebbian_learner.py` — initial seeding from brain/*.md (Fix 1b refactor: imports from entity_extractor)
- `/root/.hermes/scripts/hebbian_seed_sessions.py` — retroactive seed from request_dump_*.json + decisions.jsonl
- `/root/.hermes/scripts/hebbian_entity_extractor.py` — surface entity extraction (Fix 1: HL_COINS filter)
- `/root/.hermes/scripts/hebbian_session_learner.py` — daily session learner
- `/root/.hermes/brain/associative_memory.db` — the DB
- `/root/.hermes/.config/systemd/user/hermes-hebbian-decay.{service,timer}`
- `/root/.hermes/.config/systemd/user/hermes-session-learner.{service,timer}`

## Session references

- `references/network-diagnostic-2026-06-24.md` — initial diagnostic + biases
- `references/hebbian-fix-1-1b-session-2026-06-24.md` — Fix 1 + Fix 1b reproduction recipe, bugs caught, verification chain
- `references/hebbian-fix-2-session-2026-06-24.md` — Fix 2 (delete decisions.jsonl learning): the two-pass deletion lesson and verification recipe