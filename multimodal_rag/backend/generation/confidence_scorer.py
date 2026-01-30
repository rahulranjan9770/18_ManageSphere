"""Confidence scorer for assessing evidence quality."""
from typing import List
import numpy as np

from backend.models.query import EvidenceSource
from backend.utils.logger import logger


class ConfidenceScorer:
    """Assesses the strength and quality of retrieved evidence."""
    
    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold
    
    def score_evidence(self, sources: List[EvidenceSource]) -> tuple[float, str, str]:
        """
        Score overall evidence quality.
        
        Returns:
            (confidence_score, confidence_level, reasoning)
        """
        if not sources:
            return 0.0, "None", "No evidence found"
        
        # Calculate component scores
        relevance_scores = [s.relevance_score for s in sources]
        source_confidences = [s.confidence for s in sources]
        
        # Average relevance
        avg_relevance = np.mean(relevance_scores)
        
        # Average source quality
        avg_confidence = np.mean(source_confidences)
        
        # Cross-modal agreement (bonus if multiple modalities)
        unique_modalities = len(set(s.modality for s in sources))
        cross_modal_bonus = min(0.1 * (unique_modalities - 1), 0.2)
        
        # Diversity score (more unique sources = higher confidence)
        unique_sources = len(set(s.source_file for s in sources))
        diversity_bonus = min(0.05 * unique_sources, 0.15)
        
        # Combined confidence
        base_score = (avg_relevance * 0.5) + (avg_confidence * 0.5)
        final_score = min(base_score + cross_modal_bonus + diversity_bonus, 1.0)
        
        # Determine confidence level
        if final_score >= 0.8:
            level = "High"
        elif final_score >= self.confidence_threshold:
            level = "Medium"
        else:
            level = "Low"
        
        # Build reasoning
        reasoning_parts = [
            f"Avg relevance: {avg_relevance:.2f}",
            f"Avg source quality: {avg_confidence:.2f}",
            f"Unique sources: {unique_sources}",
            f"Modalities: {unique_modalities}"
        ]
        
        if cross_modal_bonus > 0:
            reasoning_parts.append(f"Cross-modal bonus: +{cross_modal_bonus:.2f}")
        
        reasoning = "; ".join(reasoning_parts)
        
        logger.log_confidence_assessment(
            confidence=final_score,
            sources=len(sources),
            reason=reasoning
        )
        
        return final_score, level, reasoning
    
    def identify_gaps(self, sources: List[EvidenceSource], query: str) -> List[str]:
        """Identify what information is missing from the evidence."""
        gaps = []
        
        if not sources:
            return ["No relevant sources found"]
        
        # Check for low relevance
        if all(s.relevance_score < 0.5 for s in sources):
            gaps.append("Retrieved sources have low relevance to query")
        
        # Check for missing modalities (if query suggests specific one)
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["image", "diagram", "picture"]):
            if not any(s.modality.value == "image" for s in sources):
                gaps.append("No image sources found despite query suggestion")
        
        # Check for sparse coverage
        if len(sources) < 3:
            gaps.append(f"Only {len(sources)} source(s) found, insufficient coverage")
        
        return gaps
