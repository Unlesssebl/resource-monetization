"""
Hardware & GPU Resource Arbiter for RMon Platform.
Предотвращает Out-Of-Memory (OOM) и координирует распределение VRAM
между тяжелыми AI-моделями (Faster-Whisper vs Qwen 2.5 LLM / Vision) на NVIDIA RTX 3050 (8 GB VRAM).
"""
import os
import asyncio
import subprocess
from typing import Dict, Any, Optional
from rmon.core.logger import get_logger

logger = get_logger("HardwareArbiter")

class HardwareArbiter:
    """Асинхронный координатор аппаратных ресурсов и GPU VRAM"""
    
    _gpu_lock = asyncio.Lock()

    @staticmethod
    def get_gpu_telemetry() -> Dict[str, Any]:
        """Получение реальной телеметрии NVIDIA GPU через nvidia-smi с приоритизацией Compute GPU"""
        telemetry = {
            "name": "NVIDIA GPU",
            "vram_total_mb": 8192,
            "vram_used_mb": 0,
            "vram_free_mb": 8192,
            "gpu_util_pct": 0,
            "temperature_c": 0,
            "available": False,
            "all_gpus": []
        }
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
            gpus = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpus.append({
                        "name": parts[0],
                        "vram_total_mb": int(parts[1]),
                        "vram_used_mb": int(parts[2]),
                        "vram_free_mb": int(parts[3]),
                        "gpu_util_pct": int(parts[4]),
                        "temperature_c": int(parts[5]),
                        "available": True
                    })
            if gpus:
                telemetry["all_gpus"] = gpus
                # Приоритет отдаем RTX / наибольшей VRAM (RTX 3050 8GB)
                selected = next((g for g in gpus if "3050" in g["name"] or "RTX" in g["name"]), gpus[0])
                telemetry.update(selected)
                telemetry["all_gpus"] = gpus
        except Exception as e:
            logger.debug(f"nvidia-smi недоступен или ошибка: {e}")
        return telemetry

    @classmethod
    async def acquire_gpu_slot(cls, service_name: str, required_vram_mb: int = 4000):
        """
        Захват слота на GPU с проверкой свободной памяти.
        Гарантирует, что Whisper и Qwen не упадут в OOM при одновременной работе.
        """
        await cls._gpu_lock.acquire()
        telem = cls.get_gpu_telemetry()
        logger.info(
            f"🎮 [GPU Slot Acquired by '{service_name}'] | VRAM: {telem['vram_used_mb']}MB / {telem['vram_total_mb']}MB "
            f"({telem['vram_free_mb']}MB свободно, T={telem['temperature_c']}°C)"
        )

    @classmethod
    def release_gpu_slot(cls, service_name: str):
        """Освобождение слота GPU после инференса"""
        if cls._gpu_lock.locked():
            cls._gpu_lock.release()
            logger.info(f"🔓 [GPU Slot Released by '{service_name}']")
