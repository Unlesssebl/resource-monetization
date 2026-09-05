"""
Unified Data Lake & DuckDB Storage Engine for RMon Platform.
Предоставляет высокопроизводительный доступ к данным (OLAP C++),
автоматический расчет перцентилей, медиан и экспорт в Parquet для кластерного обмена.
"""
import duckdb
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("DataLake")

class DataLake:
    """Единое аналитическое хранилище на базе DuckDB и Parquet"""

    @classmethod
    def get_connection(cls) -> duckdb.DuckDBPyConnection:
        db_path = settings.DUCKDB_PATH
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(db_path))
        cls._init_schema(conn)
        return conn

    @classmethod
    def _init_schema(cls, conn: duckdb.DuckDBPyConnection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                item_id VARCHAR,
                target_id VARCHAR,
                source VARCHAR,
                title VARCHAR,
                price_current DOUBLE,
                price_original DOUBLE,
                location VARCHAR,
                seller VARCHAR,
                url VARCHAR,
                image_url VARCHAR,
                scraped_at TIMESTAMP
            );
        """)
        # Ensure new columns exist if migrating from legacy table
        for col, col_type in [
            ("target_id", "VARCHAR"),
            ("location", "VARCHAR"),
            ("seller", "VARCHAR"),
            ("image_url", "VARCHAR"),
        ]:
            try:
                conn.execute(f"ALTER TABLE price_history ADD COLUMN IF NOT EXISTS {col} {col_type};")
            except Exception:
                pass
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON price_history(target_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scraped_at ON price_history(scraped_at);")
        except Exception:
            pass

    @classmethod
    def save_items(cls, items: List[Dict[str, Any]], target_id: str, source: str = "avito") -> int:
        if not items:
            return 0
        now = datetime.now(timezone.utc)
        conn = cls.get_connection()
        try:
            records = [
                (
                    str(it.get("id", "")),
                    target_id,
                    source,
                    str(it.get("title", "")),
                    float(it.get("price_current", 0.0)),
                    float(it.get("price_original", it.get("price_current", 0.0))),
                    str(it.get("location", "")),
                    str(it.get("seller", "")),
                    str(it.get("url", "")),
                    str(it.get("image_url", "")),
                    now
                )
                for it in items if float(it.get("price_current", 0.0)) > 0
            ]
            conn.executemany("""
                INSERT INTO price_history 
                (item_id, target_id, source, title, price_current, price_original, location, seller, url, image_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            logger.info(f"Сохранено в DataLake [{source}:{target_id}]: {len(records)} записей")
            return len(records)
        finally:
            conn.close()

    @classmethod
    def get_market_summary(cls, target_id: str) -> Dict[str, Any]:
        conn = cls.get_connection()
        try:
            query = """
                WITH latest AS (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                    FROM price_history
                    WHERE target_id = ? AND price_current > 100
                )
                SELECT 
                    count(DISTINCT item_id) as total_items,
                    coalesce(median(price_current), 0.0) as median_price,
                    coalesce(quantile_cont(price_current, 0.25), 0.0) as p25_price,
                    coalesce(quantile_cont(price_current, 0.75), 0.0) as p75_price,
                    coalesce(min(price_current), 0.0) as min_price,
                    coalesce(max(price_current), 0.0) as max_price
                FROM latest
                WHERE rn = 1;
            """
            row = conn.execute(query, [target_id]).fetchone()
            if not row:
                return {}
            return {
                "target_id": target_id,
                "total_items": row[0],
                "median_price": row[1],
                "p25_price": row[2],
                "p75_price": row[3],
                "min_price": row[4],
                "max_price": row[5]
            }
        finally:
            conn.close()

    @classmethod
    def get_anomalies(cls, target_id: str, discount_threshold_pct: float = 20.0) -> List[Dict[str, Any]]:
        conn = cls.get_connection()
        try:
            query = """
                WITH latest AS (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                    FROM price_history
                    WHERE target_id = ? AND price_current > 100
                ),
                stats AS (
                    SELECT median(price_current) as median_price
                    FROM latest WHERE rn = 1
                )
                SELECT 
                    l.item_id, l.target_id, l.source, l.title, l.price_current, l.location, l.seller, l.url, l.image_url,
                    s.median_price,
                    round(((s.median_price - l.price_current) / s.median_price) * 100, 1) as discount_from_median_pct
                FROM latest l
                CROSS JOIN stats s
                WHERE l.rn = 1 
                  AND s.median_price > 0
                  AND l.price_current <= s.median_price * (1.0 - (? / 100.0))
                ORDER BY discount_from_median_pct DESC;
            """
            df = conn.execute(query, [target_id, discount_threshold_pct]).fetchdf()
            return df.to_dict(orient="records") if not df.empty else []
        finally:
            conn.close()

    @classmethod
    def get_price_drops(cls, target_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Поиск объявлений, где продавец снизил цену в последних срезах"""
        conn = cls.get_connection()
        try:
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
                ORDER BY drop_pct DESC;
            """
            df = conn.execute(query, params).fetchdf()
            return df.to_dict(orient="records") if not df.empty else []
        finally:
            conn.close()

    @classmethod
    def export_to_parquet(cls, output_path: Optional[Path] = None) -> Path:
        """Экспорт даталейка в сжатый Parquet для синхронизации с Хостом 2 и 8 TB Cloud"""
        out = output_path or (settings.DATA_DIR / "market_data_lake.parquet")
        conn = cls.get_connection()
        try:
            conn.execute(f"COPY price_history TO '{str(out)}' (FORMAT PARQUET, COMPRESSION ZSTD);")
            logger.info(f"Даталейк успешно экспортирован в Parquet: {out}")
            return out
        finally:
            conn.close()
