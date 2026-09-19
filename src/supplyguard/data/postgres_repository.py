"""Postgres-backed implementation of the shared DataRepository contract.

Every query maps SQLAlchemy rows back into the exact same Pydantic domain
models the JSON-backed repository returns -- callers (tools, agents,
services) never know or care which backend answered the query.
"""
from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from supplyguard.data.base import BaseDataRepository, SupplierNotFoundError
from supplyguard.data.db import SessionLocal
from supplyguard.data.orm import (
    CertificationORM,
    EvaluationCaseORM,
    IncidentORM,
    RegulationORM,
    SanctionORM,
    SupplierORM,
    SustainabilityORM,
)
from supplyguard.models import (
    Certification,
    Incident,
    Regulation,
    SanctionRecord,
    Supplier,
    SupplierContact,
    SustainabilitySnapshot,
)


class PostgresDataRepository(BaseDataRepository):
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    # -- mapping helpers: ORM row -> validated Pydantic domain model -----------

    @staticmethod
    def _to_supplier(row: SupplierORM) -> Supplier:
        return Supplier(
            id=row.id,
            name=row.name,
            country=row.country,
            industry=row.industry,
            tier=row.tier,
            founded_year=row.founded_year,
            employee_count=row.employee_count,
            annual_revenue_usd=row.annual_revenue_usd,
            products=row.products,
            primary_contact=SupplierContact(
                name=row.primary_contact_name,
                title=row.primary_contact_title,
                email=row.primary_contact_email,
            ),
            address=row.address,
            website=row.website,
            relationship_start_date=row.relationship_start_date,
            criticality=row.criticality,
            parent_company=row.parent_company,
        )

    @staticmethod
    def _to_certification(row: CertificationORM) -> Certification:
        return Certification(
            id=row.id,
            supplier_id=row.supplier_id,
            certification_type=row.certification_type,
            issuing_body=row.issuing_body,
            issue_date=row.issue_date,
            expiry_date=row.expiry_date,
            status=row.status,
            scope=row.scope,
        )

    @staticmethod
    def _to_incident(row: IncidentORM) -> Incident:
        return Incident(
            id=row.id,
            supplier_id=row.supplier_id,
            incident_type=row.incident_type,
            date=row.date,
            severity=row.severity,
            description=row.description,
            source=row.source,
            status=row.status,
            resolution_notes=row.resolution_notes,
        )

    @staticmethod
    def _to_sanction(row: SanctionORM) -> SanctionRecord:
        return SanctionRecord(
            id=row.id,
            entity_name=row.entity_name,
            entity_type=row.entity_type,
            list_name=row.list_name,
            match_supplier_id=row.match_supplier_id,
            match_confidence=row.match_confidence,
            sanction_reason=row.sanction_reason,
            date_added=row.date_added,
            country=row.country,
            status=row.status,
        )

    @staticmethod
    def _to_sustainability(row: SustainabilityORM) -> SustainabilitySnapshot:
        return SustainabilitySnapshot(
            id=row.id,
            supplier_id=row.supplier_id,
            reporting_year=row.reporting_year,
            carbon_emissions_tons_co2e=row.carbon_emissions_tons_co2e,
            scope_1_emissions=row.scope_1_emissions,
            scope_2_emissions=row.scope_2_emissions,
            scope_3_emissions=row.scope_3_emissions,
            renewable_energy_pct=row.renewable_energy_pct,
            water_usage_m3=row.water_usage_m3,
            waste_recycled_pct=row.waste_recycled_pct,
            esg_score=row.esg_score,
            has_sustainability_report=row.has_sustainability_report,
            science_based_targets=row.science_based_targets,
        )

    @staticmethod
    def _to_regulation(row: RegulationORM) -> Regulation:
        return Regulation(
            id=row.id,
            regulation_name=row.regulation_name,
            jurisdiction=row.jurisdiction,
            effective_date=row.effective_date,
            description=row.description,
            applicable_industries=row.applicable_industries,
            compliance_requirement=row.compliance_requirement,
            penalty_for_noncompliance=row.penalty_for_noncompliance,
        )

    @staticmethod
    def _evaluation_case_to_dict(row: EvaluationCaseORM) -> dict[str, Any]:
        return {
            "id": row.id,
            "supplier_id": row.supplier_id,
            "scenario_description": row.scenario_description,
            "expected_risk_level": row.expected_risk_level,
            "expected_route": row.expected_route,
            "expected_flags": row.expected_flags,
            "expected_agents_triggered": row.expected_agents_triggered,
            "ground_truth_findings": row.ground_truth_findings,
            "notes": row.notes,
        }

    # -- suppliers ---------------------------------------------------------

    def list_suppliers(self) -> list[Supplier]:
        with self._session_factory() as session:
            rows = session.scalars(select(SupplierORM)).all()
            return [self._to_supplier(r) for r in rows]

    def get_supplier(self, supplier_id: str) -> Supplier:
        with self._session_factory() as session:
            row = session.get(SupplierORM, supplier_id)
            if row is None:
                raise SupplierNotFoundError(supplier_id)
            return self._to_supplier(row)

    def search_suppliers(self, query: str) -> list[Supplier]:
        needle = f"%{query}%"
        with self._session_factory() as session:
            stmt = select(SupplierORM).where(
                SupplierORM.name.ilike(needle)
                | SupplierORM.country.ilike(needle)
                | SupplierORM.industry.ilike(needle)
            )
            rows = session.scalars(stmt).all()
            return [self._to_supplier(r) for r in rows]

    # -- certifications ------------------------------------------------------

    def get_certifications(self, supplier_id: str) -> list[Certification]:
        with self._session_factory() as session:
            stmt = select(CertificationORM).where(CertificationORM.supplier_id == supplier_id)
            rows = session.scalars(stmt).all()
            return [self._to_certification(r) for r in rows]

    # -- incidents -----------------------------------------------------------

    def get_incidents(self, supplier_id: str) -> list[Incident]:
        with self._session_factory() as session:
            stmt = select(IncidentORM).where(IncidentORM.supplier_id == supplier_id)
            rows = session.scalars(stmt).all()
            return [self._to_incident(r) for r in rows]

    # -- sanctions -------------------------------------------------------------

    def list_sanctions(self) -> list[SanctionRecord]:
        with self._session_factory() as session:
            rows = session.scalars(select(SanctionORM)).all()
            return [self._to_sanction(r) for r in rows]

    def get_confirmed_sanctions_matches(self, supplier_id: str) -> list[SanctionRecord]:
        with self._session_factory() as session:
            stmt = select(SanctionORM).where(SanctionORM.match_supplier_id == supplier_id)
            rows = session.scalars(stmt).all()
            return [self._to_sanction(r) for r in rows]

    def search_sanctions_by_name(self, query: str) -> list[SanctionRecord]:
        needle = f"%{query}%"
        with self._session_factory() as session:
            stmt = select(SanctionORM).where(SanctionORM.entity_name.ilike(needle))
            rows = session.scalars(stmt).all()
            return [self._to_sanction(r) for r in rows]

    # -- sustainability --------------------------------------------------------

    def get_sustainability(self, supplier_id: str) -> SustainabilitySnapshot | None:
        with self._session_factory() as session:
            stmt = select(SustainabilityORM).where(SustainabilityORM.supplier_id == supplier_id)
            row = session.scalars(stmt).first()
            return self._to_sustainability(row) if row is not None else None

    # -- regulations -------------------------------------------------------------

    def list_regulations(self) -> list[Regulation]:
        with self._session_factory() as session:
            rows = session.scalars(select(RegulationORM)).all()
            return [self._to_regulation(r) for r in rows]

    def get_regulations_for_industry(self, industry: str) -> list[Regulation]:
        with self._session_factory() as session:
            stmt = select(RegulationORM).where(
                RegulationORM.applicable_industries.any(industry)
                | RegulationORM.applicable_industries.any("all")
            )
            rows = session.scalars(stmt).all()
            return [self._to_regulation(r) for r in rows]

    # -- evaluation cases --------------------------------------------------------

    def list_evaluation_cases(self) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            rows = session.scalars(select(EvaluationCaseORM)).all()
            return [self._evaluation_case_to_dict(r) for r in rows]

    def get_evaluation_case(self, case_id: str) -> dict[str, Any]:
        with self._session_factory() as session:
            row = session.get(EvaluationCaseORM, case_id)
            if row is None:
                raise KeyError(case_id)
            return self._evaluation_case_to_dict(row)
