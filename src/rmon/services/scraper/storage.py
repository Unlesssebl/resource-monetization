"""
Storage adapter and facade for Avito/Marketplace Scrapers.
Делегирует операции в единое ядро DataLake (rmon.core.lake),
сохраняя полную обратную совместимость для существующих сервисов.
"""
from typing import List, Dict, Any, Optional
from rmon.core.lake import DataLake
from rmon.core.logger import get_logger

logger = get_logger("ScraperStorage")


class DuckDBStorage:
    """Фасад хранилища DuckDB для обратной совместимости с модулями скрейпера"""

    @staticmethod
    def get_connection():
        return DataLake.get_connection()

    @classmethod
    def init_db(cls):
        conn = DataLake.get_connection()
        conn.close()

    @classmethod
    def save_items(cls, items: List[Dict[str, Any]], target_id: str = "default", source: str = "avito") -> int:
        """Сохранение партии объявлений через единый DataLake"""
        return DataLake.save_items(items=items, target_id=target_id, source=source)

    @classmethod
    def get_market_summary(cls, target_id: Optional[str] = None) -> Dict[str, Any]:
        """Получение агрегированных рыночных метрик"""
        if not target_id:
            return {
                "total_items": 0, "min_price": 0, "max_price": 0,
                "avg_price": 0, "median_price": 0, "p25_price": 0, "p75_price": 0
            }
        summary = DataLake.get_market_summary(target_id)
        if not summary:
            return {
                "total_items": 0, "min_price": 0, "max_price": 0,
                "avg_price": 0, "median_price": 0, "p25_price": 0, "p75_price": 0
            }
        return {
            "total_items": summary.get("total_items", 0),
            "min_price": summary.get("min_price", 0.0),
            "max_price": summary.get("max_price", 0.0),
            "avg_price": summary.get("median_price", 0.0),
            "median_price": summary.get("median_price", 0.0),
            "p25_price": summary.get("p25_price", 0.0),
            "p75_price": summary.get("p75_price", 0.0)
        }

    @classmethod
    def get_anomalies(cls, target_id: Optional[str] = None, discount_threshold_pct: float = 20.0) -> List[Dict[str, Any]]:
        """Поиск аномалий с дисконтом ниже рынка"""
        if not target_id:
            return []
        return DataLake.get_anomalies(target_id=target_id, discount_threshold_pct=discount_threshold_pct)

    @classmethod
    def get_price_drops(cls, target_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Поиск объявлений со снижением цены"""
        return DataLake.get_price_drops(target_id=target_id)
