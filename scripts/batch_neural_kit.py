"""Batch neural generation of complete Dark Fantasy Dungeon PBR Kit on RX 6800 XT."""

import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rmon.services.assets.neural_engine import NeuralAssetEngine
from rmon.services.assets.itch_packager import ItchPackager

def generate_dark_fantasy_kit():
    engine = NeuralAssetEngine(output_dir=Path("data/assets/neural_textures"))
    packager = ItchPackager()

    materials = [
        {
            "name": "dungeon_stone_wall_pbr",
            "prompt": "dark medieval dungeon stone wall, heavy rough masonry with green moss in crevices, photorealistic 8k texture"
        },
        {
            "name": "dungeon_ancient_floor_pbr",
            "prompt": "ancient medieval dungeon stone floor tiles, weathered flagstones with moss and dirt, photorealistic 8k texture"
        },
        {
            "name": "dungeon_rusted_iron_pbr",
            "prompt": "heavy rusted industrial dark iron plating, metal scratches, rivets, surface corrosion, photorealistic 8k texture"
        },
        {
            "name": "dungeon_weathered_wood_pbr",
            "prompt": "dark aged oak wood planks, ancient timber, deep wood grain with iron band details, photorealistic 8k texture"
        },
        {
            "name": "dungeon_volcanic_basalt_pbr",
            "prompt": "dark obsidian volcanic rock, sharp basalt stone with glowing orange magma in cracks, photorealistic 8k texture"
        }
    ]

    print("=" * 75)
    print("🚀 BATCH СИНТЕЗ НЕЙРОСЕТЕВОГО КИТА (Dark Fantasy Dungeon PBR)")
    print("   GPU: AMD Radeon RX 6800 XT (DirectML)")
    print("=" * 75)

    t_start = time.time()
    for i, mat in enumerate(materials, 1):
        print(f"\n[{i}/{len(materials)}] Генерация: {mat['name']}...")
        res = engine.generate_pbr_material(
            name=mat["name"],
            prompt=mat["prompt"],
            num_inference_steps=2,
            resolution=512,
            seed=100 + i
        )
        print(f"  ✓ Готово за {res['generation_time_sec']:.2f}с -> {res['dir']}")

    total_time = time.time() - t_start
    print("\n" + "=" * 75)
    print(f"✅ ВСЕ 5 НЕЙРОСЕТЕВЫХ МАТЕРИАЛОВ СИНТЕЗИРОВАНЫ ЗА {total_time:.2f} сек!")
    print("=" * 75)

    # Package as premium itch.io release
    print("\n📦 Упаковка релизного архива...")
    zip_path = packager.package_bundle(
        source_dir=Path("data/assets/neural_textures"),
        pack_slug="neural_dark_fantasy_dungeon_4k",
        title="Dark Fantasy Dungeon PBR Essentials — 5 AI-Synthesized Material Kits",
        category="textures",
        price_usd=4.99
    )
    print(f"✅ Релизный архив готов: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    generate_dark_fantasy_kit()
