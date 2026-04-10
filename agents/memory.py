"""
Memory Management (RAG) using ChromaDB & Ollama Embeddings.
Allows the agents to learn from past architectures.
"""

import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

DB_DIR = "./chroma_db"


def _get_embeddings():
    """
    Prefer local Ollama embeddings when available.
    If Ollama isn't running/installed, we degrade gracefully so the rest of the
    app can still function (memory just becomes unavailable).
    """
    try:
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model="nomic-embed-text")
    except Exception as exc:
        raise RuntimeError(
            "Embeddings backend unavailable. Install/run Ollama to enable memory features."
        ) from exc


def get_vector_store():
    """Initializes or loads the ChromaDB vector store."""
    embeddings = _get_embeddings()
    return Chroma(
        collection_name="architecture_memory",
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

def train_memory(path: str):
    """
    Reads all code/text in a directory, chunks it,
    and stores it in the local Vector Database.
    """
    if not os.path.exists(path):
        print("Path does not exist.")
        return

    print(f"[Memory] Reading codebase for training from: {path}")
    docs = []

    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append(Document(page_content=content, metadata={"source": path}))
        except Exception as e:
            print(f"Error reading file {path}: {e}")
    else:
        allowed_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".cs", ".rb", ".php", ".md", ".txt"}
        for root, _, files in os.walk(path):
            if any(part.startswith('.') for part in root.split(os.sep)) or "node_modules" in root or "venv" in root or "__pycache__" in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_exts:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            docs.append(Document(page_content=f.read(), metadata={"source": file_path}))
                    except Exception:
                        pass
    
    if not docs:
        print("No valid code or text files found to train on.")
        return

    print(f"[Memory] Chunking {len(docs)} files into memory fragments...")
    # Increase chunk size to 4000 to drastically reduce fragment count and speed up training
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=500)
    splits = text_splitter.split_documents(docs)

    print(f"[Memory] Saving {len(splits)} memory fragments to VectorDB (Chroma)...")
    try:
        vector_store = get_vector_store()
        vector_store.add_documents(splits)
        print("[Memory] Training complete.")
    except Exception as exc:
        print(f"[Memory] Training unavailable: {exc}")
        return

def retrieve_memory(query: str, k: int = 3) -> str:
    """
    Searches the VectorDB for past architectural decisions
    similar to the query.
    """
    if not os.path.exists(DB_DIR):
        return "No past architectural memory found. ChromaDB is empty."
        
    try:
        vector_store = get_vector_store()
        results = vector_store.similarity_search(query, k=k)
    except Exception as exc:
        return f"No past architectural memory found (memory backend unavailable: {exc})."
    
    if not results:
        return "No relevant past memory found."
        
    memory_text = "\n\n".join([f"[Source: {doc.metadata.get('source', 'Unknown')}]\n{doc.page_content}" for doc in results])
    return memory_text

def forget_memory(path: str):
    """
    Deletes memory fragments belonging to a specific file or resets everything.
    """
    if not os.path.exists(DB_DIR):
        print("No memory found to delete.")
        return

    vector_store = get_vector_store()

    if path.lower() == "all":
        import shutil
        shutil.rmtree(DB_DIR, ignore_errors=True)
        print("[Memory] Entire architectural memory wiped.")
        return
    
    # Chroma requires an exact metadata match for deletion
    try:
        # The vectorDB uses Document(metadata={"source": path})
        vector_store._collection.delete(where={"source": path})
        print(f"[Memory] Forgot memory trained from: {path}")
    except Exception as e:
        print(f"[Memory] Failed to remove memory: {e}")
