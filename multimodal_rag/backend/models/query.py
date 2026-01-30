"""Data models for query and response."""
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
from .document import Modality


class ResponsePersona(str, Enum):
    """Response style personas for different audiences."""
    ACADEMIC = "academic"        # Formal, citation-heavy, detailed
    EXECUTIVE = "executive"      # Brief bullet points, key takeaways
    ELI5 = "eli5"               # Simple language for beginners
    TECHNICAL = "technical"      # Deep-dive with code/formulas
    DEBATE = "debate"           # Present all conflicting viewpoints side-by-side
    LEGAL = "legal"             # Formal legal language with disclaimers
    MEDICAL = "medical"         # Clinical language with safety caveats
    CREATIVE = "creative"       # Engaging, storytelling style
    STANDARD = "standard"       # Default balanced response


class ReasoningStepType(str, Enum):
    """Types of reasoning steps in the RAG pipeline."""
    QUERY_ANALYSIS = "query_analysis"
    RETRIEVAL = "retrieval"
    CONFIDENCE_ASSESSMENT = "confidence_assessment"
    CONFLICT_DETECTION = "conflict_detection"
    RESPONSE_STRATEGY = "response_strategy"
    GENERATION = "generation"


# ============================================
# Conversation Memory & Context Models
# ============================================

class ConversationMessage(BaseModel):
    """A single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    query_id: Optional[str] = None
    entities_mentioned: List[str] = Field(default_factory=list)


class TrackedEntity(BaseModel):
    """An entity tracked across the conversation."""
    name: str                      # Canonical name (e.g., "XYZ-500 Machine")
    aliases: List[str] = Field(default_factory=list)  # Other references (e.g., "the machine", "it")
    entity_type: str = "unknown"   # machine, document, person, concept, value
    first_mentioned: str           # Query where first introduced
    last_mentioned: str            # Most recent query referencing it
    attributes: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"voltage": "220V"}


class ConversationContext(BaseModel):
    """Session-level conversation context for semantic memory."""
    session_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    entities: List[TrackedEntity] = Field(default_factory=list)
    current_topic: Optional[str] = None
    created_at: str = ""
    last_updated: str = ""
    
    def get_recent_context(self, n_messages: int = 3) -> str:
        """Get recent conversation as context string."""
        recent = self.messages[-n_messages:] if len(self.messages) > n_messages else self.messages
        context_parts = []
        for msg in recent:
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content[:200]}")
        return "\n".join(context_parts)
    
    def find_entity(self, reference: str) -> Optional[TrackedEntity]:
        """Find an entity by name or alias."""
        reference_lower = reference.lower()
        for entity in self.entities:
            if entity.name.lower() == reference_lower:
                return entity
            if any(alias.lower() == reference_lower for alias in entity.aliases):
                return entity
        return None



class SourceReference(BaseModel):
    """Reference to a specific source chunk for traceability."""
    source_id: str
    source_file: str
    content_snippet: str  # First 200 chars
    relevance_score: float
    modality: str


class ReasoningStep(BaseModel):
    """A single step in the reasoning chain."""
    step_number: int
    step_type: ReasoningStepType
    title: str
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    sources_used: List[SourceReference] = Field(default_factory=list)
    duration_ms: float = 0
    status: str = "completed"  # completed, warning, error


class ReasoningChain(BaseModel):
    """Complete reasoning chain showing how an answer was derived."""
    chain_id: str
    query: str
    timestamp: str
    total_duration_ms: float
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_decision: str  # "answered", "refused", "conflict_presented"
    key_insights: List[str] = Field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Export reasoning chain as markdown documentation."""
        md = f"""# Reasoning Chain Report

**Query:** {self.query}
**Timestamp:** {self.timestamp}
**Total Processing Time:** {self.total_duration_ms:.2f}ms
**Final Decision:** {self.final_decision}

---

## Pipeline Steps

"""
        for step in self.steps:
            status_icon = "✅" if step.status == "completed" else "⚠️" if step.status == "warning" else "❌"
            md += f"""### Step {step.step_number}: {step.title} {status_icon}

**Type:** {step.step_type.value}
**Duration:** {step.duration_ms:.2f}ms

{step.description}

"""
            if step.details:
                md += "**Details:**\n"
                for key, value in step.details.items():
                    md += f"- {key}: {value}\n"
                md += "\n"
            
            if step.sources_used:
                md += "**Sources Referenced:**\n"
                for src in step.sources_used:
                    md += f"- [{src.source_file}] (relevance: {src.relevance_score:.2f}): \"{src.content_snippet[:100]}...\"\n"
                md += "\n"
            
            md += "---\n\n"
        
        if self.key_insights:
            md += "## Key Insights\n\n"
            for insight in self.key_insights:
                md += f"- {insight}\n"
        
        return md


