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


def build_source_citation(source_id, section_heading, chunk_or_section):
    source = get_source_record(source_id)
    source_name = source_id or source.get("title") or "unknown source"
    parts = [source_name]

    if section_heading:
        parts.append(section_heading)

    if chunk_or_section:
        parts.append(chunk_or_section)

    return " | ".join(parts)
