"""Neural RPG Item & Skill Icon Generator with DirectML & Automatic Alpha Transparency."""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps, ImageFilter

from rmon.core.logger import get_logger
from rmon.services.assets.neural_engine import NeuralAssetEngine

logger = get_logger("NeuralIconEngine")


class NeuralIconEngine:
    """Generates high-fidelity stylized 2D RPG Item & Skill icons with isolated transparent alpha."""

    def __init__(self, output_dir: Optional[Path] = None, model_id: str = "stabilityai/sd-turbo"):
        self.output_dir = output_dir or Path("data/assets/rpg_icons")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.neural = NeuralAssetEngine(output_dir=self.output_dir, model_id=model_id)

    def extract_transparent_sprite(self, img: Image.Image, bg_threshold: int = 25) -> Image.Image:
        """Extract foreground sprite onto transparent RGBA canvas by removing dark background."""
        img = img.convert("RGBA")
        arr = np.array(img)
        
        # Calculate background distance (assuming black/dark background)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        brightness = 0.299 * r + 0.587 * g + 0.114 * b
        
        # Soft alpha mask based on luminance and contrast
        alpha = np.clip((brightness - bg_threshold) * (255.0 / (80.0 - bg_threshold + 1e-5)), 0, 255).astype(np.uint8)
        
        # Create circular center vignette to ensure borders are clean transparent
        h, w = alpha.shape
        y, x = np.ogrid[:h, :w]
        center_y, center_x = h / 2, w / 2
        radius = min(h, w) * 0.46
        dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        vignette = np.clip((radius - dist_from_center + 15) / 15.0, 0, 1.0)
        
        final_alpha = (alpha * vignette).astype(np.uint8)
        arr[:, :, 3] = final_alpha
        
        sprite = Image.fromarray(arr, "RGBA")
        return sprite

    def generate_rpg_icon(
        self,
        name: str,
        item_description: str,
        category: str = "item",
        num_inference_steps: int = 2,
        resolution: int = 512,
        seed: Optional[int] = None
    ) -> Path:
        """Generate an isolated, stylized RPG icon sprite with transparent background."""
        import torch

        # Stylized RPG Game Asset prompt formula
        prompt = (
            f"masterpiece RPG game inventory icon, single isolated {item_description}, "
            f"vibrant saturated colors, magical glow, handpainted World of Warcraft / Hearthstone style, "
            f"clean dark background, centered, sharp vector edges, 8k UI asset"
        )
        negative_prompt = "blurry, low resolution, multiple items, complex background, text, watermark, human face, cropped"

        pipe = self.neural.load_pipeline()
        generator = torch.Generator(device=self.neural._device)
        if seed is not None:
            generator.manual_seed(seed)

        t0 = time.time()
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=0.0,
            width=resolution,
            height=resolution,
            generator=generator
        )
        raw_img = result.images[0]

        # Extract crisp transparency
        sprite = self.extract_transparent_sprite(raw_img)

        # Save individual icon
        out_path = self.output_dir / f"{name}.png"
        sprite.save(out_path, format="PNG")
        
        logger.info(f"RPG Icon '{name}' generated in {time.time() - t0:.2f}s -> {out_path}")
        return out_path

    def build_atlas_grid(
        self,
        icon_paths: List[Path],
        sheet_name: str = "rpg_icon_atlas_512",
        cols: int = 6,
        tile_size: int = 256,
        bg_color: Tuple[int, int, int, int] = (15, 17, 23, 255)
    ) -> Tuple[Path, Path]:
        """Build both a transparent sprite sheet and a themed presentation showcase image."""
        if not icon_paths:
            raise ValueError("No icons provided for sprite sheet.")

        rows = (len(icon_paths) + cols - 1) // cols
        sheet_w = cols * tile_size
        sheet_h = rows * tile_size

        # 1. Transparent Game-Ready Atlas
        atlas = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
        
        # 2. Presentation Showcase with slotted inventory frames
        showcase = Image.new("RGBA", (sheet_w + 80, sheet_h + 120), bg_color)
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(showcase)
        
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 32)
            font_sub = ImageFont.truetype("arial.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        draw.text((40, 30), "FANTASY RPG INVENTORY & SKILL ATLAS", fill=(255, 255, 255), font=font_title)
        draw.text((40, 70), f"50+ Modular Game Sprites • Lossless PNG • Unity & Unreal Engine Ready", fill=(148, 163, 184), font=font_sub)

        for idx, p in enumerate(icon_paths):
            r = idx // cols
            c = idx % cols
            x = c * tile_size
            y = r * tile_size

            icon = Image.open(p).convert("RGBA").resize((tile_size - 16, tile_size - 16), Image.Resampling.LANCZOS)
            atlas.paste(icon, (x + 8, y + 8), icon)

            # Slot box on showcase
            sx = 40 + x
            sy = 100 + y
            draw.rounded_rectangle([sx + 4, sy + 4, sx + tile_size - 4, sy + tile_size - 4], radius=8, fill=(24, 28, 38, 255), outline=(51, 65, 85, 255), width=2)
            showcase.paste(icon, (sx + 8, sy + 8), icon)

        atlas_path = self.output_dir / f"{sheet_name}.png"
        atlas.save(atlas_path, format="PNG")

        showcase_path = self.output_dir / f"{sheet_name}_showcase.png"
        showcase.save(showcase_path, format="PNG")

        logger.info(f"Atlas saved: {atlas_path} | Showcase: {showcase_path}")
        return atlas_path, showcase_path
