import sys
import argparse
from services.vod_vault.transcoder import VodTranscoder

def main():
    parser = argparse.ArgumentParser(description="VOD Vault Transcoder CLI")
    parser.add_argument("file", help="Путь к исходному видео")
    parser.add_argument("--out", default=None, help="Выходной файл")
    args = parser.parse_args()

    out = VodTranscoder.compress_video(args.file, args.out)
    print(f"✅ Сжатое видео сохранено: {out}")

if __name__ == "__main__":
    main()