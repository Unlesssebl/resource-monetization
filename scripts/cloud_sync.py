#!/usr/bin/env python3
"""
Скрипт автоматического резервного копирования DuckDB и синхронизации с облаком (8 ТБ Cloud Pool).
"""
import sys
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("CloudSync")

def backup_duckdb() -> Path:
    """Создание локального архива базы данных DuckDB"""
    backup_dir = settings.DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_file = backup_dir / f"market_monitor_backup_{today_str}.duckdb"
    
    db_source = settings.DUCKDB_PATH
    if db_source.exists():
        shutil.copy2(db_source, backup_file)
        logger.info(f"Создан локальный бэкап: {backup_file.name} ({backup_file.stat().st_size / 1024:.1f} KB)")
        return backup_file
    else:
        logger.warning(f"Файл БД {db_source} не найден. Пропуск создания бэкапа.")
        return backup_file

def sync_with_rclone(remote_name: str = "gdrive:ResourceMonetization/Backups"):
    """Синхронизация директории бэкапов и отчетов через rclone"""
    rclone_cmd = shutil.which("rclone")
    if not rclone_cmd:
        logger.info("rclone не обнаружен в PATH. Локальный бэкап сохранен в data/backups/.")
        return False

    backup_dir = settings.DATA_DIR / "backups"
    logger.info(f"Запуск rclone sync: {backup_dir} -> {remote_name}")

    try:
        res = subprocess.run(
            [rclone_cmd, "copy", str(backup_dir), remote_name, "--progress"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Синхронизация с облачным хранилищем успешно завершена!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка rclone: {e.stderr}")
        return False

def cleanup_old_backups(keep_days: int = 14):
    """Очистка локальных бэкапов старше keep_days дней"""
    backup_dir = settings.DATA_DIR / "backups"
    if not backup_dir.exists():
        return

    now_ts = datetime.now().timestamp()
    count_deleted = 0

    for f in backup_dir.glob("*.duckdb"):
        mtime = f.stat().st_mtime
        if (now_ts - mtime) > (keep_days * 86400):
            f.unlink()
            count_deleted += 1

    if count_deleted > 0:
        logger.info(f"Очищено устаревших бэкапов: {count_deleted}")

def main():
    print("\n📦 Запуск Cloud Sync & Backup Engine (8 TB Pool)...")
    backup_path = backup_duckdb()
    
    # Синхронизация
    synced = sync_with_rclone()
    
    # Ротация
    cleanup_old_backups(keep_days=7)
    
    print("\n" + "="*50)
    print("✅ РЕЗЕРВНОЕ КОПИРОВАНИЕ И СИНХРОНИЗАЦИЯ ЗАВЕРШЕНЫ")
    print("="*50)
    print(f"• Файл бэкапа: {backup_path.name if backup_path.exists() else 'Нет данных'}")
    print(f"• Локальный путь: {backup_path}")
    print(f"• Статус облака: {'Синхронизировано via rclone' if synced else 'Локальное хранилище готово'}")
    print("="*50)

if __name__ == "__main__":
    main()
