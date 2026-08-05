# Hebbian Network Diagnostic — 2026-06-24

Findings from a study-first session where T asked how to improve the Hebbian integration. Captured here so future sessions don't re-investigate the same ground.

## Schema (verified)

```
concept_nodes(id INTEGER PK, name TEXT UNIQUE, label_type TEXT, created_at, last_seen)
synapse_weights(id INTEGER PK, concept_a_id INTEGER FK, concept_b_id INTEGER FK,
                weight REAL, co_occurrences INTEGER, last_updated,
                UNIQUE(concept_a_id, concept_b_id))
```

- Weight range: 0.5 (floor) - 100.0 (ceiling)
- Increment: +1.0 per learn_pair call
- Decay: 0.999x per day (timer currently disabled)

## Current DB state (2026-06-24)

- 144 nodes / 602 synapses
- Label distribution: token=137, decision=4, regime=3 (no file, no skill, no project)
- File birth: 2026-05-09 (engine.py install date)
- Last write: 2026-06-19

## Top edges (pollution)

```
SKIPPED         <-> NEUTRAL       : 99.5 (1066 fires)
HOT_APPROVED    <-> LONG_BIAS     : 99.5 (2434 fires)
SHORT_BIAS      <-> APPROVED      : 99.5 (1019 fires)
LONG_BIAS       <-> GALA          : 99.5 (239 fires)
HOT_APPROVED    <-> GALA          : 99.5 (182 fires)
NEUTRAL         <-> APPROVED      : 99.5 (1125 fires)
LONG_BIAS       <-> ZEC           : 99.5 (413 fires)
LONG_BIAS       <-> APPROVED      : 99.5 (1464 fires)
SKIPPED         <-> LONG_BIAS     : 99.5 (572 fires)
LONG_BIAS       <-> ICP           : 99.5 (140 fires)
```

All hit weight ceiling (99.5) because of high-frequency co-firing. These edges are useless for recall — they answer "what regime was this coin in during trades?" not "what did we discuss about this coin?"

## Empty recall (verified)

These queries return NOTHING:
- `recall hebbian`
- `recall signal_compactor`
- `recall signal_compactor.py`
- `recall cascade_flip`
- `recall XLM`
- `recall Tokyo`
- `recall accel_300`

These return only regime/decision noise:
- `recall ETH` → LONG_BIAS, HOT_APPROVED, APPROVED, SHORT_BIAS, WAIT
- `recall BTC` → LONG_BIAS, HOT_APPROVED, NEUTRAL, APPROVED, WAIT

## Token-label garbage (verified)

A query of recent concept_nodes shows label_type=token on words that are not HL coins:

```
MERL, DASH, IP, KAS, BRETT, 2Z, AIXBT, BERA, BSV, DYM, 0G, ETC, TAO, LIT, ME, GAS, MAV, GRASS, PROVE, GRIFFAIN
```

ALL_CAPS regex `\b([A-Z]{2,8})\b` catches any uppercase word — including prose like "AI", "IP", "ME", "DASH" — and labels it as a token.

## Duplicate extractors (4 places)

Each has its own `KNOWN_TOKENS`, `KNOWN_SKILLS`, `infer_label`/`extract_entities`:

1. `/root/.hermes/scripts/hebbian_learner.py` — initial brain/*.md seeder
2. `/root/.hermes/scripts/hebbian_seed_sessions.py` — retroactive request_dump seeder
3. `/root/.hermes/scripts/hebbian_entity_extractor.py` — generic surface extractor
4. `/root/.hermes/scripts/hebbian_session_learner.py` — daily session learner

Adding a coin to KNOWN_TOKENS in only one file is a known footgun.

## Timer state (verified)

```
hermes-hebbian-decay.timer:   loaded, DISABLED (no decay)
hermes-session-learner.timer: loaded, DISABLED (no daily learning)
```

Both have valid `.service` files, never auto-run since install.

## Decisions log stats

- `/root/.hermes/wandb-local/decisions.jsonl`: 5,086 lines
- Format: `{timestamp, cycle, regime, hotset_size, top_token, direction, top_score, decision, is_hot_auto, is_pattern, speed_percentile, n_signals_total, n_pattern_signals, reason}`
- Each line = multiple co-occurrence fires when learned (token<->regime, regime<->direction, decision<->token, etc.)

## Session dumps available (not yet used by brain)

- `/root/.hermes/sessions/request_dump_*.json`: 4,851 files
- Format: `{request: {body: {messages: [{role, content}, ...]}}}`
- Currently parsed only for surface entity extraction, never distilled to typed summaries

## Decisions log reasoning (per T)

T explicitly chose: **kill the decision-log learning entirely**. Reasoning:
- It drowns out the conversation/code graph
- Trade pattern analysis is a separate concern
- Belongs in `trades_brain.db` if we ever want it back

Don't add it back to the conversation graph.

## T preferences captured

- Recall mode: **visible** (surface "I recall X" in replies, not silent context)
- Session summaries: **SQL-only** (no markdown mirror)
- Decay rate: **keep 0.999** (slow, long memory)

## Plan document

Full implementation plan written to:
`/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24.md`

Status: plan written, NOT YET EXECUTED. Awaiting T's go-ahead to implement.