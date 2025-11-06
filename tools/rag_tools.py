"""
rag_tools.py
------------
RAG retrieval tool that wraps the Chroma vector database.

This tool allows the agent to search the Appia documentation when needed.
"""

from langchain_chroma import Chroma
from langchain.tools import tool
from langchain_core.documents import Document
from get_embedding_function import get_embedding_function
from ingest import CHROMA_PATH


@tool(response_format="content_and_artifact")
def retrieve_context(query: str) -> tuple[str, list[Document]]:
    """
    Retrieve relevant context from the Appia documentation vector database.
    
    Use this tool when you need information about Appia revenue management software,
    strategies, or related topics that aren't in your training data.
    
    Args:
        query: The search query to find relevant documentation
        
    Returns:
        A tuple of (formatted_context_text, list_of_source_documents)
    """
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    
    results = db.similarity_search_with_score(query, k=4)
    
    # Extract documents and format context
    docs = [doc for doc, _score in results]
    context_text = "\n\n---\n\n".join([doc.page_content for doc in docs])
    
    return context_text, docs
