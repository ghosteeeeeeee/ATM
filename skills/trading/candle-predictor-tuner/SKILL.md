---
name: candle-predictor-tuner
description: Hourly autonomous agent that analyzes candle_predictor accuracy, identifies improvement opportunities, and implements fixes to candle_predictor.py automatically.
trigger: cron hourly
---

# Candle Predictor Auto-Tuner

## Purpose
Hourly autonomous agent that analyzes candle_predictor accuracy data, identifies patterns for improvement, and implements fixes automatically.

## How It Works
Runs as a cron job every hour. The agent reads prediction.db, performs statistical analysis, identifies the biggest accuracy problems, and makes targeted changes to `candle_predictor.py`.

## Analysis Steps

### 1. Overall Accuracy Check
```sql
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions WHERE correct IS NOT NULL;
```
If accuracy < 40% or > 65%: flag as problem requiring attention.

### 2. Direction × Momentum State Breakdown
```sql
SELECT 
  momentum_state, direction,
  COUNT(*) as n,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions 
WHERE correct IS NOT NULL AND momentum_state IS NOT NULL
GROUP BY momentum_state, direction
ORDER BY accuracy;
```
Find the WORST performing combination. This is the priority target.

### 3. Per-Token Accuracy (bottom 10)
```sql
SELECT token, direction,
  COUNT(*) as n,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions WHERE correct IS NOT NULL
GROUP BY token, direction
HAVING n >= 20
ORDER BY accuracy
LIMIT 10;
```
Tokens with <40% accuracy on 20+ predictions need special handling.

### 4. Inversion Effectiveness

Two views, both required — they tell different stories:

**Cumulative (all-time) — historical net effect:**
```sql
SELECT 
  was_inverted,
  direction,
  COUNT(*) as total,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions WHERE correct IS NOT NULL
GROUP BY was_inverted, direction;
```
This is dominated by old data. Historically INVERTED ≈ 91% and NORMAL ≈ 81%
across the full table, so inversion has been a clear net win cumulatively.

**Recent (latest 200) — leading indicator from post_run_report:**
```json
"latest_200_inversion": {
  "NORMAL":    {"n": 132, "accuracy": 93.2},
  "INVERTED":  {"n":  68, "accuracy": 83.8}
}
```
This window is what the tuner should weight most heavily because it
reflects current behavior. The cumulative "inverted is better" pattern is
slow to flip — by the time it does, you've missed the turning point.

**The asymmetric signal:** if `latest_200_inversion` shows NORMAL > INVERTED
but cumulative still shows INVERTED > NORMAL, the inversion logic is **starting
to underperform**. That's the early warning — act on the recent window, not
the cumulative one. Don't wait for the cumulative to flip before tuning.

Check both. If inverted direction accuracy < raw accuracy in **either** view,
inversion thresholds need attention — but recent-window inversion lagging is
the faster signal.

### 5. Regime Accuracy
```sql
SELECT 
  regime, direction,
  COUNT(*) as n,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions 
WHERE correct IS NOT NULL AND regime IS NOT NULL
GROUP BY regime, direction;
```
Compare regime vs momentum_state accuracy — which is more predictive?

## Improvement Triggers

| Problem | Threshold | Action |
|---------|-----------|--------|
| Any direction×state combo | accuracy < 35% on n≥20 | Flag for inversion tuning |
| Inversion making things worse | `latest_200_inversion` shows NORMAL > INVERTED by ≥5pt on n≥50 each | Tighten the inversion threshold (raise the cut) for that direction×state combo |
| Per-token accuracy | <35% on n≥30 | Add token-specific override |
| Prompt failing | overall < 38% for 3 consecutive hours | Rewrite few-shot examples |
| Regime more predictive than momentum_state | regime_acc > momentum_acc by 10%+ | Swap regime/momentum_state in prompt |

## Implementation Rules
1. Only change `decide_inversion()` thresholds or prompt few-shot examples
2. Log all changes to `/root/.hermes/logs/candle-tuner.log`
3. If accuracy improves by >5% after change → commit with descriptive message
4. Never make more than 2 changes per run (reduce risk)
5. If a change makes accuracy WORSE → revert immediately and log as failed

## Files Modified
- `/root/.hermes/scripts/candle_predictor.py` — the only file this agent touches

## Operational Guide
See `references/running-predictor.md` for how to actually invoke the script
(fg vs bg, runtime expectations, output format, skip reasons, accuracy baselines).
The tuner analyzes and fixes; that doc covers running.

