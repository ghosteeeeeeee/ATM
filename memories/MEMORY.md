Memory (Index): > Quick reference. Details in linked files. > Keep under 4KB. Session details in daily logs.
§
Memory (Index): ---
§
Memory (Index) > Quick Access Files: [USER.md](./USER.md) - Your preferences
§
Memory (Index) > Quick Access Files: [trading.md](./trading.md) - Trading system & rules
§
Memory (Index) > Quick Access Files: [brain.md](./brain.md) - Brain system docs
§
Memory (Index) > Quick Access Files: [lessons.md](./lessons.md) - Hard lessons learned
§
Memory (Index) > Quick Access Files: [ideas.md](./ideas.md) - New ideas by category
§
Memory (Index) > Quick Access Files: [majorissues.md](./majorissues.md) - Known issues
§
Memory (Index) > Quick Access Files: [SHORTCUTS.md](./SHORTCUTS.md) - Chat shortcuts (/team, /sc, /hb, etc)
§
Memory (Index) > Quick Access Files: [subagents.md](./subagents.md) - AI sub-agent team
§
Memory (Index) > Quick Access Files: [memory/](./memory/) - Daily logs
§
Memory (Index): **Security:** Never expose ports publicly (localhost only)
§
Memory (Index): **Trading:** Focus ONLY on Tokyo trades
§
Memory (Index): **Backup:** Commit to git (/root/.hermes), backup to Dallas, leave note for Ro
§
Memory (Index) > Git Repo: /root/.hermes — Hermes Trading System (git commit 93f34fe)
§
Memory (Index) > DB Architecture:
  Static: /root/.hermes/data/signals_hermes.db (price_history, latest_prices, regime_log)
  Runtime: /root/.hermes/data/signals_hermes_runtime.db (signals, decisions, momentum_cache, token_intel, cooldown_tracker)
  Seed: /root/.hermes/seed/signals_hermes.sql (177K rows, 41d × 229 tokens, auto-imports on init_db)
§
Memory (Index) > Tools: **memory_search** - Search daily logs
§
Memory (Index) > Tools: **brain queries** - Query brain database
§
Memory (Index) > Tools: **lcm_grep** - Search conversation history
§
Memory (Index) > Tools: **lcm_expand_query** - Deep recall from compacted context
§
Memory (Index) > Tools: **youtube-watcher skill** - For watching YouTube videos (use skill, not web_fetch)
§
Memory (Index) > To Watch: [OpenClaw Doesn't Work Until You Do This](https://www.youtube.com/watch?v=VwHjR0xxJ1M) - Critical setup requirements
§
Memory (Index) > Security: Wallet keys: See brain (topic: wallet-security)