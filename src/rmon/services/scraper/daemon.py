import os
import json
import asyncio
import random
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Set, Dict, Any, List

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.services.scraper.avito import AvitoScraper
from rmon.services.scraper.storage import DuckDBStorage
from rmon.services.scraper.analytics import MarketAnalytics

logger = get_logger("MonitorDaemon")

class TelegramNotifier:
    """Уведомитель в Telegram с поддержкой MarkdownV2 / HTML, фото и инлайн-кнопок"""

    @staticmethod
    async def send_alert(text: str, photo_url: Optional[str] = None, lot_url: Optional[str] = None):
        token = settings.BOT_TOKEN
        admin_id = settings.ADMIN_ID

        if not token or not admin_id:
            logger.info(f"[Telegram Alert Simulation (токен не задан)]:\n{text}")
            return

        loop = asyncio.get_event_loop()

        # Формирование инлайн-кнопок
        reply_markup = None
        if lot_url:
            reply_markup = {
                "inline_keyboard": [
                    [{"text": "🔗 Открыть объявление на Авито", "url": lot_url}]
                ]
            }

        # Отправка с фото или обычным текстом
        if photo_url and photo_url.startswith("http"):
            api_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            payload = {
                "chat_id": admin_id,
                "photo": photo_url,
                "caption": text,
                "parse_mode": "HTML"
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
        else:
            api_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": admin_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=12))
            logger.info("Telegram-алерт успешно отправлен!")
        except Exception as e:
            # Fallback на обычный текст если фото не загрузилось
            if photo_url:
                logger.warning(f"Не удалось отправить фото в Telegram ({e}), повтор в текстовом режиме...")
                await TelegramNotifier.send_alert(text, photo_url=None, lot_url=lot_url)
            else:
                logger.error(f"Ошибка отправки Telegram-алерта: {e}")

class MonitorDaemon:
    """Автономный 24/7 демон сбора данных и рассылки алертов"""

    def __init__(self, config_path: Path = settings.CONFIG_DIR / "targets.json"):
        self.config_path = config_path
        self.alerted_items: Set[str] = set() # Хранит ключ: item_id_price для исключения спама
        self.is_running = False

    def load_targets(self) -> List[Dict[str, Any]]:
        if not self.config_path.exists():
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [t for t in data.get("targets", []) if t.get("enabled", True)]
        except Exception as e:
            logger.error(f"Ошибка чтения конфига таргетов: {e}")
            return []

    async def process_target(self, target: Dict[str, Any]):
        tid = target["id"]
        query = target["query"]
        city = target.get("city", "moskva")
        threshold = float(target.get("anomaly_threshold_pct", 20.0))

        logger.info(f"⏳ Сканирование таргета: [{tid}] ({query}, {city})...")

        # Сбор данных
        items = await AvitoScraper.scrape_search(query=query, city=city, limit=25, headless=True)
        if items:
            DuckDBStorage.save_items(items, target_id=tid, source="avito")

        # Анализ аномалий
        anomalies = DuckDBStorage.get_anomalies(tid, discount_threshold_pct=threshold)
        new_anomalies = []

        for a in anomalies:
            alert_key = f"{a['item_id']}_{a['price_current']}"
            if alert_key not in self.alerted_items:
                self.alerted_items.add(alert_key)
                new_anomalies.append(a)

        # Отправка алертов о новых аномалиях с AI-аудитом на RTX 3050
        if new_anomalies:
            logger.info(f"🔥 Найдено {len(new_anomalies)} новых аномалий по таргету [{tid}]. Запуск локального AI аудита...")
            from rmon.services.ai.deal_auditor import AIDealAuditor

            for a in new_anomalies:
                ai_eval = AIDealAuditor.audit_listing(
                    title=a['title'],
                    price=a['price_current'],
                    seller=a.get('seller', ''),
                    location=a.get('location', ''),
                    market_median=a.get('median_price'),
                    use_fast_model=False
                )

                verdict = ai_eval.get("verdict", "CAUTION")
                risk = ai_eval.get("risk_score", 50)
                summary = ai_eval.get("concise_summary", "")
                issues = ai_eval.get("detected_issues", [])

                verdict_badge = "🟢 <b>РЕКОМЕНДОВАНО К ВЫКУПУ</b>" if verdict == "BUY" else ("⚠️ <b>ТРЕБУЕТ ВНИМАНИЯ</b>" if verdict == "CAUTION" else "⛔ <b>ВЫСОКИЙ РИСК / СКАМ</b>")
                issues_text = f"\n⚠️ <b>Флаги риска:</b> {', '.join(issues)}" if issues else ""

                msg = (
                    f"🔥 <b>Аномалия цены (-{a['discount_from_median_pct']}% от медианы)!</b>\n\n"
                    f"📌 <b>Товар:</b> {a['title']}\n"
                    f"💰 <b>Цена:</b> <code>{a['price_current']:,.0f} ₽</code> (медиана: <code>{a['median_price']:,.0f} ₽</code>)\n"
                    f"📍 <b>Локация:</b> {a['location']} | 👤 {a['seller']}\n\n"
                    f"🤖 <b>AI-Аудитор (RTX 3050 CUDA):</b> {verdict_badge} (Риск: {risk}/100)\n"
                    f"💡 <i>{summary}</i>{issues_text}"
                )
                await TelegramNotifier.send_alert(msg, lot_url=a['url'])

        # Анализ снижения цен
        drops = DuckDBStorage.get_price_drops(tid)
        new_drops = []
        for d in drops:
            drop_key = f"drop_{d['item_id']}_{d['price_current']}"
            if drop_key not in self.alerted_items:
                self.alerted_items.add(drop_key)
                new_drops.append(d)

        if new_drops:
            logger.info(f"📉 Найдено {len(new_drops)} фактов снижения цен по таргету [{tid}]!")
            for d in new_drops:
                msg = (
                    f"📉 <b>Продавец снизил цену (-{d['drop_pct']}%)!</b>\n\n"
                    f"📌 <b>Товар:</b> {d['title']}\n"
                    f"💰 <b>Новая цена:</b> <code>{d['price_current']:,.0f} ₽</code> (было <s>{d['prev_price']:,.0f} ₽</s>)\n"
                    f"💸 <b>Скидка:</b> <code>-{d['price_drop_rub']:,.0f} ₽</code>\n"
                    f"📍 <b>Локация:</b> {d['location']}\n"
                    f"🔗 <a href='{d['url']}'>Открыть объявление на Авито</a>"
                )
                await TelegramNotifier.send_alert(msg)

    async def run(self):
        self.is_running = True
        logger.info("🚀 Фоновый демон мониторинга Авито запущен (24/7 Zero-Touch Mode)")

        while self.is_running:
            targets = self.load_targets()
            if not targets:
                logger.warning("Список активных таргетов пуст. Ожидание 60 секунд...")
                await asyncio.sleep(60)
                continue

            for target in targets:
                try:
                    await self.process_target(target)
                    await asyncio.sleep(random.uniform(8.0, 15.0))
                except Exception as e:
                    logger.error(f"Ошибка обработки таргета {target.get('id')}: {e}")

            # Пауза между полными кругами проверок
            full_cycle_pause = random.uniform(300, 600)
            logger.info(f"Круг мониторинга завершен. Отдых перед следующим циклом: {full_cycle_pause:.0f} сек.")
            await asyncio.sleep(full_cycle_pause)

    def stop(self):
        self.is_running = False
        logger.info("Фоновый демон мониторинга остановлен.")
