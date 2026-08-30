#!/usr/bin/env python3
import sys
import asyncio
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from rmon.services.whisper.bot import start_bot

if __name__ == "__main__":
    asyncio.run(start_bot())