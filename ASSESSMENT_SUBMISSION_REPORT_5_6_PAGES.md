# Agentic RAG Challenge Submission Report

## Prerequisite and Course Planning Assistant (Catalog-Grounded)

### Candidate Submission: Course RAG Assistant

## 1. Assessment Overview and Submission Scope

This submission presents an end-to-end Retrieval-Augmented Generation (RAG) assistant designed for student course planning inside an LMS-like workflow. The system is grounded in catalog documents and is built to answer prerequisite and program-policy questions with citations, generate next-term plans, ask clarifying questions when data is incomplete, and safely abstain when required information is not present in the provided source materials.

The implementation is built as a staged, agent-like architecture using LangChain-compatible retrieval components and deterministic rule-based modules where precision is critical (for example, prerequisite eligibility decisions). While it does not use CrewAI multi-agent runtime, it implements equivalent role separation in software stages (intake/profile normalization, retrieval, planning/reasoning, and response verification).

Live deployed demo for fast validation:

- Streamlit app: https://mouli005-star-course-rag-assistant-ui-zrphms.streamlit.app/

Repository includes:

- ingestion to indexing pipeline
- interactive app (Streamlit + CLI path)
- evaluation harness with 25-case test set
- generated reports and transcript examples

This report is intentionally aligned with every requirement listed in the assignment brief.

---

## 2. Scenario Fit and Objective Coverage

The assignment scenario describes an LMS assistant that helps students plan next-term courses under realistic ambiguity and policy constraints. This implementation directly targets that scenario and handles the difficult catalog patterns specified:

- prerequisite chains via recursive prerequisite graph traversal
- either/or and wording variability through retrieval-based evidence selection and grounding prompt constraints
- minimum-grade/co-requisite/policy responses only when explicitly present in retrieved text
- exceptions and policy edge cases with safe abstention when unsupported

Implemented objectives:

1. prerequisite questions answered with decision and citations
2. suggested term plan from completed-course context and student constraints
3. clarifying questions when major/term profile data is missing
4. explicit refusal to guess when information is absent in provided materials

---

## 3. Data Curation and Source Documentation

### 3.1 Chosen catalog and source basis

The assistant is built using the uploaded source catalog:

- Cisco College 2025-2026 General Catalog
- Source file used by pipeline: data/raw_docs/cisco_catalog.pdf
- Source metadata file: data/processed/sources.json
- Date accessed: 2026-03-29

Current source note in repository metadata indicates coverage of:

- course descriptions
- program requirements
- transfer credit
- satisfactory academic progress/policy-related sections
- tuition and academic-policy content

### 3.2 Dataset-size note against assignment minimum

Assignment minimum asks for:

- at least 20 course pages/descriptions
- at least 2 program requirement pages
- at least 1 policy page
- total 30,000+ words OR 25+ distinct documents/pages

Current implementation uses one canonical catalog PDF that contains multiple sections and pages. Functional coverage is achieved from that source. For strict interpretation of "distinct documents/pages," this approach is best described as a consolidated catalog corpus rather than many separate URLs. In follow-up improvement work, this can be expanded by indexing additional program and policy pages as separate source records.

### 3.3 Sources section format

Repository includes a sources registry with:

- source identifier
- source title
- source reference link/path
- date accessed
- source coverage note

This satisfies the documentation requirement for source traceability.

---

## 4. Architecture Overview

### 4.1 System components

The solution has three major layers:

1. Interface layer
- Streamlit chat interface for user interaction
- optional CLI-style interaction entry through advisor module

2. Advisor/orchestration layer
- intent detection
- profile extraction and update
- routing to eligibility, planning, policy, or search flow
- response memory and normalization

3. Knowledge and reasoning layer
- document retrieval (vector + fallback lexical)
- deterministic prerequisite engine
- course search and plan scoring
- format verifier ensuring assignment output structure

### 4.2 Agent-equivalent staged design

The staged behavior maps naturally to the assignment’s optional agentic role design:

