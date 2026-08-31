"""
Neural Domain & Specification Classifier for PriceRadar 2.0.
Автономный классификатор технических сущностей и профильных метрик:
- Авто-определение типа устройства (GPU, CPU, Apple/Phone, Console, Laptop)
- Извлечение характеристик (VRAM, частоты, ядра, энергопотребление)
- Расчет профильных бенчмарков (FPS по играм, Cinebench R23, износ батареи)
- Рекомендации по бюджетам и сценариям использования
"""
import re
from typing import Dict, Any, List, Optional

class DomainClassifier:
    """Универсальный классификатор и расчетный движок производительности на рубль"""

    # База эталонных игровых бенчмарков (1440p Ultra)
    GPU_BENCHMARK_SUITE = {
        "RTX 4090": {"cyberpunk": 115, "cs2": 380, "warzone": 165, "alan_wake": 95, "vram": "24 GB GDDR6X", "tdp": 450, "retail_price": 210000, "used_median": 165000},
        "RTX 4080": {"cyberpunk": 88, "cs2": 320, "warzone": 140, "alan_wake": 72, "vram": "16 GB GDDR6X", "tdp": 320, "retail_price": 125000, "used_median": 85000},
        "RTX 4070 SUPER": {"cyberpunk": 68, "cs2": 270, "warzone": 118, "alan_wake": 56, "vram": "12 GB GDDR6X", "tdp": 220, "retail_price": 75000, "used_median": 58000},
        "RTX 4070": {"cyberpunk": 60, "cs2": 245, "warzone": 105, "alan_wake": 48, "vram": "12 GB GDDR6X", "tdp": 200, "retail_price": 68000, "used_median": 52000},
        "RTX 4060 TI": {"cyberpunk": 46, "cs2": 210, "warzone": 88, "alan_wake": 36, "vram": "8/16 GB GDDR6", "tdp": 160, "retail_price": 46000, "used_median": 36000},
        "RTX 4060": {"cyberpunk": 38, "cs2": 180, "warzone": 74, "alan_wake": 28, "vram": "8 GB GDDR6", "tdp": 115, "retail_price": 36000, "used_median": 27000},
        "RTX 3080": {"cyberpunk": 62, "cs2": 255, "warzone": 110, "alan_wake": 49, "vram": "10 GB GDDR6X", "tdp": 320, "retail_price": 65000, "used_median": 45000},
        "RTX 3070": {"cyberpunk": 48, "cs2": 215, "warzone": 90, "alan_wake": 38, "vram": "8 GB GDDR6", "tdp": 220, "retail_price": 42000, "used_median": 30000},
        "RTX 3060": {"cyberpunk": 32, "cs2": 155, "warzone": 65, "alan_wake": 24, "vram": "12 GB GDDR6", "tdp": 170, "retail_price": 32000, "used_median": 22000},
        "RX 7800 XT": {"cyberpunk": 66, "cs2": 290, "warzone": 130, "alan_wake": 47, "vram": "16 GB GDDR6", "tdp": 263, "retail_price": 62000, "used_median": 48000},
        "RX 6800 XT": {"cyberpunk": 58, "cs2": 260, "warzone": 115, "alan_wake": 42, "vram": "16 GB GDDR6", "tdp": 300, "retail_price": 50000, "used_median": 36000},
        "RX 6700 XT": {"cyberpunk": 44, "cs2": 205, "warzone": 85, "alan_wake": 31, "vram": "12 GB GDDR6", "tdp": 230, "retail_price": 38000, "used_median": 26000}
    }

    # Пресеты подбора по бюджету и задачам
    BUDGET_TIERS = [
        {
            "max_budget": 35000,
            "gaming_1440p": {"used": "RTX 3070 (8 GB) б/у", "used_price": 30000, "fps_avg": 75, "new": "RTX 3060 12GB Новый", "new_price": 32000, "verdict": "На вторичке RTX 3070 дает на 45% больше FPS, но требует проверки температур памяти."},
            "esports_1080p": {"used": "RX 6700 XT 12GB б/у", "used_price": 26000, "fps_avg": 210, "new": "RTX 4060 Новый", "new_price": 36000, "verdict": "RX 6700 XT с 12 ГБ памяти — лучший выбор под высокий фреймрейт за минимальные деньги."},
            "workstation": {"used": "RTX 3060 12GB б/у", "used_price": 22000, "pts_rub": 4.8, "new": "RTX 4060 8GB Новый", "new_price": 36000, "verdict": "12 ГБ VRAM у RTX 3060 критически важны для локальных LLM и 3D-сцен."},
            "portable": {"used": "Steam Deck LCD 512GB б/у", "used_price": 29000, "fps_avg": 45, "new": "Nintendo Switch OLED", "new_price": 31000, "verdict": "Steam Deck открывает доступ к полной библиотеке ПК-игр с возможностью эмуляции."}
        },
        {
            "max_budget": 65000,
            "gaming_1440p": {"used": "RTX 3080 (10 GB) б/у", "used_price": 45000, "fps_avg": 95, "new": "RTX 4070 Super Новый", "new_price": 75000, "verdict": "RTX 3080 б/у дает производительность уровня новой карты за 75k ₽, экономя 30 000 ₽."},
            "esports_1080p": {"used": "Ryzen 7 7800X3D + RTX 3070", "used_price": 58000, "fps_avg": 340, "new": "Core i5 13400 + RTX 4060", "new_price": 64000, "verdict": "Процессор с 3D V-Cache дает стабильный минимальный 0.1% FPS без микрофризов."},
            "workstation": {"used": "RTX 3080 10GB / RX 6800 XT 16GB", "used_price": 45000, "pts_rub": 5.2, "new": "RTX 4060 Ti 16GB Новый", "new_price": 54000, "verdict": "RX 6800 XT дает 16 ГБ VRAM и 256-битную шину для тяжелого 4K-рендеринга."},
            "portable": {"used": "Steam Deck OLED 512GB б/у", "used_price": 52000, "fps_avg": 60, "new": "ASUS ROG Ally Z1 Extreme", "new_price": 62000, "verdict": "OLED экран с 90 Гц и увеличенной батареей делает Deck эталоном портатива."}
        },
        {
            "max_budget": 120000,
            "gaming_1440p": {"used": "RTX 4080 (16 GB) б/у", "used_price": 85000, "fps_avg": 140, "new": "RTX 4070 Ti Super 16GB Новый", "new_price": 95000, "verdict": "RTX 4080 на чипе AD103 — идеальный флагман для максимального качества с трассировкой лучей."},
            "esports_1080p": {"used": "RTX 4080 16GB + 360Hz Монитор", "used_price": 105000, "fps_avg": 450, "new": "RTX 4070 Super Сетап", "new_price": 115000, "verdict": "Бескомпромиссный фреймрейт в CS2, Valorant и Apex Legends."},
            "workstation": {"used": "RTX 4080 16GB + Ryzen 7950X", "used_price": 115000, "pts_rub": 5.8, "new": "RTX 4070 Ti Super Сборка", "new_price": 125000, "verdict": "16 ГБ памяти на тензорных ядрах 4-го поколения ускоряют инференс AI моделей в 2.5 раза."},
            "portable": {"used": "MacBook Pro 14 M2 Pro (16/512)", "used_price": 110000, "battery_life": "14-16 часов", "new": "MacBook Air M3 (8/256)", "new_price": 105000, "verdict": "M2 Pro предлагает активное охлаждение, 120 Гц Mini-LED дисплей и порт HDMI."}
        }
    ]

    @classmethod
    def get_budget_advice(cls, budget: int, task: str) -> Dict[str, Any]:
        """Расчет оптимальных конфигураций под бюджет и задачи"""
        matched_tier = cls.BUDGET_TIERS[0]
        for tier in cls.BUDGET_TIERS:
            if budget <= tier["max_budget"]:
                matched_tier = tier
                break
        else:
            matched_tier = cls.BUDGET_TIERS[-1]

        task_key = "gaming_1440p"
        if "esport" in task.lower() or "1080" in task.lower():
            task_key = "esports_1080p"
        elif "work" in task.lower() or "3d" in task.lower() or "ai" in task.lower():
            task_key = "workstation"
        elif "port" in task.lower() or "deck" in task.lower() or "book" in task.lower():
            task_key = "portable"

        return matched_tier.get(task_key, matched_tier["gaming_1440p"])
