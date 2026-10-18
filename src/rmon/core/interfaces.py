"""
Unified Core Interfaces & Abstract Protocols for RMon Platform.
Реализует Dependency Inversion Principle (DIP): сервисы зависят от абстракций,
а не от жестких реализаций (Ollama/Gemini/FasterWhisper/Playwright).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable

from rmon.core.models import ListingItem, MarketSummary, DealOpportunity, AuditVerdict, QueueTask


@runtime_checkable
class LLMProvider(Protocol):
    """Интерфейс для генеративных LLM (Gemini Cloud API, локальная Ollama и др.)"""

    async def generate_content(
        self,
        prompt: str,
        system_instruction: str = "",
        image_paths: Optional[List[str]] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """Генерация ответа модели"""
        ...


@runtime_checkable
class MarketDataSource(Protocol):
    """Интерфейс источника рыночных данных (Авито, Юла, WB и др.)"""

    async def scrape_search(
        self,
        query: str,
        city: str = "moskva",
        limit: int = 25,
        headless: bool = True
    ) -> List[Dict[str, Any]]:
        """Сбор объявлений по поисковому запросу"""
        ...


@runtime_checkable
class SpeechTranscriber(Protocol):
    """Интерфейс системы распознавания речи (Faster-Whisper DirectCompute/CUDA)"""

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Транскрибация аудио/видео файла"""
        ...


class BaseStorageRepository(ABC):
    """Абстрактный репозиторий аналитического хранилища"""

    @abstractmethod
    def save_items(self, items: List[Dict[str, Any]], target_id: str, source: str = "avito") -> int:
        pass

    @abstractmethod
    def get_market_summary(self, target_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_anomalies(self, target_id: str, discount_threshold_pct: float = 20.0) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_target_deals(self, target_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение списка лотов по таргету для аналитики и витрин"""
        pass

    @abstractmethod
    def get_unique_targets(self) -> List[str]:
        """Получение списка доступных категорий/таргетов"""
        pass


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
        """Количество задач в очереди"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Проверка доступности бэкенда очереди"""
        pass

    def push_batch(self, queue_name: str, tasks: List[QueueTask]) -> int:
        """Пакетное добавление задач"""
        count = 0
        for task in tasks:
            if self.push(queue_name, task):
                count += 1
        return count

    def pop_batch(self, queue_name: str, max_items: int = 50, timeout: float = 1.0) -> List[QueueTask]:
        """Пакетное извлечение задач с таймаутом"""
        import time
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




@runtime_checkable
class HardwareArbiterPort(Protocol):
    """Интерфейс телеметрии мульти-GPU кластера и арбитража ресурсов"""

    def get_full_system_telemetry(self) -> Dict[str, Any]:
        ...

    async def acquire_gpu_slot(self, service_name: str, required_vram_mb: int = 2000, timeout_sec: float = 60.0) -> bool:
        ...

    def release_gpu_slot(self, service_name: str) -> None:
        ...


# --- Service Resolvers (Dependency Injection & Service Locator) ---

_DEFAULT_LLM_PROVIDER: Optional[LLMProvider] = None
_DEFAULT_HARDWARE_ARBITER = None
_DEFAULT_TASK_QUEUE: Optional[BaseTaskQueue] = None


def get_llm_provider() -> Optional[LLMProvider]:
    global _DEFAULT_LLM_PROVIDER
    if _DEFAULT_LLM_PROVIDER is None:
        try:
            from rmon.core.gemini import GeminiClient
            _DEFAULT_LLM_PROVIDER = GeminiClient()
        except Exception:
            return None
    return _DEFAULT_LLM_PROVIDER


def set_llm_provider(provider: LLMProvider):
    global _DEFAULT_LLM_PROVIDER
    _DEFAULT_LLM_PROVIDER = provider


def get_hardware_arbiter() -> Any:
    global _DEFAULT_HARDWARE_ARBITER
    if _DEFAULT_HARDWARE_ARBITER is None:
        from rmon.core.hardware import HardwareArbiter
        _DEFAULT_HARDWARE_ARBITER = HardwareArbiter
    return _DEFAULT_HARDWARE_ARBITER


def set_hardware_arbiter(arbiter: Any):
    global _DEFAULT_HARDWARE_ARBITER
    _DEFAULT_HARDWARE_ARBITER = arbiter


def get_task_queue_instance() -> BaseTaskQueue:
    global _DEFAULT_TASK_QUEUE
    if _DEFAULT_TASK_QUEUE is None:
        from rmon.core.queue import get_task_queue
        _DEFAULT_TASK_QUEUE = get_task_queue()
    return _DEFAULT_TASK_QUEUE


