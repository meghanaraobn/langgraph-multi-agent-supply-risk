from supplyguard.tools.compliance import get_certifications, get_regulatory_requirements
from supplyguard.tools.rag import search_documents
from supplyguard.tools.risk import check_sanctions, search_incidents
from supplyguard.tools.supplier import get_supplier_by_id, search_supplier
from supplyguard.tools.sustainability import get_sustainability_information

SUPPLIER_TOOLS = [search_supplier, get_supplier_by_id]
COMPLIANCE_TOOLS = [get_certifications, get_regulatory_requirements]
RISK_TOOLS = [search_incidents, check_sanctions]
SUSTAINABILITY_TOOLS = [get_sustainability_information]
RAG_TOOLS = [search_documents]
ALL_TOOLS = SUPPLIER_TOOLS + COMPLIANCE_TOOLS + RISK_TOOLS + SUSTAINABILITY_TOOLS + RAG_TOOLS

__all__ = [
    "search_supplier",
    "get_supplier_by_id",
    "get_certifications",
    "get_regulatory_requirements",
    "search_incidents",
    "check_sanctions",
    "get_sustainability_information",
    "search_documents",
    "SUPPLIER_TOOLS",
    "COMPLIANCE_TOOLS",
    "RISK_TOOLS",
    "SUSTAINABILITY_TOOLS",
    "RAG_TOOLS",
    "ALL_TOOLS",
]
