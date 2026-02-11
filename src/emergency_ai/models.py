from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class IncidentReport:
    incident_id: str
    caller_text: str
    location: Coordinates
    reported_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class ResponseUnit:
    unit_id: str
    unit_type: str
    location: Coordinates
    speed_kmh: float
    capabilities: List[str]
    available: bool = True


@dataclass(frozen=True)
class RiskZone:
    zone_id: str
    center: Coordinates
    radius_km: float
    risk_type: str
    severity_modifier: float


@dataclass(frozen=True)
class TriageResult:
    incident_type: str
    severity_score: int
    urgent_signals: List[str]


@dataclass(frozen=True)
class UnitRecommendation:
    unit_id: str
    suitability: float
    distance_km: float
    eta_minutes: float


@dataclass(frozen=True)
class ResponsePlan:
    triage: TriageResult
    risk_context: List[str]
    recommendations: List[UnitRecommendation]
    actions: List[str]
