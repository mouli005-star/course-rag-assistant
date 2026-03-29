from __future__ import annotations

from typing import Iterable


def _normalize_lines(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []

    lines = []
    for item in value:
        text = str(item).strip()
        if text:
            lines.append(text)
    return lines


def format_assignment_response(
    answer,
    why,
    citations: Iterable[str] | None = None,
    clarifying_questions=None,
    assumptions=None,
) -> str:
    citation_lines = _normalize_lines(citations)
    clarifying_lines = _normalize_lines(clarifying_questions)
    assumption_lines = _normalize_lines(assumptions)

    sections = [
        "Answer / Plan:",
        "\n".join(_normalize_lines(answer)) or "I could not determine a supported answer from the available materials.",
        "",
        "Why (requirements/prereqs satisfied):",
        "\n".join(_normalize_lines(why)) or "No supported explanation available.",
        "",
        "Citations:",
        "\n".join(f"- {line}" for line in citation_lines) or "- No direct catalog citation was available for this response.",
        "",
        "Clarifying questions (if needed):",
        "\n".join(f"- {line}" for line in clarifying_lines),
        "",
        "Assumptions / Not in catalog:",
        "\n".join(f"- {line}" for line in assumption_lines),
    ]

    return "\n".join(sections)
