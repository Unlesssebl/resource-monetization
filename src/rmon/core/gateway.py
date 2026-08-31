"""
Unified Telegram Gateway for RMon Platform.
Единая точка входа и диспетчеризации команд для всех сервисов монетизации
(Мониторинг цен, Faster-Whisper транскрибация, VOD архив, телеметрия кластера).
"""
import json
import asyncio
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.core.hardware import HardwareArbiter

logger = get_logger("TelegramGateway")

class TelegramGateway:
    """Единый Telegram шлюз оповещений и интерактивного управления платформой"""

    @classmethod
    async def send_message(
        cls,
        text: str,
        chat_id: Optional[str] = None,
        photo_url: Optional[str] = None,
        inline_buttons: Optional[List[List[Dict[str, str]]]] = None
    ) -> bool:
        """
        Универсальная отправка сообщений с поддержкой HTML, фото и инлайн-кнопок.
        """
        token = settings.BOT_TOKEN
        target_chat = chat_id or settings.ADMIN_ID

        if not token or not target_chat:
            logger.info(f"[Telegram Gateway Simulation]:\n{text}")
            return False

        loop = asyncio.get_event_loop()
        reply_markup = {"inline_keyboard": inline_buttons} if inline_buttons else None

        if photo_url and photo_url.startswith("http"):
            api_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            payload = {
                "chat_id": target_chat,
                "photo": photo_url,
                "caption": text,
                "parse_mode": "HTML"
            }
        else:
            api_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": target_chat,
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
            logger.debug(f"Telegram сообщение успешно доставлено [chat_id={target_chat}]")
            return True
        except Exception as e:
            if photo_url:
                # Fallback в текстовом режиме
                return await cls.send_message(text, chat_id=target_chat, photo_url=None, inline_buttons=inline_buttons)
            logger.error(f"Ошибка отправки сообщения в Telegram: {e}")
            return False

    @classmethod
    async def send_deal_alert(cls, deal: Dict[str, Any]):
        """Форматированная отправка найденной прибыльной сделки / аномалии"""
        title = deal.get("title", "Товар")
        price = deal.get("price_current", 0.0)
        median = deal.get("median_price", 0.0)
        discount = deal.get("discount_from_median_pct", 0.0)
        location = deal.get("location", "Россия")
        seller = deal.get("seller", "Частное лицо")
        url = deal.get("url", "")
        photo = deal.get("image_url")
        
        verdict = deal.get("ai_verdict", "CAUTION")
        risk = deal.get("ai_risk", 50)
        summary = deal.get("ai_summary", "")
        profit = deal.get("net_profit_rub", max(0.0, median - price - (median * 0.07)))

        verdict_badge = "🟢 <b>РЕКОМЕНДОВАНО К ВЫКУПУ</b>" if verdict == "BUY" else ("⚠️ <b>ТРЕБУЕТ ВНИМАНИЯ</b>" if verdict == "CAUTION" else "⛔ <b>ВЫСОКИЙ РИСК / СКАМ</b>")

        text = (
            f"🔥 <b>Сигнал арбитража (-{discount:.1f}% от медианы)!</b>\n\n"
            f"📦 <b>Лот:</b> {title}\n"
            f"💰 <b>Цена выкупа:</b> <code>{price:,.0f} ₽</code>\n"
            f"📊 <b>Медиана рынка:</b> <code>{median:,.0f} ₽</code>\n"
            f"💵 <b>Чистый профит:</b> <code>+{profit:,.0f} ₽</code> (с учетом комиссии 7%)\n"
            f"📍 <b>Локация:</b> {location} | 👤 {seller}\n\n"
            f"🤖 <b>AI Аудитор (RTX 3050):</b> {verdict_badge} (Риск: {risk}/100)\n"
            f"💡 <i>{summary}</i>"
        )

        buttons = []
        if url:
            buttons.append([{"text": "🔗 Открыть лот на Авито", "url": url}])

        await cls.send_message(text=text, photo_url=photo, inline_buttons=buttons)

    @classmethod
    async def get_cluster_status_report(cls) -> str:
        """Формирование сводки статуса кластера и ресурсов"""
        telem = HardwareArbiter.get_gpu_telemetry()
        vram_info = f"{telem['vram_used_mb']} MB / {telem['vram_total_mb']} MB ({telem['temperature_c']}°C)" if telem['available'] else "GPU Inactive"

        return (
            "🖥️ <b>Статус кластера Resource Monetization (RMon):</b>\n\n"
            "🟢 <b>Host 1 (itt0666 - AI & Fast Node):</b>\n"
            f"  • CPU: Intel Core i7-12700 (20 потоков)\n"
            f"  • RAM: 56 GB DDR5\n"
            f"  • GPU VRAM: NVIDIA RTX 3050 ({vram_info})\n\n"
            "🟢 <b>Host 2 (Heavy & Cloud Node):</b>\n"
            "  • CPU: Intel Core i5-12600KF (16 потоков)\n"
            "  • RAM: 48 GB DDR4\n"
            "  • GPU: AMD Radeon RX 6800 XT (16 GB VRAM)\n"
            "  • Cloud Vault: 8 TB Pool (Google Drive + Яндекс.Диск)\n\n"
            "⚡ <b>Активные микросервисы:</b>\n"
            "  ✓ <code>services.scraper</code> (DuckDB Engine)\n"
            "  ✓ <code>services.whisper</code> (DirectCompute / CUDA)\n"
            "  ✓ <code>services.vod</code> (Cloud Stream Archive)"
        )
