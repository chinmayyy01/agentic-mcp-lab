from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rag-server")

CHROMA_DIR = (Path(__file__).parent / "chroma_data").resolve()
COLLECTION_NAME = "company_docs"

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

def _get_collection():
    """
    Loads the existing document collection. Raises a clear error if
    ingestion hasn't been run yet, rather than a confusing internal one.
    """
    existing = [c.name for c in _client.list_collections()]
    if COLLECTION_NAME not in existing:
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found. Run ingest.py first "
            f"to populate the document store."
        )
    return _client.get_collection(name=COLLECTION_NAME, embedding_function=_embedding_fn)

@mcp.tool()
def search_documents(query: str, num_results: int = 3) -> str:
    """
    Searches the company document store for chunks semantically relevant
    to the query, and returns the most relevant matches with their source
    file. Use this to answer questions about company policies, onboarding,
    expenses, or remote work. The search is semantic, not keyword-based,
    so natural language questions work well (e.g. 'how much can I spend
    on meals while traveling').
    """
    if not query.strip():
        return "Error: query cannot be empty."

    try:
        collection = _get_collection()
    except RuntimeError as e:
        return f"Error: {e}"

    num_results = max(1, min(num_results, 10))

    results = collection.query(
        query_texts=[query],
        n_results=num_results,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not documents:
        return "No relevant documents found for this query."

    lines = [f"Found {len(documents)} relevant result(s):\n"]
    best_distance = min(distances)
    if best_distance >= 0.9:
        lines.insert(0, "Note: no strongly relevant matches were found. The results below may not answer the question well.\n")

    for doc, meta, distance in zip(documents, metadatas, distances):
        relevance = _distance_to_relevance_label(distance)
        lines.append(
            f"[Source: {meta['source_file']}, relevance: {relevance}]\n{doc}\n"
        )

    return "\n".join(lines)

def _distance_to_relevance_label(distance: float) -> str:
    """
    Converts ChromaDB's raw distance score into a human-readable label.
    Lower distance = more similar. Thresholds tuned empirically against
    this collection and the all-MiniLM-L6-v2 model.
    """
    if distance < 0.7:
        return "high"
    elif distance < 0.9:
        return "medium"
    else:
        return "low"


if __name__ == "__main__":
    mcp.run(transport="stdio")