**Wall-time pitfall — concurrent load skews runs longer.** The 20-22m envelope
for 15m mode assumes Ollama is dedicated. When signals_runner and/or
price_collector are running in parallel, observed wall time stretches to
25-27 min — Ollama is shared, so per-token inference slows under contention.
Observed: 26m13s for the 2026-07-14 10:03 cron 15m run while signals_runner
was active. That's still well below the "hung" thresholds in
`references/running-predictor.md` → "Verifying It's Not Hung" — active
`→ TOKEN:` lines every ~30s, `wchan=futex_wait_queue`, Ollama responsive.
Don't kill a 25-27 min run on wall time alone. Plan for 6-9 wait chunks
(180s each) instead of 6-8 when concurrent load is likely.

**Healthy observation (15m cron run, 2026-07-15 03:36, this session) — single
session, two consecutive runs (03:30 killed, 03:36 completed cleanly):**
The agent received a one-shot cron instruction and ran the literal command
`python3 /root/.hermes/scripts/candle_predictor.py --nowandb --interval=15`
verbatim, but switched to `terminal(background=True, ...)` from the start. The
wrapper returned `exit_code: 0` within ~100ms (background wrapper subprocess,
not the script — see `hermes-agent-diagnostic` → "Pitfall 3 — `background=True`
exit code is the wrapper, not the script") and the agent briefly mistook this
for the script having finished. Verified liveness via `ps -p <pid> -o stat,etime`
(STAT=Ssl, ELAPSED growing) and `tail /var/log/candle-predictor.log` (script
still in "Fetching HL market data" phase). Polled via `process(action="wait")`
in 180s chunks (5 chunks total: 180+180+180+180+~120s) until `status: "exited",
exit_code: 0` at 03:55:00. Run: 03:36:16 → 03:55:00 (~18m44s, mid-envelope,
no concurrent Ollama load observed). 117 predicted / 39 inverted / 0 errors
/ db_total=117 matching log exactly. Persistent skip list unchanged (9
low-acc + 5 no-data, no new joins). Init reported `Overall accuracy:
68544/79930 = 85.8%`, `Inverted: 32967/36284 = 90.9%` — flat with prior
runs (cumulative stats trend is the steady 85.8% / 90.9% pair). Direction
split UP-skew continues (UP 114 / DOWN 3 — extreme, 4th consecutive
run under this regime). **Use this as the reference for "cron prompt gives
the literal command, but agent runs it in background + polls session_id
+ tail-appends the log instead of trusting the early wrapper exit_code".**
The full Step 1–4 cron workflow above was followed: preflight (lock clear,
Ollama active), background launch, 5× `wait` chunks, post-run cross-check.
The only deviation was running in background from the first try (not
foreground-then-recover), so no stale lock was generated.

**Three Ollama failure modes to distinguish** (full taxonomy in
`references/running-predictor.md` → "Ollama Failure Modes"):
1. **Transient timeout** — single `Read timed out (read timeout=30)`,
   Ollama stays `active` same PID, predictor's internal retry succeeds
   within ~20s. Recover.
2. **Auto-recovery bounce** — paired errors (`RemoteDisconnected` followed
   by `Connection refused`) in back-to-back log lines, Ollama goes
   briefly `inactive (dead)` then systemd `Restart=on-failure` respawns
   it (verify via `systemctl show ollama -p ExecMainStartTimestamp` —
   it advances during the gap), ~30s-3 min for model reload, predictor
   resumes. First observed 2026-07-14 21:16:26 — let it finish.
3. **Full crash** — Ollama stays `inactive (dead)` with no auto-respawn,
   predictor spins forever in retry loop. Kill job → rm lock → restart
   ollama → re-run.

**Misclassifying bounce as crash wastes ~22 minutes of LLM inference.**
The paired-errors signature (RemoteDisconnected immediately followed by
Connection refused) is the trigger to check `ExecMainStartTimestamp`
first, NOT to start the kill-restart sequence.

**If a previous run was killed/timed out and left a stale `/tmp/candle-predictor.lock`,
the next run will silently hang on lock acquisition until it also times out.**
The lock file contains the previous (now-dead) PID. Verify with
`pgrep -af candle_predictor` — if no matching process exists, the lock is
orphaned: `rm /tmp/candle-predictor.lock` and re-run. See
`references/running-predictor.md` → "Stale Lock From Killed Run" for the
diagnostic sequence (this is the same Pattern A as `/tmp/hermes-pipeline.lock`).

**The `candle_time` column in `predictions.db` is hardcoded to `prediction_time + 14400`
(4h) regardless of `--interval`.** Surfaced 2026-07-15 02:52: every one of
117 new 15m-mode rows had `candle_time - prediction_time = 14400` instead
of 900. The model uses the correct 15m OHLCV features for inference, but
the persisted `candle_time` points to the next 4h candle boundary — any
downstream accuracy check that uses `candle_time` to identify which candle
to resolve against will silently flip correct/wrong for every 15m-mode
prediction. Two patch options documented in
`references/running-predictor.md` → "predictions.db Schema" → "candle_time
is hardcoded to..." — flagged for T, do NOT self-patch (live script,
surgical fix required per trading rules).

