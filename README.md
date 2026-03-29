# Course RAG Assistant

Option 1 submission for the Purple Merit Technologies AI/ML Engineer Intern assessment:
`Agentic RAG Challenge: Prerequisite & Course Planning Assistant (Catalog-Grounded)`.

## What this project does

- Answers prerequisite and catalog-policy questions with grounded citations.
- Produces a next-term course plan after collecting the required student inputs.
- Asks clarifying questions when planning inputs are missing.
- Abstains when the answer is not supported by the provided catalog.
- Includes a single-screen Streamlit chat UI for testing eligibility, policy, and planning flows.

## Project Structure

- `app/app.py`: main advisor logic and planning workflow
- `ui.py`: Streamlit chat UI
- `rag/retriever.py`: grounded retrieval and citation formatting
- `rag/eligibility_checker.py`: prerequisite decision engine
- `rag/course_search.py`: course matching
- `evaluation/eval_set.json`: 25-query evaluation set
- `evaluation/run_evaluation.py`: evaluation runner
- `evaluation/REPORT.md`: evaluation summary
- `evaluation/EXAMPLE_TRANSCRIPTS.md`: three example transcripts
- `data/processed/sources.json`: source URLs, access dates, and notes

## Setup

Recommended Python version: `3.11` or `3.12`.

This repo also contains a Python `3.14` fallback path for retrieval, but the LangChain/Chroma stack is more reliable on `3.11` or `3.12`.

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` with:

```env
OPENAI_API_KEY=your_key_here
```

## Running the app

### Streamlit UI

```powershell
.\.venv\Scripts\streamlit.exe run ui.py
```

Ask questions directly in the centered chat UI. The interface is optimized for catalog QA, prerequisite checks, policy questions, and planning prompts.

### CLI

```powershell
.\.venv\Scripts\python.exe app\app.py
```

## Building / Refreshing Data

If you need to rebuild the course artifacts:

```powershell
.\.venv\Scripts\python.exe rag\build_index.py
.\.venv\Scripts\python.exe rag\extract_courses.py
.\.venv\Scripts\python.exe rag\build_course_graph.py
```

## Evaluation

Run the 25-query evaluation set:

```powershell
.\.venv\Scripts\python.exe evaluation\run_evaluation.py
```

This generates:

- `evaluation/results.json`
- `evaluation/REPORT.md`
- `evaluation/EXAMPLE_TRANSCRIPTS.md`

## Sources

Primary source corpus:

- Cisco College 2025-2026 General Catalog
  URL: `Uploaded source document (local): data/raw_docs/cisco_catalog.pdf`
  Accessed: `2026-03-29`
  Note: course descriptions, transfer credit policy, financial-aid rules, program requirements, tuition, and academic policies.

Additional source metadata is stored in `data/processed/sources.json`.

## Assignment Mapping

- Grounded answers with citations: yes
- Prerequisite reasoning with decision and next step: yes
- Course-plan generation with clarifying questions: yes
- Safe abstention for unsupported questions: yes
- Evaluation set with 25 queries: yes
- Streamlit demo UI: yes

## Known Limits

- The corpus currently uses one primary published catalog PDF rather than multiple website pages.
- Course availability by semester is not guaranteed unless explicitly present in the retrieved catalog text.
- Planning recommendations are grounded in retrieved program-rule context plus extracted course data, but they should still be manually reviewed before real enrollment decisions.
- The automated evaluation still shows room for improvement on prerequisite accuracy, so manual spot-checking is recommended before submission.
