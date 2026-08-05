# Hebbian Integration Plan — 2026-06-24 (post-audit v2)

## Audit status

This plan has been audited by ai-engineer (366s, 15 file reads, 2026-06-24). Critical corrections:

1. Fix 1 had a silent fatal bug — wrong table/column names. ✅ corrected below
2. Fix 2 was incomplete — needs call-site removal at 2 sites, not just function deletion. ✅ corrected below
3. Fix 5 was underspecified — only covered 844 of 4,851 files. ✅ corrected below
4. Fix 3 + Fix 6 dependency made explicit (must do 2 before 6 or daily pollution resumes)
5. Fix 4 needs to also wipe `session_summaries` in `clear_all()` ✅ corrected below

---

## Diagnosis (verified against code)

Current state of `/root/.hermes/brain/associative_memory.db`:

- 144 nodes / 602 synapses. Birth: 2026-05-09. Last write: 2026-06-19.
- Recall on `signal_gen.py`, `Tokyo`, `hebbian`, `cascade_flip`, `XLM` → all empty
- Recall on `ETH` returns only `LONG_BIAS/HOT_APPROVED/APPROVED/SHORT_BIAS/WAIT` — pure trade-log co-occurrence
- Top edges dominated by trade-decision pairs (SKIPPED<->NEUTRAL 1066 fires, etc.)
- 137/144 nodes labeled "token" — auditor's correction: many of these ARE real HL coins (2Z, GAS, ME, DASH, TRB, IMX, etc. are real per `ohlcv_1m`). The real garbage comes from regex artifacts (e.g. `@252` from timestamps) and the reason-text extraction in `seed_decisions_log`.
- Both timers disabled (hebbian-decay, session-learner)
- "9,705 sessions → 1.04M pairs" claim in PROJECTS.md is FALSE — DB has 144 nodes, never seeded properly
- `signals_hermes.db` schema: tables are `price_history`, `latest_prices`, `regime_log`, `ohlcv_1m`. Coin universe column is `token`, NOT `coin`. 104 distinct tokens present.
- 4,851 total session files = 844 `request_dump_*.json` + 4,007 `session_*.json`. Different schemas. `session_*.json` files contain the full SOUL.md as `system_prompt` — must skip that field during entity extraction or it pollutes the graph with the same boilerplate 4,007 times.

**Root causes (in order of severity):**

1. `seed_decisions_log()` at `hebbian_seed_sessions.py:275-329` + its call at line 344 — runs unconditionally, creates the regime<->token<->decision explosion
2. `learn_from_decisions_log()` at `hebbian_session_learner.py:80-123` + its call at line 212 — same pollution via cron
3. Entity extractor ALL_CAPS regex without coin-universe filter at `hebbian_entity_extractor.py:189-193`
4. No `session_summaries` table — only the co-occurrence graph exists, can't query by topic
5. Both systemd timers disabled (hebbian-decay at 4am, session-learner at 6am)
6. SOUL.md has no specific recall triggers — just "use proactively"

**Additional bugs the auditor caught (not in original plan):**

- `hebbian_session_learner.py:99-100` — `direction = d.get("decision")` reads wrong field; both vars get same value. Reduces pollution accidentally but silently drops direction pairs.
- Vocabularies (KNOWN_TOKENS, KNOWN_SKILLS, etc.) duplicated across 4 files with subtle differences — refactor candidate, not blocking.
- `clear_all()` at `hebbian_engine.py:244-249` doesn't include the new `session_summaries` table — must be updated when we add it.

---

## Surgical Fix Plan (8 fixes, audit-corrected)

### Fix 1: Entity extractor — real coin universe filter

File: `/root/.hermes/scripts/hebbian_entity_extractor.py`

Replace the current top-of-file setup to load the HL coin universe from `signals_hermes.db`. **Table is `ohlcv_1m`, column is `token`.** Hardcoded fallback if DB is missing/empty.

