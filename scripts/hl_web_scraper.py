#!/usr/bin/env python3
"""
HL Copy Trading - Web Scraper
Uses Agent Reach and web scraping to find top Hyperliquid traders.
"""
import json
import subprocess
import re
import time
from pathlib import Path

def run_command(cmd: str) -> str:
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def scrape_dexly_leaderboard() -> list:
    """Scrape Dexly leaderboard for top traders."""
    print("[scraper] Scraping Dexly leaderboard...")
    
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://dexly.trade/hyperliquid/leaderboard" | grep -oP '0x[0-9a-fA-F]{40}' | sort -u'''
    output = run_command(cmd)
    
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[scraper] Found {len(wallets)} wallets from Dexly")
        return wallets
    
    print(f"[scraper] Dexly scrape failed: {output}")
    return []

def scrape_hyperstats_leaderboard() -> list:
    """Scrape HyperStats leaderboard for top traders."""
    print("[scraper] Scraping HyperStats leaderboard...")
    
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://hyperstats.org/traders" | grep -oP '0x[0-9a-fA-F]{40}' | sort -u'''
    output = run_command(cmd)
    
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[scraper] Found {len(wallets)} wallets from HyperStats")
        return wallets
    
    print(f"[scraper] HyperStats scrape failed: {output}")
    return []

def scrape_beacon_leaderboard() -> list:
    """Scrape Beacon leaderboard for top traders."""
    print("[scraper] Scraping Beacon leaderboard...")
    
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://beacontrade.io/leaderboard" | grep -oP '0x[0-9a-fA-F]{40}' | sort -u'''
    output = run_command(cmd)
    
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[scraper] Found {len(wallets)} wallets from Beacon")
        return wallets
    
    print(f"[scraper] Beacon scrape failed: {output}")
    return []

def scrape_skynetx_leaderboard() -> list:
    """Scrape SkynetX leaderboard for top traders."""
    print("[scraper] Scraping SkynetX leaderboard...")
    
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://skynetx.io/hyperliquid/leaderboard" | grep -oP '0x[0-9a-fA-F]{40}' | sort -u'''
    output = run_command(cmd)
    
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[scraper] Found {len(wallets)} wallets from SkynetX")
        return wallets
    
    print(f"[scraper] SkynetX scrape failed: {output}")
    return []

def scrape_liquidwhales_leaderboard() -> list:
    """Scrape LiquidWhales leaderboard for top traders."""
    print("[scraper] Scraping LiquidWhales leaderboard...")
    
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://liquidwhales.com/leaderboard" | grep -oP '0x[0-9a-fA-F]{40}' | sort -u'''
    output = run_command(cmd)
    
    if output and not output.startswith("Error"):
        wallets = output.split('\n')
        print(f"[scraper] Found {len(wallets)} wallets from LiquidWhales")
        return wallets
    
    print(f"[scraper] LiquidWhales scrape failed: {output}")
    return []

def scrape_reddit_hl_traders() -> list:
    """Scrape Reddit for known HL traders."""
    print("[scraper] Scraping Reddit for HL traders...")
    
    # Search for HL trader discussions
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://www.reddit.com/r/hyperliquid/search.json?q=trader+wallet&sort=top&t=month&limit=10"'''
    output = run_command(cmd)
    
    wallets = []
    try:
        data = json.loads(output)
        for post in data.get('data', {}).get('children', []):
            text = post.get('data', {}).get('selftext', '') + post.get('data', {}).get('title', '')
            found = re.findall(r'0x[0-9a-fA-F]{40}', text)
            wallets.extend(found)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    
    print(f"[scraper] Found {len(wallets)} wallets from Reddit")
    return wallets

def scrape_twitter_hl_traders() -> list:
    """Scrape Twitter/X for known HL traders."""
    print("[scraper] Scraping Twitter for HL traders...")
    
    # This would require Agent Reach with Twitter configured
    # For now, return empty
    print("[scraper] Twitter scraping requires Agent Reach configuration")
    return []

