import os, json, glob, requests, streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

load_dotenv()
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
PUBLIC  = os.getenv("BACKEND_PUBLIC_URL", BACKEND)

# ---- Page config ----
st.set_page_config(
    page_title="FairStyle-AI 🎨",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.title("FairStyle-AI (PoC) 🎨")
st.caption("Consent-first licensed styles • per-generation revenue sharing • local prototype")

# ---- Sidebar ----
with st.sidebar:
    st.header("Config")
    st.write("Backend:", BACKEND)
    st.write("Public base:", PUBLIC)
    st.write("This is a demo. No real artists involved.")
    st.markdown("---")
    st.write("- Prompts containing blocked names are rejected.")
    st.write("- If no provider tokens are set, a placeholder image is generated.")

# ---- Helpers ----
def resolve_img_url(u: str):
    """Resolve preview URL: allow absolute http(s), or relative path joined with BACKEND_PUBLIC_URL."""
    if not u:
        return "https://placehold.co/512x512?text=Style"
    if u.startswith(("http://", "https://")):
        return u
    return PUBLIC.rstrip("/") + "/" + u.lstrip("/")

def normalize_style(s: dict) -> dict:
    """Map style JSON into a standard shape with safe defaults."""
    return {
        "id": s.get("id") or "style",
        "name": s.get("name") or "Demo Style",
        "artist_display_name": s.get("artist_display_name") or s.get("artist") or "Artist",
        "license_tier": s.get("license_tier") or "personal",
        "share_pct": s.get("share_pct") or "50%",
        "thumbnail": resolve_img_url(s.get("thumbnail") or s.get("preview_url")),
    }

def load_backend_styles():
    """Load styles from backend /styles endpoint."""
    try:
        r = requests.get(f"{BACKEND}/styles", timeout=5)
        r.raise_for_status()
        data = r.json()
        return [normalize_style(x) for x in (data if isinstance(data, list) else [data])]
    except Exception:
        return []

def load_local_styles():
    """Load styles from local JSON files in styles/ directory."""
    out = []
    for p in glob.glob("styles/*.json"):
        try:
            data = json.loads(Path(p).read_text())
            if isinstance(data, list):
                out.extend([normalize_style(x) for x in data])
            elif isinstance(data, dict):
                out.append(normalize_style(data))
        except Exception as e:
            st.warning(f"Failed to read {p}: {e}")
    return out

# ---- Load and merge styles ----
api_styles = load_backend_styles()
local_styles = load_local_styles()

merged = {}
order = []
for s in api_styles + local_styles:  # local overrides API on conflicts
    merged[s["id"]] = s
    if s["id"] not in order:
        order.append(s["id"])
styles = [merged[i] for i in order]

# Warn on duplicate IDs
ids = [s["id"] for s in api_styles] + [s["id"] for s in local_styles]

if not styles:
    st.error("No styles available.")
    st.stop()

# ---- Linked card grid and dropdown ----
if "selected_style_id" not in st.session_state:
    st.session_state["selected_style_id"] = styles[0]["id"]

# Card grid
st.subheader("Pick a Licensed Style")
cols = st.columns(3)
for i, s in enumerate(styles):
    with cols[i % 3]:
        with st.container(border=True):
            st.image(s["thumbnail"], use_column_width=True)
            st.markdown(f"### {s['name']}")
            st.caption(f"Artist: {s['artist_display_name']} · Share: {s['share_pct']} · Tier: {s['license_tier']}")
            if st.button("Use this style", key=f"use_{s['id']}"):
                st.session_state["selected_style_id"] = s["id"]

# Dropdown, synchronized with card selection
label_map = {f"{s['name']} — {s['artist_display_name']} ({s['id']})": s for s in styles}
current_label = next(lbl for lbl, s in label_map.items() if s["id"] == st.session_state["selected_style_id"])
choice = st.selectbox("…or select from the list", options=list(label_map.keys()), index=list(label_map.keys()).index(current_label))
sel = label_map[choice]
st.session_state["selected_style_id"] = sel["id"]

# ---- Pricing (Demo) ----
price = float(os.getenv("PRICE_PER_IMAGE", "0.20"))
infra = float(os.getenv("INFRA_COST_PER_IMAGE", "0.05"))
fee_rate = float(os.getenv("FEE_RATE", "0.03"))
artist_pct = float(os.getenv("ARTIST_SHARE_PCT_DEFAULT", "0.5"))
fee = round(price * fee_rate, 4)
net = round(price - infra - fee, 4)
artist_payout = round(net * artist_pct, 4)

st.markdown("---")
st.subheader("Pricing & Revenue Split (Demo)")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Gross (per image)", f"{price:.2f}")
    st.metric("Infra cost (est.)", f"{infra:.2f}")
with c2:
    st.metric("Fee", f"{fee:.3f}")
    st.metric("Net", f"{net:.3f}")
with c3:
    st.metric("Artist share", f"{artist_pct*100:.0f}%")
    st.metric("Artist payout (est.)", f"{artist_payout:.3f}")
st.caption("Tweak .env: PRICE_PER_IMAGE / INFRA_COST_PER_IMAGE / FEE_RATE / ARTIST_SHARE_PCT_DEFAULT")

# ---- Generate ----
st.markdown("---")
st.subheader("Generate")
prompt = st.text_area("Your prompt", height=120, placeholder="a calm city street at dawn, high-contrast ink wash, fine line art")
user_hint = st.text_input("User hint (optional, stored for auditing)")

if st.button("Generate", type="primary", disabled=not prompt.strip()):
    try:
        payload = {"prompt": prompt.strip(), "style_id": sel["id"], "user_hint": user_hint or None}
        resp = requests.post(f"{BACKEND}/generate", json=payload, timeout=60)
        if resp.status_code != 200:
            st.error(f"Generate failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            st.subheader("Output")
            st.caption(f"Style: **{sel['name']}** · Artist: **{sel['artist_display_name']}** · License: **{sel['license_tier']}**")
            st.image(data["output_url"])
            st.subheader("Receipt (Manifest)")
            st.code(json.dumps(data["receipt"], indent=2))
            st.subheader("Usage Event (Pricing Split)")
            st.json(data["usage"])
            st.success("Saved to data/outputs and logged to SQLite.")
    except Exception as e:
        st.error(f"Error: {e}")
