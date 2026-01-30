"""
Direct Vector Store Test
"""
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.storage.vector_store import VectorStore
from backend.models.document import Modality
from backend.embeddings.embedding_manager import EmbeddingManager

db = VectorStore()
emb = EmbeddingManager()

print(f"Collection count: {db.count()}")

query = "meeting discussion machine voltage"
print(f"Query: {query}")

# 1. Text embedding
text_emb = emb.embed_query(query, Modality.TEXT)
print(f"Embedding length: {len(text_emb)}")

# 2. Query for AUDIO modality
print("\nQuerying Modality.AUDIO...")
results = db.collection.query(
    query_embeddings=[text_emb],
    n_results=10,
    where={"modality": "audio"}
)

print(f"Ids found: {results['ids'][0]}")
print(f"Distances: {results['distances'][0]}")
print(f"Docs: {results['documents'][0]}")

# 3. Query for TEXT modality
print("\nQuerying Modality.TEXT...")
results_text = db.collection.query(
    query_embeddings=[text_emb],
    n_results=10,
    where={"modality": "text"}
)
print(f"Ids found: {results_text['ids'][0]}")
