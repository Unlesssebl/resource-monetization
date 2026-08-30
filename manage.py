#!/usr/bin/env python3
"""
Resource Monetization Hub — Central Service Orchestrator
Modular microservices management CLI.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from shared.config import settings
from shared.logger import get_logger

logger = get_logger("ServiceOrchestrator")

def cmd_status():
    print("=" * 60)
    print("  🚀 RESOURCE MONETIZATION HUB — СТАТУС МИКРОСЕРВИСОВ")
    print("=" * 60)
    print(f"📁 Корень проекта:  {settings.ROOT_DIR}")
    print(f"💾 База DuckDB:     {'✅ Доступна' if settings.DUCKDB_PATH.exists() else '⚠️ Еще не создана'}")
    print(f"🤖 Telegram Bot:    {'✅ Токен задан' if (settings.BOT_TOKEN and settings.BOT_TOKEN != 'your_telegram_bot_token_here') else '⚠️ Ожидает токен в configs/.env'}")
    print(f"🎙️ Whisper Engine:  {settings.WHISPER_MODEL.upper()} на {settings.WHISPER_DEVICE.upper()} ({settings.WHISPER_COMPUTE})")
    print("-" * 60)
    
    # List services
    services = ["transcription", "telegram_bot", "market_monitor", "vod_vault"]
    for s in services:
        p = ROOT_DIR / "services" / s
        print(f"  • services.{s:<18} -> {'✅ Готов к запуску' if p.exists() else '❌ Отсутствует'}")
    print("=" * 60)

def cmd_run(service_name: str, extra_args: list):
    py_exec = sys.executable
    service_map = {
        "bot": "services.telegram_bot",
        "telegram": "services.telegram_bot",
        "transcribe": "services.transcription",
        "monitor": "services.market_monitor",
        "vod": "services.vod_vault",
        "dashboard": "scripts.meta.build_dashboard"
    }

    mod = service_map.get(service_name.lower())
    if not mod:
        print(f"❌ Неизвестный сервис: '{service_name}'. Доступные: {list(service_map.keys())}")
        return

    logger.info(f"Запуск микросервиса: python -m {mod} {' '.join(extra_args)}")
    cmd = [py_exec, "-m", mod] + extra_args
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Микросервис остановлен пользователем.")
    except Exception as e:
        logger.error(f"Ошибка выполнения: {e}")

def main():
    parser = argparse.ArgumentParser(description="Microservices Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Status command
    subparsers.add_parser("status", help="Проверить статус всех микросервисов")

    # Run command
    run_parser = subparsers.add_parser("run", help="Запустить микросервис")
    run_parser.add_argument("service", choices=["bot", "telegram", "transcribe", "monitor", "vod", "dashboard"], help="Имя сервиса")
    run_parser.add_argument("extra", nargs=argparse.REMAINDER, help="Дополнительные аргументы для сервиса")

    args, unknown = parser.parse_known_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "run":
        cmd_run(args.service, args.extra + unknown)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()