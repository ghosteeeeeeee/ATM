# Plan: Hebbian Neural Network Memory for Hermes

**Date:** 2026-04-09  
**Author:** Hermes Agent  
**Type:** Architecture + Implementation Plan  

---

## Goal

Add a Hebbian associative memory layer to Hermes — "neurons that fire together, wire together." When concepts/entities co-occur across **any** domain (trading, projects, infrastructure, skills, files), their connection strength grows. This makes memory retrieval smarter: related context surfaces automatically based on Hermes's own experience, not just keyword matching.

**General purpose, not trading-specific.** Works across all Hermes domains.

---

## Current Context / Assumptions

- Hermes already has **two memory systems**:
  1. **File-based** — brain/*.md files (CONTEXT.md, SOUL.md, TASKS.md, etc.) — structural, not content-addressable
  2. **Tokyo Brain API** — pgvector-backed semantic search at `117.55.192.97:12345/brain/api/` via `brain-memory` skill — AI-powered but requires external server, SSH tunnel, and a running API
- Hermes also has **session_search** — searches past conversations by keyword
- **Signal runtime DB** at `/root/.hermes/data/signals_hermes_runtime.db` (SQLite) — stores signal records with token, direction, confidence, regime
- **No existing Hebbian/associative memory** — concepts are not linked by co-occurrence
- The goal is NOT to replace the Brain API — it's to add a lightweight, self-contained Hebbian layer that works with or without Tokyo

### Key Insight

The phrase "neurons that fire together, wire together" means:
- When concept A and concept B appear together (e.g., in the same session turn, same signal event, same file reference), increment their connection weight
- Weight accrues positively — frequent co-occurrence = strong link
- Optional: decay over time so old associations fade
- Retrieval: given concept A, return ranked list of strongly-linked concepts

---

## Proposed Approach

### Architecture: Hebbian Memory Graph

**Storage:** SQLite table in a new `brain/associative_memory.db` — lightweight, self-contained, no external dependencies.

```
concept_nodes
  id          INTEGER PRIMARY KEY
  name        TEXT UNIQUE          -- canonical concept name (e.g., "hyperliquid", "cascade_flip", "SCR", "Tokyo", "Dallas")
  label_type  TEXT                 -- "token", "skill", "file", "concept", "person", "project", "infra", "asset"
  created_at  TIMESTAMP
  last_seen   TIMESTAMP

synapse_weights
  id              INTEGER PRIMARY KEY
  concept_a_id    INTEGER FK -> concept_nodes.id
  concept_b_id    INTEGER FK -> concept_nodes.id
  weight          REAL DEFAULT 1.0     -- accumulated co-occurrence strength
  co_occurrences  INTEGER DEFAULT 1     -- how many times they fired together
  last_updated    TIMESTAMP
  UNIQUE(concept_a_id, concept_b_id)
```

**Normalization:** `(concept_a_id < concept_b_id)` enforced in code so A↔B and B↔A share one row.

### Core Hebbian Operations

| Operation | Hebbian Rule |
|-----------|-------------|
| **Learn** (co-occurrence) | `weight += 1.0` when A and B fire in same context window |
| **Recall** (given A) | `SELECT B WHERE A→B weight DESC LIMIT K` |
| **Decay** (optional, nightly) | `weight *= 0.95` for all edges older than 7 days |

### Integration Points — All Domains

When should concepts "fire together"? Hook into existing Hermes events across any domain:

1. **Session turns** — Every LLM turn contains concepts (project names, skill names, file paths, task names, asset names). Extract entities and record co-occurrences within a sliding window (same user message = one firing event)
2. **Project/task events** — When reading or updating TASKS.md, PROJECTS.md, DECISIONS.md in the same session, their concepts co-fire (e.g., "cascade_flip" + "Signal Enhancement" project)
3. **Skill usage** — When loading and using a skill, the skill name and target concepts co-fire (e.g., `code-review` + `signal_gen.py`)
4. **Infrastructure** — When working on Tokyo/Dallas servers, related configs and scripts co-fire (e.g., `hyperliquid_exchange.py` + `guardian`)
5. **File access** — When brain files are read together in a session, their contents' entities co-fire
6. **Signal generation** (trading) — token + regime + direction co-fire
7. **Trade events** (trading) — token + direction + outcome co-fire
8. **Subagent events** — When spawning a subagent, the task goal and related files/skills co-fire

### Retrieval — Making it Useful

A new skill `associative-recall`:
- Given a query concept, return top-K strongly linked concepts across all domains
- Example uses:
  - Query `Tokyo` → returns `["Dallas", "brain-sync", "SSH", "infrastructure"]`
  - Query `cascade_flip` → returns `["signal_gen", "SCR", "SHORT", "regime_filter"]`
  - Query `project-management` → returns `["TASKS.md", "kanban", "brain-memory", "hermes-brain-sync"]`
- This is different from semantic search — it finds what *Hermes itself* has linked through experience
- Sessions can surface related context before responding: "I see you mentioned Tokyo — you also worked on brain-sync recently and had issues with the SSH tunnel"

A new MCP tool `hermes_recall`:
- `recall(concept, k=5)` → returns ranked list of associated concepts with weights
- Used by the AI before responding to surface related context

### Weight Dynamics

```
Initial:    w = 1.0
On fire:    w += 1.0  (per co-occurrence event)
Decay:      w *= 0.999 per day (elephant's memory — ~3% loss/year, ~0.3%/month)
Ceiling:    w max = 100.0 (prevent overflow)
Threshold:  w < 0.5 → don't surface in recall (too weak)
```

---

## Step-by-Step Plan

### Phase 1: Foundation (Core Hebbian Engine)

- [ ] Create `/root/.hermes/brain/associative_memory.db` with schema above
- [ ] Write `/root/.hermes/scripts/hebbian_engine.py`:
  - `learn_pair(concept_a, concept_b, label_type_a=None, label_type_b=None)` — upsert nodes + increment weight
  - `recall(concept, k=5, min_weight=0.5)` — return ranked associated concepts
  - `decay_all(decay_factor=0.995, min_age_days=7)` — nightly decay run
  - `get_stats()` — total nodes, total synapses, top-weighted edges
- [ ] Write unit tests: learn/recall cycle, bidirectional symmetry, weight ceiling, decay

### Phase 2: Integration Hooks (All Domains)

- [ ] Hook into `signal_gen.py` — add `hebbian_engine.learn_pair()` for (token, regime) and (token, direction) co-occurrences
- [ ] Hook into `position_manager.py` — add learn_pair for (token, outcome) on trade close
- [ ] Hook into `ai_decider.py` — add learn_pair for (token, regime, confidence_bucket) tuples in scoring
- [ ] **General entity extractor** — new `scripts/entity_extractor.py` using LLM to pull concept-label pairs from any text (session messages, file contents, subagent goals). Replaces hand-rolled entity detection
- [ ] Hook into **every session turn** — extract entities from user message, call learn_pair on all pairs within the message
- [ ] Hook into **brain file reads** — when TASKS.md + PROJECTS.md + DECISIONS.md are read in same session, create cross-file concept links
- [ ] Hook into **skill loading** — when a skill is loaded (via skill_view or skill_manage), learn_pair(skill_name, target_topic)
- [ ] Hook into **subagent spawning** — goal + related files + skills co-fire
- [ ] Hook into **infrastructure events** — Tokyo/Dallas server context in session → link to related infra concepts

### Phase 3: Retrieval Layer

- [ ] Create skill `associative-recall` — CLI + skill instructions for using recall
- [ ] Create MCP tool `hebbian_recall` in hermes-coding-mcp server
- [ ] Add to `brain-memory` skill as a third recall mode alongside semantic/text search
- [ ] Create `/root/.hermes/scripts/hebbian_learner.py` — batch process old sessions to seed initial network from existing brain files

### Phase 4: Visualization & Monitoring (Optional)

- [ ] Add `/trades` endpoint or Streamlit tab showing "most connected concepts"
- [ ] `wasp` check: warn if no new synapses recorded in 24h (learner is silent)
- [ ] Daily decay via systemd timer `hermes-hebbian-decay.timer` (4am UTC)

---

## Files Likely to Change

| File | Change |
|------|--------|
| `brain/associative_memory.db` | **NEW** — SQLite Hebbian graph |
| `scripts/hebbian_engine.py` | **NEW** — core engine |
| `scripts/hebbian_learner.py` | **NEW** — batch seeder |
| `scripts/signal_gen.py` | Hook learn_pair on signal emit |
| `scripts/position_manager.py` | Hook learn_pair on trade close |
| `scripts/ai_decider.py` | Hook learn_pair on scoring |
| `skills/associative-recall/` | **NEW** — recall skill |
| `skills/brain-memory/` | Update — add associative-recall as 3rd recall mode |
| `brain/trading.md` | Document new system |
| `brain/TASKS.md` | Add tasks |
| `brain/PROJECTS.md` | Add project entry |
| `brain/ideas.md` | Add idea entry |

---

## Tests / Validation

1. **Learn/Recall cycle:**
   - `learn_pair("SCR", "SHORT")` → `recall("SCR")` returns "SHORT" with weight ≥ 1.0
2. **Bidirectional:** `recall("SHORT")` returns "SCR" (same edge, symmetric)
3. **Weight accumulation:** calling learn_pair twice → weight = 2.0
4. **Decay:** after decay_all(0.5), weight halves
5. **New concept:** unknown concept returns empty list (graceful)
6. **Stress test:** 10,000 learn_pair calls — no slowdown (indexed)

---

## Risks, Tradeoffs, and Open Questions

### Tradeoffs
- **PostgreSQL vs SQLite:** Tokyo Brain API uses pgvector for semantic search — powerful but external. This Hebbian layer is SQLite — simpler, self-contained, no pgvector needed. They complement each other.
- **Co-occurrence granularity:** Too coarse (session-level) = noisy links. Too fine (every word) = combinatorial explosion. Start with "per user message / per signal event" as atomic firing events.

### Risks
1. **Concept collision:** "SCR" (Suiet) vs "SCR" (some other thing) — use label_type to disambiguate
2. **Weight inflation:** Over time weights creep up. Mitigated by ceiling (100) + decay
3. **Cold start:** New system starts empty. Mitigated by `hebbian_learner.py` seeding from existing brain files

### Open Questions
1. **Should we use the Brain API's pgvector for semantic clustering** and layer Hebbian on top? E.g., cluster similar concepts automatically, then Hebbian links clusters
2. **Decay schedule:** Nightly? Weekly? TBD based on observed drift
3. **Max concepts per firing event:** If a message mentions 5 concepts, do we create `C(5,2)=10` pairs? That may be fine early on, but may need capping
4. **Should weights be directional?** (A→B stronger than B→A?) — probably not for now, keep symmetric

---

## Reference: Hebbian Learning Formula

```
Hebb's Rule (simplified):
w_ij += Δw  where Δw = η * x_i * x_j

In our discrete implementation:
- x_i, x_j ∈ {0, 1} (neuron fires or not in time window)
- η = 1.0 (each co-occurrence is equally weighted)
- w_ij = accumulated connection strength
- Recall: concepts ranked by w_ij descending
```

*"Neurons that fire together, wire together"* — Donald Hebb, 1949
