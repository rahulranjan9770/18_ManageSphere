import time
import asyncio
from backend.storage.vector_store import VectorStore
from backend.models.query import QueryRequest
from backend.generation.rag_generator import RAGGenerator
from backend.retrieval.cross_modal_retriever import CrossModalRetriever
from backend.embeddings.embedding_manager import EmbeddingManager

async def test_speed():
    print("🚀 Testing RAG Pipeline Speed...")
    start_total = time.time()
    
    # Init components
    store = VectorStore()
    embedding_manager = EmbeddingManager()
    retriever = CrossModalRetriever(store, embedding_manager)
    generator = RAGGenerator(retriever)
    
    # Cold start test
    print("querying...")
    request = QueryRequest(query="test query for speed", top_k=3)
    
    start_gen = time.time()
    try:
        response = await generator.generate_response(request)
        duration = time.time() - start_gen
        
        print(f"✅ Response Generated in {duration:.2f} seconds")
        print(f"   Confidence: {response.confidence}")
        print(f"   Answer Length: {len(response.answer)}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_speed())
