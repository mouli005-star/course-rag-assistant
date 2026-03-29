# Course RAG Assistant - Full Project Documentation

## Live Demo (Fast Testing)
Use this deployed Streamlit app for quick testing without running VS Code or terminal commands:

**Demo URL:** https://mouli005-star-course-rag-assistant-ui-zrphms.streamlit.app/

---

## 1. Project Summary

This project is an **Agentic RAG-based Academic Advisor** built for the Purple Merit Technologies AI/ML intern assessment.

It answers catalog-grounded student questions in four main categories:

1. **Prerequisite eligibility** (Can I take course X?)
2. **Next-term planning** (What should I take next?)
3. **Policy/program questions** (transfer credit, residency, SAP, etc.)
4. **Course search/discovery** (find courses by code/title/field)

All final responses are normalized into a required assignment format:

- `Answer / Plan`
- `Why (requirements/prereqs satisfied)`
- `Citations`
- `Clarifying questions (if needed)`
- `Assumptions / Not in catalog`

---

## 2. Source Corpus and Grounding

Primary source used by the system:

- **Cisco College 2025-2026 General Catalog PDF**
- URL: Uploaded source document (local): data/raw_docs/cisco_catalog.pdf
- Stored local filename: `cisco_catalog.pdf`
- Source metadata is recorded in `data/processed/sources.json`

The assistant is designed to avoid hallucinations by grounding claims in retrieved catalog content and abstaining when evidence is missing.

---

## 3. End-to-End Architecture

### 3.1 High-level flow

1. User sends a question through Streamlit chat or CLI.
2. `Advisor.handle()` detects intent and updates profile/completed-course memory.
3. The question is routed to one of these handlers:
   - eligibility flow
   - recommendation flow
   - policy flow
   - search flow
4. Response is formatted and verified to satisfy assignment structure.
5. Response is shown in UI and saved to conversation memory.

### 3.2 Retrieval strategy (hybrid/fallback)

Retrieval has layered fallbacks for reliability:

1. Simple vector index (`simple_embeddings.npy` + metadata)
2. Chroma similarity search (if environment supports it)
3. Lexical PDF fallback (token overlap scoring over extracted sections)

This keeps the app usable even when some vector dependencies are unavailable.

### 3.3 Prerequisite decision strategy

Eligibility is deterministic:

- Build prerequisite graph from extracted courses (`course_graph.json`)
- Recursively identify unmet prerequisites
- Return `Eligible` or `Not eligible` plus next step

This logic is independent of generative model output and improves consistency for prereq checks.

---

## 4. Core Functional Behaviors

### 4.1 Intent detection

`Advisor` class detects intent using keyword rules:

- policy keywords -> policy flow
- `can I take`, `eligible`, `prerequisite` -> eligibility flow
- `what can I take`, `recommend`, `plan` -> recommendation flow
- otherwise defaults to search flow

### 4.2 Eligibility flow

When user asks eligibility:

1. Match requested course from catalog extraction.
2. Run deterministic prerequisite checker.
3. Build evidence lines and citations from course records.
4. Return decision + reason + next step.

If no confident course match is found, it asks clarifying questions (code/title).

### 4.3 Recommendation flow

For planning questions:

1. Validate required profile fields (major, term).
2. Retrieve requirement context from catalog using RAG.
3. Score candidate courses based on:
   - prereq satisfaction
   - major text/code hints
   - relevance to requirement text
4. Respect planning constraints (`max_courses`, `max_credits`).
5. Return shortlist, total credits, assumptions, and citations.

### 4.4 Policy flow

Policy and program-rule questions go to grounded retrieval + LLM answer generation with strict prompt constraints.

If explicit support is missing, the system abstains instead of inventing policy details.

### 4.5 Search flow

Search behavior supports:

- field-based discovery (AI, data science, networking, etc.)
- keyword title matching
- lexical ranking
- semantic fallback via vectors

Generic broad questions are forwarded to grounded retrieval for natural catalog summaries.

---

## 5. Prompting and Output Controls

### 5.1 Extraction prompt

`COURSE_EXTRACTION_PROMPT` enforces JSON-only extraction for one course per chunk and prevents policy/program text from being misclassified as a course.

### 5.2 Grounding prompt

`GROUNDING_POLICY_PROMPT` allows course/program/policy answers **only from provided context** and requires explicit acknowledgment when information is not in materials.

### 5.3 Response verifier

`verify_response()` ensures required sections are present and normalizes citations, clarifying questions, and assumptions.

---

## 6. Streamlit UI Experience

The UI in `ui.py` provides:

- single-page chat with modern styled interface
- persistent chat sessions in `data/chat_sessions.json`
- section-aware rendering (Answer, Why, Citations, etc.)
- helper expanders for reasoning and assumptions
- fixed bottom chat input and New Chat control

It is optimized for quick conversational testing and demo use.

---

## 7. Data Pipeline and Build Steps

### 7.1 Ingestion and chunking

- Load PDFs from `data/raw_docs/`
- Split into chunks (size 1000, overlap 200)

### 7.2 Vector store/index build

- Build/persist Chroma vector DB in `data/vector_db/`
- Build simple numpy embedding index as fallback

### 7.3 Course extraction

- Iterate chunks and call LLM for structured course JSON
- Save deduplicated courses to `data/processed/courses.json`

### 7.4 Graph generation

- Build prerequisite adjacency map
- Save to `data/processed/course_graph.json`

---

## 8. Evaluation Framework

