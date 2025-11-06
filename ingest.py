"""
ingest.py
---------
This script ingests documents (PDF and TXT) into a Chroma vector database.
It:
1. Loads all documents from the `data/` folder.
2. Splits them into smaller chunks for better search accuracy.
3. Converts them into embeddings using the configured embedding model.
4. Stores them in the Chroma DB (persistent on disk).

Usage:
    python ingest.py          # Adds new documents to the database
    python ingest.py --reset  # Clears the database before adding documents
"""

import argparse
import os
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from get_embedding_function import get_embedding_function
from langchain_community.document_loaders import PyPDFDirectoryLoader, DirectoryLoader, TextLoader
from langchain_chroma import Chroma

# Folder containing the vector database
CHROMA_PATH = "chroma"

# Folder containing all documents to ingest
DATA_PATH = "data"


def main():
    # Check if the database should be cleared (using the --reset flag).
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database before ingestion.")
    args = parser.parse_args()
    
    if args.reset:
        print("Clearing Database")
        clear_database()

    # Create (or update) the data store.
    documents = load_documents()

    chunks = split_documents(documents)
    add_to_chroma(chunks)


def load_documents():
    """Loads all supported documents (PDF + TXT) from DATA_PATH."""

    # Load PDFs
    pdf_loader = PyPDFDirectoryLoader(DATA_PATH)
    pdf_docs = pdf_loader.load()

    # Load TXT files
    txt_loader = DirectoryLoader(
        DATA_PATH, glob="**/*.txt", loader_cls=TextLoader
    )
    txt_docs = txt_loader.load()

    # Add other file types if needed

    return pdf_docs + txt_docs

def split_documents(documents: list[Document]):
    """Splits documents into smaller chunks for better retrieval."""

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def add_to_chroma(chunks: list[Document]):
    """Stores chunks in the Chroma DB, avoiding duplicates."""

    # Load the existing database.
    db = Chroma(
        persist_directory=CHROMA_PATH, embedding_function=get_embedding_function()
    )

    # Calculate Page IDs.
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Add or Update the documents.
    existing_items = db.get(include=[])  # IDs are always included by default
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing chunks in DB: {len(existing_ids)}")

    # Only add documents that don't exist in the DB.
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if len(new_chunks):
        print(f"🔄 Adding new chunks: {len(new_chunks)}")
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
    else:
        print("✅ No new chunk to add")


def calculate_chunk_ids(chunks):
    """
    Generates a unique ID for each chunk based on:
    source file path : page number : chunk index
    Example: data/manual.pdf:6:2
    """

    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get("source")
        page = chunk.metadata.get("page", 0)
        current_page_id = f"{source}:{page}"

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database():
    """Deletes the existing Chroma database."""
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)


if __name__ == "__main__":
    main()