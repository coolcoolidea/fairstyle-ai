# FairStyle-AI 🎨

**Consent-first, licensed AI art styles with transparent, per-generation revenue sharing.**  
This is a **proof-of-concept** (PoC) you can run locally in minutes: Streamlit UI → FastAPI → (placeholder image or your own provider) → write an embedded **Content Credential-style** manifest → log a **usage event** → show **artist revenue share**.

> Status: Prototype for research & discussion. Not legal advice. Not a commercial product.

---

## Why

Most AI image generators were trained on data that likely includes creators' works **without consent or compensation**. That erodes trust and creates legal uncertainty for teams who want to use AI safely.

**FairStyle-AI** explores a simple question:  
**What if artists opt in, license their style, and get paid every time their style is used?**

---

## What this repo is (and isn’t)

**This repo IS** a tiny demo that shows:
- Picking a **licensed “Style Card”** (placeholder in the demo).
- Generating an image (**placeholder by default**; you can wire Replicate/Hugging Face later).
- Embedding a lightweight manifest (JSON stored inside PNG metadata) with `styleId`, `artistId`, `licenseTier`, `txnId`, `timestamp`.
- Recording a **usage_event** with a mock **revenue split** for the artist.

**This repo is NOT**:
- A model training pipeline.
- Legal cover / indemnity.
- Production-grade attribution or fraud prevention.

---

## Architecture (MVP)

~~~
[Streamlit UI] --HTTP--> [FastAPI]
    |                          |
    | prompt + style_id        | generates image (provider or placeholder)
    |                          | embeds manifest (PNG metadata)
    |                          | writes usage_event (SQLite)
    |                          v
    |<---- image + receipt ----|
~~~

- **UI**: `app/Home.py` (Streamlit)  
- **API**: `api/main.py` (FastAPI) — serves outputs at `/outputs/<txn>.png`  
- **Services**: `api/services/` (inference, manifest, billing)  
- **Data**: SQLite database at `data/fairstyle.db` + PNGs under `data/outputs/`  
- **Styles**: JSON metadata under `styles/` (no weights in repo)

The API supports a **blocklist** (name-blocking) to avoid prompts that mention unlicensed artist names (see `infra/blocklist.txt`).

---

## Quickstart

### 1) Setup

~~~bash
git clone <your-fork-or-repo-url>
cd FairStyle-AI
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
~~~

### 2) (Optional) Add real inference (not wired by default)

- Put your tokens in `.env` (you will also need to extend `api/services/inference.py`):
  - `REPLICATE_API_TOKEN=`
  - `HF_API_TOKEN=`
- By default the demo **falls back to a local placeholder image**.

### 3) Run API and UI

Open two terminals.

**Terminal A — API**
~~~bash
uvicorn api.main:app --reload --port 8000
~~~

**Terminal B — UI**
~~~bash
streamlit run app/Home.py
~~~

Open the Streamlit URL (usually `http://localhost:8501`).

---

## Using the demo

1. Pick a **Style Card** (demo includes one placeholder style).  
2. Enter a prompt. The API will **block known unlicensed names** (edit `infra/blocklist.txt`).  
3. Click **Generate**. You will see:
   - The **image** (placeholder PNG unless you wired a real provider).  
   - A **receipt** (manifest JSON) showing `txnId`, `styleId`, `artistId`, `licenseTier`, `timestamp`.  
   - A **usage event** with mock **pricing & artist share**.

Files are saved to `data/outputs/<txn>.png` and a local SQLite DB `data/fairstyle.db` is created on first run.

---

## Configuration

`.env` keys (all optional; defaults exist):

~~~
# UI -> API
BACKEND_URL=http://127.0.0.1:8000

# API builds image URLs like /outputs/<txn>.png
BACKEND_PUBLIC_URL=http://127.0.0.1:8000

# Pricing (demo only)
PRICE_PER_IMAGE=0.20
INFRA_COST_PER_IMAGE=0.05
FEE_RATE=0.03
ARTIST_SHARE_PCT_DEFAULT=0.5

# Optional inference providers (not wired by default)
REPLICATE_API_TOKEN=
HF_API_TOKEN=
~~~

---

## Manifest (Content Credential, PoC)

This PoC **embeds a small JSON manifest into the PNG** using metadata (via PIL). Example:

~~~json
{
  "spec": "fairstyle-manifest@0.1",
  "txnId": "3a1b8f9c-…",
  "styleId": "style_demo_001",
  "artistId": "artist_demo",
  "licenseTier": "personal",
  "timestamp": "2025-01-01T12:34:56Z",
  "hash": "sha256:..."
}
~~~

For production, adopt **C2PA/Content Credentials** with signing. This PoC only demonstrates the data fields.

---

## Data model (SQLite, SQLModel)

- `artist(id, display_name, share_pct)`  
- `style_card(id, artist_id, name, desc, license_tier, status)`  
- `inference_log(id, user_hint, style_id, prompt_hash, output_path, manifest_json, created_at)`  
- `usage_event(id, inference_id, gross, infra_cost, fee, net, artist_share_pct, artist_payout_est, created_at)`

---

## Roadmap (suggested)

- [ ] Multiple styles & creators dashboard  
- [ ] Signed **Content Credentials (C2PA)**  
- [ ] Stripe test mode, payout CSV export  
- [ ] Diversity-aware recommendations  
- [ ] (Stretch) Influence estimation -> dynamic split among **licensed** styles

---

## Contributing

Discussions, issues, and PRs are welcome.  
If you are an artist and want to be part of a private PoC, open an issue.

---

## Disclaimer

- This repository is for research, prototyping, and discussion.  
- Any artist names in the demo are placeholders.  
- This is not legal advice and not a commercial service.

---

## License

- **Code**: MIT (see [LICENSE](./LICENSE)).  
- **No model weights or third-party assets** are included in this repo.
