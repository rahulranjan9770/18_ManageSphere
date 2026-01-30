"""Query analyzer for intent classification and modality detection."""
import re
from typing import List, Tuple
from backend.models.document import Modality
from backend.utils.logger import logger


class QueryAnalyzer:
    """Analyzes user queries to determine intent and required modalities."""
    
    # Keyword patterns for modality detection
    IMAGE_KEYWORDS = [
        "image", "picture", "photo", "diagram", "chart", "graph",
        "illustration", "figure", "visual", "show me", "look like"
    ]
    
    AUDIO_KEYWORDS = [
        "audio", "recording", "said", "spoken", "transcript",
        "conversation", "interview", "speech", "voice", "meeting", "discuss"
    ]
    
    COMPLEX_KEYWORDS = [
        "compare", "contrast", "analyze", "explain", "relationship",
        "difference", "similarity", "comprehensive", "detailed"
    ]
    
    def analyze(self, query: str) -> Tuple[List[Modality], int, str]:
        """
        Analyze query and return (modalities, top_k, reasoning).
        
        Returns:
            - modalities: List of relevant modalities
            - top_k: Suggested number of results to retrieve
            - reasoning: Explanation of the analysis
        """
        query_lower = query.lower()
        modalities = []
        reasoning_parts = []
        
        # Check for image-related queries
        if any(keyword in query_lower for keyword in self.IMAGE_KEYWORDS):
            modalities.append(Modality.IMAGE)
            reasoning_parts.append("Image keywords detected")
        
        # Check for audio-related queries
        if any(keyword in query_lower for keyword in self.AUDIO_KEYWORDS):
            modalities.append(Modality.AUDIO)
            reasoning_parts.append("Audio keywords detected")
        
        # Always include text unless specifically excluded
        if not modalities or any(keyword in query_lower for keyword in self.COMPLEX_KEYWORDS):
            if Modality.TEXT not in modalities:
                modalities.insert(0, Modality.TEXT)
                reasoning_parts.append("Text modality included for comprehensive coverage")
        
        # Ensure Audio is searched when Text is searched (since audio is transcribed)
        if Modality.TEXT in modalities and Modality.AUDIO not in modalities:
            modalities.append(Modality.AUDIO)
            reasoning_parts.append("Audio included for transcript search")
        
        # If no specific modality detected, search all
        if not modalities:
            modalities = [Modality.TEXT, Modality.IMAGE, Modality.AUDIO]
            reasoning_parts.append("No specific modality detected, searching all")
        
        # Determine retrieval depth based on query complexity
        is_complex = (
            any(keyword in query_lower for keyword in self.COMPLEX_KEYWORDS) or
            len(query.split()) > 10 or
            "?" in query  # Questions often need more context
        )
        
        top_k = 20 if is_complex else 10
        if is_complex:
            reasoning_parts.append(f"Complex query detected, using k={top_k}")
        else:
            reasoning_parts.append(f"Simple query, using k={top_k}")
        
        reasoning = "; ".join(reasoning_parts)
        
        logger.log_retrieval_decision(
            query=query,
            modalities=[m.value for m in modalities],
            k=top_k,
            reason=reasoning
        )
        
        return modalities, top_k, reasoning
    
    def extract_entities(self, query: str) -> List[str]:
        """Extract potential entities from query (simple approach)."""
        # Remove common words
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "is", "are", "was",
            "what", "how", "why", "when", "where", "who"
        }
        
        words = re.findall(r'\b[A-Z][a-z]+\b|\b\w{4,}\b', query)
        entities = [w for w in words if w.lower() not in stopwords]
        
        return entities[:5]  # Limit to top 5
