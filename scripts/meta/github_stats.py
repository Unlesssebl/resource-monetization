#!/usr/bin/env python3
"""
GitHub Repository Statistics Fetcher (Lean & Zero-Auth)
Извлекает открытую статистику репозитория: звезды, форки, последний релиз, дату обновления.
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

def parse_repo_arg(arg: str) -> str:
    """Извлекает 'owner/repo' из ссылки или строки."""
    clean = arg.strip().rstrip('/')
    if 'github.com/' in clean:
        parts = clean.split('github.com/')[-1].split('/')
        return f"{parts[0]}/{parts[1]}"
    return clean

def fetch_github_stats(repo: str) -> dict:
    repo_path = parse_repo_arg(repo)
    api_url = f"https://api.github.com/repos/{repo_path}"
    releases_url = f"https://api.github.com/repos/{repo_path}/releases/latest"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Antigravity-Agent/1.0',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    stats = {
        "repo": repo_path,
        "url": f"https://github.com/{repo_path}",
        "queried_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status": "success"
    }
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            stats["name"] = data.get("name")
            stats["description"] = data.get("description")
            stats["stars"] = data.get("stargazers_count", 0)
            stats["forks"] = data.get("forks_count", 0)
            stats["open_issues"] = data.get("open_issues_count", 0)
            stats["language"] = data.get("language")
            stats["license"] = data.get("license", {}).get("spdx_id") if data.get("license") else None
            stats["updated_at"] = data.get("updated_at")
            stats["created_at"] = data.get("created_at")
    except urllib.error.HTTPError as e:
        stats["status"] = f"HTTP Error {e.code}: {e.reason}"
        return stats
    except Exception as e:
        stats["status"] = f"Error: {str(e)}"
        return stats

    # Попытка получить последний релиз
    try:
        req_rel = urllib.request.Request(releases_url, headers=headers)
        with urllib.request.urlopen(req_rel, timeout=10) as resp:
            rel_data = json.loads(resp.read().decode('utf-8'))
            stats["latest_release"] = {
                "tag": rel_data.get("tag_name"),
                "name": rel_data.get("name"),
                "published_at": rel_data.get("published_at")
            }
    except Exception:
        stats["latest_release"] = None
        
    return stats

def main():
    if len(sys.argv) < 2:
        print("Использование: python github_stats.py <owner/repo или URL>")
        print("Пример: python github_stats.py rclone/rclone")
        sys.exit(1)
        
    target = sys.argv[1]
    result = fetch_github_stats(target)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
