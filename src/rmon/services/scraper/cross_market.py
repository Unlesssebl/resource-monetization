import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from rmon.core.logger import get_logger
from rmon.services.scraper.avito import AvitoScraper
from rmon.services.scraper.scraper import MarketScraper
from rmon.services.scraper.storage import DuckDBStorage

logger = get_logger("CrossMarketArbitrage")

class CrossMarketArbitrage:
    """Движок кросс-маркет арбитража цен между Авито и маркетплейсами (Wildberries / Ozon)"""

    @classmethod
    async def scan_cross_market(
        cls,
        query: str,
        city: str = "moskva",
        avito_limit: int = 15,
        wb_limit: int = 10,
        target_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Одновременный параллельный сбор цен с Авито и Wildberries,
        сохранение в единый DuckDB Data Lake и расчет арбитражного спреда.
        """
        tid = target_id or f"{query.lower().replace(' ', '_')}_{city}"
        logger.info(f"Запуск кросс-маркет сканирования: query='{query}', city='{city}', target_id='{tid}'")

        # Параллельный запуск парсеров
        avito_task = AvitoScraper.scrape_search(query=query, city=city, limit=avito_limit, headless=True)
        wb_task = MarketScraper.scrape(query=query, limit=wb_limit)

        avito_items, wb_items = await asyncio.gather(avito_task, wb_task, return_exceptions=True)

        if isinstance(avito_items, Exception):
            logger.error(f"Ошибка сбора Авито: {avito_items}")
            avito_items = []
        if isinstance(wb_items, Exception):
            logger.error(f"Ошибка сбора WB: {wb_items}")
            wb_items = []

        # Сохранение в единую базу DuckDB
        if avito_items:
            DuckDBStorage.save_items(avito_items, target_id=tid, source="avito")
        if wb_items:
            # Преобразуем формат WB под общий DuckDBStorage
            formatted_wb = []
            for w in wb_items:
                formatted_wb.append({
                    "id": str(w.get("id")),
                    "title": w.get("title", ""),
                    "price_current": float(w.get("price_current", 0)),
                    "price_original": float(w.get("price_original", 0)),
                    "location": "Wildberries Marketplace",
                    "seller": w.get("brand", "WB Seller"),
                    "rating": float(w.get("rating", 0.0)),
                    "url": w.get("url", ""),
                    "image_url": ""
                })
            DuckDBStorage.save_items(formatted_wb, target_id=tid, source="wb")

        # Расчет арбитражного спреда через DuckDB
        spread_data = cls.calculate_spread(tid)
        return spread_data

    @classmethod
    def calculate_spread(cls, target_id: str) -> Dict[str, Any]:
        """
        Расчет дельты цен: сравниваем медиану нового товара (WB) с дисконтными лотами на Авито.
        """
        conn = DuckDBStorage.get_connection()
        
        # Получаем статистику отдельно по каждому источнику
        query_stats = """
            SELECT 
                source,
                count(*) as count,
                coalesce(median(price_current), 0) as median_price,
                coalesce(min(price_current), 0) as min_price,
                coalesce(max(price_current), 0) as max_price
            FROM price_history
            WHERE target_id = ? AND price_current > 100
            GROUP BY source
        """
        sources_df = conn.execute(query_stats, [target_id]).df()
        
        # Поиск арбитражных связок (лоты на Авито, которые значительно дешевле медианы WB)
        query_arbitrage = """
            WITH wb_stat AS (
                SELECT median(price_current) as wb_median
                FROM price_history
                WHERE target_id = ? AND source = 'wb' AND price_current > 100
            ),
            avito_deals AS (
                SELECT *
                FROM price_history
                WHERE target_id = ? AND source = 'avito' AND price_current > 100
            )
            SELECT 
                a.item_id,
                a.title as avito_title,
                a.price_current as avito_price,
                w.wb_median,
                round(w.wb_median - a.price_current, 0) as raw_spread_rub,
                round(((w.wb_median - a.price_current) / w.wb_median) * 100, 1) as spread_pct,
                a.location,
                a.seller,
                a.url as avito_url
            FROM avito_deals a, wb_stat w
            WHERE w.wb_median > 0 AND a.price_current <= w.wb_median * 0.75
            ORDER BY spread_pct DESC
        """
        deals_df = conn.execute(query_arbitrage, [target_id, target_id]).df()
        conn.close()

        sources_summary = {}
        for _, row in sources_df.iterrows():
            sources_summary[row["source"]] = {
                "count": int(row["count"]),
                "median": float(row["median_price"]),
                "min": float(row["min_price"]),
                "max": float(row["max_price"])
            }

        deals = deals_df.to_dict(orient="records")

        return {
            "target_id": target_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": sources_summary,
            "arbitrage_deals_count": len(deals),
            "deals": deals
        }
