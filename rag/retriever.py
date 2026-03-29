from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import sys

from openai import OpenAI
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import get_openai_api_key, warn_python_compatibility
from rag.course_search import search_course
from rag.output_formatter import format_assignment_response
from rag.prompts import GROUNDING_POLICY_PROMPT
from rag.simple_vector_index import search_simple_vector_index, simple_index_exists
from rag.source_catalog import build_source_citation, derive_section_heading
from rag.verifier import verify_response


RAW_DOCS_DIR = BASE_DIR / "data" / "raw_docs"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _lexical_score(query: str, text: str) -> int:
    query_tokens = set(_tokenize(query))
    text_tokens = set(_tokenize(text))

    if not query_tokens or not text_tokens:
        return 0

    overlap = len(query_tokens & text_tokens)
    phrase_bonus = 3 if query.lower().strip() and query.lower().strip() in text.lower() else 0
    return overlap + phrase_bonus


@lru_cache(maxsize=1)
def load_fallback_chunks():
    chunks = []
    chunk_counter = 0

    for pdf_path in sorted(RAW_DOCS_DIR.glob("*.pdf")):
        reader = PdfReader(str(pdf_path))

        for page_index, page in enumerate(reader.pages):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue

            raw_sections = [section.strip() for section in page_text.split("\n\n") if section.strip()]
            sections = raw_sections or [page_text]

            for section_index, section_text in enumerate(sections, start=1):
                chunk_counter += 1
                chunks.append(
                    {
                        "text": section_text,
                        "metadata": {
                            "source": pdf_path.name,
                            "page": page_index,
                            "chunk_id": f"{pdf_path.stem}:p{page_index + 1}:c{section_index}",
                            "section_heading": derive_section_heading(section_text, fallback=f"Page {page_index + 1}"),
                        },
                    }
                )

    return chunks


def _try_vector_search(query: str, k: int):
    try:
        if simple_index_exists():
            results = search_simple_vector_index(query, k=k)
            if results:
                return results, "simple-vector"
    except Exception:
        pass

    if sys.version_info >= (3, 14):
        return [], "vector-unavailable"

    try:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        warn_python_compatibility()
        api_key = get_openai_api_key(required=True)

        embeddings = OpenAIEmbeddings(
            api_key=api_key,
            model="text-embedding-3-small",
        )

        db = Chroma(
            persist_directory=str(BASE_DIR / "data" / "vector_db"),
            embedding_function=embeddings,
        )

        results = db.similarity_search(query, k=k)
        normalized = []

        for result in results:
            normalized.append(
                {
                    "text": result.page_content,
                    "metadata": {
                        "source": result.metadata.get("source", "unknown"),
                        "page": result.metadata.get("page"),
                        "chunk_id": result.metadata.get("chunk_id", f"vector:{len(normalized) + 1}"),
                        "section_heading": result.metadata.get("section_heading") or derive_section_heading(result.page_content),
                    },
                }
            )

        return normalized, "chroma"
    except Exception:
        return [], "vector-unavailable"


def _fallback_search(query: str, k: int):
    scored = []

    for chunk in load_fallback_chunks():
        score = _lexical_score(query, chunk["text"])
        if score <= 0:
            continue
        scored.append((score, chunk))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1]["metadata"].get("source", ""),
            item[1]["metadata"].get("page", 0),
        )
    )
    return [item[1] for item in scored[:k]]


def retrieve_context(query: str, k: int = 4):
    vector_results, vector_mode = _try_vector_search(query, k)
    if vector_results:
        return vector_results, vector_mode
    return _fallback_search(query, k), "lexical-fallback"


def _format_citation(metadata):
    page = metadata.get("page")
    page_number = page + 1 if isinstance(page, int) else "unknown"
    return build_source_citation(
        metadata.get("source", "unknown"),
        f"page {page_number}",
        None,
    )


def _default_clarifying_questions(query: str):
    lower_query = query.lower()
    questions = []

    if any(term in lower_query for term in ["plan", "take next", "recommend"]):
        if "major" not in lower_query and "program" not in lower_query:
            questions.append("What is your target major or program?")
        if all(term not in lower_query for term in ["fall", "spring", "summer", "winter", "term"]):
            questions.append("Which term are you planning for?")
        if "credit" not in lower_query and "max" not in lower_query:
            questions.append("What is your maximum course or credit load for the term?")

    return questions[:5]


def _looks_like_simple_catalog_question(query: str) -> bool:
    lowered = query.lower()
    if any(term in lowered for term in ["policy", "prereq", "prerequisite", "can i take", "eligible", "recommend", "plan"]):
        return False

    simple_starters = [
        "what is",
        "what are",
        "does",
        "do",
        "which",
        "when",
        "where",
        "how many",
        "tell me about",
        "show me",
        "list",
    ]
    return any(lowered.startswith(starter) for starter in simple_starters)


def _requires_explicit_prereq_support(query: str) -> bool:
    lower_query = query.lower()
    return any(term in lower_query for term in ["prereq", "pre-req", "can i take", "eligible", "co-requisite", "corequisite"])