def scrape_github_hl_repos() -> list:
    """Scrape GitHub for HL-related repos with wallet addresses."""
    print("[scraper] Scraping GitHub for HL wallets...")
    
    cmd = '''curl -s -H "User-Agent: Mozilla/5.0" "https://api.github.com/search/repositories?q=hyperliquid+trader+wallet&sort=stars&order=desc&per_page=5"'''
    output = run_command(cmd)
    
    wallets = []
    try:
        data = json.loads(output)
        for repo in data.get('items', []):
            # Check README for wallet addresses
            readme_url = f"https://raw.githubusercontent.com/{repo['full_name']}/main/README.md"
            readme_cmd = f'curl -s "{readme_url}"'
            readme = run_command(readme_cmd)
            found = re.findall(r'0x[0-9a-fA-F]{40}', readme)
            wallets.extend(found)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    
    print(f"[scraper] Found {len(wallets)} wallets from GitHub")
    return wallets

def scrape_all_sources() -> list:
    """Scrape all sources for top HL traders."""
    all_wallets = []
    
    # Scrape each source
    sources = [
        ("Dexly", scrape_dexly_leaderboard),
        ("HyperStats", scrape_hyperstats_leaderboard),
        ("Beacon", scrape_beacon_leaderboard),
        ("SkynetX", scrape_skynetx_leaderboard),
        ("LiquidWhales", scrape_liquidwhales_leaderboard),
        ("Reddit", scrape_reddit_hl_traders),
        ("Twitter", scrape_twitter_hl_traders),
        ("GitHub", scrape_github_hl_repos),
    ]
    
    for name, func in sources:
        try:
            wallets = func()
            all_wallets.extend(wallets)
            time.sleep(1)  # Rate limit
        except Exception as e:
            print(f"[scraper] Error scraping {name}: {e}")
    
    # Deduplicate
    unique_wallets = list(set(all_wallets))
    print(f"\n[scraper] Total unique wallets found: {len(unique_wallets)}")
    
    return unique_wallets

def scrape_new_leaderboard_sources() -> list:
    """Scrape NEW leaderboard sources not in the known list."""
    print("[scraper] Searching for new leaderboard sources...")
    
    # Known sources to skip
    known = {'dexly', 'hyperstats', 'beacon', 'liquidwhales', 'skynetx', 'hypercopy'}
    
    # Search for new sources
    cmd = '''curl -s -L -H "User-Agent: Mozilla/5.0" "https://html.duckduckgo.com/html/?q=hyperliquid+leaderboard+top+traders" | grep -oP 'href="(https?://[^"]*)"' | sed 's/href="//' | sort -u'''
    output = run_command(cmd)
    
    new_wallets = []
    if output and not output.startswith("Error"):
        urls = output.split('\n')
        for url in urls[:10]:  # Limit to 10 URLs
            # Check if it's a new leaderboard source
            domain = re.search(r'https?://([^/]+)', url)
            if domain:
                domain = domain.group(1).replace('www.', '').lower()
                if any(k in domain for k in ['hyperliquid', 'leaderboard', 'trader', 'whale']):
                    if domain not in known:
                        print(f"[scraper] Found new source: {domain}")
                        # Try to scrape it
                        try:
                            cmd = f'''curl -s -L -H "User-Agent: Mozilla/5.0" "{url}" | grep -oP '0x[0-9a-fA-F]{{40}}' | sort -u'''
                            result = run_command(cmd)
                            if result and not result.startswith("Error"):
                                wallets = result.split('\n')
                                new_wallets.extend(wallets)
                                print(f"[scraper] Found {len(wallets)} wallets from {domain}")
                        except (subprocess.TimeoutExpired, OSError):
                            pass
    
    return new_wallets

if __name__ == "__main__":
    wallets = scrape_all_sources()
    
    print("\n[scraper] Wallets found:")
    for w in wallets[:20]:
        print(f"  {w}")
