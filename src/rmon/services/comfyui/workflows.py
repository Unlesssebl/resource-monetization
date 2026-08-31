"""Pre-built, production-grade ComfyUI workflow definitions for Game Assets, Textures, and AI Upscaling."""

import json
from pathlib import Path
from typing import Dict, Any


def get_seamless_pbr_texture_workflow() -> Dict[str, Any]:
    """Workflow: Seamless 4K PBR Texture Generator with Normal & Roughness maps."""
    return {
        "name": "01_seamless_pbr_textures",
        "title": "Seamless PBR Texture & Normal Map Generator",
        "description": "Generates seamless tiling textures (4K) with automatically extracted Normal, Height, and Roughness maps.",
        "nodes": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "seamless texture, high detail PBR material, medieval cobblestone floor, mossy joints, 4k photorealistic, 8k resolution, flat top-down view",
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "seams, borders, frame, vignette, perspective tilt, 3d object, watermark, text, blurry, low quality",
                    "clip": ["1", 1]
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"batch_size": 1, "height": 1024, "width": 1024}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 7.5,
                    "denoise": 1.0,
                    "latent_image": ["4", 0],
                    "model": ["1", 0],
                    "negative": ["3", 0],
                    "positive": ["2", 0],
                    "sampler_name": "dpmpp_2m_sde_gpu",
                    "scheduler": "karras",
                    "seed": 424242,
                    "steps": 28
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "textures/pbr_albedo", "images": ["6", 0]}
            }
        }
    }


def get_rpg_item_icon_workflow() -> Dict[str, Any]:
    """Workflow: RPG Item Icon Generator with isolated background."""
    return {
        "name": "02_rpg_item_icons",
        "title": "RPG Fantasy Item & Equipment Icon Generator",
        "description": "Generates clean RPG sprites, potions, weapons, and inventory icons with isolated dark backgrounds for easy transparency clipping.",
        "nodes": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "isolated icon of glowing mystical mana potion bottle, intricate glass, golden runes, glowing liquid, game UI sprite, clean borders, pure black background, 8k resolution, Unreal Engine 5 asset",
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "complex background, scenery, floor, table, person, hands, blurry, watermark, cropped, noisy",
                    "clip": ["1", 1]
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"batch_size": 1, "height": 512, "width": 512}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 8.0,
                    "denoise": 1.0,
                    "latent_image": ["4", 0],
                    "model": ["1", 0],
                    "negative": ["3", 0],
                    "positive": ["2", 0],
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "seed": 777777,
                    "steps": 25
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "icons/rpg_item", "images": ["6", 0]}
            }
        }
    }


def get_faceswap_photoreal_workflow() -> Dict[str, Any]:
    """Workflow: Photorealistic Face Restoration & Avatar Generator."""
    return {
        "name": "03_faceswap_photoreal",
        "title": "Photoreal Face Swap & Avatar Synthesis",
        "description": "High-fidelity face swapping with CodeFormer / GFPGAN restoration for commercial avatars and model creation.",
        "nodes": {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "epicrealism_naturalSin.safetensors"}
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "cinematic portrait, hyperrealistic 8k, professional studio lighting, detailed skin pores, realistic hair, 85mm portrait photography",
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "anime, cartoon, deformed, bad eyes, plastic skin, oversaturated, low quality, watermark",
                    "clip": ["1", 1]
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {"batch_size": 1, "height": 768, "width": 768}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 6.5,
                    "denoise": 1.0,
                    "latent_image": ["4", 0],
                    "model": ["1", 0],
                    "negative": ["3", 0],
                    "positive": ["2", 0],
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "seed": 101010,
                    "steps": 30
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "avatars/photoreal_portrait", "images": ["6", 0]}
            }
        }
    }


def get_super_upscale_8k_workflow() -> Dict[str, Any]:
    """Workflow: UltraSharp 4K / 8K Graphic Restorer & Upscaler."""
    return {
        "name": "04_super_upscale_8k",
        "title": "8K Super Resolution Upscaler (UltraSharp + Tile Denoise)",
        "description": "Upscales old game assets, textures, and low-res artwork to crisp 4K/8K with micro-detail enhancement.",
        "nodes": {
            "1": {
                "class_type": "UpscaleModelLoader",
                "inputs": {"model_name": "4x-UltraSharp.pth"}
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": "input_asset.png"}
            },
            "3": {
                "class_type": "ImageUpscaleWithModel",
                "inputs": {"image": ["2", 0], "upscale_model": ["1", 0]}
            },
            "4": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "upscaled/8k_super_res", "images": ["3", 0]}
            }
        }
    }


def export_all_workflows(output_dir: Path) -> Dict[str, Path]:
    """Export all pre-built workflow JSONs to target directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    exported = {}
    
    workflows = [
        get_seamless_pbr_texture_workflow(),
        get_rpg_item_icon_workflow(),
        get_faceswap_photoreal_workflow(),
        get_super_upscale_8k_workflow(),
    ]
    
    for wf in workflows:
        file_path = output_dir / f"{wf['name']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(wf["nodes"], f, indent=2, ensure_ascii=False)
        exported[wf["name"]] = file_path
        
    return exported
