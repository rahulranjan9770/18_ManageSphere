"""Direct database inspection."""
import chromadb
from chromadb.config import Settings

# Connect to the exact same database
client = chromadb.PersistentClient(
    path="./data/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

# Get the collection
try:
    collection = client.get_collection("multimodal_knowledge")
    count = collection.count()
    print(f"Total chunks: {count}")
    
    # Get all items
    if count > 0:
        results = collection.get(limit=10, include=["documents", "metadatas"])
        print(f"\nFound {len(results['ids'])} items:")
        for i, (doc_id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
            print(f"\n--- Item {i+1} ---")
            print(f"ID: {doc_id}")
            print(f"Source: {meta.get('source_file', 'unknown')}")
            print(f"Modality: {meta.get('modality', 'unknown')}")
            print(f"Content: {doc[:150]}...")
except Exception as e:
    print(f"Error: {e}")
