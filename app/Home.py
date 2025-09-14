import os, json, requests, streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="FairStyle-AI (PoC)", layout="centered")
st.title("FairStyle-AI (PoC) 🎨")
st.caption("Consent-first licensed styles • per-generation revenue sharing • local prototype")

with st.sidebar:
    st.header("Config")
    st.write("Backend:", BACKEND)
    st.write("This is a demo. No real artists involved.")
    st.markdown("---")
    st.markdown("**Notes**")
    st.write("- Prompts containing blocked names are rejected.")
    st.write("- If no provider tokens are set, a placeholder image is generated.")

# Load styles
try:
    styles = requests.get(f"{BACKEND}/styles", timeout=10).json()
except Exception as e:
    st.error(f"Cannot reach API at {BACKEND}. Is it running?")
    st.stop()

def label_for(s):
    artist_label = s.get("artist_display_name", "Artist")
    return f"{s['name']} — {artist_label} ({s['id']})"

style_map = {label_for(s): s for s in styles}
choice = st.selectbox("Choose a licensed Style Card", options=list(style_map.keys()))
sel = style_map[choice]

prompt = st.text_area("Your prompt", height=120, placeholder="a calm city street at dawn, high-contrast ink wash, fine line art")
user_hint = st.text_input("User hint (optional, stored for auditing)")

# ====== Always-on Pricing & Revenue Split (Demo) ======
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

st.caption("Tip: tweak .env → PRICE_PER_IMAGE / INFRA_COST_PER_IMAGE / FEE_RATE / ARTIST_SHARE_PCT_DEFAULT")

# ====== Generate action ======
if st.button("Generate", type="primary", disabled=not prompt.strip()):
    try:
        payload = {"prompt": prompt.strip(), "style_id": sel["id"], "user_hint": user_hint or None}
        resp = requests.post(f"{BACKEND}/generate", json=payload, timeout=60)
        if resp.status_code != 200:
            st.error(f"Generate failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            st.subheader("Output")
            artist_label = sel.get("artist_display_name", "Artist")
            st.caption(f"Style: **{sel['name']}** · Artist: **{artist_label}** · License: **{sel.get('license_tier','personal')}**")
            st.image(data["output_url"])
            st.subheader("Receipt (Manifest)")
            st.code(json.dumps(data["receipt"], indent=2))
            st.subheader("Usage Event (Pricing Split)")
            st.json(data["usage"])
            st.success("Saved to data/outputs and logged to SQLite.")
    except Exception as e:
        st.error(f"Error: {e}")
