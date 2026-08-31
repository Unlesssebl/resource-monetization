"""
Deal Intelligence & Liquidity Engine for RMon Platform.
Автономный расчет индекса ликвидности (Views Velocity), чистой маржи с учетом логистики
и генерация психологических офферов для торга (Fast Cash Pitch) на базе локальной LLM на RTX 3050.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from rmon.core.logger import get_logger

logger = get_logger("DealIntelligence")

class DealIntelligenceEngine:
    """Аналитический движок оценки ликвидности и формирования сделок"""

    MONTH_MAP = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12
    }

    @classmethod
    def parse_views_count(cls, views_str: str) -> int:
        """Извлечение количества просмотров из строки (например, '971 просмотр')"""
        if not views_str:
            return 0
        cleaned = re.sub(r"[^\d]", "", views_str)
        try:
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0

    @classmethod
    def parse_hours_elapsed(cls, date_str: str) -> float:
        """Расчет количества часов с момента публикации объявления"""
        if not date_str:
            return 24.0 # Значение по умолчанию (1 сутки)

        now = datetime.now()
        date_lower = date_str.lower().strip()

        # 'сегодня в 14:20'
        if "сегодня" in date_lower:
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_lower)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                pub_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
                diff = (now - pub_time).total_seconds() / 3600.0
                return max(0.5, diff)
            return 4.0

        # 'вчера в 19:30'
        if "вчера" in date_lower:
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_lower)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                pub_time = (now - timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
                diff = (now - pub_time).total_seconds() / 3600.0
                return max(12.0, diff)
            return 24.0

        # '· 29 августа в 19:23' или '28 августа'
        match = re.search(r"(\d{1,2})\s+([а-яё]+)", date_lower)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            month = cls.MONTH_MAP.get(month_name, now.month)
            year = now.year
            time_match = re.search(r"(\d{1,2}):(\d{2})", date_lower)
            h, m = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (12, 0)
            try:
                pub_date = datetime(year, month, day, h, m)
                if pub_date > now:
                    pub_date = pub_date.replace(year=year - 1)
                diff = (now - pub_date).total_seconds() / 3600.0
                return max(1.0, diff)
            except Exception:
                pass

        return 48.0 # Fallback

    @classmethod
    def calculate_liquidity(cls, views_str: str, date_str: str, category_boost: float = 1.0) -> Dict[str, Any]:
        """
        Расчет индекса ликвидности (0 - 100) и скорости просмотров.
        """
        views = cls.parse_views_count(views_str)
        hours = cls.parse_hours_elapsed(date_str)
        velocity = views / hours if hours > 0 else float(views)

        # Базовая оценка ликвидности по скорости просмотров
        if velocity >= 15.0:
            score = 95
            tier = "🔥 СВЕРХЛИКВИДНЫЙ (Улетит за 12-24 ч)"
        elif velocity >= 5.0:
            score = 80
            tier = "🟢 ВЫСОКИЙ СПРОС (Продажа 1-3 дня)"
        elif velocity >= 1.5:
            score = 60
            tier = "🟡 СРЕДНИЙ СПРОС (Продажа 4-7 дней)"
        else:
            score = 35
            tier = "❄️ НИЗКИЙ СПРОС / ЗАСТОЙ (Висит > недели)"

        # Корректировка на абсолютное число просмотров
        if views > 500:
            score = min(100, score + 10)

        return {
            "views_total": views,
            "hours_online": round(hours, 1),
            "views_per_hour": round(velocity, 2),
            "liquidity_score": score,
            "liquidity_tier": tier
        }

    @classmethod
    def calculate_deal_economics(
        cls,
        price_current: float,
        market_median: float,
        delivery_fee_pct: float = 7.0,
        logistics_cost_rub: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Расчет чистой маржи и ROI с учетом Авито Доставки / бензина / торга.
        """
        if market_median <= 0:
            market_median = price_current * 1.3

        commission = market_median * (delivery_fee_pct / 100.0)
        net_resale_price = market_median - commission
        net_profit = net_resale_price - price_current - logistics_cost_rub
        roi_pct = (net_profit / price_current * 100.0) if price_current > 0 else 0.0

        return {
            "price_buy": price_current,
            "market_median": market_median,
            "commission_rub": round(commission),
            "logistics_rub": round(logistics_cost_rub),
            "net_profit_rub": round(net_profit),
            "roi_pct": round(roi_pct, 1),
            "is_profitable": net_profit > 3000
        }

    @classmethod
    def generate_negotiation_pitch(
        cls,
        title: str,
        price_current: float,
        seller_name: str = "продавец",
        discount_target_pct: float = 12.0
    ) -> str:
        """
        Генерация психологически выверенного скрипта для торга на быстрый выкуп наличными.
        """
        offer_price = int((price_current * (1.0 - (discount_target_pct / 100.0))) // 500 * 500) # Округление до 500 руб.
        
        pitches = [
            f"Здравствуйте! Готов забрать {title} сегодня самовывозом за наличные за {offer_price:,.0f} ₽ без долгих проверок (5-10 минут). Если предложение устраивает — напишите, пожалуйста, точный адрес и когда вам удобно.",
            f"Добрый день! Могу подъехать за {offer_price:,.0f} ₽ сегодня до вечера, оплата сразу на руки / перевод. Если готовы отдать без лишней траты времени — пришлите адрес.",
            f"Приветствую! Заберу сегодня за {offer_price:,.0f} ₽ за быстрый выкуп без торга на месте. Если актуально — скиньте локацию, выезжаю."
        ]
        return pitches[0]
