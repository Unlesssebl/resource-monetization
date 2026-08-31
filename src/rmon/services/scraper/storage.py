import duckdb
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("ScraperStorage")

class DuckDBStorage:
    """Универсальное аналитическое хранилище на DuckDB для мониторинга цен (Авито, WB и др.)"""

    @staticmethod
    def get_connection():
        return duckdb.connect(str(settings.DUCKDB_PATH))

    @classmethod
    def init_db(cls):
        """Инициализация схемы таблиц"""
        conn = cls.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                scraped_at TIMESTAMP,
                source VARCHAR,
                target_id VARCHAR,
                item_id VARCHAR,
                title VARCHAR,
                price_current DOUBLE,
                price_original DOUBLE,
                location VARCHAR,
                seller VARCHAR,
                rating DOUBLE,
                url VARCHAR,
                image_url VARCHAR
            );
            CREATE INDEX IF NOT EXISTS idx_target_item ON price_history(target_id, item_id);
            CREATE INDEX IF NOT EXISTS idx_scraped_at ON price_history(scraped_at);
        """)
        conn.close()

    @classmethod
    def save_items(cls, items: list[dict], target_id: str = "default", source: str = "avito"):
        """Сохранение партии объявлений с временной меткой"""
        if not items:
            return
        cls.init_db()
        conn = cls.get_connection()
        now = datetime.now(timezone.utc)

        for it in items:
            conn.execute("""
                INSERT INTO price_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                source,
                target_id,
                str(it.get("id", "")),
                str(it.get("title", "")),
                float(it.get("price_current", 0.0)),
                float(it.get("price_original", 0.0) or it.get("price_current", 0.0)),
                str(it.get("location", "")),
                str(it.get("seller", "")),
                float(it.get("rating", 0.0) or 0.0),
                str(it.get("url", "")),
                str(it.get("image_url", ""))
            ))
        conn.close()
        logger.info(f"Сохранено в DuckDB [{source}:{target_id}]: {len(items)} записей")

    @classmethod
    def get_market_summary(cls, target_id: Optional[str] = None) -> dict:
        """Расчет робастных аналитических метрик (Медиана, IQR, Мин, Макс, Кол-во)"""
        cls.init_db()
        conn = cls.get_connection()

        where_clause = "WHERE target_id = ?" if target_id else ""
        params = [target_id] if target_id else []

        query = f"""
            WITH latest_items AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                FROM price_history
                {where_clause}
            )
            SELECT
                count(*) as total_items,
                coalesce(min(price_current), 0) as min_price,
                coalesce(max(price_current), 0) as max_price,
                coalesce(avg(price_current), 0) as avg_price,
                coalesce(median(price_current), 0) as median_price,
                coalesce(quantile_cont(price_current, 0.25), 0) as p25_price,
                coalesce(quantile_cont(price_current, 0.75), 0) as p75_price
            FROM latest_items
            WHERE rn = 1 AND price_current > 100
        """
        row = conn.execute(query, params).fetchone()
        conn.close()

        if not row or row[0] == 0:
            return {"total_items": 0, "min_price": 0, "max_price": 0, "avg_price": 0, "median_price": 0, "p25_price": 0, "p75_price": 0}

        return {
            "total_items": row[0],
            "min_price": row[1],
            "max_price": row[2],
            "avg_price": round(row[3], 2),
            "median_price": round(row[4], 2),
            "p25_price": round(row[5], 2),
            "p75_price": round(row[6], 2)
        }

    @classmethod
    def get_anomalies(cls, target_id: Optional[str] = None, discount_threshold_pct: float = 20.0) -> list[dict]:
        """Поиск аномалий ниже рынка (дисконт >= discount_threshold_pct от медианы)"""
        cls.init_db()
        conn = cls.get_connection()

        where_target = "AND target_id = ?" if target_id else ""
        params = [target_id] if target_id else []

        query = f"""
            WITH latest AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                FROM price_history
                WHERE price_current > 100 {where_target}
            ),
            target_medians AS (
                SELECT target_id, median(price_current) as median_price
                FROM latest
                WHERE rn = 1
                GROUP BY target_id
            )
            SELECT l.source, l.target_id, l.item_id, l.title, l.price_current, m.median_price,
                   round(((m.median_price - l.price_current) / m.median_price) * 100, 1) as discount_from_median_pct,
                   l.location, l.seller, l.url, l.scraped_at
            FROM latest l
            JOIN target_medians m ON l.target_id = m.target_id
            WHERE l.rn = 1 AND l.price_current <= m.median_price * (1.0 - (? / 100.0))
            ORDER BY discount_from_median_pct DESC
        """
        params_full = params + [discount_threshold_pct]
        df = conn.execute(query, params_full).df()
        conn.close()
        return df.to_dict(orient="records")

    @classmethod
    def get_price_drops(cls, target_id: Optional[str] = None) -> list[dict]:
        """Поиск объявлений, где продавец снизил цену в последних срезах"""
        cls.init_db()
        conn = cls.get_connection()

        where_target = "WHERE target_id = ?" if target_id else ""
        params = [target_id] if target_id else []

        query = f"""
            WITH history_lag AS (
                SELECT item_id, title, price_current, target_id, url, location, scraped_at,
                       LAG(price_current) OVER (PARTITION BY item_id ORDER BY scraped_at ASC) as prev_price,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                FROM price_history
                {where_target}
            )
            SELECT item_id, title, price_current, prev_price,
                   round(prev_price - price_current, 0) as price_drop_rub,
                   round(((prev_price - price_current) / prev_price) * 100, 1) as drop_pct,
                   target_id, url, location, scraped_at
            FROM history_lag
            WHERE rn = 1 AND prev_price IS NOT NULL AND price_current < prev_price
            ORDER BY drop_pct DESC
        """
        df = conn.execute(query, params).df()
        conn.close()
        return df.to_dict(orient="records")
