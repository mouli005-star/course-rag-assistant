from ingestion import load_documents
from chunking import split_documents
from vector_store import create_vector_store


docs = load_documents()

chunks = split_documents(docs)

db = create_vector_store(chunks)