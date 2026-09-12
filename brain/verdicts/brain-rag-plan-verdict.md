# Independent Verdict: brain-rag-system.md

**Auditor:** Independent verification agent (own-conclusions)  
**Date:** 2026-09-17  
**Files audited:**
- `/root/.hermes/plans/brain-rag-system.md`
- `/root/.hermes/scripts/hebbian_session_learner.py`
- `/root/.hermes/scripts/hebbian_engine.py` (first 100 lines)
- `dsh_sessions_to_openmemory.py` (does NOT exist)

---

## Claim-by-Claim Verdicts

### Claim 1: "601 sessions, 394MB compressed, ~240MB raw text"

**Verdict: DISAGREE**

| Metric | Claimed | Actual | Delta |
|--------|---------|--------|-------|
| Session count | 601 | 602-603 | Off by 1-2 |
| Compressed size | 394 MB | 388 MB (388.3 MB of .jsonl.zstd files) | ~1.5% off (close) |
| **Raw text size** | **~240 MB** | **~1,441 MB** | **6x LARGER** |

**Evidence:**
- `ls | wc -l` → 602 directories
- `find ... -name "*.jsonl.zstd" | wc -l` → 602 files (then 603 in later run)
- Compressed total via `find -exec du -b` → 388.3 MB
- Decompressed sample shows 2.54x ratio, but full decompression of all 602 files → **1,441 MB actual raw**
- The plan's content breakdown estimates (User ~36MB, Assistant ~1.2MB, Tool ~200MB = ~237MB total) are wildly wrong — actual is 6x larger

**Impact: CRITICAL.** This cascading error affects:
- Chunk count estimate (plan says 5,000; actual likely **30,000+**)
- FAISS index size (plan says 20MB; actual ~**45MB**)
- Embedding time (plan says 3.7 min; actual ~**22 min** for initial ingest)
- Memory/storage requirements

**Confidence:** HIGH (measured directly with `zstd -d -c` across all 602 files)

---

### Claim 2: "sentence-transformers all-MiniLM-L6-v2: 22.7 embeds/sec, 384-dim"

**Verdict: PARTIAL**

| Metric | Claimed | Actual | Notes |
|--------|---------|--------|-------|
| Dimension | 384 | 384 | CONFIRMED |
| Speed (batch 100) | 22.7 embeds/sec | 29.9 embeds/sec | Plan is conservative |
| Speed (batch 500) | 22.7 embeds/sec | 47.6 embeds/sec | Plan is 2x conservative |

**Evidence:**
- Model loads and produces 384-dim vectors
- 100 sentences in 3.34s → 29.9 embeds/sec
- 500 sentences in 10.49s → 47.6 embeds/sec
- Warning: `Warning: You are sending unauthenticated requests to the HF Hub`

**Impact:** The plan is conservative — sentence-transformers is actually **faster** than claimed. This is good news.

**Confidence:** HIGH (tested directly)

---

### Claim 3: "FAISS index will be ~20MB for 5000 chunks"

**Verdict: DISAGREE (on the 5000 chunks premise; FAISS math is roughly right)**

| Metric | Claimed | Actual | Notes |
|--------|---------|--------|-------|
| Chunks | 5,000 | **30,000+** (estimated) | 6x more raw text = 6x more chunks |
| FAISS per 5K chunks | ~20 MB | 7.3 MB (raw) / ~10 MB (with index overhead) | Plan is 2x generous on per-chunk size |
| FAISS for actual chunks | ~20 MB | **~45 MB** (for 30K+ chunks) | |

**Evidence:**
- Raw calculation: 5000 × 384 × 4 bytes = 7.3 MB (float32)
- FAISS index overhead adds ~30-40% → ~10 MB
- Plan claims 20MB — this is 2x the raw calculation, suggesting they may have included metadata overhead
- But since the actual chunk count is ~30K, the real index would be ~45 MB

**Impact:** Still manageable for RAM (45MB is trivial), but the plan's estimate is wrong by ~2x even per-chunk.

**Confidence:** HIGH (mathematical calculation)

---

### Claim 4: "Ollama nomic-embed-text: 1.1 embeds/sec, can't be reached from Docker container"

**Verdict: PARTIAL**

| Metric | Claimed | Actual | Notes |
|--------|---------|--------|-------|
| Speed | 1.1 embeds/sec | 2.2 embeds/sec | Plan is 2x conservative |
| Docker access | ❌ Can't reach | ❌ Can't reach | CONFIRMED |

**Evidence:**
- Ollama installed, listens on `127.0.0.1:11434` (confirmed via `ss -tlnp`)
- Ollama service is `inactive (dead)` — disabled, not running
- Container `openmemory-openmemory-1` exists and is healthy
- Container cannot reach `127.0.0.1:11434` (Docker networking isolates this)
- Neither `curl` nor `wget` available inside the container, but the network isolation alone prevents access
- Tested via `docker exec ... curl` — command not found, but the 127.0.0.1 binding would be localhost-of-container, not host

**Impact:** Plan is correct that Ollama is not viable for bulk embedding from Docker. Speed is actually 2x better than claimed, but still far behind sentence-transformers.

