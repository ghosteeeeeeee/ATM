## Error Alerts — 2026-08-14 13:40 UTC

- **[WARN]** (1x): `[HYPE Mirror] FAILED — brain.py stderr empty`
- **[WARN]** (1x): `ROLLBACK FAILED: sig#1547142 already claimed by another process`
- **[WARN]** (128x): `Phantom trades — atr_sl_hit with <0.01% PnL`
- **[WARN]** (17x): `Stale prices — 17 tokens >5min without fresh candle`
- **[INFO]**: Disk at 82% — 3% from WARN threshold (85%)
- **[INFO]**: 5 empty DB files (0 bytes): brain.db, hermes.db, hermes_brain.db, hebbian_brain.db, hermes_db.db

## Error Alerts — 2026-08-14 14:09 UTC
- **NEW** (2x): `Aug N N:N:N python3[TOK]: TS   [TOK Mirror] TOK`

## Error Alerts — 2026-08-14 17:41 UTC
- **[WARN]**: Disk at 83% — 2% from WARN threshold (85%). Recommend: `find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;`
- **[WARN]**: Phantom trade — NOT SHORT #13822 closed at exactly 0.00% PnL
