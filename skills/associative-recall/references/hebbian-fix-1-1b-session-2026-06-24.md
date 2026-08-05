# Hebbian Fix 1 + 1b — Session Transcript (2026-06-24)

This is a class-level reference: any future session touching the Hebbian memory
seeder/extractor system should read this BEFORE writing code. It captures
the actual reproduction recipe, the bugs we hit, and the verification chain.

## What got shipped this session

**Fix 1** — `hebbian_entity_extractor.py`:
- Added `HL_COINS` loader (104 live coins from `signals_hermes.db.ohlcv_1m.token`)
- `infer_label` now accepts coins from EITHER KNOWN_TOKENS or HL_COINS
- ALL_CAPS regex block now requires `lt == "token"` (filters garbage)
- Added 9-line docstring explaining why strict filter is correct for T's all-caps = coin style
- Backup: `hebbian_entity_extractor.py.bak-2026-06-24`

**Fix 1b** — `hebbian_learner.py`:
- Deleted duplicated vocabularies, imports `infer_label` + `HL_COINS` from extractor
- Kept local `extract_concepts` (markdown-specific, capped at 30 concepts per file)
- Kept local `normalize_concept` (preserves underscores, filters code patterns)
- Replaced dead hardcoded script list with glob + 7-script priority list
- Added CLI flags: `--since`, `--dry-run`, `--clear`
- Backup: `hebbian_learner.py.bak-2026-06-24`

## Audit chain (the meta-lesson)

This session ran THREE audits on the integration plan before shipping Fix 1:

1. **Audit v1 (366s, 15 file reads)** — original audit, caught 5 silent bugs in v1 plan
2. **Audit v2 (subagent 266s, 11 API calls)** — second pass, found 7 corrections + 7 missing risks
3. **Audit v3 (subagent 171s, 7 API calls)** — caught the schema transform for request_dump_*.json

Each audit was verified by main-session grep + sqlite3 + python — subagent claims
were checked, not trusted (per ai-engineer skill Pattern 1: "verify-don't-trust").

## Bugs caught during Fix 1b testing (in order of discovery)

Each bug required a re-test cycle. The verification chain was:
patch → syntax check → clear DB → live run → recall test → debug.

### Bug 1: signal_compactor.py missing from script list

**Symptom**: dry-run showed only 3 scripts in `--since 720h` window, none of them priority scripts.

**Root cause**: original `[:30]` alphabetical cap put `signal_compactor.py` at position 111 of 136 eligible scripts — beyond the cap.

**Fix**: added `PRIORITY_SCRIPTS` list at the top of the glob output. Cap raised from 30 to 50.

### Bug 2: signal_gen.py and ai_decider.py in the eligible list

**Symptom**: dry-run showed deprecated scripts in the script list.

**Root cause**: glob matched them based on size filter, no name-based exclusion.

**Fix**: added `DEAD_SCRIPTS` exclusion set.

### Bug 3: Wrong deprecation flag on signal_compactor.py (T's correction)

**Symptom**: I had `signal_compactor.py` in DEAD_SCRIPTS based on memory label.

**T's correction** (delivered mid-task): "signal_compactor is defunct, but that naming convention is used for all .py files, accel_300.py for example". The convention is `signal_<topic>.py` and signal_compactor.py is the LIVE one.

**Root cause**: trusted SOUL.md memory label without verifying. Memory said "signal_compactor.py <-- main signal decision maker" but I had it backwards.

**Lesson**: never put a file in DEAD_SCRIPTS without grep -L verification.

### Bug 4: O(n²) concept explosion — RUN TIMED OUT

**Symptom**: `timeout 180 python3 hebbian_learner.py` exited at 180s. DB had 95,035 synapses from 6 brain files alone.

**Root cause**: `extract_entities` from `hebbian_entity_extractor.py` is tuned for chat text and finds 200+ concepts per markdown doc. `seed_from_file` does all-pairs `learn_pair()` = O(n²). 222 concepts in DECISIONS.md alone = 24,531 pairs in 41 seconds.

