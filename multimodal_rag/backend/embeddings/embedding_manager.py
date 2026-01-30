"""Manager for generating embeddings for different modalities."""
from typing import List, Union, Any
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from backend.config import settings
from backend.models.document import DocumentChunk, Modality
from backend.utils.logger import logger

class EmbeddingManager:
    """Manages embedding models and generation."""
    
    def __init__(self):
        self.text_model = None
        self.image_model = None
        
        try:
            if SentenceTransformer:
                logger.logger.info(f"Loading text embedding model: {settings.text_embedding_model}")
                self.text_model = SentenceTransformer(settings.text_embedding_model)
            else:
                logger.logger.warning("sentence-transformers not installed, using dummy embeddings")
        except Exception as e:
            logger.logger.error(f"Failed to load embedding models: {e}")

    def embed_query(self, query: str, modality: Modality = Modality.TEXT) -> List[float]:
        """Generate embedding for a query."""
        # Use text model for TEXT and AUDIO (since audio is searched via transcript)
        try:
            if self.text_model and modality in [Modality.TEXT, Modality.AUDIO]:
                logger.logger.info(f"Generating embedding for query='{query[:20]}...' modality={modality}")
                embedding = self.text_model.encode(query).tolist()
                return embedding
        except Exception as e:
            logger.logger.error(f"Embedding generation failed: {e}")
            
        # Fallback/Dummy
        logger.logger.warning(f"Using dummy embedding for modality={modality}")
        return [0.0] * 384

    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Generate embeddings for a list of chunks."""
        if not chunks:
            return []
            
        # Handle TEXT and AUDIO chunks (audio is transcribed to text)
        text_based_chunks = [c for c in chunks if c.modality in [Modality.TEXT, Modality.AUDIO]]
        if text_based_chunks and self.text_model:
            texts = [c.content for c in text_based_chunks]
            embeddings = self.text_model.encode(texts).tolist()
            
            # Assign embeddings
            for i, chunk in enumerate(text_based_chunks):
                chunk.embedding = embeddings[i]
        
        # For IMAGE modality, we'd need CLIP or similar
        # For now, skip image embeddings (can be added later)
        
        return chunks