## Post-Run Report (deterministic probe)

After any candle_predictor run, invoke `scripts/post_run_report.py` to get a
single JSON snapshot of the just-completed run. It parses the log boundary,
cross-checks `predictions.db` row count + direction split against the
script's own `=== Predicted N tokens, M inverted ===` summary, and reports
accuracy windows (50/200/500/1000), latest-200 direction×inversion split,
and a 200-vs-previous-200 trend.

```bash
python3 /root/.hermes/skills/trading/candle-predictor-tuner/scripts/post_run_report.py --pretty
```

Useful for the tuner before deciding on a change (gives a fresh baseline)
and for cron jobs that just ran the predictor and want a one-shot report
to relay in delivery. Safe to run while the predictor is mid-flight — it
just picks the last "Candle Predictor Starting" header seen.

**Healthy observation (15m run, 2026-07-13):** log=117 predicted / 34 inverted,
db_total=117, all-time overall 85.7%, latest-200 83.5% (up from 58.5% in
the previous 200). The latest-200 direction split often shows UP-skew
(currently 112/117 = 95.7% UP) — that is normal output, not a bug, but
DOWN sample sizes under that skew make DOWN accuracy noisy. When DOWN
accuracy dips below 50% with n≥15, that's a real inversion-tuning signal.

**Healthy observation (15m run, 2026-07-14 06:06, this session):**
log=117 / inverted=35 / errors=0 / wall=20m10s (06:06:23 → 06:26:33, exit 0).
Init reported `Overall accuracy: 67497/78760 = 85.7%`,
`Inverted: 32670/35915 = 91.0%`. Per-token LLM latency ran ~10-25s — the
slightly slower end of normal, well within the documented "<2 min variance"
bound. Skipped 7 tokens for low accuracy (INIT 15%/53, PURR 23%/730,
SNX 24%/102 + persistent list) and 5 for "no price data" (BAT, THETA, VET,
YFI, INIT-double-flag). STRK was the lone DOWN inversion this round
(UP-in-bullish dropped to 39.0% on n=59); everything else inverted to UP
because DOWN-in-bearish/neutral is empirically 20-35% per
REGIME_DOWN_ACCURACY. UP-skew direction split continues to dominate output.
No action — matches prior healthy runs exactly. Useful as a comparison
baseline against future runs that deviate.

**Healthy observation (15m cron run, 2026-07-14 10:03, this session):**
log=117 / inverted=35 / errors=0 / wall=26m13s (10:03:45 → 10:29:58, exit 0).
Init reported `Overall accuracy: 67606/78880 = 85.7%`,
`Inverted: 32707/35958 = 91.0%`. Wall time 4 min over the documented
20-22m envelope — concurrent with signals_runner pulling on Ollama (see
reference running-predictor.md for the concurrent-load note). DB row count
matched script summary exactly (117/117), no inversion-tracking side-effect
rows this round. Trend_200_blocks: latest 91.5% vs previous 89.5% (+2.0pt).
Latest-200 direction: UP 193 @ 94.8%, DOWN 7 @ 0.0% (n too small to act on).
Same persistent skip list (9 low-acc + 5 no-data, no new tokens). No action —
healthy baseline, just slower than envelope due to system load. Useful
baseline for any 15m run that hits 25+ min wall time: match this run's
behavior (still healthy) before escalating.