```python
import sqlite3
import os
from typing import Optional

DB_PATH = "/root/.hermes/data/signals_hermes.db"

# Top-50 fallback if signals_hermes.db is missing/empty
_FALLBACK_COINS = {
    "BTC", "ETH", "SOL", "AVAX", "XRP", "DOGE", "ADA", "DOT", "LINK",
    "UNI", "AAVE", "MKR", "SNX", "DYDX", "GMX", "LDO", "CRV", "APE",
    "INJ", "TIA", "SEI", "WIF", "PEPE", "SHIB", "FLOKI", "ARB", "OP",
    "MATIC", "POL", "GALA", "ENJ", "MANA", "AXS", "ICP", "ETHFI", "SKY",
    "PENDLE", "SAND", "RNDR", "VET", "NEAR", "APT", "SUI", "TON", "XLM",
    "HBAR", "FIL", "ATOM", "TRX", "AVAX",
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
            return coins if len(coins) >= 10 else set(_FALLBACK_COINS)
        finally:
            conn.close()
    except Exception as e:
        import sys
        print(f"[hebbian_entity_extractor] WARN: failed to load coin universe: {e}", file=sys.stderr)
        return set(_FALLBACK_COINS)

HL_COINS = _load_coin_universe()
```

Then update `infer_label` at line 99 to use this:
```python
def infer_label(candidate: str) -> Optional[str]:
    c = candidate.strip()
    c_lower = c.lower()
    if c in KNOWN_TOKENS or c in HL_COINS:
        return "token"
    # ... rest unchanged ...
```

Also tighten the ALL_CAPS regex block at line 189 to filter against HL_COINS:
```python
# OLD: just checks against a small stopword set
# NEW: must be in HL_COINS to be labeled "token"
for match in ALL_CAPS.finditer(text):
    val = match.group(1).strip()
    if val in HL_COINS and val not in seen:
        seen.add(val)
        found.append((val, "token"))
    # else: skip — it's not a real HL coin
```

**Verification**: After this lands:
```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS
print(f'HL_COINS size: {len(HL_COINS)}')
assert len(HL_COINS) > 50, 'Coin universe too small — Fix 1 did not load'
print('Sample:', list(HL_COINS)[:10])
"
```
Expected: prints ~104 coins.

### Fix 2: Stop learning from decisions.jsonl — INCLUDING call sites

The plan must remove the functions AND every place that calls them. Audit confirmed 2 call sites:

**`/root/.hermes/scripts/hebbian_seed_sessions.py`:**
- DELETE lines 275-329 (the entire `seed_decisions_log()` function)
- DELETE lines 343-345 in `main()`:
  ```python
  # Seed from decisions log
  print("\n[Decisions Log]")
  n = seed_decisions_log()
  print(f"Learned {n} pairs from decisions log")
  ```

**`/root/.hermes/scripts/hebbian_session_learner.py`:**
- DELETE lines 80-123 (the entire `learn_from_decisions_log()` function)
- DELETE lines 210-213 in `main()`:
  ```python
  # 2. Decisions log
  print("[Decisions Log]")
  n = learn_from_decisions_log(engine, days_back)
  print(f"  Learned {n} trading decision pairs")
  total_pairs += n
  ```

**While we're in there, fix the latent bug** at lines 99-100:
```python
# OLD (buggy):
direction = d.get("decision")  # actually reads "decision" field
decision = d.get("decision")
# NEW:
direction = d.get("direction", "")
decision = d.get("decision", "")
```

But wait — we're deleting those functions. So this latent bug fix only matters if those functions survive. Since we're deleting them, skip this fix.

**Verification** after this lands:
```bash
grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/
# Expected: no output (functions and call sites all gone)
```

### Fix 3: Wipe + reseed (RUN AFTER Fix 1 + Fix 2)

```bash
# Backup first
cp /root/.hermes/brain/associative_memory.db /root/.hermes/brain/associative_memory.db.bak-2026-06-24

# Wipe (only after Fix 4 has updated clear_all to include session_summaries)
python3 /root/.hermes/scripts/hebbian_engine.py clear_all

# Reseed
python3 /root/.hermes/scripts/hebbian_seed_sessions.py 200
```

Note: this reseed only covers 844 `request_dump_*.json` files. The 4,007 `session_*.json` files are out of scope for the seeder — Fix 5 adds a separate distill script that handles both.

**Verification** after reseed:
```bash
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type ORDER BY 2 DESC;"
# Expected: mix of file, skill, concept, project labels — NOT dominated by decision/regime
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM concept_nodes;"
# Expected: thousands of nodes, not 144
```

### Fix 4: Add session_summaries table + recall functions

File: `/root/.hermes/scripts/hebbian_engine.py`

Add to `_init_db()` after the existing tables:
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

Update `clear_all()` (line 244-249) to wipe it too:
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

