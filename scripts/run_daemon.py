#!/usr/bin/env python3
"""
Скрипт запуска автономного 24/7 демона мониторинга с отправкой алертов в Telegram.
"""
import sys
import asyncio
import argparse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rmon.services.scraper.daemon import MonitorDaemon

def main():
    parser = argparse.ArgumentParser(description="24/7 Monitor Daemon Runner")
    parser.add_argument("--once", action="store_true", help="Выполнить один полный цикл и завершить работу")
    args = parser.parse_args()

    daemon = MonitorDaemon()
    
    if args.once:
        async def run_once():
            targets = daemon.load_targets()
            for t in targets:
                await daemon.process_target(t)
        asyncio.run(run_once())
    else:
        try:
            asyncio.run(daemon.run())
        except KeyboardInterrupt:
            daemon.stop()
            print("\nДемон остановлен пользователем.")

if __name__ == "__main__":
    main()
