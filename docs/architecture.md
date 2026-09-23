# Architecture

## 1. Problem statement

Global companies source components, materials, and finished goods from hundreds of suppliers
spread across many countries, each with different labor laws, environmental standards, and
sanctions exposure. A single supplier can carry risk across several unrelated dimensions at
once — an expired social-compliance certificate, an unresolved child-labor allegation, a
sanctioned parent company, a poor ESG score — and that risk changes over time as new incidents,
certifications, and sanctions listings appear.

Today this kind of due-diligence review is done manually: a procurement or compliance analyst
opens several disconnected systems (certification registries, incident/NGO reports, sanctions
lists, sustainability disclosures, regulatory text), cross-references them by hand, and writes
up a risk memo. This is slow, inconsistent between analysts, and easy to get wrong when signals
are spread across sources that don't talk to each other — e.g. a valid certificate can mask an
active, unrelated forced-labor investigation, or a sanctions hit can be a false positive on a
similarly-named company.

**SupplyGuard AI automates this investigation.** Given a supplier identifier, it runs a
multi-agent LangGraph workflow that independently investigates compliance, risk, and
sustainability dimensions in parallel, merges the findings into a single risk assessment, and
either produces a final report directly or escalates to a human reviewer when the risk is high
enough that an automated sign-off isn't appropriate.

This project exists as a learning vehicle for building production-shaped agentic systems
(supervisor/router orchestration, parallel tool-calling sub-agents, typed state graphs,
human-in-the-loop interrupts, evaluation harnesses) around a domain — supply chain risk — that
is realistic enough to need all of them, without requiring live third-party data access.

## 2. Domain primer — for readers new to supply chain terms

Skip this section if you already work in procurement, compliance, or trade — it's here so a
reader unfamiliar with the domain can follow the rest of this document.

When a large company (a clothing retailer, an electronics brand) buys goods or materials from
another company, that other company is a **supplier**. The retailer doesn't make the fabric or
the microchips itself — it buys them from suppliers, who may buy raw materials from *their* own
suppliers, and so on down a chain — hence "supply chain."

The problem this project addresses: a supplier can look fine on paper (good prices, on-time
shipping) while doing something that exposes the buyer to legal, financial, or reputational
risk — forced labor, illegal dumping, or hidden ownership by a sanctioned individual. Large
buyers are legally and ethically responsible for knowing this about who they source from.
Checking up on a supplier this way is called **due diligence**, and each data file below
represents one channel of information a real due-diligence team would check:

- **Suppliers** — the phonebook. Who the company is, where, what they make, how big they are.
  Not risky by itself; it's the record everything else attaches to.
