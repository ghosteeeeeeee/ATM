# SPEC — Hermes Self-Improvement Loop

**Document type:** Engineering specification (binding contract for implementation)
**Status:** DRAFT — awaiting T sign-off
**Author:** Hermes
**Date:** 2026-06-20
**Replaces:** ad-hoc verbal design captured in interview

---

## 1. Scope

Build a periodic, autonomous system that:
- **(S1)** Scans the Hermes trading pipeline for bugs, race conditions, file-lock breaches, and dead signals.
- **(S2)** Files every finding as a Kanban card for human review before any code change.
- **(S3)** Auto-fixes a narrow, safe subset: (a) obvious bugs producing repeated tracebacks, (b) signal-threshold tuning inside a ±20% guarded band. Everything else asks.
- **(S4)** Improves trading win-rate across three levers — signal quality, TP/SL discipline, regime adaptation — and emits a ranked weekly report.
- **(S5)** Runs on three cadences: 4h short, 12h deep, weekly (Mon 06:00 UTC). Plus ad-hoc on incident.

**Out of scope:** trading-strategy invention, ATR constant changes, auth/secret file edits, structural refactors.

---

## 2. Architecture Overview

```
                ┌─────────────────────────────────────────────┐
                │           systemd timers (3)                │
                │  hermes-scan-short   every 4h               │
                │  hermes-scan-deep    every 12h              │
                │  hermes-scan-weekly  Mon 06:00 UTC          │
                └──────────────┬──────────────────────────────┘
                               │ invokes
                               ▼
                ┌─────────────────────────────────────────────┐
                │  system_improver.py                         │
                │    --mode {short|deep|weekly}               │
                │    --incident "ctx"                         │
                │    --dry-run                                │
                └──────────────┬──────────────────────────────┘
                               │ dispatches
                               ▼
        ┌────────────────────────────────────────────────────┐
        │  scanners/ (independent modules, single-purpose)   │
        │  ├─ scan_logs.py                                   │
        │  ├─ scan_filelocks.py                              │
        │  ├─ scan_pipeline.py                               │
        │  ├─ scan_signals.py (dead-signal detector)         │
        │  ├─ winrate_signal_quality.py                      │
        │  ├─ winrate_tpsl.py                                │
        │  ├─ winrate_regime.py                              │
        │  └─ safe_auto_fix.py                               │
        └──────────────┬─────────────────────────────────────┘
                       │ findings (JSON list)
                       ▼
        ┌────────────────────────────────────────────────────┐
        │  kanban_writer.py                                  │
        │    atomic append → KANBAN_FILE  (JSONL)            │
        │    idempotency table → data/improvements/dedup.db  │
        └────────────────────────────────────────────────────┘

   Weekly path additionally:
        findings → weekly_report.py → data/reports/winrate_YYYY-MM-DD.md
                                └─→ 1 summary Kanban card
```

**Threading model:** single-process, sequential scanners per run. No shared state between runs except Kanban file + dedup DB.
**DB access:** read-only via SQLite URI `file:...?mode=ro`. Never writes to `signals_hermes.db`, `candles.db`, or any archive DB.
**Idempotency:** every finding carries a deterministic `signature`; dedup TTL by type. See §7.

---

## 3. Module Specifications

### 3.0 `system_improver.py` — orchestrator

**Path:** `/root/.hermes/scripts/system_improver.py`

**CLI:**
```
python3 system_improver.py
    --mode {short|deep|weekly}      # required
    [--incident "context string"]   # optional, from smoke_test.py --improve
    [--dry-run]                     # default false in systemd units; true if env=DRY_RUN
    [--max-cards N]                 # default 20, hard cap per run
```

**Exit codes:**
| Code | Meaning |
|---|---|
| 0 | success, 0+ findings filed |
| 1 | success but auto-fix was blocked (human review needed) |
| 2 | scanner crash — improver self-error, not a finding |
| 3 | dedup table corrupt / disk full — fatal infra |

**Stdout (one line, JSON):**
```json
{"mode":"short","ts":"2026-06-20T02:00:00Z","elapsed_s":4.21,"findings":3,"cards_new":3,"cards_deduped":1,"auto_fix_applied":0,"auto_fix_blocked":0,"errors":[]}
```

**Stderr (only on crash):** full traceback.

**Dispatch table:**
| mode | scanners invoked | auto-fix on? |
|---|---|---|
| short | logs, filelocks, pipeline, signals(dead) | yes (bug-rule tier only) |
| deep | short + winrate_signal_quality, winrate_tpsl, winrate_regime | yes (full) |
| weekly | deep | yes (full) + report |

