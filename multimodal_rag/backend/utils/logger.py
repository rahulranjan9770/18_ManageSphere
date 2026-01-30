"""Logging utilities for tracking system operations and decisions."""
import logging
import sys
from pathlib import Path
from datetime import datetime


class RAGLogger:
    """Custom logger for RAG system with decision tracking."""
    
    def __init__(self, name: str = "multimodal_rag"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
        
        # File handler
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(
            log_dir / f"rag_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def log_retrieval_decision(self, query: str, modalities: list, k: int, reason: str):
        """Log why specific retrieval strategy was chosen."""
        self.logger.info(
            f"RETRIEVAL DECISION | Query: {query[:100]} | "
            f"Modalities: {modalities} | Top-K: {k} | Reason: {reason}"
        )
    
    def log_confidence_assessment(self, confidence: float, sources: int, reason: str):
        """Log confidence scoring rationale."""
        self.logger.info(
            f"CONFIDENCE ASSESSMENT | Score: {confidence:.3f} | "
            f"Sources: {sources} | Reason: {reason}"
        )
    
    def log_conflict_detection(self, conflicting_sources: list, details: str):
        """Log detected conflicts between sources."""
        self.logger.warning(
            f"CONFLICT DETECTED | Sources: {conflicting_sources} | Details: {details}"
        )
    
    def log_refusal(self, query: str, reason: str, missing_info: str):
        """Log when system refuses to answer."""
        self.logger.warning(
            f"REFUSAL | Query: {query[:100]} | Reason: {reason} | Missing: {missing_info}"
        )
    
    def log_adaptive_retrieval(self, iteration: int, reason: str, new_k: int):
        """Log adaptive retrieval iterations."""
        self.logger.info(
            f"ADAPTIVE RETRIEVAL | Iteration: {iteration} | Reason: {reason} | New K: {new_k}"
        )

    # Standard logging proxies
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
        
    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


# Global logger instance
logger = RAGLogger()