**Healthy observation (15m cron run, 2026-07-14 11:10, this session):**
log=117 / inverted=36 / errors=0 / wall=22m21s (10:48:29 → 11:10:50, exit 0),
isolated run (no concurrent Ollama load — signals_runner quiet). Init reported
`Overall accuracy: 67633/78910 = 85.7%`, `Inverted: 32711/35964 = 91.0%`.
Direction split: UP 113 / DOWN 4 (96.6% UP-skew — 4th consecutive confirmed
healthy run under this regime). Same persistent skip list (9 low-acc + 5 no-data,
no new tokens). **First observed instance of the cumulative↔recent divergence
flagged in Step 4**: cumulative INVERTED 91.0% > NORMAL 81.3% (still healthy
historically), but `latest_200_inversion` shows NORMAL 93.2% (n=132) >
INVERTED 83.8% (n=68) — a 9.4pt NORMAL lead in the recent window that
contradicts the cumulative picture. Borderline trigger per the Improvement
Triggers table (≥5pt NORMAL > INVERTED on n≥50 each — met on the INVERTED
side, but n=68 INVERTED is still small enough that one good batch of
inversions could flip it back). Direction split `latest_200_direction`:
UP 93.8% (192), DOWN 0.0% (8) — DOWN sample too small to act on. Trend
200: latest 90.0% vs previous 91.0% (−1.0pt, stable — not a regression).
No action this round — watch the next 2 runs to see whether the recent-window
NORMAL>INVERTED persists. Useful as the first documented instance of the
"cumulative still healthy but recent window flipping" pattern, which is
exactly the early-warning signal Step 4 is designed to catch.

**Healthy observation (15m cron run, 2026-07-14 15:30, this session):**
log=117 / inverted=39 / errors=0 / wall=26m01s (15:30:41 → 15:56:42, exit 0),
isolated run (no concurrent Ollama load observed — signals_runner quiet during
predict loop). Init reported `Overall accuracy: 67844/79150 = 85.7%`,
`Inverted: 32773/36041 = 90.9%`. **Inverted count climbed 35→36→39 across
three consecutive runs — INVERTED sample is widening.** Step 4 trigger
threshold NOW fully satisfied across two consecutive runs: latest_200_inversion
NORMAL 91.1% (n=135) vs INVERTED 81.5% (n=65) — 9.6pt NORMAL lead with both
sides n≥50. Compared to the 11:10 run (9.4pt gap on n=132/68), the gap is
slightly wider AND INVERTED n grew from 68→65 is essentially flat while the
gap held — meaning it's not a "small-sample noise" story anymore, it's a
durable 9-10pt drift. **This is the point where the tuner should take action
on the next hourly cycle**: tighten the inversion cut for the lagging
direction×state combos (per the Improvement Triggers table, ≥5pt NORMAL >
INVERTED on n≥50 each → tighten inversion thresholds). Cumulative INVERTED
91.0% > NORMAL 81.3% is still "inversion has been a net win historically"
but the recent-window picture has flipped — this is exactly the
cumulative↔recent divergence Step 4 is designed to catch, now persisting
across ≥2 consecutive runs. Trend_200_blocks: latest 88.0% vs previous 89.5%
(−1.5pt, mild regression — not yet at the >10pt regression threshold but
worth watching). Latest-200 direction: UP 90.7% (194), DOWN 0.0% (6) — DOWN
sample still below n≥15 so no action from direction split, but the
"essentially zero DOWN accuracy on n=6–8 across three consecutive runs"
pattern is the third data point in a row and worth flagging. Persistent
skip list unchanged: 9 low-acc (ETH, ETHFI, INIT, KFLOKI, MATIC, MEME, MKR,
PURR, SNX) + 5 no-data (BAT, KAVA, THETA, VET, YFI), no new joins. No
code change this run (this was a data-collection run) — but it sets up the
next hourly tuner cycle to ACT on the inversion-threshold tightening
trigger without waiting another run.

**Important: when Step 4 trigger is satisfied for ≥2 consecutive runs, act
on the next cycle, don't wait for a third.** Past pattern observed: the
11:10 run noted "watch the next 2 runs" and this 15:30 run is the second
data point — the third should be action, not another observation. The
cumulative-inverted-is-better picture is slow to flip, so when the recent
window shows a sustained NORMAL > INVERTED lead, the historical-narrative
support for keeping current thresholds is gone.