**Fix**: kept a local `extract_concepts` in `hebbian_learner.py` that is markdown-specific:
- Headers (`## ...`, `### ...`)
- Inline code (`` `something` ``) — bounded to single line
- Bold (`**...**`) — bounded to `{2,60}` chars, no `=`, `{`, `(`
- File paths (must end in `.py|.json|.md|.db|.log|.sh|.txt|.csv`)
- ALL_CAPS coins (must be in HL_COINS or KNOWN_TOKENS)
- Capped at 30 concepts per file = 435 pairs max per file

**Result**: 8,063 pairs in 13 seconds for all 21 brain files (was 95K synapses in 58s for 6 files).

### Bug 5: Greedy bold regex captured entire hl-sync-guardian.py body

**Symptom**: DB had a concept node containing the entire 4250-line `hl-sync-guardian.py` source as a "file" concept.

**Root cause**: `\*\*([^*]+)\*\*` matched everything between `**` and the next `**`, including newlines and code.

**Fix**: `\*\*([^*\n=]{2,60})\*\*` — exclude newlines, exclude `=`, bound length to 60.

### Bug 6: Greedy file path regex captured large code chunks

**Symptom**: 56 garbage "file" concepts longer than 60 characters in the DB after re-seed.

**Root cause**: original `[^\s\`\'")\]]+` was too permissive — captured everything until whitespace.

**Fix**: required `.py|.json|.md|.db|.log|.sh|.txt|.csv` extension at end: `/root/\.hermes/[^\s\`\'")\]]*\.(?:py|json|md|db|log|sh|txt|csv)`.

### Bug 7: Trailing quote in file paths

**Symptom**: DB had `/root/.hermes/data/candles.db'` (with trailing apostrophe) as a concept.

**Root cause**: original regex excluded whitespace, backtick, paren, bracket but NOT single quote.

**Fix**: added `'` and `"` to exclusion set: `[^\s\`\'")\]]`.

### Bug 8: normalize_concept stripped underscores from file paths

**Symptom**: DB had `/root/.hermes/scripts/signalcompactor.py` (NO underscore). Recall for `/root/.hermes/scripts/signal_compactor.py` returned empty.

**Root cause**: `re.sub(r'[`*_~<>]', '', name)` removed underscores from path strings.

**Fix**: removed `_` from the strip pattern. Underscores are part of every Python file path — they MUST survive normalization.

## Verification recipe (use after any seeder/extractor change)

```bash
# 1. Syntax check
python3 -m py_compile /root/.hermes/scripts/hebbian_learner.py
python3 -m py_compile /root/.hermes/scripts/hebbian_entity_extractor.py

# 2. Clear DB (this is Python API, not CLI)
PYTHONPATH=/root/.hermes/scripts python3 -c "from hebbian_engine import HebbianEngine; e = HebbianEngine(); e.clear_all()"

# 3. Live seed run (should take <60s for 85 files)
timeout 90 python3 /root/.hermes/scripts/hebbian_learner.py

# 4. Verify
PYTHONPATH=/root/.hermes/scripts python3 /root/.hermes/scripts/hebbian_engine.py stats
# Expected: 800-1200 nodes, 12000-18000 synapses, healthy label mix

# 5. Recall smoke tests
python3 /root/.hermes/scripts/hebbian_engine.py recall BTC
# Expected: ETH, SOL, AVAX, LINK with weights >= 10

python3 /root/.hermes/scripts/hebbian_engine.py recall /root/.hermes/scripts/signal_compactor.py
# Expected: file associations + coin associations, NOT empty

# 6. Garbage check
sqlite3 /root/.hermes/brain/associative_memory.db \
  "SELECT COUNT(*) FROM concept_nodes WHERE label_type='file' AND LENGTH(name) > 60;"
# Expected: < 15 (was 56 before fixes)
```

## Open follow-ups (NOT done in this session)

- Fix 2: delete `seed_decisions_log` and `learn_from_decisions_log` (still polluting the live pipeline) — ✅ DONE in Fix 2 session, see `hebbian-fix-2-session-2026-06-24.md`
- Fix 4: add `session_summaries` table
- Fix 5: write `hebbian_session_distill.py` (with schema transform + secret stripping)
- Fix 6: update SOUL.md to point to skill (not duplicate trigger table)
- Fix 7: enable systemd timers + new `hermes-brain-seeder.timer`

Full plan: `/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24-v3.md` (990 lines)