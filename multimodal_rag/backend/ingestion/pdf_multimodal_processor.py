"""Multimodal PDF processor that extracts text AND embedded images as first-class knowledge units.

This processor treats PDFs as containers with multiple modalities:
- Text content with page-level metadata
- Embedded images/figures with visual understanding
- Cross-modal relationships preserved

Images extracted from PDFs are treated identically to standalone uploaded images.
"""
import re
import uuid
import io
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import fitz  # PyMuPDF
import numpy as np

from backend.models.document import DocumentChunk, Modality
from backend.utils.logger import logger
from backend.utils.language_service import detect_language, get_language_info


class MultimodalPDFProcessor:
    """Enhanced PDF processor that extracts and indexes both text and images."""
    
    def __init__(
        self, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50,
        extract_images: bool = True,
        min_image_size: Tuple[int, int] = (100, 100),
        max_images_per_page: int = 10
    ):
        """
        Initialize the multimodal PDF processor.
        
        Args:
            chunk_size: Target size for text chunks
            chunk_overlap: Overlap between text chunks
            extract_images: Whether to extract embedded images
            min_image_size: Minimum (width, height) for image extraction
            max_images_per_page: Maximum images to extract per page
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.extract_images = extract_images
        self.min_image_size = min_image_size
        self.max_images_per_page = max_images_per_page
        self.ocr_reader: Optional[any] = None
        
    def _load_ocr(self):
        """Lazy load EasyOCR reader for image text extraction."""
        if self.ocr_reader is None:
            try:
                import easyocr
                logger.logger.info("Loading EasyOCR reader for embedded images...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.logger.info("EasyOCR loaded successfully")
            except ImportError:
                logger.logger.warning("EasyOCR not installed, image OCR disabled")
                self.ocr_reader = False
            except Exception as e:
                logger.logger.error(f"Failed to load EasyOCR: {e}")
                self.ocr_reader = False
    
    def process_pdf(self, file_path: Path) -> List[DocumentChunk]:
        """
        Process a PDF file and extract both text and images as separate chunks.
        
        Returns a unified list of chunks with proper modality tags and metadata.
        """
        chunks = []
        
        try:
            # Open PDF with PyMuPDF for multimodal extraction
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            
            logger.logger.info(
                f"Processing PDF '{file_path.name}': {total_pages} pages, "
                f"extract_images={self.extract_images}"
            )
            
            # Track all text for language detection
            all_text_parts = []
            page_text_mapping = {}
            
            # Extract images from all pages first (if enabled)
            if self.extract_images:
                image_chunks = self._extract_all_images(doc, file_path.name)
                chunks.extend(image_chunks)
                logger.logger.info(
                    f"Extracted {len(image_chunks)} images from {file_path.name}"
                )
            
            # Extract text content with page attribution
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text("text")
                
                if text.strip():
                    all_text_parts.append(text)
                    page_text_mapping[page_num + 1] = text
            
            # Combine all text
            combined_text = " ".join(all_text_parts)
            
            # Detect document language
            lang_code = "en"
            lang_confidence = 0.0
            lang_info = {"name": "English", "flag": "🇬🇧"}
            
            if combined_text.strip():
                lang_code, lang_confidence = detect_language(combined_text)
                lang_info = get_language_info(lang_code)
                logger.logger.info(
                    f"Detected language: {lang_info['name']} ({lang_code}) "
                    f"with confidence {lang_confidence:.2f}"
                )
            
            # Create text chunks
            text_chunks = self._create_text_chunks(
                combined_text,
                file_path.name,
                {
                    "total_pages": total_pages,
                    "language": lang_code,
                    "language_name": lang_info['name'],
                    "language_flag": lang_info['flag'],
                    "language_confidence": lang_confidence,
                    "source_type": "pdf_text"
                }
            )
            
            chunks.extend(text_chunks)
            
            logger.logger.info(
                f"Processed PDF {file_path.name}: "
                f"{len(text_chunks)} text chunks, "
                f"{len([c for c in chunks if c.modality == Modality.IMAGE])} image chunks"
            )
            
            doc.close()
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process PDF {file_path}: {e}")
            return []
    
    def _extract_all_images(
        self, 
        doc: fitz.Document, 
        source_filename: str
    ) -> List[DocumentChunk]:
        """
        Extract all images from the PDF document.
        
        Each image becomes a first-class DocumentChunk with:
        - Modality: IMAGE
        - Metadata: page number, position, source PDF
        - Content: Visual description + OCR text
        - Proper confidence scoring
        """
        image_chunks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1
            
            # Get all images on this page
            image_list = page.get_images(full=True)
            
            # Limit images per page
            image_list = image_list[:self.max_images_per_page]
            
            for img_index, img_info in enumerate(image_list):
                try:
                    # Extract image data
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    
                    if not base_image:
                        continue
                    
                    # Convert to PIL Image
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Check minimum size
                    if (image.width < self.min_image_size[0] or 
                        image.height < self.min_image_size[1]):
                        continue
                    
                    # Convert to RGB if necessary
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Extract text from image using OCR
                    extracted_text = self._extract_text_from_image(image)
                    
                    # Create descriptive content
                    image_description = self._create_image_description(
                        image,
                        source_filename,
                        page_number,
                        img_index + 1,
                        extracted_text
                    )
                    
                    # Calculate confidence based on image quality and OCR
                    confidence = self._calculate_image_confidence(
                        image, 
                        extracted_text
                    )
                    
                    # Create image chunk
                    chunk = DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        source_file=source_filename,
                        modality=Modality.IMAGE,
                        content=image_description,
                        metadata={
                            "source_type": "pdf_embedded_image",
                            "source_pdf": source_filename,
                            "page_number": page_number,
                            "image_index": img_index + 1,
                            "width": image.width,
                            "height": image.height,
                            "aspect_ratio": image.width / image.height,
                            "format": base_image.get("ext", "unknown"),
                            "has_ocr_text": bool(extracted_text),
                            "extracted_text_length": len(extracted_text) if extracted_text else 0,
                            "position_in_document": f"Page {page_number}, Image {img_index + 1}"
                        },
                        confidence=confidence
                    )
                    
                    image_chunks.append(chunk)
                    
                    # If OCR text is substantial, create additional TEXT chunk
                    # This enables better retrieval when users search for text content
                    if extracted_text and len(extracted_text) > 20:
                        text_chunk = DocumentChunk(
                            chunk_id=str(uuid.uuid4()),
                            source_file=source_filename,
                            modality=Modality.TEXT,
                            content=f"Text extracted from image on page {page_number} of {source_filename}:\n{extracted_text}",
                            metadata={
                                "source_type": "pdf_image_ocr",
                                "source_pdf": source_filename,
                                "page_number": page_number,
                                "image_index": img_index + 1,
                                "is_ocr_extraction": True,
                                "source_modality": "image",
                                "parent_chunk_type": "pdf_embedded_image"
                            },
                            confidence=0.85  # Slightly lower confidence for OCR
                        )
                        image_chunks.append(text_chunk)
                        
                        logger.logger.info(
                            f"Created OCR text chunk for embedded image: "
                            f"{source_filename} page {page_number} ({len(extracted_text)} chars)"
                        )
                    
                except Exception as e:
                    logger.logger.warning(
                        f"Failed to extract image {img_index + 1} from page {page_number}: {e}"
                    )
                    continue
        
        return image_chunks
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from an image using OCR."""
        try:
            self._load_ocr()
            
            if self.ocr_reader is False:
                return ""
            
            # Convert PIL image to numpy array for EasyOCR
            img_array = np.array(image)
            
            # Perform OCR
            result = self.ocr_reader.readtext(img_array, paragraph=False)
            
            if not result:
                return ""
            
            # Extract text
            texts = [detection[1] for detection in result if len(detection) > 1]
            combined_text = " ".join(texts).strip()
            
            return combined_text
            
        except Exception as e:
            logger.logger.warning(f"OCR failed for embedded image: {e}")
            return ""
    
    def _create_image_description(
        self,
        image: Image.Image,
        source_filename: str,
        page_number: int,
        image_index: int,
        extracted_text: str
    ) -> str:
        """Create a comprehensive text description of the image."""
        width, height = image.size
        orientation = "portrait" if height > width else "landscape" if width > height else "square"
        
        description_parts = [
            f"Image extracted from page {page_number} of document '{source_filename}'.",
            f"Position: Image #{image_index} on page {page_number}.",
            f"Dimensions: {width}x{height} pixels, {orientation} orientation."
        ]
        
        if extracted_text:
            description_parts.append(f"\nExtracted text from image:\n{extracted_text}")
        else:
            description_parts.append("No text detected in this image.")
        
        return " ".join(description_parts)
    
    def _calculate_image_confidence(
        self, 
        image: Image.Image, 
        extracted_text: str
    ) -> float:
        """
        Calculate confidence score for an extracted image.
        
        Based on:
        - Image resolution
        - Clarity (variance in pixel values)
        - OCR text presence and length
        """
        confidence = 0.7  # Base confidence for embedded images
        
        # Boost for high resolution
        total_pixels = image.width * image.height
        if total_pixels > 500000:  # > 500K pixels
            confidence += 0.1
        elif total_pixels < 50000:  # < 50K pixels (low quality)
            confidence -= 0.1
        
        # Boost for OCR text presence
        if extracted_text:
            if len(extracted_text) > 100:
                confidence += 0.15
            elif len(extracted_text) > 20:
                confidence += 0.1
            else:
                confidence += 0.05
        
        # Ensure confidence is in valid range
        return max(0.5, min(1.0, confidence))
    
    def _create_text_chunks(
        self,
        text: str,
        source_file: str,
        base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split text into overlapping chunks with metadata."""
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return []
        
        # Split into sentences
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
