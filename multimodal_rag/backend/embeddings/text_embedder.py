"""Text embedding functionality."""
from typing import List, Union
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from backend.config import settings
from backend.utils.logger import logger

class TextEmbedder:
    """Generates embeddings for text."""
    
    def __init__(self):
        self.model = None
        try:
            if SentenceTransformer:
                self.model = SentenceTransformer(settings.text_embedding_model)
            else:
                logger.logger.warning("sentence-transformers not installed")
        except Exception as e:
            logger.logger.error(f"Failed to load text embedding model: {e}")

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if not texts:
            return np.array([])
            
        if self.model:
            return self.model.encode(texts)
            
        # Fallback dummy embeddings
        return np.random.rand(len(texts), 384)
