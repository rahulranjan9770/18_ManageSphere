"""Conflict detector for identifying contradictions in evidence."""
from typing import List, Optional, Dict
import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from backend.models.query import EvidenceSource, ConflictInfo
from backend.embeddings.text_embedder import TextEmbedder
from backend.utils.logger import logger


class ConflictDetector:
    """Detects contradictions and conflicts between evidence sources."""
    
    def __init__(self):
        self.embedder = TextEmbedder()
        self.negation_patterns = [
            r'\bnot\b', r'\bno\b', r'\bnever\b', r'\bneither\b',
            r'\bcontradicts?\b', r'\bdisproves?\b', r'\brefutes?\b',
            r'\binstead\b', r'\bhowever\b', r'\bbut\b'
        ]
    
    def detect_conflicts(self, sources: List[EvidenceSource]) -> Optional[ConflictInfo]:
        """
        Detect if sources contain conflicting information.
        
        Returns ConflictInfo if conflicts found, None otherwise.
        """
        if len(sources) < 2:
            return None
        
        # Extract claims from each source
        claims_by_source = {}
        for source in sources:
            claims = self._extract_claims(source.content)
            if claims:
                claims_by_source[source.source_id] = {
                    'claims': claims,
                    'source': source
                }
        
        if len(claims_by_source) < 2:
            return None
        
        # Pairwise comparison
        conflicts = []
        source_ids = list(claims_by_source.keys())
        
        for i in range(len(source_ids)):
            for j in range(i + 1, len(source_ids)):
                source_a = claims_by_source[source_ids[i]]
                source_b = claims_by_source[source_ids[j]]
                
                conflict = self._compare_claims(
                    source_a['claims'],
                    source_b['claims'],
                    source_a['source'],
                    source_b['source']
                )
                
                if conflict:
                    conflicts.append(conflict)
        
        if conflicts:
            # Build ConflictInfo
            conflicting_sources = list(set(
                source_id
                for conflict in conflicts
                for source_id in conflict['sources']
            ))
            
            perspectives = [
                {
                    'source': conflict['source_a'],
                    'claim': conflict['claim_a']
                }
                for conflict in conflicts
            ] + [
                {
                    'source': conflict['source_b'],
                    'claim': conflict['claim_b']
                }
                for conflict in conflicts
            ]
            
            # Deduplicate perspectives
            unique_perspectives = []
            seen = set()
            for p in perspectives:
                key = (p['source'], p['claim'])
                if key not in seen:
                    unique_perspectives.append(p)
                    seen.add(key)
            
            conflict_info = ConflictInfo(
                conflicting_sources=conflicting_sources,
                description=f"{len(conflicts)} contradiction(s) detected between sources",
                perspectives=unique_perspectives
            )
            
            logger.log_conflict_detection(
                conflicting_sources=conflicting_sources,
                details=conflict_info.description
            )
            
            return conflict_info
        
        return None
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text (simplified)."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Filter for factual claims (sentences with verbs, nouns)
        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Basic heuristic: must be longer than 2 words
            if len(sentence.split()) > 2:
                claims.append(sentence)
        
        return claims[:3]  #Limit to top 3 claims per source
    
    def _compare_claims(
        self,
        claims_a: List[str],
        claims_b: List[str],
        source_a: EvidenceSource,
        source_b: EvidenceSource
    ) -> Optional[Dict]:
        """Compare claims between two sources."""
        if not claims_a or not claims_b:
            return None
        
        # Embed all claims
        all_claims = claims_a + claims_b
        embeddings = self.embedder.embed(all_claims)
        
        embeddings_a = embeddings[:len(claims_a)]
        embeddings_b = embeddings[len(claims_a):]
        
        # Find most similar pair
        similarities = cosine_similarity(embeddings_a, embeddings_b)
        max_sim_idx = np.unravel_index(similarities.argmax(), similarities.shape)
        max_similarity = similarities[max_sim_idx]
        
        claim_a = claims_a[max_sim_idx[0]]
        claim_b = claims_b[max_sim_idx[1]]
        
        # Check for semantic similarity but textual negation
        # High similarity (same topic) + negation pattern = conflict
        has_negation_a = any(re.search(pat, claim_a, re.IGNORECASE) for pat in self.negation_patterns)
        has_negation_b = any(re.search(pat, claim_b, re.IGNORECASE) for pat in self.negation_patterns)
        
        # Conflict conditions:
        # 1. Similar topic (similarity > 0.6) but one has negation
        # 2. OR very similar (> 0.8) but not identical (< 0.95) with different key terms
        is_conflict = False
        
        if max_similarity > 0.5:
            if has_negation_a != has_negation_b and max_similarity < 0.95:
                is_conflict = True
            elif self._has_contradictory_numbers(claim_a, claim_b):
                is_conflict = True
        
        if is_conflict:
            return {
                'sources': [source_a.source_id, source_b.source_id],
                'source_a': source_a.source_file,
                'source_b': source_b.source_file,
                'claim_a': claim_a,
                'claim_b': claim_b,
                'similarity': float(max_similarity)
            }
        
        return None
    
    def _has_contradictory_numbers(self, text_a: str, text_b: str) -> bool:
        """Check if texts contain different numbers for same concept."""
        # Extract numbers
        numbers_a = re.findall(r'\d+(?:\.\d+)?', text_a)
        numbers_b = re.findall(r'\d+(?:\.\d+)?', text_b)
        
        if numbers_a and numbers_b:
            # If both have numbers and they're different, might be conflict
            return set(numbers_a) != set(numbers_b)
        
        return False
