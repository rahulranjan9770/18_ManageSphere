"""Main RAG generator coordinating retrieval and generation."""
import time
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from backend.models.query import (
    QueryRequest, QueryResponse, EvidenceSource, ResponsePersona,
    ReasoningChain, ReasoningStep, ReasoningStepType, SourceReference,
    SmartSuggestions, FollowUpSuggestion, SuggestionType, ConflictInfo,
    ConfidenceBreakdown, ConfidenceFactor, WebSource
)
from backend.retrieval.cross_modal_retriever import CrossModalRetriever
from backend.generation.confidence_scorer import ConfidenceScorer
from backend.generation.conflict_detector import ConflictDetector
from backend.generation.llm_client import LLMClient
from backend.memory.conversation_memory import conversation_memory
from backend.web.web_search import web_search_service, WebSearchResult
from backend.config import settings
from backend.utils.logger import logger
from backend.utils.language_service import language_service, detect_language, get_language_info


class RAGGenerator:
    """Main RAG pipeline: retrieve, assess, generate."""
    
    # Persona-specific configurations
    PERSONA_CONFIGS = {
        "academic": {
            "max_tokens": 600,
            "temperature": 0.2,
            "description": "Academic/Formal"
        },
        "executive": {
            "max_tokens": 200,
            "temperature": 0.1,
            "description": "Executive Summary"
        },
        "eli5": {
            "max_tokens": 400,
            "temperature": 0.4,
            "description": "Simple (ELI5)"
        },
        "technical": {
            "max_tokens": 700,
            "temperature": 0.2,
            "description": "Technical Deep-Dive"
        },
        "debate": {
            "max_tokens": 500,
            "temperature": 0.3,
            "description": "Debate Mode"
        },
        "legal": {
            "max_tokens": 600,
            "temperature": 0.1,
            "description": "Legal/Formal"
        },
        "medical": {
            "max_tokens": 500,
            "temperature": 0.15,
            "description": "Medical/Clinical"
        },
        "creative": {
            "max_tokens": 600,
            "temperature": 0.6,
            "description": "Creative/Storytelling"
        },
        "standard": {
            "max_tokens": 500,
            "temperature": 0.3,
            "description": "Standard"
        }
    }
    
    def __init__(self, retriever: CrossModalRetriever):
        self.retriever = retriever
        self.confidence_scorer = ConfidenceScorer(settings.confidence_threshold)
        self.conflict_detector = ConflictDetector()
        self.llm_client = LLMClient()
    
    def _create_source_references(self, sources: List[EvidenceSource]) -> List[SourceReference]:
        """Create source references for reasoning chain."""
        return [
            SourceReference(
                source_id=s.source_id,
                source_file=s.source_file,
                content_snippet=s.content[:200] if s.content else "",
                relevance_score=s.relevance_score,
                modality=s.modality.value if hasattr(s.modality, 'value') else str(s.modality)
            )
            for s in sources[:5]  # Limit to top 5 for chain
        ]
    
    async def generate_response(self, request: QueryRequest) -> QueryResponse:
        """Generate evidence-based response to query with full reasoning chain."""
        pipeline_start = time.time()
        chain_id = str(uuid.uuid4())[:8]
        reasoning_steps = []
        key_insights = []
        step_num = 0
        
        # Get persona from request (default to standard)
        persona = getattr(request, 'persona', 'standard')
        if persona is None:
            persona = 'standard'
        
        include_chain = getattr(request, 'include_reasoning_chain', True)
        
        # ============ AUTO-TRANSLATION DETECTION ============
        enable_auto_translate = getattr(request, 'enable_auto_translate', True)
        target_language = getattr(request, 'target_language', None)  # User can force language
        translation_info = None
        original_query = request.query
        query_for_retrieval = request.query
        detected_lang_code = 'en'
        detected_lang_name = 'English'
        needs_translation = False
        forced_language = False
        
        if enable_auto_translate:
            # Detect language of query
            detected_lang_code, confidence = detect_language(request.query)
            lang_info = get_language_info(detected_lang_code)
            detected_lang_name = lang_info['name']
            
            # Check if user forced a specific target language
            if target_language:
                forced_language = True
                target_lang_info = get_language_info(target_language)
                logger.logger.info(f"🎯 User forced output language: {target_lang_info['flag']} {target_lang_info['name']}")
                key_insights.append(f"🎯 Output language forced: {target_lang_info['flag']} {target_lang_info['name']}")
                
                # Always translate response to target language (even if query is in that language)
                needs_translation = True
                detected_lang_code = target_language  # Use forced language for response
                detected_lang_name = target_lang_info['name']
            
            # Check if translation is needed (non-English query) - only if not forced
            if not forced_language and detected_lang_code != 'en' and confidence > 0.5:
                needs_translation = True
                logger.logger.info(f"🌍 Detected {detected_lang_name} query (confidence: {confidence:.2f})")
                key_insights.append(f"🌍 Query language detected: {lang_info['flag']} {detected_lang_name}")
            
            # Determine target language name for generation
            generation_language = detected_lang_name if (forced_language or needs_translation) else "English"

            
            # Translate query to English for retrieval (if not already English)
            if needs_translation or (forced_language and detected_lang_code != 'en'):
                # Detect actual query language for translation
                actual_query_lang = detect_language(request.query)[0] if forced_language else detected_lang_code
                
                if actual_query_lang != 'en':
                    translated_query = language_service.translate(
                        request.query,
                        source_lang=actual_query_lang,
                        target_lang='en'
                    )
                    
                    if translated_query:
                        query_for_retrieval = translated_query
                        logger.logger.info(f"🔄 Translated query: '{original_query}' → '{query_for_retrieval}'")
                        key_insights.append(f"🔄 Translated to English for retrieval")
                    else:
                        logger.logger.warning("Translation failed, using original query")
            
            # Store translation metadata
            translation_info = {
                'detected_language': detected_lang_code,
                'detected_language_name': detected_lang_name,
                'detected_language_flag': lang_info['flag'] if not forced_language else get_language_info(detected_lang_code)['flag'],
                'confidence': round(confidence, 3),
                'needs_translation': needs_translation,
                'original_query': original_query,
                'translated_query': query_for_retrieval if query_for_retrieval != original_query else None,
                'forced_language': forced_language,
                'target_language': target_language
            }
        
        # ============ CONVERSATION CONTEXT RESOLUTION ============
        session_id = getattr(request, 'session_id', None)
        resolved_query = query_for_retrieval
        context_used = False
        entities_found = []
        
        if session_id:
            # Get or create session
            context = conversation_memory.get_or_create_session(session_id)
            
            # Check if query needs context resolution
            if conversation_memory.needs_context_resolution(query_for_retrieval):
                resolved_query, context_used = conversation_memory.resolve_references(
                    session_id, query_for_retrieval
                )
                if context_used:
                    key_insights.append(f"🧠 Used conversation context to resolve: '{query_for_retrieval}' → '{resolved_query}'")
            
            # Add user message to history (use original query in user's language)
            conversation_memory.add_message(session_id, "user", original_query)
        
        # Use resolved query for retrieval
        search_query = resolved_query
        
        # ============ STEP 1: Query Analysis ============
        step_num += 1
        step_start = time.time()
        
        # Analyze query characteristics
        query_lower = search_query.lower()
        detected_intents = []
        if any(kw in query_lower for kw in ['what', 'explain', 'describe']):
            detected_intents.append("explanation")
        if any(kw in query_lower for kw in ['how', 'steps', 'process']):
            detected_intents.append("procedural")
        if any(kw in query_lower for kw in ['compare', 'difference', 'versus', 'vs']):
            detected_intents.append("comparison")
        if any(kw in query_lower for kw in ['why', 'reason', 'cause']):
            detected_intents.append("causal")
        if any(kw in query_lower for kw in ['image', 'diagram', 'picture', 'show']):
            detected_intents.append("visual")
        if not detected_intents:
            detected_intents.append("general")
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.QUERY_ANALYSIS,
            title="Query Analysis",
            description=f"Analyzed query to understand intent and required information types.",
            details={
                "query": request.query,
                "detected_intents": detected_intents,
                "persona_selected": persona,
                "requested_modalities": [m.value if hasattr(m, 'value') else str(m) for m in (request.modalities or [])]
            },
            duration_ms=(time.time() - step_start) * 1000,
            status="completed"
        ))
        
        # ============ STEP 2 & 2.5: Parallel Retrieval (Docs + Web) ============
        step_num += 1
        step_start_parallel = time.time()
        
        web_search_enabled = getattr(request, 'enable_web_search', False)
        web_sources: List[WebSource] = []
        
        # Define parallel tasks
        # 1. Document Retrieval (run in thread since it's likely sync)
        retrieval_task = asyncio.to_thread(
            self.retriever.retrieve,
            query=search_query,
            top_k=request.top_k,
            modalities=request.modalities
        )
        
        tasks = [retrieval_task]
        
        # 2. Web Search (async native)
        if web_search_enabled:
            web_results_count = getattr(request, 'web_results_count', 5)
            tasks.append(web_search_service.search(search_query, num_results=web_results_count))
            
        # Execute tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Unpack results
        sources = results[0]
        web_results = results[1] if web_search_enabled and len(results) > 1 else []
        
        parallel_duration = (time.time() - step_start_parallel) * 1000
        
        # --- Process Document Retrieval Results ---
        source_refs = self._create_source_references(sources)
        
        modalities_found = list(set(s.modality.value if hasattr(s.modality, 'value') else str(s.modality) for s in sources))
        avg_relevance = sum(s.relevance_score for s in sources) / len(sources) if sources else 0
        
        retrieval_status = "completed"
        if len(sources) == 0:
            retrieval_status = "warning"
            key_insights.append("⚠️ No relevant sources found in knowledge base")
        elif avg_relevance < 0.5:
            retrieval_status = "warning"
            key_insights.append(f"⚠️ Low average relevance ({avg_relevance:.2f}) - results may not be highly relevant")
        else:
            key_insights.append(f"✓ Retrieved {len(sources)} sources with avg relevance {avg_relevance:.2f}")
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.RETRIEVAL,
            title="Evidence Retrieval",
            description=f"Retrieved {len(sources)} relevant evidence chunks from the knowledge base using semantic search.",
            details={
                "sources_retrieved": len(sources),
                "modalities_found": modalities_found,
                "average_relevance": round(avg_relevance, 3),
                "top_k_requested": request.top_k or "default"
            },
            sources_used=source_refs,
            duration_ms=parallel_duration,
            status=retrieval_status
        ))
        
        # --- Process Web Search Results ---
        if web_search_enabled:
            step_num += 1
            
            for result in web_results:
                web_sources.append(WebSource(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    source_name=result.source_name,
                    timestamp=result.timestamp,
                    relevance_score=result.relevance_score,
                    credibility_score=getattr(result, 'credibility_score', 0.5)
                ))
            
            web_status = "completed" if web_sources else "warning"
            
            if web_sources:
                avg_credibility = sum(ws.credibility_score for ws in web_sources) / len(web_sources)
                credibility_label = "high" if avg_credibility >= 0.75 else ("medium" if avg_credibility >= 0.5 else "low")
                key_insights.append(f"🌐 Found {len(web_sources)} web sources ({credibility_label} credibility avg)")
            else:
                key_insights.append("🌐 Web search returned no results")
            
            reasoning_steps.append(ReasoningStep(
                step_number=step_num,
                step_type=ReasoningStepType.RETRIEVAL,
                title="Live Web Search (Parallel)",
                description=f"Searched the web in parallel with document retrieval.",
                details={
                    "web_sources_found": len(web_sources),
                    "sources": [{"title": ws.title, "source": ws.source_name, "credibility": f"{ws.credibility_score:.0%}"} for ws in web_sources[:3]],
                    "query_used": search_query,
                    "avg_credibility": f"{avg_credibility:.0%}" if web_sources else "N/A"
                },
                duration_ms=parallel_duration,
                status=web_status
            ))
        
        
        # ============ STEP 3: Confidence Assessment ============
        step_num += 1
        step_start = time.time()
        
        confidence_score, confidence_level, conf_reasoning = \
            self.confidence_scorer.score_evidence(sources)
        
        conf_status = "completed"
        if confidence_score < 0.3:
            conf_status = "error"
            key_insights.append(f"❌ Very low confidence ({confidence_score:.2f}) - refusing to answer")
        elif confidence_score < settings.confidence_threshold:
            conf_status = "warning"
            key_insights.append(f"⚠️ Moderate confidence ({confidence_score:.2f}) - will include caveats")
        else:
            key_insights.append(f"✓ High confidence ({confidence_score:.2f}) - proceeding with full answer")
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.CONFIDENCE_ASSESSMENT,
            title="Confidence Assessment",
            description=f"Evaluated evidence quality and determined confidence level: {confidence_level} ({confidence_score:.2f})",
            details={
                "confidence_score": round(confidence_score, 3),
                "confidence_level": confidence_level,
                "scoring_breakdown": conf_reasoning,
                "threshold": settings.confidence_threshold
            },
            duration_ms=(time.time() - step_start) * 1000,
            status=conf_status
        ))
        
        # ============ STEP 4: Conflict Detection ============
        step_num += 1
        step_start = time.time()
        
        conflicts = self.conflict_detector.detect_conflicts(sources)
        
        conflict_status = "completed"
        conflict_details = {"conflicts_found": False}
        
        if conflicts:
            conflict_status = "warning"
            conflict_details = {
                "conflicts_found": True,
                "num_conflicts": len(conflicts.perspectives) // 2,
                "conflicting_sources": conflicts.conflicting_sources,
                "description": conflicts.description
            }
            key_insights.append(f"⚠️ Detected conflicting information between {len(conflicts.conflicting_sources)} sources")
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.CONFLICT_DETECTION,
            title="Conflict Detection",
            description="Analyzed sources for contradictory information using semantic comparison.",
            details=conflict_details,
            duration_ms=(time.time() - step_start) * 1000,
            status=conflict_status
        ))
        
        # ============ STEP 5: Response Strategy Decision ============
        step_num += 1
        step_start = time.time()
        
        persona_config = self.PERSONA_CONFIGS.get(persona, self.PERSONA_CONFIGS["standard"])
        max_tokens = persona_config["max_tokens"]
        temperature = persona_config["temperature"]
        
        # Determine response strategy
        if confidence_score < 0.3:
            strategy = "REFUSE"
            strategy_reason = "Confidence too low to provide reliable answer"
        elif conflicts or persona == "debate":
            strategy = "CONFLICT_PRESENTATION"
            strategy_reason = "Conflicting sources detected or debate mode requested"
            max_tokens = min(max_tokens, 400)
        elif confidence_score < settings.confidence_threshold:
            strategy = "CAUTIOUS_ANSWER"
            strategy_reason = "Moderate confidence - will include uncertainty caveats"
            max_tokens = min(max_tokens, 300)
            temperature = 0.1
        else:
            strategy = "CONFIDENT_ANSWER"
            strategy_reason = "High confidence - proceeding with full response"
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.RESPONSE_STRATEGY,
            title="Response Strategy",
            description=f"Selected strategy: {strategy}. {strategy_reason}",
            details={
                "strategy": strategy,
                "reason": strategy_reason,
                "persona": persona,
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            duration_ms=(time.time() - step_start) * 1000,
            status="completed"
        ))
        
        # ============ STEP 6: Response Generation ============
        step_num += 1
        step_start = time.time()
        
        # Execute the chosen strategy
        if strategy == "REFUSE":
            gaps = self.confidence_scorer.identify_gaps(sources, request.query)
            response = self._create_refusal_response(
                request.query, sources, gaps, confidence_score,
                time.time() - pipeline_start, persona
            )
            final_decision = "refused"
            gen_description = "Generated refusal response due to insufficient evidence."
        elif strategy == "CONFLICT_PRESENTATION":
            response = await self._create_conflict_response(
                request.query, sources, conflicts, confidence_score,
                confidence_level, time.time() - pipeline_start, persona,
                max_tokens=max_tokens, temperature=temperature,
                web_sources=web_sources,
                target_language=generation_language if enable_auto_translate else None
            )
            final_decision = "conflict_presented"
            gen_description = "Generated response presenting multiple conflicting perspectives."
        elif strategy == "CAUTIOUS_ANSWER":
            response = await self._create_cautious_response(
                request.query, sources, confidence_score,
                confidence_level, time.time() - pipeline_start, persona,
                max_tokens=max_tokens, temperature=temperature,
                web_sources=web_sources,
                target_language=generation_language if enable_auto_translate else None
            )
            final_decision = "answered"
            gen_description = "Generated cautious response with uncertainty acknowledgment."
        else:  # CONFIDENT_ANSWER
            response = await self._create_confident_response(
                request.query, sources, confidence_score,
                confidence_level, time.time() - pipeline_start, persona,
                max_tokens=max_tokens, temperature=temperature,
                web_sources=web_sources,
                target_language=generation_language if enable_auto_translate else None
            )
            final_decision = "answered"
            gen_description = "Generated confident response with full citations."
        
        generation_duration = (time.time() - step_start) * 1000
        
        reasoning_steps.append(ReasoningStep(
            step_number=step_num,
            step_type=ReasoningStepType.GENERATION,
            title="Response Generation",
            description=gen_description,
            details={
                "strategy_used": strategy,
                "answer_length": len(response.answer),
                "sources_cited": len(response.sources)
            },
            sources_used=source_refs,
            duration_ms=generation_duration,
            status="completed"
        ))
        
        # ============ Build Reasoning Chain ============
        total_duration = (time.time() - pipeline_start) * 1000
        
        if include_chain:
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                query=request.query,
                timestamp=datetime.now().isoformat(),
                total_duration_ms=total_duration,
                steps=reasoning_steps,
                final_decision=final_decision,
                key_insights=key_insights
            )
            response.reasoning_chain = reasoning_chain
        
        # ============ Generate Smart Suggestions ============
        suggestions = self._generate_smart_suggestions(
            query=request.query,
            sources=sources,
            conflicts=conflicts,
            confidence_score=confidence_score,
            final_decision=final_decision
        )
        response.suggestions = suggestions
        
        # ============ Generate Confidence Breakdown ============
        confidence_breakdown = self._generate_confidence_breakdown(
            sources=sources,
            conflicts=conflicts,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            conf_reasoning=conf_reasoning
        )
        response.confidence_breakdown = confidence_breakdown
        
        # ============ Update Conversation Memory ============
        if session_id:
            # Extract entities from response
            new_entities = conversation_memory.extract_entities(response.answer, request.query)
            
            # Also extract from sources
            for source in sources[:3]:  # Top 3 sources
                source_entities = conversation_memory.extract_entities(source.content, request.query)
                new_entities.extend(source_entities)
            
            # Update tracked entities
            if new_entities:
                conversation_memory.update_entities(session_id, new_entities, request.query)
                entities_found = [e.name for e in new_entities[:5]]
            
            # Set current topic based on query
            topic_words = [w for w in request.query.split() if len(w) > 4][:3]
            if topic_words:
                conversation_memory.set_current_topic(session_id, " ".join(topic_words))
            
            # Add assistant response to history
            conversation_memory.add_message(
                session_id, "assistant", 
                response.answer[:500],
                entities=entities_found
            )
        
        # Set context fields on response
        response.session_id = session_id
        response.resolved_query = resolved_query if context_used else None
        response.entities_found = entities_found
        response.context_used = context_used
        
        # Set web search fields on response
        response.web_sources = web_sources
        response.web_search_enabled = web_search_enabled
        
        # ============ AUTO-TRANSLATE RESPONSE ============
        if enable_auto_translate and needs_translation and translation_info:
            # Translate response back to original language
            logger.logger.info(f"🔄 Translating response back to {detected_lang_name}")
            
            translated_answer = language_service.translate(
                response.answer,
                source_lang='auto',  # Use auto-detection in case LLM generated non-English
                target_lang=detected_lang_code
            )
            
            if translated_answer:
                # Update translation info with response translation
                translation_info['response_translated'] = True
                translation_info['original_answer_preview'] = response.answer[:200]
                
                # Replace answer with translated version
                response.answer = translated_answer
                logger.logger.info(f"✅ Response translated to {detected_lang_name}")
                key_insights.append(f"🔄 Response translated to {translation_info['detected_language_flag']} {detected_lang_name}")
            else:
                translation_info['response_translated'] = False
                translation_info['translation_error'] = "Response translation failed, returning in English"
                logger.logger.warning("Failed to translate response, returning in English")
        
        # Set translation metadata on response
        response.translation_info = translation_info
        
        # Update reasoning chain with final insights if translation occurred
        if include_chain and response.reasoning_chain and translation_info:
            response.reasoning_chain.key_insights = key_insights
        
        return response
    
    def _generate_smart_suggestions(
        self,
        query: str,
        sources: List[EvidenceSource],
        conflicts: ConflictInfo,
        confidence_score: float,
        final_decision: str
    ) -> SmartSuggestions:
        """Generate intelligent follow-up suggestions based on response context."""
        suggestions = SmartSuggestions()
        query_lower = query.lower()
        
        # ============ 1. Related Questions ============
        # Generate follow-up questions based on the query topic
        question_templates = [
            ("How does", "work in more detail?"),
            ("What are the benefits of", "?"),
            ("What are the limitations of", "?"),
            ("Can you compare", "with alternatives?"),
            ("What is the history of", "?"),
        ]
        
        # Extract key topic from query
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'does', 'can', 'you', 'tell', 'me', 'about', 'explain'}
        words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
        topic = ' '.join(words[:3]) if words else query
        
        # Add 2-3 related questions
        for i, (prefix, suffix) in enumerate(question_templates[:3]):
            suggestions.related_questions.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.RELATED_QUESTION,
                text=f"{prefix} {topic} {suffix}",
                query=f"{prefix} {topic} {suffix}",
                icon="❓",
                priority=2
            ))
        
        # ============ 2. Knowledge Gaps ============
        # Suggest uploads based on what's missing
        modalities_found = set(s.modality.value if hasattr(s.modality, 'value') else str(s.modality) for s in sources)
        
        if len(sources) < 3:
            suggestions.knowledge_gaps.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.KNOWLEDGE_GAP,
                text="📤 Upload more documents for a complete picture",
                query=None,
                icon="📤",
                priority=1
            ))
        
        if 'image' not in modalities_found and any(kw in query_lower for kw in ['show', 'diagram', 'visual', 'picture', 'see']):
            suggestions.knowledge_gaps.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.KNOWLEDGE_GAP,
                text="🖼️ Upload images or diagrams for visual context",
                query=None,
                icon="🖼️",
                priority=1
            ))
        
        if 'audio' not in modalities_found and any(kw in query_lower for kw in ['said', 'mentioned', 'discussed', 'meeting', 'call']):
            suggestions.knowledge_gaps.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.KNOWLEDGE_GAP,
                text="🎙️ Upload audio recordings for spoken content",
                query=None,
                icon="🎙️",
                priority=1
            ))
        
        if confidence_score < 0.6:
            suggestions.knowledge_gaps.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.KNOWLEDGE_GAP,
                text="📚 Add more relevant documents to improve confidence",
                query=None,
                icon="📚",
                priority=1
            ))
        
        # ============ 3. Deep-Dive Prompts ============
        # Suggest exploring conflicts or details
        if conflicts and conflicts.perspectives:
            source_names = []
            for p in conflicts.perspectives[:2]:
                if 'source' in p:
                    name = p['source'].split('/')[-1].split('\\')[-1][:30]
                    source_names.append(name)
            
            if len(source_names) >= 2:
                suggestions.deep_dives.append(FollowUpSuggestion(
                    suggestion_type=SuggestionType.DEEP_DIVE,
                    text=f"⚔️ Explain the conflict between {source_names[0]} and {source_names[1]}",
                    query=f"Explain the contradiction between the sources regarding {topic}",
                    icon="⚔️",
                    priority=1
                ))
            
            suggestions.deep_dives.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.DEEP_DIVE,
                text="🔍 Which source is more reliable for this topic?",
                query=f"Which source is more reliable regarding {topic}?",
                icon="🔍",
                priority=2
            ))
        
        # Add detail exploration
        if sources:
            suggestions.deep_dives.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.DEEP_DIVE,
                text=f"📖 Tell me more details about {topic}",
                query=f"Give me more detailed information about {topic}",
                icon="📖",
                priority=2
            ))
        
        # ============ 4. Cross-Modal Exploration ============
        # Suggest exploring other modalities
        if 'image' in modalities_found:
            suggestions.cross_modal.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.CROSS_MODAL,
                text="🖼️ There are images related to this — explore visual content",
                query=f"Show me images related to {topic}",
                icon="🖼️",
                priority=1
            ))
        
        if 'audio' in modalities_found:
            suggestions.cross_modal.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.CROSS_MODAL,
                text="🎧 Audio content available — explore spoken information",
                query=f"What was said about {topic} in audio recordings?",
                icon="🎧",
                priority=1
            ))
        
        if len(modalities_found) > 1:
            suggestions.cross_modal.append(FollowUpSuggestion(
                suggestion_type=SuggestionType.CROSS_MODAL,
                text=f"🔄 Compare information across {', '.join(modalities_found)}",
                query=f"Compare what different sources say about {topic}",
                icon="🔄",
                priority=2
            ))
        
        return suggestions
    
    def _generate_confidence_breakdown(
        self,
        sources: List[EvidenceSource],
        conflicts: ConflictInfo,
        confidence_score: float,
        confidence_level: str,
        conf_reasoning: dict
    ) -> ConfidenceBreakdown:
        """Generate detailed breakdown of confidence score factors."""
        factors = []
        tips = []
        
        # ============ Factor 1: Source Quality ============
        avg_relevance = 0.0
        if sources:
            avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
        
        source_quality_score = min(1.0, avg_relevance * 1.2)  # Boost slightly
        factors.append(ConfidenceFactor(
            name="Source Quality",
            score=round(source_quality_score, 2),
            weight=0.3,
            description=f"Average relevance of {len(sources)} sources: {avg_relevance:.0%}",
            icon="📚"
        ))
        
        if source_quality_score < 0.5:
            tips.append("📚 Upload more relevant documents to improve source quality")
        
        # ============ Factor 2: Multimodal Support ============
        modalities = set()
        for s in sources:
            mod = s.modality.value if hasattr(s.modality, 'value') else str(s.modality)
            modalities.add(mod)
        
        multimodal_score = min(1.0, len(modalities) / 3.0)  # 3 modalities = 100%
        factors.append(ConfidenceFactor(
            name="Multimodal Support",
            score=round(multimodal_score, 2),
            weight=0.2,
            description=f"Evidence from {len(modalities)} modalities: {', '.join(modalities) if modalities else 'none'}",
            icon="🔄"
        ))
        
        if 'image' not in modalities:
            tips.append("🖼️ Upload images for visual evidence support")
        if 'audio' not in modalities:
            tips.append("🎙️ Add audio recordings for spoken context")
        
        # ============ Factor 3: Source Consistency ============
        consistency_score = 1.0 if not conflicts else 0.4
        if conflicts and conflicts.perspectives:
            consistency_score = max(0.2, 1.0 - (len(conflicts.perspectives) * 0.2))
        
        factors.append(ConfidenceFactor(
            name="Source Consistency",
            score=round(consistency_score, 2),
            weight=0.25,
            description="No conflicts detected" if not conflicts else f"Found {len(conflicts.perspectives) if conflicts else 0} conflicting perspectives",
            icon="⚖️"
        ))
        
        if consistency_score < 0.6:
            tips.append("⚔️ Conflicting information detected - review sources for accuracy")
        
        # ============ Factor 4: Evidence Quantity ============
        quantity_score = min(1.0, len(sources) / 5.0)  # 5+ sources = 100%
        factors.append(ConfidenceFactor(
            name="Evidence Quantity",
            score=round(quantity_score, 2),
            weight=0.15,
            description=f"{len(sources)} evidence chunks found",
            icon="📊"
        ))
        
        if quantity_score < 0.6:
            tips.append("📤 Upload more documents to increase evidence coverage")
        
        # ============ Factor 5: Keyword Coverage ============
        # Check if sources contain substantial content
        total_content_length = sum(len(s.content) for s in sources)
        coverage_score = min(1.0, total_content_length / 2000)  # 2000+ chars = good
        factors.append(ConfidenceFactor(
            name="Content Depth",
            score=round(coverage_score, 2),
            weight=0.1,
            description=f"Total evidence content: {total_content_length} characters",
            icon="📝"
        ))
        
        if coverage_score < 0.5:
            tips.append("📄 Documents may be too brief - consider adding detailed documentation")
        
        # Find strongest and weakest factors
        sorted_factors = sorted(factors, key=lambda f: f.score * f.weight, reverse=True)
        strongest = sorted_factors[0].name if sorted_factors else None
        weakest = sorted_factors[-1].name if sorted_factors else None
        
        # Limit tips
        tips = tips[:4]
        
        return ConfidenceBreakdown(
            overall_score=round(confidence_score, 2),
            overall_label=confidence_level,
            factors=factors,
            actionable_tips=tips,
            strongest_factor=strongest,
            weakest_factor=weakest
        )
    
    def _create_refusal_response(
        self,
        query: str,
        sources: List[EvidenceSource],
        gaps: List[str],
        confidence: float,
        processing_time: float,
        persona: str = "standard"
    ) -> QueryResponse:
        """Create response when confidence is too low."""
        missing_info = "; ".join(gaps)
        reason = f"Insufficient evidence to answer confidently. Issues: {missing_info}"
        
        logger.log_refusal(
            query=query,
            reason=reason,
            missing_info=missing_info
        )
        
        answer = (
            f"I cannot answer this query confidently due to insufficient evidence.\n\n"
            f"**Issues identified:**\n"
        )
        for gap in gaps:
            answer += f"- {gap}\n"
        
        answer += (
            f"\n**Suggestion:** Please upload more relevant documents or rephrase your query."
        )
        
        return QueryResponse(
            query=query,
            answer=answer,
            confidence="None",
            confidence_score=confidence,
            sources=sources,
            refusal_reason=reason,
            retrieval_iterations=1,
            processing_time=processing_time,
            persona=persona
        )
    
    async def _create_conflict_response(
        self,
        query: str,
        sources: List[EvidenceSource],
        conflicts,
        confidence: float,
        confidence_level: str,
        processing_time: float,
        persona: str = "standard",
        max_tokens: int = 400,
        temperature: float = 0.3,
        web_sources: Optional[List[WebSource]] = None,
        target_language: Optional[str] = None
    ) -> QueryResponse:
        """Create response when conflicts detected or debate mode."""
        # Build prompt based on persona with web sources
        prompt = self._build_persona_prompt(
            query, sources, persona, conflicts, 
            web_sources=web_sources, target_language=target_language
        )
        
        # Generate answer with custom parameters
        answer = await self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        
        return QueryResponse(
            query=query,
            answer=answer,
            confidence=confidence_level,
            confidence_score=confidence,
            sources=sources,
            conflicts=conflicts,
            retrieval_iterations=1,
            processing_time=processing_time,
            persona=persona
        )
    
    async def _create_cautious_response(
        self,
        query: str,
        sources: List[EvidenceSource],
        confidence: float,
        confidence_level: str,
        processing_time: float,
        persona: str = "standard",
        max_tokens: int = 300,
        temperature: float = 0.3,
        web_sources: Optional[List[WebSource]] = None,
        target_language: Optional[str] = None
    ) -> QueryResponse:
        """Create response with explicit caveats."""
        prompt = self._build_persona_prompt(
            query, sources, persona, cautious=True, 
            web_sources=web_sources, target_language=target_language
        )
        answer = await self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        
        return QueryResponse(
            query=query,
            answer=answer,
            confidence=confidence_level,
            confidence_score=confidence,
            sources=sources,
            retrieval_iterations=1,
            processing_time=processing_time,
            persona=persona
        )
    
    async def _create_confident_response(
        self,
        query: str,
        sources: List[EvidenceSource],
        confidence: float,
        confidence_level: str,
        processing_time: float,
        persona: str = "standard",
        max_tokens: int = 300,
        temperature: float = 0.3,

        web_sources: Optional[List[WebSource]] = None,
        target_language: Optional[str] = None
    ) -> QueryResponse:
        """Create high-confidence response with persona."""
        prompt = self._build_persona_prompt(
            query, sources, persona, 
            web_sources=web_sources, target_language=target_language
        )
        answer = await self.llm_client.generate(prompt, temperature=temperature, max_tokens=max_tokens)
        
        return QueryResponse(
            query=query,
            answer=answer,
            confidence=confidence_level,
            confidence_score=confidence,
            sources=sources,
            retrieval_iterations=1,
            processing_time=processing_time,
            persona=persona
        )
    
    def _build_persona_prompt(
        self, 
        query: str, 
        sources: List[EvidenceSource], 
        persona: str,
        conflicts=None,
        cautious: bool = False,
        web_sources: Optional[List[WebSource]] = None,
        target_language: Optional[str] = None
    ) -> str:
        """Build persona-specific prompt for response generation."""
        
        # Build evidence text (top 3 sources) - full context for quality
        evidence_text = "\n\n".join([
            f"[{i+1}] {source.source_file}: {source.content[:1500]}" 
            for i, source in enumerate(sources[:3])
        ])
        
        # Build web sources text if available
        web_text = ""
        if web_sources:
            web_items = [
                f"[Web {i+1}] {ws.source_name} - {ws.title}: {ws.snippet[:400]}"
                for i, ws in enumerate(web_sources[:3])
            ]
            web_text = "\n\n🌐 Live Web Results:\n" + "\n\n".join(web_items)
        
        # Persona-specific instruction suffixes
        persona_instructions = {
            "academic": """Respond in a formal academic style:
- Use precise, scholarly language with technical terminology
- Provide extensive citations [1], [2], etc. for every claim
- Include nuanced analysis and caveats
- Structure with clear thesis and supporting arguments
- Mention limitations and areas needing further research""",

            "executive": """Respond as an executive summary:
- Maximum 3-4 bullet points
- Lead with the key takeaway
- Focus on actionable insights
- No jargon - business-friendly language
- Include bottom-line recommendation""",

            "eli5": """Explain Like I'm 5 (ELI5):
- Use very simple, everyday language
- Explain concepts with relatable analogies
- Avoid all technical terms
- Short sentences, friendly tone
- Use examples a child could understand""",

            "technical": """Provide a technical deep-dive:
- Include specific data, formulas, or code if relevant
- Use precise technical terminology
- Explain underlying mechanisms
- Reference methodologies and approaches
- Be comprehensive and detailed""",

            "debate": """Present a balanced debate view:
- List ALL perspectives and viewpoints found
- Present each side's arguments clearly
- Note which sources support each position
- Highlight areas of agreement and disagreement
- Don't favor any side - let user decide""",

            "legal": """Respond in formal legal style:
- Use precise legal terminology where appropriate
- Include relevant disclaimers and caveats
- Note this is informational, not legal advice
- Reference source documents explicitly
- Be thorough but avoid unfounded claims
- End with: "This information is for educational purposes only and does not constitute legal advice." """,

            "medical": """Respond in clinical/medical style:
- Use accurate medical terminology with lay explanations
- Include appropriate safety warnings
- Emphasize consulting healthcare professionals
- Note limitations of the information provided
- Be factual and evidence-based
- Start or end with: "Consult a qualified healthcare provider for personalized medical advice." """,

            "creative": """Respond in an engaging, creative style:
- Use vivid language and storytelling techniques
- Make the information memorable and interesting
- Include relevant analogies and metaphors
- Maintain accuracy while being entertaining
- Write in an engaging, conversational tone
- Make the reader want to learn more""",

            "standard": """Answer briefly and cite sources [1], [2], etc."""
        }
        
        instruction = persona_instructions.get(persona, persona_instructions["standard"])
        
        # Add cautious prefix if needed
        cautious_note = "(Note: Limited evidence available - express appropriate uncertainty)\n" if cautious else ""
        
        # Add conflict info for debate mode
        conflict_context = ""
        if conflicts and (persona == "debate" or conflicts):
            conflict_perspectives = "\n".join([
                f"• {p['source']}: {p['claim'][:100]}"
                for p in conflicts.perspectives[:3]
            ]) if conflicts else ""
            if conflict_perspectives:
                conflict_context = f"\n\nConflicting perspectives found:\n{conflict_perspectives}"
        
        # Simplified web source instruction for speed
        web_instruction = ""
        if web_sources:
            web_instruction = "\nUse [1],[2] for docs, [Web 1],[Web 2] for web. Docs are primary; note if sources agree."
        
        # Add language instruction
        lang_instruction = ""
        if target_language and target_language != "English":
            lang_instruction = f"\nIMPORTANT: Your entire response must be in {target_language}."
        
        prompt = f"""Answer the question using the evidence below.

📁 Document Evidence:
{evidence_text}{conflict_context}
{web_text}

Question: {query}

{cautious_note}{instruction}{web_instruction}

Be concise and cite sources.
{lang_instruction}"""
        
        return prompt
    
    # Legacy prompt methods for backwards compatibility
    def _build_confident_prompt(self, query: str, sources: List[EvidenceSource]) -> str:
        """Build OPTIMIZED prompt for high-confidence generation."""
        return self._build_persona_prompt(query, sources, "standard")
    
    def _build_cautious_prompt(self, query: str, sources: List[EvidenceSource]) -> str:
        """Build OPTIMIZED prompt for moderate-confidence generation."""
        return self._build_persona_prompt(query, sources, "standard", cautious=True)
    
    def _build_conflict_prompt(self, query: str, sources: List[EvidenceSource], conflicts) -> str:
        """Build HIGHLY OPTIMIZED prompt for conflicting evidence."""
        return self._build_persona_prompt(query, sources, "debate", conflicts)