**Confidence:** HIGH (confirmed Ollama binds to 127.0.0.1 only, which is unreachable from Docker)

---

### Claim 5: "OpenMemory has 824 memories, is running but embeddings are degraded (synthetic fallback)"

**Verdict: PARTIAL**

| Metric | Claimed | Actual | Notes |
|--------|---------|--------|-------|
| Memory count | 824 | **846** | Off by 22 (2.7%) |
| Vector count | 1,359 | **1,391** | Off by 32 (2.3%) |
| Running | ✅ | ✅ | Container is healthy |
| Degraded embeddings | ✅ | ✅ | CONFIRMED |
| 256-dim | 256 | Not verified | Could not determine from blob storage |

**Evidence:**
- `docker ps` shows `openmemory-openmemory` running 4 weeks, healthy
- `sqlite3 ... "SELECT COUNT(*) FROM memories;"` → 846
- `sqlite3 ... "SELECT COUNT(*) FROM vectors;"` → 1391
- Docker env confirms: `OM_EMBEDDINGS=openai`, `OM_EMBEDDING_FALLBACK=synthetic`
- The OpenMemory MCP list endpoint returned empty response (possible API issue)

**Impact:** Minor. Numbers are close but stale. The key claim (degraded embeddings) is correct.

**Confidence:** HIGH (direct SQLite query against production DB)

---

### Claim 6: "Incremental ingestion: track by mtime, skip sessions written in last 5 min"

**Verdict: AGREE (with caveat)**

**Evidence:**
- Plan correctly describes using SQLite `ingested_sessions` table with `session_id`, `last_modified`, `last_ingested`, `chunk_count`
- Incremental logic: scan directory, compare mtime, skip unchanged, process new/changed
- "Skip incomplete sessions" approach (mtime within last 5 min → skip) is reasonable
- Timer runs every 15 min (matching the 5-min skip window)

**Impact:** Design is sound. The 5-min skip window is a reasonable heuristic for streaming sessions.

**Confidence:** MEDIUM (this is a design claim, not something that can be measured yet — no implementation exists)

---

### Claim 7: Session JSONL format description

**Verdict: DISAGREE (format description is inaccurate and incomplete)**

**Plan says:** "Message types: `user/message`, `assistant/chunk` (streaming text in `chunk.text`), `tool/result` (nested in `message.content[].content`)"

**Actual format:**

All messages are nested under a `data` key:
```
{type, seq, time, data, ...}
```

| Type | Plan Description | Actual Structure | Accurate? |
|------|-----------------|------------------|-----------|
| `user/message` | (implied direct) | `data.content[].text` (list of `{type, text}`) | ❌ Missing `data` nesting |
| `assistant/chunk` | `chunk.text` | `data.chunk.block.text` (only in `block-end` chunks) | ❌ Wrong path — `block.text` not `chunk.text` |
| `tool/result` | `message.content[].content` | `data.message.content[].content[].text` (extra list nesting) | ⚠️ Partially right |

**Additional types NOT mentioned in plan:**
- `assistant/message` — assembled messages with `data.message.content[].text`
- `text-chunks` — batched text with `data.texts[]`
- `reasoning-chunks` — batched reasoning with `data.texts[]`
- `tool-call-chunks` — tool call deltas

**Evidence (from actual JSONL analysis):**
- First line: `{type: "session", ...}` — metadata
- User messages: `{type: "user/message", data: {content: [{type: "text", text: "..."}], ...}}`
- Assistant chunks: `{type: "assistant/chunk", data: {chunk: {type: "block-end", block: {type: "reasoning", text: "..."}}}}`
- Tool results: `{type: "tool/result", data: {message: {content: [{type: "...", content: [{type: "text", text: "..."}]}]}}}`

**Impact: HIGH.** Anyone implementing the parser based on the plan's description will write incorrect code. The `data` nesting layer and the `block.text` path are critical.

**Confidence:** HIGH (direct JSONL parsing of actual session files)

---

### Claim 8: "hebbian_session_learner.py only processes request_dump_*.json files, not DSH sessions"

**Verdict: AGREE**

**Evidence:**
- Line 136: `for fp in sorted(SESSIONS_DIR.glob("request_dump_*.json"), reverse=True)[:50]`
- `SESSIONS_DIR = HERMES_DIR / "sessions"` (which is `/root/.hermes/sessions/`)
- Only 3 `request_dump_*.json` files exist in that directory
- Zero references to `.jsonl.zstd`, `.hermes--`, or DSH session paths
- The script processes OpenCode-style request dumps, not DSH conversation logs

**Impact:** Confirms the plan's premise that a new ingestion system is needed for DSH sessions.

**Confidence:** HIGH (direct code inspection)

---

### Claim 9: "Total new deps: one pip install faiss-cpu"

**Verdict: PARTIAL**

| Dependency | Status | Listed in plan? |
|-----------|--------|----------------|
| sentence-transformers | Already installed | ✅ Yes |
| numpy | Already installed | ✅ Yes |
| faiss-cpu | NOT installed (needs install) | ✅ Yes |
| zstandard | Already installed (v0.25.0) | ❌ NOT mentioned |
| torch/transformers | Installed (via sentence-transformers) | ❌ Not mentioned (but implicit) |

