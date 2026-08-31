"""Batch Neural Synthesis of 24+ Stylized Fantasy RPG Icons with Sprite Atlas Packaging."""

import sys
import time
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rmon.services.assets.neural_icons import NeuralIconEngine
from rmon.services.assets.itch_packager import ItchPackager

ITEMS = [
    # 🧪 Potions & Flasks
    ("potion_crimson_health", "glass flask with glowing crimson red health potion liquid and golden stopper"),
    ("potion_sapphire_mana", "intricate crystal vial with swirling magical blue mana liquid and stardust"),
    ("potion_emerald_stamina", "round alchemy bottle with sparkling green nature stamina elixir"),
    ("potion_void_poison", "skulled flask with dripping glowing purple venomous poison"),
    ("potion_holy_elixir", "ornate celestial glass chalice with golden divine liquid and light rays"),
    ("potion_fire_fury", "spiked volcanic bottle with bubbling orange magma fury essence"),

    # ⚔️ Weapons & Combat
    ("weapon_flame_sword", "legendary medieval broadsword with blade engulfed in glowing fiery runes"),
    ("weapon_frost_dagger", "crystal ice dagger with glowing frozen frost particles and silver hilt"),
    ("weapon_obsidian_axe", "heavy double-headed battleaxe forged from dark obsidian stone with purple runes"),
    ("weapon_arcane_staff", "twisted wooden wizard staff topped with a hovering glowing arcane orb"),
    ("weapon_holy_warhammer", "massive paladin warhammer of pure silver radiating divine sun rays"),
    ("weapon_shadow_bow", "elven curved composite bow made of dark wood with glowing ethereal string"),

    # 💎 Gems, Crystals & Runes
    ("gem_blood_ruby", "flawless multifaceted blood red ruby gemstone reflecting bright light facets"),
    ("gem_deep_sapphire", "cut glowing blue royal sapphire gem radiating cold magic aura"),
    ("gem_celestial_emerald", "octagonal glowing bright green emerald crystal with nature sparkles"),
    ("gem_void_amethyst", "dark purple jagged crystal cluster hovering with dark energy particles"),
    ("rune_sun_stone", "circular ancient stone tablet engraved with glowing golden solar rune"),
    ("rune_storm_stone", "lightning-etched granite rune tablet with crackling blue electrical sparks"),

    # 📜 Magic Scrolls & Grimoires
    ("scroll_fireball", "ancient rolled parchment scroll sealed with wax emitting blazing orange fire sparks"),
    ("scroll_teleport", "mystic celestial scroll tied with blue ribbon glowing with cosmic portal glyphs"),
    ("book_arcane_grimoire", "leather-bound spellbook with glowing arcane eye symbol on the cover"),
    ("book_necronomicon", "dark sinister grimoire bound with iron chains and glowing green skull emblem"),

    # 🛡️ Relics, Armor & Loot
    ("relic_dragon_shield", "golden kite shield embossed with an ornate roaring dragon crest"),
    ("relic_phoenix_ring", "golden royal signet ring set with a burning orange phoenix feather gem"),
    ("relic_shadow_cloak", "folded dark velvet hood and mantle shimmering with ethereal starlight"),
    ("loot_gold_pouch", "heavy leather pouch overflowing with gleaming embossed gold coins and jewels"),
]

def main():
    print("=" * 80)
    print("🎮 ЗАПУСК НЕЙРОСЕТЕВОГО СИНТЕЗА RPG ICON PACK (24 ИКОНКИ + АТЛАС СПРАЙТОВ)")
    print("   GPU: AMD Radeon RX 6800 XT (DirectML) | Модель: DirectML Diffusion")
    print("=" * 80)

    out_dir = Path("data/assets/rpg_icons")
    engine = NeuralIconEngine(output_dir=out_dir)
    packager = ItchPackager()

    generated_paths = []
    t_start = time.time()

    for idx, (name, prompt) in enumerate(ITEMS, 1):
        print(f"\n[{idx:02d}/{len(ITEMS)}] Генерация спрайта: '{name}'...")
        p = engine.generate_rpg_icon(
            name=name,
            item_description=prompt,
            num_inference_steps=2,
            resolution=512,
            seed=200 + idx
        )
        generated_paths.append(p)

    total_time = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"✅ ВСЕ {len(ITEMS)} RPG-СПРАЙТОВ СИНТЕЗИРОВАНЫ ЗА {total_time:.2f} сек ({total_time/len(ITEMS):.2f}с на иконку)!")
    print("=" * 80)

    # 1. Build Atlas Grid & Showcase
    print("\n🗺️ Компиляция прозрачного атласа спрайтов и витрины...")
    atlas_path, showcase_path = engine.build_atlas_grid(
        generated_paths,
        sheet_name="fantasy_rpg_icons_atlas_24",
        cols=6,
        tile_size=256
    )
    print(f"  ✓ Атлас спрайтов: {atlas_path}")
    print(f"  ✓ Шоукейс-витрина: {showcase_path}")

    # 2. Package into itch.io ZIP
    print("\n📦 Упаковка коммерческого релиза в ZIP...")
    zip_path = packager.package_bundle(
        source_dir=out_dir,
        pack_slug="fantasy_rpg_icons_vol1",
        title="Fantasy RPG Inventory & Skill Icons Vol. 1 (24+ Handpainted Sprites & Atlas)",
        category="sprites",
        price_usd=4.99
    )
    print(f"✅ Готовый коммерческий релиз: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    main()
