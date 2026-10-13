# Bug-Hunter Verification v2 — `automatic-implementation` Skill (Updated)

**Verifier:** bug_hunter subagent
**Date:** 2026-10-13 03:30–03:35 UTC
**Target:** `/root/.config/opencode/skills/automatic-implementation/SKILL.md` (511 lines)
**Context:** Second verification pass after 5 agent-feedback items were incorporated. First pass (`automatic_implementation_skill_verify.md`) found the "Sep 23 / 3 weeks shadow" factual error — that fix is confirmed.

---

## Verdict: **PASS with 2 findings** (1 skill bug to fix, 1 production gap the skill exposes)

All 5 feedback items are present and accurate. The Phase 2 quickstart skeleton **actually runs** against the live environment — it parsed 2 real `SHADOW BLOCK` lines out of the production `pipeline.log` on first try. Systemd templates validate clean. Symlink exists. The old Sep 23 error is fixed. One small pseudo-code snippet in Phase 1 has a syntax error and an inverted-logic typo (Finding 1). Separately, the skill loudly teaches a log-rotation fix citing `gate_shadow.py` being dead for 2 days — but the real `gate_shadow.py` **still doesn't have that fix** (Finding 2).

---

## Check Results

### ✅ Check 1: Symlink exists — **PASS**
```
lrwxrwxrwx 1 root root 54 Oct 13 03:30 /root/.hermes/skills/shared/automatic-implementation
    -> /root/.config/opencode/skills/automatic-implementation
```
Created Oct 13 03:30, resolves to the correct original. Verified readable through the symlink path.

### ⚠️ Check 2: All Python blocks compile — **4 of 5 PASS, Block 0 FAIL**
```
Block 0: SYNTAX ERROR line 6: invalid syntax   (Phase 1 illustrative snippet, 18 lines)
Block 1: OK (219 lines)   ← Phase 2 quickstart skeleton
Block 2: OK (1 line)      ← range_reversion SHADOW_MODE quote
Block 3: OK (1 line)      ← neutral_sniper SHADOW_MODE quote
Block 4: OK (2 lines)     ← RR engine flags quote
```
Block 0 is the small Phase 1 gate snippet. Two defects (detailed in Finding 1): invalid `...` parameter, and `if not not result['pass']:` which inverts the gate. It's framed as illustrative pseudo-code and the *quickstart* (the actual copy-paste artifact) is clean — but agents copy snippets. **See Finding 1.**

### ✅ Check 3: Phase 2 quickstart skeleton actually runs — **PASS** (strongest result)
Extracted the 219-line skeleton, placed it in `/root/.hermes/scripts/` (so its `from paths import HERMES_DATA, HERMES_LOG_DIR` resolves), ran every mode:
```
--report  → [my_gate_shadow] ─── SHADOW REPORT ─── / blocks=0 ... / no would-be trades yet   [exit 0]
--record  → [my_gate_shadow] record: +2 events, total=2, offset=50948962                    [exit 0]
--record  → [my_gate_shadow] record: +0 events, total=2, offset=50961191   (dedup WORKS)    [exit 0]
--close   → [my_gate_shadow] close: 0 pending events                                         [exit 0]
```
Key evidence:
- The skeleton's `BLOCK_RE` regex matched **2 real production log lines** from `pipeline.log` (`[rr-engine] SHADOW BLOCK NEAR LONG $5.3110: R:R 0.74 < 2.0 minimum for EXTREME regime`) with zero adjustment — the "test against real log lines before deploying" instruction pays off.
- Offset persisted to `/root/.hermes/data/my_gate_shadow_offset.txt`, re-record correctly resumed (`+0`), dedup bucket logic verified (`strftime('%Y%m%d%H%M')[:-1]` = 10-min bucket).
- DB created at `brain/my_gate_shadow.db` — matches the skeleton's documented location and the convention used by all 3 real trackers (`gate_shadow.py`, `expiry_shadow.py`, `t5_shadow.py` all use `os.path.join(os.path.dirname(HERMES_DATA), 'brain', ...)`).
- `paths.py` exports confirmed: `HERMES_DATA=/root/.hermes/data`, `HERMES_LOG_DIR=/root/.hermes/logs`.
- Test-artifact note: the task's `exec(open(...))` import test fails with `NameError: __file__` — that's a harness artifact of `exec()` (no `__file__` in exec scope), **not** a skill bug. Running as a real file works.
- All test artifacts cleaned up (`brain/my_gate_shadow.db`, offset file, temp script removed).

