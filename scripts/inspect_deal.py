#!/usr/bin/env python3
"""
Скрипт глубокой инспекции конкретного объявления Авито:
- Скачивает полное описание, рейтинг продавца, статистику просмотров
- Скачивает все фотографии лота в высоком разрешении в data/deal_photos/{item_id}/
- Готовит структурированный payload для мультимодального анализа агентом AGY
"""
import sys
import json
import asyncio
import argparse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rmon.services.scraper.avito import AvitoScraper
from rmon.services.scraper.storage import DuckDBStorage
from rmon.core.logger import get_logger

from typing import Optional

logger = get_logger("InspectDeal")

async def inspect(url: Optional[str] = None, top_anomaly: bool = False, target: str = "rtx_3080_moskva"):
    if not url and top_anomaly:
        anomalies = DuckDBStorage.get_anomalies(target, discount_threshold_pct=20.0)
        if not anomalies:
            print(f"❌ В базе данных нет аномалий по таргету [{target}]. Сначала запустите сбор.")
            return
        url = anomalies[0]["url"]
        print(f"🎯 Выбрана топ-аномалия из базы: {anomalies[0]['title']} ({anomalies[0]['price_current']:,.0f} ₽)")

    if not url:
        print("❌ Укажите URL объявления (--url) или флаг --top-anomaly.")
        return

    print(f"\n🔍 Запуск глубокого сбора карточки: {url}...")
    details = await AvitoScraper.get_listing_details(url=url, download_photos=True, headless=True)

    print("\n" + "="*60)
    print(f"📦 ЛОТ: {details.get('title') or 'Без названия'}")
    print(f"💰 Цена: {details.get('price', 0):,.0f} ₽")
    print(f"📍 Локация: {details.get('location')}")
    print(f"👤 Продавец: {details.get('seller_name')} (★ {details.get('seller_rating', 0)} | {details.get('seller_reviews', 0)} отзывов)")
    print(f"👁️ Просмотры: {details.get('views')} | Опубликовано: {details.get('date_posted')}")
    print("="*60)
    print(f"📝 ОПИСАНИЕ ПРОДАВЦА:")
    print(details.get('description') or 'Описание отсутствует.')
    print("="*60)
    
    photos = details.get('local_photos', [])
    print(f"📸 СКАЧАНО ФОТОГРАФИЙ ({len(photos)} шт.):")
    for idx, p in enumerate(photos, 1):
        print(f"  [{idx}] {p}")
    print("="*60)

    # Сохраняем JSON-метаданные рядом с фото
    if photos:
        meta_file = Path(photos[0]).parent / "details.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(details, f, ensure_ascii=False, indent=2)
        print(f"💾 Метаданные сохранены в: {meta_file}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Avito Listing Inspector")
    parser.add_argument("--url", help="Direct URL to Avito listing")
    parser.add_argument("--top-anomaly", action="store_true", help="Inspect top anomaly from DuckDB")
    parser.add_argument("--target", default="rtx_3080_moskva", help="Target ID for top anomaly")
    args = parser.parse_args()

    asyncio.run(inspect(url=args.url, top_anomaly=args.top_anomaly, target=args.target))
