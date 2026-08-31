"""RPG & Game UI Item Icon Generator with Alpha Transparency & Sprite Sheet Packing."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from rmon.core.logger import get_logger

logger = get_logger("IconEngine")


class IconEngine:
    """Generates isolated RPG item sprites and combines them into sprite sheets."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/assets/icons")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_procedural_icon(self, item_name: str, item_type: str = "potion", color_rgb: Tuple[int, int, int] = (220, 40, 60), size: int = 512) -> Path:
        """Create high-res icon sprite with clean RGBA transparency."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        center = size // 2

        if item_type == "potion":
            # Bottle neck
            neck_w = size // 8
            draw.rectangle([center - neck_w // 2, size // 6, center + neck_w // 2, size // 3], fill=(200, 200, 220, 220))
            # Cork
            draw.rectangle([center - neck_w // 2 - 4, size // 8, center + neck_w // 2 + 4, size // 6], fill=(139, 69, 19, 255))
            # Bulb body
            r = size // 3
            draw.ellipse([center - r, size // 3, center + r, size // 3 + 2 * r], fill=(*color_rgb, 230), outline=(255, 255, 255, 180), width=6)
            # Liquid glow bubble
            glow_r = r // 2
            draw.ellipse([center - glow_r, size // 2, center + glow_r, size // 2 + glow_r * 2], fill=(255, 255, 255, 80))

        elif item_type == "sword":
            # Blade
            draw.polygon([(center, size // 8), (center + size // 16, size // 2), (center - size // 16, size // 2)], fill=(210, 220, 230, 255))
            # Guard
            draw.rectangle([center - size // 4, size // 2, center + size // 4, size // 2 + size // 16], fill=(218, 165, 32, 255))
            # Handle & Pommel
            draw.rectangle([center - size // 24, size // 2 + size // 16, center + size // 24, size * 3 // 4], fill=(100, 50, 20, 255))
            draw.ellipse([center - size // 16, size * 3 // 4, center + size // 16, size * 3 // 4 + size // 8], fill=(218, 165, 32, 255))

        elif item_type == "gem":
            # Faceted gem polygon
            pts = [
                (center, size // 6),
                (center + size // 3, size // 3),
                (center + size // 4, size * 3 // 4),
                (center, size * 5 // 6),
                (center - size // 4, size * 3 // 4),
                (center - size // 3, size // 3)
            ]
            draw.polygon(pts, fill=(*color_rgb, 240), outline=(255, 255, 255, 220), width=4)
            # Inner facets
            draw.line([(center, size // 6), (center, size * 5 // 6)], fill=(255, 255, 255, 120), width=3)
            draw.line([(center - size // 3, size // 3), (center + size // 3, size // 3)], fill=(255, 255, 255, 120), width=3)

        else: # scroll / book
            draw.rounded_rectangle([center - size // 3, size // 4, center + size // 3, size * 3 // 4], radius=20, fill=(*color_rgb, 255), outline=(218, 165, 32, 255), width=6)
            draw.line([center - size // 4, size // 2, center + size // 4, size // 2], fill=(255, 255, 255, 160), width=4)

        # Soft glow filter
        glow = img.filter(ImageFilter.GaussianBlur(radius=8))
        combined = Image.alpha_composite(glow, img)

        out_path = self.output_dir / f"{item_name}.png"
        combined.save(out_path, format="PNG")
        logger.info(f"Item icon saved: {out_path}")
        return out_path

    def build_sprite_sheet(self, icon_paths: List[Path], sheet_name: str = "rpg_items_atlas", cols: int = 4) -> Path:
        """Combine multiple icons into a unified 2D Sprite Sheet Grid."""
        if not icon_paths:
            raise ValueError("No icon paths provided to build sprite sheet.")

        sample = Image.open(icon_paths[0])
        tile_w, tile_h = sample.size
        rows = (len(icon_paths) + cols - 1) // cols

        sheet = Image.new("RGBA", (cols * tile_w, rows * tile_h), (0, 0, 0, 0))

        for idx, p in enumerate(icon_paths):
            r = idx // cols
            c = idx % cols
            icon = Image.open(p)
            sheet.paste(icon, (c * tile_w, r * tile_h), icon)

        sheet_path = self.output_dir / f"{sheet_name}.png"
        sheet.save(sheet_path, format="PNG")
        logger.info(f"Sprite sheet generated: {sheet_path} ({cols}x{rows} grid)")
        return sheet_path
