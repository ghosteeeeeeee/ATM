import time, sqlite3, json, openai

time.sleep(10)

conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("""
    SELECT token, direction, signal_type, confidence, source, created_at, compact_rounds, survival_score
    FROM signals
    WHERE decision IN ('PENDING', 'APPROVED') AND executed = 0 AND created_at > datetime('now', '-3 hours')
    ORDER BY confidence DESC LIMIT 60
""")
rows = [dict(r) for r in c.fetchall()]
seen = {}
for r in rows:
    key = f"{r['token']}:{r['direction']}"
    if key not in seen:
        seen[key] = r
deduped = list(seen.values())
conn.close()

lines = [f"[{i}] {r['token']} | {r['direction']} | conf={r['confidence']:.0f}% | age={r['created_at'][-8:]}" for i, r in enumerate(deduped)]
signals_text = "\n".join(lines)

with open('/var/www/hermes/data/hotset.json') as f:
    hs = json.load(f)
hot_tokens = [f"{s['token']}({s['direction'][0]},{s['confidence']:.0f}%)" for s in hs['hotset']]
hotset_str = ", ".join(hot_tokens)

BLACKLIST_SHORT = "SUI FET SPX ARK TON ONDO CRV RUNE AR NXPC DASH ARB TRUMP LDO NEAR APT CELO SEI ACE"
prompt = f"""HOT SURVIVORS: {hotset_str}
SIGNALS: {signals_text}
RULES: reject<70, no SHORT on:{BLACKLIST_SHORT}, penalize SHORT vs hot LONG -15%, dedupe, prefer LONG.
OUT: TOKEN DIR CONF REASON (max 20 lines)"""

with open('/root/.hermes/auth.json') as f:
    auth = json.load(f)
client = openai.OpenAI(api_key=auth['credential_pool']['minimax'][0]['access_token'], base_url='https://api.minimax.io/v1')

resp = None
for attempt in range(4):
    try:
        resp = client.chat.completions.create(model="MiniMax-M2", messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=4000)
        raw = resp.choices[0].message.content
        break
    except Exception as e:
        print(f"Attempt {attempt+1} failed: {str(e)[:80]}")
        if attempt < 3:
            time.sleep(10)
        else:
            raw = ""

# Strip thinking block - find the  marker
THINK_END = '\n'
if raw and THINK_END in raw:
    content = raw.split(THINK_END)[-1].strip()
else:
    content = raw.strip() if raw else ""

rt = 0
ot = 0
if resp and hasattr(resp, 'usage') and resp.usage:
    rt = getattr(resp.usage.completion_tokens_details, 'reasoning_tokens', 0) or 0
    ot = resp.usage.completion_tokens - rt

print("=== LLM HOT-SET RANKING ===")
print(content if content else "(empty or failed)")
print(f"\nTotal: {resp.usage.total_tokens if resp and hasattr(resp, 'usage') else 'N/A'} | Reasoning: {rt} | Output: {ot}")

print("\n=== ALGORITHM HOT-SET (current) ===")
for s in hs['hotset']:
    print(f"  {s['token']:8s} {s['direction']:5s} conf={s['confidence']:.1f}% sr={s['survival_round']}")

print("\n=== AGREEMENT ===")
if content:
    algo_tokens = {s['token'] for s in hs['hotset']}
    llm_tokens = set()
    for line in content.split('\n'):
        parts = line.split()
        if parts:
            llm_tokens.add(parts[0])
    print(f"Algorithm: {sorted(algo_tokens)}")
    print(f"LLM:       {sorted(llm_tokens)}")
    print(f"Match:     {algo_tokens == llm_tokens}")
else:
    print("(no LLM output)")