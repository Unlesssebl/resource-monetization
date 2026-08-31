"""
Autonomous Marketplace Auto-Miner & Self-Updating Pipeline.
Автономный конвейер полного цикла:
1. Непрерывный парсинг маркетплейсов по пулу целевых категорий (GPU, CPU, Apple, Consoles, Handhelds).
2. Запись в DuckDB Data Lake с автоматическим пересчетом медиан и перцентилей.
3. Локальный AI-аудит аномалий и рисков на RTX 3050 CUDA.
4. Автоматическая пересборка Programmatic SEO портала и калькуляторов в docs/ и data/seo_site/.
5. Автономный коммит и выкат в GitHub Pages без участия человека.
"""
import sys
import json
import asyncio
import random
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.core.lake import DataLake
from rmon.services.scraper.avito import AvitoScraper
from rmon.services.scraper.storage import DuckDBStorage
from rmon.services.seo.generator import MagazineArticleSEOGenerator

logger = get_logger("AutoMiner")

class AutoMinerPipeline:
    """Центральный оркестратор автономного парсинга и динамического обновления экосистемы"""

    @classmethod
    async def mine_targets(cls, target_ids: Optional[List[str]] = None, limit_per_target: int = 8, auto_deploy: bool = True) -> Dict[str, Any]:
        """
        Запуск пакетного парсинга маркетплейса с автоматической пересборкой портала
        """
        config_path = settings.CONFIG_DIR / "targets.json"
        all_targets = []
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_targets = data.get("targets", [])

        if target_ids:
            targets_to_run = [t for t in all_targets if t["id"] in target_ids]
        else:
            targets_to_run = [t for t in all_targets if t.get("enabled", True)]

        logger.info(f"🚀 Запуск автономного парсинга по {len(targets_to_run)} направлениям...")
        results = {}

        for target in targets_to_run:
            tid = target["id"]
            query = target["query"]
            city = target.get("city", "moskva")
            logger.info(f"⏳ Сбор данных: [{tid}] ({query}, {city})...")

            try:
                items = await AvitoScraper.scrape_search(query=query, city=city, limit=limit_per_target, headless=True)
                if items:
                    DuckDBStorage.save_items(items, target_id=tid, source="avito")
                    logger.info(f"✓ Успешно собрано и сохранено {len(items)} лотов для [{tid}]")
                    results[tid] = len(items)
                else:
                    logger.warning(f"⚠️ 0 лотов найдено для [{tid}]")
                    results[tid] = 0
            except Exception as e:
                logger.error(f"❌ Ошибка сбора для [{tid}]: {e}")
                results[tid] = 0

            # Jitter между категориями для защиты от блокировок
            await asyncio.sleep(random.uniform(5.0, 10.0))

        # Пересборка портала
        logger.info("🔨 Автоматическая пересборка Programmatic SEO портала и калькуляторов...")
        MagazineArticleSEOGenerator.build_full_portal()

        # Авто-деплой в GitHub Pages при необходимости
        if auto_deploy:
            cls.git_sync_pages()

        return results

    @classmethod
    def git_sync_pages(cls):
        """Автономная синхронизация и отправка обновлений на GitHub Pages"""
        try:
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_msg = f"auto(data): update data lake and dynamic calculators [{now_str}]"

            # git add docs data/seo_site
            subprocess.run(["git", "add", "docs", "data/seo_site", "data/market_monitor.duckdb"], cwd=str(repo_root), check=False)
            commit_res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(repo_root), capture_output=True, text=True)

            if "nothing to commit" not in commit_res.stdout:
                logger.info("🚀 Отправка свежих данных в GitHub Pages...")
                subprocess.run(["git", "push", "origin", "main"], cwd=str(repo_root), check=False)
                # push subtree to gh-pages in background if needed
                subprocess.Popen(["git", "subtree", "push", "--prefix", "docs", "origin", "gh-pages"], cwd=str(repo_root))
                logger.info("✓ GitHub Pages успешно обновлен!")
            else:
                logger.info("Данные не изменились, коммит пропущен.")
        except Exception as e:
            logger.warning(f"Git auto-deploy warning: {e}")
