"""Test retrieval for the voltage query."""
import sys
sys.path.insert(0, 'c:/Users/Rahul kumar/gita/multimodal_rag')

from backend.storage.vector_store import VectorStore
from backend.embeddings.embedding_manager import EmbeddingManager
from backend.retrieval.cross_modal_retriever import CrossModalRetriever
from backend.models.document import Modality

# Initialize components
vector_store = VectorStore()
embedding_manager = EmbeddingManager()
retriever = CrossModalRetriever(vector_store, embedding_manager)

# Query
query = "What is the operating voltage of the machine?"

print(f"Query: {query}")
print(f"Total chunks in DB: {vector_store.count()}\n")

# Retrieve
results = retriever.retrieve(query, top_k=5, modalities=[Modality.TEXT, Modality.IMAGE])

print(f"Retrieved {len(results)} sources:")
for i, source in enumerate(results):
    print(f"\n--- Source {i+1} ---")
    print(f"File: {source.source_file}")
    print(f"Modality: {source.modality}")
    print(f"Relevance: {source.relevance_score:.3f}")
    print(f"Content: {source.content[:200]}...")
