import os
import subprocess
from pathlib import Path
from shared.config import settings
from shared.logger import get_logger

logger = get_logger("VodTranscoder")

class VodTranscoder:
    @staticmethod
    def compress_video(input_path: str, output_path: str = None) -> str:
        input_path = Path(input_path).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Видеофайл не найден: {input_path}")

        settings.VOD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = Path(output_path) if output_path else (settings.VOD_OUTPUT_DIR / f"compressed_{input_path.stem}.mp4")

        logger.info(f"Запуск аппаратного сжатия GPU AMF для: {input_path.name}")
        # Try FFmpeg with AMD AMF hardware acceleration (hevc_amf)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-c:v", "hevc_amf",
            "-quality", "speed",
            "-c:a", "aac",
            "-b:a", "128k",
            str(out_file)
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0:
                logger.warning("hevc_amf недоступен в текущей сессии, откат на CPU libx265/libx264...")
                cmd_fallback = [
                    "ffmpeg", "-y",
                    "-i", str(input_path),
                    "-c:v", "libx264", "-crf", "26", "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "128k",
                    str(out_file)
                ]
                subprocess.run(cmd_fallback, check=True)

            logger.info(f"Сжатие успешно завершено: {out_file}")
            return str(out_file)
        except Exception as e:
            logger.error(f"Ошибка транскодирования: {e}")
            raise