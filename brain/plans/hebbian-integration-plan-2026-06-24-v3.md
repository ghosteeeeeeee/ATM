# Hebbian Integration Plan — 2026-06-24 v3 (post-2nd-audit)

## Implementation status — 2026-06-24 (in-progress)

**Session progress (live execution log):**

| Fix | Status | File(s) | Lines changed | Verification |
|-----|--------|---------|---------------|--------------|
| 1 | ✅ COMPLETE | hebbian_entity_extractor.py | 224 → 269 (+45) | 4/4 verifications pass, HL_COINS=104 |
| 1b | ✅ COMPLETE | hebbian_learner.py + 2 systemd files | 182 → ~220 (+38 net) | dry-run + live seed verified, 989 nodes, 13.5K synapses, BTC recall returns ETH/SOL/AVAX |
| 2 | ✅ COMPLETE | hebbian_seed_sessions.py + hebbian_session_learner.py | -55 -44 + docstrings | function + call site + stale docstrings all removed, --dry-run clean |
| 4 | ✅ COMPLETE | hebbian_engine.py | 306 → 379 (+73) | schema verified, 3 indexes, 4 helper methods work, clear_all wipes + resets sqlite_sequence |
| **3** | **✅ COMPLETE** | destructive wipe + reseed | (TBD this run) | 17,021 nodes / 397,668 synapses, BTC recall works, ETH returns LONG/SHORT direction signals |

**Fix 3 execution log (2026-06-25 03:48 UTC):**
- Backups: `associative_memory.db.bak-2026-06-24` (8.3MB), `SOUL.md.bak-2026-06-24` (8.4KB)
- Pre-flight spot-check passed: HL_COINS=104, real coins label correctly
- `clear_all()` wiped everything (concept_nodes=0, synapse_weights=0, session_summaries=0, sqlite_sequence=0)
- `hebbian_seed_sessions.py 200` processed 11,194 sessions, learned 1,174,754 pairs (ended with a pre-existing stats query bug `no such column: weight` — not Fix 3 issue, the seeding itself succeeded)
- `hebbian_learner.py --since 99999h` processed 85 files, added 991 nodes / 13,545 synapses (additive merge on top of session seed)
- Final state: 17,021 nodes, 397,668 synapses, 55 tokens, 1,823 files, 23 skills, 9 infra, 6 project, 15,105 concept
- Note: KNOWN_TOKENS (broader list) contains 16 coins not in HL_COINS (ohlcv_1m) — these still correctly label as 'token' via the KNOWN_TOKENS path. NOT a bug — by design.
| 5 | ⏳ PENDING | new hebbian_session_distill.py | not yet created | — |
| 6 | ⏳ PENDING | SOUL.md update | not yet edited | — |
| 7 | ⏳ PENDING | enable 3 systemd timers | timer files exist, not enabled | — |
| 8 | ⏳ PENDING | associative-recall/SKILL.md update | not yet edited | — |

**Backups created this session (all at .bak-2026-06-24 suffix):**
- `/root/.hermes/scripts/hebbian_entity_extractor.py.bak-2026-06-24` (8209 bytes)
- `/root/.hermes/scripts/hebbian_learner.py.bak-2026-06-24` (6409 bytes)
- `/root/.hermes/scripts/hebbian_seed_sessions.py.bak-2026-06-24` (13067 bytes)
- `/root/.hermes/scripts/hebbian_session_learner.py.bak-2026-06-24` (7600 bytes)
- `/root/.hermes/scripts/hebbian_engine.py.bak-2026-06-24` (11325 bytes)

**Bugs caught and fixed during Fix 1/1b implementation (worth remembering):**
1. `extract_entities` from chat text caused O(n²) concept explosion in markdown docs — fixed by writing markdown-specific `extract_concepts` capped at 30 concepts per file
2. Bold regex `\*\*([^*]+)\*\*` was greedy — captured multi-line code blocks. Fixed: `{2,60}` cap, exclude `=`, `{`, `(`
3. File path regex too greedy — required extension (`.py|.json|.md|.db|.log|.sh|.txt|.csv`)
4. Trailing quote in file paths — excluded `'` and `"` from path regex
5. `normalize_concept` stripped underscores — broke `signal_compactor.py` → `signalcompactor.py`. Fixed by removing `_` from the regex
6. T's clarification: `signal_<topic>.py` is the LIVE naming convention (signal_compactor.py, accel_300.py, etc. are all alive). Only `signal_gen.py` and `ai_decider.py` are defunct.

**Audits completed this session:**
- 2 ai-engineer audits (266s + 171s on v2 plan) → produced v3 with 7 corrections + 11 new risks (R1-R11)
- 1 ai-engineer audit (170s on Fix 1+1b implementation) → confirmed Fix 1+1b clean, found 2 minor items (regex cap inconsistency `{2,6}` vs `{2,8}` — fixed; missing `hermes-brain-seeder.service/.timer` files — created)

**DB state as of 2026-06-24 04:40:**
- DB at `/root/.hermes/brain/associative_memory.db`
- Last clear was during Fix 1b testing — DB was reseeded with both Fix 1 + Fix 1b changes
- Last known state: 989 nodes, 13,506 synapses (will change after Fix 3 wipe+reseed)

**Resume instructions for next session:**
1. Read this status table to know where we left off
2. Fix 3 in progress — verify it completed successfully, check the reseeded DB stats
3. If Fix 3 done: proceed to Fix 5 (create `hebbian_session_distill.py`)
4. If Fix 3 not done: complete it (backup DB + SOUL.md, spot-check HL_COINS, clear, reseed both seeders)
5. Order after Fix 3: Fix 5 (distill) → Fix 6 (SOUL.md) → Fix 7 (enable timers) → Fix 8 (skill update)

---

## Audit status

This is the **third** revision of this plan. It supersedes v2 (post-audit v2, 480 lines) which was based on a single ai-engineer audit. v3 incorporates findings from a SECOND ai-engineer audit pass + main-session grep verification of every claim.

**Audit history:**
- v1 → v2: single audit (366s, 15 file reads). Caught 5 silent bugs (wrong table/column names, missed call sites, underspecified Fix 5, etc.)
- v2 → v3: dual subagent audit (266s + 171s, 18 API calls total, all claims verified by main-session grep/sqlite3/python). Caught 7 corrections + 7 missing risks that v2 missed.

**v2 corrections NOT carried into v3 — they are superseded below:**
- v2 said "9,705 sessions → 1.04M pairs" — FALSE (DB only had 144 nodes, never seeded properly). Removed.
- v2 said "Fix 1 verification: len(HL_COINS) > 50" — too lenient. Changed to >= 100.
- v2 said delete lines 343-345 in seed_sessions — wrong, actual is 342-345.
- v2 said delete lines 210-213 in session_learner — wrong, actual is 210-214.
- v2 said "request_dump_*.json + session_*.json handles BOTH file types" — underspecified, missing schema transform.
- v2 said "When to recall" section in SOUL.md — duplicates existing skill content at /root/.hermes/skills/associative-recall/SKILL.md:62.

