#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from scripts.meta.build_dashboard import build_dashboard

if __name__ == "__main__":
    build_dashboard(fetch_live_github=True)