# Hermes Signal Debugging — Reference Archive

Session-specific debug transcripts and troubleshooting records. Each entry captures a specific bug or investigation path for future reference.

---

## 2026-05-16: ZK SHORT approved without support/resistance signal

**Symptom:** ZK SHORT appeared in approved with confidence 79.4%, sources `ema-angle-,zscore-pump-`.

**Investigation:**
- Checked signals.json for ZK entries with `decision` field
- Found ZK SHORT at signals.json line 1836: `decision: "SKIPPED"` — not APPROVED
- Confirmed ZK SHORT with `rs-r54` IS present in source: `src=ema-angle-,rs-r54,zscore-pump-`
- Signal compactor enforces rs requirement at line ~864:
  ```python
  has_rs = any(p.startswith('rs') for p in source_parts)
  if not has_rs:
      log(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — requires rs-s# or rs-r#")
  ```
- ZK PASSED because rs-r54 was present; zscore-pump- is valid directional co-signal

**Pattern:** A combo like `zscore-pump-,ema-angle-` (no rs) would be BLOCKED. The `rs` signal is a hard requirement in signal_compactor's hot-set filter.

---

## 2026-05-15: accel-300 SHORT completely blocked — gap comparison bug

**Symptom:** accel-300- never fired despite positive gap values.

**Root cause:** accel_300.py line 222:
```python
if gap_now < MIN_GAP_PCT:  # was: gap_now < MIN_GAP_PCT (negative for SHORT always fails)
```
Fix: `abs(gap_now) < MIN_GAP_PCT` — both LONG and SHORT compare absolute gap to threshold.

**Secondary bug in rs.py:** add_signal missing source/confidence args (lines 667-671). Both confirmed applied.

---

## 2026-05-15: All 5 fast signals silently failing — `_run_signal` hardcoded 'run'

**Symptom:** ema_angle, rs, volume_hl, atr_compression, zscore_pump all returning 0 signals.

**Root cause in signals/__init__.py `run_all_signals`:**
```python
# BEFORE (broken): name_to_module stored module names, _run_signal looked for 'run'
work = [(signal['name'], name_to_module.get(signal['name']))]
# _run_signal did: getattr(mod, 'run', None) — only finds signals with function literally named 'run'

# AFTER (fixed): store actual function names, pass them through
work = [(signal['name'], signal['run'].__name__)]  # actual fn name
# _run_signal now: getattr(mod, fn_name, None)  # uses correct function
```

**All 5 fast signals use non-standard function names:**
- zscore_pump → `scan_zscore_pump_signals`
- accel_300 → `scan_accel_300_signals`
- ema_angle → `scan_ema_angle_signals`
- rs → `scan_rs_signals`
- volume_hl → `main`

**Also fixed:** `__import__(f'signals.{sig_name}', fromlist=[fn_name])` — was passing module name instead of fn_name.

---

## 2026-05-12: post-reboot zscore-pump not firing — ZSCORE_PUMP_ENABLED=False

**Symptom:** zscore_pump signal absent from pipeline output after server reboot.

**Root cause:** `ZSCORE_PUMP_ENABLED = False` in hermes_constants.py (line 565). Kill-switch was False (correct default), but was set to False during previous session and persisted.

**Fix:** Changed to `True`. Per-direction flags were already True: `ZSCORE_PUMP_PLUS_ENABLED=True`, `ZSCORE_PUMP_MINUS_ENABLED=True`.

---

## 2026-04-22: CASCADE_FLIP_ENABLED=False — cascade flip disabled

**Decision:** Cascade flip causes re-entry issues. Disabled via hermes_constants. Re-enabling requires explicit T approval.

---

## 2026-04-13: pipeline.log binary false positive

**Symptom:** `grep: binary file matches` on pipeline.log.

**Root cause:** Log timestamps (`[2026-04-03 05:59:06]`) contain whitespace that confuses grep into binary detection. File is plain text.

**Note:** run_bg() pipes subprocess stdout to same file parent process writes — causes double entries. This is the expected behavior, not corruption.