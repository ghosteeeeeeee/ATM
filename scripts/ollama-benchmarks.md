# Ollama Model Benchmarks

**System:** Tokyo, 7.8GB RAM, no GPU, 4.2GB swap active
**Ollama:** localhost:11434

## qwen2.5:1.5b (Q4_K_M, 986MB) — PRODUCTION RECOMMENDED

| Test | Gen time | Total | Throughput |
|------|----------|-------|------------|
| Short (2 tokens) | 0.1s | 4.8s | 20 tok/s |
| Realistic ~100 token output | 7.5s | 16.8s | 13 tok/s |
| Prompt eval (cached) | 2.2s | — | — |
| Prompt eval (cold) | 9s | — | — |
| Stress (5 rapid calls) | 0.06s avg | — | — |

Stability: 5/5 OK under stress.

## qwen2.5:3b (Q4_K_M, 1.9GB) — NOT VIABLE

| Test | Result |
|------|--------|
| Short (2 tokens) | 3s gen, 6.8s total, 0.7 tok/s |
| Realistic ~100 token output | **TIMEOUT at 60s** |

**Problem:** Prompt eval exhausts free RAM, swap kicks in (4.2GB), system hangs.
RAM: ~1.1GB per runner. 3b exceeds available memory for generation on this hardware.
**DO NOT run 3b in production.**

## Ceiling Analysis

- 7b Q4_K_M = 4GB: Would OOM on load
- Better AI options: (1) add 8GB+ RAM, (2) Q2_K 7b (~2.8GB), (3) external API for hard decisions, (4) keep 1.5b + MiniMax for complex cases
- AI decide() prompt: ~336 chars in, ~100 chars out → 1.5b handles at 16s total (7s gen). Acceptable for infrequent runs.

## Runner Management

- Stuck runners: `pkill -9 -f "ollama runner"` then `nohup ollama serve > /tmp/ollama.log 2>&1 &`
- Unload model: `curl -X DELETE localhost:11434/api/generate -d '{"model":"qwen2.5:3b"}'`
- Check memory: `ps aux | grep ollama | grep -v grep` + `free -h`
