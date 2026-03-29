import json
from pathlib import Path
import re
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import get_openai_api_key, warn_python_compatibility


COURSES_FILE = BASE_DIR / "data" / "processed" / "courses.json"

PERSIST_DIR = BASE_DIR / "data" / "vector_db"


def normalize(text):

    return text.lower().strip()


def simplify_query(text):
    query = normalize(text)
    removable_phrases = [
        "can i take",
        "am i eligible for",
        "eligible for",
        "what do i need before",
        "what are the prerequisites for",
        "prerequisites for",
        "show me",
        "show",
        "list",
        "recommend",
        "courses for",
    ]

    for phrase in removable_phrases:
        query = query.replace(phrase, " ")

    return " ".join(query.split())


def tokenize(text):
    return re.findall(r"[a-z0-9]+", normalize(text))


def has_token_sequence(full_text, phrase_text):
    full_tokens = tokenize(full_text)
    phrase_tokens = tokenize(phrase_text)

    if not phrase_tokens or len(phrase_tokens) > len(full_tokens):
        return False

    for index in range(len(full_tokens) - len(phrase_tokens) + 1):
        if full_tokens[index:index + len(phrase_tokens)] == phrase_tokens:
            return True

    return False


def detect_query_field(query):
    query = normalize(query)

    field_aliases = {
        "ai": ["ai", "artificial intelligence", "machine learning", "deep learning", "neural network"],
        "data_science": ["data science", "statistics", "data mining", "data analysis", "big data"],
        "networking": ["network", "networking", "tcp", "routing", "distributed"],
        "programming": ["programming", "software development", "coding", "software"],
        "math": ["math", "mathematics", "calculus", "algebra"],
    }

    for field, keywords in field_aliases.items():
        if any(keyword in query for keyword in keywords):
            return field

    return None


def field_search(query):
    query = simplify_query(query)
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        courses = json.load(f)

    detected_field = detect_query_field(query)
    if not detected_field:
        return []

    matches = []

    for c in courses:
        if c.get("field") == detected_field:
            matches.append({
                "course_name": c.get("course_name"),
                "course_code": c.get("course_code"),
                "page": c.get("page"),
                "field": c.get("field"),
            })

    return matches


def keyword_search(query):
    query = simplify_query(query)

    with open(COURSES_FILE, "r", encoding="utf-8") as f:

        courses = json.load(f)


    query = normalize(query)


    matches = []


    for c in courses:

        name = normalize(c["course_name"])


        if query in name:

            matches.append({

                "course_name": c["course_name"],

                "course_code": c["course_code"],

                "page": c["page"],

                "field": c.get("field", "other")

            })


    return matches


def lexical_search(query, limit=5):
    query = simplify_query(query)
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        courses = json.load(f)

    query_text = normalize(query)
    query_tokens = set(tokenize(query))

    if not query_tokens and not query_text:
        return []

    scored = []

    for course in courses:
        course_name = course.get("course_name", "")
        course_code = course.get("course_code", "")
        searchable = f"{course_name} {course_code}"
        searchable_tokens = set(tokenize(searchable))

        overlap = len(query_tokens & searchable_tokens)
        phrase_bonus = 3 if course_name and has_token_sequence(query_text, course_name) else 0
        code_bonus = 4 if course_code and normalize(course_code).replace(" ", "") in query_text.replace(" ", "") else 0
        score = overlap + phrase_bonus + code_bonus

        if score <= 0:
            continue

        scored.append(
            (
                score,
                {
                    "course_name": course_name,
                    "course_code": course_code,
                    "page": course.get("page"),
                    "field": course.get("field", "other"),
                },
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1]["course_name"] or ""))
    return [item[1] for item in scored[:limit]]


def semantic_search(query):
    query = simplify_query(query)
    try:
        from langchain_chroma import Chroma
    except Exception:
        try:
            from langchain_community.vectorstores import Chroma
        except Exception:
            return []

    try:
        from langchain_openai import OpenAIEmbeddings
    except Exception:
        return []

    try:
        warn_python_compatibility()
        api_key = get_openai_api_key(required=True)

        embeddings = OpenAIEmbeddings(
            api_key=api_key,
            model="text-embedding-3-small"
        )


        db = Chroma(

            persist_directory=str(PERSIST_DIR),

            embedding_function=embeddings

        )


        results = db.similarity_search(query, k=5)
    except Exception:
        # Keep search usable via keyword/field matching when vector stack is unavailable.
        return []


    matches = []


    for r in results:

        matches.append({

            "course_name": r.metadata.get("course_name"),

            "course_code": r.metadata.get("course_code"),

            "page": r.metadata.get("page"),

            "field": r.metadata.get("field", "other")

        })


    return matches


def search_course(query):

    # Handle field queries like "AI courses" before name similarity matching.
    field_matches = field_search(query)

    if len(field_matches) > 0:

        return field_matches

    # try strict name match first

    keyword_matches = keyword_search(query)


    if len(keyword_matches) > 0:

        return keyword_matches

    lexical_matches = lexical_search(query)

    if len(lexical_matches) > 0:

        return lexical_matches


    # fallback to semantic search

    return semantic_search(query)



if __name__ == "__main__":

    matches = search_course("health care")


    print("\nMatches:\n")


    for m in matches:

        print(m)
