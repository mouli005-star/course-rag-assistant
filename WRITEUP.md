# Agentic RAG Challenge - Short Write-Up (Assessment 1)

## Live Demo
https://mouli005-star-course-rag-assistant-ui-zrphms.streamlit.app/

## 1) Catalog and Sources
Institution/catalog used: Cisco College 2025-2026 General Catalog.

Sources documentation is maintained in `data/processed/sources.json` with:
- source reference
- date accessed
- coverage note

Current source record:
- URL/reference: Uploaded source document (local): data/raw_docs/cisco_catalog.pdf
- Date accessed: 2026-03-29
- Covers course descriptions, prerequisites, program requirements, and policy sections.

## 2) Architecture Overview (LangChain-equivalent staged design)
The system is implemented as modular stages (equivalent to router + retrieval + verifier chains):
- Intake/Profile stage: extracts/updates student context (completed courses, major, term, limits).
- Retriever stage: fetches grounded catalog evidence.
- Reasoning/Planner stage: answers prerequisite questions and builds next-term suggestions.
- Verifier stage: normalizes output into the required assignment structure and guards against unsupported responses.

This design provides agent-like separation without requiring a full multi-agent runtime.

## 3) RAG Pipeline and Tradeoffs
- Ingestion: PDF catalog parsing from `data/raw_docs`.
- Chunking: recursive chunking with chunk_size=1000 and chunk_overlap=200.
- Embeddings: OpenAI `text-embedding-3-small`.
- Vector store: Chroma persistent store (`data/vector_db`) plus a simple embedding fallback index.
- Retrieval config: top-k retrieval (default k=4), with layered fallback:
	1. simple vector index
	2. Chroma similarity search
	3. lexical fallback over extracted text

Tradeoff: fallback retrieval improves reliability across environments, but lexical fallback can be less precise than vector similarity.

## 4) Prompts and Roles
- Grounding prompt enforces: use only provided context, do not invent missing policy/prereq facts, and return structured sections.
- Extraction prompt enforces JSON-only course extraction for cleaner downstream prerequisite graphing.
- Router/handler logic supports required behaviors:
	- prerequisite eligibility responses
	- course planning responses
	- clarifying questions when key profile data is missing
	- safe abstention when information is not in provided materials

## 5) Output Format Alignment
Responses are standardized to:
- Answer / Plan
- Why (requirements/prereqs satisfied)
- Citations
- Clarifying questions (if needed)
- Assumptions / Not in catalog

## 6) Evaluation Summary
Evaluation set contains 25 queries with required distribution:
- 10 prerequisite checks
- 5 prerequisite chain questions
- 5 program requirement questions
- 5 not-in-docs/trick questions

Current reported results:
- Citation coverage rate: 100.0%
- Eligibility correctness (prereq checks): 70.0% (7/10)
- Abstention accuracy (not-in-docs): 100.0% (5/5)

## 7) Key Failure Modes and Next Improvements
Observed gaps and improvements:
- Improve prerequisite correctness on edge cases (course extraction/prereq normalization quality).
- Strengthen citation strictness to include URL + section/chunk references consistently.
- Expand clarifying gates for planning (catalog year, grades, transfer-credit detail checks where applicable).

This implementation is end-to-end runnable (index build, chat interaction, and evaluation) and aligned to the assignment goals for grounded prerequisite and course-planning assistance.
