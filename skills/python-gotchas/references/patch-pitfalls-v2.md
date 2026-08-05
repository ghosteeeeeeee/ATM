# Patch File Pitfalls — Additional Bugs

Two more bugs to add to the patch pitfalls reference.

---

## Pitfall 5: `write_file()` Destroys Existing Files

**Problem**: `write_file()` overwrites the ENTIRE file with new content. It is NOT a safe append/inject operation.

**Broken workflow**:
```
skill_view(name='some-skill')
# user asks to "add run() wrapper to signals/ma300_candle_confirm.py"
write_file(file_content="""  # overwrites entire file with wrapper only
def run(prices_dict=None):
    from ma300_candle_confirm_signals import scan_ma300_candle_signals
    ...
""", file_path='signals/ma300_candle_confirm.py')
# Result: 269-line original file replaced with 10-line wrapper
# scan_ma300_candle_signals, detect_ma300_candle, EMA calcs, _get_candles_1m — ALL GONE
```

**Effect**: Signal module becomes completely broken. `run()` raises `NameError` because the function it calls no longer exists.

**Rule**: NEVER use `write_file()` on an existing file. Use `patch()` for any in-file edit. `write_file()` is only safe when creating a NEW empty file from scratch.

**Safe alternative for adding run() wrappers**:
```python
# Use patch() with old_string / new_string instead
skill_manage(action='patch', name='module-name',
    old_string="""if __name__ == '__main__':
    result = scan_xxx_signals(get_all_latest_prices())
    print(f"Signals: {result}")""",
    new_string="""def run(prices_dict=None):
    if prices_dict is None:
        from signals_helpers import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_xxx_signals(prices_dict)

if __name__ == '__main__':
    result = run()
    print(f"{result}")""")
```

---

## Pitfall 6: `global VAR` Before First Assignment = SyntaxError

**Problem**: Python resolves `global` declarations at compile time, not at runtime. The FIRST assignment to a name in the function scope determines whether `global` is valid. If `global FOO` appears but `FOO = ...` appears first (lexically later in the function), Python raises `SyntaxError`.

**Broken code**:
```python
def main(args):
    global DRY_RUN          # ← declared here, valid
    # ... later in same function ...
    DRY_RUN = args.dry      # ← FIRST assignment to DRY_RUN in this function
    # Python resolves names at compile time:
    # "DRY_RUN is assigned to before global declaration"
```

**Why Python treats this as an error**: At compile time, Python scans the function body and sees `global DRY_RUN` followed by an assignment `DRY_RUN = args.dry`. The `global` declaration says "DRY_RUN refers to the global variable", but the assignment would create a local variable — these are contradictory. Python detects this at compile time rather than letting it fail at runtime.

**Fix**: Remove `global DRY_RUN` if the variable is already module-level (no local assignment needed). If you must write to a global from within a function, the `global` declaration must appear BEFORE any assignment to that name in the function.

**Also applies to**: Any variable name that appears both in a `global` declaration and gets assigned later in the same function body.

**Verification**:
```bash
python3 -m py_compile /path/to/file.py
# If you see "SyntaxError: name 'X' is assigned to before global declaration"
# → find the function with both "global X" and "X = ..." and remove the global line
```

---

## Signal Module Import Path Reference

When adding `run()` wrappers to signal modules, the import path depends on where the `scan_*` function lives:

| Scan function location | Import in run() wrapper |
|---|---|
| `signals/` subdirectory | `from signals.module_name import scan_xxx` |
| Parent `/root/.hermes/scripts/` | `from module_name import scan_xxx` (no `signals.` prefix) |
| Dual-path (wrapper + parent scanner) | Use parent dir import |

**Current dual-path modules** (scan function in parent, wrapper in signals/):
- `ma300_candle_confirm` → `from ma300_candle_confirm_signals import scan_ma300_candle_signals`

**Audit command after any patch**:
```bash
cd /root/.hermes/scripts
python3 -c "
import sys; sys.path.insert(0,'.')
for mod_name in ['ma_cross', 'atr_compression', 'hh_hl', 'macd_accel', 'ema9_sma20',
    'ma300_candle_confirm', 'r2_trend', 'r2_rev', 'gap_300', 'macd_1m',
    'ema20_50', 'exhaustion', 'guppy', 'volume_hl', 'trend_purity']:
    try:
        mod = __import__(f'signals.{mod_name}', fromlist=['run'])
        r = mod.run(None)
        print(f'OK   {mod_name:22s} → {type(r).__name__}')
    except Exception as e:
        print(f'FAIL {mod_name:22s} → {e}')
"
```