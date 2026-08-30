import os
import sys
import time
import shutil
import subprocess
import wave
from pathlib import Path
from datetime import timedelta
import av

from rmon.core.config import settings
from rmon.core.logger import get_logger

logger = get_logger("WhisperEngine")

class WhisperEngine:
    GPU_BIN = settings.ROOT_DIR / "tools" / "whisper_gpu" / "main.exe"
    MODELS_DIR = settings.DATA_DIR / "models"
    _detector_model = None

    @classmethod
    def get_detector(cls):
        if cls._detector_model is None:
            from faster_whisper import WhisperModel
            cls._detector_model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
        return cls._detector_model

    @classmethod
    def detect_language(cls, audio_wav: Path) -> str:
        try:
            detector = cls.get_detector()
            _, info = detector.transcribe(str(audio_wav), beam_size=1)
            lang = info.language or "ru"
            logger.info(f"🌐 Язык аудио определен: {lang.upper()} (уверенность: {info.language_probability:.2f})")
            return lang
        except Exception as e:
            logger.warning(f"Не удалось определить язык ({e}), по умолчанию: ru")
            return "ru"

    @classmethod
    def convert_to_wav16k(cls, input_path: Path, output_wav: Path):
        with av.open(str(input_path)) as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            with wave.open(str(output_wav), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                for frame in container.decode(audio=0):
                    resampled_frames = resampler.resample(frame)
                    for r_frame in resampled_frames:
                        wav.writeframes(r_frame.to_ndarray().tobytes())
            container.close()

    @classmethod
    def transcribe(
        cls,
        file_path: str,
        output_dir: str = None,
        model_size: str = "medium",
        language: str = None
    ) -> dict:
        start_time = time.time()
        file_path = Path(file_path).resolve()
        out_dir = Path(output_dir or (settings.DATA_DIR / "output_transcripts")).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        # Check audio duration
        with av.open(str(file_path)) as c:
            duration = float(c.duration) / av.time_base if c.duration else 0.0
            c.close()

        model_file = cls.MODELS_DIR / f"ggml-{model_size}.bin"
        base_name = file_path.stem
        srt_path = out_dir / f"{base_name}.srt"
        txt_path = out_dir / f"{base_name}.txt"
        md_path = out_dir / f"{base_name}.md"

        # 1. Try AMD Radeon DirectCompute GPU Engine
        if cls.GPU_BIN.exists() and model_file.exists():
            logger.info(f"🚀 Запуск GPU DirectCompute инференса: {file_path.name}")
            temp_wav = settings.DATA_DIR / f"temp_{base_name}_{int(time.time()*1000)}.wav"
            try:
                cls.convert_to_wav16k(file_path, temp_wav)
                
                # Resolve language
                target_lang = language or settings.WHISPER_LANGUAGE or "auto"
                if target_lang.lower() in ["auto", "none", ""]:
                    target_lang = cls.detect_language(temp_wav)
                
                cmd = [
                    str(cls.GPU_BIN),
                    "-m", str(model_file),
                    "-f", str(temp_wav),
                    "-gpu", "0",
                    "-osrt",
                    "-otxt",
                    "-l", str(target_lang)
                ]

                proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Move generated output files
                gen_srt = temp_wav.with_suffix(".srt")
                gen_txt = temp_wav.with_suffix(".txt")

                if gen_srt.exists():
                    shutil.move(str(gen_srt), str(srt_path))
                if gen_txt.exists():
                    shutil.move(str(gen_txt), str(txt_path))

                full_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
                detected_lang = target_lang

            except Exception as e:
                logger.warning(f"Ошибка GPU DirectCompute: {e}. Откат на CPU...")
                return cls._fallback_cpu_transcribe(file_path, out_dir, model_size, language)
            finally:
                for p in [temp_wav, temp_wav.with_suffix(".srt"), temp_wav.with_suffix(".txt")]:
                    if p.exists():
                        try:
                            p.unlink(missing_ok=True)
                        except Exception:
                            pass
        else:
            return cls._fallback_cpu_transcribe(file_path, out_dir, model_size, language)

        elapsed = time.time() - start_time
        speed_factor = duration / elapsed if elapsed > 0 else 0

        # Generate Markdown Summary
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# 📝 Транскрипт (GPU RX 6800 XT): {file_path.name}\n\n")
            f.write(f"- **Длительность аудио:** {timedelta(seconds=int(duration))}\n")
            f.write(f"- **Время обработки GPU:** {elapsed:.2f} сек ({speed_factor:.1f}x быстрее реального времени)\n")
            f.write(f"- **Аппаратное ускорение:** AMD Radeon RX 6800 XT (DirectCompute 12)\n")
            f.write(f"- **Язык:** {detected_lang.upper()}\n")
            f.write(f"- **Модель:** ggml-{model_size}.bin\n\n")
            f.write(f"---\n\n## 📄 Текст\n\n{full_text}\n")

        logger.info(f"✅ GPU обработка завершена за {elapsed:.2f} сек ({speed_factor:.1f}x speed)")

        return {
            "duration": duration,
            "elapsed": elapsed,
            "speed_factor": speed_factor,
            "language": detected_lang,
            "srt_path": str(srt_path),
            "txt_path": str(txt_path),
            "md_path": str(md_path),
            "full_text": full_text
        }

    @classmethod
    def _fallback_cpu_transcribe(cls, file_path: Path, out_dir: Path, model_size: str, language: str) -> dict:
        from faster_whisper import WhisperModel
        logger.info("Запуск резервного инференса на CPU...")
        start_time = time.time()
        cpu_threads = min(os.cpu_count() or 4, 16)
        model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=cpu_threads)
        segments, info = model.transcribe(str(file_path), beam_size=5, language=language)

        base_name = file_path.stem
        srt_path = out_dir / f"{base_name}.srt"
        txt_path = out_dir / f"{base_name}.txt"
        md_path = out_dir / f"{base_name}.md"

        srt_lines = []
        text_lines = []
        for idx, seg in enumerate(segments, 1):
            td_s = str(timedelta(seconds=int(seg.start)))
            td_e = str(timedelta(seconds=int(seg.end)))
            srt_lines.append(f"{idx}\n{td_s},000 --> {td_e},000\n{seg.text.strip()}\n")
            text_lines.append(seg.text.strip())

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        full_text = " ".join(text_lines)
        txt_path.write_text(full_text, encoding="utf-8")

        elapsed = time.time() - start_time
        duration = info.duration
        speed_factor = duration / elapsed if elapsed > 0 else 0

        return {
            "duration": duration,
            "elapsed": elapsed,
            "speed_factor": speed_factor,
            "language": info.language,
            "srt_path": str(srt_path),
            "txt_path": str(txt_path),
            "md_path": str(md_path),
            "full_text": full_text
        }