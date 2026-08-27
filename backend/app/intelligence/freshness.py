"""Freshness labels. Provider-specific notes override generic bins."""
from datetime import datetime, timezone
from typing import Optional
from backend.app.intelligence.schemas import Freshness


def classify_age_seconds(age: Optional[float], *, live_capable: bool) -> str:
    if age is None:
        return "UNKNOWN"
    if live_capable and age < 5 * 60:
        return "LIVE"
    if age < 60 * 60:
        return "VERY_RECENT"
    if age < 6 * 3600:
        return "RECENT"
    if age < 96 * 3600:
        return "HISTORICAL_RECENT"
    return "HISTORICAL"


def build_freshness(
    source: str,
    observation_time: Optional[datetime],
    retrieved_at: Optional[datetime] = None,
    *,
    live_capable: bool = False,
    provider_note: Optional[str] = None,
    force_status: Optional[str] = None,
) -> Freshness:
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    age = None
    if observation_time is not None:
        obs = observation_time
        if obs.tzinfo is None:
            obs = obs.replace(tzinfo=timezone.utc)
        age = max(0.0, (retrieved_at - obs).total_seconds())
    status = force_status or classify_age_seconds(age, live_capable=live_capable)
    if not live_capable and status == "LIVE":
        status = "VERY_RECENT"
        provider_note = provider_note or "Provider is not a live AIS feed."
    return Freshness(
        source=source,
        retrieved_at=retrieved_at,
        observation_time=observation_time,
        data_age_seconds=age,
        freshness_status=status,
        provider_freshness_note=provider_note,
    )
