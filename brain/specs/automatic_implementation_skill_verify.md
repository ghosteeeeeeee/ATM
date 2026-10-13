# Verification: `automatic-implementation` SKILL.md

**Verifier:** bug_hunter
**Date:** 2026-10-12 (run 23:58 UTC – 00:15 UTC)
**Target:** `/root/.config/opencode/skills/automatic-implementation/SKILL.md` (236 lines)
**Method:** Read the skill, then verify every factual claim against git history, live files, systemd units, and by executing the shadow scripts' `--report` modes.

## Verdict

**The pattern itself is sound and matches the codebase. 4 factual errors found — 1 HIGH, 3 MEDIUM — plus 4 minor findings.** The HIGH error teaches the wrong enforcement date for the RR confidence multiplier (Sep 23, actually Sep 4) and invents a "3 weeks of shadow data" justification that never happened. The two MEDIUM errors claim shadow periods of "~7 days" and "~3 days" for signals that actually shadowed for ~4 hours and ~20 hours — which also directly contradicts the skill's own anti-pattern "Don't use <7 days of shadow data."

## Claim-by-Claim Results

### Scripts exist and work — PASS (4/4)

| Check | Result | Evidence |
|---|---|---|
| `scripts/gate_shadow.py` exists, `--report` runs | **PASS** | Ran `python3 scripts/gate_shadow.py --report` → full per-gate table, 23 gates, exit 0 |
| `scripts/expiry_shadow.py` exists, `--report` runs | **PASS** | Ran `--report` → conf-band table + by-reason breakdown, exit 0 |
| `scripts/t5_shadow.py` exists, `--report` runs | **PASS** | Ran `--report` → WOULD_TRADE/SKIP/UNCERTAIN table + P4 gate line, exit 0 |
| `scripts/monte_carlo_gate.py` exists | **PASS** | 5,950 bytes, mtime Aug 4 |

### Signals exist — PASS (2/2)

| Check | Result | Evidence |
|---|---|---|
| `scripts/signals/range_reversion.py` | **PASS** | Exists; `SHADOW_MODE = False` at line 59 |
| `scripts/signals/neutral_sniper.py` | **PASS** | Exists; `SHADOW_MODE = False` at line 70 |

### Systemd timers — PASS (3/3)

| Timer | Skill claim | Actual unit file | Result |
|---|---|---|---|
| `hermes-gate-shadow.timer` | hourly | `OnCalendar=hourly`, `Persistent=true` | **PASS** |
| `hermes-expiry-shadow.timer` | 30min | `OnCalendar=*:00/30` | **PASS** |
| `hermes-t5-shadow.timer` | 15min | `OnUnitActiveSec=900` | **PASS** |