**Healthy observation (15m cron run, 2026-07-14 16:00, this session):**
log=117 / inverted=37 / errors=0 / wall=27m19s (16:00:55 → 16:28:14, exit 0).
Init reported `Overall accuracy: 67870/79180 = 85.7%`,
`Inverted: 32782/36052 = 90.9%`. **Fourth consecutive 15m run confirming
the NORMAL>INVERTED recent-window divergence first flagged at 11:10.**
Step 4 trigger now satisfied four runs in a row: latest_200_inversion
shows NORMAL 90.5% (n=137) > INVERTED 81.0% (n=63), a 9.5pt gap. INVERTED
sample size has grown across all four points (68 → 65 → 63) — the gap
holding with a stable or growing INVERTED n is the durable-signal signature.
DB: 117 rows persisted, matching log exactly (no inversion-tracking
side-effect variance this round). Trend_200_blocks: latest 87.5% vs
previous 90.5% (−3.0pt — still well below the >10pt regression threshold
but the trend is now consistently negative across 4 runs:
−1.0pt → −1.5pt → −3.0pt). Latest-200 direction: UP 89.7% (n=195),
DOWN 0.0% (n=5) — DOWN sample still below n≥15. Persistent skip list
unchanged. **Action drift observation**: this is the 4th consecutive
"no action — watch next run" data point since the trigger first fired
at the 11:10 run. The SKILL.md guidance says "act on the next cycle,
don't wait for a third" (after the 15:30 run) — but the next cycle
(this 16:00 run) collected more data rather than tightening the
inversion thresholds. The trigger threshold per the table
(≥5pt NORMAL > INVERTED on n≥50 each) has been met for **3 of the last
3 runs**. The next hourly cycle MUST take action (tighten inversion
thresholds), not just observe. If the 16:00 run cannot act because
the trigger logic is gated on a different path, that's a bug to fix.
No code change this run — data-collection only, but the
act-on-next-cycle rule is overdue.

**Healthy observation (15m cron run, 2026-07-14 20:00, this session):**
log=117 / inverted=36 / errors=0 / wall=~24m30s (20:00:48 → 20:25:18, exit 0).
Init reported `Overall accuracy: 67923/79240 = 85.7%`,
`Inverted: 32800/36074 = 90.9%`. **5th consecutive 15m run confirming
the NORMAL>INVERTED recent-window divergence** — and the gap widened
further: latest_200_inversion NORMAL 92.5% (n=134) vs INVERTED 80.3%
(n=66), a **12.2pt NORMAL lead**. This is the widest gap observed
since the trigger first fired at 11:10 (timeline: 9.4pt → 9.6pt →
9.5pt → **12.2pt**). INVERTED n held at 66 (up from 63), so this is
sample-size-resilient — not noise. DB: 117/117 match, persistent skip
list unchanged (9 low-acc + 5 no-data), direction split
UP 114 / DOWN 3 (extreme UP-skew). Trend_200_blocks: latest 88.5% vs
previous 88.0% (+0.5pt — slight improvement, breaking the recent
−1.0→−1.5→−3.0 downward trend). Cumulative INVERTED 90.9% still >
NORMAL 81.3% (historical cushion intact), but the recent-window
NORMAL>INVERTED gap is now substantially above the 5pt trigger
threshold for 5 consecutive runs with the INVERTED sample size well
above n≥50. The downgrade-strategy decision is now overdue: either
the next hourly cycle tightens inversion thresholds, or the tuner
needs to acknowledge the cumulative window is no longer a sufficient
reason to keep current thresholds. No code change this run
(data-collection run, same as the prior three). This entry serves
as the freshest baseline for the inversion-gap widening — any future
run that reverses the trend (NORMAL < INVERTED in latest_200) is a
regime change worth investigating immediately.

**Healthy observation (15m cron run, 2026-07-14 21:00, this session) —
Ollama auto-recovery bounce, captured for the first time:**
log=115 / inverted=37 / errors=2 / wall=~24m04s (21:00:45 → 21:24:49, exit 0).
Init reported `Overall accuracy: 67977/79300 = 85.7%`,
`Inverted: 32818/36096 = 90.9%`. **First documented Auto-Recovery Bounce
event** in this reference doc: at 21:16:26 a single paired error
(`RemoteDisconnected` immediately followed by `Connection refused`)
appeared mid-loop. Ollama went briefly `inactive (dead)` and systemd
auto-respawned it (`ExecMainStartTimestamp=Tue 2026-07-14 21:16:27 UTC`,
journal shows `Stopped` → `Started` in succession). Predictor's next
retry succeeded once the new Ollama instance warmed up; first
`POST /api/generate` 200 response at 21:19:10 (after ~3 min model
reload — OpenCoder 1.5B context). Run resumed cleanly through ZEN/ZORA
to completion. DB: 115/115 match (zero data loss). Trend_200_blocks:
latest 87.5% vs previous 88.5% (−1.0pt, stable). Latest-200 direction:
UP 89.3% (n=196), DOWN 0.0% (n=4 — tiny sample). Persistent skip list
unchanged (9 low-acc + 5 no-data). Cumulative INVERTED 90.9% > NORMAL
81.3% still healthy; recent-window NORMAL 91.5% (n=130) vs INVERTED
80.0% (n=70) — 11.5pt NORMAL lead, 6th consecutive run with this
divergence, gap consistent with the 12.2pt peak last hour so not a
new expansion. No code change. **Useful as the canonical Auto-Recovery
Bounce baseline**: when you see paired errors mid-run, check
`systemctl show ollama -p ExecMainStartTimestamp` and `journalctl -u ollama`
for a recent `Stopped`/`Started` pair before assuming it's a full
crash. See `references/running-predictor.md` → "Ollama Failure Modes"
for the full three-mode taxonomy and diagnostic checklist.

