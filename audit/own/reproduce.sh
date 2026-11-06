#!/bin/bash
# Fresh runs of the spec's documented reproduce commands (§7)
set -x
cd /root/.hermes
OUT=/root/.hermes/audit/own/fresh
mkdir -p $OUT
python3 scripts/backtest_atr60_momentum.py --coin BTC --threshold 60 --sweep --split --variants --htf --movesize --entry --fresh --recent > $OUT/round1.txt 2>&1
echo "round1 rc=$?"
python3 scripts/backtest_atr60_momentum.py --pooled --pct 0.076 --tfs 15m > $OUT/pooled_15m.txt 2>&1; echo "pooled rc=$?"
python3 scripts/backtest_atr60_momentum.py --pooled --pct 0.076 --tfs 5m,15m,1h > $OUT/pooled_all.txt 2>&1; echo "pooled_all rc=$?"
python3 scripts/backtest_atr60_momentum.py --pooled --pct 0.076 --tfs 15m --half first > $OUT/pooled_15m_h1.txt 2>&1; echo "h1 rc=$?"
python3 scripts/backtest_atr60_momentum.py --pooled --pct 0.076 --tfs 15m --half second > $OUT/pooled_15m_h2.txt 2>&1; echo "h2 rc=$?"
python3 scripts/backtest_atr60_momentum.py --cont --cont-db recorded > $OUT/cont_recorded.txt 2>&1; echo "cont_rec rc=$?"
python3 scripts/backtest_atr60_momentum.py --cont-flip --cont-db recorded > $OUT/contflip_recorded.txt 2>&1; echo "contflip_rec rc=$?"
python3 scripts/backtest_atr60_momentum.py --cont > $OUT/cont_replay.txt 2>&1; echo "cont_rep rc=$?"
python3 scripts/backtest_atr60_momentum.py --cont-flip > $OUT/contflip_replay.txt 2>&1; echo "contflip_rep rc=$?"
python3 scripts/continuum_replay.py --token BTC --validate > $OUT/replay_validate.txt 2>&1; echo "replay rc=$?"
echo ALL_DONE
