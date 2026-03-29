#!/usr/bin/env python3
"""
Free Model Hunter - Find and benchmark best free OpenRouter models daily
"""
import requests
import time
import json
import os
from datetime import datetime
from pathlib import Path

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
STATS_FILE = Path("/root/shared_notes/free-model-stats.md")
CONFIG_FILE = Path.home() / ".openclaw" / "openclaw.json"

# Models to bias towards (known good performers)
BIASED_MODELS = [
    "liquid/lfm-2.5-1.2b-instruct",
    "nvidia/nemotron-3-nano-30b-a3b",
    "google/gemma-3-4b-it",
]

# Quick test prompts
TEST_PROMPTS = [
    "Say hi in 3 words",
    "What is 2+2?",
]

def get_free_models():
    """Get list of free models from OpenRouter"""
    resp = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        timeout=30
    )
    models = resp.json().get("data", [])
    free = [m["id"] for m in models if ":free" in m.get("id", "").lower() 
             and "vision" not in m.get("id", "").lower()
             and "image" not in m.get("id", "").lower()]
    return free[:15]  # Test top 15

def test_model(model_id):
    """Quick test a model"""
    start = time.time()
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": TEST_PROMPTS[0]}],
                "max_tokens": 20,
            },
            timeout=20,
        )
        latency = time.time() - start
        if resp.status_code == 200:
            return {"success": True, "latency": round(latency, 2)}
        return {"success": False, "error": resp.status_code, "latency": round(latency, 2)}
    except Exception as e:
        return {"success": False, "error": str(e)[:50], "latency": round(time.time() - start, 2)}

def update_stats(results):
    """Update the stats markdown file"""
    working = [r for r in results if r["success"]]
    working.sort(key=lambda x: x["latency"])
    
    # Apply bias (boost biased models)
    for r in working:
        if any(b in r["model"] for b in BIASED_MODELS):
            r["latency"] = r["latency"] * 0.7  # 30% speed boost for biased
    
    working.sort(key=lambda x: x["latency"])
    best = working[0] if working else None
    
    md = f"""# Free Model Stats

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Today's Rankings

| Rank | Model | Latency | Status |
|------|-------|---------|--------|
"""
    for i, r in enumerate(working, 1):
        bias_note = " ⭐" if any(b in r["model"] for b in BIASED_MODELS) else ""
        md += f"| {i} | {r['model']} | {r['latency']}s | ✅{bias_note} |\n"
    
    md += f"""
## Not Working
"""
    failed = [r for r in results if not r["success"]]
    for r in failed:
        md += f"- {r['model']}: {r.get('error', 'unknown')}\n"
    
    if best:
        md += f"""
## Best Model Today

**{best['model']}** ({best['latency']}s)

To use as fallback:
```
openclaw config set agents.defaults.model.fallbacks '["openrouter/{best['model']}:free"]'
```
"""
    
    STATS_FILE.write_text(md)
    return best

def update_config(best_model):
    """Update OpenClaw config with best model"""
    import json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    else:
        config = {}
    
    if "agents" not in config:
        config["agents"] = {}
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    if "model" not in config["agents"]["defaults"]:
        config["agents"]["defaults"]["model"] = {}
    
    # Handle models that already have :free suffix
    model_for_config = best_model if ":free" in best_model else f"{best_model}:free"
    config["agents"]["defaults"]["model"]["fallbacks"] = [f"openrouter/{model_for_config}"]
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    return True

def main():
    print(f"=== Free Model Hunter === {datetime.now()}")
    
    print("Fetching free models...")
    models = get_free_models()
    print(f"Found {len(models)} free models")
    
    results = []
    for model in models:
        print(f"Testing {model}...", end=" ")
        result = test_model(f"{model}:free")
        results.append({"model": model, **result})
        print(f"{'✅' if result['success'] else '❌'} {result['latency']}s")
        time.sleep(1)  # Rate limit
    
    print("\nUpdating stats...")
    best = update_stats(results)
    
    if best:
        print(f"\nBest: {best['model']} ({best['latency']}s)")
        update_config(best["model"])
        print("Updated OpenClaw config!")
    else:
        print("No working models found!")
    
    return best

if __name__ == "__main__":
    main()