---

### 3.1 `scanners/scan_logs.py`

**Purpose:** Find repeating tracebacks and recurring ERROR lines.

**Inputs:** globs `/var/log/*.log`, `/var/log/*.err.log`, `/root/.hermes/logs/*.log`. Per-file: tail last 50,000 lines OR lines with mtime within last 4h, whichever is smaller.

**Algorithm:**
1. For each file, stream line-by-line.
2. Match against two regex sets:
   - `TRACEBACK_RE = r'^Traceback \(most recent call last\):'`
   - `ERROR_RE = r'\b(ERROR|CRITICAL)\b'`
3. Group matches by `(exception_type, script_basename)`. `exception_type` = first line of the traceback block, e.g. `KeyError: 'foo'`. `script_basename` = first `.py` filename in the stack trace.
4. Emit finding if `count >= 2` (tracebacks) OR `count >= 5` (errors) within the window.
5. Whitelist filter: drop matches whose `(exception_type, script_basename)` is in module-level `KNOWN_NOISE` set.

**Finding schema (logs):**
```json
{
  "type": "log_error",
  "signature": "log_error:KeyError:'foo':signal_compactor.py",
  "script": "signal_compactor.py",
  "exception_type": "KeyError: 'foo'",
  "count": 7,
  "first_seen": "2026-06-20T01:55:00Z",
  "last_seen": "2026-06-20T02:00:00Z",
  "sample_line": "File \"signal_compactor.py\", line 482, in compact_signals",
  "log_file": "/var/log/pipeline.err.log",
  "confidence": 0.95,
  "severity": 0.8,
  "auto_fix_eligible": true,
  "auto_fix_kind": "bug_rule"
}
```

**Confidence:** 0.95 if count ≥ 2 tracebacks; 0.85 if 5+ errors; 0.70 if 3-4 errors.
**Severity:** 0.8 if traceback in `signal_compactor.py` / `position_manager.py` / `hl-sync-guardian.py`; 0.5 otherwise.

**Self-test:** `--selftest` plants `/tmp/hermes_st_log.log` with 3 identical tracebacks; expects 1 finding with `count=3`.

---

### 3.2 `scanners/scan_filelocks.py`

**Purpose:** Detect orphan `.lock` files whose owning PID is dead.

**Inputs:** globs:
- `/root/.hermes/data/*.lock`
- `/var/www/hermes/data/*.lock`
- `/tmp/hermes_*.lock`
- `/tmp/*.lock` (only if filename contains "hermes")

**Algorithm:**
1. For each lock file:
   a. Stat `mtime`. If `now - mtime < 60s` → skip (in-flight write).
   b. Read PID from file. Lock files MUST be JSON `{"pid": <int>, "owner": "<script>", "created": "<iso>"}`. Malformed JSON → finding `malformed_lock`.
   c. Check `/proc/<pid>` exists. If not → finding `orphan_lock`.
   d. If alive, cross-check `owner` matches `pid`'s `/proc/<pid>/cmdline` (best-effort). Mismatch → finding `stolen_lock`.

**Findings:**
| type | severity | confidence | auto_fix |
|---|---|---|---|
| `orphan_lock` | 0.6 | 0.99 | yes — unlink file |
| `malformed_lock` | 0.4 | 1.0 | no |
| `stolen_lock` | 0.9 | 0.85 | no |

**Allowlist (never flagged):** `*.lock` matching `/(healthcheck|metrics_collector)/`.

**Self-test:** create `/tmp/hermes_st.lock` with `pid: 99999999` (dead), expect 1 `orphan_lock` finding.

---

### 3.3 `scanners/scan_pipeline.py`

**Purpose:** Detect stalled or failing systemd units and stale heartbeats.

**Algorithm:**
1. `systemctl is-active hermes-pipeline hermes-hl-sync-guardian hermes-metrics hermes-coding-mcp`. For each not `active` → finding `service_down`.
2. Read `PIPELINE_HB_FILE` (from `paths.py`). If `now - mtime > 180s` → finding `pipeline_stalled`.
3. Read `MAX_HEARTBEAT_AGE` constant from `safe_auto_fix.py` (default 180s).
4. For each script modified in `/root/.hermes/scripts/*.py` within last 4h (mtime): call `smoke_test.py --target <script>` via subprocess. Non-zero exit → finding `smoke_regression`.
5. Bonus: scan for write contention. Read `paths.py` to enumerate shared files. Grep scripts for `open(.*, ['\"]w['\"])` + same path in ≥2 scripts. If unprotected (no `.lock` companion and no `fcntl.flock`) → finding `race_risk`.

