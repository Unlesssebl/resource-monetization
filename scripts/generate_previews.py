"""Generate professional 1280x720 cover banner and screenshots for itch.io store listing."""

import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_gradient_bg(width: int, height: int, top_color=(18, 20, 26), bottom_color=(10, 11, 15)) -> Image.Image:
    """Create subtle modern dark theme gradient background."""
    base = Image.new("RGB", (width, height), top_color)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        factor = y / height
        r = int(top_color[0] * (1 - factor) + bottom_color[0] * factor)
        g = int(top_color[1] * (1 - factor) + bottom_color[1] * factor)
        b = int(top_color[2] * (1 - factor) + bottom_color[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base

def draw_rounded_rect(draw: ImageDraw.ImageDraw, coords, radius: int, fill, outline=None, width=1):
    """Draw a smooth rounded rectangle."""
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)

def generate_store_cover(textures_dir: Path, output_path: Path):
    """Generate 1280x720 professional store cover banner."""
    width, height = 1280, 720
    banner = create_gradient_bg(width, height, (24, 28, 36), (12, 14, 18))
    draw = ImageDraw.Draw(banner)
    
    # Grid lines / subtle cyber pattern
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 6), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 6), width=1)
    
    # Load fonts (fallback to default if system font not available)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 46)
        font_sub = ImageFont.truetype("arial.ttf", 22)
        font_badge = ImageFont.truetype("arialbd.ttf", 15)
        font_tag = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_tag = ImageFont.load_default()

    # Header Badges
    draw_rounded_rect(draw, (50, 45, 190, 75), radius=6, fill=(34, 197, 94), outline=None)
    draw.text((65, 52), "COMMERCIAL OK", fill=(10, 30, 15), font=font_badge)

    draw_rounded_rect(draw, (200, 45, 340, 75), radius=6, fill=(30, 41, 59), outline=(71, 85, 105))
    draw.text((215, 52), "SEAMLESS 4K", fill=(226, 232, 240), font=font_badge)

    draw_rounded_rect(draw, (350, 45, 500, 75), radius=6, fill=(30, 41, 59), outline=(71, 85, 105))
    draw.text((365, 52), "5 MATERIAL SETS", fill=(226, 232, 240), font=font_badge)

    # Main Title & Subtitle
    draw.text((50, 95), "SEAMLESS PBR ESSENTIALS", fill=(255, 255, 255), font=font_title)
    draw.text((50, 155), "Game-Ready Physically Based Textures for Unreal Engine 5, Unity & Godot", fill=(148, 163, 184), font=font_sub)

    # Material Swatches Grid (5 cards)
    materials = [
        ("medieval_cobblestone_vol1", "Cobblestone"),
        ("scifi_metal_panels_vol1", "Sci-Fi Panels"),
        ("wood_oak_planks_vol1", "Oak Planks"),
        ("alien_terrain_vol1", "Alien Terrain"),
        ("ancient_stone_vol2", "Ancient Stone"),
    ]

    card_width = 220
    card_height = 420
    start_x = 50
    gap = 20
    card_y = 220

    for i, (mat_name, label) in enumerate(materials):
        x = start_x + i * (card_width + gap)
        mat_path = textures_dir / mat_name
        
        # Outer Card Container
        draw_rounded_rect(draw, (x, card_y, x + card_width, card_y + card_height), radius=10, fill=(20, 24, 33), outline=(51, 65, 85), width=2)
        
        # 1. Albedo Preview (Top half)
        albedo_file = mat_path / f"{mat_name}_albedo.png"
        if albedo_file.exists():
            alb = Image.open(albedo_file).convert("RGB").resize((card_width - 16, 180), Image.Resampling.LANCZOS)
            banner.paste(alb, (x + 8, card_y + 8))
            draw.rectangle([x + 8, card_y + 8, x + card_width - 8, card_y + 188], outline=(71, 85, 105), width=1)
            # Label
            draw.rectangle([x + 12, card_y + 12, x + 70, card_y + 32], fill=(0, 0, 0, 180))
            draw.text((x + 16, card_y + 14), "ALBEDO", fill=(255, 255, 255), font=font_tag)

        # 2. Normal Map Preview (Bottom half)
        normal_file = mat_path / f"{mat_name}_normal.png"
        if normal_file.exists():
            norm = Image.open(normal_file).convert("RGB").resize((card_width - 16, 150), Image.Resampling.LANCZOS)
            banner.paste(norm, (x + 8, card_y + 196))
            draw.rectangle([x + 8, card_y + 196, x + card_width - 8, card_y + 346], outline=(71, 85, 105), width=1)
            # Label
            draw.rectangle([x + 12, card_y + 200, x + 70, card_y + 220], fill=(0, 0, 0, 180))
            draw.text((x + 16, card_y + 202), "NORMAL", fill=(200, 220, 255), font=font_tag)

        # Title at bottom of card
        draw.text((x + 12, card_y + 360), label, fill=(241, 245, 249), font=font_badge)
        draw.text((x + 12, card_y + 385), "5 Maps • 1024 / 4K", fill=(100, 116, 139), font=font_tag)

    # Footer Engine Tags
    draw.text((50, 675), "⚡ Compatible with:", fill=(148, 163, 184), font=font_tag)
    draw.text((180, 675), "Unreal Engine 5  •  Unity 6  •  Godot 4  •  Blender 4  •  RPG Maker", fill=(56, 189, 248), font=font_tag)

    banner.save(output_path, quality=95)
    print(f"Cover banner successfully created: {output_path} ({width}x{height})")


