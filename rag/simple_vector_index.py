from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from openai import OpenAI
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import get_openai_api_key
from rag.source_catalog import derive_section_heading


RAW_DOCS_DIR = BASE_DIR / "data" / "raw_docs"
INDEX_DIR = BASE_DIR / "data" / "vector_db"
EMBEDDINGS_FILE = INDEX_DIR / "simple_embeddings.npy"
METADATA_FILE = INDEX_DIR / "simple_metadata.json"
MODEL_NAME = "text-embedding-3-small"


def chunk_raw_docs():
    chunks = []
    for pdf_path in sorted(RAW_DOCS_DIR.glob("*.pdf")):
        reader = PdfReader(str(pdf_path))
        for page_index, page in enumerate(reader.pages):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue

            raw_sections = [section.strip() for section in page_text.split("\n\n") if section.strip()]
            sections = raw_sections or [page_text]

            for section_index, section_text in enumerate(sections, start=1):
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


def _embed_texts(texts: list[str]) -> np.ndarray:
    client = OpenAI(api_key=get_openai_api_key(required=True))
    response = client.embeddings.create(model=MODEL_NAME, input=texts)
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype=np.float32)


def build_simple_vector_index(batch_size: int = 64):
    chunks = chunk_raw_docs()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    all_vectors = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = _embed_texts([item["text"] for item in batch])
        all_vectors.append(vectors)

    embeddings = np.vstack(all_vectors) if all_vectors else np.zeros((0, 1536), dtype=np.float32)
    np.save(EMBEDDINGS_FILE, embeddings)
    METADATA_FILE.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    return len(chunks)


def simple_index_exists():
    return EMBEDDINGS_FILE.exists() and METADATA_FILE.exists()


def load_simple_index():
    if not simple_index_exists():
        return None, None
    embeddings = np.load(EMBEDDINGS_FILE)
    metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return embeddings, metadata


def search_simple_vector_index(query: str, k: int = 4):
    embeddings, metadata = load_simple_index()
    if embeddings is None or metadata is None or len(metadata) == 0:
        return []

    query_vector = _embed_texts([query])[0]
    doc_norms = np.linalg.norm(embeddings, axis=1)
    query_norm = np.linalg.norm(query_vector)
    scores = np.dot(embeddings, query_vector) / (doc_norms * query_norm + 1e-8)
    top_indices = np.argsort(scores)[::-1][:k]
    return [metadata[int(index)] for index in top_indices if float(scores[int(index)]) > 0]


if __name__ == "__main__":
    total = build_simple_vector_index()
    print(f"Built simple vector index with {total} chunks")
