"""All ORM table classes, imported here so they register on Base's mapper
registry together -- relationship() string references like
Mapped["CertificationORM"] on SupplierORM resolve by class name against that
registry, regardless of which module each class actually lives in.
"""
from supplyguard.data.orm.certification import CertificationORM
from supplyguard.data.orm.evaluation_case import EvaluationCaseORM
from supplyguard.data.orm.incident import IncidentORM
from supplyguard.data.orm.regulation import RegulationORM
from supplyguard.data.orm.sanction import SanctionORM
from supplyguard.data.orm.supplier import SupplierORM
from supplyguard.data.orm.sustainability import SustainabilityORM

__all__ = [
    "CertificationORM",
    "EvaluationCaseORM",
    "IncidentORM",
    "RegulationORM",
    "SanctionORM",
    "SupplierORM",
    "SustainabilityORM",
]
