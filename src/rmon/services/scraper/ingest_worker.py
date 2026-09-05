"""
Background Ingestion Worker for RMon Platform.
Асинхронно/многопоточно вычитывает распарсенные лоты из TaskQueue (Redis / Fallback)
и пачками (batch) сохраняет их в DuckDB DataLake, полностью устраняя блокировки БД.
"""
import time
import signal
import sys
from typing import List, Dict, Any, Optional
from collections import defaultdict

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.core.models import QueueTask, ListingItem
from rmon.core.queue import get_task_queue, BaseTaskQueue
from rmon.core.lake import DataLake

logger = get_logger("IngestWorker")


class IngestWorker:
    """Воркер пакетной записи данных в аналитический DataLake"""

    QUEUE_NAME = "scrape_ingest"

    def __init__(
        self,
        queue: Optional[BaseTaskQueue] = None,
        batch_size: int = 50,
        flush_interval_sec: float = 3.0
    ):
        self.queue = queue or get_task_queue()
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self._running = False

    def enqueue_scraped_items(self, target_id: str, items: List[Dict[str, Any]], source: str = "avito") -> bool:
        """Метод для внешних скрейперов: публикация пачки в очередь буфера"""
        if not items:
            return True
        task = QueueTask(
            task_type="ingest_items",
            payload={
                "target_id": target_id,
                "source": source,
                "items": items
            }
        )
        return self.queue.push(self.QUEUE_NAME, task)

    def process_batch(self, tasks: List[QueueTask]) -> int:
        """Группировка и сохранение пачки задач в DuckDB"""
        if not tasks:
            return 0

        grouped_items: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
        for t in tasks:
            if t.task_type != "ingest_items":
                continue
            payload = t.payload
            target_id = payload.get("target_id", "default")
            source = payload.get("source", "avito")
            items = payload.get("items", [])
            grouped_items[(target_id, source)].extend(items)

        total_saved = 0
        for (target_id, source), items in grouped_items.items():
            try:
                saved = DataLake.save_items(items, target_id=target_id, source=source)
                total_saved += saved
            except Exception as e:
                logger.error(f"Ошибка сохранения пачки [{source}:{target_id}] в DataLake: {e}")

        if total_saved > 0:
            logger.info(f"✓ IngestWorker сохранил {total_saved} записей в DataLake")
        return total_saved

    def run(self):
        """Основной рабочий цикл воркера"""
        self._running = True
        logger.info(f"🚀 IngestWorker запущен (очередь='{self.QUEUE_NAME}', batch_size={self.batch_size})")

        # Перехват сигналов завершения
        def handle_signal(sig, frame):
            logger.info(f"Получен сигнал остановки ({sig}), завершение воркера...")
            self.stop()

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        except (ValueError, AttributeError):
            pass

        while self._running:
            try:
                tasks = self.queue.pop_batch(
                    self.QUEUE_NAME,
                    max_items=self.batch_size,
                    timeout=self.flush_interval_sec
                )
                if tasks:
                    self.process_batch(tasks)
                else:
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"Непредвиденная ошибка в цикле IngestWorker: {e}")
                time.sleep(1.0)

        logger.info("IngestWorker штатно остановлен.")

    def stop(self):
        self._running = False


if __name__ == "__main__":
    worker = IngestWorker()
    worker.run()
