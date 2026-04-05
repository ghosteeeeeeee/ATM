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
```sql
SELECT 
  was_inverted,
  direction,
  COUNT(*) as total,
  SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END)*100.0/COUNT(*) as accuracy
FROM predictions WHERE correct IS NOT NULL
GROUP BY was_inverted, direction;
```
Check if inversions are actually helping. If inverted direction accuracy < raw accuracy, the inversion is making things worse.

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
| Inversion making things worse | inverted_acc < raw_acc | Disable that inversion |
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

## Output
Writes to `/root/.hermes/logs/candle-tuner.log`:
```
[HH:MM:SS] ANALYSIS: n=XXXX overall_acc=XX.X% worst=XXXX (XX.X%)
[HH:MM:SS] CHANGE: [description of what was changed]
[HH:MM:SS] RESULT: [was it committed/reverted]
```