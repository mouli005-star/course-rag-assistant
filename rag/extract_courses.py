import json
from pathlib import Path
import sys

from openai import OpenAI

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import get_openai_api_key, warn_python_compatibility
from prompts import COURSE_EXTRACTION_PROMPT

OUTPUT_PATH = BASE_DIR / "data" / "processed" / "courses.json"
VECTOR_DB_PATH = BASE_DIR / "data" / "vector_db"


warn_python_compatibility()
api_key = get_openai_api_key(required=True)

client = OpenAI(api_key=api_key)


def detect_field(description):
    description = str(description or "").lower()

    rules = {
        "ai": [
            "machine learning",
            "artificial intelligence",
            "neural network",
            "deep learning",
        ],
        "data_science": [
            "statistics",
            "data mining",
            "data analysis",
            "big data",
        ],
        "networking": [
            "network",
            "tcp",
            "routing",
            "distributed",
        ],
        "programming": [
            "programming",
            "software",
            "coding",
        ],
        "math": [
            "calculus",
            "algebra",
            "mathematics",
        ],
    }

    for field, keywords in rules.items():
        for keyword in keywords:
            if keyword in description:
                return field

    return "other"


def _normalize_course_payload(payload):
    if not isinstance(payload, dict):
        return None

    normalized = {
        "course_name": str(payload.get("course_name", "")).strip(),
        "course_code": str(payload.get("course_code", "")).strip(),
        "credits": str(payload.get("credits", "")).strip(),
        "prerequisites": payload.get("prerequisites", []),
        "description": str(payload.get("description", "")).strip(),
        "field": "other",
    }

    if not isinstance(normalized["prerequisites"], list):
        normalized["prerequisites"] = []

    if not normalized["course_name"]:
        return None

    normalized["field"] = detect_field(normalized["description"])

    return normalized


def extract_courses():

    embeddings = OpenAIEmbeddings()

    db = Chroma(
        persist_directory=str(VECTOR_DB_PATH),
        embedding_function=embeddings
    )

    db_data = db.get(include=["documents", "metadatas"])
    docs = db_data.get("documents") or []
    metadatas = db_data.get("metadatas") or []

    if not docs:
        print("No documents found in vector DB. Build/rebuild the index first.")
        return

    extracted_courses = []
    skipped_invalid_json = 0
    skipped_empty_course = 0
    seen_courses = set()

    for i, doc in enumerate(docs):
        metadata = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}

        print(f"Processing chunk {i+1}/{len(docs)}")

        # Use explicit replacement to avoid str.format parsing JSON braces in the prompt template.
        prompt = COURSE_EXTRACTION_PROMPT.replace("{context}", doc)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text_output = response.output_text.strip()

        try:
            course_json = json.loads(text_output)
        except json.JSONDecodeError:
            skipped_invalid_json += 1
            continue

        normalized_course = _normalize_course_payload(course_json)
        if normalized_course is None:
            skipped_empty_course += 1
            continue

        normalized_course["source"] = metadata.get("source", "unknown")
        normalized_course["page"] = metadata.get("page")

        course_key = (
            normalized_course["course_name"].lower(),
            normalized_course["course_code"].lower(),
        )

        if course_key in seen_courses:
            continue

        seen_courses.add(course_key)
        extracted_courses.append(normalized_course)


    # save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(extracted_courses, f, indent=2)


    print("\nExtraction completed")
    print(f"Courses found: {len(extracted_courses)}")
    print(f"Skipped invalid JSON responses: {skipped_invalid_json}")
    print(f"Skipped empty/non-course outputs: {skipped_empty_course}")



if __name__ == "__main__":
    extract_courses()