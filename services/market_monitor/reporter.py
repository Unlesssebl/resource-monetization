from datetime import datetime
from shared.config import settings
from shared.logger import get_logger
from services.market_monitor.storage import MarketDB

logger = get_logger("MarketReporter")

class MarketReporter:
    @staticmethod
    def build_reports() -> tuple[str, str]:
        MarketDB.init_db()
        conn = MarketDB.get_connection()
        today_str = datetime.now().strftime("%Y-%m-%d")
        settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_file = settings.REPORTS_DIR / f"market_report_{today_str}.csv"
        md_file = settings.REPORTS_DIR / f"market_report_{today_str}.md"

        query = """
            WITH latest AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY scraped_at DESC) as rn
                FROM price_history
            )
            SELECT source, item_id, title, brand, price_current, price_original, discount_pct, rating, feedbacks_count, in_stock, url
            FROM latest
            WHERE rn = 1
            ORDER BY price_current ASC
        """
        df = conn.execute(query).df()
        conn.close()

        df.to_csv(csv_file, index=False, encoding="utf-8-sig")

        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# 📊 Ежедневный срез цен конкурентов ({today_str})\n\n")
            f.write(f"- **Позиций в мониторинге:** {len(df)}\n")
            f.write(f"- **Дата формирования:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")
            f.write("| Источник | Бренд | Товар | Цена | Скидка | Рейтинг | Ссылка |\n")
            f.write("|---|---|---|:---:|:---:|:---:|:---:|\n")
            for _, row in df.iterrows():
                f.write(f"| {row['source'].upper()} | {row['brand']} | {row['title'][:30]}... | **{row['price_current']:,.0f} ₽** | -{row['discount_pct']}% | ⭐ {row['rating']} | [Открыть]({row['url']}) |\n")

        logger.info(f"Сгенерированы отчеты: {csv_file.name}, {md_file.name}")
        return str(csv_file), str(md_file)