- Intake role: profile extraction and missing-input detection
- Retriever role: context retrieval from catalog chunks
- Planner role: recommendation shortlist generation and justification
- Verifier role: response formatting and citation normalization

This stage separation delivers most practical benefits of an agentic pipeline while keeping runtime simple and deterministic where needed.

---

## 5. RAG Pipeline Implementation Details

### 5.1 Ingestion

Documents are loaded from the raw data folder and parsed page-wise from PDF. Each page is retained with metadata including source identity and page index.

### 5.2 Cleaning and chunking strategy

Chunking configuration in pipeline:

- chunk size: 1000 characters
- overlap: 200 characters

Rationale:

- large enough to preserve policy/prerequisite context
- overlap reduces boundary loss for requirement statements
- manageable token footprint for retrieval and prompt assembly

For robust fallback retrieval, paragraph-like page sections are also represented and tagged with chunk id and section heading.

### 5.3 Embeddings model

Embedding model used:

- text-embedding-3-small

This is used for both Chroma-based retrieval and the simple local vector-index fallback.

### 5.4 Vector store

Primary vector store:

- Chroma persistent store in data/vector_db

Fallback index:

- numpy embedding matrix + metadata JSON (simple index)

This dual strategy improves compatibility and availability across environments.

### 5.5 Retriever behavior and configuration

The retriever attempts in order:

1. simple vector index
2. Chroma similarity retrieval
3. lexical fallback search over extracted sections

Default top-k retrieval is configured at k=4 in core retrieval path.

### 5.6 Prompt constraints for grounding and safe behavior

Grounding prompt enforces:

- use only supplied context
- do not invent requirements or policies
- explicit "not available in provided materials" behavior
- structured output with mandatory sections

Extraction prompt enforces JSON-only, one-course-per-response behavior for course extraction quality.

---

## 6. Functional Requirement Mapping

### 6.1 Grounded answers with citations (mandatory)

Implemented behavior:

- responses include citations for factual claims
- citation formatting includes source identifier and page context
- verifier normalizes citations and ensures section structure

Safety behavior:

- if no evidence can be cited, response abstains rather than asserting unsupported facts

### 6.2 Prerequisite reasoning (mandatory)

Supported question styles include:

- Can I take course X given completed courses?
- What is required before course X?

Reasoning output includes:

- Decision: Eligible / Not eligible
- Evidence: prerequisite checks and citations
- Next step: what to take/do before enrollment

Implementation detail:

- deterministic prerequisite graph traversal avoids LLM-only eligibility logic

### 6.3 Course plan generation (mandatory)

Given profile and constraints, planner returns:

- suggested next-term course list
- credit-aware selection under max courses/credits
- justification per selected course
- assumptions/risks section

Current planner uses:

- prereq satisfaction filter
- major field hints + code-prefix alignment
- relevance to retrieved requirement context

### 6.4 Clarifying questions (mandatory)

When essential planning inputs are absent, assistant asks clarifying questions before producing a plan. Typical required fields include:

- major/program
- target term
- optional constraints such as max credits/courses
- transfer-credit context

### 6.5 Safe abstention (mandatory)

For out-of-scope or unsupported details (example: semester seat availability, instructor assignment, real-time schedule specifics), assistant explicitly states the information is not available in provided materials and suggests next checks (advisor/department/schedule pages).

---

## 7. Output Format Compliance

Every final response is normalized to this mandatory structure:

- Answer / Plan:
- Why (requirements/prereqs satisfied):
- Citations:
- Clarifying questions (if needed):
- Assumptions / Not in catalog:

A verifier module checks and normalizes the output even if upstream generation deviates.

---

## 8. Evaluation Design and Results

### 8.1 Test set coverage (25 queries)

Evaluation set contains required categories:

1. 10 prerequisite checks (eligible/not eligible)
2. 5 prerequisite-chain style checks
3. 5 program/policy requirement questions
4. 5 not-in-docs trick questions

