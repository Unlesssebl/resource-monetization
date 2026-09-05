"""
Unified Media Storage & Cloud Asset Manager for RMon Platform.
Обеспечивает централизованное хранение медиа-файлов (изображения лотов, обложки, аудио)
в общем каталоге data/cloud/media (синхронизируемом через rclone с 8 TB облаком),
предотвращая 'split-brain' файлов между узлами кластера (Хост 1 и Хост 2).
"""
import hashlib
import urllib.request
from pathlib import Path
from typing import Optional

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("MediaStorage")


class MediaStorage:
    """Хранилище медиа-ассетов с дедупликацией по SHA256 и поддержкой rclone-облака"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or (settings.SHARED_STORAGE_DIR / "media")
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Не удалось создать каталог shared storage ({e}), fallback на локальный data/media")
            self.base_dir = settings.DATA_DIR / "media"
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def compute_sha256(self, data: bytes) -> str:
        """Расчет контрольной суммы для дедупликации"""
        return hashlib.sha256(data).hexdigest()

    def save_bytes(self, data: bytes, extension: str = "jpg", subfolder: str = "listings") -> Path:
        """Сохранение байтов в хранилище с дедупликацией"""
        file_hash = self.compute_sha256(data)
        dest_dir = self.base_dir / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = dest_dir / f"{file_hash}.{extension.lstrip('.')}"
        if not file_path.exists():
            with open(file_path, "wb") as f:
                f.write(data)
            logger.debug(f"Медиа сохранено: {file_path.name} ({len(data)} байт)")
        return file_path

    def download_image(self, url: str, subfolder: str = "listings", timeout: float = 10.0) -> Optional[Path]:
        """Загрузка изображения по URL с дедупликацией"""
        if not url or not url.startswith("http"):
            return None

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                ext = "jpg"
                if "png" in content_type:
                    ext = "png"
                elif "webp" in content_type:
                    ext = "webp"
                return self.save_bytes(data, extension=ext, subfolder=subfolder)
        except Exception as e:
            logger.warning(f"Ошибка загрузки медиа по URL '{url[:50]}...': {e}")
            return None

    def resolve_path(self, relative_or_absolute: str) -> Optional[Path]:
        """Разрешение пути к медиафайлу в рамках кластерного хранилища"""
        path = Path(relative_or_absolute)
        if path.is_absolute() and path.exists():
            return path
        
        shared_path = self.base_dir / relative_or_absolute
        if shared_path.exists():
            return shared_path
            
        local_fallback = settings.DATA_DIR / "media" / relative_or_absolute
        if local_fallback.exists():
            return local_fallback

        return None


_default_media_storage: Optional[MediaStorage] = None

def get_media_storage() -> MediaStorage:
    """Получение глобального инстанса медиа-хранилища"""
    global _default_media_storage
    if _default_media_storage is None:
        _default_media_storage = MediaStorage()
    return _default_media_storage
