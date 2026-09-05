"""
Unified Task Queue & Ingestion Buffer for RMon Platform.
Поддерживает Redis (LPUSH/BRPOP) с автоматическим Graceful Fallback на
локальную файлово-памятьевую очередь (LocalFallbackTaskQueue) при отсутствии Docker/Redis.
"""
from abc import ABC, abstractmethod
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import deque
import threading

from rmon.core.config import settings
from rmon.core.logger import get_logger
from rmon.core.models import QueueTask

logger = get_logger("TaskQueue")


class BaseTaskQueue(ABC):
    """Базовый абстрактный класс очереди задач"""

    @abstractmethod
    def push(self, queue_name: str, task: QueueTask) -> bool:
        """Поместить задачу в конец очереди"""
        pass

    @abstractmethod
    def pop(self, queue_name: str, timeout: float = 0.0) -> Optional[QueueTask]:
        """Извлечь задачу из начала очереди (FIFO)"""
        pass

    @abstractmethod
    def qsize(self, queue_name: str) -> int:
        """Получить текущий размер очереди"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Проверка доступности бэкенда очереди"""
        pass

    def push_batch(self, queue_name: str, tasks: List[QueueTask]) -> int:
        """Пакетное добавление задач"""
        count = 0
        for t in tasks:
            if self.push(queue_name, t):
                count += 1
        return count

    def pop_batch(self, queue_name: str, max_items: int = 50, timeout: float = 1.0) -> List[QueueTask]:
        """Пакетное извлечение задач с таймаутом"""
        items: List[QueueTask] = []
        deadline = time.time() + timeout
        while len(items) < max_items:
            remaining = max(0.0, deadline - time.time())
            item = self.pop(queue_name, timeout=remaining if items == [] else 0.0)
            if item:
                items.append(item)
            else:
                break
        return items


class RedisTaskQueue(BaseTaskQueue):
    """Очередь на базе Redis (высокая производительность и межхостовый обмен)"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            import redis
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.5,
                socket_connect_timeout=1.5
            )
            # Проверка доступности через ping
            self._client.ping()
            logger.info(f"✓ Подключено к Redis TaskQueue [{self.redis_url}]")
        except Exception as e:
            logger.debug(f"Redis недоступен ({e}), переключение на локальный fallback")
            self._client = None

    def is_connected(self) -> bool:
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def push(self, queue_name: str, task: QueueTask) -> bool:
        if not self.is_connected():
            return False
        try:
            payload_str = json.dumps(task.to_dict(), ensure_ascii=False)
            self._client.rpush(f"rmon:queue:{queue_name}", payload_str)
            return True
        except Exception as e:
            logger.error(f"Ошибка push в Redis ({queue_name}): {e}")
            return False

    def pop(self, queue_name: str, timeout: float = 0.0) -> Optional[QueueTask]:
        if not self.is_connected():
            return None
        key = f"rmon:queue:{queue_name}"
        try:
            if timeout > 0:
                result = self._client.blpop(key, timeout=int(max(1, timeout)))
                if result:
                    _, raw_data = result
                    return QueueTask.from_dict(json.loads(raw_data))
                return None
            else:
                raw_data = self._client.lpop(key)
                if raw_data:
                    return QueueTask.from_dict(json.loads(raw_data))
                return None
        except Exception as e:
            logger.error(f"Ошибка pop из Redis ({queue_name}): {e}")
            return None

    def qsize(self, queue_name: str) -> int:
        if not self.is_connected():
            return 0
        try:
            return int(self._client.llen(f"rmon:queue:{queue_name}"))
        except Exception:
            return 0


class LocalFallbackTaskQueue(BaseTaskQueue):
    """
    Автономная локальная очередь с персистентностью в JSONL файл.
    Работает без Docker и внешних сервисов с нулевой задержкой.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (settings.DATA_DIR / "queue")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._queues: Dict[str, deque] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._load_pending()

    def _get_lock(self, queue_name: str) -> threading.Lock:
        with self._global_lock:
            if queue_name not in self._locks:
                self._locks[queue_name] = threading.Lock()
            if queue_name not in self._queues:
                self._queues[queue_name] = deque()
            return self._locks[queue_name]

    def _load_pending(self):
        """Загрузка сохраненных задач при старте процесса"""
        for filepath in self.storage_dir.glob("*.jsonl"):
            queue_name = filepath.stem
            lock = self._get_lock(queue_name)
            with lock:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                task_dict = json.loads(line)
                                self._queues[queue_name].append(QueueTask.from_dict(task_dict))
                    # Очищаем файл, так как задачи в памяти
                    open(filepath, "w", encoding="utf-8").close()
                    if self._queues[queue_name]:
                        logger.info(f"Восстановлено из локального буфера [{queue_name}]: {len(self._queues[queue_name])} задач")
                except Exception as e:
                    logger.warning(f"Ошибка восстановления очереди {filepath}: {e}")

    def _persist_task(self, queue_name: str, task: QueueTask):
        filepath = self.storage_dir / f"{queue_name}.jsonl"
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(task.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Ошибка персистенции задачи в {filepath}: {e}")

    def is_connected(self) -> bool:
        return True

    def push(self, queue_name: str, task: QueueTask) -> bool:
        lock = self._get_lock(queue_name)
        with lock:
            self._queues[queue_name].append(task)
            self._persist_task(queue_name, task)
            return True

    def pop(self, queue_name: str, timeout: float = 0.0) -> Optional[QueueTask]:
        lock = self._get_lock(queue_name)
        start_time = time.time()
        while True:
            with lock:
                if self._queues[queue_name]:
                    return self._queues[queue_name].popleft()
            if timeout <= 0 or (time.time() - start_time) >= timeout:
                break
            time.sleep(0.05)
        return None

    def qsize(self, queue_name: str) -> int:
        lock = self._get_lock(queue_name)
        with lock:
            return len(self._queues[queue_name])


_default_queue: Optional[BaseTaskQueue] = None

def get_task_queue(prefer_redis: bool = True, redis_url: Optional[str] = None) -> BaseTaskQueue:
    """
    Фабрика получения очереди:
    1. Пробует Redis (если prefer_redis=True и Redis доступен).
    2. При сбое автоматически переключается на LocalFallbackTaskQueue.
    """
    global _default_queue
    if _default_queue is not None and _default_queue.is_connected():
        return _default_queue

    if prefer_redis:
        try:
            import redis
            redis_q = RedisTaskQueue(redis_url=redis_url)
            if redis_q.is_connected():
                _default_queue = redis_q
                return _default_queue
        except (ImportError, Exception):
            pass

    logger.debug("Используется локальная буферная очередь (LocalFallbackTaskQueue)")
    _default_queue = LocalFallbackTaskQueue()
    return _default_queue
