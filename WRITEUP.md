# Short Write-Up

## Chosen Catalog and Sources

This project is grounded in the Cisco College 2023-2024 General Catalog. The primary source URL is:
`https://www.cisco.edu/uploads/files/general/Official-Course-Catalog-Published-08.15.23-for-23-24_2023-08-21-144222_llgc.pdf`
Accessed on `2026-03-29`.

## Architecture Overview

The system combines a deterministic prerequisite checker with a grounded catalog retriever. Extracted course records are stored in `courses.json`, prerequisite edges are stored in `course_graph.json`, and broader policy or degree-rule questions are answered through retrieval over catalog chunks. The advisor layer routes each question to one of four flows: prerequisite eligibility, planning, policy/program reasoning, or course search. A Streamlit chat UI sits on top for interactive testing.

## Chunking / Retrieval Choices

The project keeps a Chroma-based retrieval path for supported Python environments, but adds a lexical PDF-chunk fallback for Python 3.14 compatibility. The chunking approach uses roughly `1000` characters with `200` overlap in the build pipeline, while the fallback retriever uses paragraph-like page sections and attaches chunk ids plus section headings. This tradeoff favors reliability and citation traceability over retrieval sophistication.

## Prompts / Roles

There is no multi-agent orchestration layer in this submission; instead, the advisor implements stage-like routing. The grounding prompt explicitly allows prerequisite, policy, and program-rule questions, requires abstention when evidence is missing, and enforces the assignment response structure. Planning uses structured profile collection before generating a next-term shortlist.

## Evaluation Summary, Failure Modes, and Next Steps

The repo includes a 25-query evaluation set covering prerequisite checks, multi-hop prerequisite chains, program/policy questions, and “not in docs” cases. The automated report measures citation coverage, prerequisite-decision correctness, and abstention accuracy. The main current failure modes are imperfect program-plan ranking and dependency sensitivity in the LangChain/Chroma stack on Python 3.14. The next improvement would be stronger program-specific planning using richer requirement extraction and a fuller source corpus with explicit program pages and policy pages stored as separate source documents.