Add helper methods:
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
    base = filepath.removesuffix('.py')
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

**Verification**:
```bash
sqlite3 /root/.hermes/brain/associative_memory.db ".schema session_summaries"
# Expected: shows the new table
```

### Fix 5: Backfill session_summaries from existing dumps

New file: `/root/.hermes/scripts/hebbian_session_distill.py`

Handles BOTH file types (`request_dump_*.json` AND `session_*.json`). For `session_*.json`, MUST skip the `system_prompt` field — it's the full SOUL.md embedded, which would create 4,007 duplicate co-occurrences of every concept in SOUL.md.

**Summary generation method (heuristic, no LLM):**
- Take the first user message, truncate to 200 chars
- Extract top 5 entities from that message
- Append: `summary = "[{discussion_type}] " + first_user_msg[:200] + " | " + " ".join(top5_entities)`

**Discussion type heuristic** (regex-only):
- `bug_fix`: contains trigger word (`bug|broken|wrong|fix|regression|reversed`) AND a fix verb (`fixed|reversed|changed|added|removed|patched`)
- `decision`: contains (`decided|going with|let's use|approved|rejected|chose|picked`)
- `plan`: contains numbered list pattern or markdown `## Step` or `Phase`
- `refactor`: contains (`refactor|rewrite|restructure|moved|split`)
- `coin`: mentions an HL_COINS ticker AND contains (`trending|setup|looking at|watching|breaking out`)
- else: `analysis`

**Idempotency**: check `session_summaries` for existing `session_id` before insert; skip if present.

**Background execution**:
```bash
nohup python3 /root/.hermes/scripts/hebbian_session_distill.py > /root/.hermes/data/hebbian_distill.log 2>&1 &
echo $! > /tmp/hebbian_distill.pid
```

Use `process` action `wait` or `poll` to monitor.

**Coverage decision (per audit)**: scope to all 4,851 files. 1.8 GB total. The distill script doesn't need to read the full content — only first 200 chars per message + entity extraction, so it's I/O-bound but not memory-heavy. Estimate: 5-15 min in background.

**Verification** after Fix 5:
```bash
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries;"
# Expected: hundreds to ~thousands

sqlite3 /root/.hermes/brain/associative_memory.db "SELECT discussion_type, COUNT(*) FROM session_summaries GROUP BY discussion_type;"
# Expected: most are 'analysis', some 'plan', few 'bug_fix'/'decision'

PYTHONPATH=/root/.hermes/scripts python3 -c "
from hebbian_engine import recall_sessions_for_file, recall_sessions_for_coin
r = recall_sessions_for_file('signal_compactor')
print(f'Found {len(r)} sessions for signal_compactor')
for s in r[:3]:
    print(' ', s.get('summary', '')[:120])
"
```

### Fix 6: SOUL.md update (RUN BEFORE Fix 7)

File: `/root/.hermes/SOUL.md` (path confirmed: `/root/.hermes/SOUL.md`, not `brain/SOUL.md`)

Existing hebbian block at lines 24-40. Add an explicit triggers section after it:

```markdown
### When to recall (proactive triggers)

Call `mcp_hermes_coding_mcp_hebbian_recall` from MCP, OR run `python3 /root/.hermes/scripts/hebbian_engine.py recall <concept>`:

| T's message contains | Recall these concepts |
|---|---|
| Session start (any topic) | `trading`, `signal_compactor`, `Tokyo` (broad entry points) |
| Coin ticker (e.g. `XLM`, `ETH`, `SOL`) | that ticker |
| `.py` filename (e.g. `signal_compactor.py`) | filename with and without `.py` |
| "the X bug", "X is broken", "X issue" | `X` |
| "what did we do", "remind me" | concepts from message |

**Skip recall** for: greetings, status checks, smoke tests, "show me stats", pure commands.

**Visible mode**: if recall returns weight >= 5.0 associations, surface 1-3 in the reply:
> "I recall we discussed X in a prior session — Y."

**Session-level recall** (better than co-occurrence for "what did we do" questions):
```python
from hebbian_engine import recall_sessions_for_file, recall_sessions_for_coin
# e.g. "what did we do on signal_compactor?"
print(recall_sessions_for_file("signal_compactor.py"))
```
```

**Verification**: after fix, just `grep -c "When to recall" /root/.hermes/SOUL.md` should return 1.

