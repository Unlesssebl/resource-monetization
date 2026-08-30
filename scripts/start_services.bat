@echo off
chcp 65001 >nul
title Resource Monetization Hub - 24/7 Automation

echo ========================================================
echo   🚀 RESOURCE MONETIZATION HUB (CLEAN SRC ARCHITECTURE)
echo   Hardware: Intel i5-12600KF ^| 48GB RAM ^| RX 6800 XT 16GB
echo ========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Виртуальное окружение не найдено. Создание через uv...
    uv venv .venv --python 3.12
    uv pip install -r requirements.txt
)

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [*] Создан файл конфигурации .env. Пожалуйста, укажите BOT_TOKEN.
    )
)

echo [1] Запустить Telegram AI-транскрибатор (24/7)
echo [2] Запустить транскрибацию тестового аудио
echo [3] Запустить мониторинг цен маркетплейсов (DuckDB)
echo [4] Пересобрать интерактивный HTML-дашборд
echo [5] Выход
echo.

set /p choice="Выберите действие (1-5): "

if "%choice%"=="1" (
    .venv\Scripts\python.exe scripts\run_bot.py
)
if "%choice%"=="2" (
    .venv\Scripts\python.exe scripts\run_transcribe.py data\test_sample.wav --model medium
    pause
)
if "%choice%"=="3" (
    .venv\Scripts\python.exe scripts\run_monitor.py --query "авточехлы" --limit 15
    pause
)
if "%choice%"=="4" (
    .venv\Scripts\python.exe scripts\run_dashboard.py
    pause
)