**Finding (race_risk) schema:**
```json
{
  "type": "race_risk",
  "signature": "race:hotset.json:signal_compactor.py,guardian.py",
  "path": "/var/www/hermes/data/hotset.json",
  "writers": ["signal_compactor.py", "hl-sync-guardian.py"],
  "protected": false,
  "writes_last_24h": 142,
  "severity": 0.7,
  "confidence": 0.8,
  "auto_fix_eligible": false
}
```

**Self-test:** `--selftest` creates two scripts that both write `/tmp/hermes_st_shared.json` without lock; expects `race_risk` finding with `protected=false`.

---

### 3.4 `scanners/scan_signals.py` — dead-signal detector

**Purpose:** Find signals registered but never firing in the last 24h.

**Algorithm:**
1. Read `signals/__init__.py` `REGISTRY` dict. Keys = signal names.
2. SQL: `SELECT signal_type, COUNT(*) FROM signals WHERE ts > datetime('now','-1 day') GROUP BY signal_type`. Open via `sqlite3.connect(f"file:{SIGNALS_DB}?mode=ro", uri=True)`.
3. For each registered signal: if `count == 0` AND signal module mtime is > 24h old (signal has had time to run) → finding `dead_signal`.

**Finding:**
```json
{
  "type": "dead_signal",
  "signature": "dead:ema_angle:v2",
  "signal_name": "ema_angle",
  "registered_at": "2026-05-12T11:00:00Z",
  "last_fire": "2026-06-18T04:22:00Z",
  "hours_since_fire": 38.5,
  "severity": 0.5,
  "confidence": 0.9,
  "auto_fix_eligible": false,
  "auto_fix_kind": null,
  "recommendation": "investigate: filter too strict? data dependency missing?"
}
```

**Self-test:** register a fake signal in `/tmp/hermes_st_signals/__init__.py` with no DB rows; expect 1 finding.

---

### 3.5 `scanners/winrate_signal_quality.py`

**Purpose:** Rank signals by expected loss per week from false positives.

**Inputs:** `/root/.hermes/archive/trades_analysis.db::closed_trades` (last 30 days), `signals_hermes.db::signals` (last 7 days for fire count).

**Algorithm:**
1. Pull all closed trades last 30d: `SELECT entry_signals, pnl_usd, exit_reason, ts_close FROM closed_trades WHERE ts_close > datetime('now','-30 days')`.
2. Group by `tuple(sorted(entry_signals))`. Per group compute:
   - `n` (sample size)
   - `hit_rate = wins / n` where `win = pnl_usd > 0`
   - `avg_pnl` (dollars)
   - `false_positive_rate = 1 - hit_rate`
3. Suppress groups with `n < 10`.
4. For each non-suppressed group, compute `fires_per_week = sum(signals where type IN group AND ts > -7d) / 4.0`.
5. `expected_loss_per_week = fp_rate * abs(avg_pnl_when_loss) * fires_per_week`.

**Finding:**
```json
{
  "type": "low_quality_signal",
  "signature": "lowq:rs-r136:v3",
  "signals": ["rs-r136"],
  "n_trades": 47,
  "hit_rate": 0.34,
  "avg_pnl_usd": -12.4,
  "fires_per_week": 38,
  "expected_loss_per_week_usd": 311.5,
  "severity": 0.9,
  "confidence": 0.85,
  "auto_fix_eligible": true,
  "auto_fix_kind": "quarantine_signal",
  "recommended_action": "quarantine_signal('rs-r136')"
}
```

**Auto-fix eligible when:** `expected_loss_per_week_usd >= QUARANTINE_LOSS_THRESHOLD_USD` (default 50, lives in `safe_auto_fix.py`).

---

### 3.6 `scanners/winrate_tpsl.py`

**Purpose:** Find TP/SL misconfiguration via MFE/MAE reconstruction.

**Inputs:** closed trades (last 30d), 1m candles from `signals_hermes.db::price_history` for the entry→exit window.

**Algorithm:**
1. For each closed trade: pull entry_ts, exit_ts, intended_sl_pct, intended_tp_pct, exit_reason.
2. Query 1m prices for `[entry_ts, exit_ts]` window.
3. Compute:
   - `MFE = max(high) / entry_price - 1` (signed by side)
   - `MAE = 1 - min(low) / entry_price` (signed by side)