**Healthy observation (15m cron run, 2026-07-14 22:00, this session):**
log=117 / inverted=37 / errors=0 / wall=~24m58s (22:00:45 → 22:25:43, exit 0).
Init reported `Overall accuracy: 68032/79360 = 85.7%`,
`Inverted: 32833/36114 = 90.9%`. **7th consecutive 15m run confirming the
NORMAL>INVERTED recent-window divergence** (timeline: 9.4pt → 9.6pt →
9.5pt → 12.2pt → 11.5pt → **10.1pt**). Latest-200_inversion: NORMAL 93.9%
(n=132) vs INVERTED 83.8% (n=68) — gap is consistent with the 9-12pt band
observed since 11:10, INVERTED sample size held at n=68 (stable — durable
signal, not noise). Cumulative INVERTED 90.9% > NORMAL 81.3% still the
historical cushion picture; recent-window flip persists. DB: 117/117
match — log summary and DB total align exactly with no inversion-tracking
side-effect variance. Trend_200_blocks: **latest 90.5% vs previous 87.5%
(+3.0pt)** — a clear positive swing that reverses the recent negative
trend (−1.0pt → −1.5pt → −3.0pt → +3.0pt). This is the first
non-negative swing in 4 runs and a useful fresh baseline: if the next
run drops by ≥5pt from this 90.5% point, that's a regression signal.
Latest-200 direction: UP 91.9% (n=197), DOWN 0.0% (n=3) — DOWN sample
still far below n≥15, no action from direction split. Persistent skip
list unchanged (9 low-acc: ETH, ETHFI, INIT, KFLOKI, MATIC, MEME, MKR,
PURR, SNX + 5 no-data: BAT, KAVA, THETA, VET, YFI). Direction split
direction split UP 114 / DOWN 3 (extreme UP-skew — 5th+ consecutive run under this
regime). No code change — same data-collection posture as the prior
three runs, but the positive trend swing is the first sign the inversion
divergence may be approaching equilibrium rather than expanding. Useful
as the freshness baseline for the "trend_200_blocks positive swing"
pattern: any future run where trend_200 is again negative by ≥5pt from
the 90.5% point set here is a regression worth investigating.

**Healthy observation (15m cron run, 2026-07-15 01:12, this session):**
log=117 / inverted=37 / errors=0 / wall=~19m55s (01:12:49 → 01:32:50, exit 0).
Init reported `Overall accuracy: 68328/79690 = 85.7%`,
`Inverted: 32913/36214 = 90.9%`. **8th consecutive 15m run confirming
the NORMAL>INVERTED recent-window divergence** (timeline extension:
9.4pt → 9.6pt → 9.5pt → 12.2pt → 11.5pt → 10.1pt → **?** — post_run_report
not run this cycle, gap not measured directly, but cumulative INVERTED
90.9% / NORMAL 81.3% spread intact). Init resolved-prediction counts
moved up by exactly +30 from the 22:00 baseline (67633 → 68328 on overall,
32711 → 32913 on inverted) — consistent with 30 newly-resolved predictions
in the 3h gap between runs, no anomalous delta. Persistent skip list
unchanged: 2 no-data tokens skipped (VET, YFI — both long-standing gaps
in `signals_hermes.db`, same as prior runs); the 9-token low-accuracy skip
list was applied inside the predict loop without explicit WARN logs this
round (script may suppress WARN for tokens already in the persistent
skip list). Direction split UP-skew continues to dominate output — every
kept prediction landed UP at conf=55, with 31.6% (37/117) inverted from
underlying DOWN signals (DOWN-in-neutral/bearish accuracy empirically
0%–38% per REGIME_DOWN_ACCURACY thresholds). Wall time 19m55s is at
the **fast end of the 20-22m envelope** (no concurrent Ollama load
observed — signals_runner quiet). DB total not measured this run
(post_run_report not invoked), but log_total=117 matches the script's
own `=== Predicted 117 tokens, 37 inverted ===` summary exactly.
No code change — same data-collection posture as the prior four runs.
**Use this entry as the freshness baseline for "post-midnight cron,
quiet system load, healthy baseline":** the 19m55s wall time and
+30 resolved predictions are both within normal expectations. Any
future run with a larger-than-expected jump in resolved-prediction
counts (e.g. +60 instead of +30) suggests a backlog flush, which
would warrant checking for previously-missed validation runs.

