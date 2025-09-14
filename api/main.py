import io, os, json, hashlib, uuid, pathlib
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from dotenv import load_dotenv

from api.models import engine, create_db_and_tables, Artist, StyleCard, InferenceLog, UsageEvent
from api.services.inference import maybe_real_generation
from api.services.c2pa import make_manifest, embed_manifest_png
from api.services.billing import price_breakdown

load_dotenv()

app = FastAPI(title="FairStyle-AI PoC", version="0.1.0")
app.mount("/outputs", StaticFiles(directory="data/outputs"), name="outputs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLOCKLIST = set()
try:
    with open("infra/blocklist.txt", "r", encoding="utf-8") as f:
        BLOCKLIST = set([x.strip().lower() for x in f.readlines() if x.strip()])
except FileNotFoundError:
    BLOCKLIST = set()

class GenerateReq(BaseModel):
    prompt: str
    style_id: str
    user_hint: Optional[str] = None

class GenerateResp(BaseModel):
    output_url: str
    receipt: dict
    usage: dict

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/styles")
def list_styles():
    from sqlmodel import Session, select
    with Session(engine) as session:
        styles = session.exec(select(StyleCard).where(StyleCard.status == "active")).all()
        out = []
        for s in styles:
            artist = session.exec(select(Artist).where(Artist.id == s.artist_id)).first()
            out.append({
                "id": s.id,
                "artist_id": s.artist_id,
                "name": s.name,
                "desc": s.desc,
                "license_tier": s.license_tier,
                "artist_display_name": (artist.display_name if artist else "Unknown"),
            })
        return out


@app.post("/generate", response_model=GenerateResp)
def generate(req: GenerateReq):
    # blocklist check
    tokens = set(req.prompt.lower().split())
    if any(b in req.prompt.lower() for b in BLOCKLIST):
        raise HTTPException(status_code=400, detail="Prompt contains blocked or unlicensed names. Please revise.")

    with Session(engine) as session:
        style: StyleCard = session.exec(select(StyleCard).where(StyleCard.id == req.style_id)).first()
        if not style:
            raise HTTPException(status_code=404, detail="Style not found")
        artist: Artist = session.exec(select(Artist).where(Artist.id == style.artist_id)).first()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        # generate image (placeholder for PoC)
        img = maybe_real_generation(req.prompt, style.name)
        # temporary save to get hash
        tmp_bytes = io.BytesIO()
        img.save(tmp_bytes, format="PNG")
        txn_id = str(uuid.uuid4())
        manifest = make_manifest(style.id, style.artist_id, style.license_tier, txn_id, tmp_bytes.getvalue())
        # embed manifest & save final
        png_bytes = embed_manifest_png(img, manifest)
        out_dir = "data/outputs"
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{txn_id}.png")
        with open(file_path, "wb") as f:
            f.write(png_bytes)

        # log inference
        prompt_hash = hashlib.sha256(req.prompt.encode("utf-8")).hexdigest()
        inf = InferenceLog(
            id=txn_id,
            user_hint=req.user_hint,
            style_id=style.id,
            prompt_hash=prompt_hash,
            output_path=file_path,
            manifest_json=json.dumps(manifest),
        )
        session.add(inf)
        session.commit()

        # calculate usage / revenue split
        pb = price_breakdown()
        ue = UsageEvent(
            id=str(uuid.uuid4()),
            inference_id=inf.id,
            gross=pb["gross"],
            infra_cost=pb["infra_cost"],
            fee=pb["fee"],
            net=pb["net"],
            artist_share_pct=pb["artist_share_pct"],
            artist_payout_est=pb["artist_payout_est"],
        )
        session.add(ue)
        session.commit()

        # Build output URL (file path for local demo)
        base = os.getenv("BACKEND_PUBLIC_URL", "http://127.0.0.1:8000")
        url = f"{base}/outputs/{txn_id}.png"
        return GenerateResp(output_url=url, receipt=manifest, usage={
            "gross": ue.gross,
            "infra_cost": ue.infra_cost,
            "fee": ue.fee,
            "net": ue.net,
            "artist_share_pct": ue.artist_share_pct,
            "artist_payout_est": ue.artist_payout_est,
        })

@app.get("/artist/{artist_id}/summary")
def artist_summary(artist_id: str):
    from sqlmodel import select, func
    with Session(engine) as session:
        styles = session.exec(select(StyleCard).where(StyleCard.artist_id == artist_id)).all()
        style_ids = [s.id for s in styles]
        inferences = session.exec(select(InferenceLog).where(InferenceLog.style_id.in_(style_ids))).all()
        usage = session.exec(select(UsageEvent)).all()
        total_payout = sum(u.artist_payout_est for u in usage if u.inference_id in [i.id for i in inferences])
        return {
            "artist_id": artist_id,
            "styles": [s.id for s in styles],
            "inference_count": len(inferences),
            "estimated_payout": round(total_payout, 4),
        }