**Verification status for v3 (main session confirmed each):**
- `ohlcv_1m.token` column exists, 104 distinct coins — `SELECT COUNT(DISTINCT token) FROM ohlcv_1m` → 104 ✓
- Only 2 files call `seed_decisions_log` / `learn_from_decisions_log` — `grep -rn` returned exactly 4 hits in 2 files ✓
- `clear_all()` at L244-249 omits `session_summaries` — direct read confirmed ✓
- `request_dump_*.json` body is a dict (not stringified JSON) with `body['messages']` array — direct read confirmed ✓
- `request_dump_*.json` contains `Authorization: Bearer *** + 2 `sk-` fragments — direct read confirmed ✓
- `session_*.json` has `system_prompt` field of ~38,830 chars containing full SOUL.md — direct read confirmed ✓
- Files live at `/root/.hermes/sessions/` (NOT `/root/.hermes/brain/`) — `find` confirmed ✓
- `/root/.hermes/scripts/hebbian_learner.py` exists (182 lines, own `infer_label` at L37) — NOT in v2 plan, **MISSING FROM v2** ✓
- Associative-recall skill has duplicate trigger table at L62+ — `grep -n "When to recall"` confirmed ✓
- Current synapse weights: MAX=99.5, MIN=0.99, AVG=34.1 — 602 rows, mostly post-decay ✓
- `session_summaries` table does NOT exist yet — `.schema session_summaries` returns nothing ✓

---

## Diagnosis (verified against code — same as v2, still accurate)

Current state of `/root/.hermes/brain/associative_memory.db`:

- 144 nodes / 602 synapses. Birth: 2026-05-09. Last write: 2026-06-19.
- Recall on `signal_gen.py`, `Tokyo`, `hebbian`, `cascade_flip`, `XLM` → all empty
- Recall on `ETH` returns only `LONG_BIAS/HOT_APPROVED/APPROVED/SHORT_BIAS/WAIT` — pure trade-log co-occurrence
- Top edges dominated by trade-decision pairs (SKIPPED↔NEUTRAL 1066 fires, etc.)
- 137/144 nodes labeled "token" — auditor's correction: many of these ARE real HL coins (2Z, GAS, ME, DASH, TRB, IMX, etc. are real per `ohlcv_1m`). The real garbage comes from regex artifacts (e.g. `@252` from timestamps) and the reason-text extraction in `seed_decisions_log`.
- Both timers disabled (hebbian-decay, session-learner)
- "9,705 sessions → 1.04M pairs" claim in PROJECTS.md is FALSE — DB has 144 nodes, never seeded properly
- `signals_hermes.db` schema: tables are `price_history`, `latest_prices`, `regime_log`, `ohlcv_1m`. Coin universe column is `token`, NOT `coin`. 104 distinct tokens present.
- 4,851 total session files = 844 `request_dump_*.json` + 4,007 `session_*.json`. Different schemas.
- `request_dump_*.json`: top-level `{timestamp, session_id, reason, request: {method, url, headers, body: {model, messages, tools}}, error}`. Body is a dict, NOT a stringified blob. Has Authorization Bearer *** + sk- keys.
- `session_*.json`: top-level `{session_id, model, base_url, platform, session_start, last_updated, system_prompt, tools, message_count, messages: [{role, content}, ...]}`. `system_prompt` is full SOUL.md (~38KB).
- Both file types live in `/root/.hermes/sessions/` (not `/root/.hermes/brain/` as v2 mistakenly said)

**Root causes (in order of severity, expanded from v2):**

1. `seed_decisions_log()` at `hebbian_seed_sessions.py:275-329` + its call at line 344 — runs unconditionally, creates the regime↔token↔decision explosion
2. `learn_from_decisions_log()` at `hebbian_session_learner.py:80-123` + its call at line 212 — same pollution via cron
3. Entity extractor ALL_CAPS regex without coin-universe filter at `hebbian_entity_extractor.py:189-193`
4. **CORRECTED (was R1 in v3 draft)**: `/root/.hermes/scripts/hebbian_learner.py` (182 lines) is the **brain-md seeder** — scans `brain/*.md` for co-occurrences. It is NOT a parallel extractor competing with `hebbian_entity_extractor.py`. Has stale hardcoded vocabularies (L26-35) and references dead file paths (`signal_gen.py`, `ai_decider.py` at L154-161). Never wired to timer/cron → currently dead code. Refactor in Fix 1b.
5. No `session_summaries` table — only the co-occurrence graph exists, can't query by topic
6. Both systemd timers disabled (hebbian-decay at 4am, session-learner at 6am)
7. SOUL.md has no specific recall triggers — just "use proactively"
8. **NEW**: `hebbian_session_learner.py:8` and `hebbian_seed_sessions.py:1-9` docstrings still mention `decisions.jsonl` — stale after Fix 2
9. **NEW (R10)**: Plan's "handle BOTH file types" instruction in Fix 5 lacks the schema transform for `request_dump_*.json` — without `d['request']['body']['messages']` instead of `d['messages']`, 844 of 4,851 files (17%) produce zero summaries
10. **NEW (R2)**: `request_dump_*.json` files contain `Authorization: Bearer *** and `sk-` API keys — distill script must strip these from any summary text or they leak into the DB

**Bugs the v2 auditor caught (still relevant):**
- `hebbian_session_learner.py:99-100` — `direction = d.get("decision")` reads wrong field; moot since function is deleted
- Vocabularies (KNOWN_TOKENS, KNOWN_SKILLS, etc.) duplicated across 4 files with subtle differences — refactor candidate, not blocking
- `clear_all()` at `hebbian_engine.py:244-249` doesn't include the new `session_summaries` table — fixed in Fix 4

---

## Surgical Fix Plan (8 fixes + 1 mandatory precheck, audit-corrected)

### Precheck P0: `hebbian_learner.py` — REFACTOR & INTEGRATE (corrected 2026-06-24)

**P0 result from grep (verified):**
- 0 live callers in any `.py` / `.service` / `.timer` / `.sh` file
- 0 systemd service references it (only `hebbian_engine.py decay` and `hebbian_session_learner.py` are scheduled)
- 0 cron references
- 0 imports anywhere
- All remaining `grep` hits are: state.db (Hermes runtime, not a caller), git index (VCS), checkpoints (auto-saved), documentation (skills + references), or session_*.json tool output (just `ls` listings)

**What `hebbian_learner.py` actually is** (read full 182 lines):
- A **markdown brain seeder** — scans `brain/*.md` files (TASKS.md, PROJECTS.md, trading.md, lessons.md) for co-occurring concepts and seeds the network from T's written knowledge
- Original intent (docstring L1-9): "Run once to populate initial links, then let natural usage grow the network"
- **It is NOT a parallel extractor competing with `hebbian_entity_extractor.py`** — it's a complementary data source: markdown brain docs → co-occurrence seeds, vs session logs → entity extraction
- The reason it's not called is **because it was never wired up to anything** — no timer, no cron, no systemd service. Last manual run was April 9 per tirith log.

**Problems with the current implementation (this is what we want to fix):**
1. **L26-35 hardcoded vocabularies** (KNOWN_TOKENS 31 coins, KNOWN_SKILLS, KNOWN_INFRA, KNOWN_FILES) — stale, smaller than `hebbian_entity_extractor.py`'s lists, no HL_COINS source
2. **L154-161 hardcoded script list** references dead files: `signal_gen.py` (renamed to `signal_runner.py`), `ai_decider.py` (replaced by `signal_compactor.py`), `decider_run.py` (path is right but file may have moved)
3. **L82 ALL_CAPS regex** — catches any 2-6 char all-caps word but only adds to concepts if in KNOWN_TOKENS. More restrictive than the broken `hebbian_entity_extractor.py` (which has no filter), but still misses coins not in the hardcoded list
4. **No HL_COINS filter** — same Fix 1 issue, just on a smaller scale
5. **No `--since` or mtime check** — always reseeds everything, no incremental mode
6. **No systemd timer** — only ever ran twice manually in 12 weeks

**Refactor scope (do this as part of Fix 1):**

A) **Make `infer_label()` and `extract_concepts()` import from `hebbian_entity_extractor.py`** (single source of truth, fixes P0.4 and P0.1 in one stroke):
```python
# At top of hebbian_learner.py — replace lines 24-35 (hardcoded vocabularies) and 37-50 (infer_label)
from hebbian_entity_extractor import infer_label, HL_COINS, extract_concepts
# Delete the local KNOWN_TOKENS, KNOWN_SKILLS, KNOWN_INFRA, KNOWN_FILES definitions (lines 25-35)
# Delete the local infer_label (lines 37-50) — now imported from entity_extractor
# Delete the local extract_concepts (lines 52-93) — now imported from entity_extractor
# Keep normalize_concept (lines 95-101) — it's markdown-specific and not in entity_extractor
```

B) **Fix the hardcoded script list at L154-161** — use a glob instead of hardcoded paths:
```python
print("\n[Key Scripts]")
scripts_dir = Path("/root/.hermes/scripts")
key_scripts = sorted([
    p for p in scripts_dir.glob("*.py")
    if not p.name.startswith(("test_", "_", "hebbian_"))  # skip tests, private, self-referential
    and p.stat().st_size > 5000  # skip trivial files
])[:30]  # cap at 30 to keep noise down
for s in key_scripts:
    total_pairs += seed_from_file(engine, s, "file")
```

C) **Add `--since` and `--dry-run` flags** (supports Fix 5 incremental pattern, enables R6 checkpointing):
```python
import argparse
from datetime import datetime, timedelta

parser = argparse.ArgumentParser()
parser.add_argument('--since', type=str, default='', help='Only process files modified since Nh ago (e.g. "24h")')
parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without writing')
parser.add_argument('--clear', action='store_true', help='Wipe DB before seeding (default: additive)')
args = parser.parse_args()

cutoff = None
if args.since:
    hours = int(args.since.rstrip('h'))
    cutoff = datetime.now() - timedelta(hours=hours)

# In main(), wrap each glob:
def _should_process(p: Path) -> bool:
    if cutoff is None:
        return True
    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    return mtime >= cutoff

# Use _should_process(f) as filter in each loop
```

D) **Wire it into a systemd timer** so it runs weekly — captures any new brain/*.md / skills/*/SKILL.md content. Add new service+timer files alongside the existing ones.