4. Classify:
   - **tpsl_too_tight:** exit_reason in `{tp_hit, sl_hit}` AND `MFE < 1.2 * intended_tp_pct` (TP was reachable, we left money) AND `MAE < intended_sl_pct` (never threatened)
   - **sl_too_tight:** exit_reason=`sl_hit` AND `MAE < 0.3 * ATR_at_entry` (whipsaw)
   - **sl_too_loose:** exit_reason=`sl_hit` AND `MAE > 2.0 * intended_sl_pct` (trailing bug, SL never moved)

**Aggregate per coin:** group findings; emit one card per coin with `count_tpsl_too_tight`, `count_sl_too_tight`, `count_sl_too_loose`.

**Auto-fix eligible:** NO. TP/SL constants require T approval per SOUL rule. Card always `auto_fix_eligible=false`.

---

### 3.7 `scanners/winrate_regime.py`

**Purpose:** Detect regime-misfit where signals underperform in non-favored regimes.

**Inputs:** `regime_cache` (path per `paths.py`), closed trades (last 14d).

**Algorithm:**
1. For each closed trade: lookup regime at `entry_ts` from regime_cache.
2. Build matrix `win_rate[signal_class][regime]`. `signal_class` = first entry_signal token.
3. Compute `overall_win_rate` across all rows.
4. For each cell with `n >= 20` AND `win_rate < 0.35` AND `win_rate < 0.5 * overall_win_rate` → finding `regime_misfit`.

**Finding:**
```json
{
  "type": "regime_misfit",
  "signature": "regime:SHORT_BIAS:zscore_pump",
  "regime": "SHORT_BIAS",
  "signal_class": "zscore_pump",
  "n": 23,
  "win_rate": 0.22,
  "overall_win_rate": 0.48,
  "expected_loss_per_week_usd": 87.0,
  "severity": 0.7,
  "confidence": 0.8,
  "auto_fix_eligible": false,
  "recommendation": "consider regime-aware filter on zscore_pump during SHORT_BIAS"
}
```

---

### 3.8 `scanners/safe_auto_fix.py`

**Purpose:** Apply guarded auto-fixes per autonomy rules.

**Public API:**
```python
def attempt_auto_fix(finding: dict, dry_run: bool = False) -> dict:
    """Returns {"applied": bool, "patch_path": str|None, "blocked_reason": str|None, "kind": str}"""
```

**Decision tree (deterministic, in order):**
1. If `finding["auto_fix_eligible"] != True` → return `{"applied": False, "blocked_reason": "not_eligible", "kind": None}`.
2. If `finding["auto_fix_kind"]` not in `ALLOWED_KINDS` → blocked `not_allowed_kind`.
3. If `finding["confidence"] < AUTO_FIX_CONFIDENCE_FLOOR` (default 0.9) → blocked `low_confidence`.
4. Run `verify_reversible(finding["auto_fix_kind"], finding)` — see below. Fail → blocked.
5. Resolve target file + change. Generate unified diff. Write to `/root/.hermes/data/improvements/proposed_<ts>_<uuid8>.patch`.
6. If `dry_run` → return `{"applied": False, "blocked_reason": "dry_run", "patch_path": ...}`.
7. Apply change atomically (write-temp + rename).
8. Verify post-state (re-read file, confirm change landed). Fail → rollback, blocked `post_verify_failed`.
9. Return `{"applied": True, "patch_path": ..., "kind": ..., "rollback_cmd": ...}`.

**`ALLOWED_KINDS`:**
```python
ALLOWED_KINDS = {
    "quarantine_signal",    # adds `quarantine=True` to REGISTRY entry in signals/__init__.py
    "tune_threshold",       # edits a numeric threshold inside ±20% guarded band
    "fix_typo_bug",         # bug-rule tier: edits string literal that matches a traceback
}
```

**`verify_reversible` per kind:**
- `quarantine_signal`: change is a single-line addition (`True` flag). Revert = remove that line.
- `tune_threshold`: change ≤ ±20% of original AND original value > 0. Revert = re-set original. Both values stored in patch header.
- `fix_typo_bug`: requires `finding["sample_line"]` to be a substring of the target file AND proposed fix is a string-literal swap matching the traceback. Revert = re-swap.

**Hardcoded blocklist (any write hits any of these → immediate block, severity-1 Kanban card):**
```python
BLOCKED_PATH_GLOBS = [
    "*hermes_constants.py",
    "*auth*.json",
    "*/secrets/*",
    "*/.ssh/*",
    "*/.gnupg/*",
    "/etc/passwd", "/etc/shadow",
    "*/scanners/safe_auto_fix.py",     # improver cannot modify itself
    "*/scanners/__init__.py",          # improver cannot modify its registry
]
```