def _looks_course_specific(query: str) -> bool:
    lower_query = query.lower()
    if re.search(r"\b[a-z]{3,4}\s*-?\s*\d{4}\b", lower_query):
        return True

    markers = [
        "prereq",
        "prerequisite",
        "can i take",
        "eligible",
        "course code",
        "course title",
        "for course",
        "about course",
    ]
    return any(marker in lower_query for marker in markers)


def _has_explicit_prereq_language(chunks) -> bool:
    markers = [
        "prereq",
        "pre-req",
        "prerequisite",
        "co-requisite",
        "corequisite",
        "permission of instructor",
        "consent of instructor",
    ]
    for chunk in chunks:
        text = chunk["text"].lower()
        if any(marker in text for marker in markers):
            return True
    return False


def _generate_grounded_answer(query: str, chunks):
    context_blocks = []
    citations = []

    for chunk in chunks:
        metadata = chunk["metadata"]
        citations.append(_format_citation(metadata))
        context_blocks.append(f"[{metadata['chunk_id']}]\n{chunk['text']}")

    api_key = get_openai_api_key(required=True)
    client = OpenAI(api_key=api_key)

    prompt = f"""
{GROUNDING_POLICY_PROMPT}

If the answer is not clearly supported, say that the information is not available in the provided catalog.
Return exactly these four labeled sections:

Answer / Plan:
Why (requirements/prereqs satisfied):
Clarifying questions (if needed):
Assumptions / Not in catalog:

Rules:
- Do not invent policies, prerequisites, offerings, or exceptions.
- Keep the answer concise, natural, and grounded in the provided context.
- For simple factual questions, write the answer in normal natural language, not in robotic bullet fragments.
- Keep the "Why" section short and plain.
- Only add clarifying questions if they are actually needed to answer.
- Only add assumptions if something is genuinely missing from the provided materials.
- If no clarifying questions are needed, write "None."
- If no assumptions are needed, write "None."

QUESTION:
{query}

CONTEXT:
{chr(10).join(context_blocks)}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text.strip(), sorted(set(citations))


def _polish_grounded_response(text: str) -> str:
    polished = text
    polished = polished.replace("Clarifying questions (if needed):\nNone.", "Clarifying questions (if needed):\n")
    polished = polished.replace("Clarifying questions (if needed):  \nNone.", "Clarifying questions (if needed):\n")
    polished = polished.replace("Assumptions / Not in catalog:\nNone.", "Assumptions / Not in catalog:\n")
    polished = polished.replace("Assumptions / Not in catalog:  \nNone.", "Assumptions / Not in catalog:\n")
    polished = polished.replace("Assumptions / Not in catalog:  \nNone; all statements are grounded explicitly in the provided excerpts.", "Assumptions / Not in catalog:\n")
    polished = polished.replace("Assumptions / Not in catalog:\nNone; all statements are grounded explicitly in the provided excerpts.", "Assumptions / Not in catalog:\n")
    return polished


def ask(query: str, k: int = 4):
    matched_courses = search_course(query)
    matched_course = matched_courses[0] if matched_courses else None

    if _looks_course_specific(query) and not matched_course:
        response = {
            "Answer": "I could not find a course with that exact name in the catalog.",
            "Clarifying questions": [
                "Could you provide the course code?",
                "Or confirm the exact course title?",
            ],
            "Citations": [],
        }
        return response

    chunks, retrieval_mode = retrieve_context(query, k=k)

    if not chunks:
        response = format_assignment_response(
            answer="I don’t have that information in the provided catalog or extracted course data.",
            why="No sufficiently relevant supporting text was retrieved for this question.",
            citations=[],
            clarifying_questions=_default_clarifying_questions(query),
            assumptions=[
                "Check the department page, schedule of classes, or an academic advisor if you need information outside the provided catalog."
            ],
        )
        print(response)
        return response

    if _requires_explicit_prereq_support(query) and not _has_explicit_prereq_language(chunks):
        response = format_assignment_response(
            answer="I don’t have an explicit prerequisite statement for that question in the provided catalog excerpts.",
            why="Relevant text was retrieved, but it does not explicitly state prerequisite or co-requisite requirements.",
            citations=[_format_citation(chunk["metadata"]) for chunk in chunks],
            clarifying_questions=[],
            assumptions=[
                "Check the official course page, schedule of classes, or an academic advisor for prerequisite confirmation."
            ],
        )
        print(response)
        return response

    try:
        body, citations = _generate_grounded_answer(query, chunks)
        body = _polish_grounded_response(body)
        final_response = body + "\n\nCitations:\n" + "\n".join(f"- {item}" for item in citations)
        final_response = verify_response(final_response, fallback_citations=sorted(set(citations)))
    except Exception:
        citations = [_format_citation(chunk["metadata"]) for chunk in chunks]
        final_response = format_assignment_response(
            answer="I found relevant catalog text, but the language-model answer step failed. Review the cited chunks directly.",
            why=f"Retrieval succeeded using {retrieval_mode}, but answer generation did not complete.",
            citations=sorted(set(citations)),
            clarifying_questions=[],
            assumptions=[],
        )
        final_response = verify_response(final_response, fallback_citations=sorted(set(citations)))

    print(final_response)
    return final_response


if __name__ == "__main__":
    ask("What are the prerequisites for Calculus I?")
