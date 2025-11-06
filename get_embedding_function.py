from langchain_huggingface.embeddings import HuggingFaceEmbeddings


def get_embedding_function():
    """
    Returns the embedding model used for both ingestion and retrieval.
    Keep this consistent across ingest.py and main.py.  
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    return embeddings