"""Knowledge Graph Builder for visualizing document relationships."""
import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from backend.storage.vector_store import VectorStore
from backend.utils.logger import logger


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str
    label: str
    node_type: str  # document, entity, concept, value
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            "metadata": self.metadata
        }


@dataclass
class GraphEdge:
    """An edge connecting two nodes."""
    source: str
    target: str
    relationship: str
    weight: float = 1.0
    
    def to_dict(self):
        return {
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "weight": self.weight
        }


class KnowledgeGraphBuilder:
    """Builds a knowledge graph from the vector store documents."""
    
    # Patterns for entity extraction
    ENTITY_PATTERNS = {
        'value': r'\b(\d+(?:\.\d+)?)\s*(V|v|volt|volts|W|watts?|A|amps?|Hz|kg|lbs?|°[CF]|%|mm|cm|m)\b',
        'machine': r'\b([A-Z][A-Z0-9]+-\d+[A-Z]?)\b',
        'year': r'\b(19|20)\d{2}\b',
    }
    
    # Relationship patterns
    RELATIONSHIP_PATTERNS = [
        (r'(\w+)\s+(?:is|are|was|were)\s+(\w+)', 'is'),
        (r'(\w+)\s+(?:has|have|had)\s+(\w+)', 'has'),
        (r'(\w+)\s+(?:requires?|needs?)\s+(\w+)', 'requires'),
        (r'(\w+)\s+(?:contains?|includes?)\s+(\w+)', 'contains'),
        (r'voltage\s*[:=]?\s*(\d+\s*[vV])', 'has_voltage'),
        (r'manufactured?\s*[:=]?\s*((?:19|20)\d{2})', 'manufactured_in'),
    ]
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
    
    def build_graph(self) -> Dict:
        """Build the knowledge graph from all documents."""
        self.nodes = {}
        self.edges = []
        
        try:
            # Get all chunks from vector store
            all_data = self.vector_store.get_all()
            
            if not all_data or 'documents' not in all_data:
                return self._empty_graph()
            
            documents = all_data.get('documents', [])
            metadatas = all_data.get('metadatas', [])
            ids = all_data.get('ids', [])
            
            # Process each document
            doc_entities: Dict[str, Set[str]] = {}  # doc_id -> entities
            
            for i, (doc_id, content, metadata) in enumerate(zip(ids, documents, metadatas)):
                # Create document node regardless of content
                source_file = metadata.get('source_file', 'Unknown')
                modality = metadata.get('modality', 'text')
                
                # Use source file as document node ID (dedupe chunks)
                doc_node_id = f"doc_{self._sanitize_id(source_file)}"
                
                if doc_node_id not in self.nodes:
                    self.nodes[doc_node_id] = GraphNode(
                        id=doc_node_id,
                        label=source_file.split('/')[-1].split('\\')[-1],
                        node_type="document",
                        metadata={
                            "modality": modality,
                            "full_path": source_file,
                            "chunk_count": 1
                        }
                    )
                    doc_entities[doc_node_id] = set()
                else:
                    # Increment chunk count
                    self.nodes[doc_node_id].metadata["chunk_count"] = \
                        self.nodes[doc_node_id].metadata.get("chunk_count", 0) + 1
                
                # Extract entities from content only if content exists
                if content:
                    entities = self._extract_entities(content)
                    doc_entities[doc_node_id].update(entities)
            
            # Create entity nodes and edges
            for doc_id, entities in doc_entities.items():
                for entity_id, entity_label, entity_type in entities:
                    # Create entity node if not exists
                    if entity_id not in self.nodes:
                        self.nodes[entity_id] = GraphNode(
                            id=entity_id,
                            label=entity_label,
                            node_type=entity_type,
                            metadata={"mentions": 1}
                        )
                    else:
                        self.nodes[entity_id].metadata["mentions"] = \
                            self.nodes[entity_id].metadata.get("mentions", 0) + 1
                    
                    # Create edge from document to entity
                    self.edges.append(GraphEdge(
                        source=doc_id,
                        target=entity_id,
                        relationship="mentions",
                        weight=1.0
                    ))
            
            # Find relationships between entities
            self._find_entity_relationships(doc_entities)
            
            return self._build_response()
            
        except Exception as e:
            logger.logger.error(f"Error building knowledge graph: {e}")
            return self._empty_graph()
    
    def _extract_entities(self, content: str) -> Set[Tuple[str, str, str]]:
        """Extract entities from content. Returns set of (id, label, type)."""
        entities = set()
        
        # Extract values (voltages, weights, etc.)
        for match in re.finditer(self.ENTITY_PATTERNS['value'], content, re.IGNORECASE):
            value = f"{match.group(1)}{match.group(2).upper()}"
            entity_id = f"val_{self._sanitize_id(value)}"
            entities.add((entity_id, value, "value"))
        
        # Extract machine/model IDs
        for match in re.finditer(self.ENTITY_PATTERNS['machine'], content):
            machine = match.group(1)
            entity_id = f"machine_{self._sanitize_id(machine)}"
            entities.add((entity_id, machine, "machine"))
        
        # Extract years
        for match in re.finditer(self.ENTITY_PATTERNS['year'], content):
            year = match.group(0)
            entity_id = f"year_{year}"
            entities.add((entity_id, year, "year"))
        
        # Extract key concepts (capitalized words/phrases)
        concepts = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', content)
        for concept in concepts[:5]:  # Limit concepts per chunk
            if len(concept) > 3 and concept.lower() not in ['the', 'and', 'for', 'with']:
                entity_id = f"concept_{self._sanitize_id(concept)}"
                entities.add((entity_id, concept, "concept"))
        
        return entities
    
    def _find_entity_relationships(self, doc_entities: Dict[str, Set[str]]):
        """Find relationships between entities that appear in the same documents."""
        # Group entities by document
        entity_to_docs: Dict[str, List[str]] = {}
        
        for doc_id, entities in doc_entities.items():
            for entity_tuple in entities:
                entity_id = entity_tuple[0]
                if entity_id not in entity_to_docs:
                    entity_to_docs[entity_id] = []
                entity_to_docs[entity_id].append(doc_id)
        
        # Find entities that co-occur in documents
        entity_ids = list(entity_to_docs.keys())
        for i, entity1 in enumerate(entity_ids):
            for entity2 in entity_ids[i+1:]:
                # Check for co-occurrence
                docs1 = set(entity_to_docs[entity1])
                docs2 = set(entity_to_docs[entity2])
                common_docs = docs1 & docs2
                
                if common_docs:
                    # Determine relationship based on types
                    type1 = self.nodes[entity1].node_type if entity1 in self.nodes else "unknown"
                    type2 = self.nodes[entity2].node_type if entity2 in self.nodes else "unknown"
                    
                    relationship = self._infer_relationship(type1, type2)
                    
                    self.edges.append(GraphEdge(
                        source=entity1,
                        target=entity2,
                        relationship=relationship,
                        weight=len(common_docs)
                    ))
    
    def _infer_relationship(self, type1: str, type2: str) -> str:
        """Infer relationship between two entity types."""
        relationships = {
            ("machine", "value"): "has_specification",
            ("machine", "year"): "manufactured_in",
            ("document", "value"): "contains",
            ("document", "machine"): "describes",
            ("concept", "value"): "has_value",
            ("concept", "machine"): "applies_to",
        }
        
        key = (type1, type2)
        if key in relationships:
            return relationships[key]
        
        key_reversed = (type2, type1)
        if key_reversed in relationships:
            return relationships[key_reversed]
        
        return "related_to"
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text to create a valid ID."""
        return re.sub(r'[^a-zA-Z0-9]', '_', text.lower())[:50]
    
    def _empty_graph(self) -> Dict:
        """Return empty graph structure."""
        return {
            "nodes": [],
            "edges": [],
            "stats": {
                "node_count": 0,
                "edge_count": 0,
                "document_count": 0,
                "entity_count": 0
            }
        }
    
    def _build_response(self) -> Dict:
        """Build the final graph response."""
        # Count by type
        doc_count = sum(1 for n in self.nodes.values() if n.node_type == "document")
        entity_count = len(self.nodes) - doc_count
        
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "document_count": doc_count,
                "entity_count": entity_count
            }
        }
    
    def get_node_details(self, node_id: str) -> Dict:
        """Get detailed information about a specific node."""
        if node_id not in self.nodes:
            return {"error": "Node not found"}
        
        node = self.nodes[node_id]
        
        # Find connected nodes
        connected = []
        for edge in self.edges:
            if edge.source == node_id:
                if edge.target in self.nodes:
                    connected.append({
                        "node": self.nodes[edge.target].to_dict(),
                        "relationship": edge.relationship,
                        "direction": "outgoing"
                    })
            elif edge.target == node_id:
                if edge.source in self.nodes:
                    connected.append({
                        "node": self.nodes[edge.source].to_dict(),
                        "relationship": edge.relationship,
                        "direction": "incoming"
                    })
        
        return {
            "node": node.to_dict(),
            "connections": connected,
            "connection_count": len(connected)
        }
