# Bugs to Fix

## Price data freshness — max 120s stale
**Reported:** 2026-05-16
**Severity:** High
**Check:** `smoke_test.py` → `price_data_fresh` — currently allows 180s max age before flagging fail.
**Problem:** Prices were 207s stale. Trading requires fresher data for accurate signal generation and trade execution. 120s should be the hard limit.
**Fix:** In `smoke_test.py` `check_price_data_fresh()`, change `max_age_sec=180` → `max_age_sec=120`. Also check price_collector service is running and cycling every minute.
**Status:** Pending

---

## Pipeline flapping check threshold too low
**Reported:** 2026-05-16
**Severity:** Low (false alarm)
**Check:** `smoke_test.py` → `no_flapping`
**Problem:** The check flags when cycles > 55 per 60min. But a normally-running 1-per-minute pipeline produces exactly 60 cycles. So a healthy pipeline always fails this check. Not actual flapping — the threshold is wrong.
**Fix:** Change `> 55` threshold to `> 65` (allow 5 min slack for occasional slow cycles). Also add a crash/restart counter as distinct from normal cycle count — currently the check conflates "many cycles" with "flapping."
**Status:** Pending