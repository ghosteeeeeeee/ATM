## CEO Decision — 2026-10-12 — ceo-comm rework (design-only, no implementation)

### Decisions (lead)
1. **Root cause CONFIRMED** = unbounded scope + all-or-nothing kill. Not a model/provider speed problem. Evidence: `run_ceo.sh:37` is a single `timeout 600 bash -c "cat ceo_prompt.md | opencode run"` — SIGTERM kills the process, zero partial output captured. `ceo_prompt.md` (394 lines) mandates Steps 0–5 as "ACTIVE — every run" (live SQL verification, tune a signal, develop a signal, develop coin_tracker) plus a Monday 6-subagent MoE panel. That cannot fit in 600s. Secondary finding: the script's own comment says "Timeout: 5 minutes (300s)" but the actual timeout is 600 — stale comment, fix on implement.
2. **Compaction-safe design APPROVED with 3 amendments** (full detail below). Your instinct that `-c` resume of a compacted giant session is BAD is correct — auto-compact keeps only ~15k recent tokens and prunes tool outputs; resumed impl sessions would edit files on a summary, not on evidence. Do not use `-c`/`-s` across runs for implementation at all.
3. **Step 0–5 on every run: NO — trim and split.** Concrete split below. The "develop new signal / coin_tracker every run" language is the primary budget blowout and moves to weekly.

### The design I approve
| Piece | Verdict | Amendment |
|-------|---------|-----------|
| (a) Status-report = one read-only bounded session | ✅ | One SQL batch (24h + 7d + per-signal), not Step 2's full interrogation. Budget ~3 min. |
| (b) Decision/impl = fresh single-goal subagent sessions | ✅ | Same pattern that made bug_hunter succeed. One goal per session, parent never edits files itself. |
| (c) Checkpoint-to-disk BEFORE any edits | ✅ | Parent writes `automation/ceo/checkpoints/<ts>-decision.md` (decision + evidence + plan + files-to-touch) BEFORE dispatching. Each subagent appends `<ts>-result-<n>.md`. Even a hard kill leaves the decision and partial results on disk; next run assembles the report from checkpoints. |
| (d) auto-compact OFF on impl sessions | ✅ | Silent mid-edit summarization is strictly worse than a loud overflow failure. Config per-session or via agent config. |
| (e) Detach + JSON stream | ✅ | `nohup`/`systemd-run` + `--format json >> logs/ceo/<ts>.jsonl` + capture exit code to a `.exit` file. Timeout becomes a signal to inspect, not a data-loss event. |

**Amendments / risks you missed:**
1. **Lock is read-only today.** `run_ceo.sh` checks `/tmp/hermes-session-active.lock` but never CREATES it. A detached impl session that edits `hermes_constants.py` while a human session is live would collide. Fix: the detached impl run must acquire the lock before its first edit and release on exit (flock or timestamp file). Status sessions don't need it.
2. **Concurrent-writer hazard.** Multiple detached sessions (status + N subagents) all potentially touching `ceo_kanban.md` / `ceo_report.md`. Rule: subagents write ONLY their own checkpoint files; a single aggregator (parent or next run) is the sole writer of kanban/report. Use `flock` on that writer.
3. **Port collision.** Current script pins `--port 4099`. Two detached sessions = conflict. Use a random/ephemeral port for detached runs, or one port per session type.
4. **MoE panel must leave the normal run entirely.** Separate script (`run_ceo_moe.sh`), own budget (detached, ~30 min), Monday only. Never in the same process as a normal run.
5. **`-c`/`-s` usage policy:** status session may use `-s` within its own short life if it needs a second turn; NEVER resume a prior run's session for implementation. Fresh session every time.

### Concrete run-split (recommendation for Step 0–5)
| Run type | Frequency | Scope | Budget |
|----------|-----------|-------|--------|
| **Status run** | every scheduled tick | CURRENT.md + team updates + ONE SQL batch (24h totals, 7d totals, per-signal 7d) + ONE rotating proactive question + write report. Read-only. | ~3 min, in-process OK |
| **Deep run** | weekly (or when status run flags a problem) | Regime-aware analysis (Step 2b), ONE signal tune, ONE signal-development task — each dispatched as a fresh subagent session with a checkpoint file. | detached, per-task budget |
| **MoE panel** | Monday only, separate script | 6 parallel expert subagents, synthesis to `reports/`. | detached, ~30 min |

Rationale: the current prompt conflates "CEO checks the system" (cheap, frequent) with "CEO improves the system" (expensive, rare). Splitting them keeps the frequent path bounded and makes the expensive path survivable. "Develop new signals / coin_tracker every run" becomes "every weekly deep run" — that alone recovers most of the budget.

### What I am NOT approving
- Resuming one giant `-c` session across runs (your analysis is right; rejected).
- Raising the timeout instead of bounding the work (treats the symptom).
- Removing the checkpoint-before-edit rule for any session that touches files.

### Verification plan (when implemented)
1. Run status session 3× back-to-back — must complete <3 min each, produce a report every time.
2. Kill an impl session mid-flight with SIGTERM — checkpoint file + partial subagent results must exist on disk and be assemblable.
3. Confirm auto-compact-off session fails loudly (non-zero exit, error in .jsonl) on a deliberately oversized prompt instead of summarizing.

---

## CEO Report — 2026-10-12