**`safe_auto_fix.py` constants (top of file, editable by T):**
```python
AUTO_FIX_CONFIDENCE_FLOOR = 0.90
QUARANTINE_LOSS_THRESHOLD_USD = 50.0
TUNE_THRESHOLD_BAND = 0.20          # ±20%
MAX_HEARTBEAT_AGE_SEC = 180
MAX_CARDS_PER_DAY = 20
```

**Self-test:** `--selftest` simulates a `quarantine_signal` finding on a fake registry file; expects patch file produced + atomic write succeeded + rollback path valid.

---

### 3.9 `scanners/kanban_writer.py`

**Public API:**
```python
def write_card(card: dict) -> dict:
    """Returns {"id": str, "created": bool, "deduped_against": str|None}"""

def build_card_from_finding(finding: dict, mode: str) -> dict:
    """Construct a Kanban card from a finding + run mode."""
```

**Card schema (required fields):**
```json
{
  "id": "uuid4-string",
  "created_at": "2026-06-20T02:00:00Z",
  "status": "pending_review" | "auto_applied" | "rejected" | "closed",
  "type": "<finding.type>",
  "summary": "<= 120 char human line>",
  "details": "<full finding object>",
  "severity": 0.0,
  "confidence": 0.0,
  "source": "system_improver",
  "mode": "short" | "deep" | "weekly" | "incident",
  "auto_fix": {
    "applied": false,
    "patch_path": null,
    "kind": null,
    "rollback_cmd": null
  },
  "tags": ["auto_fixable", "winrate"] // derived
}
```

**Atomic write protocol:**
1. Read current `KANBAN_FILE` (JSONL).
2. Compute idempotency check (see §7).
3. Append new line to in-memory list.
4. Write to `KANBAN_FILE.tmp.<pid>`, fsync, `os.replace(tmp, final)`.

**Per-day cap:** if `count(cards today) + new >= MAX_CARDS_PER_DAY`, instead write ONE digest card with `type=improver_digest`, `details.summary=count_by_type`, and skip the individual cards. Digest card itself bypasses dedup.

---

### 3.10 `scanners/weekly_report.py`

**Inputs:** all findings from the three win-rate scanners (deep mode).

**Algorithm:**
1. Collect findings from `winrate_*` modules.
2. Compute `expected_impact = finding["severity"] * (1.0 - rolling_30d_win_rate)`.
3. Sort descending by `expected_impact`.
4. Write markdown to `/root/.hermes/data/reports/winrate_YYYY-MM-DD.md` (per §4.3 schema).
5. Emit ONE summary Kanban card with top-3 findings inlined in `details`.

**Weekly-only:** if total `closed_trades` in last 7d < 30, report body contains: `> ⚠️ Insufficient data: only N trades in last 7 days. First reliable report due YYYY-MM-DD.`

---

## 4. Data Schemas

### 4.1 Finding (internal, scanner → orchestrator → kanban_writer)

```json
{
  "type": "log_error | orphan_lock | malformed_lock | stolen_lock | service_down | pipeline_stalled | smoke_regression | race_risk | dead_signal | low_quality_signal | tpsl_misfit | regime_misfit",
  "signature": "<deterministic dedup key, see §7>",
  "severity": 0.0,
  "confidence": 0.0,
  "auto_fix_eligible": false,
  "auto_fix_kind": null | "quarantine_signal" | "tune_threshold" | "fix_typo_bug",
  "...type-specific fields...": "..."
}
```

Severity/confidence are floats in `[0.0, 1.0]`. Both MUST be set.

### 4.2 Kanban card (written to `KANBAN_FILE`)

JSONL — one card per line. Schema above (§3.9).

### 4.3 Weekly report markdown

```markdown
# Hermes Win-Rate Report — YYYY-MM-DD

**Period:** YYYY-MM-DD → YYYY-MM-DD (last 7d, comparison: prior 7d)
**Closed trades:** N (vs M prior)
**Rolling 30d win rate:** XX.X% (vs YY.Y% prior)

> ⚠️ Insufficient data banner if applicable.

## Top findings (ranked by expected_impact)

### 1. <type>: <summary>
- **Severity:** 0.X  **Confidence:** 0.X
- **Expected impact:** $XXX/week
- **Recommendation:** ...
- **Card:** <card_id>

### 2. ...

## Win-rate lever breakdown

### Signal quality
- ...

### TP/SL discipline
- ...

### Regime adaptation
- ...

## Auto-fixes applied since last report
- (none) | list with patch paths

## Open cards (pending_review)
- count by type
```

