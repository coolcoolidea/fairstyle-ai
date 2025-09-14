import os, io, uuid, textwrap
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

# Placeholder generation. If provider tokens are present, you could add real calls here.
def generate_placeholder(prompt: str, style_name: str, size: Tuple[int,int]=(768,512)) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, (245, 245, 245))
    draw = ImageDraw.Draw(img)
    title = f"DEMO ONLY\n{style_name}"
    body = textwrap.fill(prompt, width=36)
    try:
        # use default PIL font; no external font dependency
        draw.text((20, 20), title, fill=(0,0,0))
        draw.text((20, 120), body, fill=(30,30,30))
    except Exception:
        pass
    return img

def maybe_real_generation(prompt: str, style_name: str, size: Tuple[int,int]=(768,512)) -> Image.Image:
    # For PoC, always return placeholder. Users can extend to call Replicate/HF.
    return generate_placeholder(prompt, style_name, size)

def save_image(image: Image.Image, out_dir="data/outputs") -> str:
    os.makedirs(out_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    path = os.path.join(out_dir, f"{file_id}.png")
    image.save(path, format="PNG")
    return path