class WebSource(BaseModel):
    """Represents a web search result source."""
    title: str
    url: str
    snippet: str
    source_name: str  # e.g., "Wikipedia", "BBC News"
    timestamp: Optional[str] = None
    relevance_score: float = 0.5
    credibility_score: float = 0.5  # Trust level of the source (0.0 - 1.0)



class QueryRequest(BaseModel):
    """Request model for user queries."""
    query: str
    top_k: Optional[int] = None
    modalities: Optional[List[Modality]] = None
    persona: ResponsePersona = ResponsePersona.STANDARD
    include_reasoning_chain: bool = True  # Whether to return detailed reasoning
    session_id: Optional[str] = None  # Session ID for conversation context
    enable_web_search: bool = False  # Enable live web search integration
    web_results_count: int = 3  # Number of web results to fetch
    enable_auto_translate: bool = True  # Auto-translate query and response
    target_language: Optional[str] = None  # Force specific output language (e.g., 'hi', 'es', 'fr')
    
    class Config:
        use_enum_values = True


class EvidenceSource(BaseModel):
    """Represents a single source of evidence."""
    source_id: str
    source_file: str
    modality: Modality
    content: str
    relevance_score: float
    confidence: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConflictInfo(BaseModel):
    """Information about detected conflicts."""
    conflicting_sources: List[str]
    description: str
    perspectives: List[Dict[str, str]]


class SuggestionType(str, Enum):
    """Types of follow-up suggestions."""
    RELATED_QUESTION = "related_question"      # Follow-up questions
    KNOWLEDGE_GAP = "knowledge_gap"            # Missing info suggestions
    DEEP_DIVE = "deep_dive"                    # Explore conflicts/details
    CROSS_MODAL = "cross_modal"                # Explore other modalities


class FollowUpSuggestion(BaseModel):
    """A single follow-up suggestion."""
    suggestion_type: SuggestionType
    text: str                                  # Display text
    query: Optional[str] = None               # Pre-filled query if clicked
    icon: str = "💡"                          # Display icon
    priority: int = 1                         # 1=high, 3=low


class SmartSuggestions(BaseModel):
    """Collection of smart follow-up suggestions."""
    related_questions: List[FollowUpSuggestion] = Field(default_factory=list)
    knowledge_gaps: List[FollowUpSuggestion] = Field(default_factory=list)
    deep_dives: List[FollowUpSuggestion] = Field(default_factory=list)
    cross_modal: List[FollowUpSuggestion] = Field(default_factory=list)
    
    def all_suggestions(self) -> List[FollowUpSuggestion]:
        """Get all suggestions sorted by priority."""
        all_items = (
            self.related_questions + 
            self.knowledge_gaps + 
            self.deep_dives + 
            self.cross_modal
        )
        return sorted(all_items, key=lambda x: x.priority)


class ConfidenceFactor(BaseModel):
    """Individual factor contributing to confidence score."""
    name: str                    # Factor name
    score: float                 # 0.0 to 1.0
    weight: float                # How much this factor matters (0.0 to 1.0)
    description: str             # Human readable explanation
    icon: str = "📊"            # Display icon


class ConfidenceBreakdown(BaseModel):
    """Detailed breakdown of how confidence score was calculated."""
    overall_score: float                             # Final confidence score
    overall_label: str                               # "High", "Medium", "Low"
    factors: List[ConfidenceFactor] = Field(default_factory=list)
    actionable_tips: List[str] = Field(default_factory=list)
    strongest_factor: Optional[str] = None           # What's helping most
    weakest_factor: Optional[str] = None             # What needs improvement


class QueryResponse(BaseModel):
    """Response model for queries."""
    query: str
    answer: str
    confidence: str  # "High", "Medium", "Low"
    confidence_score: float
    sources: List[EvidenceSource]
    conflicts: Optional[ConflictInfo] = None
    refusal_reason: Optional[str] = None
    retrieval_iterations: int = 1
    processing_time: float
    persona: str = "standard"  # Response style used
    reasoning_chain: Optional[ReasoningChain] = None  # Full reasoning trace
    suggestions: Optional[SmartSuggestions] = None  # Smart follow-up suggestions
    confidence_breakdown: Optional[ConfidenceBreakdown] = None  # Explainability
    # Conversation Context
    session_id: Optional[str] = None
    resolved_query: Optional[str] = None  # Query after resolving references
    entities_found: List[str] = Field(default_factory=list)  # Entities extracted
    context_used: bool = False  # Whether conversation context was used
    # Web Search Integration
    web_sources: List[WebSource] = Field(default_factory=list)  # Live web search results
    web_search_enabled: bool = False  # Whether web search was used
    # Auto-Translation Support
    translation_info: Optional[Dict[str, Any]] = None  # Translation metadata


