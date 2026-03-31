Memory (Index): > Quick access: [USER.md] prefs | [trading.md] system | [ollama-benchmarks.md] model benchmarks | [lessons.md] lessons | See brain (topic: wallet-security)
§
Memory (Index) > Ollama: qwen2.5:1.5b production recommended | 3b hangs system | benchmarks in scripts/ollama-benchmarks.md | Runner fix: pkill -9 -f "ollama runner"
§
Memory (Index) > Git: /root/.hermes | Commits: 54c9e41 | DB: signals_hermes.db (243K rows) + signals_hermes_runtime.db
§
Memory (Index) > Tools: **memory_search** | **brain queries** | **lcm_grep** | youtube-watcher skill
§
Live trading: hype_live_trading.json ON | mirror_open fix: hyperliquid_exchange.py missing `import sys` | signal combining: merge same token+direction signals
Signal study pipeline: OpenClaw writes to /root/.openclaw/workspace/data/signals.db (NOT Hermes runtime DB). Use ATTACH DATABASE in signal_schema.get_confluence_signals() to query both DBs together. OpenClaw sources: mtf-macd-bullish, mtf-macd+momentum+rsi, mtf-rsi-oversold/overbought, etc. Hermes sources: rsi-confluence, macd-confluence, momentum (source starts with mtf- in Hermes too for multi-timeframe signals).
Study winning combos: /root/.hermes/scripts/study_winning_combos.py runs 4x/day (02,08,14,20 UTC). Logs to logs/study_winning_combos.log + logs/study_history.log. Analyzes closed trades in brain.trades, links to signals via token+direction+time.
Guardian LIVE now: hl-sync-guardian.py runs with --apply flag for LIVE mode (closes orphan HL positions). Default DRY=False. 8 orphan trades (BERA,STX,POPCAT,ORDI,SAND,INJ,0G,POLYX) closed by HL SL/TP at 17:27 on 2026-03-31 — none recorded in brain.trades (guardian was DRY at that time).
§
Memory (Index) > Security: Never expose ports publicly | Wallet keys: See brain (topic: wallet-security)
§
Memory (Index): > 2026-03-29 FIXES: hype-sync was blind to HL positions (pm_get_open defaults wrong server), signal_schema decays confidence now not just boosts, hyperliquid_exchange missing import sys

Memory (Index): > Ollama 3b tests DONE - benchmarks in scripts/ollama-benchmarks.md | DO NOT use 3b (hangs system)