# Plan: Fix Hot-Set Signal Quality — ai_decider Bug Fixes

## Goal

Fix three bugs in `ai_decider.py` and `main-prompt.md`:
1. The word `COIN` in the prompt output schema causes the LLM to output `COIN` as a literal token, which then gets rejected by the hallucination guard (line 1560), wasting a hot-set slot
2. `survival_round` from the LLM's compaction is never synced back to `hot_cycle_count` in the DB — tokens that survived r5 cycles lose their round history when a new signal arrives
3. Survivor context fed to the LLM is missing the `regime` field, so counter-regime survivors can't be properly penalized during re-ranking

---

## Issue 1: `COIN` Placeholder in Prompt Schema → LLM Outputs Literal `COIN`

### Root Cause

The prompt output schema (lines 104-105 in `main-prompt.md`) uses `COIN` as an example placeholder:
```
1. COIN | DIRECTION | CONF=75% | ROUNDS=2 | WAVE=... // reason
2. COIN | DIRECTION | CONF=75% | ROUNDS=2 | WAVE=... // reason
```

The LLM confuses this with the literal word `COIN` and sometimes emits it as the actual token in its ranked output, e.g.:
```
1. COIN | LONG | CONF=85% | ROUNDS=3 | WAVE=accelerating | ...
```

The hallucination guard at line 1560 catches this:
```python
if token == '***' or token == 'COIN' or (token not in valid_tokens ...
```

Since `COIN` is not in `valid_tokens` (which contains real symbols like XPL, BTC), the guard fires. The recovery logic then tries to find the token via direction+confidence matching — a lossy operation that can assign one token's slot to a different token. When recovery fails, the slot is dropped entirely.

### Fix

**Step 1a: In `main-prompt.md` output schema, change `COIN` → `COIN_SYM`** in lines 104-105, 109, 113.

The word `COIN_SYM` is unambiguous — it's clearly a placeholder and cannot be confused with a real token symbol.

**Step 1b: In `main-prompt.md` survivor context line 40**, change:
```
For each: COIN | DIRECTION | conf={.}% ...
```
to:
```
For each: COIN_SYM | DIRECTION | conf={.}% ...
```

**Step 1c: In `main-prompt.md` new signals context line 72**, change:
```
For each: COIN | DIRECTION | conf={.}% ...
```
to:
```
For each: COIN_SYM | DIRECTION | conf={.}% ...
```

**Step 1d: In `main-prompt.md` APPROVED/SKIP/REJECTED lines 48-50 and 76-78**, keep `APPROVED:COIN:DIRECTION` format only if the COIN there is in the context of "fill in the coin symbol here" — NOT as an example placeholder. Since those are instruction lines (not output examples), the `COIN` there is already understood as "the coin's symbol" and won't confuse the LLM. No change needed there.

**Step 1e: In `ai_decider.py` line 1560**, remove `token == 'COIN' or` from the guard:
```python
# Before:
if token == '***' or token == 'COIN' or (token not in valid_tokens ...

# After:
if token == '***' or (token not in valid_tokens and token not in _hot_tokens_set):
```
Keep `token == '***'` as a safety net. Keep the invalid-token guard. The `COIN` check is now redundant since `COIN_SYM` in the prompt won't produce `COIN` output.

---

## Issue 2: `survival_round` Never Syncs to `hot_cycle_count` in DB (CRITICAL)

### Root Cause

After the LLM compacts the hot-set, the `survival_round` value (e.g., `SOL=5`) is written to `hotset.json` but **never propagated back** to the `hot_cycle_count` column in `signals_hermes_runtime.db`.

The APPROVED UPDATE at line ~1709 is:
```sql
UPDATE signals
SET decision = 'APPROVED', updated_at = CURRENT_TIMESTAMP
WHERE decision = 'PENDING'
  AND executed = 0
  AND created_at > datetime('now', '-10 minutes')   -- <-- 10-min constraint
  AND token NOT LIKE '@%'
  AND (token='A' AND direction='LONG') OR ...
```

