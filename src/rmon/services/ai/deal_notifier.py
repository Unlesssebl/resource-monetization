"""
Deal Alert Notifier Use Case for RMon Platform.
Координирует оценку ликвидности лота, расчет юнит-экономики и передачу готового
уведомления в инфраструктурный транспорт TelegramGateway.
"""
from typing import Dict, Any, Optional
from rmon.services.ai.deal_intelligence import DealIntelligenceEngine
from rmon.core.logger import get_logger

logger = get_logger("DealAlertNotifier")


class DealAlertNotifier:
    """Прикладной сценарий форматирования и отправки сигналов выгодных сделок"""

    _transport = None

    @classmethod
    def set_transport(cls, transport):
        """Инъекция кастомного транспорта для тестов или альтернативных каналов"""
        cls._transport = transport

    @classmethod
    def get_transport(cls):
        """Резолвер транспорта по умолчанию"""
        if cls._transport is None:
            from rmon.core.gateway import TelegramGateway
            cls._transport = TelegramGateway
        return cls._transport

    @classmethod
    async def send_deal_alert(cls, deal: Dict[str, Any], transport: Optional[Any] = None) -> bool:
        """Форматированная отправка найденной прибыльной сделки / аномалии"""
        title = deal.get("title", "Товар")
        price = deal.get("price_current", 0.0)
        median = deal.get("median_price", 0.0)
        discount = deal.get("discount_from_median_pct", 0.0)
        location = deal.get("location", "Россия")
        seller = deal.get("seller", "Частное лицо")
        url = deal.get("url", "")
        photo = deal.get("image_url")

        # Расчет экономики через доменный сервис
        econ = DealIntelligenceEngine.calculate_deal_economics(price, median)
        profit = econ["net_profit_rub"]
        roi = econ["roi_pct"]

        # Оценка ликвидности
        views_str = deal.get("views", "30")
        date_str = deal.get("date_posted", "сегодня")
        liq = DealIntelligenceEngine.calculate_liquidity(views_str, date_str)

        # Скрипт торга
        pitch = DealIntelligenceEngine.generate_negotiation_pitch(title, price, seller)

        verdict = deal.get("ai_verdict", "CAUTION")
        risk = deal.get("ai_risk", 50)
        summary = deal.get("ai_summary", "")

        verdict_badge = (
            "🟢 <b>РЕКОМЕНДОВАНО К ВЫКУПУ</b>"
            if verdict == "BUY"
            else ("⚠️ <b>ТРЕБУЕТ ВНИМАНИЯ</b>" if verdict == "CAUTION" else "⛔ <b>ВЫСОКИЙ РИСК / СКАМ</b>")
        )

        text = (
            f"🔥 <b>Сигнал сделки (-{discount:.1f}% от медианы)!</b>\n\n"
            f"📦 <b>Лот:</b> {title}\n"
            f"💰 <b>Цена выкупа:</b> <code>{price:,.0f} ₽</code> (рынок: <code>{median:,.0f} ₽</code>)\n"
            f"💵 <b>Чистый профит:</b> <code>+{profit:,.0f} ₽</code> (ROI: <b>+{roi}%</b>)\n"
            f"📈 <b>Ликвидность:</b> <b>{liq['liquidity_score']}/100</b> ({liq['liquidity_tier']})\n"
            f"📍 <b>Локация:</b> {location} | 👤 {seller}\n\n"
            f"🤖 <b>AI Аудитор:</b> {verdict_badge} (Риск: {risk}/100)\n"
            f"💡 <i>{summary}</i>\n\n"
            f"💬 <b>Скрипт торга (быстрый выкуп на 10% дешевле):</b>\n"
            f"<code>{pitch}</code>"
        )

        buttons = []
        if url:
            buttons.append([{"text": "🔗 Открыть лот на Авито", "url": url}])

        t = transport or cls.get_transport()
        return await t.send_message(text=text, photo_url=photo, inline_buttons=buttons)
