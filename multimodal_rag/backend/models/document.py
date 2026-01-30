"""Data models for document representation."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Modality(str, Enum):
    """Supported data modalities."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class DocumentChunk(BaseModel):
    """Represents a chunk of processed content."""
    chunk_id: str
    source_file: str
    modality: Modality
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.now)
    cross_refs: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class ProcessedDocument(BaseModel):
    """Represents a fully processed document."""
    doc_id: str
    filename: str
    file_path: str
    modalities: List[Modality]
    chunks: List[DocumentChunk]
    total_chunks: int
    processing_time: float
    status: str = "processed"
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    success: bool
    doc_id: str
    filename: str
    modalities_detected: List[str]  # Changed from List[Modality] to List[str]
    chunks_created: int
    message: str