The 10-minute constraint means: if a survivor token's most recent PENDING signal was created 11 minutes ago, the UPDATE affects **0 rows**. The token stays PENDING in the DB with `hot_cycle_count=0`.

When `decider_run._run_hot_set()` queries for open positions (line 876-881), it checks `decision='APPROVED' AND executed=0`. If the UPDATE never fired, the token has no APPROVED record — even though it survived 5 compaction cycles.

**Consequence**: SOL has `survival_round=5` in `hotset.json` (carried forward from previous cycles) but `hot_cycle_count=0` in the DB. A new PENDING signal for SOL (e.g., created at t=0) gets a fresh `hot_cycle_count=0` row. Now there are two SOL records: one with r=0 (new) and one with r=0 (old, never updated). The LLM might see both, get confused, and drop SOL from the hot-set.

### Fix

**Step 2: Add Step 7b after writing `hotset.json`** (~line 1745 in `ai_decider.py`):

After writing `hotset.json`, loop over `hotset_entries` and UPDATE `signals.hot_cycle_count` to match `survival_round` for each ranked token. This bypasses the 10-minute constraint entirely.

```python
# STEP 7b: Sync survival_round → hot_cycle_count in DB
# For all tokens in the new hotset, update hot_cycle_count to match
# survival_round so decider_run and hype-sync see correct round counts.
# This fires regardless of 10-min signal age — we trust the LLM's computation.
for entry in hotset_entries:
    c.execute("""
        UPDATE signals
        SET hot_cycle_count = ?
        WHERE token = ? AND direction = ?
          AND hot_cycle_count < ?
    """, (entry['survival_round'], entry['token'], entry['direction'].upper(),
          entry['survival_round']))
conn.commit()
print(f"  [LLM-compaction] Synced survival_round -> hot_cycle_count for {len(hotset_entries)} tokens")
```

Note: The condition `hot_cycle_count < survival_round` is safe — it never decreases an existing value, only ever increases it to match the LLM's count.

---

## Issue 3: Survivor Context Missing `regime` Field

### Root Cause

The HOT SURVIVORS context built at lines 1313-1331 pulls data from `prev_hotset` (the previous `hotset.json`). However, `hotset.json` entries only get their `regime` and `regime_conf` fields set when the token was **newly ranked** by the LLM in the previous cycle (lines ~1692-1693):

```python
'regime': _reg,        # only set when token is in parsed output
'regime_conf': _reg_conf,
```

When a survivor is carried forward from the previous JSON without being re-parsed, `regime` defaults to `'N'` (neutral) — even if the token had a strong LONG or SHORT regime. The LLM re-ranks the survivor without knowing its regime, and cannot apply the counter-regime penalty.

This means a LONG survivor with regime=SHORT_BIAS stays in the hot-set unpenalized, or a new SHORT signal with regime=LONG_BIAS gets ranked highly despite contradicting the market.

### Fix

**Step 3: Add regime to survivor detail string** (line ~1326 in `ai_decider.py`):

Add `regime={reg_tag}` and `regime_conf` to the survivor detail line:

```python
# Line ~1313 — change survivor builder to include regime
_reg_tag = f"{_reg[:2].upper()}({_reg_conf:.0f}%)" if _reg != 'NEUTRAL' else 'N'
_survivor_detail_str += (
    f"{s['token']} | {s['direction']} | conf={conf:.0f}% | "
    f"regime={_reg_tag} | "   # <-- ADD THIS
    f"rounds={rounds} | src={src} | z={z} | WAVE={wave} | "
    f"MOM={mom:.0f} | SPD={spd:.0f} | OVEREXT={overext} | "
    f"age={age_h:.1f}h\n"
)
```

But this alone won't help — `prev_hotset` from the JSON only has regime for newly-ranked tokens. The real fix requires ensuring ALL tokens with `hot_cycle_count >= 1` have regime data available.

**Step 3b: Also ensure regime is captured for carried-forward survivors in hotset.json write** (lines ~1692-1693):

For carried-forward survivors (tokens in `prev_hotset` but not in `parsed`), the regime should be looked up and included in the JSON too:

```python
# In hotset_entries loop around line 1680:
# For new tokens: regime was computed above
# For carried survivors (from prev_hotset not in parsed):
#   look up regime via get_regime() and include it
```

Actually, the cleanest solution for Issue 3 is the survivor DB query fix described in the next section — that fetches regime for ALL hot tokens from the DB (or the regime cache), not just from the JSON.

**Step 3c (combined with Issue 2's Step 7b): Also sync `regime` to hotset.json for carried survivors**

When writing `hotset.json` at Step 7, for each entry that came from `prev_hotset` (carried survivor, not newly ranked), look up its current regime and include it:

```python
# Around line 1680 — in the hotset_entries building loop:
# Check if token came from prev_hotset as a survivor
_key = f"{s['token']}:{s['direction']}"
if _key in prev_hotset and s.get('regime') in (None, 'N'):
    # Carried survivor — look up current regime
    _reg, _reg_conf = get_regime(s['token'].upper())
    s['regime'] = _reg
    s['regime_conf'] = _reg_conf
```

---

## Comprehensive Step-by-Step

### Step 1: Fix `main-prompt.md` — Replace `COIN` with `COIN_SYM` in Output Schema

File: `/root/.hermes/prompt/main-prompt.md`

In the output schema section (lines 104-105), replace:
```
1. COIN | DIRECTION | CONF={.}% ...
2. COIN | DIRECTION | CONF={.}% ...
```
with:
```
1. COIN_SYM | DIRECTION | CONF={.}% ...
2. COIN_SYM | DIRECTION | CONF={.}% ...
```

In the schema field descriptions (lines ~109 and ~113):
- Line 109: Change `` Use `{coin} — {reason}` `` → `` Use `{COIN_SYM} — {reason}` ``
- Line 113: Change `- 'COIN' — coin symbol (e.g. HYPE)` → `- 'COIN_SYM' — coin symbol (e.g. HYPE)`

In the survivor detail template (line 40):
```
For each: COIN | DIRECTION | conf={.}% ...
```
→ ```
For each: COIN_SYM | DIRECTION | conf={.}% ...
```

In the new signals detail template (line 72):
```
For each: COIN | DIRECTION | conf={.}% ...
```
→ ```
For each: COIN_SYM | DIRECTION | conf={.}% ...
```

### Step 2: Fix `ai_decider.py` Line 1560 — Remove `token == 'COIN'`

File: `/root/.hermes/scripts/ai_decider.py`, line 1560

```python
# Before:
if token == '***' or token == 'COIN' or (token not in valid_tokens and token not in _hot_tokens_set):

# After:
if token == '***' or (token not in valid_tokens and token not in _hot_tokens_set):
```

Keep the `***` safety net. Keep the invalid-token check. Remove `COIN` since `COIN_SYM` in the prompt prevents it.

### Step 3: Fix Survivor Context — Add `regime` to Survivor Detail String

File: `/root/.hermes/scripts/ai_decider.py`, lines ~1313-1331

Add `regime={reg_tag}` to the survivor detail string so the LLM can penalize counter-regime survivors:

```python
# Around line 1326 — change:
_reg_tag = f"{_reg[:2].upper()}({_reg_conf:.0f}%)" if _reg != 'NEUTRAL' else 'N'
_survivor_detail_str += (
    f"{s['token']} | {s['direction']} | conf={conf:.0f}% | "
    f"regime={_reg_tag} | "   # ADD THIS LINE
    f"rounds={rounds} | src={src} | z={z} | WAVE={wave} | "
    f"MOM={mom:.0f} | SPD={spd:.0f} | OVEREXT={overext} | "
    f"age={age_h:.1f}h\n"
)
```

### Step 4: Add Step 7b — Sync `survival_round → hot_cycle_count` in DB After hotset.json Write

File: `/root/.hermes/scripts/ai_decider.py`, after line ~1745 (after `hotset.json` write + `conn.commit()`)

```python
# STEP 7b: Sync survival_round → hot_cycle_count in DB
# Tokens that survived N rounds in the LLM's compaction need their DB record
# updated to reflect that survival count. This fires regardless of signal age
# (bypasses 10-min constraint) because we trust the LLM's computation.
for entry in hotset_entries:
    c.execute("""
        UPDATE signals
        SET hot_cycle_count = ?
        WHERE token = ? AND direction = ?
          AND hot_cycle_count < ?
    """, (entry['survival_round'], entry['token'], entry['direction'].upper(),
          entry['survival_round']))
conn.commit()
print(f"  [LLM-compaction] Synced survival_round -> hot_cycle_count for {len(hotset_entries)} tokens")
```

### Step 5: Also Sync `regime` for Carried Survivors in hotset.json Write

File: `/root/.hermes/scripts/ai_decider.py`, in the hotset_entries building loop (around line 1680)

For tokens coming from `prev_hotset` (carried survivors, not newly ranked), look up their regime and include it in the JSON:

```python
# Around line 1680, in the hotset_entries building loop:
# For carried survivors (from prev_hotset not in parsed), look up regime
_key = f"{s['token']}:{s['direction']}"
if _key in prev_hotset:
    _existing = prev_hotset[_key]
    # If regime is missing or stale ('N'), look it up
    if not _existing.get('regime') or _existing.get('regime') == 'N':
        _reg, _reg_conf = get_regime(s['token'].upper())
        _existing['regime'] = _reg
        _existing['regime_conf'] = _reg_conf
```

---

## Files to Change

| File | Change | Lines |
|------|--------|-------|
| `main-prompt.md` | Replace `COIN` → `COIN_SYM` in output schema examples | 40, 72, 104, 105, 109, 113 |
| `ai_decider.py` | Remove `token == 'COIN' or` from hallucination guard | ~1560 |
| `ai_decider.py` | Add `regime={reg_tag}` to survivor detail string | ~1326-1330 |
| `ai_decider.py` | Add Step 7b: sync `survival_round → hot_cycle_count` after hotset.json write | ~1745+ |
| `ai_decider.py` | Sync regime for carried survivors in hotset.json write | ~1680 |

---

## Validation Plan

After applying all changes, run ai_decider and check:

1. **`/tmp/llm_compaction_content.txt`** — Search for literal `COIN` as a token. Should find 0 occurrences. `COIN_SYM` should appear in the output schema examples in the prompt section (the `---` wrapped content the LLM sees).

2. **DB `hot_cycle_count` for a known survivor** — Before running, note SOL's `hot_cycle_count`. After running, query again — should equal SOL's `survival_round` in `hotset.json`.

3. **Survivor lines in prompt** — In `/tmp/llm_compaction_content.txt` or via debug print at line 1436, survivor lines should include `regime=LO(..%)` or `regime=SH(..%)` not just `regime=N`.

4. **`hotset.json`** — All 20 entries should have `regime` and `regime_conf` fields (not null/empty).

5. **No dropped slots from `COIN` guard** — Log should show 0 "Recovered token" messages.

---

## Risks and Tradeoffs

1. **COIN → COIN_SYM change**: Small risk that the LLM still outputs the literal `COIN_SYM` if confused. If that happens, add `COIN_SYM` to the hallucination guard alongside `***`. But `COIN_SYM` is more obviously a placeholder than `COIN`, so this is unlikely.

2. **`hot_cycle_count` sync**: Using `hot_cycle_count < survival_round` is safe — it never decreases an existing value. However, a token that was manually approved by T (not through ai_decider) would have its `hot_cycle_count` overwritten if the LLM ranked it with a higher survival_round. This is acceptable since the LLM is the authoritative compactor.

3. **`regime` sync for carried survivors**: Calling `get_regime()` for each carried survivor on every compaction adds latency. With `LIMIT 30` survivors and local regime cache, this is negligible.

4. **Breaking the 10-min APPROVED flow**: The Step 7b sync doesn't replace the APPROVED UPDATE — it complements it. The APPROVED UPDATE still fires for 10-min-window signals. The sync ensures that even if APPROVED misses (due to 10-min constraint), the survival_round is still recorded.