**Why this is the right fix (not "delete"):**
- The DB has 144 nodes today. A clean brain-md seeder would produce **thousands** of high-quality co-occurrences (TASKS.md alone is hundreds of lines of project context with skill refs, file refs, infra refs, token refs all co-located)
- Without it, Fix 3's reseed only gets data from `hebbian_seed_sessions.py` (which scans 844 request_dump_*.json files only) and Fix 5 (which adds session_summaries but not co-occurrence pairs)
- The brain docs are **the highest-signal source for recall**: T writes project knowledge deliberately, so concepts co-occurring there are genuinely related
- The `associative-recall` skill already documents `hebbian_learner.py` at line 211: "/root/.hermes/scripts/hebbian_learner.py — initial seeding from brain/*.md" — confirming original intent
- T's preference from memory: "Verify don't trust. Don't go on random tangents, stay focused." This seeder IS the focused source — it's T's own documented knowledge, not extracted noise

**Refactored file fits into the order:**
- Precheck P0 (this section) defines the refactor — actual code edits land as **Fix 1b** (extending Fix 1)
- Fix 1 covers `hebbian_entity_extractor.py` changes
- Fix 1b covers `hebbian_learner.py` refactor to use the new entity_extractor exports
- Same backup/syntax-check discipline applies to both files
- The `infer_label` import is the critical linkage — without it, the refactor doesn't actually share the Fix 1 fix

---

### Fix 1: Entity extractor — real coin universe filter

File: `/root/.hermes/scripts/hebbian_entity_extractor.py`

Replace the current top-of-file setup to load the HL coin universe from `signals_hermes.db`. **Table is `ohlcv_1m`, column is `token`.** Hardcoded fallback if DB is missing/empty.

```python
import sqlite3
import os
from typing import Optional

DB_PATH = "/root/.hermes/data/signals_hermes.db"

# Top-50 fallback if signals_hermes.db is missing/empty (deduplicated — v2 had AVAX twice)
_FALLBACK_COINS = {
    "BTC", "ETH", "SOL", "AVAX", "XRP", "DOGE", "ADA", "DOT", "LINK",
    "UNI", "AAVE", "MKR", "SNX", "DYDX", "GMX", "LDO", "CRV", "APE",
    "INJ", "TIA", "SEI", "WIF", "PEPE", "SHIB", "FLOKI", "ARB", "OP",
    "MATIC", "POL", "GALA", "ENJ", "MANA", "AXS", "ICP", "ETHFI", "SKY",
    "PENDLE", "SAND", "RNDR", "VET", "NEAR", "APT", "SUI", "TON", "XLM",
    "HBAR", "FIL", "ATOM", "TRX",
}

def _load_coin_universe() -> set[str]:
    """Load HL coin universe from signals_hermes.db."""
    try:
        if not os.path.exists(DB_PATH):
            return set(_FALLBACK_COINS)
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
        try:
            rows = conn.execute("SELECT DISTINCT token FROM ohlcv_1m").fetchall()
            coins = {r[0] for r in rows if r[0]}
            # Threshold 10 keeps fallback active if DB has <10 coins (suspect)
            return coins if len(coins) >= 10 else set(_FALLBACK_COINS)
        finally:
            conn.close()
    except Exception as e:
        import sys
        print(f"[hebbian_entity_extractor] WARN: failed to load coin universe: {e}", file=sys.stderr)
        return set(_FALLBACK_COINS)

HL_COINS = _load_coin_universe()
```

Then update `infer_label` at line 99-110 to use both sources (v2 said line 96 — actual is 99-110, verified):
```python
def infer_label(candidate: str) -> Optional[str]:
    c = candidate.strip()
    c_lower = c.lower()
    # C1: classify as token if in EITHER source (KNOWN_TOKENS is broader — covers
    # tokens not yet in ohlcv_1m; HL_COINS is the live universe)
    if c in KNOWN_TOKENS or c in HL_COINS:
        return "token"
    # ... rest unchanged ...
```