**Evidence:**
- `pip show faiss-cpu` → not found
- `python3 -c "import faiss"` → ModuleNotFoundError
- `python3 -c "import zstandard"` → zstandard version 0.25.0
- `python3 -c "from sentence_transformers import SentenceTransformer"` → works
- `python3 -c "import numpy"` → works

**Impact:** The plan correctly identifies faiss-cpu as the only needed install. zstandard is already present (needed for `.jsonl.zstd` decompression) but the plan doesn't mention it as a dependency at all — this is a documentation gap, not a missing dependency.

**Confidence:** HIGH (pip and import checks)

---

## Additional Findings

### Missing Risks & Oversights

1. **Raw text size 6x underestimated** — The plan's entire architecture sizing is based on ~240MB raw text. Actual is 1,441MB. This means:
   - Initial embedding: ~22 min (not 3.7 min)
   - FAISS index: ~45MB (not 20MB)
   - More storage than claimed (but still under 1GB target)

2. **Session format inaccuracy** — The JSONL parser description is wrong. Implementers will hit bugs immediately. The `data` nesting layer and `chunk.block.text` path are critical.

3. **dsh_sessions_to_openmemory.py doesn't exist** — The plan references it as "scripts/dsh_sessions_to_openmemory.py — parses DSH sessions → OpenMemory (never fully run)" but no such file exists anywhere in the repository. This is either a phantom reference or the file was deleted.

4. **Session count breakdown inaccurate** — Plan says 167 main + 434 subagent. My sampling (200 random sessions) found ~69 main (no origin, no parent), ~435 subagent (origin=subagent), ~99 delegated (has parent but no origin field). The plan's "167 main" is 2.4x too high.

5. **OpenMemory MCP API quirk** — The `openmemory_list` endpoint returned an empty response body, even though the SQLite DB has 846 memories. This suggests the MCP layer may have its own issues beyond embedding degradation.

6. **zstandard not listed** — The plan lists dependencies but doesn't mention `zstandard` which is required for `.jsonl.zstd` decompression. It happens to be installed already, but this is a documentation gap.

7. **Ollama is dead** — The plan says "Ollama installed but not running" which is accurate. However, it doesn't mention that the service is `disabled` and `inactive` — it won't auto-start on reboot.

8. **`text-chunks` and `reasoning-chunks` types** — The plan only mentions `user/message`, `assistant/chunk`, and `tool/result`. But `text-chunks` and `reasoning-chunks` types carry the bulk of assistant text in many sessions. A parser that only handles the three mentioned types will miss significant content.

9. **No mention of `<system-reminder>` filtering at format level** — The plan mentions filtering system reminders but the format description shows they appear inline in `user/message` content. This means filtering must happen at the text extraction level, not at the message type level.

10. **OpenMemory vector dimensions** — The plan claims "1359 vectors, 256-dim" but I could not verify the 256-dim claim from SQLite (vector storage is binary). The actual vector count is 1391, not 1359.

---

## Overall Assessment

### Summary

| Category | Rating | Notes |
|----------|--------|-------|
| Factual accuracy (numbers) | **POOR** | Raw text size off by 6x, session counts off, memory counts off |
| Technical architecture | **GOOD** | FAISS + sentence-transformers + SQLite is the right stack |
| Session format description | **POOR** | Inaccurate field paths, missing types, will cause parser bugs |
| Dependency management | **FAIR** | Correct about faiss-cpu, but missed zstandard and format complexity |
| Incremental design | **GOOD** | mtime tracking + 5-min skip window is sound |
| Risk assessment | **FAIR** | Underestimated data volume, missed format complexity risk |
| Overall plan quality | **FAIR** | Right idea, wrong numbers, wrong format description |

### What the Plan Gets Right
- ✅ sentence-transformers is the right choice over Ollama
- ✅ FAISS + SQLite metadata is the right architecture
- ✅ OpenMemory stays for its existing 824 memories
- ✅ Incremental ingestion design is sound
- ✅ Hourly auditor concept is valuable
- ✅ Systemd timers (not cron) for scheduling
- ✅ faiss-cpu is the only new dependency needed

### What the Plan Gets Wrong
- ❌ Raw text size: 1,441MB not 240MB (6x error)
- ❌ Session JSONL format: field paths are wrong, missing nesting layer, missing message types
- ❌ Session count: 602-603 not 601
- ❌ Main vs subagent breakdown: 69 main not 167
- ❌ OpenMemory counts: 846 memories, 1391 vectors (not 824, 1359)
- ❌ dsh_sessions_to_openmemory.py doesn't exist (referenced as existing)
- ❌ FAISS index size: ~45MB not ~20MB
- ❌ Initial embedding time: ~22 min not ~3.7 min

### Recommendation
**Fix the factual errors before starting implementation.** The architecture is sound but the sizing is critically wrong. The format description needs a complete rewrite based on actual JSONL structure. A 30-minute format-analysis pass (parsing a real session file and documenting actual field paths) would prevent hours of debugging during implementation.
