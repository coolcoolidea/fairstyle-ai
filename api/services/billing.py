import os

def get_env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except Exception:
        return default

def price_breakdown():
    gross = get_env_float("PRICE_PER_IMAGE", 0.20)
    infra = get_env_float("INFRA_COST_PER_IMAGE", 0.05)
    fee_rate = get_env_float("FEE_RATE", 0.03)
    fee = round(gross * fee_rate, 4)
    net = round(gross - infra - fee, 4)
    artist_pct = get_env_float("ARTIST_SHARE_PCT_DEFAULT", 0.5)
    artist_payout = round(net * artist_pct, 4)
    return {
        "gross": gross,
        "infra_cost": infra,
        "fee": fee,
        "net": net,
        "artist_share_pct": artist_pct,
        "artist_payout_est": artist_payout,
    }
