"""itch.io, Unity Store & GameBanana Asset Packager with License & Metadata Generation."""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from rmon.core.logger import get_logger

logger = get_logger("ItchPackager")


class ItchPackager:
    """Packages game asset folders into distribution ZIP archives with itch.io store metadata."""

    def __init__(self, releases_dir: Optional[Path] = None):
        self.releases_dir = releases_dir or Path("data/releases/assets")
        self.releases_dir.mkdir(parents=True, exist_ok=True)

    def create_license_file(self, target_dir: Path, pack_name: str) -> Path:
        """Generate a commercial indie developer friendly license."""
        license_text = (
            f"=== Commercial Indie Game License: {pack_name} ===\n\n"
            "1. You are free to use these assets in commercial and non-commercial games.\n"
            "2. You may modify, resize, recolor, and adapt the assets.\n"
            "3. You may NOT resell or redistribute these raw asset files as a standalone asset pack.\n"
            "4. Attribution is appreciated but not mandatory (e.g. 'Assets by RMon AI Studio').\n\n"
            "Created with Open Source First AI pipeline on dedicated NVIDIA hardware.\n"
        )
        license_path = target_dir / "LICENSE.txt"
        license_path.write_text(license_text, encoding="utf-8")
        return license_path

    def package_bundle(self, source_dir: Path, pack_slug: str, title: str, category: str = "textures", price_usd: float = 4.99) -> Path:
        """Create a complete ZIP release bundle with store metadata."""
        bundle_temp = self.releases_dir / f"temp_{pack_slug}"
        bundle_temp.mkdir(parents=True, exist_ok=True)

        # Copy source asset files
        if source_dir.is_dir():
            for item in source_dir.glob("**/*"):
                if item.is_file() and item.suffix in [".png", ".jpg", ".tga", ".json", ".md"]:
                    rel = item.relative_to(source_dir)
                    dest = bundle_temp / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

        # Add License & Store Metadata
        self.create_license_file(bundle_temp, title)
        
        metadata = {
            "title": title,
            "slug": pack_slug,
            "category": category,
            "price_usd": price_usd,
            "file_format": "PNG (Lossless) + PBR Normal/Roughness maps",
            "resolution": "Up to 4096x4096",
            "compatible_engines": ["Unreal Engine 5", "Unity", "Godot", "RPG Maker", "Roblox"],
            "support_url": "https://t.me/your_bot"
        }
        (bundle_temp / "store_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        # Zip bundle
        zip_path = self.releases_dir / f"{pack_slug}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in bundle_temp.rglob("*"):
                if item.is_file():
                    zf.write(item, item.relative_to(bundle_temp))

        # Cleanup temp
        shutil.rmtree(bundle_temp, ignore_errors=True)
        logger.info(f"Asset pack successfully built for itch.io: {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
        return zip_path
