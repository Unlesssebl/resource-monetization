#!/usr/bin/env python3
"""
Dashboard Generator (Lean & Single-File HTML)
Компилирует интерактивный визуальный дашборд docs/dashboard.html на основе configs/cases.json,
метрик AI-автономности и живых данных GitHub / поискового спроса.
"""

import sys
import os
import json
from datetime import datetime, timezone

# Гарантируем импорт модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from github_stats import fetch_github_stats

def build_dashboard(fetch_live_github: bool = True) -> str:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config_path = os.path.join(root_dir, "configs", "cases.json")
    output_html_path = os.path.join(root_dir, "docs", "dashboard.html")
    
    if not os.path.exists(config_path):
        print(f"Ошибка: не найден файл конфигурации {config_path}")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        
    # Дополняем живыми метриками GitHub
    if fetch_live_github:
        print("⚡ Обновление живых метрик GitHub...")
        for c in data.get("cases", []):
            repo = c.get("repo")
            if repo:
                gh = fetch_github_stats(repo)
                if gh.get("status") == "success":
                    c["live_github"] = {
                        "stars": gh.get("stars", 0),
                        "forks": gh.get("forks", 0),
                        "release": gh.get("latest_release", {}).get("tag") if gh.get("latest_release") else None,
                        "url": gh.get("url")
                    }

    cases_json = json.dumps(data["cases"], ensure_ascii=False)
    hw = data.get("hardware_profile", {})
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    html_template = f"""<!DOCTYPE html>
<html lang="ru" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Монетизация ресурсов — Аналитический Дашборд</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        brand: {{
                            50: '#eef2ff',
                            500: '#6366f1',
                            600: '#4f46e5',
                            900: '#312e81',
                        }},
                        darkBg: '#0b0f19',
                        cardBg: '#1e293b',
                        cardBorder: '#334155'
                    }}
                }}
            }}
        }}
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        body {{ font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #f1f5f9; }}
        .glass-card {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }}
        .glass-card:hover {{ border-color: rgba(99, 102, 241, 0.4); transform: translateY(-2px); transition: all 0.2s ease; }}
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">

    <!-- Header -->
    <header class="max-w-7xl mx-auto mb-8">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
            <div>
                <div class="flex items-center gap-3">
                    <span class="inline-flex items-center justify-center p-2 bg-indigo-500/20 text-indigo-400 rounded-xl">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </span>
                    <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
                        Resource Monetization Hub
                    </h1>
                </div>
                <p class="text-slate-400 text-sm mt-1">Визуальное сравнение стратегий, индекс AI-автономии и доказательная база</p>
            </div>
            
            <div class="flex flex-wrap items-center gap-2">
                <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Срез: Август 2026
                </span>
                <span class="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Топ AI-автономия: 95% (Парсинг 24/7)
                </span>
                <span class="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                    Обновлено: {now_str}
                </span>
            </div>
        </div>

        <!-- Hardware Specs Bar -->
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6">
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Облако</span>
                <span class="text-sm font-semibold text-indigo-400">{hw.get('cloud')}</span>
            </div>
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Сеть</span>
                <span class="text-sm font-semibold text-emerald-400">{hw.get('network')}</span>
            </div>
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Процессор</span>
                <span class="text-sm font-semibold text-slate-200">{hw.get('cpu')}</span>
            </div>
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Оперативная память</span>
                <span class="text-sm font-semibold text-amber-400">{hw.get('ram')}</span>
            </div>
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Видеокарта</span>
                <span class="text-sm font-semibold text-purple-400">{hw.get('gpu')}</span>
            </div>
            <div class="glass-card rounded-xl p-3">
                <span class="text-xs text-slate-400 block">Накопитель</span>
                <span class="text-sm font-semibold text-cyan-400">{hw.get('ssd')}</span>
            </div>
        </div>
    </header>

    <!-- Main Content Grid -->
    <main class="max-w-7xl mx-auto space-y-8">

        <!-- Visual Analytics Row -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Radar Chart: Multi-Factor Comparison -->
            <div class="lg:col-span-6 glass-card rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-200">Многофакторный радар-анализ</h2>
                        <p class="text-xs text-slate-400">Включая индекс AI-Автономии (1–10)</p>
                    </div>
                    <span class="text-xs text-slate-400">Шкала: 1 - 10</span>
                </div>
                <div class="relative h-[340px] flex items-center justify-center">
                    <canvas id="radarChart"></canvas>
                </div>
            </div>

            <!-- Bar Chart: Revenue Comparison -->
            <div class="lg:col-span-6 glass-card rounded-2xl p-6">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-bold text-slate-200">Прогноз дохода (Месяц 1 vs Месяц 3–6)</h2>
                        <p class="text-xs text-slate-400">Потенциал выручки в ₽/мес</p>
                    </div>
                    <span class="text-xs text-slate-400">В рублях</span>
                </div>
                <div class="relative h-[340px] flex items-center justify-center">
                    <canvas id="incomeBarChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Cases Visual Cards -->
        <div>
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-xl font-bold text-slate-100 flex items-center gap-2">
                    <span>Карточки направлений и оценка автономности</span>
                    <span class="text-xs font-normal px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">5 кейсов</span>
                </h2>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="cardsGrid">
                <!-- Javascript will render cards -->
            </div>
        </div>
    </main>

    <footer class="max-w-7xl mx-auto mt-12 pt-6 border-t border-slate-800 text-center text-xs text-slate-500">
        Resource Monetization Framework • AI Autonomy Metric • Lean & Open Source First
    </footer>

    <!-- Interactive Data & Scripts -->
    <script>
        const cases = {cases_json};

        // Render Cards
        const grid = document.getElementById('cardsGrid');
        cases.forEach((c, idx) => {{
            const liveStars = c.live_github ? `<span class="inline-flex items-center gap-1 text-amber-400 text-xs font-medium bg-amber-400/10 px-2 py-0.5 rounded-md border border-amber-400/20">⭐ ${{c.live_github.stars.toLocaleString()}}</span>` : '';
            const autonomyPct = (c.ai_autonomy * 10).toFixed(0);
            
            const card = document.createElement('div');
            card.className = "glass-card rounded-2xl p-6 flex flex-col justify-between";
            card.innerHTML = `
                <div>
                    <div class="flex items-start justify-between gap-2 mb-3">
                        <span class="text-xs font-semibold uppercase tracking-wider text-indigo-400">${{c.category}}</span>
                        <span class="text-xs font-medium px-2.5 py-0.5 rounded-full bg-${{c.badge_color}}-500/10 text-${{c.badge_color}}-400 border border-${{c.badge_color}}-500/20">${{c.badge}}</span>
                    </div>
                    <h3 class="text-lg font-bold text-white mb-2 leading-snug">${{c.title}}</h3>
                    <p class="text-slate-400 text-xs leading-relaxed mb-4">${{c.description}}</p>

                    <!-- AI Autonomy Metric Banner -->
                    <div class="mb-4 bg-indigo-950/40 border border-indigo-800/40 p-3 rounded-xl">
                        <div class="flex justify-between items-center text-xs mb-1.5">
                            <span class="text-indigo-300 font-medium flex items-center gap-1.5">
                                <svg class="w-3.5 h-3.5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                                AI-Автономия агента:
                            </span>
                            <span class="font-bold text-indigo-400 font-mono">${{c.ai_autonomy_label}}</span>
                        </div>
                        <div class="w-full bg-slate-800 rounded-full h-1.5">
                            <div class="bg-indigo-500 h-1.5 rounded-full" style="width: ${{autonomyPct}}%"></div>
                        </div>
                    </div>

                    <!-- Score Indicators -->
                    <div class="grid grid-cols-3 gap-2 mb-4 bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-center">
                        <div>
                            <span class="text-[10px] text-slate-400 block">Скорость</span>
                            <span class="text-xs font-bold text-emerald-400">${{c.scores.speed}}/10</span>
                        </div>
                        <div>
                            <span class="text-[10px] text-slate-400 block">Доход</span>
                            <span class="text-xs font-bold text-indigo-400">${{c.scores.income_potential}}/10</span>
                        </div>
                        <div>
                            <span class="text-[10px] text-slate-400 block">Безопасность</span>
                            <span class="text-xs font-bold text-cyan-400">${{c.scores.safety}}/10</span>
                        </div>
                    </div>

                    <!-- Revenue Forecast -->
                    <div class="mb-4">
                        <div class="flex items-center justify-between text-xs bg-slate-800/40 p-2.5 rounded-lg border border-slate-700/50">
                            <div>
                                <span class="text-slate-500 block text-[10px]">1-й месяц</span>
                                <span class="font-semibold text-slate-200">${{c.income_month_1[0].toLocaleString()}} – ${{c.income_month_1[1].toLocaleString()}} ₽</span>
                            </div>
                            <div class="text-right">
                                <span class="text-slate-500 block text-[10px]">3–6 месяцев</span>
                                <span class="font-semibold text-emerald-400">${{c.income_month_3_6[0].toLocaleString()}} – ${{c.income_month_3_6[1].toLocaleString()}} ₽</span>
                            </div>
                        </div>
                    </div>

                    <!-- Human Friction Point -->
                    <div class="mb-3 text-xs bg-amber-500/5 border border-amber-500/10 p-2 rounded-lg">
                        <span class="text-amber-400/90 font-medium block text-[11px] mb-0.5">Участие человека:</span>
                        <span class="text-slate-400 text-[11px] leading-tight block">${{c.human_friction}}</span>
                    </div>

                    <!-- Evidence & Proofs -->
                    <div class="mb-3 space-y-2 text-[11px]">
                        <div class="bg-indigo-950/30 border border-indigo-500/20 p-2.5 rounded-lg">
                            <span class="text-indigo-300 font-semibold block mb-1">📊 Доказательства и метрики (Август 2026):</span>
                            <span class="text-slate-300 block mb-1.5">${{c.evidence ? c.evidence.search_volume : c.metrics.search_volume}}</span>
                            <div class="flex flex-wrap gap-1.5 mt-1">
                                ${{c.evidence && c.evidence.proof_links ? c.evidence.proof_links.map(p => `<a href="${{p.url}}" target="_blank" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/40 transition-colors text-[10px] font-medium border border-indigo-500/30">🔗 ${{p.label}}</a>`).join('') : ''}}
                            </div>
                        </div>

                        ${{c.evidence && c.evidence.financial_math ? `
                        <div class="bg-emerald-950/20 border border-emerald-500/20 p-2 rounded-lg text-slate-300">
                            <strong class="text-emerald-400 block text-[10px] mb-0.5">💰 Расчет экономики:</strong>
                            <span class="text-[11px] leading-tight block text-slate-300">${{c.evidence.financial_math}}</span>
                        </div>` : ''}}

                        ${{c.evidence && c.evidence.competitive_edge ? `
                        <div class="bg-purple-950/20 border border-purple-500/20 p-2 rounded-lg text-slate-300">
                            <strong class="text-purple-400 block text-[10px] mb-0.5">⚔️ Отстройка от конкурентов:</strong>
                            <span class="text-[11px] leading-tight block text-slate-300">${{c.evidence.competitive_edge}}</span>
                        </div>` : ''}}
                    </div>
                </div>

                <div class="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
                    <div class="flex flex-wrap gap-1.5">
                        ${{c.stack.map(s => `<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] font-mono">${{s}}</span>`).join('')}}
                    </div>
                    <div class="flex items-center gap-2">
                        ${{liveStars}}
                    </div>
                </div>
            `;
            grid.appendChild(card);
        }});

        // Render Radar Chart (6 Axes including AI-Autonomy)
        const radarCtx = document.getElementById('radarChart').getContext('2d');
        new Chart(radarCtx, {{
            type: 'radar',
            data: {{
                labels: ['Скорость', 'Доходность', 'Простота', 'Безопасность', 'AI-Автономия', 'Железо'],
                datasets: cases.map((c, i) => {{
                    const colors = [
                        'rgba(99, 102, 241, 0.85)',
                        'rgba(14, 165, 233, 0.85)',
                        'rgba(168, 85, 247, 0.85)',
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(245, 158, 11, 0.85)'
                    ];
                    return {{
                        label: c.title.split(' ')[0] + '...',
                        data: [
                            c.scores.speed,
                            c.scores.income_potential,
                            c.scores.simplicity,
                            c.scores.safety,
                            c.scores.ai_autonomy,
                            c.scores.hardware_fit
                        ],
                        borderColor: colors[i],
                        backgroundColor: colors[i].replace('0.85', '0.12'),
                        borderWidth: 2,
                        pointBackgroundColor: colors[i]
                    }};
                }})
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    r: {{
                        min: 0,
                        max: 10,
                        ticks: {{ stepSize: 2, color: '#94a3b8', backdropColor: 'transparent' }},
                        grid: {{ color: 'rgba(255, 255, 255, 0.08)' }},
                        angleLines: {{ color: 'rgba(255, 255, 255, 0.08)' }},
                        pointLabels: {{ color: '#cbd5e1', font: {{ size: 10, weight: 500 }} }}
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#cbd5e1', font: {{ size: 10 }} }} }}
                }}
            }}
        }});

        // Render Income Bar Chart
        const barCtx = document.getElementById('incomeBarChart').getContext('2d');
        new Chart(barCtx, {{
            type: 'bar',
            data: {{
                labels: cases.map(c => c.title.substring(0, 15) + '...'),
                datasets: [
                    {{
                        label: 'Месяц 1 (Макс ₽)',
                        data: cases.map(c => c.income_month_1[1]),
                        backgroundColor: 'rgba(99, 102, 241, 0.85)',
                        borderRadius: 6
                    }},
                    {{
                        label: 'Месяц 3–6 (Макс ₽)',
                        data: cases.map(c => c.income_month_3_6[1]),
                        backgroundColor: 'rgba(16, 185, 129, 0.85)',
                        borderRadius: 6
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }},
                        grid: {{ display: false }}
                    }},
                    y: {{
                        ticks: {{ color: '#94a3b8', callback: val => val.toLocaleString() + ' ₽' }},
                        grid: {{ color: 'rgba(255, 255, 255, 0.08)' }}
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#cbd5e1', font: {{ size: 10 }} }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"✅ Дашборд с AI-автономией успешно сгенерирован: {output_html_path}")
    return output_html_path

def main():
    build_dashboard(fetch_live_github=True)

if __name__ == "__main__":
    main()