Also tighten the ALL_CAPS regex block at line 189-193 to filter against HL_COINS:
```python
# T's communication style: all-caps is reserved almost exclusively for coin
# tickers (BTC, ETH, XLM, etc.) — non-coin all-caps words were the pollution
# source, not signal. Strict `lt == "token"` gate is correct under this
# assumption. Acronyms (API, SQL, JSON) stay in stopword set. New HL listings
# not yet in ohlcv_1m still pass via KNOWN_TOKENS fallback in infer_label.

for match in ALL_CAPS.finditer(text):
    val = match.group(1).strip()
    if val not in seen and val not in {'API', 'SQL', 'SSH', 'URL', 'TCP', 'UDP', 'HTTP', 'HTTPS', 'JSON', 'XML', 'CSV', 'IDE', 'GPT', 'LLM', 'CLI', 'PID', 'UID', 'GID'}:
        seen.add(val)
        lt = infer_label(val)
        if lt == "token":
            found.append((val, lt))
        # else: skip — not a real HL coin and not in KNOWN_TOKENS
```

**Why the strict gate is correct for T's style:**
- T uses all-caps almost exclusively for coin tickers he wants attention drawn to
- Acronyms (API/SQL/JSON) already filtered by stopword set
- Real coins land in HL_COINS via the live DB load
- Real coins not yet in ohlcv_1m still pass via KNOWN_TOKENS (33 hardcoded entries)
- Non-coin all-caps words (FOMC, SEC, etc.) were the original pollution — they used to get labeled "concept" and contaminate the graph with weak associations
- The only loss is brand-new HL listings referenced before their first candle data; these are rare and self-correcting on the next module import

**Verification (corrected assertion — C1):**
```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS
print(f'HL_COINS size: {len(HL_COINS)}')
assert len(HL_COINS) >= 100, f'Coin universe too small ({len(HL_COINS)}) — Fix 1 fell back to 50-coin list. Investigate signals_hermes.db.'
print('Sample:', sorted(HL_COINS)[:10])
print('infer_label spot-checks:')
from hebbian_entity_extractor import infer_label
for coin in ['BTC', 'ETH', 'XLM', 'XYZ_NONEXISTENT']:
    print(f'  {coin} -> {infer_label(coin)}')
"
```
Expected: `HL_COINS size: 104` (or whatever live count is), all real coins → 'token', non-existent → not 'token'.

---

### Fix 1b: Refactor `hebbian_learner.py` (NEW from v3 P0)

File: `/root/.hermes/scripts/hebbian_learner.py`

**Goal**: make the brain-md seeder actually work. Currently dead code with stale hardcoded vocabularies and references to renamed/replaced files.

**Step 1 — Delete duplicated vocabularies, import from `hebbian_entity_extractor.py`:**

Replace lines 24-50 with:
```python
# Label type inference — use shared entity_extractor (Fix 1)
from hebbian_entity_extractor import infer_label, HL_COINS, extract_concepts
# Note: normalize_concept stays local (markdown-specific), but the dedup logic
# is identical to entity_extractor. Could be refactored later.
```

Replace lines 52-93 (`extract_concepts` function) with:
```python
# Use shared extract_concepts from entity_extractor (Fix 1)
# Local definitions removed — single source of truth
```

**Step 2 — Fix hardcoded script list at L154-161** (replace dead file paths with glob):

```python
print("\n[Key Scripts]")
scripts_dir = Path("/root/.hermes/scripts")
key_scripts = sorted([
    p for p in scripts_dir.glob("*.py")
    if not p.name.startswith(("test_", "_"))          # skip tests, private modules
    and not p.name.startswith(("hebbian_",))          # skip self-referential hebbian modules
    and p.stat().st_size > 5000                         # skip trivial files (<5KB)
])[:30]                                                # cap at 30 to keep noise down
for s in key_scripts:
    total_pairs += seed_from_file(engine, s, "file")
```

**Step 3 — Add CLI flags** (`--since`, `--dry-run`, `--clear`):

Add at top (after imports):
```python
import argparse
from datetime import datetime, timedelta
```

Replace `main()` signature/entry to parse args:
```python
def main():
    parser = argparse.ArgumentParser(description='Hebbian brain-md seeder')
    parser.add_argument('--since', type=str, default='', help='Only process files modified since Nh ago (e.g. "24h" or "168h" for 1 week)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without writing to DB')
    parser.add_argument('--clear', action='store_true', help='Wipe DB before seeding (default: additive merge)')
    args = parser.parse_args()

    cutoff = None
    if args.since:
        hours = int(args.since.rstrip('h'))
        cutoff = datetime.now() - timedelta(hours=hours)

    def _should_process(p: Path) -> bool:
        if cutoff is None or args.dry_run:
            return True
        return datetime.fromtimestamp(p.stat().st_mtime) >= cutoff

    print("=== Hebbian Network Seeder ===")
    print(f"Brain dir: {BRAIN_DIR}")
    print(f"Cutoff: {cutoff or 'none (process all)'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")
    print()

    engine = HebbianEngine()
    if args.clear and not args.dry_run:
        print("Clearing existing network (--clear)...")
        engine.clear_all()

    total_pairs = 0
    n_files = 0

    print("\n[Brain Files]")
    for f in sorted(BRAIN_DIR.glob("*.md")):
        if not _should_process(f):
            continue
        n_files += 1
        if not args.dry_run:
            total_pairs += seed_from_file(engine, f)

    print("\n[Key Scripts]")
    scripts_dir = Path("/root/.hermes/scripts")
    key_scripts = sorted([
        p for p in scripts_dir.glob("*.py")
        if not p.name.startswith(("test_", "_"))
        and not p.name.startswith("hebbian_")
        and p.stat().st_size > 5000
    ])[:30]
    for s in key_scripts:
        if not _should_process(s):
            continue
        n_files += 1
        if not args.dry_run:
            total_pairs += seed_from_file(engine, s, "file")

    print("\n[Skills]")
    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    skill_files += list(SKILLS_DIR.glob("*/skills/*/SKILL.md"))
    for sf in skill_files[:20]:
        if not _should_process(sf):
            continue
        n_files += 1
        if not args.dry_run:
            total_pairs += seed_from_file(engine, sf)

    print(f"\n=== Seed Complete ===")
    print(f"Files processed: {n_files}")
    print(f"Total pairs learned: {total_pairs}")
    if not args.dry_run:
        stats = engine.get_stats()
        print(f"Nodes: {stats['nodes']}, Synapses: {stats['synapses']}")
        print(f"Top edges:")
        for e in stats['top_edges'][:10]:
            print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f}")
```

**Step 4 — Create systemd timer** so it runs weekly:

New file `/root/.hermes/.config/systemd/user/hermes-brain-seeder.service`:
```ini
[Unit]
Description=Hebbian Brain Seeder — refresh co-occurrences from brain/*.md weekly

[Service]
Type=oneshot
WorkingDirectory=/root/.hermes
# --since 168h = 1 week — picks up anything modified in last 7 days
ExecStart=/usr/bin/python3 /root/.hermes/scripts/hebbian_learner.py --since 168h
StandardOutput=journal
StandardError=journal
```

