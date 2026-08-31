"""Neural PBR & Game Asset Generator powered by DirectML (AMD Radeon RX 6800 XT / DirectCompute)."""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

from rmon.core.logger import get_logger
from rmon.services.assets.texture_engine import PBRTextureEngine

logger = get_logger("NeuralAssetEngine")


class NeuralAssetEngine:
    """Neural text-to-texture and game asset generator with DirectML GPU acceleration."""

    def __init__(self, output_dir: Optional[Path] = None, model_id: str = "stabilityai/sd-turbo"):
        self.output_dir = output_dir or Path("data/assets/neural_textures")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_id = model_id
        self.pbr_engine = PBRTextureEngine(output_dir=self.output_dir)
        self._pipe = None
        self._device = None

    def _init_device(self):
        """Initialize DirectML device for AMD Radeon RX 6800 XT (16 GB VRAM)."""
        if self._device is not None:
            return self._device

        try:
            import torch
            import torch_directml
            self._device = torch_directml.device()
            gpu_name = torch_directml.device_name(0)
            logger.info(f"DirectML GPU initialized: {gpu_name} (Device: {self._device})")
        except Exception as e:
            logger.warning(f"DirectML init fallback to CPU: {e}")
            import torch
            self._device = torch.device("cpu")

        return self._device

    def make_seamless(self, image: Image.Image, blend_fraction: float = 0.15) -> Image.Image:
        """Make an image seamless using circular offset edge blending."""
        w, h = image.size
        img_arr = np.array(image.convert("RGB"), dtype=np.float32)
        
        # Roll image by 50% horizontally and vertically
        rolled = np.roll(np.roll(img_arr, w // 2, axis=1), h // 2, axis=0)
        
        # Create a cross-blend mask
        blend_x = int(w * blend_fraction)
        blend_y = int(h * blend_fraction)
        
        mask = np.ones((h, w), dtype=np.float32)
        
        # Blend seams at center (which was the original border)
        for i in range(blend_x):
            weight = i / blend_x
            col = w // 2 - blend_x // 2 + i
            if 0 <= col < w:
                mask[:, col] = np.sin(weight * np.pi * 0.5) ** 2

        for j in range(blend_y):
            weight = j / blend_y
            row = h // 2 - blend_y // 2 + j
            if 0 <= row < h:
                mask[row, :] *= np.sin(weight * np.pi * 0.5) ** 2

        mask_3d = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
        blended = img_arr * (1.0 - mask_3d) + rolled * mask_3d
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        
        return Image.fromarray(blended)

    def load_pipeline(self):
        """Lazy load Diffusers pipeline with DirectML acceleration."""
        if self._pipe is not None:
            return self._pipe

        import torch
        from diffusers import AutoPipelineForText2Image

        device = self._init_device()
        logger.info(f"Loading neural model '{self.model_id}' onto {device}...")
        t0 = time.time()

        self._pipe = AutoPipelineForText2Image.from_pretrained(
            self.model_id,
            torch_dtype=torch.float32,
            variant="fp16" if "turbo" in self.model_id else None
        )
        self._pipe.to(device)
        logger.info(f"Neural model loaded successfully in {time.time() - t0:.2f}s")
        return self._pipe

    def generate_pbr_material(
        self,
        name: str,
        prompt: str,
        negative_prompt: str = "blur, low quality, artifacts, watermark, text, seams",
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        resolution: int = 512,
        seed: Optional[int] = None
    ) -> Dict[str, Path]:
        """Generate a complete AI PBR material with Diffuse, Normal, Roughness, Height, and AO."""
        import torch

        mat_dir = self.output_dir / name
        mat_dir.mkdir(parents=True, exist_ok=True)
        
        enhanced_prompt = f"seamless texture, top-down flat material, photorealistic {prompt}, 8k pbr material, high detail, physically based rendering"
        
        logger.info(f"Generating AI texture: '{name}' | Prompt: '{prompt}'")
        t0 = time.time()

        pipe = self.load_pipeline()
        generator = torch.Generator(device=self._device)
        if seed is not None:
            generator.manual_seed(seed)

        # Generate diffuse albedo
        result = pipe(
            prompt=enhanced_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=resolution,
            height=resolution,
            generator=generator
        )
        raw_image = result.images[0]
        
        # 1. Seamless Albedo
        albedo_img = self.make_seamless(raw_image)
        albedo_path = mat_dir / f"{name}_albedo.png"
        albedo_img.save(albedo_path)

        # 2. Extract Grayscale Height
        gray = ImageOps.grayscale(albedo_img)
        height_arr = np.array(gray)
        height_path = mat_dir / f"{name}_height.png"
        gray.save(height_path)

        # 3. Compute High-Fidelity Normal Map
        normal_arr = self.pbr_engine.compute_normal_map(height_arr, strength=3.5)
        normal_path = mat_dir / f"{name}_normal.png"
        Image.fromarray(normal_arr).save(normal_path)

        # 4. Compute Roughness Map
        roughness_arr = self.pbr_engine.compute_roughness_map(height_arr)
        roughness_path = mat_dir / f"{name}_roughness.png"
        Image.fromarray(roughness_arr).save(roughness_path)

        # 5. Compute Ambient Occlusion
        ao_arr = self.pbr_engine.compute_ambient_occlusion(height_arr, radius=6)
        ao_path = mat_dir / f"{name}_ao.png"
        Image.fromarray(ao_arr).save(ao_path)

        gen_time = time.time() - t0
        logger.info(f"Neural PBR Material '{name}' completed in {gen_time:.2f}s (5 maps saved to {mat_dir})")

        return {
            "albedo": albedo_path,
            "normal": normal_path,
            "roughness": roughness_path,
            "height": height_path,
            "ao": ao_path,
            "dir": mat_dir,
            "generation_time_sec": gen_time
        }
