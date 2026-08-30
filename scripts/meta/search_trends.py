#!/usr/bin/env python3
"""
Search Demand & Suggestions Extractor (Lean & Zero-Auth)
Опрашивает открытые эндпоинты поисковых систем (Google / Яндекс) для сбора
популярных запросов, поискового спроса и ассоциаций без API-ключей.
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

def fetch_google_suggestions(query: str, lang: str = "ru") -> list:
    """Получает подсказки Google Suggest."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://suggestqueries.google.com/complete/search?client=chrome&hl={lang}&q={encoded_q}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            if isinstance(data, list) and len(data) > 1:
                return data[1] # список подсказок
    except Exception:
        pass
    return []

def fetch_yandex_suggestions(query: str) -> list:
    """Получает подсказки Яндекс Suggest."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://suggest.yandex.ru/suggest-ya.cgi?part={encoded_q}&v=4"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
            data = json.loads(raw)
            if isinstance(data, list) and len(data) > 1:
                return [item for item in data[1] if isinstance(item, str)]
    except Exception:
        pass
    return []

def analyze_search_demand(query: str) -> dict:
    now_utc = datetime.now(timezone.utc)
    
    google_suggs = fetch_google_suggestions(query)
    yandex_suggs = fetch_yandex_suggestions(query)
    
    return {
        "query": query,
        "queried_at": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        "status": "success",
        "total_suggestions_found": len(google_suggs) + len(yandex_suggs),
        "google_suggestions": google_suggs[:10],
        "yandex_suggestions": yandex_suggs[:10]
    }

def main():
    if len(sys.argv) < 2:
        print("Использование: python search_trends.py <поисковый запрос>")
        print("Пример: python search_trends.py 'steam deck сборка'")
        sys.exit(1)
        
    q = " ".join(sys.argv[1:])
    res = analyze_search_demand(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