def generate_pbr_breakdown(textures_dir: Path, mat_name: str, output_path: Path):
    """Generate a screenshot showcasing all 5 maps of a single material."""
    width, height = 1280, 720
    shot = create_gradient_bg(width, height, (20, 24, 32), (10, 12, 16))
    draw = ImageDraw.Draw(shot)
    
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 36)
        font_label = ImageFont.truetype("arialbd.ttf", 18)
        font_sub = ImageFont.truetype("arial.ttf", 16)
    except:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((50, 40), f"PBR Map Breakdown: {mat_name.replace('_', ' ').title()}", fill=(255, 255, 255), font=font_title)
    draw.text((50, 85), "Full physically-based surface response maps included in lossless PNG format", fill=(148, 163, 184), font=font_sub)

    maps_info = [
        ("albedo", "1. Albedo (Diffuse Color)"),
        ("normal", "2. Normal (OpenGL Y+)"),
        ("roughness", "3. Roughness (Gloss/Micro)"),
        ("height", "4. Height (Displacement)"),
        ("ao", "5. Cavity / AO (Occlusion)"),
    ]

    slot_w, slot_h = 220, 480
    start_x = 50
    gap = 20
    start_y = 140

    mat_path = textures_dir / mat_name
    for i, (suffix, title) in enumerate(maps_info):
        x = start_x + i * (slot_w + gap)
        draw_rounded_rect(draw, (x, start_y, x + slot_w, start_y + slot_h), radius=8, fill=(24, 28, 38), outline=(51, 65, 85), width=2)
        
        file_path = mat_path / f"{mat_name}_{suffix}.png"
        if file_path.exists():
            img = Image.open(file_path).convert("RGB").resize((slot_w - 16, slot_w - 16), Image.Resampling.LANCZOS)
            shot.paste(img, (x + 8, start_y + 8))
            draw.rectangle([x + 8, start_y + 8, x + slot_w - 8, start_y + slot_w - 8], outline=(71, 85, 105), width=1)
        
        draw.text((x + 12, start_y + slot_w + 20), title, fill=(241, 245, 249), font=font_label)
        draw.text((x + 12, start_y + slot_w + 50), "• Lossless PNG\n• 1024x1024 Seamless\n• 4K Upscale Ready", fill=(148, 163, 184), font=font_sub)

    shot.save(output_path, quality=95)
    print(f"PBR Breakdown screenshot created: {output_path}")

if __name__ == "__main__":
    tex_dir = Path("data/assets/textures")
    out_dir = Path("data/releases/assets")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    generate_store_cover(tex_dir, out_dir / "cover_1280x720.png")
    generate_pbr_breakdown(tex_dir, "scifi_metal_panels_vol1", out_dir / "screenshot_01_pbr_maps.png")
    generate_pbr_breakdown(tex_dir, "medieval_cobblestone_vol1", out_dir / "screenshot_02_cobblestone_maps.png")
    print("ALL STORE PREVIEWS GENERATED SUCCESSFULLY!")
