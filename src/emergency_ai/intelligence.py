from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, List

from emergency_ai.models import (
    Coordinates,
    IncidentReport,
    ResponseUnit,
    RiskZone,
    TriageResult,
    UnitRecommendation,
)


INCIDENT_KEYWORDS = {
    "medical": {"unconscious", "bleeding", "heart", "stroke", "injury", "collapse"},
    "fire": {"fire", "smoke", "burning", "explosion", "flames"},
    "police": {"assault", "weapon", "robbery", "shooter", "violence"},
    "rescue": {"trapped", "flood", "landslide", "missing", "stranded"},
    "infrastructure": {"gas leak", "chemical", "power outage", "bridge", "spill"},
}

SEVERITY_SIGNALS = {
    "critical": {"unconscious", "explosion", "active shooter", "mass casualty", "not breathing"},
    "high": {"severe", "trapped", "weapon", "spreading", "major"},
    "moderate": {"injury", "smoke", "bleeding", "flooding", "panic"},
}

CAPABILITY_MAP = {
    "medical": {"paramedic", "ambulance", "advanced life support"},
    "fire": {"fire engine", "hazmat", "ladder"},
    "police": {"law enforcement", "tactical", "crowd control"},
    "rescue": {"search and rescue", "boat rescue", "high-angle rescue"},
    "infrastructure": {"utility response", "hazmat", "engineering"},
}


class LocationIntelligenceEngine:
    """Provides incident triage and geospatial recommendation logic."""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        clean = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text)
        return [t for t in clean.split() if t]

    @staticmethod
    def haversine_km(origin: Coordinates, target: Coordinates) -> float:
        r = 6371.0
        lat1, lon1 = math.radians(origin.latitude), math.radians(origin.longitude)
        lat2, lon2 = math.radians(target.latitude), math.radians(target.longitude)
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    def infer_incident_type(self, tokens: Iterable[str]) -> str:
        counts = Counter()
        token_set = set(tokens)
        joined_text = " ".join(tokens)

        for category, keywords in INCIDENT_KEYWORDS.items():
            for keyword in keywords:
                if " " in keyword and keyword in joined_text:
                    counts[category] += 2
                elif keyword in token_set:
                    counts[category] += 1

        if not counts:
            return "medical"
        return counts.most_common(1)[0][0]

    def severity_score(self, tokens: Iterable[str], risk_modifier: float = 0.0) -> tuple[int, List[str]]:
        token_set = set(tokens)
        joined_text = " ".join(tokens)
        score = 3
        urgent = []

        for signal in SEVERITY_SIGNALS["critical"]:
            if (" " in signal and signal in joined_text) or signal in token_set:
                score += 4
                urgent.append(signal)

        for signal in SEVERITY_SIGNALS["high"]:
            if signal in token_set:
                score += 2
                urgent.append(signal)

        for signal in SEVERITY_SIGNALS["moderate"]:
            if signal in token_set:
                score += 1

        score = min(10, max(1, round(score + risk_modifier)))
        return score, sorted(set(urgent))

    def triage(self, report: IncidentReport, risk_modifier: float = 0.0) -> TriageResult:
        tokens = self.tokenize(report.caller_text)
        incident_type = self.infer_incident_type(tokens)
        score, urgent = self.severity_score(tokens, risk_modifier=risk_modifier)
        return TriageResult(incident_type=incident_type, severity_score=score, urgent_signals=urgent)

    def active_risks(self, location: Coordinates, risk_zones: Iterable[RiskZone]) -> List[RiskZone]:
        active = []
        for zone in risk_zones:
            distance = self.haversine_km(location, zone.center)
            if distance <= zone.radius_km:
                active.append(zone)
        return active

    def rank_units(
        self,
        incident_type: str,
        incident_location: Coordinates,
        units: Iterable[ResponseUnit],
        limit: int = 3,
    ) -> List[UnitRecommendation]:
        capabilities_needed = CAPABILITY_MAP.get(incident_type, set())
        ranked = []
        for unit in units:
            if not unit.available:
                continue

            distance = self.haversine_km(incident_location, unit.location)
            eta_min = (distance / max(unit.speed_kmh, 1)) * 60
            capability_overlap = len(capabilities_needed.intersection({c.lower() for c in unit.capabilities}))
            base = 100 - (distance * 3) - eta_min
            suitability = base + (capability_overlap * 20)

            ranked.append(
                UnitRecommendation(
                    unit_id=unit.unit_id,
                    suitability=round(suitability, 2),
                    distance_km=round(distance, 2),
                    eta_minutes=round(eta_min, 1),
                )
            )

        ranked.sort(key=lambda item: item.suitability, reverse=True)
        return ranked[:limit]
