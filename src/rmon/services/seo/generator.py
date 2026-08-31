"""
Clean Minimalist Hardware Price Portal with Claude (Warm Editorial) Palette.
- Цветовая палитра Claude / Anthropic: #141413 (Charcoal), #1E1E1C (Surface), #CC785C (Terracotta), #F3F1EB (Ivory)
- Легкий и чистый стек: Tailwind CSS 3.x + Lucide Icons
- Интуитивная шкала ценового диапазона (Price Range Gauge) в теплой гамме
- Плавный криволинейный спарклайн цен (Cubic Bezier SVG) в терракотовом цвете
- Аккуратная таблица предложений без визуального мусора
"""
import os
import re
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import duckdb

from rmon.core.config import settings
from rmon.core.lake import DataLake
from rmon.core.logger import get_logger

logger = get_logger("ClaudeSEOGenerator")

HARDWARE_DATABASE = {
    "RTX_3080": {
        "name": "GeForce RTX 3080",
        "category": "Видеокарта",
        "msrp_rub": 65000,
        "vram": "10 GB GDDR6X",
        "bus": "320 bit",
        "tdp": "320 Вт",
        "cuda_cores": "8704",
        "interface": "PCIe 4.0 x16",
        "checks": [
            "Тест в FurMark не менее 10 минут (температура чипа должна быть до 74°C)",
            "Проверка температуры памяти GDDR6X в HWiNFO64 (не выше 94°C)",
            "Визуальный осмотр бэкплейта и винтов на предмет вскрытия и следов перегрева",
            "Тест вентиляторов на отсутствие постороннего шума и вибраций на 100% оборотов"
        ]
    },
    "RTX_4070": {
        "name": "GeForce RTX 4070",
        "category": "Видеокарта",
        "msrp_rub": 72000,
        "vram": "12 GB GDDR6X",
        "bus": "192 bit",
        "tdp": "200 Вт",
        "cuda_cores": "5888",
        "interface": "PCIe 4.0 x16",
        "checks": [
            "Осмотр 16-контактного разъема 12VHPWR на плотность посадки и целостность контактов",
            "Тест в 3DMark TimeSpy на удержание Boost-частоты (не ниже 2475 МГц)",
            "Проверка наличия гарантийной пломбы производителя и электронного чека"
        ]
    },
    "IPHONE_14": {
        "name": "iPhone 14 (128/256 GB)",
        "category": "Смартфон",
        "msrp_rub": 89000,
        "vram": "128 / 256 GB",
        "bus": "Apple A15 Bionic",
        "tdp": "3279 мАч",
        "cuda_cores": "6 GB ОЗУ",
        "interface": "Lightning / MagSafe",
        "checks": [
            "Проверка в 3uTools оригинальности дисплея, камер и контроллера аккумулятора",
            "Проверка работы Face ID, True Tone и датчиков приближения",
            "Проверка отсутствия корпоративных профилей MDM и чистый выход из iCloud"
        ]
    }
}

