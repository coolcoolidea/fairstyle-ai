import json, hashlib, io
from datetime import datetime, timezone
from PIL import Image, PngImagePlugin

def make_manifest(style_id: str, artist_id: str, license_tier: str, txn_id: str, image_bytes: bytes) -> dict:
    h = hashlib.sha256(image_bytes).hexdigest()
    return {
        "spec": "fairstyle-manifest@0.1",
        "txnId": txn_id,
        "styleId": style_id,
        "artistId": artist_id,
        "licenseTier": license_tier,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": f"sha256:{h}",
    }

def embed_manifest_png(pil_img, manifest: dict) -> bytes:
    meta = PngImagePlugin.PngInfo()
    meta.add_text("fairstyle_manifest", json.dumps(manifest))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()
