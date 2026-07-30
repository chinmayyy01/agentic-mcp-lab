import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

DOCS_DIR = (Path(__file__).parent.parent.parent / "data" / "sample_docs").resolve()
CHROMA_DIR = (Path(__file__).parent / "chroma_data").resolve()

CHUNK_SIZE = 200
CHUNK_OVERLAP = 40

def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Splits text into overlapping chunks of roughly `chunk_size` characters.
    Overlap preserves context across chunk boundaries so a sentence split
    mid way isn't completely lost to either chunk.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def main():
    client = chromadb.PersistentClient(path = str(CHROMA_DIR))

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name = "all-MiniLM-L6-v2"
    )

    collection = client.get_or_create_collection(
        name = "company_docs",
        embedding_function = embedding_fn
    )

    all_ids = []
    all_documents = []
    all_metadatas = []

    for file_path in DOCS_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_path.stem}_chunk{i}"
            all_ids.append(chunk_id)
            all_documents.append(chunk)
            all_metadatas.append({
                "source_file": file_path.name,
                "chunk_index": i,
            })

        print(f"  {file_path.name}: {len(chunks)} chunks")

    collection.add(
        ids = all_ids,
        documents = all_documents,
        metadatas = all_metadatas
    )

    print(f"\nIngested {len(all_ids)} total chunks into '{collection.name}'.")
    print(f"Stored at: {CHROMA_DIR}")


if __name__ == "__main__":
    main()