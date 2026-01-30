"""Smart Email/Report Drafter using knowledge base context."""
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from backend.retrieval.cross_modal_retriever import CrossModalRetriever
from backend.generation.llm_client import LLMClient
from backend.config import settings
from backend.utils.logger import logger


class DocumentType(str, Enum):
    """Type of document to draft."""
    EMAIL = "email"
    REPORT = "report"
    MEMO = "memo"
    SUMMARY = "summary"
    LETTER = "letter"


class DraftTone(str, Enum):
    """Tone of the drafted document."""
    FORMAL = "formal"
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    URGENT = "urgent"
    APOLOGETIC = "apologetic"
    CONFIDENT = "confident"


class SourceContext(BaseModel):
    """Context from a retrieved source."""
    source_file: str
    content: str
    page_reference: Optional[str] = None
    relevance_score: float = 0.0


class DraftRequest(BaseModel):
    """Request model for drafting documents."""
    communication_goal: str  # What the user wants to communicate
    document_type: DocumentType = DocumentType.EMAIL
    tone: DraftTone = DraftTone.PROFESSIONAL
    recipient: Optional[str] = None  # e.g., "client", "manager", "team"
    source_documents: List[str] = Field(default_factory=list)  # Specific docs to reference
    include_sources: bool = True  # Include page/source references
    sender_name: Optional[str] = None
    additional_context: Optional[str] = None  # Extra info to include
    max_length: Optional[int] = None  # Approximate word limit


class DraftResponse(BaseModel):
    """Response model for drafted documents."""
    draft_id: str
    document_type: str
    subject: Optional[str] = None  # For emails
    title: Optional[str] = None  # For reports
    body: str
    sources_used: List[SourceContext] = Field(default_factory=list)
    tone: str
    word_count: int
    processing_time: float
    suggestions: List[str] = Field(default_factory=list)  # Improvement suggestions


