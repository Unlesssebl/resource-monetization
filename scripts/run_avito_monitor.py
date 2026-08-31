#!/usr/bin/env python3
"""
CLI Runner для мониторинга цен Авито с сохранением в DuckDB и аналитикой для agy.
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rmon.services.scraper.avito import AvitoScraper
from rmon.services.scraper.storage import DuckDBStorage
from rmon.services.scraper.analytics import MarketAnalytics

async def main_async(args):
    target_id = args.target_id or f"{args.query.lower().replace(' ', '_')}_{args.city}"

    if not args.stats_only:
        print(f"\n🔍 Запуск сбора объявлений Авито: '{args.query}' [{args.city}]...")
        items = await AvitoScraper.scrape_search(
            query=args.query,
            city=args.city,
            limit=args.limit,
            headless=args.headless
        )
        
        if items:
            DuckDBStorage.save_items(items, target_id=target_id, source="avito")
            print(f"✅ Успешно сохранено в DuckDB: {len(items)} объявлений")
        else:
            print("⚠️ Новых карточек не получено (возможно сработал антифрод или пустая выдача).")

    # Формирование аналитики
    stats = DuckDBStorage.get_market_summary(target_id)
    print("\n" + "="*50)
    print(f"📊 СВОДКА РЫНКА ДЛЯ ТАРГЕТА: [{target_id}]")
    print("="*50)
    print(f"• Всего активных лотов: {stats['total_items']}")
    print(f"• Медианная цена:      {stats['median_price']:,.0f} ₽")
    print(f"• 25-й перцентиль:     {stats['p25_price']:,.0f} ₽ (низ рынка)")
    print(f"• Диапазон цен:        {stats['min_price']:,.0f} ₽ — {stats['max_price']:,.0f} ₽")
    print("="*50)

    # Аномалии
    anomalies = DuckDBStorage.get_anomalies(target_id, discount_threshold_pct=args.threshold)
    if anomalies:
        print(f"\n🔥 ОБНАРУЖЕНЫ АНОМАЛИИ НИЖЕ РЫНКА (дисконт >= {args.threshold}%):")
        for i, a in enumerate(anomalies, 1):
            print(f"  {i}. {a['title'][:35]} -> {a['price_current']:,.0f} ₽ (-{a['discount_from_median_pct']}% от медианы)")
            print(f"     Локация: {a['location']} | Ссылка: {a['url']}")
    else:
        print(f"\nℹ️ Аномалий с дисконтом >= {args.threshold}% не найдено.")

    # Снижения цен
    drops = DuckDBStorage.get_price_drops(target_id)
    if drops:
        print("\n📉 ЗАФИКСИРОВАНЫ СНИЖЕНИЯ ЦЕН ПРОДАВЦАМИ:")
        for d in drops:
            print(f"  • {d['title'][:35]}: {d['prev_price']:,.0f} ₽ -> {d['price_current']:,.0f} ₽ (-{d['drop_pct']}%)")
            print(f"    Ссылка: {d['url']}")

    # Генерация отчета
    md_path, summary = MarketAnalytics.generate_markdown_report(target_id, discount_threshold=args.threshold)
    print(f"\n📄 Отчет сформирован: {md_path}")

def main():
    parser = argparse.ArgumentParser(description="Avito Market Monitor & Intelligence Runner")
    parser.add_argument("--query", default="RTX 3080", help="Поисковый запрос")
    parser.add_argument("--city", default="moskva", help="Город (транслит, например moskva, spb)")
    parser.add_argument("--target-id", default=None, help="Кастомный идентификатор таргета")
    parser.add_argument("--limit", type=int, default=25, help="Лимит позиций для сбора")
    parser.add_argument("--threshold", type=float, default=20.0, help="Порог дисконта для аномалий в процентах (по умолчанию 20)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Запуск с видимым окном браузера")
    parser.add_argument("--stats-only", action="store_true", help="Только расчет аналитики по существующей базе")
    parser.set_defaults(headless=True)

    args = parser.parse_args()
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