All three active per `systemctl list-timers` (last runs 23:00 / 23:30 / 23:53 UTC, next runs scheduled). All three `.service` files exist with correct `ExecStart` paths (note: gate passes `--since-hours 6`, t5 passes `--since-min 20` — the skill's generic example omits args, harmless).

### Shadow DBs — PASS (3/3)

| DB | Skill claim | Actual size | Result |
|---|---|---|---|
| `brain/gate_shadow.db` | 2.6MB | 2,641,920 B (2.64 MB) | **PASS** |
| `brain/expiry_shadow.db` | 2.1MB | 2,154,496 B (2.15 MB) | **PASS** |
| `brain/t5_shadow.db` | 4.3MB | 4,321,280 B (4.32 MB) | **PASS** |

All three contain live data (reports produced thousands of rows).

### Specific code-behavior claims

| Claim | Result | Evidence |
|---|---|---|
| `RR_ENGINE_SHADOW=True, RR_ENGINE_CONF_SHADOW=False` | **PASS** | `scripts/hermes_constants.py` line 3848 (`True`) and line 3901 (`False`). Skill says "hermes_constants.py" without path — actual path is `scripts/hermes_constants.py`. Minor. |
| `monte_carlo_gate_oracle` uses `force=False` default | **PASS** | `monte_carlo_gate.py:120` — `def monte_carlo_gate_oracle(signal_type, direction, force: bool = False)`; shadow path returns `True` at line 139, docstring matches skill quote verbatim |
| gate_shadow.py: 10-min dedup | **PASS** | Line 136: `bucket = b_dt.strftime('%Y%m%d%H%M')[:-1]` → 10-min bucket; `dedup_key UNIQUE` at line 68 |
| gate_shadow.py: 24h close window | **PASS** | Line 35: `CLOSE_AFTER_HOURS = 24`; `--close` uses 24h cutoff + 24h forward-open join |
| gate_shadow.py: offset tracking | **PASS** | `OFFSET_FILE` line 34; atomic `_read_offset`/`_write_offset` (tmp+`os.replace`) lines 79–91 |
| expiry_shadow.py records EXPIRED/SKIPPED | **PASS** | Line 77: `WHERE id > ? AND decision IN ('EXPIRED','SKIPPED')` from `signals_hermes_runtime.db` |
| t5_shadow.py uses cell_stats.db | **PASS** | Line 35: `CELL_DB = .../brain/cell_stats.db`; file exists (327KB) |
| `SHADOW BLOCK` distinct prefix | **PASS** | `risk_reward_engine.py:882` logs exactly `SHADOW BLOCK {token} {direction}...`; greppable |
| Report decision rules (relax ≥55%/n≥15, keep ≤35%) | **PASS** | `gate_shadow.py:244–250` implements exactly this; `--report` output format matches the skill's Phase 4 sample table |
| Shadow flag code pattern (log + `return True`) | **PASS** | Matches `risk_reward_engine.py:880–893` (`if not passed and shadow and not force: ... passed = True`) |
| Trade learning P0-P4 (Oct 4–11) | **PASS** | File mtimes: t5 Oct 4, expiry Oct 9, gate Oct 10 |
| "RR engine killed 201 signals before audit found 3 false-kill bugs" | **PASS** | Commit `d0e205b2` (2026-10-12): "fix: 3 false-kill patterns in RR engine — kills reduced 201→27" |

### Date/number claims — where the errors are

| Claim | Result | Evidence |
|---|---|---|
| range_reversion: "shadow proved 288 signals/24h, CEO flipped Sep 1" | **PASS** | `range_reversion.py:59` comment matches verbatim; commit `555bf091` 2026-09-01 04:20 UTC "range_reversion SHADOW→LIVE (288 signals/24h validated)" |
| range_reversion: **"Shadow ran ~7 days"** | **FAIL** | File created Aug 30 22:35 (`f8a0a72b`, no SHADOW_MODE flag in that version). Flag added Sep 1 00:07 (`a1572101`), flipped live Sep 1 04:20 (`555bf091`). Shadow flag existed **~4 hours**; even generous file-lifetime counting is **~30 hours**. Not 7 days. |
| neutral_sniper: "3756 shadow signals in 11h, CEO flipped Sep 6" | **PASS** | `neutral_sniper.py:70` comment matches verbatim; commit `72a4cb5a` 2026-09-06 02:37 UTC |
| neutral_sniper: **"Shadow ran ~3 days"** | **FAIL** | Created Sep 5 06:38 with `SHADOW_MODE = True` (`7e077847`), flipped Sep 6 02:37. Shadow ran **~20 hours**. |
| **"RR_ENGINE_CONF_SHADOW ... enforced (flipped Sep 23)" / "enforced Sep 23 after 3 weeks of shadow data"** | **FAIL (HIGH)** | `git log -G` on the flag shows exactly two commits: added `True` Sep 2 (`b5c4e789`), flipped `False` **Sep 4** (`69203f91`, "config: enable RR engine — RR_ENGINE_CONF_SHADOW=False", CASHCAT SHORT R:R=0.31). Enforcement was **2 days** after build, not 3 weeks. The Sep 23 commit (`f52bb96e`) changed `RR_ENGINE_CONF_HARD_BLOCK_RR` 0.95→0.70 — a **threshold change, not a shadow flip**. The skill author appears to have conflated the two. |
| RR engine: "Built Sep 2 with dual shadow flags" | **MINOR** | `RR_ENGINE_SHADOW` added **Aug 25** (`397a940b`/`c9f55aab`); `RR_ENGINE_CONF_SHADOW` added Sep 2. Dual-flag setup complete Sep 2, but the gate flag predates it by a week. |
| RR engine: "3 rounds of bug fixes (12+ bugs found via bug_hunter) **before enforcement**" | **MINOR** | The 12-bug hunt is `rr_engine_bug_hunt_2.md`, dated **Oct 5** — after CONF_SHADOW enforcement (Sep 4). True only if "enforcement" means the still-pending gate enforcement (`RR_ENGINE_SHADOW` still `True`, confirmed current). Misleading as written. |
| "Gate still in shadow (regime minimums too aggressive per CEO) ... still shadow as of Oct 12" | **PASS** | `RR_ENGINE_SHADOW = True` currently; ceo_report.md Oct 12 confirms hard-blocks live only via `RR_ENGINE_CONF_SHADOW=False` |

## Factual Errors in the Skill (ranked)

### 1. HIGH — "Confidence multiplier enforced Sep 23 after 3 weeks of shadow data" (lines 186, 189)

Wrong on both facts. Actual: built Sep 2, enforced **Sep 4** (`69203f91`) — **2 days** of shadow, and the commit message shows enforcement was reactive (CASHCAT SHORT had R:R=0.31), not data-driven validation. Sep 23 was a `HARD_BLOCK_RR` 0.95→0.70 threshold loosening. This matters because the skill exists to teach the pattern from real history — it currently presents a rushed 2-day enforcement as a careful 3-week validated rollout, which misrepresents the standard it preaches.

### 2. MEDIUM — "range_reversion: Shadow ran ~7 days" (line 171)

Shadow flag lived ~4 hours (Sep 1 00:07 → 04:20). Max defensible number from file creation is ~30 hours.

### 3. MEDIUM — "neutral_sniper: Shadow ran ~3 days" (line 179)

Shadow ran ~20 hours (Sep 5 06:38 → Sep 6 02:37). The file's own comment says the evidence was "3756 shadow signals in **11h**."

### 4. MEDIUM — The real examples contradict the skill's own anti-pattern #3

Anti-pattern: "Don't use <7 days of shadow data. Sample sizes are too small." Both cited real examples shadowed for <1 day. Either the anti-pattern is aspirational (should be labeled as such) or the examples are bad exemplars (they prove a signal *fires*, not that it's *profitable* — 288 signals/24h and 3756 signals/11h are volume counts, not win rates). The skill should acknowledge the real rollouts were fast, volume-validated go-lives, not the 7–14 day outcome-validated rollouts it prescribes.

## Minor Findings

1. **Checklist claims rotation handling that gate_shadow.py lacks.** Skill line 75/219/237 lists "Log rotation handling (size check before seek)" as a core pattern property. Actual `gate_shadow.py:106–107` does a bare `f.seek(offset)` with no `offset > current_size` check — after a log rotation/truncation it would silently read nothing forever (exactly the failure anti-pattern #7 warns about). The advice is correct; the attribution to the reference implementation is not. (Suggested fix: add `if offset > os.path.getsize(PIPELINE_LOG): offset = 0` in gate_shadow.py, or soften the skill wording.)
2. **`monte_carlo_gate_oracle` has no callers.** Grep across `scripts/` finds only `signal_schema.py` importing plain `monte_carlo_gate`. The oracle wrapper exists and works but was never wired in — the skill implies it was "used to validate thresholds before enforcement."
3. **Constants path.** Skill says "hermes_constants.py"; actual path is `scripts/hermes_constants.py`.
4. **Timer example syntax.** Skill Phase 2 sample uses `OnCalendar=*:0/30`; real unit uses `*:00/30`. Cosmetic, but copy-pasting the sample may not parse.

## Verified-Good (no action needed)

- The 6-phase structure, shadow-flag pattern, fail-open rule, standalone-counterfactual design, dedup/close/report CLI modes, and the decision-rules table all match the actual codebase.
- `ceo_report.md` exists at `automation/ceo/ceo_report.md` where the skill says CEO decisions go.
- All three shadow scripts are genuinely standalone (zero trading-path imports beyond read-only queries) and run clean with `--report`.
- The Phase 4 sample report table matches real `gate_shadow.py --report` output format exactly.

## Recommended Fixes to SKILL.md

1. Line 186/189: change "flipped Sep 23" → "enforced Sep 4 (commit 69203f91, 2 days after build — reactive, CASHCAT R:R=0.31)"; replace "after 3 weeks of shadow data" with the true 2-day history, and add a note that this fast flip was the exception, not the model.
2. Line 171: "Shadow ran ~7 days" → "Shadow flag ran ~4h (file existed ~30h)".
3. Line 179: "Shadow ran ~3 days" → "Shadow ran ~20h".
4. Add a line to "Real Examples" clarifying these were signal-*volume* validations, distinct from the gate pattern's outcome-based decision rules.
5. Line 75: either mark rotation handling as "recommended, NOT yet in gate_shadow.py" or fix gate_shadow.py first.
