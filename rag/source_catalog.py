import json
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCES_FILE = BASE_DIR / "data" / "processed" / "sources.json"


@lru_cache(maxsize=1)
def load_sources():
    if not SOURCES_FILE.exists():
        return {}

    records = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {record["source_id"]: record for record in records}


def get_source_record(source_id):
    return load_sources().get(source_id, {})


def derive_section_heading(text, fallback="Section unavailable"):
    for line in str(text or "").splitlines():
        cleaned = " ".join(line.split()).strip(" -:\t")
        if len(cleaned) >= 4:
            return cleaned[:120]
    return fallback


def build_source_citation(source_id, section_heading, chunk_or_section, page_label=None):
    source = get_source_record(source_id)
    source_name = source.get("title") or source_id or "unknown source"
    source_url = source.get("url") or "URL unavailable"

    parts = [
        source_name,
        f"URL: {source_url}",
    ]

    if section_heading:
        parts.append(f"Section: {section_heading}")

    if chunk_or_section:
        parts.append(f"Ref: {chunk_or_section}")

    if page_label:
        parts.append(f"Page: {page_label}")

    return " | ".join(parts)