### 4.4 Patch artifact

Path: `/root/.hermes/data/improvements/proposed_<UTC-timestamp>_<uuid8>.patch`

Header (before diff):
```
# Hermes safe-auto-fix patch
# finding_type: <type>
# finding_signature: <signature>
# target_file: <abs path>
# change_kind: <kind>
# original_value: <repr>     (for tune_threshold)
# new_value: <repr>          (for tune_threshold)
# confidence: <float>
# applied_at: <iso>
# rollback: <exact git checkout or sed cmd>
```

Body: unified diff (`diff -u` format).

---

## 5. Cadence & Systemd Specs

### 5.1 `hermes-scan-short` — every 4h

**Service unit** (`/etc/systemd/system/hermes-scan-short.service`):
```ini
[Unit]
Description=Hermes Short Scan (logs, locks, pipeline, dead signals)
After=hermes-pipeline.service hermes-metrics.service
Wants=hermes-pipeline.service

[Service]
Type=oneshot
User=hermes
Group=hermes
Environment=DRY_RUN=true
ExecStart=/usr/bin/python3 /root/.hermes/scripts/system_improver.py --mode short
StandardOutput=journal
StandardError=journal
Nice=10
TimeoutStartSec=300
```

**Timer unit** (`/etc/systemd/system/hermes-scan-short.timer`):
```ini
[Unit]
Description=Hermes Short Scan timer (every 4h)

[Timer]
OnCalendar=*-*-* 00/4:00:00
Persistent=true
AccuracySec=60s
Unit=hermes-scan-short.service

[Install]
WantedBy=timers.target
```

**First 48h after deploy:** `Environment=DRY_RUN=true`. After T confirms cards are useful, edit service to `DRY_RUN=false` and `systemctl daemon-reload`.

### 5.2 `hermes-scan-deep` — every 12h

```ini
# service
OnCalendar=offset...
[Service]
Type=oneshot
User=hermes
Group=hermes
Environment=DRY_RUN=true
ExecStart=/usr/bin/python3 /root/.hermes/scripts/system_improver.py --mode deep
TimeoutStartSec=900
```

```ini
# timer
OnCalendar=*-*-* 00/12:05:00     # 5 min after short to avoid contention
Persistent=true
```

### 5.3 `hermes-scan-weekly` — Mon 06:00 UTC

```ini
# service
ExecStart=/usr/bin/python3 /root/.hermes/scripts/system_improver.py --mode weekly
TimeoutStartSec=1800
```

```ini
# timer
OnCalendar=Mon *-*-* 06:00:00
Persistent=true
```

