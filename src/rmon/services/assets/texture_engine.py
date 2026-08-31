"""PBR Texture Baking & Processing Engine (Normal, Roughness, Height, AO Synthesis)."""

import math
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from rmon.core.logger import get_logger

logger = get_logger("PBRTextureEngine")


class PBRTextureEngine:
    """Bakes full PBR material sets (Albedo, Normal, Roughness, Height, AO) from diffuse images."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/assets/textures")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compute_normal_map(self, height_arr: np.ndarray, strength: float = 2.5) -> np.ndarray:
        """Compute tangent-space OpenGL/DirectX Normal map using Sobel gradient filters."""
        # Sobel convolution
        zy, zx = np.gradient(height_arr.astype(float))
        
        # Scale gradients by strength
        zx = zx * strength
        zy = zy * strength
        
        # Tangent vector: (-dx, -dy, 1.0)
        norm = np.sqrt(zx**2 + zy**2 + 1.0)
        
        # Normal components [-1, 1] mapped to [0, 255]
        r = (( -zx / norm ) * 0.5 + 0.5) * 255.0
        g = (( -zy / norm ) * 0.5 + 0.5) * 255.0  # OpenGL format (DirectX inverts Y)
        b = (( 1.0 / norm ) * 0.5 + 0.5) * 255.0
        
        normal_rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        return normal_rgb

    def compute_roughness_map(self, gray_arr: np.ndarray, invert: bool = False) -> np.ndarray:
        """Compute micro-surface roughness map from surface luminance variance."""
        roughness = gray_arr.astype(float)
        # Normalize and enhance contrast
        p2, p98 = np.percentile(roughness, (2, 98))
        roughness = np.clip((roughness - p2) / (p98 - p2 + 1e-5), 0, 1) * 255.0
        if invert:
            roughness = 255.0 - roughness
        return roughness.astype(np.uint8)

    def compute_ambient_occlusion(self, height_arr: np.ndarray, radius: int = 5) -> np.ndarray:
        """Compute Cavity / Ambient Occlusion map from local height depressions."""
        img = Image.fromarray(height_arr.astype(np.uint8))
        blurred = img.filter(ImageFilter.GaussianBlur(radius))
        blurred_arr = np.array(blurred, dtype=float)
        
        # Cavity = height - blurred_height
        diff = height_arr.astype(float) - blurred_arr
        ao = np.clip(128.0 + diff * 3.0, 0, 255)
        return ao.astype(np.uint8)

    def generate_procedural_material(self, name: str, style: str = "cobblestone", resolution: int = 1024) -> Dict[str, Path]:
        """Generate a procedural master texture set for instant catalog generation."""
        mat_dir = self.output_dir / name
        mat_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate base procedural noise / cellular pattern
        x = np.linspace(0, 8 * np.pi, resolution)
        y = np.linspace(0, 8 * np.pi, resolution)
        xv, yv = np.meshgrid(x, y)
        
        if style == "cobblestone":
            pattern = np.sin(xv) * np.cos(yv) + 0.5 * np.sin(2 * xv + yv)
            base_color = np.array([120, 115, 110]) # stone grey
        elif style == "scifi_metal":
            pattern = np.sign(np.sin(xv)) * np.sign(np.cos(yv)) * 0.5 + 0.5 * np.cos(4 * xv)
            base_color = np.array([40, 50, 65]) # dark metal blue
        elif style == "wood_planks":
            pattern = np.sin(xv * 0.2) + 0.3 * np.sin(yv * 4.0) + 0.1 * np.random.randn(resolution, resolution)
            base_color = np.array([140, 90, 50]) # warm wood
        else: # alien_rock
            pattern = np.sin(xv * yv * 0.05) + np.cos(xv + yv)
            base_color = np.array([80, 40, 110]) # purple alien rock

        # Normalize pattern to [0, 1]
        pattern_norm = (pattern - pattern.min()) / (pattern.max() - pattern.min())
        
        # 1. Albedo (Diffuse)
        albedo_arr = np.zeros((resolution, resolution, 3), dtype=np.uint8)
        for c in range(3):
            albedo_arr[:, :, c] = np.clip(base_color[c] * (0.6 + 0.8 * pattern_norm), 0, 255).astype(np.uint8)
        albedo_img = Image.fromarray(albedo_arr)
        albedo_path = mat_dir / f"{name}_albedo.png"
        albedo_img.save(albedo_path)

        # 2. Height Map (Grayscale)
        height_arr = (pattern_norm * 255).astype(np.uint8)
        height_path = mat_dir / f"{name}_height.png"
        Image.fromarray(height_arr).save(height_path)

        # 3. Normal Map
        normal_arr = self.compute_normal_map(height_arr, strength=3.0)
        normal_path = mat_dir / f"{name}_normal.png"
        Image.fromarray(normal_arr).save(normal_path)

        # 4. Roughness Map
        roughness_arr = self.compute_roughness_map(height_arr)
        roughness_path = mat_dir / f"{name}_roughness.png"
        Image.fromarray(roughness_arr).save(roughness_path)

        # 5. Ambient Occlusion (AO)
        ao_arr = self.compute_ambient_occlusion(height_arr)
        ao_path = mat_dir / f"{name}_ao.png"
        Image.fromarray(ao_arr).save(ao_path)

        logger.info(f"PBR Material set generated: {name} at {mat_dir}")
        return {
            "albedo": albedo_path,
            "normal": normal_path,
            "roughness": roughness_path,
            "height": height_path,
            "ao": ao_path,
            "dir": mat_dir
        }
