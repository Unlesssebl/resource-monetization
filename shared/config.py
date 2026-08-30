import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env
load_dotenv(CONFIG_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

class Settings:
    ROOT_DIR: Path = ROOT_DIR
    CONFIG_DIR: Path = CONFIG_DIR
    DATA_DIR: Path = DATA_DIR
    LOGS_DIR: Path = LOGS_DIR

    # Telegram Gateway Settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: str = os.getenv("ADMIN_ID", "")

    # Whisper AI Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "medium")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE: str = os.getenv("WHISPER_COMPUTE", "int8")

    # Market Monitor Settings
    DUCKDB_PATH: Path = DATA_DIR / "market_monitor.duckdb"
    REPORTS_DIR: Path = DATA_DIR / "market_reports"

    # VOD Vault Settings
    VOD_OUTPUT_DIR: Path = DATA_DIR / "vod_recordings"

settings = Settings()