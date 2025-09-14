from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine, Session, select

import os
from sqlmodel import SQLModel, Field, create_engine, Session, select

DB_PATH = os.getenv("DB_PATH", "data/fairstyle.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DB_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
# engine = create_engine(DB_URL, echo=False)

class Artist(SQLModel, table=True):
    id: str = Field(primary_key=True)
    display_name: str
    share_pct: float = 0.5  # default artist share of net

class StyleCard(SQLModel, table=True):
    id: str = Field(primary_key=True)
    artist_id: str
    name: str
    desc: str = ""
    license_tier: str = "personal"
    status: str = "active"  # or 'paused'

class InferenceLog(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_hint: Optional[str] = None
    style_id: str
    prompt_hash: str
    output_path: str
    manifest_json: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UsageEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    inference_id: str
    gross: float
    infra_cost: float
    fee: float
    net: float
    artist_share_pct: float
    artist_payout_est: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # seed demo artist/style if not exists
    with Session(engine) as session:
        artist = session.exec(select(Artist).where(Artist.id == "artist_demo")).first()
        if not artist:
            session.add(Artist(id="artist_demo", display_name="Demo Artist", share_pct=0.5))
        style = session.exec(select(StyleCard).where(StyleCard.id == "style_demo_001")).first()
        if not style:
            session.add(StyleCard(
                id="style_demo_001",
                artist_id="artist_demo",
                name="Demo Ink Sketch",
                desc="High‑contrast ink sketch style. (Demo only)",
                license_tier="personal",
                status="active",
            ))
        session.commit()
