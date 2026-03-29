try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise ImportError(
            "RecursiveCharacterTextSplitter not found. Install with: "
            "pip install langchain-text-splitters"
        ) from exc


def split_documents(documents):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = text_splitter.split_documents(documents)

    print(f"Created {len(chunks)} chunks")

    print("\nExample chunk:\n")
    print(chunks[0].page_content[:300])

    return chunks