- **Certifications** — proof a supplier follows a standard. Independent auditors inspect a
  factory and award a certification (e.g. "no forced labor" — SA8000, "manages chemical waste
  properly" — ISO 14001, "timber is from a responsibly managed forest" — FSC), valid until an
  expiry date, like a food-safety inspection sticker. An expired one means nobody has
  independently re-checked recently.
- **Incidents** — specific bad things that were reported: a news investigation, an NGO report,
  a labor board complaint, a failed safety inspection. Unlike a certification (proactive: "we
  checked, it's fine"), an incident is reactive — something went wrong and someone documented
  it, and it may still be unresolved.
- **Sanctions** — government blacklists (US OFAC, EU, UK, UN) of companies and individuals it is
  illegal to do business with, usually over war crimes, weapons trafficking, or international
  sanctions. If a supplier — or its owner — is listed, dealing with them can be a crime for the
  buyer too, not just the supplier. A major real-world pitfall: names collide. A sanctioned
  company can share a near-identical name with an innocent one, so a real hit has to be
  confirmed by registration, address, and ownership — not by name alone.
- **Sustainability data** — a supplier's actual reported environmental/social numbers: carbon
  emissions, share of renewable energy, water use, waste recycled, and an overall **ESG score**
  (Environmental, Social, Governance — a widely used 0–100 reputation figure). This is what a
  supplier's marketing claims should be checked against.
- **Regulations** — the actual laws that make this due diligence mandatory rather than optional,
  e.g. the US **UFLPA** (bans importing goods potentially made with forced labor from a specific
  region), the US **Conflict Minerals Rule** (requires disclosure if minerals originate from
  conflict zones in Central Africa), the **EU Deforestation Regulation**, and the UK **Modern
  Slavery Act**. This file isn't tied to a specific supplier — the system has to reason "this
  supplier mines cobalt in the Congo, so the Conflict Minerals Rule applies to them," the way a
  compliance officer would.
- **Evaluation cases** — not a real-world business document at all; it's a testing tool. For
  each supplier it states the conclusion a correct system should reach (e.g. "this supplier
  should be rated `critical` risk and require human review") so that once the agents exist, we
  can grade their output against it — an answer key, not a data source.

In short: suppliers = *who*, certifications = *what they've proven*, incidents = *what went
wrong*, sanctions = *who's illegal to deal with*, sustainability = *their footprint*,
regulations = *the laws that make this matter*, evaluation cases = *how we grade whether the
system got it right*.

## 3. What documents/data we're working with

All data lives in [`data/`](../data/) as JSON files that stand in for systems a real deployment
would integrate with over an API. They are hand-authored **synthetic** records (no real
companies, people, or events) built to be internally consistent — the same 14 fictional
suppliers recur across every file so the agents have to cross-reference records, not just read
one table.

| File | Represents (in a real deployment) | Keyed by |
|---|---|---|
| `suppliers.json` | The supplier master record / vendor master data system | `id` (`SUP-xxx`) |
| `certifications.json` | A certification/audit registry (ISO, SA8000, SMETA, RBA, FSC, etc.) | `supplier_id` |
| `incidents.json` | NGO reports, news investigations, audit findings, labor board filings | `supplier_id` |
| `sanctions.json` | Sanctions list screening output (OFAC SDN, EU, UK, UN lists) | `match_supplier_id` (nullable — many rows are non-matches or false positives, by design) |
| `sustainability.json` | ESG / sustainability disclosure data (emissions, water, waste, ESG score) | `supplier_id` |
| `regulations.json` | Reference data: regulatory text summaries (UFLPA, EU CSDDD, EUDR, REACH, RoHS, etc.) | not supplier-keyed — matched by industry/jurisdiction at query time |
| `evaluation_cases.json` | Ground truth for the evaluation harness: expected risk level, expected routing decision, expected flags per supplier | `supplier_id` |
| `documents/raw/*.pdf` + `documents/manifest.json` | Unstructured on-site audit reports / desk reviews — the RAG Agent's corpus, ingested into Weaviate (see §6) | `supplier_id` (in the manifest) |

Design choices worth knowing before writing tools against this data:

- **Sanctions data intentionally contains noise.** `SAN-004` is a name collision with `SUP-002`
  that is *not* a real match (`match_supplier_id: null`, `match_confidence: "low"`), and `SAN-005`/
  `SAN-006` are unrelated entities. A tool that treats every fuzzy name match as a hit will fail
  the compliance agent's evaluation cases.
- **One supplier (`SUP-012`) has zero certification records.** Absence of data is itself a
  compliance finding, not something to silently treat as "no issues."
- **Incident severity and status are independent.** A `critical` severity incident can be
  `resolved` (e.g. `INC-005`, a fire with verified corrective action); an open, lower-severity
  incident (e.g. `INC-002`, an open wage complaint) can still be relevant. Risk scoring should
  weigh both fields, not severity alone.
- **`regulations.json` has no supplier foreign key.** Agents are expected to match a supplier's
  `industry` and the countries involved in its incidents against a regulation's
  `applicable_industries` / `jurisdiction`, the same reasoning step a human analyst does when
  deciding "does UFLPA apply here?"
- `evaluation_cases.json` is the answer key for [docs/evaluation.md](evaluation.md) — every
  case names the specific fields in the other six files that justify its expected outcome, so a
  disagreement between a case and the agents' output should be traceable to one of those fields.

## 4. Goal / task definition

**Input:** a supplier `id` (optionally: a free-text reason for the investigation, e.g. "renewal
due diligence" or "flagged by news alert").

**Output:** a structured investigation report containing:

1. A per-dimension summary from the Compliance, Risk, Sustainability, and RAG agents (what each
   found, and which source records support it).
2. A single merged risk assessment (risk level + the specific flags that drove it) produced by
   the Risk Analyst node.
3. A routing decision: `final_report` for normal risk, or `human_review` for high/critical risk
   — with the criteria for that decision made explicit and auditable, not a black box.
4. If routed to human review: a summary of exactly what a human needs to confirm or overrule
   before the report is finalized.

**Non-goals (out of scope for this project):**

- Live integration with real sanctions/certification/news providers — the JSON fixtures are the
  system of record for this project.
- Making the final accept/reject sourcing decision — SupplyGuard produces a risk assessment and
  routes it; it does not autonomously approve or terminate a supplier relationship.
- A production-grade UI — this is a backend/agent-architecture project (see
  [README.md](../README.md)).

**Definition of done for the workflow:** every case in `evaluation_cases.json` runs through the
LangGraph workflow end-to-end and produces the `expected_risk_level` and `expected_route` for
that case, with the `expected_flags` traceable to specific records in the underlying data files.
That evaluation loop (implemented in `src/supplyguard/evaluation/`) is the project's primary
correctness signal, in place of manual QA against a live system.

## 5. High-level flow

```
User -> FastAPI -> LangGraph (Investigation State)
                        -> Supervisor
                            -> Compliance Agent    -> certification + sanctions tools
                            -> Risk Agent           -> incident + sanctions tools
                            -> Sustainability Agent -> sustainability + regulation tools
                            -> RAG Agent            -> document search tool -> Weaviate
                        -> Risk Analyst (merges findings into one risk assessment)
                            -> Normal    -> Final Report
                            -> High Risk -> Human Review -> Final Report
```

Supervisor and routing design decisions are recorded as they're made in [docs/adr/](adr/); the
per-agent responsibilities and prompt/tool contracts are detailed in
[docs/agent-design.md](agent-design.md) and [docs/tool-design.md](tool-design.md) as those are
filled in.

## 6. Planned extensions

This section used to defer two capabilities past the core 25-milestone roadmap. One (RAG agent)
has since been built; the other (text-to-SQL) is still intentionally deferred, so it doesn't
get lost.

**RAG agent (built).** Retrieval-augmented generation over unstructured supplier documents,
resolving the open question this section used to pose ("what's the corpus?"): on-site audit
reports and transparency/sanctions-exposure desk reviews, one PDF per supplier, in
`data/documents/raw/` (synthetic, generated by `scripts/generate_synthetic_pdfs.py`; see the
data table in §3). Pipeline: `pdfplumber` (layout/table-aware parsing) -> per-page
`NLTKTextSplitter` (sentence-boundary) chunking, falling back to
`RecursiveCharacterTextSplitter` for oversized sentence-less pieces (e.g. tables) -> `sentence-transformers`
(`BAAI/bge-large-en-v1.5`) embeddings -> Weaviate (self-provided vectors, no built-in
vectorizer module), queried via hybrid search (BM25 keyword matching fused with vector
similarity, alpha=0.7) so exact terms (regulation names, subcontractor names, certification
codes) aren't lost to a purely semantic match. Wired into the graph as a fourth parallel
specialist, `rag_agent`
(`src/supplyguard/agents/rag_agent.py`), structurally identical to the other three: one tool
(`search_documents`), the same tool-calling-loop -> structured-output -> `ground_findings`
pattern, and its findings feed into `risk_analyst` the same way. Grounding for this agent's
`Evidence.source_type="document"` resolves a cited `chunk_id` against Weaviate
(`agents/grounding.py`) instead of Postgres/JSON, the one place this agent's evidence
verification differs from the other three's.

**Text-to-SQL tool.** A `fetch_schema()` tool plus a general query-execution tool, letting an
agent answer questions the fixed toolset in `src/supplyguard/tools/` didn't anticipate. This is
a materially different trust model from the rest of the tool layer — every existing tool can
only ever run one hard-coded, narrow query, which is what keeps compliance/risk findings
auditable and evidence-backed. A free-form SQL tool must not weaken that guarantee for the rest
of the system. When built, it needs:

- `fetch_schema()` reflecting the schema from SQLAlchemy's own metadata (`Base.metadata.tables`)
  or Postgres's `information_schema` — never hand-maintained, so it can't drift from the real
  tables.
- The query tool executing against a **separate, read-only Postgres role** (`GRANT SELECT` only
  — no `INSERT`/`UPDATE`/`DELETE`/`DROP`), so a malicious or buggy LLM-generated query is
  structurally incapable of mutating data.
- A query validator rejecting anything that isn't a single `SELECT`, as a second layer on top of
  the role restriction.
- A row limit and statement timeout, so a runaway query can't hang or dump the full dataset.
- Kept as an *additional* tool for open-ended questions, not a replacement for the narrow tools.

**RAG agent.** Retrieval-augmented generation over some text corpus. Open question not yet
decided: what the corpus actually is in this domain — candidates include the full text of the
regulations in `regulations.json` (currently only summarized), or a larger set of incident/news
reports beyond the structured fields in `incidents.json`. This needs a concrete decision before
implementation, not just a vector store bolted onto existing structured data.
