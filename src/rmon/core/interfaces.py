"""
Unified Core Interfaces & Abstract Protocols for RMon Platform.
Реализует Dependency Inversion Principle (DIP): сервисы зависят от абстракций,
а не от жестких реализаций (Ollama/Gemini/FasterWhisper/Playwright).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Protocol, runtime_checkable

from rmon.core.models import ListingItem, MarketSummary, DealOpportunity, AuditVerdict


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
