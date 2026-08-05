# Signal Debugging Triggers Registry
# This file contains the full trigger list for hermes-signal-debugging SKILL.md
# Add new triggers here, NOT in SKILL.md (100K char limit)

triggers:
  - "stale signals in hot-set after regime change"
  - "phase_accel not appearing in hot-set"
  - "LAYER-type move not detected"
  - "zscore-momentum tuner sweeps 0 tokens"
  - "phase_accel fires every cycle — no cooldown"
  - "accel-300 fires on brief EMA dip then reverses — ME/UNI/CHIP should have been LONG"
  - "signal fires while guardian closing same token"
  - "zscore-pump+ combo loses always"
  - "guardian closing marker not blocking signal"
  - "z=None in trade records despite zscore-pump in sources"
  - "signals not combining"
  - "signals not merging into hot-set"
  - "hot-set only has one signal type"
  - "rs.py fires no signal on support/resistance breach — only bounce detection fires"  # refs: rs-py-logic.md
  - "rs-s-broken SHORT fires in uptrends — bounces=False asymmetry"  # refs: rs-broken-bounces-bug.md
  - "losing SHORT trades with rs-s-broken in uptrend"  # refs: rs-broken-bounces-bug.md
  - "combo_key=None in hotset.json / signals no trade"  # refs: combo-key-null-bug-2026-05-21.md
  - "P0: SIGNAL_SOURCE_BLACKLIST not enforced in decider_run"  # refs: combo-key-null-bug-2026-05-21.md
  - "P2: log() sig mismatch decider_run.py:219/2012"
  - "signal not in hotset despite higher score than visible signals"
  - "all signals skipped — no trade placed — guardian clean exit"
  - "combo_signal flagged in sources but no combo_key in hotset.json"