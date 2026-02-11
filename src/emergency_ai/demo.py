from __future__ import annotations

from emergency_ai.models import Coordinates, IncidentReport, ResponseUnit, RiskZone
from emergency_ai.system import EmergencyResponseSystem


def main() -> None:
    units = [
        ResponseUnit(
            unit_id="MED-12",
            unit_type="ambulance",
            location=Coordinates(40.741, -73.989),
            speed_kmh=70,
            capabilities=["Paramedic", "Ambulance", "Advanced Life Support"],
        ),
        ResponseUnit(
            unit_id="FIRE-7",
            unit_type="fire engine",
            location=Coordinates(40.729, -73.997),
            speed_kmh=65,
            capabilities=["Fire Engine", "Hazmat"],
        ),
        ResponseUnit(
            unit_id="SAR-3",
            unit_type="rescue",
            location=Coordinates(40.751, -73.971),
            speed_kmh=60,
            capabilities=["Search and Rescue", "Boat Rescue"],
        ),
    ]

    zones = [
        RiskZone(
            zone_id="FLOOD-A",
            center=Coordinates(40.735, -73.995),
            radius_km=3.5,
            risk_type="urban flood risk",
            severity_modifier=1.0,
        )
    ]

    report = IncidentReport(
        incident_id="INC-1001",
        caller_text=(
            "Multiple people trapped after explosion and fire in lower building levels; "
            "heavy smoke and severe injuries reported."
        ),
        location=Coordinates(40.733, -73.993),
    )

    system = EmergencyResponseSystem(risk_zones=zones, units=units)
    plan = system.build_plan(report)

    print("=== AI Emergency Response Plan ===")
    print(f"Incident type: {plan.triage.incident_type}")
    print(f"Severity: {plan.triage.severity_score}/10")
    print(f"Urgent signals: {', '.join(plan.triage.urgent_signals) or 'None'}")
    print(f"Risk context: {', '.join(plan.risk_context) or 'None'}")
    print("\nTop units:")
    for rec in plan.recommendations:
        print(f" - {rec.unit_id}: suitability={rec.suitability}, ETA={rec.eta_minutes} min")

    print("\nActions:")
    for action in plan.actions:
        print(f" - {action}")


if __name__ == "__main__":
    main()