**Healthy observation (15m cron run, 2026-07-15 02:23, this session) — first
foreground-timeout → stale-lock → recovery → clean-background completion in one session:**
log=117 / inverted=38 / errors=0 / wall=~17m37s (02:23:30 → 02:41:07, exit 0).
Init reported `Overall accuracy: 68435/79810 = 85.7%`,
`Inverted: 32938/36248 = 90.9%`. **This run validated the full recovery
recipe end-to-end in a single session.** The agent first tried
`terminal(foreground=True)` (default 300s timeout) — got `exit_code: 124`
exactly as predicted in `references/running-predictor.md` →
"Distinguishing a killed-by-timeout run from a clean-exit run". The
foreground kill left `/tmp/candle-predictor.lock` orphaned (verified
empty `pgrep -af candle_predictor` output, lock still present). The
agent then ran the documented stale-lock recovery (`rm /tmp/candle-predictor.lock`),
relaunched with `terminal(background=True, timeout=900, notify_on_complete=True)`,
and polled the returned `session_id` via `process(action="wait")` chunks
of 180s (matching the documented `wait` clamps-at-180s note) until
`status: "exited", exit_code: 0`. The run completed in 17m37s — **fast end
of envelope**, no concurrent Ollama load. Persistent skip list unchanged
(9 low-acc + 5 no-data). DB row count for this run alone = 117 (matching
log_total exactly); the broader DB saw +153 rows this session because
the aborted foreground run had managed to commit 36 predictions between
its `0G` start (02:16:41) and its `DYM` kill point (02:20:26) before
SIGKILL at the 300s mark — confirming the **partial-commit hazard
documented in `references/running-predictor.md` → "Batch write, not
streaming"**: predictions written before the kill stuck, everything
after the kill was lost. So `db_total > log_total` for the SESSION
even though `db_total == log_total` for the successful background
re-run alone. That's expected behavior, not a regression. **Use this
as the canonical reference run for the "foreground timeout happens,
follow the documented recovery, complete cleanly" sequence** — the
predictions.db invariants (117/117 match for the clean run; +36 from
the partial-commit pre-kill portion) and the lock-recovery procedure
both behaved exactly as the docs predicted.

**Healthy observation (15m cron run, 2026-07-15 01:54, this session):**
log=117 / inverted=36 / errors=0 / wall=13m52s (01:54:59 → 02:08:51, exit 0).
Init reported `Overall accuracy: 68328/79690 = 85.7%`,
`Inverted: 32913/36214 = 90.9%`. **Fast run — well under the 20-22m envelope**
(no concurrent Ollama load — signals_runner quiet during the predict loop).
Persistent skip list unchanged: 9 low-acc (ETH, ETHFI, INIT, KFLOKI, MATIC,
MEME, MKR, PURR, SNX) + 5 no-data (BAT, KAVA, THETA, VET, YFI). DB total
matched log exactly: 117/117, zero inversion-tracking side-effect rows this
round (current production behavior — see `references/running-predictor.md`
→ "Expecting log_total == db_total" pitfall for the early-run note). All 36
inversions were DOWN→UP flips (DOWN in neutral/bearish is empirically 0-38%
per REGIME_DOWN_ACCURACY). Confidence=55 across all predictions (uniform —
calibration is a separate workstream). Direction split: extreme UP-skew
continues (every kept prediction UP — by inversion, not raw LLM output).
Trend_200_blocks not measured this cycle (post_run_report not invoked), but
cumulative INVERTED 90.9% > NORMAL 81.3% spread intact, and resolved-count
delta from the 01:12 baseline is within normal range (no anomalous
backlog flush). **Use this as the fast-end wall-time baseline** — wall
time below ~15 min does NOT indicate a model improvement, it's just an
unloaded-Ollama run. Useful as the freshness baseline for "quiet system
load, no concurrent signals_runner, all skips persistent, healthy run".

