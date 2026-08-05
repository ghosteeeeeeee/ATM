# Audit: Surface pattern ≠ root cause (hebbian_learner.py, 2026-06-24)

This reference documents a subagent false-positive that caused real damage to the plan
(`/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24.md` v3, since corrected).

## What happened

Two parallel ai-engineer audits were dispatched on the Hebbian integration plan. Both audits
flagged `/root/.hermes/scripts/hebbian_learner.py` (182 lines) as a "parallel pollution source"
or "redundant extractor" because it had its own `infer_label()` (L37), `extract_concepts()` (L52),
`normalize_concept()` (L95), and `seed_from_file()` (L103). The audit conclusions:

- "Delete it, or apply Fix 1's filter, otherwise it keeps polluting the DB."
- "Add to Precheck P0 outcomes A/B/C: delete / refactor / apply Fix 1 changes."

The main session accepted this framing and wrote a "Precheck P0 — investigate callers" section
recommending deletion as the first outcome (Outcome A).

## Why it was wrong

`hebbian_learner.py` is a **markdown brain seeder**. Read its actual code:

- Docstring (L1-9): "Hebbian Network Seeder — bootstraps initial synapses from existing brain files.
  Scans all brain/*.md files and extracts co-occurring concepts, seeding the associative memory
  network so it's not empty on day one."
- `main()` (L135-179): builds a `HebbianEngine`, calls `clear_all()`, then iterates:
  1. `BRAIN_DIR.glob("*.md")` — TASKS.md, PROJECTS.md, trading.md, lessons.md, ideas.md, etc.
  2. Hardcoded list of "key scripts" (L154-161) — though this list references dead files
  3. `SKILLS_DIR.glob("*/SKILL.md")` — the skill documentation files
- For each file, calls `seed_from_file()` which extracts concepts and writes co-occurrence pairs
  via `engine.learn_pair(a, b, lt_a, lt_b)`.

The data source is **T's own written knowledge** — TASKS.md, PROJECTS.md, trading.md are
high-signal project documentation with deliberate concept co-occurrences (skill refs, file refs,
infra refs, coin refs all appear in natural context). This is exactly the data source that
Fix 3's reseed should be drawing from. The reason it has zero live callers is that **it was never
wired to a timer** — not that it was abandoned.

## The structural pattern that misled the subagent

The subagent saw:
- Same function name as `hebbian_entity_extractor.py` (`infer_label`, `extract_concepts`)
- Same vocabulary constants (`KNOWN_TOKENS`, `KNOWN_SKILLS`, `KNOWN_INFRA`, `KNOWN_FILES`)
- Same imports (`from hebbian_engine import HebbianEngine`)
- No live callers anywhere in `*.py`, `*.service`, `*.timer`, `*.sh`

It concluded: "Same purpose, no callers, current code is broken — must be pollution source or
dead code." This is a *structural* match (file-shape similarity) but the subagent never read
the docstring or `main()` to verify the *semantic* role.

## The lesson (encoded in ai-engineer SKILL.md Pattern 62)

When a subagent flags a file as "redundant / parallel / pollution source" purely on the basis
of structural similarity:

1. **Read the file's docstring (L1-10).** One sentence usually tells you the purpose.
2. **Read its `main()` or top-level entry.** This shows the actual data flow: what it reads,
   what it writes, what state it mutates.
3. **Grep for output consumers, not just code callers.** A file may produce JSON/SQLite/files
   that other components read without importing the file's symbols.
   `grep -rn "output_table\|output_path\|writes_to"` on the file's known outputs.
4. **Check git log if available.** `git log --follow --oneline -- path/to/file` shows whether
   it was ever wired up, intentionally archived, or replaced.
5. **Asymmetric risk:** deleting wrong is permanent; integrating wrong is reversible. When in
   doubt, prefer the reversible action.

## The same pattern in code review (not just subagents)

This trap also applies when reading code directly:

- Two functions with the same name in different modules are often *intentionally* parallel
  (different input domains, different output consumers)
- A file with zero imports can still be a critical data source if it produces files/DB rows
  consumed by other tools
- A file with hardcoded paths to dead files is *stale*, not *dead* — the question is whether
  the *concept* it implements is still wanted, not whether the specific paths are still valid

## What we did instead (the fix)

After T pushed back, the main session rewrote Precheck P0 as Fix 1b:

- **Import from `hebbian_entity_extractor.py`** (single source of truth — `infer_label`,
  `HL_COINS`, `extract_concepts`)
- **Fix hardcoded script list at L154-161** — use `scripts_dir.glob("*.py")` filtered by size,
  no dead filenames
- **Add `--since`, `--dry-run`, `--clear` flags** — enables incremental mode for the new
  weekly systemd timer
- **Wire `hermes-brain-seeder.timer`** — Sunday 3am UTC, picks up anything modified in last 7
  days via `--since 168h`

Net result: instead of deleting a critical data source, we made it work. Plan now produces
**thousands of high-quality co-occurrences** from T's documented knowledge, automatically
refreshing weekly.

## Reproducer for future audits

If you see a subagent flagging a file as "redundant/parallel" with similar reasoning:

```python
# In main session, before accepting the framing:
def audit_subagent_framing(filepath):
    # 1. Docstring check
    with open(filepath) as f:
        head = "".join(f.readlines()[:15])
    if "seeder" in head.lower() or "extracts from" in head.lower():
        print("⚠️  Likely a DATA PRODUCER, not a redundant extractor")

    # 2. main() check
    import re
    content = open(filepath).read()
    if re.search(r'def main\(' * ', content):
        m = re.search(r'def main\([^)]*\):(.*?)(?=\ndef |\Z)', content, re.DOTALL)
        if m:
            body = m.group(1)
            # What does it write to?
            writes = re.findall(r'\.write\(|\.save\(|\.dump\(|INSERT|UPDATE|learn_pair', body)
            if writes:
                print(f"⚠️  main() writes: {writes} — this file PRODUCES data")

    # 3. Output consumer check
    # Look for tables, paths, files this script produces and grep for them
    for pattern in ['brain/associative_memory.db', 'output.json', 'summary']:
        consumers = subprocess.run(['grep', '-rln', pattern, '/root/.hermes/'],
                                    capture_output=True, text=True)
        if consumers.stdout.strip():
            print(f"⚠️  Output {pattern} consumed by: {consumers.stdout.strip()[:200]}")
```

If any of these checks fire, the file is NOT dead code — it's a data producer that needs to
be wired up, not deleted.

## Related references in this skill

- ai-engineer SKILL.md Pattern 62 (surface pattern ≠ root cause) — the rule
- ai-engineer SKILL.md Pattern 1, 21 (verify subagent findings in main session) — the
  discipline that should have caught this
- ai-engineer SKILL.md Pattern 63 (subagent delegation tracking) — adjacent workflow lesson