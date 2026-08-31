from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path
from rmon.core.config import settings
from rmon.services.scraper.storage import DuckDBStorage

class MarketAnalytics:
    """Аналитический модуль для формирования отчетов и сигналов для агента agy"""

    @classmethod
    def generate_markdown_report(cls, target_id: str = "rtx_3080_msk", discount_threshold: float = 20.0) -> Tuple[str, str]:
        """
        Формирование подробного Markdown и CSV отчета по таргету.
        Возвращает (путь_к_md, краткое_резюме_для_agy).
        """
        stats = DuckDBStorage.get_market_summary(target_id)
        anomalies = DuckDBStorage.get_anomalies(target_id, discount_threshold)
        drops = DuckDBStorage.get_price_drops(target_id)

        today_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        md_file = settings.REPORTS_DIR / f"avito_report_{target_id}_{today_str}.md"

        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# 📊 Срез рынка Авито: `{target_id}`\n\n")
            f.write(f"- **Дата среза:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write(f"- **Всего лотов в выборке:** {stats['total_items']}\n")
            f.write(f"- **Медианная цена:** `{stats['median_price']:,.0f} ₽`\n")
            f.write(f"- **25-й перцентиль (низ рынка):** `{stats['p25_price']:,.0f} ₽`\n")
            f.write(f"- **Мин / Макс:** `{stats['min_price']:,.0f} ₽` / `{stats['max_price']:,.0f} ₽`\n\n")

            f.write("## 🚀 Топ аномалий ниже рынка (Дисконт $\\ge " + f"{discount_threshold:.0f}\\%$ от медианы)\n\n")
            if anomalies:
                f.write("| Товар | Цена | Медиана | Дисконт | Локация | Ссылка |\n")
                f.write("|---|:---:|:---:|:---:|---|:---:|\n")
                for a in anomalies:
                    f.write(f"| {a['title'][:40]} | **{a['price_current']:,.0f} ₽** | {a['median_price']:,.0f} ₽ | **-{a['discount_from_median_pct']}%** | {a['location']} | [Открыть]({a['url']}) |\n")
            else:
                f.write("> Аномалий с дисконтом более " + f"{discount_threshold:.0f}% не обнаружено.\n")

            f.write("\n## 📉 Зафиксированные снижения цен продавцами (Price Drop)\n\n")
            if drops:
                f.write("| Товар | Новая цена | Старая цена | Снижение | Локация | Ссылка |\n")
                f.write("|---|:---:|:---:|:---:|---|:---:|\n")
                for d in drops:
                    f.write(f"| {d['title'][:40]} | **{d['price_current']:,.0f} ₽** | ~{d['prev_price']:,.0f} ₽~ | **-{d['drop_pct']}%** (-{d['price_drop_rub']:,.0f} ₽) | {d['location']} | [Открыть]({d['url']}) |\n")
            else:
                f.write("> За последние проверки снижений цен не зафиксировано.\n")

        summary = (
            f"🎯 Таргет: {target_id} | Лотов: {stats['total_items']} | Медиана: {stats['median_price']:,.0f} ₽\n"
            f"🔥 Аномалий: {len(anomalies)} | 📉 Снижений цен: {len(drops)}\n"
            f"📄 Полный отчет: {md_file.name}"
        )

        return str(md_file), summary