### Diagnosis
Regime-recalibration backtest claimed a profitable SHORT hump at 2.5–4.0% ATR (t=1.92–2.10, LOO-robust, "+$15.71 suppressed"). I re-derived independently (same basis: 5,140 trades, ATR%(14) from 1h candles pre-open — n matches exactly). **The hump does not reproduce at claimed significance.** System: 24h 26T +$1.00 26.9% WR; 7d 145T −$0.10 37.9% (flipped negative).

### Root Cause
Two-part:
1. **Evidence gap (THE PATTERN).** My repro: SHORT 2.5–4.0 n=209 +$1.68 WR 48.8% **t=0.95** (doc: t=1.92). Sub-bin 2.5–3.0 t=1.72 (doc: 2.09). LOO drops **FET** (not XMR) → t=0.49 (doc: 2.10). Doc's LOO n=244 > my full-band n=209 → band membership differs = unreproducible derivation. "+$15.71" is winners-only sum; true unblock counterfactual is **net ≈ +$2** before fees on 209 extra trades.
2. **What DID reproduce:** LONG FLAT edge t=2.65 ✓; LONG decays with ATR ✓; MAXXED (≥4.0) bad BOTH dirs (LONG 44.4% −$1.48; SHORT 24.0% −$1.16) ✓ direction-consistent.

### Decision
1. **MAXXED tier: APPROVED IN PRINCIPLE, shadow-only first.** ≥4.0% is genuinely toxic both directions. Hard constraint: every existing `regime=='EXTREME'` comparison must treat MAXXED as EXTREME-equivalent (naive relabel would accidentally UNBLOCK EXTREME restrictions — blast-radius audit required before any live wiring).
2. **EXTREME-hi SHORT-allow: REJECTED pending reproduction.** The entire economic case (+$15.71) rests on a hump that fails independent verification. No live change to SHORT treatment in 1.5–4.0%.
3. **LONG-restrict EXTREME-hi: NO** — −$2.46/173T t=−1.21, not significant; blanket blocks need more.
4. **Full ladder re-cut: NO** — correctly rejected; per-signal overrides rest on current buckets.

### Verification (pre-code-change, mandatory)
- **own-conclusions: REQUIRED and ordered** — reproduce the SHORT hump with a checked-in, fully scripted derivation; resolve the n=244-vs-209 band mismatch. Pass bar: |t|≥2.0, LOO-robust, net counterfactual (incl. fee drag) > +$5/30d.
- Any future implementation: 48h shadow logging of would-be decisions before enforcement; protected flags untouched; CONFLUENCE_REQUIRED stays True.

### Next
DELEGATE signal_analyst: MAXXED shadow label (observability only, EXTREME-equivalent mapping) + reproduction script. DELEGATE own-conclusions: fresh-eyes repro of the 2.5–3.0 SHORT cell. 7d PnL now −$0.10 — protecting ≥$0 checkpoint.

---

## CEO Acknowledgment — 2026-10-12 02:22 UTC — MAXXED tier DEPLOYED (T-directed)

### Acknowledged
T-directed MAXXED tier is live. Accept the design and the two-pass verification. Commits 2b6c85ca + 1bf84683 pushed.

### Constraint satisfied (structurally)
My hard constraint — naive `regime='MAXXED'` relabel would silently unblock all `== 'EXTREME'` restrictions — is avoided by design, not by audit. `classify_volatility()` unchanged (still returns EXTREME at ATR%>=4.0); MAXXED is an additive block via `is_maxxed()` on `MAXXED_ATR_PCT_THRESH=4.0`. Zero `== 'MAXXED'` comparisons anywhere. MAXXED can only block more, never less. No relabel risk exists.

### Shipped
- `hermes_constants.py`: MAXXED_ATR_PCT_THRESH=4.0, MAXXED_BLOCK_ENABLED=True, MAXXED_REGIME_LOG=True. New constants only; line-2 protection honored.
- `volatility_gate_v2.py`: `is_maxxed()`.
- `signal_compactor.py`: approval-time block, both directions, logs [MAXXED-BLOCK].
- `decider_run.py`: exec-time backstop in `execute_trade()` — BUG-052-safe (return-before-claim).

### Verified
- Static pass: 88 insertions 0 deletions; classify_volatility invariant holds v1+v2; imports complete; conn closed in finally; ATR div-zero guarded.
- Live pass: pipeline restarted 02:09:16 UTC, cycles rc=0, zero tracebacks, 3 tokens MAXXED (S 6.78%, W 5.51%, STRK 5.43%), dry-run of exec backstop fired correctly, GRASS SHORT (ATR 3.82) correctly not blocked. Kill-switch sanity clean.
- Zero [MAXXED-BLOCK] firings since restart is expected — those tokens produced no hotset signals in window. Block is armed and provably functional.

### Decisions on informational findings
1. Fail-open on <15 closed 1h candles (fresh explosive listings): **accept as-is.** Fail-safe by design; no [MAXXED-UNKNOWN] shadow log for now — add if fresh-listing leakage becomes visible.
2. Inlined ATR-14 copy in compactor (drift risk vs `get_atr_pct()`): **defer.** Matches today; cleanup when next touching compactor. Not worth a standalone diff.

### Extensibility
Higher tier later (e.g. APOCALYPSE) = same additive pattern: one `is_*` helper + one additive block; inherits all MAXXED/EXTREME blocks automatically. Threshold is a named constant. T's requirement met.

### No action
Position_manager D3 trail-floor removal + stray HML_TRAIL_MIN_GAP_PCT comment-only edit (value unchanged 0.20) — housekeeping acknowledged, no further action. SHORT EXTREME-hi unblock remains REJECTED pending own-conclusions repro; MAXXED deployment does not change that.
