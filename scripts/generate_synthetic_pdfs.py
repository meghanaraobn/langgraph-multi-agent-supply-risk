"""One-off generator for the synthetic supplier audit report PDFs used to
exercise the RAG pipeline. Not part of the app or CI -- run by hand:

    python scripts/generate_synthetic_pdfs.py

Writes PDFs to data/documents/raw/ and data/documents/manifest.json, which
supplyguard.rag.ingest.ingest_from_manifest() reads to know which PDF
belongs to which supplier.

Content is entirely fictional, built around seven real supplier ids already
in data/suppliers.json (SUP-001/002/003/004/009/011/013) so the resulting
findings tie back into the existing investigation flow. Deliberately spans a
range of risk profiles and document types (clean audits, moderate and
serious non-conformances, and one non-factory transparency/sanctions
desk review) so rag_agent's findings show real variance rather than
several copies of the same result.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
RAW_DIR = DOCUMENTS_DIR / "raw"

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle(name="AuditTitle", parent=_styles["Title"], fontSize=16))
_styles.add(ParagraphStyle(name="AuditHeading", parent=_styles["Heading2"], spaceBefore=14))
_styles.add(ParagraphStyle(name="AuditBody", parent=_styles["BodyText"], spaceAfter=8))

AUDITS: list[dict[str, Any]] = [
    {
        "supplier_id": "SUP-001",
        "document_id": "SUP-001-audit",
        "file": "SUP-001-audit-report.pdf",
        "title": "Meridian Electronics Co. — On-Site Audit Report",
        "meta": {
            "Facility": "Hsinchu Science Park, Taiwan",
            "Audit type": "SA8000 social compliance + ISO 14001 environmental",
            "Audit dates": "2026-03-10 to 2026-03-11 (2 days)",
            "Auditor": "Meridian Assurance Partners (third-party)",
            "Overall rating": "Satisfactory — Low Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This audit found Meridian Electronics Co.'s Hsinchu facility to be in "
                    "substantial conformance with SA8000 social compliance and ISO 14001 "
                    "environmental requirements. No major non-conformances were identified. "
                    "One minor observation was raised and corrected on-site during the audit.",
                ],
            ),
            (
                "Labor Practices",
                [
                    "A review of 30 randomly sampled timekeeping records found working hours "
                    "and wage payments consistent with Taiwanese labor law and the facility's "
                    "stated policies. No evidence of underage workers was found; all sampled "
                    "personnel files contained valid age verification documentation. Overtime "
                    "was voluntary and compensated at the legally required premium rate in all "
                    "sampled cases.",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Personal protective equipment was observed in use at all inspected "
                    "workstations on the SMT and PCB assembly lines. Fire drills are conducted "
                    "quarterly per facility records, with the most recent drill logged on "
                    "2026-01-14. One observation was raised: fire extinguisher inspection tags "
                    "in Building C were found to be 2 weeks overdue for their monthly check. "
                    "Facility staff re-inspected and re-tagged all affected extinguishers "
                    "before the audit concluded.",
                ],
            ),
            (
                "Environmental",
                [
                    "Wastewater discharge samples taken during the audit were within the "
                    "facility's environmental permit limits for all tested parameters. "
                    "Hazardous waste (solder dross, spent etching solution) manifests were "
                    "reviewed for the preceding 6 months and reconciled correctly against "
                    "licensed disposal contractor records.",
                ],
            ),
            (
                "Management Systems & Documentation",
                [
                    "The facility's internal audit and management review process was found to "
                    "operate on schedule, with the most recent management review dated "
                    "2025-12-08. Corrective and preventive action (CAPA) records for the "
                    "preceding 12 months show a median closure time of 9 days, well within "
                    "the facility's own 30-day target. Training records for all 14 sampled "
                    "line supervisors showed current certification in both SA8000 awareness "
                    "and ISO 14001 procedures.",
                ],
            ),
            (
                "Worker Interview Summary",
                [
                    "18 workers were interviewed individually across day and night shifts. "
                    "No worker reported unpaid wages, restricted freedom of movement, or "
                    "retaliation concerns. Workers consistently described the grievance "
                    "hotline and knew how to reach it, which the auditor verified by testing "
                    "the hotline number posted at two of the three sampled workstations.",
                ],
            ),
        ],
        "table": {
            "heading": "Corrective Action Log",
            "header": ["Finding", "Severity", "Due Date", "Status"],
            "rows": [
                [
                    "Overdue fire extinguisher inspection tags, Building C",
                    "Minor",
                    "Immediate",
                    "Closed — corrected on-site",
                ],
            ],
        },
        "conclusion": (
            "Recommendation: continued certification with no follow-up audit required "
            "before the next scheduled annual audit (2027-03)."
        ),
    },
    {
        "supplier_id": "SUP-002",
        "document_id": "SUP-002-audit",
        "file": "SUP-002-audit-report.pdf",
        "title": "Golden Thread Textiles — On-Site Audit Report",
        "meta": {
            "Facility": "Zirabo Industrial Area, Savar, Dhaka, Bangladesh",
            "Audit type": "SA8000-aligned social compliance audit",
            "Audit dates": "2026-02-02 to 2026-02-04 (3 days)",
            "Auditor": "Meridian Assurance Partners (third-party)",
            "Overall rating": "Conditional — Medium Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This audit of Golden Thread Textiles' Savar facility identified several "
                    "non-conformances requiring corrective action. None were assessed as an "
                    "immediate threat to life, but the excessive-overtime and fire-alarm "
                    "findings below require verified remediation within the stated deadlines "
                    "or the facility's rating will be downgraded at follow-up.",
                ],
            ),
            (
                "Labor Practices",
                [
                    "Worker interviews (42 workers sampled across three shifts) and "
                    "timekeeping records for the peak production period (August-October "
                    "2025) showed average weekly hours of 68, exceeding the 60-hour legal "
                    "maximum including overtime. Base wages matched the legally mandated "
                    "minimum wage in all sampled records, but overtime premium pay for "
                    "temporary/contract workers was calculated at the standard hourly rate "
                    "rather than the required 1.5x premium in 11 of 30 sampled pay slips.",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Two emergency exits on the Building B sewing floor were found obstructed "
                    "by stacked fabric rolls at the start of the audit; both were cleared "
                    "before the auditors left the floor. Facility records show the fire alarm "
                    "and detection system was last tested 14 months ago, exceeding the "
                    "facility's own stated 12-month testing interval.",
                ],
            ),
            (
                "Grievance Mechanism",
                [
                    "A worker grievance hotline and suggestion-box system exists per facility "
                    "policy documents. However, of the 42 workers interviewed, only 9 were "
                    "aware the mechanism existed, and several expressed distrust that "
                    "complaints would be handled without retaliation.",
                ],
            ),
        ],
        "table": {
            "heading": "Corrective Action Log",
            "header": ["Finding", "Severity", "Due Date", "Status"],
            "rows": [
                ["Excessive weekly overtime (68 hrs vs 60 hr legal max)", "Major", "60 days", "Open"],
                ["Overtime premium miscalculated for temp workers", "Major", "30 days", "Open"],
                ["Fire alarm system testing overdue", "Major", "Immediate", "Open"],
                ["Low worker awareness of grievance mechanism", "Minor", "90 days", "Open"],
            ],
        },
        "conclusion": (
            "Recommendation: conditional pass. A follow-up audit is scheduled for 2026-05-04 "
            "(90 days) to verify closure of all open corrective actions. Certification will be "
            "suspended if the overtime and fire-alarm findings are not verifiably remediated."
        ),
    },
    {
        "supplier_id": "SUP-003",
        "document_id": "SUP-003-audit",
        "file": "SUP-003-audit-report.pdf",
        "title": "Cobalt Basin Mining Ltd — On-Site Audit Report",
        "meta": {
            "Facility": "Kolwezi processing facility and affiliated artisanal collection "
            "points, Democratic Republic of the Congo",
            "Audit type": "Unannounced audit — site visit, subcontractor review, "
            "community interviews",
            "Audit dates": "2026-04-07 to 2026-04-10 (4 days)",
            "Auditor": "Meridian Assurance Partners (third-party), with independent "
            "environmental lab (Corelab DRC)",
            "Overall rating": "Unsatisfactory — High Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This unannounced audit identified critical non-conformances in labor, "
                    "environmental, and chain-of-custody practices connected to Cobalt Basin "
                    "Mining Ltd's artisanal supply chain. Given the severity of the labor "
                    "findings, the auditor recommends immediate suspension of sourcing from "
                    "the implicated subcontractor pending independent investigation.",
                ],
            ),
            (
                "Labor Practices",
                [
                    "Auditors observed individuals who appeared to be between 14 and 16 years "
                    "old working at two artisanal mineral collection points that feed into "
                    "Cobalt Basin's supply chain via the subcontractor Kivu Mineral "
                    "Aggregators. Age-verification documentation requested from the "
                    "subcontractor for workers at these sites was incomplete for the majority "
                    "of the roughly 60 workers observed, and the documentation that was "
                    "provided contained internal inconsistencies (mismatched names and dates "
                    "of birth across different records for the same individual).",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Shallow hand-dug shafts at the collection points inspected had "
                    "inadequate or no shoring to prevent collapse. No records of personal "
                    "protective equipment distribution to artisanal workers at these sites "
                    "could be produced by the subcontractor.",
                ],
            ),
            (
                "Environmental",
                [
                    "Independent laboratory analysis of a tailings pond discharge sample "
                    "collected on 2026-04-08 found cobalt and copper concentrations exceeding "
                    "the facility's environmental permit limits (see lab results table below).",
                ],
            ),
            (
                "Chain of Custody",
                [
                    "Traceability documentation linking artisanal collection points to the "
                    "Kolwezi processing facility could not be fully verified for "
                    "approximately 18% of the lots sampled during the audit, meaning material "
                    "from unverified or non-audited collection points may be entering the "
                    "supply chain without detection.",
                ],
            ),
        ],
        "table": {
            "heading": "Environmental Lab Results — Tailings Pond Discharge (2026-04-08)",
            "header": ["Parameter", "Result", "Permit Limit", "Status"],
            "rows": [
                ["Cobalt (dissolved)", "3.8 mg/L", "1.0 mg/L", "Exceeds limit"],
                ["Copper (dissolved)", "2.1 mg/L", "1.5 mg/L", "Exceeds limit"],
                ["pH", "6.9", "6.0–9.0", "Within limit"],
            ],
        },
        "conclusion": (
            "Recommendation: certification is suspended effective immediately. Sourcing from "
            "Kivu Mineral Aggregators should be paused pending an independent investigation "
            "into the age-verification findings. A full re-audit is required before "
            "certification can be reinstated; no timeline is proposed until the labor "
            "investigation concludes."
        ),
    },
    {
        "supplier_id": "SUP-004",
        "document_id": "SUP-004-audit",
        "file": "SUP-004-audit-report.pdf",
        "title": "Rhine Valley Chemicals GmbH — On-Site Audit Report",
        "meta": {
            "Facility": "Ludwigshafen production site, Germany",
            "Audit type": "ISO 14001 environmental + REACH chemical compliance audit",
            "Audit dates": "2026-01-20 to 2026-01-21 (2 days)",
            "Auditor": "Meridian Assurance Partners (third-party)",
            "Overall rating": "Conditional — Medium-High Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This audit of Rhine Valley Chemicals' Ludwigshafen site found the "
                    "facility's core environmental management system to be well established, "
                    "but identified chemical labeling, engineering, and PPE-compliance gaps "
                    "that require corrective action before the next audit cycle.",
                ],
            ),
            (
                "Chemical Handling & Labeling",
                [
                    "Of 40 sampled chemical storage containers, 3 were found with safety data "
                    "sheet labels that did not match the current REACH registration for the "
                    "substance inside (two due to an unrecorded supplier reformulation, one "
                    "due to a transcription error during relabeling). No exposure incidents "
                    "were linked to the mislabeling, but the facility's relabeling "
                    "verification step failed to catch the discrepancy.",
                ],
            ),
            (
                "Environmental",
                [
                    "Facility self-reporting logs show one wastewater pH excursion event in "
                    "the preceding 6 months (2025-10-03, pH 5.4 against a permit floor of "
                    "6.0), attributed to a neutralization dosing pump fault. The facility "
                    "reported the excursion to the regulator within the required window and "
                    "replaced the pump the same day; no repeat excursions have occurred since.",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Respiratory protective equipment fit-testing was found overdue for 12% "
                    "of workers classified as at-risk for airborne exposure, against the "
                    "facility's own policy of annual fit-testing for this group. Spill "
                    "containment berms around Tank Farm B were measured and found undersized "
                    "for the worst-case single-tank failure volume specified in the facility's "
                    "own risk assessment — an engineering non-conformance rather than an "
                    "operational one.",
                ],
            ),
        ],
        "table": {
            "heading": "Corrective Action Log",
            "header": ["Finding", "Severity", "Due Date", "Status"],
            "rows": [
                ["Mislabeled chemical storage containers (3 of 40 sampled)", "Major", "30 days", "Open"],
                ["Respiratory PPE fit-testing overdue (12% of at-risk workers)", "Major", "45 days", "Open"],
                ["Tank Farm B containment berms undersized for worst case", "Major", "90 days", "Open"],
                ["Wastewater pH excursion, 2025-10-03", "Minor", "Closed", "Closed — pump replaced"],
            ],
        },
        "conclusion": (
            "Recommendation: conditional pass. Follow-up audit scheduled for 2026-04-20 "
            "(90 days), aligned to the longest-lead-time item (containment berm engineering "
            "work). Certification will be downgraded if the labeling and PPE findings are "
            "not closed within their stated deadlines."
        ),
    },
    {
        "supplier_id": "SUP-009",
        "document_id": "SUP-009-audit",
        "file": "SUP-009-audit-report.pdf",
        "title": "Andes Copper Corp — On-Site Audit Report",
        "meta": {
            "Facility": "Underground mine and processing complex, Antofagasta region, Chile",
            "Audit type": "ICMM-aligned safety & labor audit, with community relations review",
            "Audit dates": "2026-02-16 to 2026-02-19 (4 days)",
            "Auditor": "Meridian Assurance Partners (third-party)",
            "Overall rating": "Conditional — Medium Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This audit found Andes Copper Corp's underground operations to be "
                    "generally well managed, with strong community relations and tailings "
                    "management, but identified ventilation and fatigue-management gaps in "
                    "underground haulage and drilling operations that require follow-up.",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Facility incident records show two lost-time injuries in underground "
                    "haulage operations over the preceding 12 months, below the industry "
                    "benchmark but above the facility's own internal target of zero. "
                    "Mandatory rest periods under the site's fatigue-management policy were "
                    "not consistently logged for night-shift drill crews — records were "
                    "complete for day shift but incomplete for roughly a third of sampled "
                    "night-shift records. Ventilation monitoring in the Level 7 decline "
                    "showed diesel particulate matter readings intermittently above the "
                    "site's internal action threshold, though within regulatory limits.",
                ],
            ),
            (
                "Tailings & Environmental",
                [
                    "The site's tailings storage facility inspection was current and passed "
                    "with no findings, consistent with the facility's Global Industry "
                    "Standard on Tailings Management self-assessment.",
                ],
            ),
            (
                "Community Relations",
                [
                    "Interviews with representatives of two neighboring communities found the "
                    "grievance process to be functioning well, with reported complaints "
                    "(primarily dust and truck traffic) acknowledged and addressed within the "
                    "facility's stated response windows.",
                ],
            ),
            (
                "Training & Competency",
                [
                    "Underground haulage and drilling operators sampled (22 of an estimated "
                    "140 underground workforce) all held current statutory competency "
                    "certification. Refresher training on the site's fatigue-management "
                    "policy was last delivered site-wide in 2025-09, and the auditor "
                    "recommends this be repeated alongside the ventilation and logging "
                    "corrective actions below, since the incomplete night-shift logs suggest "
                    "the policy's rationale may not be fully understood by night-shift crews.",
                ],
            ),
            (
                "Documentation Review",
                [
                    "Equipment maintenance logs for underground ventilation fans were "
                    "reviewed for the preceding 12 months and found complete and current, "
                    "with no overdue maintenance intervals — the elevated particulate "
                    "readings noted above therefore appear to reflect an airflow design or "
                    "utilization issue in the Level 7 decline rather than an equipment fault.",
                ],
            ),
        ],
        "table": {
            "heading": "Corrective Action Log",
            "header": ["Finding", "Severity", "Due Date", "Status"],
            "rows": [
                ["Elevated diesel particulate readings, Level 7 decline", "Major", "60 days", "Open"],
                ["Incomplete fatigue-management logs, night-shift drill crews", "Minor", "45 days", "Open"],
            ],
        },
        "conclusion": (
            "Recommendation: conditional pass. Follow-up audit scheduled for 2026-04-20 "
            "(60 days) to verify ventilation remediation in the Level 7 decline. Tailings "
            "management and community relations practices are commended as strong."
        ),
    },
    {
        "supplier_id": "SUP-011",
        "document_id": "SUP-011-audit",
        "file": "SUP-011-audit-report.pdf",
        "title": "Nordic Timber Group — On-Site Audit Report",
        "meta": {
            "Facility": "Forest management units and sawmill, Värmland, Sweden",
            "Audit type": "FSC Chain of Custody + labor compliance audit",
            "Audit dates": "2026-03-02 to 2026-03-03 (2 days)",
            "Auditor": "Meridian Assurance Partners (third-party)",
            "Overall rating": "Satisfactory — Low Risk",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This audit found Nordic Timber Group to be in strong conformance with "
                    "FSC Chain of Custody and labor compliance requirements. Only one minor "
                    "administrative finding was raised, corrected the same day.",
                ],
            ),
            (
                "Chain of Custody",
                [
                    "All 25 sampled timber lots were correctly traced back to FSC-certified "
                    "forest management units, with harvest volumes for the audited period "
                    "within the approved annual allowable cut. Two purchase order records "
                    "were found missing their FSC claim codes; both were corrected by the "
                    "facility's procurement team before the audit concluded.",
                ],
            ),
            (
                "Health & Safety",
                [
                    "Facility incident records show zero lost-time injuries over the "
                    "preceding three years, notably better than the sector average for "
                    "forestry and sawmill operations. Chainsaw and forwarder operators "
                    "sampled all held current certification and PPE compliance was observed "
                    "at 100% across inspected harvest sites.",
                ],
            ),
            (
                "Environmental",
                [
                    "A GPS-based survey of a sample of harvest blocks confirmed biodiversity "
                    "buffer zones around waterways were maintained at or above the required "
                    "width in all cases reviewed.",
                ],
            ),
            (
                "Worker Interview Summary",
                [
                    "12 forestry and sawmill workers were interviewed across harvest and mill "
                    "operations. All reported being paid on schedule and in line with the "
                    "sector collective bargaining agreement. Seasonal workers interviewed "
                    "(3 of the 12) confirmed they received the same safety training and PPE "
                    "as permanent staff before starting harvest work.",
                ],
            ),
            (
                "Management Systems",
                [
                    "The facility's FSC Chain of Custody procedures were last internally "
                    "reviewed in 2025-11, with no gaps identified. Staff responsible for "
                    "claim-code entry have been retrained following the two missing-code "
                    "records noted above, and a secondary review step has been added to the "
                    "purchase order approval workflow to catch similar omissions going "
                    "forward.",
                ],
            ),
        ],
        "table": {
            "heading": "Corrective Action Log",
            "header": ["Finding", "Severity", "Due Date", "Status"],
            "rows": [
                ["Purchase orders missing FSC claim codes (2 records)", "Minor", "Immediate", "Closed — corrected on-site"],
            ],
        },
        "conclusion": (
            "Recommendation: continued certification with no follow-up audit required "
            "before the next scheduled annual audit (2027-03). Facility is commended for "
            "its safety record and chain-of-custody discipline."
        ),
    },
    {
        "supplier_id": "SUP-013",
        "document_id": "SUP-013-review",
        "file": "SUP-013-transparency-review.pdf",
        "title": "Volga Metals Trading — Supply Chain Transparency & Sanctions Exposure Review",
        "meta": {
            "Scope": "Corporate structure, beneficial ownership, banking relationships, "
            "certificates of origin (desk review — not a facility audit; Volga Metals "
            "Trading is a trading intermediary, not a manufacturer)",
            "Review type": "Enhanced due diligence desk review",
            "Review dates": "2026-01-28 to 2026-01-30",
            "Reviewer": "Meridian Assurance Partners, Trade Compliance Practice",
            "Overall rating": "Unsatisfactory — High Risk (pending disclosure)",
        },
        "sections": [
            (
                "Executive Summary",
                [
                    "This desk review examined Volga Metals Trading's corporate structure, "
                    "upstream supplier relationships, and banking arrangements for sanctions "
                    "and transparency red flags. No direct sanctions list match was found for "
                    "Volga Metals Trading or its disclosed ownership, but material gaps in "
                    "upstream ownership transparency and an undisclosed banking relationship "
                    "warrant enhanced due diligence before the relationship continues at its "
                    "current volume.",
                ],
            ),
            (
                "Beneficial Ownership",
                [
                    "Corporate registry records for one upstream supplier — a scrap metal "
                    "aggregator supplying approximately 15% of Volga Metals Trading's "
                    "sampled volume — show a multi-layer holding company structure "
                    "registered in a low-transparency jurisdiction, with the ultimate "
                    "beneficial owner not disclosed in any of the corporate filings "
                    "reviewed. Repeated requests to Volga Metals Trading for the aggregator's "
                    "beneficial ownership documentation had not been fulfilled as of the "
                    "review date.",
                ],
            ),
            (
                "Banking & Payment Routing",
                [
                    "Payment records for two transactions in the past 12 months were routed "
                    "through a bank not previously disclosed in Volga Metals Trading's "
                    "on-file banking relationships. Volga Metals Trading has not yet provided "
                    "an explanation for the change in routing.",
                ],
            ),
            (
                "Certificates of Origin",
                [
                    "Certificates of origin and contract documentation for the sampled "
                    "shipments not involving the flagged aggregator were complete, internally "
                    "consistent, and matched the declared countries of origin.",
                ],
            ),
        ],
        "table": {
            "heading": "Follow-Up Actions",
            "header": ["Action", "Severity", "Due Date", "Status"],
            "rows": [
                ["Obtain full beneficial ownership disclosure for flagged aggregator", "Critical", "30 days", "Open"],
                ["Clarify undisclosed banking relationship", "Major", "30 days", "Open"],
                ["Enhanced due diligence monitoring of transaction volume", "Major", "Ongoing", "Open"],
            ],
        },
        "conclusion": (
            "Recommendation: escalate to compliance/legal for review. Do not suspend the "
            "relationship on this review alone, since no direct sanctions match was found, "
            "but apply enhanced monitoring and withhold volume increases until beneficial "
            "ownership documentation for the flagged aggregator is provided."
        ),
    },
]


def _build_pdf(audit: dict[str, Any], output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story: list[Any] = [Paragraph(audit["title"], _styles["AuditTitle"]), Spacer(1, 0.15 * inch)]

    meta_rows = [[f"{key}:", value] for key, value in audit["meta"].items()]
    meta_table = Table(meta_rows, colWidths=[1.4 * inch, 5.1 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.2 * inch))

    for heading, paragraphs in audit["sections"]:
        story.append(Paragraph(heading, _styles["AuditHeading"]))
        for para in paragraphs:
            story.append(Paragraph(para, _styles["AuditBody"]))

    table_spec = audit["table"]
    story.append(Paragraph(table_spec["heading"], _styles["AuditHeading"]))
    data = [table_spec["header"], *table_spec["rows"]]
    findings_table = Table(data, repeatRows=1)
    findings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(findings_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Conclusion", _styles["AuditHeading"]))
    story.append(Paragraph(audit["conclusion"], _styles["AuditBody"]))

    doc.build(story)


def generate() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    for audit in AUDITS:
        output_path = RAW_DIR / audit["file"]
        _build_pdf(audit, output_path)
        manifest.append(
            {
                "file": audit["file"],
                "supplier_id": audit["supplier_id"],
                "document_id": audit["document_id"],
                "title": audit["title"],
            }
        )
        print(f"Wrote {output_path}")

    manifest_path = DOCUMENTS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    generate()
