from __future__ import annotations

from typing import Iterable

from emergency_ai.intelligence import LocationIntelligenceEngine
from emergency_ai.models import IncidentReport, ResponsePlan, ResponseUnit, RiskZone


class EmergencyResponseSystem:
    def __init__(self, risk_zones: Iterable[RiskZone], units: Iterable[ResponseUnit]) -> None:
        self.engine = LocationIntelligenceEngine()
        self.risk_zones = list(risk_zones)
        self.units = list(units)

    def build_plan(self, report: IncidentReport) -> ResponsePlan:
        active_risk_zones = self.engine.active_risks(report.location, self.risk_zones)
        risk_modifier = sum(zone.severity_modifier for zone in active_risk_zones)

        triage = self.engine.triage(report, risk_modifier=risk_modifier)
        recommendations = self.engine.rank_units(
            incident_type=triage.incident_type,
            incident_location=report.location,
            units=self.units,
        )

        risk_context = [f"{zone.risk_type} ({zone.zone_id})" for zone in active_risk_zones]
        actions = self._generate_actions(triage.severity_score, triage.incident_type, recommendations)

        return ResponsePlan(
            triage=triage,
            risk_context=risk_context,
            recommendations=recommendations,
            actions=actions,
        )

    @staticmethod
    def _generate_actions(severity: int, incident_type: str, recommendations) -> list[str]:
        actions = [
            f"Classify incident as {incident_type} with severity {severity}/10.",
            "Notify nearest command center and initiate digital incident log.",
        ]

        if recommendations:
            top = recommendations[0]
            actions.append(
                f"Dispatch primary unit {top.unit_id} (ETA {top.eta_minutes} min, distance {top.distance_km} km)."
            )

        if severity >= 8:
            actions.append("Escalate to multi-agency response and request regional backup.")
            actions.append("Trigger public alert workflow if life safety risk may spread.")
        elif severity >= 5:
            actions.append("Stage secondary support units and monitor telemetry every 3 minutes.")
        else:
            actions.append("Handle with local unit response and maintain periodic updates.")

        return actions