Evaluation uses 25 test cases from `evaluation/eval_set.json` across categories:

- `prereq_check`
- `prereq_chain`
- `program_requirement`
- `not_in_docs`

Metrics generated by `evaluation/run_evaluation.py`:

1. Citation coverage
2. Eligibility correctness
3. Abstention accuracy

Current report (`evaluation/REPORT.md`):

- Total queries: **25**
- Citation coverage: **100.0%**
- Eligibility correctness (prereq checks): **70.0%** (7/10)
- Abstention accuracy: **100.0%** (5/5)

Interpretation:

- Grounding/abstention are strong.
- Deterministic prereq logic still needs refinement for some edge cases in extracted prerequisite data quality.

---

## 9. Repository File-by-File Explanation

### 9.1 Root files

- `README.md` - main usage/readme and project framing.
- `WRITEUP.md` - short design and tradeoff summary.
- `config.py` - environment loading, API-key retrieval, Python compatibility warnings.
- `ui.py` - Streamlit frontend.
- `test_openai.py` - simple OpenAI connectivity test.
- `requirements.txt` - project dependencies.
- `.env` - local secrets/environment values (not for sharing).

### 9.2 App layer

- `app/__init__.py` - exposes `Advisor`.
- `app/app.py` - central orchestration (intent routing, memory, profile updates, response handlers).

### 9.3 RAG/data logic (`rag/`)

- `ingestion.py` - PDF loading.
- `chunking.py` - chunk split strategy.
- `vector_store.py` - Chroma store build/persist.
- `build_index.py` - end-to-end index build script.
- `simple_vector_index.py` - numpy embedding index build/search fallback.
- `retriever.py` - retrieval mode selection, grounded answer generation, abstention safeguards.
- `prompts.py` - extraction and grounding prompts.
- `extract_courses.py` - LLM-based structured course extraction.
- `build_course_graph.py` - prerequisite graph generation.
- `eligibility_checker.py` - deterministic prereq eligibility engine.
- `course_search.py` - field/keyword/lexical/semantic course matching.
- `output_formatter.py` - canonical section formatter.
- `verifier.py` - response structure/citation normalization.
- `source_catalog.py` - source metadata + citation formatting helpers.

### 9.4 Data files (`data/`)

- `data/raw_docs/cisco_catalog.pdf` - source catalog PDF.
- `data/processed/sources.json` - source metadata registry.
- `data/processed/courses.json` - extracted course objects.
- `data/processed/course_graph.json` - course -> prerequisites graph.
- `data/chat_memory.json` - short memory used by advisor.
- `data/chat_sessions.json` - UI chat history store.
- `data/vector_db/` - persisted Chroma + simple vector artifacts.

### 9.5 Evaluation (`evaluation/`)

- `eval_set.json` - 25 benchmark prompts and expectations.
- `run_evaluation.py` - evaluator and report generator.
- `results.json` - detailed run output.
- `REPORT.md` - summary metrics.
- `EXAMPLE_TRANSCRIPTS.md` - representative transcript samples.

---

## 10. Environment and Dependencies

Python recommendation from codebase:

- Preferred: **Python 3.11 or 3.12**
- Python 3.14+ may have compatibility issues in parts of LangChain stack, with fallbacks implemented.

Primary libraries:

- `openai`
- `python-dotenv`
- `langchain-openai`
- `langchain-community`
- `langchain-text-splitters`
- `langchain-chroma`
- `pypdf`
- `chromadb`
- `streamlit`

---

## 11. How to Run Locally (if needed)

### 11.1 Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
OPENAI_API_KEY=your_key_here
```

### 11.2 Start UI

```powershell
.\.venv\Scripts\streamlit.exe run ui.py
```

### 11.3 Optional data rebuild

```powershell
.\.venv\Scripts\python.exe rag\build_index.py
.\.venv\Scripts\python.exe rag\extract_courses.py
.\.venv\Scripts\python.exe rag\build_course_graph.py
```

### 11.4 Run evaluation

```powershell
.\.venv\Scripts\python.exe evaluation\run_evaluation.py
```

---

## 12. Known Limitations

1. Corpus currently centers on a single main catalog PDF.
2. Semester-specific offering details (days/times/instructor/seat counts) are often unavailable in catalog-only context.
3. Planning output quality depends on extracted prerequisite and requirement quality.
4. Prerequisite correctness is good but not perfect (70% in current automated prereq set).

---

## 13. Suggested Next Improvements

1. Add more source documents (program pages, policy pages, department pages) as separate indexed sources.
2. Improve prerequisite extraction quality and co-requisite parsing.
3. Add stronger planning ranker using explicit degree-audit rules.
4. Add confidence scoring and richer failure diagnostics in evaluation.
5. Add optional user profile form in UI for cleaner planning inputs.

---

## 14. Fast Share Version (for sending to others)

If you need a one-paragraph summary to paste in email/chat:

"I built a catalog-grounded Course RAG Assistant with a Streamlit chat UI that handles prerequisite eligibility checks, next-term planning, policy/program Q&A, and course discovery with citations from the Cisco College catalog PDF. The system combines deterministic prerequisite graph logic with retrieval-based grounded answering, includes abstention behavior for unsupported questions, and has a 25-case evaluation suite. Current metrics: 100% citation coverage, 100% abstention accuracy, and 70% eligibility correctness on prerequisite tests. Live demo: https://mouli005-star-course-rag-assistant-ui-zrphms.streamlit.app/"

---

Document prepared from the current repository implementation and generated artifacts.