### Fix 7: Enable systemd timers (RUN AFTER Fix 2 + Fix 5)

```bash
# Verify the call-site removal in session_learner.py landed first
grep -n "learn_from_decisions_log\|decisions.jsonl" /root/.hermes/scripts/hebbian_session_learner.py
# Expected: no output

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

### Fix 8: Skill update

File: `/root/.hermes/skills/associative-recall/SKILL.md`

The skill is mostly accurate already (mentions the MCP tool, lists trigger conditions). The audit's correction: this is mostly cosmetic. Add:
- New session_summaries recall functions
- Updated label distribution example after fixes
- Note that trade-log learning is disabled

---

## Implementation order (audit-corrected)

1. **Fix 1** (entity extractor — corrected table/column, fallback list)
2. **Fix 2** (kill decision-log learning — function AND call sites at 2 places)
3. **Fix 4** (session_summaries schema + clear_all update)
4. **Fix 3** (backup → wipe → reseed — only after 1+2+4 land)
5. **Fix 5** (distill script — background it, handle both file types, skip system_prompt)
6. **Fix 6** (SOUL.md update — gets the recall triggers in place before the timer turns on)
7. **Fix 7** (enable timers — only after Fix 2 verified, or daily pollution resumes)
8. **Fix 8** (skill update — cosmetic, last)

Critical order dependencies:
- Fix 2 must complete before Fix 7 (otherwise timer re-introduces pollution)
- Fix 4 must complete before Fix 3 (otherwise clear_all doesn't wipe session_summaries)
- Fix 6 must complete before Fix 7 (otherwise new data lands but agent has no recall rules)

---

## Verification (full)

After all 8 fixes:

```bash
# 1. Entity extractor loads coin universe
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_entity_extractor import HL_COINS
print(f'HL_COINS: {len(HL_COINS)} tokens')
assert len(HL_COINS) > 50
"

# 2. No call sites for killed functions
grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/
# Expected: empty

# 3. DB has variety of labels
sqlite3 /root/.hermes/brain/associative_memory.db \
  "SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type ORDER BY 2 DESC;"
# Expected: file/skill/concept/project mix, NOT dominated by decision/regime

# 4. Session summaries exist
sqlite3 /root/.hermes/brain/associative_memory.db "SELECT COUNT(*) FROM session_summaries;"
# Expected: hundreds+

# 5. Recall returns useful associations
PYTHONPATH=/root/.hermes/scripts python3 /root/.hermes/scripts/hebbian_engine.py recall signal_compactor
PYTHONPATH=/root/.hermes/scripts python3 /root/.hermes/scripts/hebbian_engine.py recall XLM
# Expected: real associations, not empty, not just regime/decision

# 6. Session-level recall works
PYTHONPATH=/root/.hermes/scripts python3 -c "
from hebbian_engine import recall_sessions_for_file
print(recall_sessions_for_file('signal_compactor'))
"

# 7. Timers enabled
systemctl --user list-timers --all | grep hebbian

# 8. SOUL.md updated
grep -c "When to recall" /root/.hermes/SOUL.md
```

---

## Risks

1. **Wipe loses existing data.** Mitigation: backup DB to `associative_memory.db.bak-2026-06-24` before clear_all.
2. **Coin universe might not load** if signals_hermes.db is empty. Mitigation: 50-coin hardcoded fallback.
3. **Distill script processes 4,007 session_*.json files that all contain the same SOUL.md** — if we don't skip the `system_prompt` field, we re-pollute the graph with every SOUL.md concept × 4,007. Mitigation: skip system_prompt during entity extraction in the distill script.
4. **Discussion_type heuristic under-fires** for `bug_fix` and `decision` (auditor tested — most sessions classify as `analysis`). Acceptable: the buckets work, sparse buckets are still useful when they fire.
5. **Storage bloat**: 4,851-file backfill ≈ 5M pairs ≈ 250 MB. SQLite handles it fine. The session_summaries table stays small (~5,000 rows). Acceptable.
6. **Race condition: Fix 3 wipe leaves stale session_summaries** — fixed by updating `clear_all()` in Fix 4 BEFORE running Fix 3.
7. **Latent bug at hebbian_session_learner.py:99-100** is moot since the function gets deleted in Fix 2.

---

## Open questions

None — T answered the four big ones (kill trade log, visible recall, SQL-only, keep decay at 0.999). The audit caught all the technical bugs.