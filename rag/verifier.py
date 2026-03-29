from __future__ import annotations

from rag.output_formatter import format_assignment_response


REQUIRED_HEADERS = [
    "Answer / Plan:",
    "Why (requirements/prereqs satisfied):",
    "Citations:",
    "Clarifying questions (if needed):",
    "Assumptions / Not in catalog:",
]


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_header = None
    buffer: list[str] = []

    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped in REQUIRED_HEADERS:
            if current_header is not None:
                sections[current_header] = "\n".join(buffer).strip()
            current_header = stripped
            buffer = []
            continue
        buffer.append(line)

    if current_header is not None:
        sections[current_header] = "\n".join(buffer).strip()

    return sections


def normalize_citations(citations_text: str) -> list[str]:
    items = []
    for line in str(citations_text or "").splitlines():
        cleaned = line.strip()
        if cleaned.startswith("- "):
            cleaned = cleaned[2:].strip()
        if cleaned:
            items.append(cleaned)
    return items


def verify_response(
    response_text: str,
    fallback_citations: list[str] | None = None,
    default_assumptions: list[str] | None = None,
) -> str:
    fallback_citations = fallback_citations or []
    default_assumptions = default_assumptions or []

    if all(header in str(response_text or "") for header in REQUIRED_HEADERS):
        sections = parse_sections(response_text)
        citations = normalize_citations(sections.get("Citations:", ""))
        clarifying = normalize_citations(sections.get("Clarifying questions (if needed):", ""))
        assumptions = normalize_citations(sections.get("Assumptions / Not in catalog:", ""))

        if not citations:
            citations = fallback_citations

        return format_assignment_response(
            answer=sections.get("Answer / Plan:", ""),
            why=sections.get("Why (requirements/prereqs satisfied):", ""),
            citations=citations,
            clarifying_questions=clarifying,
            assumptions=assumptions or default_assumptions,
        )

    return format_assignment_response(
        answer=response_text,
        why="The verifier normalized the response into the required assignment format.",
        citations=fallback_citations,
        clarifying_questions=[],
        assumptions=default_assumptions,
    )
