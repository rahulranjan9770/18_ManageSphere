"""Image processor for extracting visual information and text via OCR."""
import uuid
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2

from backend.models.document import DocumentChunk, Modality
from backend.utils.logger import logger


class ImageProcessor:
    """Processes images and extracts visual features + text via OCR with advanced preprocessing."""
    
    def __init__(self, max_size: tuple = (1600, 1600)):  # Increased from 800x800
        self.max_size = max_size
        self.ocr_reader: Optional[any] = None
    
    def _load_ocr(self):
        """Lazy load EasyOCR reader."""
        if self.ocr_reader is None:
            try:
                import easyocr
                logger.logger.info("Loading EasyOCR reader for English...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.logger.info("EasyOCR loaded successfully")
            except ImportError:
                logger.logger.warning("EasyOCR not installed, OCR disabled")
                self.ocr_reader = False
            except Exception as e:
                logger.logger.error(f"Failed to load EasyOCR: {e}")
                self.ocr_reader = False
    
    def _preprocess_for_ocr(self, image_path: Path) -> List[np.ndarray]:
        """
        ULTRA FAST MODE: Skip preprocessing, use original image only.
        Trading some OCR quality for 5x faster upload speed.
        """
        return []  # Return empty - will use image path directly in OCR
    
    def process_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process an image file with enhanced OCR text extraction."""
        try:
            image = Image.open(file_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (but keep higher resolution for better OCR)
            if image.size[0] > self.max_size[0] or image.size[1] > self.max_size[1]:
                image.thumbnail(self.max_size, Image.Resampling.LANCZOS)
            
            # Extract basic features
            width, height = image.size
            aspect_ratio = width / height
            
            # Get dominant colors
            img_array = np.array(image)
            avg_color = img_array.mean(axis=(0, 1))
            
            # Extract text using enhanced OCR
            extracted_text = self._extract_text_ocr(file_path)
            
            # Create descriptive content
            if extracted_text:
                description = (
                    f"Image file: {file_path.name}\n"
                    f"Extracted text from image:\n{extracted_text}\n\n"
                    f"Image properties: {width}x{height} pixels"
                )
                confidence = 0.9
            else:
                description = self._generate_basic_description(image, file_path.name)
                confidence = 0.7
            
            # Create primary Image chunk
            image_chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                source_file=file_path.name,
                modality=Modality.IMAGE,
                content=description,
                metadata={
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "avg_color": avg_color.tolist(),
                    "file_size": file_path.stat().st_size,
                    "image_path": str(file_path.absolute()),
                    "has_ocr_text": bool(extracted_text),
                    "extracted_text_length": len(extracted_text) if extracted_text else 0
                },
                confidence=confidence
            )
            
            chunks = [image_chunk]
            
            # Create secondary Text chunk for better text matching
            if extracted_text and len(extracted_text) > 10:
                text_chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    source_file=file_path.name,
                    modality=Modality.TEXT,
                    content=f"Text extracted from {file_path.name}:\n{extracted_text}",
                    metadata={
                        "original_image_path": str(file_path.absolute()),
                        "is_ocr_extraction": True,
                        "source_modality": "image"
                    },
                    confidence=0.95
                )
                chunks.append(text_chunk)
                logger.logger.info(f"Created OCR text chunk for {file_path.name} ({len(extracted_text)} chars)")
            
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process image {file_path}: {e}")
            return []
    
    def _extract_text_ocr(self, image_path: Path) -> str:
        """Extract text from image using OCR (ULTRA FAST MODE - no preprocessing)."""
        try:
            self._load_ocr()
            
            if self.ocr_reader is False:
                return ""
            
            # ULTRA FAST: Use original image path directly, no preprocessing
            result = self.ocr_reader.readtext(str(image_path), paragraph=False)
            
            if not result:
                return ""
            
            # Extract text
            texts = [detection[1] for detection in result if len(detection) > 1]
            combined_text = " ".join(texts).strip()
            
            if combined_text:
                logger.logger.info(f"OCR extracted {len(combined_text)} characters from {image_path.name}")
            
            return combined_text
            
        except Exception as e:
            logger.logger.warning(f"OCR failed for {image_path}: {e}")
            return ""
    
    def _generate_basic_description(self, image: Image.Image, filename: str) -> str:
        """Generate basic text description of image."""
        width, height = image.size
        orientation = "portrait" if height > width else "landscape" if width > height else "square"
        
        file_type = filename.split('.')[-1].upper()
        
        return (
            f"Image file: {filename}. "
            f"Format: {file_type}. "
            f"Dimensions: {width}x{height} pixels, {orientation} orientation."
        )
