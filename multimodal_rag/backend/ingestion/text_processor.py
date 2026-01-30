"""Text document processor for PDF, DOCX, and TXT files."""
import re
from pathlib import Path
from typing import List, Dict, Any
import uuid
from pypdf import PdfReader
from docx import Document
import chardet

from backend.models.document import DocumentChunk, Modality
from backend.utils.logger import logger
from backend.utils.language_service import detect_language, get_language_info


class TextProcessor:
    """Processes text documents and creates semantic chunks."""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process a file based on its extension."""
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.pdf':
                return self._process_pdf(file_path)
            elif extension == '.docx':
                return self._process_docx(file_path)
            elif extension == '.txt':
                return self._process_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {extension}")
        except Exception as e:
            logger.logger.error(f"Error processing {file_path}: {str(e)}")
            return []
    
    def _process_pdf(self, file_path: Path) -> List[DocumentChunk]:
        """Extract text from PDF with page attribution."""
        chunks = []
        
        try:
            reader = PdfReader(str(file_path))
            full_text = []
            page_mapping = []
            
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        full_text.append(text)
                        page_mapping.extend([page_num] * len(text.split()))
                except Exception as e:
                    logger.logger.warning(f"Error extracting page {page_num}: {e}")
                    continue
            
            combined_text = " ".join(full_text)
            chunks = self._create_chunks(
                combined_text,
                file_path.name,
                {"total_pages": len(reader.pages)}
            )
            
            logger.logger.info(f"Processed PDF {file_path.name}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process PDF {file_path}: {e}")
            return []
    
    def _process_docx(self, file_path: Path) -> List[DocumentChunk]:
        """Extract text from DOCX preserving structure."""
        try:
            doc = Document(str(file_path))
            paragraphs = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            full_text = "\n".join(paragraphs)
            chunks = self._create_chunks(
                full_text,
                file_path.name,
                {"total_paragraphs": len(paragraphs)}
            )
            
            logger.logger.info(f"Processed DOCX {file_path.name}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process DOCX {file_path}: {e}")
            return []
    
    def _process_txt(self, file_path: Path) -> List[DocumentChunk]:
        """Extract text from TXT with encoding detection."""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            # Read with detected encoding
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            
            chunks = self._create_chunks(
                text,
                file_path.name,
                {"encoding": encoding}
            )
            
            logger.logger.info(f"Processed TXT {file_path.name}: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process TXT {file_path}: {e}")
            return []
    
    def _create_chunks(
        self, 
        text: str, 
        source_file: str, 
        base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Detect language of the document
        lang_code, lang_confidence = detect_language(text)
        lang_info = get_language_info(lang_code)
        logger.logger.info(f"Detected language: {lang_info['name']} ({lang_code}) with confidence {lang_confidence:.2f}")
        
        # Add language to base metadata
        base_metadata['language'] = lang_code
        base_metadata['language_name'] = lang_info['name']
        base_metadata['language_flag'] = lang_info['flag']
        base_metadata['language_confidence'] = lang_confidence
        
        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0

        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk)
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    source_file=source_file,
                    modality=Modality.TEXT,
                    content=chunk_text,
                    metadata={
                        **base_metadata,
                        "chunk_index": len(chunks),
                        "word_count": current_length
                    },
                    confidence=1.0
                )
                chunks.append(chunk)
                
                # Keep overlap
                overlap_words = " ".join(current_chunk).split()[-self.chunk_overlap:]
                current_chunk = [" ".join(overlap_words), sentence]
                current_length = len(overlap_words) + sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                source_file=source_file,
                modality=Modality.TEXT,
                content=chunk_text,
                metadata={
                    **base_metadata,
                    "chunk_index": len(chunks),
                    "word_count": current_length
                },
                confidence=1.0
            )
            chunks.append(chunk)
        
        return chunks