**Healthy observation (15m cron run, 2026-07-15 02:23, this session) — end-to-end
validation of the foreground-timeout → stale-lock → background recovery sequence:**
The agent first tried `terminal(foreground=True)` against the predictor and
hit `exit_code: 124` at the 300s mark (exactly as "Distinguishing a
killed-by-timeout run from a clean-exit run" above predicts). The kill
left `/tmp/candle-predictor.lock` orphaned — `pgrep -af candle_predictor`
returned empty (lock holder dead), lock file still present. Recovery
followed the "Stale Lock From Killed Run" recipe verbatim: `rm
/tmp/candle-predictor.lock`, relaunch with
`terminal(background=True, timeout=900, notify_on_complete=True)`, then
poll the returned `session_id` via `process(action="wait")` chunks of 180s
(matching the "wait clamps at 180s regardless of timeout parameter" note
in `references/running-predictor.md` → "Runtime Expectations") until
`status: "exited", exit_code: 0`. Final run: 02:23:30 → 02:41:07
(~17m37s, fast end of envelope, no concurrent Ollama load). Persistent
skip list unchanged (9 low-acc + 5 no-data). Clean re-run:
log=117 / inverted=38 / errors=0, db_total=117 (clean match). The aborted
foreground run had already committed 36 predictions between its `0G`
start (02:16:41) and its `DYM` kill point (02:20:26) before SIGKILL —
**confirming the "Batch write, not streaming" hazard in this document**:
predictions written before the kill stuck, everything after the kill
was lost. So db_total for the SESSION (153) is greater than db_total for
the clean re-run alone (117), but db_total == log_total for the clean
re-run holds. That's expected behavior, not a regression. **Use this
as the canonical end-to-end test of the documented recovery recipe.**
If the recovery ever fails to behave this way, this entry is the
exact-spec reference for what success looks like.

**Healthy observation (15m cron run, 2026-07-15 02:52, this session) — first
agent-driven 15m run of the day + new bug discovery:**
log=117 / inverted=39 / errors=0 / wall=21m19s (02:52:13 → 03:13:32, exit 0).
Init reported `Overall accuracy: 68490/79870 = 85.8%`, `Inverted: 32952/36265
= 90.9%`. Persistent skip list unchanged (9 low-acc + 5 no-data, no new
joins). Direction split UP 113 / DOWN 4 (extreme UP-skew continues). All
39 inversions were DOWN→UP flips (DOWN-in-neutral/bearish is empirically
0-38% per REGIME_DOWN_ACCURACY); only 2 native DOWN predictions survived
(ATOM, BERA — both above the keep threshold for their regime). DB row
count matched log exactly (117/117, zero inversion-tracking side-effect
variance this round). Trend_200_blocks not measured (post_run_report not
invoked) but cumulative INVERTED 90.9% > NORMAL 81.3% spread intact —
recent-window NORMAL>INVERTED divergence continues per the 8-run streak
documented in `references/running-predictor.md` → "Healthy observation
(15m cron run, 2026-07-15 02:23)". **First surfaced bug**: verified
candle_time is hardcoded to `prediction_time + 14400` (4h) regardless of
`--interval` — every one of the 117 new rows has the 4h delta, not the
expected 15m delta. The model uses the correct 15m OHLCV features for
inference (log says "15m candles", predictions reflect 15m-aggregated
prices), but the persisted `candle_time` points to the next 4h boundary.
This means any downstream accuracy check that uses `candle_time` to
identify which candle to resolve against will silently flip correct/
wrong for every 15m-mode prediction. Two patch options documented
in the reference doc; flagged for T (live script, surgical fix
required per trading rules). **Use this as the reference for "agent
cron received the task, ran in foreground by mistake, hit the documented
timeout, recovered, and completed cleanly"** — and the first run that
established the candle_time bug as a 117-row-confirmed pattern (not a
one-off row anomaly). No code change this run — bug found, not fixed.

**Healthy observation (15m cron run, 2026-07-14 23
Writes to `/root/.hermes/logs/candle-tuner.log`:
```
[HH:MM:SS] ANALYSIS: n=XXXX overall_acc=XX.X% worst=XXXX (XX.X%)
[HH:MM:SS] CHANGE: [description of what was changed]
[HH:MM:SS] RESULT: [was it committed/reverted]
```