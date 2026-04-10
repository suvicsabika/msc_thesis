from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class PositionPoint(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    weight: int = 1


class EventItem(BaseModel):
    timestamp: float
    event_type: Literal["kill", "plant", "ace", "unknown"]
    position: PositionPoint | None = None
    description: str | None = None


class RoundEvents(BaseModel):
    round_number: int
    events: list[EventItem] = []


class MatchEvents(BaseModel):
    match_id: str
    match_name: str | None = None
    map_name: str | None = None
    rounds: list[RoundEvents] = []


class RoundStats(BaseModel):
    round_number: int
    kills: int = 0
    plants: int = 0
    dominant_zone: str = "unknown"
    activity_score: float = 0.0


class MatchStats(BaseModel):
    match_id: str
    round_stats: list[RoundStats] = []


class HeatmapData(BaseModel):
    match_id: str
    map_name: str | None = None
    points: list[PositionPoint] = []


class SummaryResponse(BaseModel):
    match_id: str
    scope: Literal["match", "round"]
    summary: str