"""Cross-modal retriever for unified multimodal search."""
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from backend.models.document import Modality
from backend.models.query import EvidenceSource
from backend.storage.vector_store import VectorStore
from backend.embeddings.embedding_manager import EmbeddingManager
from backend.retrieval.query_analyzer import QueryAnalyzer
from backend.utils.logger import logger
from backend.utils.language_service import language_service, detect_language



class CrossModalRetriever:
    """Performs cross-modal retrieval with alignment scoring."""
    
    def __init__(self, vector_store: VectorStore, embedding_manager: EmbeddingManager):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.query_analyzer = QueryAnalyzer()
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = None,
        modalities: List[Modality] = None,
        cross_lingual: bool = True
    ) -> List[EvidenceSource]:
        """
        Retrieve relevant chunks across modalities with cross-lingual support.
        
        Args:
            query: User query string
            top_k: Number of results (if None, use query analyzer suggestion)
            modalities: Specific modalities to search (if None, analyze query)
            cross_lingual: Enable cross-lingual search (translate query to multiple languages)
        
        Returns:
            List of EvidenceSource objects ranked by relevance
        """
        # Analyze query if parameters not provided
        if top_k is None or modalities is None:
            analyzed_modalities, analyzed_k, reasoning = self.query_analyzer.analyze(query)
            modalities = modalities or analyzed_modalities
            top_k = top_k or analyzed_k
            
        self.query_text = query  # Store for keyword boosting logic
        
        # Detect query language
        query_lang, lang_confidence = detect_language(query)
        logger.logger.info(f"Query language detected: {query_lang} ({lang_confidence:.2f})")
        
        # Build list of queries to search (original + translations)
        queries_to_search = [(query, query_lang)]
        
        # Cross-lingual search: translate query to other languages
        if cross_lingual and language_service.translator:
            # Translate to English and Hindi for cross-lingual search
            target_langs = ['en', 'hi']
            for target_lang in target_langs:
                if target_lang != query_lang:
                    translated = language_service.translate(query, query_lang, target_lang)
                    if translated and translated.lower() != query.lower():
                        queries_to_search.append((translated, target_lang))
                        logger.logger.info(f"Added cross-lingual query ({target_lang}): {translated[:50]}...")
        elif cross_lingual:
            logger.logger.info("Translation unavailable - using semantic embeddings for cross-lingual search")
        
        # Stage 1: Initial retrieval per modality with all query variants
        all_results = []
        seen_ids = set()  # Track seen document IDs to avoid duplicates
        
        for search_query, search_lang in queries_to_search:
            for modality in modalities:
                # Get modality-specific embedding
                query_embedding = self.embedding_manager.embed_query(search_query, modality)
                
                # Query vector store
                results = self.vector_store.query(
                    query_embedding=query_embedding,
                    n_results=top_k,
                    modality_filter=modality
                )
                
                # Convert to EvidenceSource objects
                for i, (doc_id, document, metadata, distance) in enumerate(zip(
                    results['ids'][0],
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Skip if already seen
                    if doc_id in seen_ids:
                        continue
                    seen_ids.add(doc_id)
                    
                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    similarity = 1 / (1 + distance)
                    
                    # Boost if query language matches document language
                    doc_lang = metadata.get('language', 'en')
                    if doc_lang == search_lang:
                        similarity *= 1.1  # 10% boost for same language
                    
                    source = EvidenceSource(
                        source_id=doc_id,
                        source_file=metadata.get('source_file', 'unknown'),
                        modality=Modality(metadata.get('modality', 'text')),
                        content=document,
                        relevance_score=similarity,
                        confidence=float(metadata.get('confidence', 0.5)),
                        metadata={
                            **metadata,
                            'matched_query_language': search_lang,
                            'cross_lingual_match': search_lang != query_lang
                        }
                    )
                    all_results.append(source)
        
        # Stage 2: Cross-modal alignment scoring
        if len(modalities) > 1:
            all_results = self._apply_cross_modal_scoring(all_results)
        
        # Stage 3: Re-rank and deduplicate
        final_results = self._rerank_and_deduplicate(all_results, top_k)
        
        # Log language distribution
        langs_found = set()
        for r in final_results:
            lang = r.metadata.get('language', 'unknown')
            langs_found.add(lang)
        
        logger.logger.info(
            f"Retrieved {len(final_results)} results across "
            f"{len(set(r.modality for r in final_results))} modalities, "
            f"languages: {', '.join(langs_found)}"
        )
        
        return final_results

    
    def _apply_cross_modal_scoring(self, results: List[EvidenceSource]) -> List[EvidenceSource]:
        """Boost scores for chunks with cross-modal support and keyword matches."""
        # 1. Boost based on keyword matches (Hybrid Search Lite)
        for result in results:
            if hasattr(self, 'query_text'):  # Check based on saved query
                query_terms = [t.lower() for t in self.query_text.split() if len(t) > 3]
                matches = sum(1 for term in query_terms if term in result.content.lower())
                if matches > 0:
                    # Boost score if keywords are present in the text
                    keyword_boost = 1.0 + (0.1 * matches)  # 10% boost per matching term
                    result.relevance_score *= min(keyword_boost, 1.5)  # Cap boost at 50%
                    result.metadata['keyword_boost'] = True

        # 2. Group by source file
        by_source = {}
        for result in results:
            if result.source_file not in by_source:
                by_source[result.source_file] = []
            by_source[result.source_file].append(result)
        
        # 3. Boost scores for files with multiple modalities
        for source_file, chunks in by_source.items():
            unique_modalities = set(c.modality for c in chunks)
            if len(unique_modalities) > 1:
                # Cross-modal agreement: boost all chunks from this source
                boost = 1.2
                for chunk in chunks:
                    chunk.relevance_score *= boost
                    chunk.metadata['cross_modal_boost'] = True
        
        return results
    
    def _rerank_and_deduplicate(
        self, 
        results: List[EvidenceSource], 
        top_k: int
    ) -> List[EvidenceSource]:
        """Re-rank results and remove near-duplicates."""
        # Sort by combined score (relevance * confidence)
        results.sort(
            key=lambda x: x.relevance_score * x.confidence,
            reverse=True
        )
        
        # Remove duplicates based on content similarity
        unique_results = []
        seen_content = []
        
        for result in results:
            # Check if content is too similar to already selected results
            is_duplicate = False
            for seen in seen_content:
                if self._content_similarity(result.content, seen) > 0.9:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
                seen_content.append(result.content)
            
            if len(unique_results) >= top_k:
                break
        
        return unique_results
    
    def _content_similarity(self, text1: str, text2: str) -> float:
        """Simple content similarity based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
