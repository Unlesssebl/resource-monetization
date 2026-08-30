#!/usr/bin/env python3
import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from rmon.services.scraper.scraper import MarketScraper, ScraperStorage

async def run(query: str, limit: int):
    items = await MarketScraper.scrape(query, limit)
    ScraperStorage.save_items(items)
    csv_p, md_p = ScraperStorage.generate_reports()
    print(f"\n✅ Мониторинг завершен! Отчеты сохранены:")
    print(f"📊 CSV: {csv_p}")
    print(f"📝 MD:  {md_p}")

def main():
    parser = argparse.ArgumentParser(description="Market Scraper Runner")
    parser.add_argument("--query", default="авточехлы", help="Поисковый запрос")
    parser.add_argument("--limit", type=int, default=15, help="Лимит позиций")
    args = parser.parse_args()
    asyncio.run(run(args.query, args.limit))

if __name__ == "__main__":
    main()