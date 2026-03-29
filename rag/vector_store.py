from pathlib import Path
import sys

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import get_openai_api_key, warn_python_compatibility


def create_vector_store(chunks):
    warn_python_compatibility()
    api_key = get_openai_api_key(required=True)

    embeddings = OpenAIEmbeddings(
        api_key=api_key,
        model="text-embedding-3-small"
    )

    persist_directory = BASE_DIR / "data" / "vector_db"

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(persist_directory)
    )

    vector_store.persist()

    print("Vector DB created and saved")

    return vector_store