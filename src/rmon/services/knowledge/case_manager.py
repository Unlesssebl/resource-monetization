"""
Monetization Case Knowledge Base & Idea Radar for RMon Platform.
Управляет коллекцией бизнес-кейсов, моделей монетизации и связок:
- Хранение в виде Markdown-досье с YAML/Frontmatter (data/knowledge/cases/*.md)
- Индексация в DuckDB Data Lake для мгновенных SQL-запросов и скоринга
- AI-обогащение сырых идей через Gemini / Qwen (оценка трения, рисков, автономности и юнит-экономики)
- Консольный и Telegram интерфейс
- Zero-dependency: нативный парсинг frontmatter без внешних библиотек
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import duckdb

from rmon.core.config import settings
from rmon.core.gemini import GeminiClient
from rmon.core.lake import DataLake
from rmon.core.logger import get_logger

logger = get_logger("CaseManager")

class CaseManager:
    """Менеджер базы знаний кейсов монетизации и идей"""

    CASES_DIR = settings.DATA_DIR / "knowledge" / "cases"

    @staticmethod
    def _parse_yaml_frontmatter(text: str) -> Dict[str, Any]:
        """Простой и надежный нативный парсер YAML frontmatter без pyyaml"""
        meta = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            
            # Приведение типов
            if v.lower() == "true":
                meta[k] = True
            elif v.lower() == "false":
                meta[k] = False
            else:
                try:
                    if "." in v:
                        meta[k] = float(v)
                    else:
                        meta[k] = int(v)
                except ValueError:
                    meta[k] = v
        return meta

    @staticmethod
    def _dump_yaml_frontmatter(meta: Dict[str, Any]) -> str:
        """Нативный дамп словаря в YAML frontmatter"""
        lines = []
        for k, v in meta.items():
            if isinstance(v, (int, float, bool)):
                lines.append(f"{k}: {v}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    @classmethod
    def init_storage(cls):
        """Инициализация папки досье и таблицы в DuckDB"""
        cls.CASES_DIR.mkdir(parents=True, exist_ok=True)
        conn = DataLake.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monetization_cases (
                    slug VARCHAR PRIMARY KEY,
                    title VARCHAR,
                    category VARCHAR,
                    status VARCHAR,
                    budget_start_rub DOUBLE,
                    monthly_potential_rub DOUBLE,
                    time_to_cash_days INTEGER,
                    ai_autonomy_pct INTEGER,
                    traffic_source VARCHAR,
                    monetization_model VARCHAR,
                    hardware_required VARCHAR,
                    risk_score INTEGER,
                    market_evidence TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    file_path VARCHAR
                );
            """)
        finally:
            conn.close()

    @classmethod
    def sync_all_to_duckdb(cls):
        """Синхронизация всех Markdown-файлов из data/knowledge/cases/ в DuckDB"""
        cls.init_storage()
        files = list(cls.CASES_DIR.glob("*.md"))
        conn = DataLake.get_connection()
        try:
            for f in files:
                case_data = cls.parse_markdown_case(f)
                if case_data:
                    meta = case_data.get("meta", {})
                    slug = meta.get("slug") or f.stem
                    conn.execute("""
                        INSERT OR REPLACE INTO monetization_cases VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """, [
                        slug,
                        meta.get("title", f.stem),
                        meta.get("category", "other"),
                        meta.get("status", "IDEA"),
                        float(meta.get("budget_start_rub", 0.0)),
                        float(meta.get("monthly_potential_rub", 0.0)),
                        int(meta.get("time_to_cash_days", 7)),
                        int(meta.get("ai_autonomy_pct", 90)),
                        meta.get("traffic_source", ""),
                        meta.get("monetization_model", ""),
                        meta.get("hardware_required", ""),
                        int(meta.get("risk_score", 30)),
                        meta.get("market_evidence", ""),
                        datetime.now(),
                        datetime.now(),
                        str(f)
                    ])
        finally:
            conn.close()

    @classmethod
    def parse_markdown_case(cls, file_path: Path) -> Optional[Dict[str, Any]]:
        """Парсинг Markdown-досье с Frontmatter"""
        if not file_path.exists():
            return None
        content = file_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                meta = cls._parse_yaml_frontmatter(parts[1])
                body = parts[2].strip()
                return {"meta": meta, "body": body, "path": file_path}
        return {"meta": {"title": file_path.stem}, "body": content, "path": file_path}

    @classmethod
    def save_case_dossier(cls, meta: Dict[str, Any], body: str) -> Path:
        """Сохранение досье в Markdown и обновление DuckDB"""
        cls.init_storage()
        slug = meta.get("slug") or re.sub(r"[^\w\-]", "", meta.get("title", "case").lower().replace(" ", "-"))
        meta["slug"] = slug
        meta["updated_at"] = datetime.now().isoformat()
        if "created_at" not in meta:
            meta["created_at"] = datetime.now().isoformat()

        file_path = cls.CASES_DIR / f"{slug}.md"
        yaml_header = cls._dump_yaml_frontmatter(meta)
        full_doc = f"---\n{yaml_header}\n---\n\n{body.strip()}\n"

        file_path.write_text(full_doc, encoding="utf-8")
        cls.sync_all_to_duckdb()
        logger.info(f"✓ Кейс '{meta.get('title')}' успешно сохранен: {file_path.name}")
        return file_path

    @classmethod
    async def add_case_with_ai(cls, user_idea: str) -> Dict[str, Any]:
        """AI-обогащение и упаковка сырой идеи в полноценное бизнес-досье"""
        system_instruction = """Ты — прагматичный венчурный аналитик и системный архитектор платформы Resource Monetization.
Твоя цель: превратить сырую идею в строгое, реалистичное бизнес-досье со скорингом и трезвым Reality Check.

Ответь строго JSON-объектом следующего формата:
{
  "meta": {
    "slug": "короткий-slug-на-латинице",
    "title": "Ёмкое профессиональное название кейса",
    "category": "programmatic_seo" | "video_factory" | "b2b_leadgen" | "micro_saas" | "speed_arbitrage" | "b2b_saas",
    "status": "RESEARCHING" | "VALIDATED" | "MVP" | "IDEA",
    "budget_start_rub": 0.0,
    "monthly_potential_rub": 40000.0,
    "time_to_cash_days": 3,
    "ai_autonomy_pct": 95,
    "traffic_source": "Органический поиск / YouTube Shorts / Inbound / B2B Webhook",
    "monetization_model": "CPA Партнерки / Подписка / Фикс за лид / Разовый чек",
    "hardware_required": "NVIDIA RTX 3050 CUDA, 8TB Cloud, DuckDB",
    "risk_score": 25,
    "market_evidence": "Краткое доказательство спроса (Wordstat/рынок/аналоги)"
  },
  "body_markdown": "# Полное структурированное досье в Markdown формате:\n## 1. Суть связки\n## 2. Механика работы и роль AI (90%+)\n## 3. Юнит-экономика и воронка\n## 4. Трезвый Reality Check и скрытые риски\n## 5. Пошаговый план запуска за 24 часа"
}"""

        prompt = f"Разверни и проанализируй следующую идею/связку монетизации:\n\"{user_idea}\""

        client = GeminiClient()
        logger.info("🧠 AI Генерация досье кейса через Gemini...")
        res = await client.generate_content(prompt=prompt, system_instruction=system_instruction, json_mode=True)
        data = res.get("json") or {}

        meta = data.get("meta", {})
        body = data.get("body_markdown", f"# {meta.get('title', 'Кейс')}\n\n{user_idea}")

        saved_path = cls.save_case_dossier(meta, body)
        return {
            "meta": meta,
            "path": str(saved_path),
            "body": body
        }

    @classmethod
    def list_cases(cls, category: Optional[str] = None, sort_by: str = "potential") -> List[Dict[str, Any]]:
        """Получение списка кейсов из DuckDB с сортировкой"""
        cls.sync_all_to_duckdb()
        conn = DataLake.get_connection()
        order_clause = "monthly_potential_rub DESC" if sort_by == "potential" else ("ai_autonomy_pct DESC" if sort_by == "autonomy" else "time_to_cash_days ASC")
        where_clause = f"WHERE category = '{category}'" if category else ""
        
        try:
            query = f"SELECT * FROM monetization_cases {where_clause} ORDER BY {order_clause}"
            rows = conn.execute(query).fetchall()
            cols = [desc[0] for desc in conn.description]
            return [dict(zip(cols, row)) for row in rows]
        finally:
            conn.close()

    @classmethod
    def format_cli_table(cls) -> str:
        """Красивая сводная таблица всех кейсов в терминале"""
        cases = cls.list_cases()
        if not cases:
            return "📭 База знаний кейсов пуста. Добавьте первый кейс через: python scripts/rmon.py cases add \"...\""

        lines = [
            "=" * 110,
            " 💎 БАЗА ЗНАНИЙ МОДЕЛЕЙ МОНЕТИЗАЦИИ & IDEA RADAR",
            "=" * 110,
            f"{'№':<3} | {'Кейс':<42} | {'Категория':<16} | {'Доход/мес':<12} | {'Срок':<7} | {'AI %':<6} | {'Бюджет':<7}",
            "-" * 110
        ]

        for idx, c in enumerate(cases, 1):
            title = c['title'][:40]
            cat = c['category'][:15]
            pot = f"{c['monthly_potential_rub']:,.0f} ₽"
            ttc = f"{c['time_to_cash_days']} дн."
            aut = f"{c['ai_autonomy_pct']}%"
            bud = f"{c['budget_start_rub']:,.0f} ₽"
            lines.append(f"{idx:<3} | {title:<42} | {cat:<16} | {pot:<12} | {ttc:<7} | {aut:<6} | {bud:<7}")

        lines.extend([
            "=" * 110,
            f" Всего кейсов в базе: {len(cases)} | Хранилище: data/knowledge/cases/ (DuckDB Indexed)",
            "=" * 110
        ])
        return "\n".join(lines)
