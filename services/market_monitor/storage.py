from datetime import datetime, timezone
import duckdb
from shared.config import settings
from shared.logger import get_logger

logger = get_logger("MarketStorage")

class MarketDB:
    @staticmethod
    def get_connection():
        return duckdb.connect(str(settings.DUCKDB_PATH))

    @classmethod
    def init_db(cls):
        conn = cls.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                scraped_at TIMESTAMP,
                source VARCHAR,
                item_id VARCHAR,
                title VARCHAR,
                brand VARCHAR,
                price_current DOUBLE,
                price_original DOUBLE,
                discount_pct INTEGER,
                rating DOUBLE,
                feedbacks_count INTEGER,
                in_stock BOOLEAN,
                url VARCHAR
            )
        """)
        conn.close()

    @classmethod
    def save_items(cls, items: list[dict]):
        if not items:
            return
        cls.init_db()
        conn = cls.get_connection()
        now = datetime.now(timezone.utc)

        for item in items:
            conn.execute("""
                INSERT INTO price_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                item.get("source", "wb"),
                str(item.get("id")),
                item.get("title", ""),
                item.get("brand", ""),
                float(item.get("price_current", 0)),
                float(item.get("price_original", 0)),
                int(item.get("discount_pct", 0)),
                float(item.get("rating", 0.0)),
                int(item.get("feedbacks_count", 0)),
                bool(item.get("in_stock", True)),
                item.get("url", "")
            ))
        conn.close()
        logger.info(f"Сохранено в DuckDB: {len(items)} записей")