**Enable sequence:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-scan-short.timer hermes-scan-deep.timer hermes-scan-weekly.timer
sudo systemctl list-timers 'hermes-scan-*'
```

---

## 6. Autonomy Guardrails (deterministic)

| Condition | Behavior |
|---|---|
| `auto_fix_eligible == False` | No-op. Card filed. |
| `auto_fix_kind` not in `ALLOWED_KINDS` | No-op. Card filed with `blocked_reason=not_allowed_kind`. |
| `confidence < AUTO_FIX_CONFIDENCE_FLOOR` (0.90) | No-op. Card filed. |
| Target path matches `BLOCKED_PATH_GLOBS` | No-op. Card filed with severity 1.0 and tag `BLOCKLIST_HIT`. |
| Threshold change > `TUNE_THRESHOLD_BAND` (20%) | No-op. Card filed. |
| Patch file write fails | No-op. Card filed with `blocked_reason=patch_write_failed`. |
| Post-apply verify fails | Rollback. Card filed with `blocked_reason=post_verify_failed` and `auto_fix.applied=false`. |
| `dry_run == True` (or env `DRY_RUN=true`) | Patch written, not applied. Card `auto_fix.applied=false, patch_path=set`. |
| `MAX_CARDS_PER_DAY` exceeded | Skip to digest card. |

**Hard rules:**
- Never touches `hermes_constants.py` (SOUL rule, repeated in `BLOCKED_PATH_GLOBS`).
- Never writes to any `*.db` except `/root/.hermes/data/improvements/dedup.db` and `/root/.hermes/data/improvements/state.json`.
- Never invokes `subprocess` to run trading scripts.
- Never calls `subprocess.run` on `decider_run.py`, `position_manager.py`, or anything that places orders.

---

## 7. Idempotency & Dedup

**Dedup DB:** `/root/.hermes/data/improvements/dedup.db` (SQLite, single table).

```sql
CREATE TABLE findings (
    signature TEXT PRIMARY KEY,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    card_id TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_last_seen ON findings(last_seen);
```

**Signature composition by type:**
| type | signature format |
|---|---|
| `log_error` | `log_error:<exception_type>:<script_basename>` |
| `orphan_lock` | `orphan_lock:<abs_path>` |
| `service_down` | `service_down:<unit_name>` |
| `pipeline_stalled` | `pipeline_stalled` (single key) |
| `race_risk` | `race:<path>:<sorted_writers_csv>` |
| `dead_signal` | `dead:<signal_name>` |
| `low_quality_signal` | `lowq:<sorted_signals_csv>:<period_days>` |
| `tpsl_misfit` | `tpsl:<coin>:<class>` |
| `regime_misfit` | `regime:<regime>:<signal_class>` |

**TTL per type (hours):**
| type | TTL |
|---|---|
| `log_error` | 24 |
| `orphan_lock` | 6 |
| `service_down` | 1 |
| `pipeline_stalled` | 1 |
| `race_risk` | 168 (7d) |
| `dead_signal` | 24 |
| `low_quality_signal` | 168 |
| `tpsl_misfit` | 168 |
| `regime_misfit` | 168 |

**Lookup algorithm:**
1. Compute `signature`.
2. `SELECT first_seen, last_seen, card_id FROM findings WHERE signature = ?`.
3. If row exists AND `now - last_seen < TTL(type)` → return existing `card_id`, increment `count`, skip write.
4. Else → INSERT (or UPDATE `last_seen`), write new card, return new id.

---

## 8. Error Handling

| Failure | Behavior | Exit |
|---|---|---|
| Single scanner raises | Log to stderr, mark as `errors=[scanner_name]`, continue other scanners | 0 |
| Kanban writer fails | Abort run, log full traceback | 3 |
| Patch write fails | Continue (card filed, auto_fix not applied) | 0 |
| DB read fails (ro) | Skip that scanner, log error, continue | 0 |
| Dedup DB corrupt | Abort run | 3 |
| Improver itself crashes | Catch in `system_improver.py::main`, write stderr trace, exit 2 | 2 |

**No retry.** If a run fails, next scheduled run handles it. The pipeline must not depend on improver success.

**Logger:** `/root/.hermes/logs/improver.log` (rotated by logrotate if present; else manual). Format:
```
2026-06-20T02:00:00Z INFO mode=short scanners=4 findings=3 cards_new=2 cards_deduped=1 auto_fix_applied=0 errors=[]
```

---

## 9. Verification Protocol

Per-module verification commands (run during implementation, before commit):

| Module | Command | Expected |
|---|---|---|
| `system_improver.py` | `python3 system_improver.py --mode short --dry-run` | exit 0, stdout JSON with `findings>=0` |
| `scan_logs.py` | `python3 scan_logs.py --selftest` | exit 0, prints "OK" |
| `scan_filelocks.py` | `python3 scan_filelocks.py --selftest` | exit 0, prints "OK" |
| `scan_pipeline.py` | `python3 scan_pipeline.py --selftest` | exit 0, prints "OK" |
| `scan_signals.py` | `python3 scan_signals.py --selftest` | exit 0, prints "OK" |
| `winrate_signal_quality.py` | `python3 winrate_signal_quality.py --selftest --archive-db /tmp/hermes_st_archive.db` | exit 0, prints finding count |
| `winrate_tpsl.py` | `python3 winrate_tpsl.py --selftest` | exit 0, prints "OK" |
| `winrate_regime.py` | `python3 winrate_regime.py --selftest` | exit 0, prints "OK" |
| `safe_auto_fix.py` | `python3 safe_auto_fix.py --selftest` | exit 0, prints "OK", patch file exists |
| `kanban_writer.py` | `python3 kanban_writer.py --selftest` | exit 0, card visible in KANBAN_FILE.tmp |
| `weekly_report.py` | `python3 weekly_report.py --selftest --output /tmp/hermes_st_report.md` | exit 0, file contains "# Hermes Win-Rate Report" |

**End-to-end test** (`tests/test_improver_e2e.sh`):
```bash
#!/bin/bash
set -euo pipefail
# 1. Stop timers to avoid interference
sudo systemctl stop hermes-scan-{short,deep,weekly}.timer

# 2. Plant dirty state
mkdir -p /tmp/hermes_e2e
echo "Traceback (most recent call last): File \"fake.py\"" > /tmp/hermes_e2e/err.log
echo "Traceback (most recent call last): File \"fake.py\"" >> /tmp/hermes_e2e/err.log
echo "Traceback (most recent call last): File \"fake.py\"" >> /tmp/hermes_e2e/err.log
echo '{"pid": 99999999, "owner": "fake"}' > /tmp/hermes_e2e/orphan.lock

# 3. Run short mode
HERMES_DATA=/tmp/hermes_e2e python3 /root/.hermes/scripts/system_improver.py --mode short

# 4. Assert KANBAN_FILE has new cards
test $(jq -s 'map(select(.source=="system_improver")) | length' /var/www/hermes/data/kanban.jsonl) -ge 2

# 5. Plant known-bad signal in archive DB
sqlite3 /root/.hermes/archive/trades_analysis.db "INSERT INTO closed_trades ..."
# ... (see test fixture in tests/fixtures/)

# 6. Run deep
HERMES_DATA=/tmp/hermes_e2e python3 /root/.hermes/scripts/system_improver.py --mode deep

# 7. Assert quarantine card or auto_applied card present
test $(jq -s 'map(select(.type=="low_quality_signal")) | length' /var/www/hermes/data/kanban.jsonl) -ge 1

# 8. Run weekly dry-run
HERMES_DATA=/tmp/hermes_e2e python3 /root/.hermes/scripts/system_improver.py --mode weekly --dry-run

# 9. Assert report file
test -f /root/.hermes/data/reports/winrate_*.md

# 10. Cleanup
rm -rf /tmp/hermes_e2e
echo "E2E PASS"
```

---

## 10. Acceptance Criteria

System is "done" when ALL of the following are true:

- [ ] AC-1: `system_improver.py --mode short` runs in < 30s on idle pipeline, exits 0.
- [ ] AC-2: Synthetic log traceback produces exactly 1 `log_error` card within 1 run.
- [ ] AC-3: Synthetic orphan lock is unlinked by auto-fix (deep mode, non-dry-run) AND `.patch` file exists.
- [ ] AC-4: No card with same `(type, signature)` is written twice within TTL window.
- [ ] AC-5: `hermes_constants.py` mtime unchanged after 7 days of auto-fix runs.
- [ ] AC-6: Weekly report exists in `data/reports/` on every Monday after 06:00 UTC.
- [ ] AC-7: Auto-applied patches are reversible via single git/sed command (verified by running `rollback_cmd` in test).
- [ ] AC-8: `MAX_CARDS_PER_DAY` cap holds — a smoke test forcing 50 findings produces 1 digest card + 19 individual cards, not 50.
- [ ] AC-9: All 11 module `--selftest` commands pass.
- [ ] AC-10: End-to-end test (`tests/test_improver_e2e.sh`) passes.
- [ ] AC-11: ATM-Architecture.md has "Self-Improvement Loop" section with disable commands.
- [ ] AC-12: `systemctl disable --now hermes-scan-{short,deep,weekly}.timer` cleanly halts the loop; no orphan timers.

---

## 11. Out of Scope (explicit)

- Changes to `hermes_constants.py`.
- Trading strategy invention (new signal types).
- ATR TP/SL constant changes.
- Refactors of existing scanner code beyond what auto-fix needs.
- Auth/secret/key file edits.
- Network calls to external services from improver itself.
- Realtime alerting (Telegram/etc.) — flagged for future spec.
- Multi-host deployment (assumes single host `/root/.hermes`).

---

## 12. References

- `/root/.hermes/scripts/paths.py` — single source of truth for all paths
- `/root/.hermes/scripts/smoke_test.py` — chassis we extend
- `/root/.hermes/ATM/ATM-Architecture.md` — system overview
- `/root/.hermes/scripts/signals/__init__.py` — signal registry format
- `/root/.hermes/archive/trades_analysis.db::closed_trades` — win-rate data source
- SOUL.md — autonomy rules, ATR TP/SL rule, "no cron" rule, Bug Fix Rule
- Interview answers captured 2026-06-20 (cadence, kanban, autonomy, levers, style)

---

## 13. Open Questions (blocking T sign-off)

1. First 48h `DRY_RUN=true` on short timer? **[Default: yes]**
2. `QUARANTINE_LOSS_THRESHOLD_USD` start at $50 or $20? **[Default: $50]**
3. Weekly report delivery: Kanban card only, or also Telegram/CLI ping? **[Default: Kanban only]**
