#!/usr/bin/env python3
"""
Evidence Triplet Formatter (Evidence & Timestamps Standard)
Форматирует блоки доказательной базы в утвержденный формат:
[Дата среза + Прямые ссылки на проекты + Твердые числовые метрики]
"""

import sys
import json
from datetime import datetime

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

def format_evidence_block(title: str, metrics: list, sources: list, custom_date: str = None) -> str:
    now = datetime.now()
    date_str = custom_date if custom_date else f"{MONTHS_RU[now.month - 1]} {now.year}"
    
    lines = [
        f"### 📌 Валидация спроса: {title}",
        f"> 🕒 **Срез актуальности данных:** {date_str}",
        "",
        "**Подтвержденные числовые метрики:**"
    ]
    
    for m in metrics:
        lines.append(f"* {m}")
        
    lines.append("")
    lines.append("**Прямые источники и ссылки на бенчмарки:**")
    for s in sources:
        lines.append(f"* {s}")
        
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        demo = format_evidence_block(
            title="Plug-and-Play сборки для Steam Deck / Эмуляторов",
            metrics=[
                "Wordstat: ~140 000+ запросов/мес по теме эмуляторов",
                "4PDA: ветка Steam Deck Игры — 1 200+ страниц, 2.8M просмотров",
                "EmuDeck: 3 500+ звезд на GitHub, сотни платных подписчиков на Patreon"
            ],
            sources=[
                "[4PDA Steam Deck Games](https://4pda.to/forum/index.php?showtopic=1049907)",
                "[GitHub EmuDeck](https://github.com/dragoonDorise/EmuDeck)",
                "[Graphtreon Nolvus Tracker](https://graphtreon.com/creator/nolvus)"
            ]
        )
        print(demo)
    else:
        # Прием JSON через аргумент
        try:
            data = json.loads(sys.argv[1])
            res = format_evidence_block(
                title=data.get("title", "Анализ спроса"),
                metrics=data.get("metrics", []),
                sources=data.get("sources", []),
                custom_date=data.get("date")
            )
            print(res)
        except Exception as e:
            print(f"Ошибка парсинга JSON: {e}")

if __name__ == "__main__":
    main()
