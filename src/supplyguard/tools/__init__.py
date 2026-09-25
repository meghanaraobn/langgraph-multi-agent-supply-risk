from supplyguard.tools.compliance import get_certifications, get_regulatory_requirements
from supplyguard.tools.rag import search_documents
from supplyguard.tools.registry import tools_for
from supplyguard.tools.risk import check_sanctions, search_incidents
from supplyguard.tools.supplier import get_supplier_by_id, search_supplier
from supplyguard.tools.sustainability import get_sustainability_information

# Each tool registers its own domain via @register_tool at definition time
# (see tools/registry.py) -- these are built from that registry, not
# hand-maintained, so a new tool can't silently go missing from its agent's
# toolset by someone forgetting to also list it here.
SUPPLIER_TOOLS = tools_for("supplier")
COMPLIANCE_TOOLS = tools_for("compliance")
RISK_TOOLS = tools_for("risk")
SUSTAINABILITY_TOOLS = tools_for("sustainability")
RAG_TOOLS = tools_for("rag")
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
