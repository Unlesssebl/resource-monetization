import os
from pathlib import Path
from dotenv import load_dotenv

# Root is 3 levels up from src/rmon/core
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load root .env
load_dotenv(ROOT_DIR / ".env")

class Settings:
    ROOT_DIR: Path = ROOT_DIR
    CONFIG_DIR: Path = CONFIG_DIR
    DATA_DIR: Path = DATA_DIR
    LOGS_DIR: Path = LOGS_DIR

    # Telegram Gateway
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: str = os.getenv("ADMIN_ID", "")

    # Whisper Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "medium")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "gpu")
    WHISPER_COMPUTE: str = os.getenv("WHISPER_COMPUTE", "directcompute")
    WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "ru")

    # Market Monitor
    DUCKDB_PATH: Path = DATA_DIR / "market_monitor.duckdb"
    REPORTS_DIR: Path = DATA_DIR / "market_reports"

    # VOD Vault
    VOD_OUTPUT_DIR: Path = DATA_DIR / "vod_recordings"

settings = Settings()