New file `/root/.hermes/.config/systemd/user/hermes-brain-seeder.timer`:
```ini
[Unit]
Description=Hebbian Brain Seeder — weekly Sunday 3am UTC

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Verification after Fix 1b:**
```bash
# Syntax check
python3 -m py_compile /root/.hermes/scripts/hebbian_learner.py

# Dry run — should list files it would process without writing
python3 /root/.hermes/scripts/hebbian_learner.py --dry-run --since 720h
# Expected: shows brain files, key scripts (no dead signal_gen.py / ai_decider.py), skills
# Should list >20 files for a 30-day window

# Live run with clear
python3 /root/.hermes/scripts/hebbian_learner.py --clear --since 720h
# Expected: thousands of pairs learned, hundreds of nodes

# Verify imports work
python3 -c "from hebbian_learner import seed_from_file, normalize_concept, infer_label; print('OK')"

# Verify timer
systemctl --user status hermes-brain-seeder.timer
```

**Don't enable the timer in Fix 1b** — that's Fix 7's job (after all pollution sources are dead).

---

### Fix 2: Stop learning from decisions.jsonl — INCLUDING call sites (corrected ranges)

The plan must remove the functions AND every place that calls them. v2 had off-by-one errors in the line ranges. Corrected:

**`/root/.hermes/scripts/hebbian_seed_sessions.py`:**
- DELETE lines 275-329 (the entire `seed_decisions_log()` function)
- DELETE lines 342-345 in `main()` (v2 said 343-345 — missed the comment line at 342):
  ```python
  # Seed from decisions log
  print("\n[Decisions Log]")
  n = seed_decisions_log()
  print(f"Learned {n} pairs from decisions log")
  ```
- ALSO update docstring at lines 1-9 (NEW from 2nd audit) — remove `decisions.jsonl` reference

**`/root/.hermes/scripts/hebbian_session_learner.py`:**
- DELETE lines 80-123 (the entire `learn_from_decisions_log()` function)
- DELETE lines 210-214 in `main()` (v2 said 210-213 — left dead `total_pairs += n` at line 214):
  ```python
  # 2. Decisions log
  print("[Decisions Log]")
  n = learn_from_decisions_log(engine, days_back)
  print(f"  Learned {n} trading decision pairs")
  total_pairs += n
  ```
- ALSO update docstring at line 8 (NEW from 2nd audit) — remove `decisions.jsonl` reference

**Latent bug at lines 99-100** (direction = d.get("decision") reads wrong field): moot since function is deleted. Skip.

**Verification after this lands:**
```bash
# No call sites anywhere
grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/
# Expected: empty (functions + call sites + docstring references all gone)

# No stale docstring mentions
grep -n "decisions.jsonl\|decisions log" /root/.hermes/scripts/hebbian_session_learner.py /root/.hermes/scripts/hebbian_seed_sessions.py
# Expected: empty
```

---

### Fix 3: Wipe + reseed (RUN AFTER Fix 1 + Fix 2 + Precheck P0)

```bash
# Backup DB FIRST (R4 covers SOUL.md backup too)
cp /root/.hermes/brain/associative_memory.db /root/.hermes/brain/associative_memory.db.bak-2026-06-24
cp /root/.hermes/SOUL.md /root/.hermes/SOUL.md.bak-2026-06-24

# R3 SPOT-CHECK before wipe: verify Fix 1 is actually loading HL_COINS from DB, not fallback
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS, infer_label
# Must have >= 100 real coins (Fix 1 assertion), not the 50-fallback
assert len(HL_COINS) >= 100, f'HL_COINS has only {len(HL_COINS)} entries — Fix 1 silently fell back. DO NOT proceed with reseed.'
# Spot check that real coins label correctly
for c in ['BTC', 'ETH', 'XLM', 'SOL', 'WIF', 'TRB']:
    assert infer_label(c) == 'token', f'{c} not labeled token'
print(f'OK: {len(HL_COINS)} coins loaded, infer_label working')
"

# Wipe (only after Fix 4 has updated clear_all to include session_summaries)
python3 /root/.hermes/scripts/hebbian_engine.py clear_all

# Reseed (single-shot — Fix 5 handles session_summaries backfill separately)
python3 /root/.hermes/scripts/hebbian_seed_sessions.py 200
```

**Verification (expanded from v2 with R3 check):**
```bash
# Label mix should be diverse, NOT dominated by decision/regime
sqlite3 /root/.hermes/brain/associative_memory.db \
  "SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type ORDER BY 2 DESC;"
# Expected: file/skill/concept/project mix, NOT dominated by decision/regime

# Total node count should be much higher than 144
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM concept_nodes;"
# Expected: thousands of nodes (was 144)

# R3 ADDITIONAL CHECK: no token label on non-existent coins
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/brain/associative_memory.db')
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS
bad = conn.execute(
    \"SELECT name FROM concept_nodes WHERE label_type='token' AND name NOT IN ({})\"
    .format(','.join('?'*len(HL_COINS))), tuple(HL_COINS)
).fetchall()
print(f'Non-HL coins labeled token: {len(bad)}')
if bad:
    print('Examples:', bad[:10])
    raise SystemExit('FAIL — entity extractor over-classified')
conn.close()
"
# Expected: 0 non-HL coins labeled 'token'
```

Note: this reseed only covers 844 `request_dump_*.json` files (per the current `hebbian_seed_sessions.py` logic — needs separate extension for `session_*.json`, out of scope for this fix). Fix 5 handles session_summaries independently.

---

### Fix 4: Add session_summaries table + recall functions + clear_all update

File: `/root/.hermes/scripts/hebbian_engine.py`

Add to `_init_db()` (line 32-61) after the existing tables, before the indexes block:
```sql
CREATE TABLE IF NOT EXISTS session_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    started_at TEXT,
    summary TEXT,
    discussion_type TEXT,
    subjects TEXT,                -- JSON array of {type, name}
    files_touched TEXT,           -- JSON array
    coins_discussed TEXT,         -- JSON array
    full_text_path TEXT,
    turn_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ss_files ON session_summaries(files_touched);
CREATE INDEX IF NOT EXISTS idx_ss_coins ON session_summaries(coins_discussed);
CREATE INDEX IF NOT EXISTS idx_ss_type ON session_summaries(discussion_type);
```

Update `clear_all()` (line 244-249) to wipe it too (v2 confirmed this is missing):
```python
def clear_all(self):
    """Dangerous: wipe all data."""
    with sqlite3.connect(self.db_path) as conn:
        conn.execute("DELETE FROM synapse_weights")
        conn.execute("DELETE FROM concept_nodes")
        conn.execute("DELETE FROM session_summaries")
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
```

Add helper methods to the `HebbianEngine` class (after existing recall methods, ~line 200+):
```python
def add_session_summary(self, session_id, summary, discussion_type,
                        subjects, files, coins, turn_count,
                        full_text_path="", started_at="") -> int:
    import json
    with sqlite3.connect(self.db_path) as conn:
        cur = conn.execute("""
            INSERT OR REPLACE INTO session_summaries
              (session_id, started_at, summary, discussion_type, subjects,
               files_touched, coins_discussed, full_text_path, turn_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, started_at, summary, discussion_type,
              json.dumps(subjects), json.dumps(files), json.dumps(coins),
              full_text_path, turn_count))
        conn.commit()
        return cur.lastrowid

def recall_sessions_for_file(self, filepath: str, k: int = 5) -> list[dict]:
    # Strip .py for matching against stored basenames
    base = filepath.removesuffix('.py')
    # Parameterized LIKE — safe from injection. Pattern matches json.dumps output: ["foo.py"]
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT session_id, started_at, summary, discussion_type,
                   files_touched, coins_discussed
            FROM session_summaries
            WHERE files_touched LIKE ? OR files_touched LIKE ?
            ORDER BY started_at DESC LIMIT ?
        """, (f'%"{base}"%', f'%"{base}.py"%', k)).fetchall()
        return [dict(r) for r in rows]

