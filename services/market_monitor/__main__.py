import asyncio
import argparse
from services.market_monitor.scraper import MarketScraper
from services.market_monitor.storage import MarketDB
from services.market_monitor.reporter import MarketReporter

async def run_market_service(query: str, limit: int):
    items = await MarketScraper.scrape(query, limit)
    MarketDB.save_items(items)
    csv_p, md_p = MarketReporter.build_reports()
    print(f"\n✅ Мониторинг завершен! Отчеты сохранены:\n• CSV: {csv_p}\n• MD:  {md_p}")

def main():
    parser = argparse.ArgumentParser(description="Market Monitor Microservice CLI")
    parser.add_argument("--query", default="авточехлы", help="Поисковый запрос")
    parser.add_argument("--limit", type=int, default=15, help="Лимит позиций")
    args = parser.parse_args()
    asyncio.run(run_market_service(args.query, args.limit))

if __name__ == "__main__":
    main()