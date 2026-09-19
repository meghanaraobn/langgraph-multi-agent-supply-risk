"""Load the synthetic JSON dataset into Postgres.

Reuses the JSON-backed DataRepository, so every record has already passed
through its Pydantic model's validation before it's written to the database
-- Postgres never receives data the domain models themselves would reject.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from supplyguard.data.db import Base, SessionLocal, engine
from supplyguard.data.orm import (
    CertificationORM,
    EvaluationCaseORM,
    IncidentORM,
    RegulationORM,
    SanctionORM,
    SupplierORM,
    SustainabilityORM,
)
from supplyguard.data.repository import JsonDataRepository


def seed(reset: bool = True) -> None:
    repo = JsonDataRepository()

    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        _seed_suppliers(session, repo)
        session.flush()  # suppliers must exist before any FK to them is inserted
        _seed_certifications(session, repo)
        _seed_incidents(session, repo)
        _seed_sanctions(session, repo)
        _seed_sustainability(session, repo)
        _seed_regulations(session, repo)
        _seed_evaluation_cases(session, repo)
        session.commit()


def _seed_suppliers(session: Session, repo: JsonDataRepository) -> None:
    for s in repo.list_suppliers():
        session.add(
            SupplierORM(
                id=s.id,
                name=s.name,
                country=s.country,
                industry=s.industry,
                tier=s.tier,
                founded_year=s.founded_year,
                employee_count=s.employee_count,
                annual_revenue_usd=s.annual_revenue_usd,
                products=s.products,
                primary_contact_name=s.primary_contact.name,
                primary_contact_title=s.primary_contact.title,
                primary_contact_email=s.primary_contact.email,
                address=s.address,
                website=s.website,
                relationship_start_date=s.relationship_start_date,
                criticality=s.criticality,
                parent_company=s.parent_company,
            )
        )


def _seed_certifications(session: Session, repo: JsonDataRepository) -> None:
    for supplier in repo.list_suppliers():
        for c in repo.get_certifications(supplier.id):
            session.add(
                CertificationORM(
                    id=c.id,
                    supplier_id=c.supplier_id,
                    certification_type=c.certification_type,
                    issuing_body=c.issuing_body,
                    issue_date=c.issue_date,
                    expiry_date=c.expiry_date,
                    status=c.status,
                    scope=c.scope,
                )
            )


def _seed_incidents(session: Session, repo: JsonDataRepository) -> None:
    for supplier in repo.list_suppliers():
        for i in repo.get_incidents(supplier.id):
            session.add(
                IncidentORM(
                    id=i.id,
                    supplier_id=i.supplier_id,
                    incident_type=i.incident_type,
                    date=i.date,
                    severity=i.severity.value,
                    description=i.description,
                    source=i.source,
                    status=i.status,
                    resolution_notes=i.resolution_notes,
                )
            )


def _seed_sanctions(session: Session, repo: JsonDataRepository) -> None:
    for s in repo.list_sanctions():
        session.add(
            SanctionORM(
                id=s.id,
                entity_name=s.entity_name,
                entity_type=s.entity_type,
                list_name=s.list_name,
                match_supplier_id=s.match_supplier_id,
                match_confidence=s.match_confidence,
                sanction_reason=s.sanction_reason,
                date_added=s.date_added,
                country=s.country,
                status=s.status,
            )
        )


def _seed_sustainability(session: Session, repo: JsonDataRepository) -> None:
    for supplier in repo.list_suppliers():
        record = repo.get_sustainability(supplier.id)
        if record is None:
            continue
        session.add(
            SustainabilityORM(
                id=record.id,
                supplier_id=record.supplier_id,
                reporting_year=record.reporting_year,
                carbon_emissions_tons_co2e=record.carbon_emissions_tons_co2e,
                scope_1_emissions=record.scope_1_emissions,
                scope_2_emissions=record.scope_2_emissions,
                scope_3_emissions=record.scope_3_emissions,
                renewable_energy_pct=record.renewable_energy_pct,
                water_usage_m3=record.water_usage_m3,
                waste_recycled_pct=record.waste_recycled_pct,
                esg_score=record.esg_score,
                has_sustainability_report=record.has_sustainability_report,
                science_based_targets=record.science_based_targets,
            )
        )


def _seed_regulations(session: Session, repo: JsonDataRepository) -> None:
    for r in repo.list_regulations():
        session.add(
            RegulationORM(
                id=r.id,
                regulation_name=r.regulation_name,
                jurisdiction=r.jurisdiction,
                effective_date=r.effective_date,
                description=r.description,
                applicable_industries=r.applicable_industries,
                compliance_requirement=r.compliance_requirement,
                penalty_for_noncompliance=r.penalty_for_noncompliance,
            )
        )


def _seed_evaluation_cases(session: Session, repo: JsonDataRepository) -> None:
    for case in repo.list_evaluation_cases():
        session.add(
            EvaluationCaseORM(
                id=case["id"],
                supplier_id=case["supplier_id"],
                scenario_description=case["scenario_description"],
                expected_risk_level=case["expected_risk_level"],
                expected_route=case["expected_route"],
                expected_flags=case["expected_flags"],
                expected_agents_triggered=case["expected_agents_triggered"],
                ground_truth_findings=case["ground_truth_findings"],
                notes=case.get("notes"),
            )
        )


if __name__ == "__main__":
    seed()
    print("Seed complete.")