### 8.2 Reported metrics

Generated report metrics currently show:

- Citation coverage rate: 100.0%
- Eligibility correctness on prerequisite checks: 70.0% (7/10)
- Abstention accuracy on not-in-docs questions: 100.0% (5/5)

### 8.3 Rubric interpretation

- Citation coverage: response contains grounded citation section
- Eligibility correctness: decision label matches expected outcome
- Abstention accuracy: system correctly refuses unsupported claims

### 8.4 Example transcripts

Repository includes transcript examples for:

1. correct eligibility decision with citations
2. planning output with justification and citations
3. correct abstention with guidance

---

## 9. Key Failure Modes and Current Limitations

1. Prerequisite accuracy is not yet perfect
- Some prerequisite outcomes depend on extraction quality and phrasing consistency in source text

2. Catalog-source breadth
- Current corpus is centered on one uploaded catalog PDF rather than many independently indexed web pages/documents

3. Offering/schedule limitations
- Catalog-grounded system cannot reliably answer real-time availability and instructor-specific operational questions unless explicitly documented in indexed sources

4. Ranking quality for plan generation
- Planner ranking is practical but heuristic; richer degree-audit semantics would improve prioritization

---

## 10. Improvements Planned (Next Iteration)

1. Expand source corpus
- Add separate program pages and policy pages as distinct source entries with explicit URLs where available

2. Improve prerequisite extraction and parsing
- Better handling for co-requisites, minimum grades, and either/or expressions

3. Strengthen planning engine
- Introduce requirement-graph or rule engine for audit-grade plan validation

4. Add confidence and diagnostics
- Report confidence bands and unsupported-claim checks in evaluation outputs

5. UX enhancements
- Dedicated profile intake form for cleaner planning interactions

---

## 11. Reproducibility and Run Instructions

### 11.1 Environment setup

- Create virtual environment
- Install dependencies from requirements file
- set OPENAI_API_KEY in .env

### 11.2 Build/rebuild pipeline

- run index build
- run course extraction
- run prerequisite graph build

### 11.3 Run interaction app

- run Streamlit UI locally
- or use deployed Streamlit URL for quick testing

### 11.4 Run evaluation

- execute evaluation script to regenerate results and report

Repository already contains generated evaluation outputs and report files.

---

## 12. Deliverables Checklist Against Assignment

1. Implementation (GitHub): completed
- end-to-end pipeline scripts present
- interactive app present
- evaluation runner and outputs present

2. Short write-up: completed in repository
- source description
- architecture summary
- retrieval/chunking choices
- prompt/role summary
- evaluation and improvements

3. Optional demo: completed
- deployed Streamlit app URL available

---

## 13. Submission-Ready Notes

For final external submission package, include:

- GitHub repository link
- this PDF-converted report (5-6 pages)
- the one-page short write-up
- Streamlit demo link

When converting this report to PDF, keep section headings and lists intact for readability and rubric mapping.

---

## Appendix A: Clear Requirement-to-Implementation Matrix

- Grounded citations: implemented in retrieval + formatter + verifier
- Prerequisite decisions: deterministic graph-based checker
- Plan generation: profile-aware scoring + constraints
- Clarifying questions: triggered on missing major/term and other planning context
- Safe abstention: explicit fallback messaging when unsupported by retrieved context
- Structured output: enforced by output formatter and verifier modules
- Evaluation with 25 queries: implemented and reported

---

## Appendix B: Fast Demo Script for Reviewer

1. Open deployed app URL.
2. Ask eligibility question: "Can I take Programming Fundamentals II if I completed COSC1336?"
3. Ask planning question with missing info: "Recommend next term courses."
4. Provide major and term, then ask planning again.
5. Ask trick question: "How many seats are left this semester?"

Expected behavior:

- eligibility decision with citations
- clarifying questions before full planning output
- plan with assumptions and citations
- abstention on unavailable operational info

End of report.