### ✅ Check 4: Systemd templates valid — **PASS**
`systemd-analyze verify` on both skill templates (written verbatim to temp files):
```
hermes-my-gate-shadow.timer   → exit 0 (valid)
hermes-my-gate-shadow.service → exit 0 (valid; only warning was from an unrelated pre-existing unit)
```
- `OnCalendar=*:00/30` is valid systemd calendar syntax.
- Structure matches the working production units it's modeled on: `hermes-gate-shadow.service/.timer`, `hermes-expiry-shadow.service/.timer`, `hermes-t5-shadow.service/.timer` all exist and are installed. Production `hermes-gate-shadow.service` adds `EnvironmentFile`, `StandardOutput=journal`, `TimeoutStartSec=300` — optional hardening, not required for validity. Template is safe to copy.

### ✅ Check 5: Constants path — **PASS**
Skill references `scripts/hermes_constants.py` (3 places). File exists at `/root/.hermes/scripts/hermes_constants.py`. Line 2 carries the `# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!` warning — skill's Phase 6 correctly frames the flip as a single-flag change requiring CEO sign-off, consistent with the protected-flag convention.

### ✅ Check 6: CEO override section — **PASS**
- `automation/ceo/ceo_report.md` exists (the documented destination for decisions).
- `automation/ceo/checkpoints/` exists; latest checkpoint (`20261013T000026Z-decision.md`) has exactly the sections the Multi-Session Handoff section claims: `## Decision`, `## Evidence`, `## Plan`, `## Files-to-touch`, `## Rollback` — matches the skill's claim verbatim.
- `ceo-comm` skill exists at `/root/.config/opencode/skills/ceo-comm/`; `bug-hunter` exists too (Phase 6's mandatory step).
- Override language is consistent with how CEO decisions actually work: shadow data is input, CEO has final authority, override reasoning documented in the decision. This mirrors the real pattern (e.g., RR conf enforcement was reactive/domain-driven, not pure data-driven).

### ✅ Check 7: Real Examples verified against git + code — **PASS**
| Skill claim | Verified | Evidence |
|---|---|---|
| range_reversion `SHADOW_MODE = False  # CEO 2026-09-01 — ...288 signals/24h across 20 tokens` | ✅ | `range_reversion.py:59` exact match; git `555bf091` "CEO: range_reversion SHADOW→LIVE (288 signals/24h validated)" 2026-09-01 |
| neutral_sniper flipped Sep 6, 3756 shadow signals in 11h | ✅ | `neutral_sniper.py:70` exact match; git `72a4cb5a` 2026-09-06 |
| `RR_ENGINE_SHADOW = True` (still shadow) | ✅ | `hermes_constants.py:3848` — still `True` today |
| `RR_ENGINE_CONF_SHADOW = False` (enforced, flipped **Sep 4** — was Sep 23 in v1) | ✅ | `hermes_constants.py:3901` — **old factual error confirmed fixed**; no "Sep 23"/"3 weeks" strings remain in the skill |
| Trade-learning P0-P4 trackers standalone, own DBs, systemd timers | ✅ | All 3 scripts + all 3 service/timer pairs exist; DBs in `brain/*.shadow.db` per grep |
| Decision rules (WR≥55 + positive PnL, n≥15 → PROPOSE RELAX) | ✅ | Matches both skeleton `report()` and production `gate_shadow.py:244` (`wr >= 55 and pnl > 0`), consistent with Oct 10 commit `6f218c3e` "relax proposals now require positive PnL" |
| `python3 -c "import scripts.<module>"` handoff check | ✅ | `import scripts.gate_shadow` → OK from `/root/.hermes` (namespace package, no `__init__.py` needed) |
| "12+ bugs over Oct, 3 rounds of bug fixes" | ~ Plausible | Multiple bug-hunter commits Oct 4 (`f3fd0021`, `0e1459c0`, `1b177e9c`) — consistent, exact count not independently tallied |

### ✅ Check 8: New feedback sections present — **PASS**
| Feedback item | Present? | Where |
|---|---|---|
| 1. Chicken-and-egg clarified | ✅ | "How Shadow Mode Actually Works" + ASCII diagram (lines 19–43) — diagram accurately shows filter→log→tracker→24h close, and correctly states the filter improving signals IS the desired effect |
| 2. Multi-session handoff | ✅ | Lines 431–446 — all 5 checkpoint/verify steps verified against real layout |
| 3. Systemd templates | ✅ | Lines 318–352 — validate clean (Check 4) |
| 4. CEO override | ✅ | Phase 5, line 402 + template field line 409 — consistent with real CEO process (Check 6) |
| 5. Phase 2 quickstart | ✅ | Lines 92–312 — runs against production (Check 3) |

---

## Findings

### 🐞 Finding 1 — Phase 1 snippet: syntax error + inverted gate logic — **MEDIUM**
**File:** SKILL.md, Phase 1 illustrative snippet (python Block 0, ~line 57–68)

Two defects in one snippet:
```python
def my_gate(token, direction, ...):        # ← `...` is not a valid parameter — doesn't compile
    ...
    if not not result['pass']:             # ← double negation: means `if result['pass']:`
        _log(f"BLOCK {token} ...")
        return False                       # ← BLOCKS the trade when the gate PASSED
    return True                            # ← a failing result falls through and PASSES
```
`not not result['pass']` is valid syntax but inverted logic: a trade that **passes** the gate gets logged as BLOCK and blocked; a trade that **fails** falls to `return True` and passes. The intent was clearly `if not result['pass']:`. Combined with the `...` parameter this block fails `compile()`.

**Impact:** It's labeled illustrative and the real copy-paste artifact (Phase 2 quickstart) is correct — but this skill's whole audience is agents that copy snippets. An agent replicating Phase 1's structure ships a gate that does the exact opposite of its name, on live trading.

**Fix:** Replace `...` with real params (e.g., `def my_gate(token, direction, ctx=None):`) and `if not not result['pass']:` with `if not result['pass']:`. Then the block compiles and the logic is: shadow → log + pass; enforcement → block on fail; pass → `return True`.

### ⚠️ Finding 2 (sideways find, production code) — Real shadow trackers still lack the log-rotation check the skill calls CRITICAL — **MEDIUM**
The skill's quickstart says: *"CRITICAL: gate_shadow.py was silently dead for 2 days after log rotation because it didn't check file size before seeking"* — and anti-pattern #7 repeats it. The skeleton implements it correctly (`if offset > file_size: offset = 0`). **But none of the three production trackers have this check:**
```
grep "offset > \|rotation" gate_shadow.py expiry_shadow.py t5_shadow.py → no matches
```
`gate_shadow.py:107` does a bare `f.seek(offset)` with no size comparison — after the next `pipeline.log` rotation, it will silently read nothing, exactly the failure mode the skill warns about. The skill is teaching a fix the codebase hasn't applied.

**Suggested fix:** patch the 3 production trackers with the skeleton's rotation check (small diff: get size via `f.seek(0,2)`, compare to offset, reset to 0 + trailing-20MB seek if offset > size). This is a bug-fix-rule obvious fix — worth doing without waiting for approval.

**Unverified historical claim:** "dead for 2 days" — plausible (rotation on 50MB-ish logs, offset persisted) but I could not confirm the specific incident from git; treated as narrative, not a factual claim that affects the pattern.

---

## Summary Table

| # | Check | Result |
|---|-------|--------|
| 1 | Symlink exists | ✅ PASS |
| 2 | Python blocks compile | ⚠️ 4/5 — Block 0 fails (Finding 1) |
| 3 | Quickstart runs (record/dedup/close/report) | ✅ PASS — matched 2 real production log lines |
| 4 | Systemd templates valid | ✅ PASS (`systemd-analyze verify` clean) |
| 5 | hermes_constants path | ✅ PASS |
| 6 | CEO override section | ✅ PASS |
| 7 | Real Examples dates/constants | ✅ PASS — Sep 23 error confirmed fixed, Sep 4 correct |
| 8 | 5 feedback items incorporated | ✅ PASS |
| F1 | Phase 1 snippet bug | 🐞 MEDIUM — fix `...` param + `not not` inversion |
| F2 | Production trackers lack rotation check | ⚠️ MEDIUM sideways find — patch 3 scripts |

**Bottom line:** The updated skill is accurate and the quickstart is genuinely executable — verified against live production data, not just read. Ship it after the one-line Phase 1 snippet fix (Finding 1). Finding 2 is a production-code gap, not a skill defect, but the skill itself makes the case for fixing it immediately.

**Test artifacts cleaned:** `brain/my_gate_shadow.db`, `data/my_gate_shadow_offset.txt`, `/root/.hermes/scripts/_verify_quickstart_tmp.py`, `/tmp/test_quickstart.py`, `/tmp/sdcheck/` all removed. Production systems untouched.
