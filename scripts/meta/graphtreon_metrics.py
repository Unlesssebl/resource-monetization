#!/usr/bin/env python3
"""
Crowdfunding & Creator Benchmark Extractor (Lean & Zero-Auth)
Извлекает открытую информацию о подписчиках и доходах авторов (Patreon/Graphtreon).
"""

import sys
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone

def fetch_creator_metrics(creator_name: str) -> dict:
    clean_name = creator_name.strip().lower().replace(" ", "")
    graphtreon_url = f"https://graphtreon.com/creator/{clean_name}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    result = {
        "creator": creator_name,
        "graphtreon_url": graphtreon_url,
        "queried_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status": "success",
        "patrons": None,
        "monthly_earnings": None,
        "rank": None
    }
    
    try:
        req = urllib.request.Request(graphtreon_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
            # Поиск количества патронов
            patron_match = re.search(r'([\d,]+)\s+patrons', html, re.IGNORECASE)
            if patron_match:
                result["patrons"] = int(patron_match.group(1).replace(",", ""))
                
            # Поиск ежемесячного дохода
            earnings_match = re.search(r'\$([\d,]+)\s+per month', html, re.IGNORECASE)
            if earnings_match:
                result["monthly_earnings"] = f"${earnings_match.group(1)}"
                
            # Поиск ранга
            rank_match = re.search(r'Ranked\s+#?([\d,]+)', html, re.IGNORECASE)
            if rank_match:
                result["rank"] = rank_match.group(1)
                
    except urllib.error.HTTPError as e:
        result["status"] = f"HTTP {e.code}"
    except Exception as e:
        result["status"] = f"Error: {str(e)}"
        
    return result

def main():
    if len(sys.argv) < 2:
        print("Использование: python graphtreon_metrics.py <creator_name>")
        print("Пример: python graphtreon_metrics.py nolvus")
        sys.exit(1)
        
    creator = sys.argv[1]
    res = fetch_creator_metrics(creator)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
