from langchain_community.document_loaders import PyPDFLoader
import os


DATA_PATH = "data/raw_docs"


def load_documents():

    documents = []

    for file in os.listdir(DATA_PATH):

        if file.endswith(".pdf"):

            loader = PyPDFLoader(os.path.join(DATA_PATH, file))

            docs = loader.load()

            for d in docs:

                d.metadata["source"] = file

            documents.extend(docs)

    return documents