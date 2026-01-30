"""Conversation Memory Manager for semantic memory across sessions."""
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from backend.models.query import (
    ConversationContext, ConversationMessage, TrackedEntity
)
from backend.utils.logger import logger


class ConversationMemoryManager:
    """Manages conversation context and entity tracking across sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationContext] = {}
        # Patterns for detecting references that need resolution
        self.reference_patterns = [
            (r'\b(it|this|that)\b', 'pronoun'),
            (r'\bthe (machine|device|system|document|file|image|audio)\b', 'definite_article'),
            (r'\b(other one|another|previous|same|above|mentioned)\b', 'reference'),
            (r'\bwhat about\b', 'followup'),
            (r'\b(also|too|as well)\b', 'additional'),
            (r'\bmore (about|on|regarding|details?)\b', 'continuation'),
        ]
        # Entity type patterns
        self.entity_patterns = {
            'value': r'\b(\d+(?:\.\d+)?)\s*(V|v|volt|volts|W|watts?|A|amps?|Hz|kg|lbs?|°[CF]|%|mm|cm|m)\b',
            'machine': r'\b([A-Z][A-Z0-9]+-\d+[A-Z]?)\b',  # e.g., XYZ-500
            'document': r'\b(\w+\.(pdf|docx?|txt|png|jpg|jpeg|mp3|wav))\b',
        }
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationContext:
        """Get existing session or create a new one."""
        if not session_id:
            session_id = str(uuid.uuid4())[:12]
        
        if session_id not in self.sessions:
            now = datetime.now().isoformat()
            self.sessions[session_id] = ConversationContext(
                session_id=session_id,
                created_at=now,
                last_updated=now
            )
            logger.logger.info(f"Created new conversation session: {session_id}")
        
        return self.sessions[session_id]
    
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        entities: List[str] = None
    ) -> ConversationMessage:
        """Add a message to the conversation history."""
        context = self.get_or_create_session(session_id)
        
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            query_id=str(uuid.uuid4())[:8],
            entities_mentioned=entities or []
        )
        
        context.messages.append(message)
        context.last_updated = datetime.now().isoformat()
        
        # Limit message history to last 20 messages
        if len(context.messages) > 20:
            context.messages = context.messages[-20:]
        
        return message
    
    def extract_entities(self, text: str, query: str) -> List[TrackedEntity]:
        """Extract entities from text for tracking."""
        entities = []
        text_lower = text.lower()
        
        # Extract value entities (e.g., "220V", "110 volts")
        for match in re.finditer(self.entity_patterns['value'], text, re.IGNORECASE):
            value = f"{match.group(1)}{match.group(2)}"
            entity = TrackedEntity(
                name=value,
                aliases=[value.lower(), value.upper()],
                entity_type="value",
                first_mentioned=query,
                last_mentioned=query,
                attributes={"unit": match.group(2)}
            )
            entities.append(entity)
        
        # Extract machine/model entities (e.g., "XYZ-500")
        for match in re.finditer(self.entity_patterns['machine'], text):
            model = match.group(1)
            entity = TrackedEntity(
                name=model,
                aliases=["the machine", "this device", "it", model.lower()],
                entity_type="machine",
                first_mentioned=query,
                last_mentioned=query
            )
            entities.append(entity)
        
        # Extract document references
        for match in re.finditer(self.entity_patterns['document'], text, re.IGNORECASE):
            doc_name = match.group(1)
            entity = TrackedEntity(
                name=doc_name,
                aliases=["the document", "the file", "it"],
                entity_type="document",
                first_mentioned=query,
                last_mentioned=query
            )
            entities.append(entity)
        
        return entities
    
    def update_entities(self, session_id: str, new_entities: List[TrackedEntity], query: str):
        """Update tracked entities in a session."""
        context = self.get_or_create_session(session_id)
        
        for new_entity in new_entities:
            # Check if entity already exists
            existing = context.find_entity(new_entity.name)
            if existing:
                existing.last_mentioned = query
                # Merge attributes
                existing.attributes.update(new_entity.attributes)
            else:
                context.entities.append(new_entity)
        
        # Limit entities to last 15
        if len(context.entities) > 15:
            # Keep most recently mentioned
            context.entities = sorted(
                context.entities, 
                key=lambda e: e.last_mentioned, 
                reverse=True
            )[:15]
    
    def needs_context_resolution(self, query: str) -> bool:
        """Check if query contains references that need resolution."""
        query_lower = query.lower()
        
        for pattern, _ in self.reference_patterns:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    def resolve_references(self, session_id: str, query: str) -> Tuple[str, bool]:
        """
        Resolve references in query using conversation context.
        Returns (resolved_query, was_modified).
        """
        context = self.get_or_create_session(session_id)
        
        if not context.messages or not context.entities:
            return query, False
        
        resolved_query = query
        was_modified = False
        
        # Try to resolve "the machine", "it", etc.
        query_lower = query.lower()
        
        # Handle "what about..." type follow-ups
        if "what about" in query_lower:
            # Get recent topic context
            if context.current_topic:
                # Append context
                resolved_query = f"{query} (regarding {context.current_topic})"
                was_modified = True
            elif context.entities:
                # Use most recent entity
                recent_entity = context.entities[-1]
                resolved_query = f"{query} (regarding {recent_entity.name})"
                was_modified = True
        
        # Handle pronoun references
        for entity in reversed(context.entities):  # Most recent first
            for alias in entity.aliases:
                # Create pattern that matches the alias as a whole word
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, query_lower):
                    # Replace with entity name for search context
                    resolved_query = re.sub(
                        pattern, 
                        entity.name, 
                        resolved_query, 
                        flags=re.IGNORECASE,
                        count=1  # Only replace first occurrence
                    )
                    was_modified = True
                    break  # One replacement per entity
        
        # Handle "more details" type queries
        if re.search(r'\bmore\s+(details?|info|information|about)\b', query_lower):
            if context.messages:
                # Get the last user query topic
                last_query = None
                for msg in reversed(context.messages):
                    if msg.role == "user":
                        last_query = msg.content
                        break
                
                if last_query and last_query.lower() != query_lower:
                    resolved_query = f"{query} (continuing from: {last_query[:100]})"
                    was_modified = True
        
        if was_modified:
            logger.logger.info(f"Resolved query: '{query}' -> '{resolved_query}'")
        
        return resolved_query, was_modified
    
    def get_context_summary(self, session_id: str) -> dict:
        """Get a summary of the conversation context for a session."""
        context = self.get_or_create_session(session_id)
        
        return {
            "session_id": session_id,
            "message_count": len(context.messages),
            "entity_count": len(context.entities),
            "current_topic": context.current_topic,
            "entities": [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "aliases": e.aliases[:3]
                }
                for e in context.entities[-5:]  # Last 5 entities
            ],
            "recent_queries": [
                m.content[:80] 
                for m in context.messages[-3:] 
                if m.role == "user"
            ]
        }
    
    def set_current_topic(self, session_id: str, topic: str):
        """Set the current conversation topic."""
        context = self.get_or_create_session(session_id)
        context.current_topic = topic
    
    def clear_session(self, session_id: str):
        """Clear a session's history."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.logger.info(f"Cleared conversation session: {session_id}")


# Global conversation memory manager
conversation_memory = ConversationMemoryManager()
