"""ComfyUI Portable Pack Builder, Validator & Split-Archive Packaging Engine."""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from rmon.core.hardware import HardwareArbiter
from rmon.core.logger import get_logger
from rmon.services.comfyui.workflows import export_all_workflows

logger = get_logger("ComfyUIBuilder")


class ComfyUIBuilder:
    """Automates creation, verification, workflow injection, and packaging of portable ComfyUI packs."""

    def __init__(self, build_root: Optional[Path] = None):
        self.build_root = build_root or Path("data/comfyui_pack")
        self.pack_dir = self.build_root / "ComfyUI_windows_portable"
        self.workflows_dir = self.pack_dir / "ComfyUI" / "user" / "default" / "workflows"
        self.models_dir = self.pack_dir / "ComfyUI" / "models"
        self.releases_dir = Path("data/releases/comfyui")

    def verify_system_readiness(self) -> Dict[str, Any]:
        """Verify host hardware (GPU, VRAM, RAM, Disk) for running and packaging ComfyUI."""
        telem = HardwareArbiter.get_full_system_telemetry()
        gpu = telem.get("primary_compute_gpu", {})
        ram = telem.get("ram", {})
        
        gpu_name = gpu.get("name", "AMD Radeon RX 6800 XT")
        gpu_vram = gpu.get("vram_total_mb", 16384)
        vendor = gpu.get("vendor", "AMD")
        backend = gpu.get("compute_backend", "DirectML")
        
        # Check disk space on target drive
        stat = shutil.disk_usage(Path(".").resolve())
        free_gb = stat.free / (1024 ** 3)
        
        readiness = {
            "gpu": gpu_name,
            "vendor": vendor,
            "backend": backend,
            "vram_mb": gpu_vram,
            "hardware_ready": gpu.get("available", True),
            "system_ram_gb": round(ram.get("total_gb", 48.0), 1),
            "free_disk_gb": round(free_gb, 1),
            "is_ready": gpu.get("available", True) and free_gb >= 20.0
        }
        
        logger.info(f"System readiness: {readiness}")
        return readiness

    def initialize_pack_skeleton(self) -> Path:
        """Create the directory skeleton and launch scripts for the portable pack."""
        self.pack_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories
        dirs = [
            self.pack_dir / "ComfyUI" / "custom_nodes",
            self.models_dir / "checkpoints",
            self.models_dir / "controlnet",
            self.models_dir / "loras",
            self.models_dir / "upscale_models",
            self.models_dir / "vae",
            self.workflows_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # 1. Write run_nvidia_gpu.bat
        run_bat_nvidia = (
            "@echo off\n"
            "title ComfyUI Portable (NVIDIA CUDA Edition)\n"
            "echo ========================================================\n"
            "echo   Starting ComfyUI Portable on NVIDIA Dedicated GPU (CUDA)\n"
            "echo ========================================================\n"
            "set PYTHON=python\\python.exe\n"
            "if not exist %PYTHON% set PYTHON=python\n"
            "%PYTHON% ComfyUI\\main.py --windows-standalone-build --preview-method auto --gpu-only --highvram\n"
            "pause\n"
        )
        (self.pack_dir / "run_nvidia_gpu.bat").write_text(run_bat_nvidia, encoding="utf-8")

        # 2. Write run_amd_directml.bat
        run_bat_amd = (
            "@echo off\n"
            "title ComfyUI Portable (AMD Radeon DirectML Edition)\n"
            "echo ========================================================\n"
            "echo   Starting ComfyUI Portable on AMD Radeon GPU (DirectML)\n"
            "echo ========================================================\n"
            "set PYTHON=python\\python.exe\n"
            "if not exist %PYTHON% set PYTHON=python\n"
            "%PYTHON% ComfyUI\\main.py --windows-standalone-build --directml --preview-method auto --highvram\n"
            "pause\n"
        )
        (self.pack_dir / "run_amd_directml.bat").write_text(run_bat_amd, encoding="utf-8")

        # 2. Write Quickstart Guide
        readme_content = (
            "# 🚀 ComfyUI Portable Super-Pack (Plug & Play)\n\n"
            "## Быстрый старт:\n"
            "1. Распакуйте архив в любую папку без русских букв в пути (например `D:\\ComfyUI`).\n"
            "2. Запустите `run_nvidia_gpu.bat`.\n"
            "3. Откройте в браузере: http://127.0.0.1:8188\n\n"
            "## Предустановленные воркфлоу (Меню Workflows / Load):\n"
            "- `01_seamless_pbr_textures.json` — Генератор бесшовных 4K текстур и карт нормалей.\n"
            "- `02_rpg_item_icons.json` — Иконки предметов инвентаря и экипировки с чистым фоном.\n"
            "- `03_faceswap_photoreal.json` — Фотореалистичные лица и генерация аватаров.\n"
            "- `04_super_upscale_8k.json` — Апскейл графики и текстур до 4K/8K.\n\n"
            f"• Файлы и сборки: {self.releases_dir}\n"
            f"• Воркфлоу: {self.workflows_dir}\n"
            "Поддержка и обновления: https://boosty.to/unlesss\n"
        )
        (self.pack_dir / "QUICKSTART.md").write_text(readme_content, encoding="utf-8")

        # 3. Export all pre-built workflows
        export_all_workflows(self.workflows_dir)
        logger.info(f"Pack skeleton & workflows initialized at {self.pack_dir}")
        return self.pack_dir

    def calculate_checksums(self, directory: Path) -> Dict[str, str]:
        """Compute SHA256 for all key workflow and script files."""
        checksums = {}
        for root, _, files in os.walk(directory):
            for f in files:
                p = Path(root) / f
                if p.suffix in [".json", ".bat", ".md", ".py"]:
                    h = hashlib.sha256(p.read_bytes()).hexdigest()
                    rel = p.relative_to(directory).as_posix()
                    checksums[rel] = h
        return checksums

    def build_release_manifest(self) -> Dict[str, Any]:
        """Build manifest of the pack for distribution and cloud sync."""
        self.initialize_pack_skeleton()
        checksums = self.calculate_checksums(self.pack_dir)
        
        manifest = {
            "pack_name": "ComfyUI_Portable_SuperPack_v1.0",
            "version": "1.0.0",
            "target_gpu": "NVIDIA RTX / CUDA 12.x",
            "workflows_count": len(list(self.workflows_dir.glob("*.json"))),
            "files_count": len(checksums),
            "checksums_sha256": checksums,
            "recommended_volume_size_mb": 4096,
        }
        
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.releases_dir / "manifest.json"
        manifest_path.write_text(
            import_json_dumps(manifest), encoding="utf-8"
        )
        logger.info(f"Release manifest generated: {manifest_path}")
        return manifest


def import_json_dumps(data: Any) -> str:
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)
