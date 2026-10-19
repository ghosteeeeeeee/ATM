# Current State — brain_auditor Run Oct 19 04:45 UTC

**Last Updated: 2026-10-19 04:45 UTC**
**Updated by: brain_auditor — 1 bugfix (precheck CONF argv), 0 live config changes**

## PIPELINE STATUS (04:45 UTC)

- **Trading LIVE** with 0.3x size-reduce (7d WR 34.0% < 37 AND 7d PnL −$3.91 < $0 — both resume conditions still failing). Resume ~Oct 23.
- **24h 14T 6W −$0.17 (42.9%). | since last audit (Oct 18 07:45): 10T 5W $0.00. | 7d 197T 67W −$3.91 (34.0%). | 30d 750T 43.9% −$4.19.**
- **0 open.** Regime: SHORT_BIAS (66/127 tokens), NORMAL vol, BTC trend_quality STRONG_DOWN, above 1m EMA300 floor.
- Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor

**BUGFIX: ai_trader_precheck.py CONF argv** — `__main__` never parsed CONF; SHORT regime gate always false-failed "conf unknown". Now parses argv[3]. Zero live-trading behavior.

**DUAL-CONDITION TAT OOS = FAIL** (last-run creative killed): bb-bounce-v2 30d candle, T=55/MFE<0.20/live<−0.20 → 4 fires net −$0.06, 2 FK. Fails pre-reg bar. Single-condition shadow stays collecting; flip path closed.

**CEO triage:**
- pump-chain- blanket-kill **REJECT** (14d wash +$0.05, 30d −$1.10 weak, 7 EXTREME winners, combo +$0.51)
- hl_copy NORMAL block **HOLD** (n=6 < 10)
- remove pump-chain- midband exemption **REJECT** (45-50 band 30d +$0.39)

## WEALTH GAP (7d) — UNCHANGED

| Family | Trades | WR | PnL |
|--------|--------|-----|-----|
| TRAIL/PROFIT | ~59 | ~90% | **+$5.84** |
| CHOP/SL (hard_max_loss+atr_sl) | 121 | 3.3% | −$9.44 |

## LOSING PATTERN (24h)

Trend-continuation won (BTC continuum-trend+ ×2, ME ai-trader+ trail). Bounce/chop lost (ETC/BANANA bb-bounce, IO pump-chain+ timeout). BTC SHORT #16273 squeezed −5.36% at EMA300 floor; manual LONG 7min later +4.31%.

## ACTIVE SHADOWS

- ai-trader+ EXTREME LONG conf-demote — n=14 < 20, collecting
- pp-conditional penalty floor — 51 would-blocks since Oct 18 (pp<0.10)
- MFE-CUT / bb-bounce TAT / contrarian PROMOTE — collecting (contrarian pump-chain- span 4.8d < 14d gate)
- RR-engine would-blocks — ~10/hr

## NEXT

- Oct 23 resume-day CEO eyeball: 12+ unvalidated changes land together
- hl_copy NORMAL recheck at n≥10
- contrarian pump-chain- PROMOTE re-eval ~Oct 29 (14d span)
- ai-trader+ EXTREME re-eval when n≥20
