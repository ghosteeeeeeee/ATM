# Decision Request: "Follow the Giants' Light" — resolve the mirror's blind spots

**User directive (verbatim):** *"please resolve this we literally have people
shining giants light to get us in the right direction, we literally just have
to follow their lead"*

**Ask:** Give a complete verdict on the four fixes below PLUS the freshness-gate
policy tension, so we can implement immediately. The standing principle: the
system's only job is to get us INTO the positions the pro traders are showing us.

---

## The complaint (from the user, with their leaderboard snapshot)

They watched a Top-uPnL leaderboard snapshot close profits in front of their eyes
(DQh8×3 +$2.5k positions, 5cFc×6, AuT8, 5d3L, 5SfD, Dohj, 2WYs, CkNE, D5m6...)
and asked: **why aren't we in these positions?**

## Investigation results (verified against signals DB + mirror log + live feed)

### Layer 1 — We WERE emitting; signals die in the approval gauntlet
Last 3h: **42 mirror signals → 1 EXECUTED.** The snapshot wallets' emissions
(multiple per wallet, conf 62-88, clusters up to ×9) died as:

| Kill reason | Count | Mechanism |
|---|---|---|
| `combo_key stale` churn | 15 | Re-mirror every 3min → row expires before surviving 2 compaction cycles → approval clock never completes |
| `expired: token on blacklist` | 9 | Pre-b40baeb2 casualties (compactor's 6 sites — NOW FIXED) |
| `compaction_stale_10min` | 8 | Didn't survive 2 cycles in time |
| `rep-low-reputation` | 4+ | coin_shame 0.30× multiplies conf 66-88 → ~20-25% → below 50 floor |
| `long-midband`, `rr-engine-hard-block` | 4 | entry-quality gates (confirmed: #1696213, #1697797) |

Direct examples:
- `#1697791 5SfD SOL LONG conf=88 → EXPIRED: rep-low-reputation`
- `#1697797 DQh8 BTC LONG conf=82 → EXPIRED: long-midband`
- `#1696213 CkNE SOL LONG conf=85 → EXPIRED: rr-engine-hard-block`

**The rep-gate is now the #1 binding constraint for LONG mirror signals** —
the cluster bonus (+15 cap) and conf cap (88) cannot survive a 0.30×
multiplication.

### Layer 2 — Freshness gate vs the snapshot itself (POLICY CONFLICT)
The snapshot's winners are MULTI-HOUR holders. Live feed right now:
DQh8 BTC longs **289min old**, 5cFc SOL longs **211-271min**, CkNE 246min —
all `seen + attempts=5` (terminal). **157 STALE SKIPs today** — any position
first seen after 10min of holding never fires.

The user's own rule ("older than 5-10 mins is useless", implemented earlier
today) structurally forbids mirroring exactly the big holds they now want to
be in. Freshness and "follow the giants" are in direct conflict for
hour-long positions.

### Layer 3 — Tracking gaps
- **Dohj and 4mYM dropped off the tracked list**: sidebar label resolution
  requires the wallet to be in the LIVE positions feed; when they close, the
  label can't resolve → next 10-min scrape loses them entirely until they reopen.
- **STALE SKIP log lines carry no wallet label** — 157 today, zero
  attributable to a trader (same auditability gap bug_hunter flagged for
  BLOCKED lines).

## Proposed fixes (need your verdict on each)

1. **Rep-gate exemption for `jup_yolo_mirrored`** — Option-D pattern: route
   through `directional_block`-style central check or a source carve-out so
   coin_shame 0.30× doesn't multiply our mirror signals below the floor.
   This is currently the #1 execution blocker for LONGs.
2. **Kill the re-mirror churn** — only re-mirror when the previous death was
   at an EXEC gate (vol storm, max positions), NOT at approval gates
   (rep/midband/rr/compaction) — those re-emissions just restart the
   approval clock 15×/3h and guarantee each row dies again. Alternative:
   lengthen REEMIT beyond compaction cadence. Pick a mechanism.
3. **Sticky sidebar wallets** — merge previously-resolved wallets into the
   leaderboard file (keep resolved entries alive for e.g. 24h) instead of
   full-replace, so Dohj/4mYM-style churn stops.
4. **Label STALE SKIP + give-up log lines with wallet label + pid** — makes
   the next investigation possible.

## The policy question (Layer 2) — choose ONE

- **(a) Keep 10-min strict** — we only catch fresh entries; hour-long holds
  are structurally out. Matches the letter of the earlier directive.
- **(b) Freshness from position-open only when wallet was tracked at open**
  — e.g. tracked-at-open: allow up to 60min (they entered while we watched,
  we just missed the window); newly-tracked mid-hold: keep 10min.
- **(c) Full override** — drop/raise the gate significantly for tracked
  wallets (e.g. 60min for everyone) — re-opens the stale-entry problem the
  gate was built to kill (the pre-fix losses were exactly late entries).

Recommend ONE with reasoning. Note: trades opened in the last hours post-fix
showed 89% WR on the fresh-entry batch — the gate correlates with the
improvement we've measured.

## Constraints

- Protected flags in `hermes_constants.py` — your verdict authorizes edits
  for this session (same as Option D).
- All gate changes must go through the central helpers where they exist
  (`directional_block` pattern) to avoid zombie signals — bug_hunter found
  6 unpatched compactor sites that turned Option D's first attempt into
  churn (commit b40baeb2).
- Anything you decide gets implemented immediately, then bug_hunter
  verification per repo rules.

## Fresh numbers

- Mirror: 42 signals/3h → 1 EXECUTED; trades #16592 SOL +0.90%,
  #16593 HYPE +3.68%, #16594 SOL open +0.54% (22:00-23:30)
- Freshness: 157 STALE SKIP lines today; all snapshot positions att=5 terminal
- Tracked: 72 wallets; Dohj/4mYM absent
- Overall mirror PnL since inception: 26 trades, 58% WR, −$0.48, with the
  post-fix batch at 89% (8W/1L)