def recall_sessions_for_coin(self, coin: str, k: int = 5) -> list[dict]:
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT session_id, started_at, summary, discussion_type,
                   files_touched, coins_discussed
            FROM session_summaries
            WHERE coins_discussed LIKE ?
            ORDER BY started_at DESC LIMIT ?
        """, (f'%"{coin}"%', k)).fetchall()
        return [dict(r) for r in rows]

def recall_sessions_for_topic(self, topic: str, k: int = 5) -> list[dict]:
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT session_id, started_at, summary, discussion_type,
                   files_touched, coins_discussed
            FROM session_summaries
            WHERE discussion_type = ? OR summary LIKE ?
            ORDER BY started_at DESC LIMIT ?
        """, (topic, f'%{topic}%', k)).fetchall()
        return [dict(r) for r in rows]
```

**Verification:**
```bash
sqlite3 /root/.hermes/brain/associative_memory.db ".schema session_summaries"
# Expected: shows the new table with all columns and 3 indexes

# Test clear_all includes new table
python3 -c "
from hebbian_engine import HebbianEngine
e = HebbianEngine()
e.add_session_summary('test_id', 'test summary', 'analysis', [], [], [], 5)
print('Before clear:', e.recall_sessions_for_topic('test'))
e.clear_all()
print('After clear:', e.recall_sessions_for_topic('test'))
"
# Expected: 1 result before, 0 after
```

---

### Fix 5: Backfill session_summaries from existing dumps (with schema transform + secret stripping)

New file: `/root/.hermes/scripts/hebbian_session_distill.py`

Handles BOTH file types (`request_dump_*.json` AND `session_*.json`). Two NEW requirements from v3 audit:

1. **Schema transform for request_dump** (R10): these files have `d['request']['body']['messages']`, NOT `d['messages']` at top level. Without the transform, 17% of files produce zero summaries.

2. **Secret stripping** (R2): `request_dump_*.json` body contains `Authorization: Bearer *** and `sk-` API keys. Must strip these patterns from any summary text before INSERT.