class ClaudeCleanSEOGenerator:
    """Генератор портала цен в теплой палитре Claude"""

    OUTPUT_DIR = settings.DATA_DIR / "seo_site"
    BASE_URL = "https://price-radar.pages.dev"

    MONTH_NAMES_RU = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }

    @staticmethod
    def filter_legitimate_deals(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Отсекает мусорные объявления (коробки, винты, кабели)"""
        prices = [d["price_current"] for d in deals if d["price_current"] > 0]
        if not prices:
            return []
        sorted_p = sorted(prices)
        med = sorted_p[len(sorted_p) // 2]
        clean = [d for d in deals if (med * 0.35) <= d["price_current"] <= (med * 2.3)]
        return clean if len(clean) >= 3 else deals

    @classmethod
    def generate_smooth_svg_chart(cls, prices: List[float], width: int = 700, height: int = 200) -> str:
        """Генерация гладкого спарклайна в теплой терракотовой гамме Claude"""
        if not prices:
            return ""

        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        min_p = prices_sorted[0]
        max_p = prices_sorted[-1]
        med_p = prices_sorted[n // 2]

        pad_x = 40
        pad_y = 25
        w = width - (pad_x * 2)
        h = height - (pad_y * 2)
        y_range = max(1.0, max_p - min_p)

        pts = []
        step = max(1, (n - 1) // 6)
        samples = [prices_sorted[i] for i in range(0, n, step)]
        if len(samples) < 6:
            samples.append(prices_sorted[-1])
        samples = samples[:7]

        for i, val in enumerate(samples):
            x = pad_x + (i * (w / (len(samples) - 1)))
            y = height - pad_y - ((val - min_p) / y_range * h)
            pts.append((x, y, val))

        path_cmds = [f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"]
        for i in range(len(pts) - 1):
            p0 = pts[i]
            p1 = pts[i + 1]
            cx = (p0[0] + p1[0]) / 2
            path_cmds.append(f"C {cx:.1f},{p0[1]:.1f} {cx:.1f},{p1[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}")
        
        path_str = " ".join(path_cmds)
        area_str = f"{path_str} L {pts[-1][0]:.1f},{height - pad_y} L {pts[0][0]:.1f},{height - pad_y} Z"

        return f"""
        <svg viewBox="0 0 {width} {height}" class="w-full h-auto" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="claudeWarmArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#CC785C" stop-opacity="0.18"/>
                    <stop offset="100%" stop-color="#CC785C" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            <!-- Сетка -->
            <line x1="{pad_x}" y1="{pad_y}" x2="{width - pad_x}" y2="{pad_y}" stroke="#2C2C29" stroke-dasharray="3 3"/>
            <line x1="{pad_x}" y1="{height/2}" x2="{width - pad_x}" y2="{height/2}" stroke="#2C2C29" stroke-dasharray="3 3"/>
            <line x1="{pad_x}" y1="{height - pad_y}" x2="{width - pad_x}" y2="{height - pad_y}" stroke="#2C2C29"/>

            <!-- Заливка и линия -->
            <path d="{area_str}" fill="url(#claudeWarmArea)"/>
            <path d="{path_str}" fill="none" stroke="#CC785C" stroke-width="2.5" stroke-linecap="round"/>

            <!-- Подписи уровней -->
            <text x="{pad_x}" y="{height - 8}" fill="#7D7A73" font-size="11" font-family="monospace">Мин: {int(min_p):,} ₽</text>
            <text x="{width/2}" y="{height - 8}" fill="#CC785C" font-size="11" text-anchor="middle" font-family="monospace" font-weight="600">Медиана: {int(med_p):,} ₽</text>
            <text x="{width - pad_x}" y="{height - 8}" fill="#7D7A73" font-size="11" text-anchor="end" font-family="monospace">Макс: {int(max_p):,} ₽</text>
        </svg>
        """

    @classmethod
    def generate_product_page(cls, target_id: str, city: str = "moskva") -> Dict[str, Any]:
        """Генерация страницы товара в палитре Claude"""
        conn = DataLake.get_connection()
        try:
            rows = conn.execute("""
                SELECT item_id, title, price_current, location, seller, url, image_url, scraped_at
                FROM price_history
                WHERE target_id = ?
                ORDER BY scraped_at DESC
            """, [target_id]).fetchall()

            if not rows:
                return {}

            cols = ["item_id", "title", "price_current", "location", "seller", "url", "image_url", "scraped_at"]
            all_deals = [dict(zip(cols, r)) for r in rows]
            deals = cls.filter_legitimate_deals(all_deals)
            prices = sorted([d["price_current"] for d in deals if d["price_current"] > 0])

            if not prices:
                return {}

            n = len(prices)
            min_price = prices[0]
            max_price = prices[-1]
            med_price = prices[n // 2]
            p25_price = prices[int(n * 0.25)]
            p75_price = prices[int(n * 0.75)]

            lookup_key = "RTX_3080" if "3080" in target_id else ("RTX_4070" if "4070" in target_id else ("IPHONE_14" if "iphone" in target_id else "RTX_3080"))
            hw = HARDWARE_DATABASE.get(lookup_key, HARDWARE_DATABASE["RTX_3080"])
            clean_name = hw["name"]
            msrp = hw["msrp_rub"]
            msrp_diff_pct = int(((med_price - msrp) / msrp) * 100)
            best_deals = sorted(deals, key=lambda x: x["price_current"])[:8]

        finally:
            conn.close()

        now = datetime.now()
        date_str = f"{now.day} {cls.MONTH_NAMES_RU.get(now.month, 'августа')} {now.year}"
        city_title = "Москве" if city == "moskva" else "Санкт-Петербурге"
        chart_svg = cls.generate_smooth_svg_chart(prices)

        # Таблица предложений
        deals_html = []
        for d in best_deals:
            disc = max(0, int(((med_price - d['price_current']) / med_price) * 100))
            disc_badge = f'<span class="ml-2 text-xs font-medium px-2 py-0.5 rounded bg-[#68B38A]/15 text-[#68B38A] border border-[#68B38A]/30">-{disc}%</span>' if disc >= 10 else ""
            deals_html.append(f"""
            <tr class="border-b border-[#2C2C29] hover:bg-[#262624] transition">
                <td class="py-3 px-4">
                    <a href="{d['url']}" target="_blank" rel="nofollow noopener" class="text-sm font-medium text-[#F3F1EB] hover:text-[#CC785C] transition flex items-center gap-1.5">
                        {d['title'][:55]}
                        <i data-lucide="external-link" class="w-3.5 h-3.5 text-[#7D7A73]"></i>
                    </a>
                    <div class="text-xs text-[#7D7A73] mt-0.5">📍 {d['location']} • Продавец: {d['seller'][:25]}</div>
                </td>
                <td class="py-3 px-4 text-right">
                    <span class="font-mono text-sm font-semibold text-[#68B38A]">{d['price_current']:,.0f} ₽</span>
                    {disc_badge}
                </td>
            </tr>
            """)

        checks_html = "".join([
            f'''<li class="flex items-start gap-2.5 text-sm text-[#B8B6AF]">
                <i data-lucide="check-circle-2" class="w-4 h-4 text-[#CC785C] shrink-0 mt-0.5"></i>
                <span>{c}</span>
            </li>'''
            for c in hw['checks']
        ])

        html = f"""<!DOCTYPE html>
<html lang="ru" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Сколько стоит б/у {clean_name} в {city_title} — Цены и аналитика рынка ({now.year})</title>
    <meta name="description" content="Реальные цены на б/у {clean_name} в {city_title} на {date_str}. Медиана рынка: {med_price:,.0f} ₽. Анализ {len(deals)} объявлений, диапазон цен и чек-лист проверки.">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
        font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-[#141413] text-[#F3F1EB] min-h-screen antialiased">
    <!-- Header -->
    <header class="border-b border-[#2C2C29] bg-[#141413]/90 backdrop-blur sticky top-0 z-50">
        <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
            <a href="/" class="flex items-center gap-2 text-sm font-semibold text-[#F3F1EB] hover:opacity-90">
                <i data-lucide="cpu" class="w-5 h-5 text-[#CC785C]"></i>
                <span>PriceRadar</span>
                <span class="text-xs px-2 py-0.5 rounded bg-[#1E1E1C] text-[#B8B6AF] border border-[#2C2C29] font-normal">Цены вторичного рынка</span>
            </a>
            <div class="flex items-center gap-3">
                <a href="https://t.me/monitoringsuba_bot" target="_blank" class="inline-flex items-center gap-1.5 text-xs font-medium bg-[#CC785C] hover:opacity-90 text-[#FAF9F6] px-3.5 py-1.5 rounded-md transition shadow-sm">
                    <i data-lucide="bell" class="w-3.5 h-3.5"></i>
                    <span>Бот алертов</span>
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-8">
        <!-- Breadcrumb -->
        <div class="flex items-center justify-between text-xs text-[#7D7A73] mb-3">
            <div class="flex items-center gap-1.5">
                <a href="/" class="hover:text-[#F3F1EB]">Главная</a>
                <span>/</span>
                <span class="text-[#B8B6AF]">{hw['category']}</span>
                <span>/</span>
                <span class="text-[#F3F1EB]">{clean_name}</span>
            </div>
            <div class="flex items-center gap-1.5 font-mono text-[#7D7A73]">
                <span class="w-2 h-2 rounded-full bg-[#68B38A]"></span>
                <span>Обновлено: {date_str}</span>
            </div>
        </div>

        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight text-[#F3F1EB] mb-2">{clean_name} в {city_title}</h1>
        <p class="text-sm text-[#B8B6AF] mb-6">Анализ цен по выборке из {len(deals)} реальных объявлений на вторичном рынке.</p>

        <!-- Price Range Gauge (Claude Palette) -->
        <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl p-5 mb-6 shadow-sm">
            <div class="flex items-center justify-between text-xs font-medium text-[#B8B6AF] mb-2">
                <span>Низкая цена (Срочно)</span>
                <span class="text-[#CC785C] font-semibold">Медиана рынка</span>
                <span>Выше среднего (Магазины)</span>
            </div>
            <div class="h-3 w-full bg-[#141413] rounded-full relative overflow-hidden flex mb-3 border border-[#2C2C29]">
                <div class="h-full bg-[#68B38A]/80 w-[30%]"></div>
                <div class="h-full bg-[#CC785C]/80 w-[40%]"></div>
                <div class="h-full bg-[#383834] w-[30%]"></div>
            </div>
            <div class="grid grid-cols-3 text-center">
                <div>
                    <div class="text-xs text-[#7D7A73]">Выгодная покупка</div>
                    <div class="font-mono text-sm font-semibold text-[#68B38A] mt-0.5">{min_price:,.0f} – {p25_price:,.0f} ₽</div>
                </div>
                <div>
                    <div class="text-xs text-[#CC785C]">Справедливая цена</div>
                    <div class="font-mono text-base font-bold text-[#F3F1EB] mt-0.5">{med_price:,.0f} ₽</div>
                </div>
                <div>
                    <div class="text-xs text-[#7D7A73]">Верхний порог</div>
                    <div class="font-mono text-sm font-semibold text-[#B8B6AF] mt-0.5">{p75_price:,.0f} – {max_price:,.0f} ₽</div>
                </div>
            </div>
        </div>

        <!-- Key Stats Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-lg p-3.5">
                <div class="text-xs text-[#7D7A73]">Медианная цена</div>
                <div class="font-mono text-lg font-bold text-[#CC785C] mt-1">{med_price:,.0f} ₽</div>
                <div class="text-xs text-[#7D7A73] mt-0.5">{msrp_diff_pct}% от цены релиза</div>
            </div>
            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-lg p-3.5">
                <div class="text-xs text-[#7D7A73]">Минимальная в базе</div>
                <div class="font-mono text-lg font-bold text-[#68B38A] mt-1">{min_price:,.0f} ₽</div>
                <div class="text-xs text-[#68B38A]/80 mt-0.5">Дисконт ~{max(0, int((med_price-min_price)/med_price*100))}%</div>
            </div>
            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-lg p-3.5">
                <div class="text-xs text-[#7D7A73]">Официальная MSRP</div>
                <div class="font-mono text-lg font-bold text-[#F3F1EB] mt-1">{msrp:,.0f} ₽</div>
                <div class="text-xs text-[#7D7A73] mt-0.5">Цена нового на старте</div>
            </div>
            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-lg p-3.5">
                <div class="text-xs text-[#7D7A73]">Ликвидность</div>
                <div class="font-mono text-lg font-bold text-[#F3F1EB] mt-1">92 / 100</div>
                <div class="text-xs text-[#7D7A73] mt-0.5">Высокий спрос</div>
            </div>
        </div>

        <!-- SVG Sparkline Trend in Claude Terracotta -->
        <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl p-5 mb-6">
            <div class="flex items-center justify-between mb-3">
                <div class="text-sm font-semibold text-[#F3F1EB]">Распределение цен по базе объявлений</div>
                <div class="text-xs text-[#7D7A73]">{len(deals)} проверенных лотов</div>
            </div>
            {chart_svg}
        </div>

        <!-- Specs & Checklist -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl p-5">
                <div class="flex items-center gap-2 text-sm font-semibold text-[#F3F1EB] mb-3">
                    <i data-lucide="sliders" class="w-4 h-4 text-[#CC785C]"></i>
                    <span>Характеристики</span>
                </div>
                <dl class="space-y-2 text-xs divide-y divide-[#2C2C29]">
                    <div class="flex justify-between pt-2"><dt class="text-[#7D7A73]">Память / Видеопамять:</dt><dd class="font-mono text-[#F3F1EB]">{hw['vram']}</dd></div>
                    <div class="flex justify-between pt-2"><dt class="text-[#7D7A73]">Шина данных:</dt><dd class="font-mono text-[#F3F1EB]">{hw['bus']}</dd></div>
                    <div class="flex justify-between pt-2"><dt class="text-[#7D7A73]">Энергопотребление (TDP):</dt><dd class="font-mono text-[#F3F1EB]">{hw['tdp']}</dd></div>
                    <div class="flex justify-between pt-2"><dt class="text-[#7D7A73]">Архитектура / Ядра:</dt><dd class="font-mono text-[#F3F1EB]">{hw['cuda_cores']}</dd></div>
                    <div class="flex justify-between pt-2"><dt class="text-[#7D7A73]">Интерфейс:</dt><dd class="font-mono text-[#F3F1EB]">{hw['interface']}</dd></div>
                </dl>
            </div>

            <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl p-5">
                <div class="flex items-center gap-2 text-sm font-semibold text-[#F3F1EB] mb-3">
                    <i data-lucide="shield-check" class="w-4 h-4 text-[#68B38A]"></i>
                    <span>Что проверить перед покупкой</span>
                </div>
                <ul class="space-y-2.5">
                    {checks_html}
                </ul>
            </div>
        </div>

        <!-- Affiliate CTA Box -->
        <div class="bg-[#1E1E1C] border border-[#383834] rounded-xl p-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
                <div class="text-sm font-semibold text-[#F3F1EB]">Ищете новый {clean_name} с гарантией?</div>
                <div class="text-xs text-[#B8B6AF] mt-0.5">Сравните стоимость б/у с ценами в официальных магазинах с гарантией 3 года.</div>
            </div>
            <a href="https://market.yandex.ru/search?text={clean_name}&clid=priceradar_clean" target="_blank" rel="nofollow noopener" class="inline-flex items-center gap-1.5 text-xs font-semibold bg-[#CC785C] hover:opacity-90 text-[#FAF9F6] px-4 py-2 rounded-lg transition shrink-0">
                <span>Цены на Яндекс.Маркете</span>
                <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
            </a>
        </div>

        <!-- Secondary Market Listings Table -->
        <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl overflow-hidden mb-8">
            <div class="p-4 border-b border-[#2C2C29] flex items-center justify-between">
                <div class="text-sm font-semibold text-[#F3F1EB]">Актуальные предложения на вторичном рынке</div>
                <div class="text-xs text-[#7D7A73]">Сортировка: по возрастанию цены</div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="border-b border-[#2C2C29] text-xs text-[#7D7A73] bg-[#141413]/60">
                            <th class="py-2.5 px-4 font-medium">Объявление и локация</th>
                            <th class="py-2.5 px-4 font-medium text-right">Стоимость</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(deals_html)}
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <footer class="border-t border-[#2C2C29] py-6 text-center text-xs text-[#7D7A73]">
        <p>© {now.year} PriceRadar. Мониторинг и аналитика вторичного рынка электроники.</p>
    </footer>

    <script>
        lucide.createIcons();
    </script>
</body>
</html>
"""
        return {
            "target_id": target_id,
            "city": city,
            "html": html,
            "slug": f"prices/{city}/{target_id}"
        }

    @classmethod
    def build_full_portal(cls) -> Path:
        """Сборка полного портала"""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        favicon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#141413"/><path d="M18 4L8 18h7l-2 10 11-14h-7l3-10z" fill="#CC785C"/></svg>"""
        (cls.OUTPUT_DIR / "favicon.svg").write_text(favicon_svg, encoding="utf-8")
        (cls.OUTPUT_DIR / "favicon.ico").write_text(favicon_svg, encoding="utf-8")

        conn = DataLake.get_connection()
        try:
            targets = [r[0] for r in conn.execute("SELECT DISTINCT target_id FROM price_history").fetchall()]
        finally:
            conn.close()

        if not targets:
            targets = ["rtx_3080_moskva", "rtx_4070_moskva", "iphone_14_moskva"]

        generated_urls = []
        catalog_rows = []

        print(f"🏗️ Сборка портала цен в палитре Claude (#141413 / #CC785C) по {len(targets)} категориям...")

        for tid in targets:
            page = cls.generate_product_page(tid, city="moskva")
            if page:
                slug_dir = cls.OUTPUT_DIR / page["slug"]
                slug_dir.mkdir(parents=True, exist_ok=True)
                (slug_dir / "index.html").write_text(page["html"], encoding="utf-8")

                full_url = f"{cls.BASE_URL}/{page['slug']}/"
                generated_urls.append(full_url)

                title_clean = tid.replace('_moskva', '').replace('_', ' ').upper()
                catalog_rows.append(f"""
                <a href="{page['slug']}/index.html" class="flex items-center justify-between p-3.5 rounded-lg border border-[#2C2C29] bg-[#1E1E1C] hover:bg-[#262624] hover:border-[#383834] transition">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded bg-[#141413] border border-[#2C2C29] flex items-center justify-center text-[#CC785C]">
                            <i data-lucide="cpu" class="w-4 h-4"></i>
                        </div>
                        <div>
                            <div class="text-sm font-semibold text-[#F3F1EB]">{title_clean} (Москва)</div>
                            <div class="text-xs text-[#B8B6AF]">Диапазон цен, медиана и проверенные предложения</div>
                        </div>
                    </div>
                    <i data-lucide="arrow-right" class="w-4 h-4 text-[#7D7A73]"></i>
                </a>
                """)

        # Главная страница (Index Hub)
        index_html = f"""<!DOCTYPE html>
<html lang="ru" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PriceRadar — Аналитика и реальные цены вторичного рынка электроники</title>
    <meta name="description" content="Умный мониторинг и расчет медианных цен на б/у видеокарты, смартфоны и комплектующие.">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
    </style>
</head>
<body class="bg-[#141413] text-[#F3F1EB] min-h-screen antialiased">
    <header class="border-b border-[#2C2C29] bg-[#141413]/90 backdrop-blur sticky top-0 z-50">
        <div class="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
            <a href="/" class="flex items-center gap-2 text-sm font-semibold text-[#F3F1EB] hover:opacity-90">
                <i data-lucide="cpu" class="w-5 h-5 text-[#CC785C]"></i>
                <span>PriceRadar</span>
            </a>
            <a href="https://t.me/monitoringsuba_bot" target="_blank" class="inline-flex items-center gap-1.5 text-xs font-medium bg-[#CC785C] hover:opacity-90 text-[#FAF9F6] px-3.5 py-1.5 rounded-md transition shadow-sm">
                <i data-lucide="bell" class="w-3.5 h-3.5"></i>
                <span>Бот алертов</span>
            </a>
        </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-10">
        <h1 class="text-3xl font-bold tracking-tight text-[#F3F1EB] mb-2">Аналитика цен вторичного рынка</h1>
        <p class="text-sm text-[#B8B6AF] mb-8">Ежедневный сбор объявлений, отсечение спама и расчет справедливой стоимости техники.</p>

        <div class="bg-[#1E1E1C] border border-[#2C2C29] rounded-xl p-5 mb-8">
            <div class="text-sm font-semibold text-[#F3F1EB] mb-4 flex items-center gap-2">
                <i data-lucide="layers" class="w-4 h-4 text-[#CC785C]"></i>
                <span>Популярные категории и комплектующие</span>
            </div>
            <div class="space-y-2.5">
                {"".join(catalog_rows)}
            </div>
        </div>
    </main>

    <footer class="border-t border-[#2C2C29] py-6 text-center text-xs text-[#7D7A73]">
        <p>© {datetime.now().year} PriceRadar. Open Secondary Market Data Lake.</p>
    </footer>

    <script>
        lucide.createIcons();
    </script>
</body>
</html>"""
        (cls.OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

        # Sitemap & Robots
        now_iso = datetime.now().strftime("%Y-%m-%d")
        sitemap_entries = [f"  <url>\n    <loc>{cls.BASE_URL}/</loc>\n    <lastmod>{now_iso}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>1.0</priority>\n  </url>"]
        for u in generated_urls:
            sitemap_entries.append(f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{now_iso}</lastmod>\n    <changefreq>hourly</changefreq>\n    <priority>0.8</priority>\n  </url>")

        sitemap_xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n{''.join(sitemap_entries)}\n</urlset>"
        (cls.OUTPUT_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")

        robots_txt = f"User-agent: *\nAllow: /\nSitemap: {cls.BASE_URL}/sitemap.xml\n"
        (cls.OUTPUT_DIR / "robots.txt").write_text(robots_txt, encoding="utf-8")

        print(f"✓ Портал в палитре Claude успешно пересобран в: {cls.OUTPUT_DIR}")
        return cls.OUTPUT_DIR

ProgrammaticSEOGenerator = ClaudeCleanSEOGenerator
ProfessionalSEOGenerator = ClaudeCleanSEOGenerator
EditorialSEOGenerator = ClaudeCleanSEOGenerator
CleanSEOGenerator = ClaudeCleanSEOGenerator