class EmailDrafter:
    """Smart email and report drafter using RAG context."""
    
    DOCUMENT_TEMPLATES = {
        "email": {
            "structure": ["subject", "greeting", "opening", "body", "closing", "signature"],
            "max_tokens": 600
        },
        "report": {
            "structure": ["title", "executive_summary", "findings", "recommendations", "conclusion"],
            "max_tokens": 1000
        },
        "memo": {
            "structure": ["header", "purpose", "background", "key_points", "action_items"],
            "max_tokens": 500
        },
        "summary": {
            "structure": ["overview", "key_points", "conclusion"],
            "max_tokens": 400
        },
        "letter": {
            "structure": ["date", "greeting", "opening", "body", "closing", "signature"],
            "max_tokens": 700
        }
    }
    
    TONE_PROMPTS = {
        "formal": "Use formal, professional language. Avoid contractions and casual phrases.",
        "professional": "Use clear, professional language. Be direct but polite.",
        "friendly": "Use warm, approachable language. Be personable but professional.",
        "urgent": "Convey urgency clearly. Be direct and action-oriented.",
        "apologetic": "Express sincere apology. Be humble and solution-focused.",
        "confident": "Use confident, assertive language. Be clear and decisive."
    }
    
    def __init__(self, retriever: CrossModalRetriever):
        self.retriever = retriever
        self.llm_client = LLMClient()
    
    async def draft_document(self, request: DraftRequest) -> DraftResponse:
        """Generate a professional document draft using knowledge base context."""
        start_time = time.time()
        draft_id = str(uuid.uuid4())[:8]
        
        # Step 1: Retrieve relevant context from knowledge base
        sources = await self._retrieve_context(
            request.communication_goal,
            request.source_documents
        )
        
        # Step 2: Build the prompt
        prompt = self._build_draft_prompt(request, sources)
        
        # Step 3: Generate the draft
        template = self.DOCUMENT_TEMPLATES.get(
            request.document_type.value, 
            self.DOCUMENT_TEMPLATES["email"]
        )
        max_tokens = request.max_length * 2 if request.max_length else template["max_tokens"]
        
        try:
            draft_content = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.4  # Balanced creativity vs consistency
            )
        except Exception as e:
            logger.logger.error(f"Draft generation error: {e}")
            draft_content = self._generate_fallback_draft(request, sources)
        
        # Step 4: Parse the generated content
        parsed = self._parse_draft(draft_content, request.document_type)
        
        # Step 5: Create source contexts
        source_contexts = []
        for s in sources[:5]:  # Limit to top 5 sources
            page_ref = s.metadata.get("page", s.metadata.get("chunk_index", ""))
            source_contexts.append(SourceContext(
                source_file=s.source_file,
                content=s.content[:200] + "..." if len(s.content) > 200 else s.content,
                page_reference=f"page {page_ref}" if page_ref else None,
                relevance_score=s.relevance_score
            ))
        
        # Step 6: Generate improvement suggestions
        suggestions = self._generate_suggestions(parsed, request, sources)
        
        processing_time = time.time() - start_time
        
        return DraftResponse(
            draft_id=draft_id,
            document_type=request.document_type.value,
            subject=parsed.get("subject"),
            title=parsed.get("title"),
            body=parsed.get("body", draft_content),
            sources_used=source_contexts,
            tone=request.tone.value,
            word_count=len(parsed.get("body", draft_content).split()),
            processing_time=processing_time,
            suggestions=suggestions
        )
    
    async def _retrieve_context(
        self, 
        goal: str, 
        specific_docs: List[str]
    ) -> List:
        """Retrieve relevant context from knowledge base."""
        try:
            # Retrieve based on communication goal
            sources = self.retriever.retrieve(
                query=goal,
                top_k=10
            )
            
            # If specific documents mentioned, prioritize them
            if specific_docs:
                specific_matches = []
                other_matches = []
                
                for source in sources:
                    source_lower = source.source_file.lower()
                    if any(doc.lower() in source_lower for doc in specific_docs):
                        specific_matches.append(source)
                    else:
                        other_matches.append(source)
                
                # Prioritize specific document matches
                sources = specific_matches + other_matches
            
            return sources
        except Exception as e:
            logger.logger.error(f"Context retrieval error: {e}")
            return []
    
    def _build_draft_prompt(
        self, 
        request: DraftRequest, 
        sources: List
    ) -> str:
        """Build the prompt for document generation."""
        template = self.DOCUMENT_TEMPLATES.get(
            request.document_type.value,
            self.DOCUMENT_TEMPLATES["email"]
        )
        structure = template["structure"]
        tone_instruction = self.TONE_PROMPTS.get(
            request.tone.value,
            self.TONE_PROMPTS["professional"]
        )
        
        # Build evidence section
        evidence_parts = []
        for i, source in enumerate(sources[:5], 1):
            page_info = ""
            if "page" in source.metadata:
                page_info = f" (page {source.metadata['page']})"
            elif "chunk_index" in source.metadata:
                page_info = f" (section {source.metadata['chunk_index']})"
            
            evidence_parts.append(
                f"[Source {i}: {source.source_file}{page_info}]\n"
                f"{source.content[:400]}"
            )
        
        evidence_text = "\n\n".join(evidence_parts) if evidence_parts else "No specific evidence available."
        
        # Determine document-specific instructions
        if request.document_type == DocumentType.EMAIL:
            format_instructions = """
Generate a professional email with:
- Subject line (on its own line, starting with "Subject:")
- Appropriate greeting
- Clear body paragraphs
- Professional closing
- Signature placeholder [Name]

Include source references in parentheses where relevant, e.g., (ref: document.pdf, page 5)
"""
        elif request.document_type == DocumentType.REPORT:
            format_instructions = """
Generate a formal report with:
- Title (on its own line, starting with "Title:")
- Executive Summary section
- Key Findings (with numbered points)
- Recommendations
- Conclusion

Include source citations where relevant, e.g., (Source: document.pdf, page 5)
"""
        elif request.document_type == DocumentType.MEMO:
            format_instructions = """
Generate a professional memo with:
- TO: [Recipient]
- FROM: [Sender]
- DATE: [Current Date]
- RE: [Subject]
- Body with clear sections

Include source references where relevant.
"""
        elif request.document_type == DocumentType.SUMMARY:
            format_instructions = """
Generate a concise summary with:
- Key Points (bulleted list)
- Brief overview paragraph
- Action items if applicable

Include source references where relevant.
"""
        else:  # LETTER
            format_instructions = """
Generate a formal letter with:
- Date
- Recipient address placeholder
- Greeting
- Body paragraphs
- Closing
- Signature

Include source references where relevant.
"""
        
        # Build recipient info
        recipient_info = ""
        if request.recipient:
            recipient_info = f"\nRecipient: {request.recipient}"
        
        # Build sender info
        sender_info = ""
        if request.sender_name:
            sender_info = f"\nSender Name: {request.sender_name}"
        
        # Build additional context
        additional_info = ""
        if request.additional_context:
            additional_info = f"\nAdditional Context: {request.additional_context}"
        
        prompt = f"""You are a professional document drafter. Create a {request.document_type.value} based on the following information.

COMMUNICATION GOAL:
{request.communication_goal}
{recipient_info}{sender_info}{additional_info}

TONE REQUIREMENT:
{tone_instruction}

EVIDENCE FROM KNOWLEDGE BASE:
{evidence_text}

{format_instructions}

IMPORTANT:
1. Use the evidence provided to support your message
2. Include specific references (source file, page) where you cite information
3. Maintain the {request.tone.value} tone throughout
4. Be clear, concise, and professional
5. If evidence is lacking, note what information might be helpful to include

Generate the {request.document_type.value} now:"""
        
        return prompt
    
    def _parse_draft(self, content: str, doc_type: DocumentType) -> Dict[str, str]:
        """Parse the generated draft into components."""
        result = {"body": content}
        
        lines = content.strip().split("\n")
        body_start = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Extract subject/title
            if line_lower.startswith("subject:"):
                result["subject"] = line[8:].strip()
                body_start = i + 1
            elif line_lower.startswith("title:"):
                result["title"] = line[6:].strip()
                body_start = i + 1
            elif line_lower.startswith("re:"):
                result["subject"] = line[3:].strip()
                body_start = i + 1
        
        # Get remaining body
        if body_start > 0:
            result["body"] = "\n".join(lines[body_start:]).strip()
        
        return result
    
    def _generate_suggestions(
        self, 
        parsed: Dict[str, str], 
        request: DraftRequest,
        sources: List
    ) -> List[str]:
        """Generate improvement suggestions for the draft."""
        suggestions = []
        body = parsed.get("body", "")
        
        # Check source citations
        if request.include_sources and sources:
            ref_count = body.lower().count("ref:") + body.lower().count("source:")
            if ref_count < min(len(sources), 3):
                suggestions.append(
                    "💡 Consider adding more source references to strengthen credibility"
                )
        
        # Check word count
        word_count = len(body.split())
        if request.document_type == DocumentType.EMAIL:
            if word_count > 300:
                suggestions.append(
                    "✂️ Consider shortening the email for better readability"
                )
            elif word_count < 50:
                suggestions.append(
                    "📝 Consider adding more detail to fully convey your message"
                )
        
        # Check for action items
        if request.document_type in [DocumentType.REPORT, DocumentType.MEMO]:
            action_keywords = ["next steps", "action", "recommend", "should", "need to"]
            if not any(kw in body.lower() for kw in action_keywords):
                suggestions.append(
                    "✅ Consider adding clear action items or recommendations"
                )
        
        # Check tone consistency
        if request.tone == DraftTone.URGENT:
            urgent_words = ["immediately", "urgent", "asap", "priority", "critical"]
            if not any(word in body.lower() for word in urgent_words):
                suggestions.append(
                    "⚡ Consider emphasizing urgency more clearly"
                )
        
        # Suggest personalization
        if "[" in body and "]" in body:
            suggestions.append(
                "📋 Remember to fill in placeholders marked with [brackets]"
            )
        
        return suggestions
    
    def _generate_fallback_draft(
        self, 
        request: DraftRequest, 
        sources: List
    ) -> str:
        """Generate a basic fallback draft if LLM fails."""
        if request.document_type == DocumentType.EMAIL:
            source_refs = ""
            if sources:
                refs = [f"- {s.source_file}" for s in sources[:3]]
                source_refs = "\n\nReferences:\n" + "\n".join(refs)
            
            return f"""Subject: {request.communication_goal[:50]}...

Dear [Recipient],

{request.communication_goal}

{request.additional_context or ''}
{source_refs}

Best regards,
{request.sender_name or '[Your Name]'}"""
        
        else:  # Generic fallback
            return f"""Title: {request.communication_goal[:50]}

{request.communication_goal}

{request.additional_context or ''}

---
Note: This is a basic draft. Please enhance with specific details from your knowledge base."""