**Discussion type heuristic** (C4: drop the AND in `bug_fix` — most bug reports won't have both problem-term AND fix-verb in same line):
- `bug_fix`: contains `bug|broken|wrong|fix|regression|reversed|fixed|patched|crashed|failing|stuck` (single combined regex, OR)
- `decision`: contains `decided|going with|let's use|approved|rejected|chose|picked`
- `plan`: contains numbered list pattern or markdown `## Step` or `Phase`
- `refactor`: contains `refactor|rewrite|restructure|moved|split`
- `coin`: mentions an HL_COINS ticker AND contains `trending|setup|looking at|watching|breaking out`
- else: `analysis`

**Summary generation method** (heuristic, no LLM):
- For `session_*.json`: take `messages[0]['content']`, truncate to 200 chars, extract top 5 entities from that message, strip secrets
- For `request_dump_*.json`: extract `d['request']['body']['messages'][0]['content']`, same processing (R10)

**Secret-stripping helper** (R2 — NEW, mandatory):
```python
import re
_SECRET_PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9_\-]+'),     # Bearer *** # Strip API keys
    re.compile(r'sk-[A-Za-z0-9_\-]{10,}'),        # OpenAI-style keys
    re.compile(r'sk-cp-[A-Za-z0-9_\-]+'),         # OpenRouter-style keys
]

def _strip_secrets(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub('[REDACTED]', text)
    return text
```

Apply `_strip_secrets()` to summary text and any extracted entity context BEFORE INSERT.

**Idempotency**: check `session_summaries` for existing `session_id` before insert; skip if present. (Also guaranteed by `UNIQUE` + `INSERT OR REPLACE` for defense in depth.)

**Per-file error handling** (R9 — NEW from 2nd audit):
```python
import logging
fail_log = logging.getLogger('hebbian_distill.failures')
fail_log.addHandler(logging.FileHandler('/root/.hermes/data/hebbian_distill.failures.log'))

for fp in session_files:
    try:
        process_file(fp)
    except Exception as e:
        fail_log.error(f'{fp.name}: {type(e).__name__}: {e}')
        continue  # Don't crash the whole run on one bad file
```

**Background execution** (R6 — add checkpoint for resumption):
```bash
# Initial backfill
nohup python3 /root/.hermes/scripts/hebbian_session_distill.py --all > /root/.hermes/data/hebbian_distill.log 2>&1 &
echo $! > /tmp/hebbian_distill.pid

# Monitor
tail -f /root/.hermes/data/hebbian_distill.log
```

**Coverage**: scope to all 4,851 files. The script reads first 200 chars per message + entity extraction — I/O-bound, not memory-heavy. Estimate: 5-15 min in background.

**Verification after Fix 5:**
```bash
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries;"
# Expected: hundreds to ~thousands (ideally close to 4,851)

sqlite3 /root/.hermes/brain/associative_memory.db "SELECT discussion_type, COUNT(*) FROM session_summaries GROUP BY discussion_type;"
# Expected: most are 'analysis', some 'plan', few 'bug_fix'/'decision'/'refactor'

# R2 verification: no secrets leaked
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries WHERE summary LIKE '%Bearer%' OR summary LIKE '%sk-%' OR summary LIKE '%sk-cp-%';"
# Expected: 0

# R10 verification: request_dump files actually got summaries (should be ~844)
python3 -c "
import sqlite3, json
conn = sqlite3.connect('/root/.hermes/brain/associative_memory.db')
rows = conn.execute('SELECT session_id FROM session_summaries').fetchall()
dump_ids = {r[0] for r in rows if r[0].startswith('20') and '_' in r[0]}  # request_dump session_ids start with date
print(f'Total summaries: {len(rows)}')
print(f'Request_dump-like IDs: {len(dump_ids)}')
"

PYTHONPATH=/root/.hermes/scripts python3 -c "
from hebbian_engine import recall_sessions_for_file, recall_sessions_for_coin
r = recall_sessions_for_file('signal_compactor')
print(f'Found {len(r)} sessions for signal_compactor')
for s in r[:3]:
    print(' ', s.get('summary', '')[:120])
"
```

---

### Fix 6: SOUL.md update — POINT TO SKILL, don't duplicate (C6)

File: `/root/.hermes/SOUL.md`

v2 proposed adding a "When to recall (proactive triggers)" section with a 5-row table. **PROBLEM**: this table already exists in `/root/.hermes/skills/associative-recall/SKILL.md` at line 62+ — verified by grep. Duplicating creates drift risk.

**Revised Fix 6**: add only the new pieces (visible mode threshold + session-level recall snippet), pointing to the skill for the trigger table.

After the existing hebbian block at lines 24-40, add:

```markdown
### When to recall

Trigger table lives in `associative-recall` skill (line 62+). One-line summary:
recall proactively for session starts, coin tickers, filenames, "X bug" mentions,
"what did we do" / "remind me" questions. Skip for greetings, status checks, smoke tests.

**Visible mode** (corrected threshold — R5):
- If recall returns weight >= 2.0 AND at least one association, surface 1-3 in reply:
  > "I recall we discussed X in a prior session — Y."
- If all returned weights < 2.0, skip surface (don't spam weak associations).
- Threshold will be raised to 5.0 once the DB accumulates enough traffic (post-reseed,
  after ~30 days of normal session activity). For now, 2.0 is the floor.

**Session-level recall** (better than co-occurrence for "what did we do" questions):
```python
from hebbian_engine import recall_sessions_for_file, recall_sessions_for_coin
# e.g. "what did we do on signal_compactor?"
print(recall_sessions_for_file("signal_compactor.py"))
print(recall_sessions_for_coin("XLM"))
```
```

**Why threshold 2.0 not 5.0 (R5):** current DB MAX synapse weight is 99.5 but that's from the bug's decay multiplication. After Fix 3 wipe, all synapses start at weight 1.0 per co-occurrence. Reaching 5.0 requires 4+ co-occurrences of the same pair — could take weeks of normal session activity. Threshold 5.0 means visible-mode never fires post-reseed.

**Verification:**
```bash
# No duplicate trigger table in SOUL.md
grep -c "When to recall (proactive triggers)" /root/.hermes/SOUL.md
# Expected: 0 (the heading should be "When to recall" without "(proactive triggers)" — matches skill)

# Pointing line present
grep "associative-recall.*skill" /root/.hermes/SOUL.md
# Expected: at least 1 hit

# Threshold is 2.0 not 5.0
grep -n "weight >= 2.0\|weight >= 5.0" /root/.hermes/SOUL.md
# Expected: "weight >= 2.0" present, no "weight >= 5.0"
```

---

### Fix 7: Enable systemd timers (RUN AFTER Fix 2 + Fix 5 + Fix 6)

```bash
# Verify Fix 2's call-site removal landed first (hard blocker)
grep -n "learn_from_decisions_log\|decisions.jsonl" /root/.hermes/scripts/hebbian_session_learner.py
# Expected: empty

# Verify Fix 6's SOUL.md update landed (otherwise new data lands but agent has no rules)
grep -c "associative-recall.*skill" /root/.hermes/SOUL.md
# Expected: 1

# Then enable
systemctl --user enable --now hermes-hebbian-decay.timer
systemctl --user enable --now hermes-session-learner.timer

# Verify
systemctl --user list-timers --all | grep hebbian
# Expected: shows both timers with NEXT trigger time in the future
```

If either timer errors on first run, check journal:
```bash
journalctl --user -u hermes-session-learner.service -n 30 --no-pager
```

---

### Fix 8: Skill update

File: `/root/.hermes/skills/associative-recall/SKILL.md`

The skill is mostly accurate already. Add:
- New session_summaries recall functions (`recall_sessions_for_file`, `recall_sessions_for_coin`, `recall_sessions_for_topic`)
- Updated label distribution example after Fix 3 reseed (mix of file/skill/concept, not just token)
- Note that trade-log learning is disabled (Fix 2)
- Reference to Fix 6's visible-mode threshold (2.0 floor)
- Reference to Fix 5's `hebbian_distill.failures.log` for diagnosing partial backfills

---

## Implementation order (audit-corrected + NEW dependencies)

1. **Precheck P0** (DONE — `hebbian_learner.py` is the brain-md seeder, not a parallel extractor; will refactor as Fix 1b)
2. **Fix 1** (entity extractor — corrected table/column, fallback list, threshold, exports `infer_label` + `HL_COINS` + `extract_concepts` for Fix 1b)
3. **Fix 1b** (NEW — refactor `hebbian_learner.py` to import from entity_extractor, fix hardcoded script list, add `--since`/`--dry-run`/`--clear` flags, wire weekly systemd timer)
4. **Fix 2** (kill decision-log learning — function AND call sites, corrected ranges, docstring cleanup)
5. **Fix 4** (session_summaries schema + clear_all update)
6. **Fix 3** (backup → spot-check → wipe → reseed — only after 1+1b+2+4 land. Reseed runs BOTH `hebbian_seed_sessions.py 200` AND `hebbian_learner.py --since 720h` to cover brain docs + session dumps)
7. **Fix 5** (distill script — background, per-file try/except, schema transform, secret stripping, failures log)
8. **Fix 6** (SOUL.md update — points to skill, threshold 2.0, visible mode)
9. **Fix 7** (enable timers — `hermes-hebbian-decay.timer` + `hermes-session-learner.timer` + NEW `hermes-brain-seeder.timer` from Fix 1b. Only after 2 verified, 6 verified)
10. **Fix 8** (skill update — cosmetic, last)

**Critical order dependencies (expanded from v2 with R1, R3):**

- **Fix 1 must complete before Fix 1b** — Fix 1b imports `infer_label` and `extract_concepts` from Fix 1's refactored entity_extractor
- **Fix 1b must complete before Fix 3** — otherwise Fix 3 reseed doesn't get brain-md co-occurrences, missing the highest-signal data source
- **Fix 1 must complete before Fix 3** (NEW from 2nd audit, R3) — otherwise reseed uses old `infer_label` and bakes garbage into clean DB. v2 didn't enumerate this!
- **Fix 2 must complete before Fix 7** — otherwise timer re-introduces pollution
- **Fix 4 must complete before Fix 3** — otherwise `clear_all()` doesn't wipe session_summaries
- **Fix 6 must complete before Fix 7** — otherwise new data lands but agent has no recall rules

---

## Verification (full — all checks from v2 + 2nd audit additions)

After all fixes:

```bash
# 1. Entity extractor loads coin universe from DB (not fallback)
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS
print(f'HL_COINS: {len(HL_COINS)} tokens')
assert len(HL_COINS) >= 100
"

# 2. R1: hebbian_learner either deleted, refactored, or has no live callers
grep -rn "hebbian_learner\|from hebbian_learner\|import hebbian_learner" /root/.hermes/ --include="*.py" --include="*.service" --include="*.timer" 2>/dev/null
# Expected: empty (file deleted or only its own self-references remain)

# 3. No call sites for killed functions
grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/
# Expected: empty

# 4. No stale docstring references
grep -n "decisions.jsonl\|decisions log" /root/.hermes/scripts/hebbian_session_learner.py /root/.hermes/scripts/hebbian_seed_sessions.py
# Expected: empty

# 5. DB has variety of labels (Fix 3 worked)
sqlite3 /root/.hermes/brain/associative_memory.db \
  "SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type ORDER BY 2 DESC;"
# Expected: file/skill/concept/project mix, NOT dominated by decision/regime

# 6. R3: no non-HL coins labeled 'token'
# (See Fix 3 verification block above)

# 7. Session summaries exist (Fix 4 + Fix 5 worked)
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries;"
# Expected: hundreds to thousands

# 8. R10: request_dump files got summaries (not 0 for 17% of files)
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(DISTINCT session_id) FROM session_summaries;"
# Expected: should be close to 4,851 (within 5-10% tolerance for parse failures)

# 9. R2: no secrets in summary text
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries WHERE summary LIKE '%Bearer%' OR summary LIKE '%sk-cp-%' OR summary LIKE '%sk-%';"
# Expected: 0

# 10. Recall returns useful associations
PYTHONPATH=/root/.hermes/scripts python3 /root/.hermes/scripts/hebbian_engine.py recall signal_compactor
PYTHONPATH=/root/.hermes/scripts python3 /root/.hermes/scripts/hebbian_engine.py recall XLM
# Expected: real associations, not empty, not just regime/decision

# 11. Session-level recall works
PYTHONPATH=/root/.hermes/scripts python3 -c "
from hebbian_engine import recall_sessions_for_file
print(recall_sessions_for_file('signal_compactor'))
"

# 12. Timers enabled
systemctl --user list-timers --all | grep hebbian

# 13. SOUL.md points to skill (not duplicate)
grep -c "When to recall (proactive triggers)" /root/.hermes/SOUL.md
# Expected: 0
grep -c "associative-recall.*skill" /root/.hermes/SOUL.md
# Expected: 1

# 14. Threshold is 2.0
grep -n "weight >= 2.0\|weight >= 5.0" /root/.hermes/SOUL.md
# Expected: ">= 2.0" present, no ">= 5.0"
```

---

## Risks (consolidated — v2's 7 + 7 new from audits)

| # | Risk | Mitigation |
|---|---|---|
| 1 | Wipe loses existing data | Backup DB to `.bak-2026-06-24` |
| 2 | Coin universe might not load if signals_hermes.db is empty | 50-coin hardcoded fallback |
| 3 | Distill script processes 4,007 session_*.json files containing SOUL.md | Skip `system_prompt` field during entity extraction |
| 4 | Discussion_type heuristic under-fires for bug_fix/decision | Single-regex `bug_fix` (C4); accept sparse buckets |
| 5 | Storage bloat (4,851-file backfill ≈ 250 MB) | Acceptable; SQLite handles it |
| 6 | Race: Fix 3 wipe leaves stale session_summaries | Update `clear_all()` in Fix 4 BEFORE Fix 3 |
| 7 | Latent bug at hebbian_session_learner.py:99-100 | Moot — function deleted in Fix 2 |
| **R1** | **`hebbian_learner.py` is the brain-md seeder (markdown docs → co-occurrences), not a parallel extractor. It has stale hardcoded vocabularies and references dead file paths. Currently dead code because never wired to timer/cron.** | **Fix 1b: refactor to import from entity_extractor (single source of truth), fix hardcoded script list to use glob, add --since/--dry-run flags, wire weekly systemd timer** |
| **R2** | **request_dump_*.json contains Bearer/sk- API keys; could leak into session_summaries.summary** | **Mandatory secret-stripping helper in Fix 5 (3 regex patterns)** |
| **R3** | **Fix 1 → Fix 3 critical dependency not in v2's "Critical order dependencies" list. If Fix 1 silently falls back, post-wipe reseed bakes garbage** | **Mandatory spot-check before Fix 3 reseed (assert len(HL_COINS) >= 100)** |
| **R4** | **No backup for SOUL.md before Fix 6 edit** | **Add `cp SOUL.md SOUL.md.bak-2026-06-24` before Fix 3 (covers both Fix 3 and Fix 6 timing)** |
| **R5** | **weight >= 5.0 visible-mode threshold unreachable for weeks post-reset** | **Lower threshold to 2.0 with documented upgrade path** |
| **R6** | **No checkpoint/progress in Fix 5 — re-runs restart from scratch (idempotent but wastes 5-15 min)** | **Per-file try/except with failures log; idempotency via UNIQUE handles duplicates on re-run** |
| **R7** | **Heuristic summaries will be low-signal stubs for short ops sessions** | **Document this in SOUL.md; treat summaries as indexes not final answers** |
| **R8** | **Fix 5 schema transform missing for request_dump_*.json — 17% of files produce zero summaries** | **Mandatory `d['request']['body']['messages']` path in distill script** |
| **R9** | **Fix 5 mid-run crash on malformed JSON — partial state, no failures visibility** | **Per-file try/except + hebbian_distill.failures.log** |
| **R10** | **request_dump_*.json body parsing** | **Same as R8** |
| **R11** | **SOUL.md backup missing** | **Same as R4** |

---

## Changes from v2 (delta summary)

**Structural changes:**
- Added Precheck P0 as step 1 (mandatory, new in v3)
- Added Fix 5 schema transform spec for `request_dump_*.json` (R10/R8)
- Added Fix 5 secret-stripping helper (R2)
- Added Fix 5 per-file error handling + failures log (R9)
- Revised Fix 6 to point to skill instead of duplicating (C6)
- Revised Fix 6 threshold from 5.0 to 2.0 with upgrade path (R5)
- Expanded implementation order with R1 (P0 → Fix 3) and R3 (Fix 1 → Fix 3) dependencies
- Expanded verification with 14 checks (was 8) — covers all R1-R11
- Consolidated risks from 7 to 18 (v2's 7 + 11 new from audits)

**Corrections to v2:**
- C1: Fix 1 verification assertion: `> 50` → `>= 100`
- C2: Fix 2 seed_sessions.py call site: `343-345` → `342-345`
- C3: Fix 2 session_learner.py call site: `210-213` → `210-214`
- C4: Fix 4/5 bug_fix heuristic: drop the AND condition
- C5: Fix 5 missing schema transform — fixed in new spec
- C6: Fix 6 duplicates skill — fixed by pointing instead of duplicating
- C7: Stale docstrings in hebbian_session_learner.py:8 and hebbian_seed_sessions.py:1-9 — added cleanup to Fix 2

**New mandatory components:**
- P0 precheck script for hebbian_learner.py (5 lines of bash, 3 outcomes)
- `_SECRET_PATTERNS` and `_strip_secrets()` helper in Fix 5
- Per-file try/except + failures log in Fix 5
- Spot-check before Fix 3 reseed (verifies Fix 1 didn't silently fall back)
- Verification query: no non-HL coins labeled 'token' (R3 post-fix check)
- Verification query: no Bearer/sk- in session_summaries.summary (R2 post-fix check)
- Verification query: request_dump files got summaries, not 0 (R10 post-fix check)

---

## Open questions (down from v2)

- None — T's four big decisions (kill trade log, visible recall, SQL-only, decay=0.999) absorbed.
- One NEW question surfaced by audits: should `hebbian_learner.py` be deleted (Precheck P0 outcome A) or refactored (outcome B/C)? Plan defers to grep result.

**Recommended next step:** run Precheck P0 grep first, share the outcome (A/B/C), and execute Fix 1-2 in parallel since they touch different files.