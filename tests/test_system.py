from emergency_ai.models import Coordinates, IncidentReport, ResponseUnit, RiskZone
from emergency_ai.system import EmergencyResponseSystem


def test_high_severity_incident_with_risk_zone_escalates() -> None:
    system = EmergencyResponseSystem(
        risk_zones=[
            RiskZone(
                zone_id="IND-1",
                center=Coordinates(34.050, -118.250),
                radius_km=4.0,
                risk_type="industrial corridor",
                severity_modifier=2.0,
            )
        ],
        units=[
            ResponseUnit(
                unit_id="MED-1",
                unit_type="ambulance",
                location=Coordinates(34.052, -118.245),
                speed_kmh=75,
                capabilities=["Paramedic", "Ambulance"],
            ),
            ResponseUnit(
                unit_id="FIRE-1",
                unit_type="fire engine",
                location=Coordinates(34.058, -118.240),
                speed_kmh=65,
                capabilities=["Fire Engine", "Hazmat"],
            ),
        ],
    )

    report = IncidentReport(
        incident_id="INC-9",
        caller_text="Explosion with heavy smoke and trapped victims not breathing.",
        location=Coordinates(34.051, -118.248),
    )

    plan = system.build_plan(report)

    assert plan.triage.incident_type == "fire"
    assert plan.triage.severity_score >= 8
    assert any("industrial corridor" in item for item in plan.risk_context)
    assert any("Escalate to multi-agency response" in item for item in plan.actions)


def test_recommendation_prefers_nearby_capable_unit() -> None:
    system = EmergencyResponseSystem(
        risk_zones=[],
        units=[
            ResponseUnit(
                unit_id="FAR-UNIT",
                unit_type="rescue",
                location=Coordinates(35.0, -119.0),
                speed_kmh=60,
                capabilities=["Search and Rescue"],
            ),
            ResponseUnit(
                unit_id="NEAR-MED",
                unit_type="ambulance",
                location=Coordinates(34.0525, -118.2437),
                speed_kmh=80,
                capabilities=["Paramedic", "Advanced Life Support"],
            ),
        ],
    )

    report = IncidentReport(
        incident_id="INC-10",
        caller_text="Person unconscious and bleeding in office lobby.",
        location=Coordinates(34.0522, -118.2437),
    )

    plan = system.build_plan(report)

    assert plan.recommendations
    assert plan.recommendations[0].unit_id == "NEAR-MED"
    assert plan.recommendations[0].eta_minutes < plan.recommendations[-1].eta_minutes
