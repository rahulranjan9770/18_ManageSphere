"""Audio processor for transcription and segmentation."""
import uuid
from pathlib import Path
from typing import List, Optional
import whisper

from backend.models.document import DocumentChunk, Modality
from backend.utils.logger import logger
from backend.config import settings


class AudioProcessor:
    """Processes audio files and creates timestamped transcripts with enhanced quality."""
    
    def __init__(self):
        self.model: Optional[whisper.Whisper] = None
    
    def _load_model(self):
        """Lazy load Whisper model."""
        if self.model is None:
            logger.logger.info(f"Loading Whisper {settings.whisper_model} model...")
            self.model = whisper.load_model(settings.whisper_model)
            logger.logger.info("Whisper model loaded successfully")
    
    def process_file(self, file_path: Path) -> List[DocumentChunk]:
        """Transcribe audio file with enhanced quality settings."""
        try:
            self._load_model()
            
            logger.logger.info(f"Transcribing {file_path.name}...")
            
            # Enhanced transcription with optimal parameters
            try:
                result = self.model.transcribe(
                    str(file_path),
                    language='en',
                    task='transcribe',
                    # Quality improvements
                    temperature=0.0,  # Deterministic output
                    best_of=5,  # Try 5 candidates, pick best
                    beam_size=5,  # Beam search for better accuracy
                    # Hallucination prevention
                    no_speech_threshold=0.6,  # Higher threshold to avoid false positives
                    logprob_threshold=-1.0,  # Filter low-confidence
                    compression_ratio_threshold=2.4,  # Detect repetitive hallucinations
                    # Fine control
                    condition_on_previous_text=True,  # Use context
                    initial_prompt="",  # Optional: add domain-specific context
                    word_timestamps=False,  # Disable for faster processing
                    verbose=False
                )
            except Exception as transcribe_error:
                logger.logger.warning(f"Enhanced transcription failed, using fallback: {transcribe_error}")
                # Fallback to simple transcription
                result = self.model.transcribe(
                    str(file_path),
                    language='en',
                    verbose=False
                )
            
            # Extract transcription
            text = result.get('text', '').strip()
            
            if not text:
                logger.logger.warning(f"No transcription for {file_path.name}")
                return [DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    source_file=file_path.name,
                    modality=Modality.AUDIO,
                    content="[Audio file - silent or no speech detected]",
                    metadata={
                        "audio_path": str(file_path.absolute()),
                        "note": "No speech detected"
                    },
                    confidence=0.5
                )]
            
            # Create chunks from segments
            chunks = []
            segments = result.get('segments', [])
            
            # Calculate overall transcription quality
            avg_logprob = result.get('avg_logprob', -0.5)
            no_speech_prob = result.get('no_speech_prob', 0.0)
            overall_confidence = max(0.1, min(1.0, (avg_logprob + 1.0) * (1.0 - no_speech_prob)))
            
            if not segments:
                # Create single chunk with full transcription
                chunks.append(DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    source_file=file_path.name,
                    modality=Modality.AUDIO,
                    content=text,
                    metadata={
                        "audio_path": str(file_path.absolute()),
                        "full_transcription": True,
                        "language": result.get('language', 'en'),
                        "overall_confidence": overall_confidence,
                        "duration": result.get('duration', 0)
                    },
                    confidence=overall_confidence
                ))
            else:
                # Create chunks per segment
                for segment in segments:
                    segment_text = segment.get('text', '').strip()
                    if not segment_text:
                        continue
                    
                    # Calculate segment confidence
                    seg_logprob = segment.get('avg_logprob', -0.5)
                    seg_no_speech = segment.get('no_speech_prob', 0.0)
                    seg_confidence = max(0.1, min(1.0, (seg_logprob + 1.0) * (1.0 - seg_no_speech)))
                    
                    chunk = DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        source_file=file_path.name,
                        modality=Modality.AUDIO,
                        content=segment_text,
                        metadata={
                            "start_time": segment.get('start', 0),
                            "end_time": segment.get('end', 0),
                            "segment_id": segment.get('id', 0),
                            "audio_path": str(file_path.absolute()),
                            "compression_ratio": segment.get('compression_ratio', 1.0),
                            "language": result.get('language', 'en')
                        },
                        confidence=seg_confidence
                    )
                    chunks.append(chunk)
            
            logger.logger.info(
                f"Transcribed {file_path.name}: "
                f"{len(chunks)} segments, {len(text)} chars, "
                f"confidence: {overall_confidence:.2f}"
            )
            return chunks
            
        except Exception as e:
            logger.logger.error(f"Failed to process audio {file_path}: {e}")
            return [DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                source_file=file_path.name,
                modality=Modality.AUDIO,
                content=f"[Audio processing error: {str(e)[:100]}]",
                metadata={
                    "error": str(e),
                    "status": "failed"
                },
                confidence=0.1
            )]
