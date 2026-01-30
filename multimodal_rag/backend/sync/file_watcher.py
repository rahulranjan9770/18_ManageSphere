"""File watcher for real-time document synchronization."""
import os
import hashlib
import time
import asyncio
from pathlib import Path
from typing import Dict, Set, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent

from backend.config import settings
from backend.utils.logger import logger


@dataclass
class FileChange:
    """Represents a file change event."""
    path: str
    change_type: str  # "created", "modified", "deleted"
    timestamp: str
    file_name: str
    file_size: int = 0
    file_hash: Optional[str] = None


class DocumentWatcher(FileSystemEventHandler):
    """Watches a folder for document changes."""
    
    SUPPORTED_EXTENSIONS = {
        '.pdf', '.docx', '.txt',  # Text
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff',  # Images
        '.mp3', '.wav', '.m4a', '.mp4', '.flac', '.ogg', '.aac'  # Audio
    }
    
    def __init__(self, watch_path: str):
        super().__init__()
        self.watch_path = Path(watch_path)
        self.observer: Optional[Observer] = None
        self.is_running = False
        
        # Track file hashes to detect actual changes
        self.file_hashes: Dict[str, str] = {}
        
        # Pending changes queue
        self.pending_changes: list = []
        
        # Callbacks for notification
        self._on_change_callbacks: list = []
        
        # Stats
        self.total_changes_detected = 0
        self.last_change_time: Optional[str] = None
        
        # Debounce settings (to avoid rapid duplicate events)
        self._last_events: Dict[str, float] = {}
        self._debounce_seconds = 2.0
        
        # Ensure watch folder exists
        if not self.watch_path.exists():
            self.watch_path.mkdir(parents=True, exist_ok=True)
            logger.logger.info(f"Created watch folder: {self.watch_path}")
    
    def _is_supported_file(self, path: str) -> bool:
        """Check if file has a supported extension."""
        ext = Path(path).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    def _compute_file_hash(self, path: str) -> Optional[str]:
        """Compute MD5 hash of a file for change detection."""
        try:
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    def _should_process_event(self, path: str) -> bool:
        """Debounce rapid events for the same file."""
        now = time.time()
        last_time = self._last_events.get(path, 0)
        
        if now - last_time < self._debounce_seconds:
            return False
        
        self._last_events[path] = now
        return True
    
    def _create_change_event(self, path: str, change_type: str) -> FileChange:
        """Create a FileChange object."""
        file_path = Path(path)
        file_size = 0
        file_hash = None
        
        if file_path.exists():
            try:
                file_size = file_path.stat().st_size
                file_hash = self._compute_file_hash(path)
            except Exception:
                pass
        
        return FileChange(
            path=str(file_path),
            change_type=change_type,
            timestamp=datetime.now().isoformat(),
            file_name=file_path.name,
            file_size=file_size,
            file_hash=file_hash
        )
    
    def on_created(self, event):
        """Handle file creation."""
        if event.is_directory:
            return
        
        if not self._is_supported_file(event.src_path):
            return
        
        if not self._should_process_event(event.src_path):
            return
        
        change = self._create_change_event(event.src_path, "created")
        self._handle_change(change)
        logger.logger.info(f"File created: {change.file_name}")
    
    def on_modified(self, event):
        """Handle file modification."""
        if event.is_directory:
            return
        
        if not self._is_supported_file(event.src_path):
            return
        
        if not self._should_process_event(event.src_path):
            return
        
        # Check if content actually changed using hash
        new_hash = self._compute_file_hash(event.src_path)
        old_hash = self.file_hashes.get(event.src_path)
        
        if new_hash and new_hash == old_hash:
            return  # No actual content change
        
        self.file_hashes[event.src_path] = new_hash
        
        change = self._create_change_event(event.src_path, "modified")
        self._handle_change(change)
        logger.logger.info(f"File modified: {change.file_name}")
    
    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory:
            return
        
        if not self._is_supported_file(event.src_path):
            return
        
        if not self._should_process_event(event.src_path):
            return
        
        # Remove from hash cache
        self.file_hashes.pop(event.src_path, None)
        
        change = self._create_change_event(event.src_path, "deleted")
        self._handle_change(change)
        logger.logger.info(f"File deleted: {change.file_name}")
    
    def _handle_change(self, change: FileChange):
        """Process a file change."""
        self.pending_changes.append(change)
        self.total_changes_detected += 1
        self.last_change_time = change.timestamp
        
        # Notify all callbacks
        for callback in self._on_change_callbacks:
            try:
                callback(change)
            except Exception as e:
                logger.logger.error(f"Callback error: {e}")
    
    def add_change_callback(self, callback: Callable[[FileChange], None]):
        """Add a callback for change notifications."""
        self._on_change_callbacks.append(callback)
    
    def start(self):
        """Start watching the folder."""
        if self.is_running:
            return
        
        # Clear tracked files so existing files are detected as new
        self.file_hashes.clear()
        
        self.observer = Observer()
        self.observer.schedule(self, str(self.watch_path), recursive=True)
        self.observer.start()
        self.is_running = True
        logger.logger.info(f"Started watching folder: {self.watch_path}")
    
    def stop(self):
        """Stop watching the folder."""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.logger.info("Stopped folder watcher")
    
    def get_pending_changes(self) -> list:
        """Get and clear pending changes."""
        changes = self.pending_changes.copy()
        self.pending_changes.clear()
        return changes
    
    def get_status(self) -> dict:
        """Get watcher status."""
        return {
            "is_running": self.is_running,
            "watch_path": str(self.watch_path),
            "total_changes_detected": self.total_changes_detected,
            "pending_changes": len(self.pending_changes),
            "last_change_time": self.last_change_time,
            "tracked_files": len(self.file_hashes)
        }
    
    def scan_existing_files(self) -> list:
        """Scan and return all existing supported files."""
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            pattern = f"*{ext}"
            for file_path in self.watch_path.rglob(pattern):
                if file_path.is_file():
                    files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix.lower()
                    })
                    # Cache hash
                    self.file_hashes[str(file_path)] = self._compute_file_hash(str(file_path))
        return files


# Global watcher instance (initialized lazily)
_document_watcher: Optional[DocumentWatcher] = None


def get_document_watcher(watch_path: str = None) -> DocumentWatcher:
    """Get or create the global document watcher."""
    global _document_watcher
    
    if _document_watcher is None:
        path = watch_path or str(Path(settings.upload_dir) / "watch")
        _document_watcher = DocumentWatcher(path)
    
    return _document_watcher
