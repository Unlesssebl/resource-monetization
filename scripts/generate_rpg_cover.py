"""Generate 1280x720 Store Banner Cover for Fantasy RPG Icon Pack."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_rpg_cover():
    width, height = 1280, 720
    banner = Image.new("RGB", (width, height), (15, 17, 24))
    draw = ImageDraw.Draw(banner)

    # Gradient background
    for y in range(height):
        factor = y / height
        r = int(24 * (1 - factor) + 12 * factor)
        g = int(20 * (1 - factor) + 14 * factor)
        b = int(34 * (1 - factor) + 20 * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 44)
        font_sub = ImageFont.truetype("arial.ttf", 20)
        font_badge = ImageFont.truetype("arialbd.ttf", 15)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    # Badges
    draw.rounded_rectangle([50, 40, 190, 70], radius=6, fill=(34, 197, 94))
    draw.text((65, 47), "COMMERCIAL OK", fill=(10, 30, 15), font=font_badge)

    draw.rounded_rectangle([200, 40, 360, 70], radius=6, fill=(30, 41, 59), outline=(71, 85, 105))
    draw.text((215, 47), "26+ SPRITES & ATLAS", fill=(226, 232, 240), font=font_badge)

    draw.rounded_rectangle([370, 40, 520, 70], radius=6, fill=(30, 41, 59), outline=(71, 85, 105))
    draw.text((385, 47), "TRANSPARENT PNG", fill=(226, 232, 240), font=font_badge)

    # Title
    draw.text((50, 90), "FANTASY RPG ICONS & SPRITE ATLAS", fill=(255, 255, 255), font=font_title)
    draw.text((50, 145), "Handpainted Item Sprites (Potions, Weapons, Gems, Scrolls, Relics) for Unity & Unreal", fill=(148, 163, 184), font=font_sub)

    # Load Showcase Atlas Image
    showcase_path = Path("data/assets/rpg_icons/fantasy_rpg_icons_atlas_24_showcase.png")
    if showcase_path.exists():
        showcase = Image.open(showcase_path).convert("RGB")
        # Resize to fit lower half
        showcase_resized = showcase.resize((1180, 470), Image.Resampling.LANCZOS)
        banner.paste(showcase_resized, (50, 190))
        draw.rectangle([50, 190, 1230, 660], outline=(71, 85, 105), width=2)

    # Footer
    draw.text((50, 680), "⚡ Compatible with: Unity 6 • Unreal Engine 5 • Godot 4 • RPG Maker MZ • GameMaker", fill=(56, 189, 248), font=font_badge)

    out_path = Path("data/releases/assets/rpg_icons_cover_1280x720.png")
    banner.save(out_path, quality=95)
    print(f"RPG Icon Cover generated: {out_path}")

if __name__ == "__main__":
    make_rpg_cover()
