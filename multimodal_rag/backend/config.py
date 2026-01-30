"""Simplified configuration without pydantic-settings dependency."""
from pathlib import Path
from typing import List
import os


class Settings:
    """Application settings with simple defaults."""
    
    # Ollama Configuration
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    
    # Google Gemini API (Primary)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # OpenRouter API (Backup)
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    fallback_model: str = os.getenv("FALLBACK_MODEL", "google/gemini-flash-1.5")
    
    # Vector Database
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    collection_name: str = os.getenv("COLLECTION_NAME", "multimodal_knowledge")
    
    # Embedding Models
    text_embedding_model: str = os.getenv("TEXT_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    image_embedding_model: str = os.getenv("IMAGE_EMBEDDING_MODEL", "openai/clip-vit-base-patch32")
    whisper_model: str = os.getenv("WHISPER_MODEL", "tiny")
    
    # Retrieval Configuration
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))  # Lowered to reduce false negatives
    max_retrieval_iterations: int = int(os.getenv("MAX_RETrieval_ITERATIONS", "1"))
    
    # Server Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Upload Limits
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    allowed_extensions: List[str] = os.getenv(
        "ALLOWED_EXTENSIONS", 
        "pdf,docx,txt,jpg,jpeg,png,bmp,tiff,mp3,wav,m4a,mp4,m4v,mpeg,mpg,avi,flac,ogg,aac"
    ).split(",")
    
    # Paths
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
    cloud_import_dir: Path = Path(os.getenv("CLOUD_IMPORT_DIR", "./data/cloud_imports"))
    processed_dir: Path = Path(os.getenv("PROCESSED_DIR", "./data/processed"))
    
    def __init__(self):
        # Create directories if they don't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.cloud_import_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
