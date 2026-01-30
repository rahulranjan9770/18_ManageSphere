"""Vector store using ChromaDB for multimodal embeddings."""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.models.document import DocumentChunk, Modality
from backend.config import settings
from backend.utils.logger import logger


class VectorStore:
    """Manages vector storage and retrieval using ChromaDB."""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"description": "Multimodal RAG knowledge base"}
            )
            logger.logger.info(f"Connected to collection: {settings.collection_name}")
        except Exception as e:
            logger.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Add document chunks to the vector store."""
        if not chunks:
            return 0
        
        # Filter chunks with embeddings
        valid_chunks = [c for c in chunks if c.embedding is not None]
        
        if not valid_chunks:
            logger.logger.warning("No chunks with embeddings to add")
            return 0
        
        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in valid_chunks]
        embeddings = [chunk.embedding for chunk in valid_chunks]
        documents = [chunk.content for chunk in valid_chunks]
        metadatas = [
            {
                "source_file": chunk.source_file,
                "modality": chunk.modality,  # Already a string due to use_enum_values=True
                "confidence": chunk.confidence,
                "timestamp": chunk.timestamp.isoformat(),
                **{k: str(v) for k, v in chunk.metadata.items()}
            }
            for chunk in valid_chunks
        ]
        
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logger.logger.info(f"Added {len(valid_chunks)} chunks to vector store")
            return len(valid_chunks)
        except Exception as e:
            logger.logger.error(f"Failed to add chunks: {e}")
            return 0
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        modality_filter: Optional[Modality] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the vector store for similar chunks."""
        where_clause = {}
        
        if modality_filter:
            where_clause["modality"] = modality_filter if isinstance(modality_filter, str) else modality_filter.value
        
        if metadata_filter:
            where_clause.update(metadata_filter)
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.logger.debug(
                f"Query returned {len(results['ids'][0])} results "
                f"(modality: {modality_filter}, k: {n_results})"
            )
            
            return results
        except Exception as e:
            logger.logger.error(f"Query failed: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    def get_by_ids(self, chunk_ids: List[str]) -> Dict[str, Any]:
        """Retrieve specific chunks by their IDs."""
        try:
            results = self.collection.get(
                ids=chunk_ids,
                include=["documents", "metadatas", "embeddings"]
            )
            return results
        except Exception as e:
            logger.logger.error(f"Failed to get chunks by IDs: {e}")
            return {"ids": [], "documents": [], "metadatas": []}
    
    def get_all(self) -> Dict[str, Any]:
        """Retrieve all chunks from the store for knowledge graph building."""
        try:
            results = self.collection.get(
                include=["documents", "metadatas"]
            )
            return results
        except Exception as e:
            logger.logger.error(f"Failed to get all chunks: {e}")
            return {"ids": [], "documents": [], "metadatas": []}
    
    def count(self) -> int:
        """Get total number of chunks in the store."""
        try:
            return self.collection.count()
        except:
            return 0
    
    def reset(self):
        """Clear all data from the collection."""
        try:
            # On Windows, delete_collection can cause file locking issues.
            # Instead, we'll get all IDs and delete them.
            ids = self.collection.get()['ids']
            if ids:
                self.collection.delete(ids=ids)
                logger.logger.warning(f"Vector store reset: {len(ids)} items deleted")
            else:
                logger.logger.warning("Vector store already empty")
        except Exception as e:
            logger.logger.error(f"Failed to reset vector store: {e}")
            # Fallback to delete_collection if listing IDs fails
            try:
                self.client.delete_collection(settings.collection_name)
                self.collection = self.client.create_collection(
                    name=settings.collection_name,
                    metadata={"description": "Multimodal RAG knowledge base"}
                )
            except Exception as e2:
                logger.logger.error(f"Fallback reset failed: {e2}")
