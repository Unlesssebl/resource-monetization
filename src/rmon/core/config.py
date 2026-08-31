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

    # Gemini API Settings & Key Pool
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def GEMINI_API_KEYS(self) -> list:
        keys = []
        single = os.getenv("GEMINI_API_KEY")
        if single:
            keys.append(single.strip())
        
        comma_list = os.getenv("GEMINI_API_KEYS")
        if comma_list:
            keys.extend([k.strip() for k in comma_list.split(",") if k.strip()])
            
        for k, v in os.environ.items():
            if k.startswith("GEMINI_API_KEY_") and v.strip():
                if v.strip() not in keys:
                    keys.append(v.strip())
        return list(dict.fromkeys(keys)) # Deduplicate preserving order

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