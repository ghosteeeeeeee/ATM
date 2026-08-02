#!/usr/bin/env python3
"""Apply all hot-set quality fixes to ai_decider.py cleanly."""
import re

path = '/root/.hermes/scripts/ai_decider.py'
prompt_path = '/root/.hermes/prompt/main-prompt.md'

with open(path, 'r') as f:
    content = f.read()

# ── CHANGE 1: Double budget ───────────────────────────────────────────────────
content = content.replace("_DAILY_PROMPT_BUDGET=2400000", "_DAILY_PROMPT_BUDGET=4800000")
print("✓ Budget doubled to 4.8M")

# ── CHANGE 2: Remove COIN from hallucination guard ───────────────────────────
content = content.replace(
    "if token == '***' or token == 'COIN' or (token not in valid_tokens",
    "if token == '***' or (token not in valid_tokens"
)
print("✓ COIN removed from hallucination guard")

# ── CHANGE 3: Fix budget guard to fall through instead of returning ────────────
# Original:
#     if not _check_token_budget(4000):
#         print("...skipping")
#         conn.close()
#         return
#     else:
#         from openai import OpenAI
#         ...
#         parsed = _parse_llm_output(...)
#
# We want:
#     if not _check_token_budget(4000):
#         print("...skipping LLM call, falling through")
#         parsed = []
#         raw = ""
#     else:
#         from openai import OpenAI
#         ...

old_budget_guard = """        if not _check_token_budget(4000):
            print("[LLM-compaction] Token budget exceeded — skipping")
            conn.close()
            return

        from openai import OpenAI"""

new_budget_guard = """        if not _check_token_budget(4000):
            print("[LLM-compaction] Token budget exceeded — skipping LLM call, falling through to preservation")
            parsed = []
            raw = ""
        else:
            from openai import OpenAI"""

if old_budget_guard in content:
    content = content.replace(old_budget_guard, new_budget_guard)
    print("✓ Budget guard fixed to fall through")
else:
    print("✗ Budget guard pattern not found")

# ── CHANGE 4: COIN → COIN_SYM in main-prompt.md ─────────────────────────────
with open(prompt_path, 'r') as f:
    prompt = f.read()

# Replace COIN | DIRECTION (placeholder pattern) with COIN_SYM | DIRECTION
prompt = prompt.replace('COIN | DIRECTION', 'COIN_SYM | DIRECTION')

with open(prompt_path, 'w') as f:
    f.write(prompt)
print(f"✓ Prompt updated — COIN_SYM count: {prompt.count('COIN_SYM')}")

# ── CHANGE 5: Add regime= to survivor detail string ───────────────────────────
old_survivor = (
    'f"rounds={rounds} | src={src} | z={z} | WAVE={wave} | "\n'
    '                f"MOM={mom:.0f} | SPD={spd:.0f} | OVEREXT={overext} | "\n'
    '                f"age={age_h:.1f}h\\n"\n'
)
new_survivor = (
    'f"regime={_s_reg_tag} | rounds={rounds} | src={src} | z={z} | WAVE={wave} | "\n'
    '                f"MOM={mom:.0f} | SPD={spd:.0f} | OVEREXT={overext} | "\n'
    '                f"age={age_h:.1f}h\\n"\n'
)
if old_survivor in content:
    content = content.replace(old_survivor, new_survivor)
    print("✓ Regime added to survivor detail string")
else:
    print("✗ Survivor detail pattern not found")

# ── CHANGE 6: Add Step 7b sync after hotset.json write ───────────────────────
old_sync_marker = '    print(f"  [LLM-compaction] Wrote hotset.json with {len(hotset_final)} tokens (cycle={_compaction_cycle})")\n\n    # Update pipeline heartbeat'
new_sync_block = """    print(f"  [LLM-compaction] Wrote hotset.json with {len(hotset_final)} tokens (cycle={_compaction_cycle})")

    # STEP 7b: Sync survival_round → hot_cycle_count in DB (2026-04-16)
    # Tokens that survived N rounds need their DB record to reflect hot_cycle_count=N
    # even if their last PENDING signal was >10 min ago. This bypasses the 10-min
    # signal freshness constraint — we trust the LLM's computation.
    try:
        import sqlite3 as _sqlite3
        _db_path = '/root/.hermes/data/signals_hermes_runtime.db'
        _sync_conn = _sqlite3.connect(_db_path, timeout=10)
        _sync_c = _sync_conn.cursor()
        _sync_count = 0
        for _entry in hotset_final:
            _sync_c.execute(
                "UPDATE signals SET hot_cycle_count = ? WHERE token = ? AND direction = ? AND hot_cycle_count < ?",
                (_entry['survival_round'], _entry['token'], _entry['direction'].upper(), _entry['survival_round'])
            )
            _sync_count += _sync_c.rowcount
        _sync_conn.commit()
        _sync_conn.close()
        print(f"  [LLM-compaction] Synced survival_round -> hot_cycle_count for {len(hotset_final)} tokens ({_sync_count} rows)")
    except Exception as _e:
        print(f"  [LLM-compaction] DB sync failed: {_e}")

    # Update pipeline heartbeat"""

if old_sync_marker in content:
    content = content.replace(old_sync_marker, new_sync_block)
    print("✓ Step 7b sync added")
else:
    print("✗ Sync marker not found")

# ── CHANGE 7: Add placeholder filter to preservation path ─────────────────────
old_pres_filter = """                    if _src and _src.split(',')[0] == 'hzscore' and ',' not in _src:
                        print(f"  🚫 [HOTSET-FILTER] {_tok}: blocked — bare hzscore (combo-only)")
                        continue
                    # FIX (2026-04-12): Update timestamp"""
new_pres_filter = """                    if _src and _src.split(',')[0] == 'hzscore' and ',' not in _src:
                        print(f"  🚫 [HOTSET-FILTER] {_tok}: blocked — bare hzscore (combo-only)")
                        continue
                    if _tok in ('***', 'COIN_SYM', 'COIN') or not _tok.isalpha():
                        print(f"  🚫 [HOTSET-FILTER] {_tok}: blocked — placeholder/hallucination token")
                        continue
                    # FIX (2026-04-12): Update timestamp"""
if old_pres_filter in content:
    content = content.replace(old_pres_filter, new_pres_filter)
    print("✓ Preservation path placeholder filter added")
else:
    print("✗ Preservation filter pattern not found")

# ── CHANGE 8: Add placeholder filter to normal hotset write loop ──────────────
old_norm_filter = """        if is_delisted(tkn):
            print(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — delisted")
            continue
        spd = _speed_cache.get(tkn, {})"""
new_norm_filter = """        if is_delisted(tkn):
            print(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — delisted")
            continue
        if tkn in ('***', 'COIN_SYM', 'COIN') or not tkn.isalpha():
            print(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — placeholder/hallucination token")
            continue
        spd = _speed_cache.get(tkn, {})"""
if old_norm_filter in content:
    content = content.replace(old_norm_filter, new_norm_filter)
    print("✓ Normal loop placeholder filter added")
else:
    print("✗ Normal loop filter pattern not found")

# ── Write ─────────────────────────────────────────────────────────────────────
with open(path, 'w') as f:
    f.write(content)

# ── Syntax check ───────────────────────────────────────────────────────────────
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("\n✓ Syntax OK")
except py_compile.PyCompileError as e:
    print(f"\n✗ Syntax ERROR: {e}")
