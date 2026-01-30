from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
import shutil
import uuid
import os
import asyncio
import json

# ⚡ Load environment variables FIRST for ultra-fast Gemini API
from dotenv import load_dotenv
load_dotenv()  # Loads GEMINI_API_KEY and all other settings

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import time
import uuid

from backend.config import settings
from backend.models.document import ProcessedDocument, UploadResponse, Modality
from backend.models.query import QueryRequest, QueryResponse
from backend.ingestion.text_processor import TextProcessor
from backend.ingestion.image_processor import ImageProcessor
from backend.ingestion.audio_processor import AudioProcessor
from backend.embeddings.embedding_manager import EmbeddingManager
from backend.storage.vector_store import VectorStore
from backend.retrieval.cross_modal_retriever import CrossModalRetriever
from backend.generation.rag_generator import RAGGenerator
from backend.memory.conversation_memory import conversation_memory
from backend.graph.knowledge_graph import KnowledgeGraphBuilder
from backend.sync.file_watcher import get_document_watcher, FileChange
from backend.utils.logger import logger
from backend.utils.language_service import language_service, detect_language, get_language_info
from backend.cloud.cloud_storage import cloud_storage_manager, CloudProvider, CloudCredentials
from backend.web.web_search import web_search_service, search_web


# Initialize app
app = FastAPI(
    title="Multimodal RAG System",
    description="Evidence-based multimodal retrieval and generation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Initialize components
vector_store = VectorStore()
embedding_manager = EmbeddingManager()
retriever = CrossModalRetriever(vector_store, embedding_manager)
rag_generator = RAGGenerator(retriever)

text_processor = TextProcessor()
image_processor = ImageProcessor()
audio_processor = AudioProcessor()

# ============ WebSocket Connection Manager ============
class ConnectionManager:
    """Manages WebSocket connections for real-time sync notifications."""
    
    def __init__(self):
        self.active_connections: list = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

ws_manager = ConnectionManager()

# ============ File Watcher Setup ============
# Watch the main uploads directory for ALL file changes
document_watcher = get_document_watcher(watch_path=str(settings.upload_dir))

# Callback for file changes - queues for async processing
pending_sync_changes: list = []

# Auto-index setting - when enabled, automatically index new files
auto_index_enabled: bool = False
auto_index_queue: list = []  # Queue of files to auto-index

def on_file_change(change: FileChange):
    """Handle file change from watcher."""
    change_data = {
        "type": "file_change",
        "change_type": change.change_type,
        "file_name": change.file_name,
        "path": change.path,
        "timestamp": change.timestamp,
        "file_size": change.file_size
    }
    pending_sync_changes.append(change_data)
    logger.logger.info(f"Sync: {change.change_type} - {change.file_name}")
    
    # Handle deleted files - remove from auto-index queue
    if change.change_type == "deleted":
        if change.path in auto_index_queue:
            auto_index_queue.remove(change.path)
            logger.logger.info(f"Removed deleted file from auto-index queue: {change.file_name}")
    
    # If auto-index is enabled and file was created, queue for indexing
    elif auto_index_enabled and change.change_type == "created":
        auto_index_queue.append(change.path)
        logger.logger.info(f"Auto-index queued: {change.file_name}")


document_watcher.add_change_callback(on_file_change)

# Helper to trigger sync notification for uploaded files
def trigger_upload_notification(file_path: str, file_name: str, file_size: int):
    """Manually trigger a notification for uploaded files."""
    pending_sync_changes.append({
        "type": "file_change",
        "change_type": "uploaded",
        "file_name": file_name,
        "path": file_path,
        "timestamp": datetime.now().isoformat(),
        "file_size": file_size
    })
    logger.logger.info(f"Sync: uploaded - {file_name}")
    
    # If auto-index is enabled, also queue uploaded file for indexing
    if auto_index_enabled:
        auto_index_queue.append(file_path)
        logger.logger.info(f"Auto-index queued (uploaded): {file_name}")



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a document."""
    start_time = time.time()
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{file_ext} not allowed. Allowed: {settings.allowed_extensions}"
        )
    
    # Validate file size
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    temp_file = settings.upload_dir / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        # Save uploaded file
        with open(temp_file, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > settings.max_file_size_mb * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
                    )
                buffer.write(chunk)
        
        # Process based on file type
        chunks = []
        modalities = []
        
        if file_ext in ['pdf', 'docx', 'txt']:
            chunks = text_processor.process_file(temp_file)
            modalities.append(Modality.TEXT)
        elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
            chunks = image_processor.process_file(temp_file)
            modalities.append(Modality.IMAGE)
        elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'm4v', 'mpeg', 'mpg', 'avi', 'flac', 'ogg', 'aac']:
            chunks = audio_processor.process_file(temp_file)
            modalities.append(Modality.AUDIO)
        
        if not chunks:
            raise HTTPException(status_code=500, detail="Failed to process file")
        
        # Generate embeddings
        chunks = embedding_manager.embed_chunks(chunks)
        
        # Store in vector database
        stored_count = vector_store.add_chunks(chunks)
        
        processing_time = time.time() - start_time
        
        logger.logger.info(
            f"Uploaded and processed {file.filename}: "
            f"{stored_count} chunks in {processing_time:.2f}s"
        )
        
        # Trigger real-time sync notification if watcher is running
        if document_watcher.is_running:
            trigger_upload_notification(
                file_path=str(temp_file),
                file_name=file.filename,
                file_size=file_size
            )
        
        return UploadResponse(
            success=True,
            doc_id=str(uuid.uuid4()),
            filename=file.filename,
            modalities_detected=[m.value for m in modalities],  # Convert enum to string
            chunks_created=stored_count,
            message=f"Successfully processed {file.filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if temp_file.exists():
            temp_file.unlink()


@app.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """Query the knowledge base."""
    try:
        response = await rag_generator.generate_response(request)
        return response
    except Exception as e:
        logger.logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    return {
        "total_chunks": vector_store.count(),
        "collection": settings.collection_name,
        "models": {
            "text": settings.text_embedding_model,
            "image": settings.image_embedding_model,
            "llm": settings.ollama_model
        }
    }


@app.delete("/reset")
async def reset_database():
    """Reset the vector database (for testing)."""
    try:
        vector_store.reset()
        return {"message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ Conversation Context Endpoints ============

@app.get("/context/{session_id}")
async def get_conversation_context(session_id: str):
    """Get the conversation context summary for a session."""
    try:
        return conversation_memory.get_context_summary(session_id)
    except Exception as e:
        logger.logger.error(f"Context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/context/{session_id}")
async def clear_conversation_context(session_id: str):
    """Clear the conversation context for a session."""
    try:
        conversation_memory.clear_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        logger.logger.error(f"Clear context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Language API Endpoints ============

@app.post("/language/detect")
async def detect_text_language(text: str):
    """Detect the language of given text."""
    try:
        lang_code, confidence = detect_language(text)
        lang_info = get_language_info(lang_code)
        return {
            "language_code": lang_code,
            "language_name": lang_info['name'],
            "language_flag": lang_info['flag'],
            "confidence": round(confidence, 3)
        }
    except Exception as e:
        logger.logger.error(f"Language detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/language/translate")
async def translate_text(text: str, source: str = "auto", target: str = "en"):
    """Translate text from source language to target language."""
    try:
        if not language_service.translator:
            raise HTTPException(status_code=503, detail="Translation service unavailable")
        
        translated = language_service.translate(text, source, target)
        if translated is None:
            raise HTTPException(status_code=500, detail="Translation failed")
        
        # Get language info
        source_info = get_language_info(source if source != "auto" else detect_language(text)[0])
        target_info = get_language_info(target)
        
        return {
            "original_text": text,
            "translated_text": translated,
            "source_language": source_info,
            "target_language": target_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/language/supported")
async def get_supported_languages():
    """Get list of supported languages for detection and translation."""
    from backend.utils.language_service import LANGUAGE_NAMES, LANGUAGE_FLAGS
    
    languages = []
    for code, name in LANGUAGE_NAMES.items():
        languages.append({
            "code": code,
            "name": name,
            "flag": LANGUAGE_FLAGS.get(code, "🌐")
        })
    
    return {
        "languages": languages,
        "translation_available": language_service.translator is not None
    }


# ============ Knowledge Graph Endpoints ============

# Initialize knowledge graph builder
graph_builder = KnowledgeGraphBuilder(vector_store)

@app.get("/graph")
async def get_knowledge_graph():
    """Get the full knowledge graph for visualization."""
    try:
        graph_data = graph_builder.build_graph()
        return graph_data
    except Exception as e:
        logger.logger.error(f"Knowledge graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/node/{node_id}")
async def get_graph_node_details(node_id: str):
    """Get detailed information about a specific node."""
    try:
        # Rebuild graph to ensure it's current
        graph_builder.build_graph()
        node_details = graph_builder.get_node_details(node_id)
        return node_details
    except Exception as e:
        logger.logger.error(f"Graph node error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Real-Time Sync Endpoints ============

@app.websocket("/ws/sync")
async def websocket_sync(websocket: WebSocket):
    """WebSocket endpoint for real-time sync notifications."""
    await ws_manager.connect(websocket)
    
    # Send initial status
    await websocket.send_json({
        "type": "connected",
        "message": "Connected to sync notifications",
        "watcher_status": document_watcher.get_status()
    })
    
    try:
        while True:
            # Check for pending changes to broadcast
            if pending_sync_changes:
                changes = pending_sync_changes.copy()
                pending_sync_changes.clear()
                
                for change in changes:
                    await ws_manager.broadcast(change)
            
            # Also listen for client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=1.0
                )
                
                # Handle client commands
                if data.get("command") == "get_status":
                    await websocket.send_json({
                        "type": "status",
                        "watcher_status": document_watcher.get_status()
                    })
                elif data.get("command") == "start_watcher":
                    document_watcher.start()
                    await websocket.send_json({
                        "type": "watcher_started",
                        "message": "File watcher started"
                    })
                elif data.get("command") == "stop_watcher":
                    document_watcher.stop()
                    await websocket.send_json({
                        "type": "watcher_stopped",
                        "message": "File watcher stopped"
                    })
                    
            except asyncio.TimeoutError:
                # No message received, continue loop
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.get("/sync/status")
async def get_sync_status():
    """Get the current sync/watcher status."""
    return {
        "watcher_status": document_watcher.get_status(),
        "pending_changes": len(pending_sync_changes),
        "websocket_connections": len(ws_manager.active_connections),
        "auto_index_enabled": auto_index_enabled,
        "auto_index_queue_size": len(auto_index_queue)
    }


@app.post("/sync/start")
async def start_sync():
    """Start the file watcher."""
    try:
        document_watcher.start()
        return {
            "message": "File watcher started",
            "watch_path": str(document_watcher.watch_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/stop")
async def stop_sync():
    """Stop the file watcher."""
    try:
        document_watcher.stop()
        return {"message": "File watcher stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/files")
async def get_watched_files():
    """Get list of files in the watch folder."""
    try:
        files = document_watcher.scan_existing_files()
        return {
            "watch_path": str(document_watcher.watch_path),
            "file_count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/changes")
async def get_sync_changes():
    """Get pending file changes (polling endpoint)."""
    global pending_sync_changes
    
    # Check for new files not yet tracked (fallback scan)
    if document_watcher.is_running:
        # Get existing tracked files before scanning
        previously_tracked = set(document_watcher.file_hashes.keys())
        
        # Scan for all current files (this will update file_hashes)
        current_files = document_watcher.scan_existing_files()
        
        # Check for files that exist now but weren't tracked before
        for file_info in current_files:
            file_path = file_info['path']
            if file_path not in previously_tracked:
                # New file detected via scan
                found_in_pending = any(c.get('path') == file_path for c in pending_sync_changes)
                if not found_in_pending:
                    pending_sync_changes.append({
                        "type": "file_change",
                        "change_type": "created",
                        "file_name": file_info['name'],
                        "path": file_path,
                        "timestamp": datetime.now().isoformat(),
                        "file_size": file_info['size']
                    })
                    logger.logger.info(f"Sync: detected new file {file_info['name']}")
    
    changes = pending_sync_changes.copy()
    pending_sync_changes.clear()
    return {
        "changes": changes,
        "watcher_status": document_watcher.get_status()
    }


@app.post("/sync/index-file")
async def index_watched_file(file_path: str):
    """Index a specific file from the watch folder."""
    try:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_ext = path.suffix.lower().lstrip('.')
        chunks = []
        
        if file_ext in ['pdf', 'docx', 'txt']:
            chunks = text_processor.process_file(path)
        elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
            chunks = image_processor.process_file(path)
        elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'ogg', 'aac']:
            chunks = audio_processor.process_file(path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        if chunks:
            chunks = embedding_manager.embed_chunks(chunks)
            stored_count = vector_store.add_chunks(chunks)
            
            # Broadcast to WebSocket clients
            await ws_manager.broadcast({
                "type": "file_indexed",
                "file_name": path.name,
                "chunks_created": stored_count
            })
            
            return {
                "message": f"Indexed {path.name}",
                "chunks_created": stored_count
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Index file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/auto-index")
async def toggle_auto_index(enabled: bool):
    """Toggle auto-indexing of new files."""
    global auto_index_enabled
    auto_index_enabled = enabled
    logger.logger.info(f"Auto-index {'enabled' if enabled else 'disabled'}")
    return {
        "auto_index_enabled": auto_index_enabled,
        "message": f"Auto-index {'enabled' if enabled else 'disabled'}"
    }


@app.get("/sync/auto-index/status")
async def get_auto_index_status():
    """Get auto-index status and queue."""
    return {
        "auto_index_enabled": auto_index_enabled,
        "queue_size": len(auto_index_queue),
        "queued_files": [Path(p).name for p in auto_index_queue[:10]]  # Show first 10
    }


@app.post("/sync/auto-index/process")
async def process_auto_index_queue():
    """Process all files in the auto-index queue."""
    global auto_index_queue
    
    if not auto_index_queue:
        return {"message": "Queue is empty", "processed": 0}
    
    processed = 0
    failed = 0
    results = []
    
    # Process each file in the queue
    for file_path in auto_index_queue.copy():
        try:
            path = Path(file_path)
            if not path.exists():
                auto_index_queue.remove(file_path)
                continue
            
            file_ext = path.suffix.lower().lstrip('.')
            chunks = []
            
            if file_ext in ['pdf', 'docx', 'txt']:
                chunks = text_processor.process_file(path)
            elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                chunks = image_processor.process_file(path)
            elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'ogg', 'aac']:
                chunks = audio_processor.process_file(path)
            
            if chunks:
                chunks = embedding_manager.embed_chunks(chunks)
                stored_count = vector_store.add_chunks(chunks)
                results.append({
                    "file": path.name,
                    "chunks": stored_count,
                    "status": "success"
                })
                processed += 1
                
                # Add notification for auto-indexed file
                pending_sync_changes.append({
                    "type": "file_change",
                    "change_type": "auto_indexed",
                    "file_name": path.name,
                    "path": file_path,
                    "timestamp": datetime.now().isoformat(),
                    "file_size": path.stat().st_size
                })
            
            auto_index_queue.remove(file_path)
            
        except Exception as e:
            logger.logger.error(f"Auto-index error for {file_path}: {e}")
            failed += 1
            auto_index_queue.remove(file_path)
    
    return {
        "message": f"Processed {processed} files, {failed} failed",
        "processed": processed,
        "failed": failed,
        "results": results
    }


@app.get("/dump")
async def dump_database():
    """Dump all contents from the vector database for debugging."""
    try:
        # Get all items from the collection
        results = vector_store.collection.get()
        return {
            "count": len(results["ids"]),
            "data": [
                {
                    "id": id,
                    "document": doc,
                    "metadata": meta
                }
                for id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-reasoning-chain")
async def export_reasoning_chain(request: QueryRequest):
    """
    Export a query's reasoning chain as markdown documentation.
    This endpoint runs the query and returns the reasoning chain in markdown format.
    """
    try:
        # Ensure reasoning chain is included
        request.include_reasoning_chain = True
        response = await rag_generator.generate_response(request)
        
        if response.reasoning_chain:
            markdown_content = response.reasoning_chain.to_markdown()
            return {
                "success": True,
                "chain_id": response.reasoning_chain.chain_id,
                "markdown": markdown_content,
                "query": request.query,
                "timestamp": response.reasoning_chain.timestamp
            }
        else:
            return {
                "success": False,
                "error": "No reasoning chain generated"
            }
    except Exception as e:
        logger.logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summarize")
async def summarize_repository():
    """
    Generate an executive summary of all documents in the knowledge base.
    Includes: overview, table of contents, themes, and potential conflicts.
    """
    try:
        # Get all items from the collection
        results = vector_store.collection.get()
        
        if not results["ids"]:
            return {
                "success": True,
                "summary": {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "modalities": [],
                    "sources": [],
                    "themes": [],
                    "executive_summary": "No documents have been uploaded yet. Upload some documents to see a summary of your knowledge base.",
                    "potential_gaps": ["No documents uploaded - knowledge base is empty"],
                    "potential_conflicts": []
                }
            }
        
        # Analyze the repository
        chunks = list(zip(results["ids"], results["documents"], results["metadatas"]))
        
        # Extract unique sources and modalities
        sources_map = {}
        modality_counts = {}
        all_content_samples = []
        
        for chunk_id, content, metadata in chunks:
            source_file = metadata.get("source_file", "Unknown")
            modality = metadata.get("modality", "text")
            
            # Track sources
            if source_file not in sources_map:
                sources_map[source_file] = {
                    "file": source_file,
                    "modality": modality,
                    "chunk_count": 0,
                    "preview": content[:200] + "..." if len(content) > 200 else content
                }
            sources_map[source_file]["chunk_count"] += 1
            
            # Track modalities
            modality_counts[modality] = modality_counts.get(modality, 0) + 1
            
            # Collect content samples for theme analysis
            if len(all_content_samples) < 20:
                all_content_samples.append(content[:300])
        
        sources_list = list(sources_map.values())
        
        # Identify themes using keyword extraction
        themes = _extract_themes(all_content_samples)
        
        # Generate executive summary using LLM
        executive_summary = await _generate_executive_summary(
            sources_list, 
            themes, 
            modality_counts,
            all_content_samples[:5]
        )
        
        # Identify potential gaps
        gaps = _identify_knowledge_gaps(sources_list, modality_counts)
        
        # Check for potential conflicts by analyzing similar chunks
        conflicts = await _detect_potential_conflicts(chunks[:50])  # Limit for performance
        
        return {
            "success": True,
            "summary": {
                "total_documents": len(sources_list),
                "total_chunks": len(chunks),
                "modalities": [
                    {"name": mod, "count": count, "percentage": round(count/len(chunks)*100, 1)}
                    for mod, count in modality_counts.items()
                ],
                "sources": sources_list,
                "themes": themes,
                "executive_summary": executive_summary,
                "potential_gaps": gaps,
                "potential_conflicts": conflicts
            }
        }
        
    except Exception as e:
        logger.logger.error(f"Summarize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_themes(content_samples: list) -> list:
    """Extract main themes from content using keyword analysis."""
    from collections import Counter
    import re
    
    # Common stop words to filter
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
        'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
        'because', 'until', 'while', 'this', 'that', 'these', 'those', 'it',
        'its', 'text', 'extracted', 'document', 'file', 'png', 'jpg', 'pdf'
    }
    
    # Extract words from all samples
    all_words = []
    for content in content_samples:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        all_words.extend([w for w in words if w not in stop_words])
    
    # Get most common words as themes
    word_counts = Counter(all_words)
    top_themes = word_counts.most_common(10)
    
    return [
        {"theme": theme, "frequency": count, "importance": "high" if i < 3 else "medium" if i < 7 else "low"}
        for i, (theme, count) in enumerate(top_themes)
    ]


async def _generate_executive_summary(sources: list, themes: list, modalities: dict, samples: list) -> str:
    """Generate an executive summary using LLM."""
    from backend.generation.llm_client import LLMClient
    
    llm = LLMClient()
    
    # Build context
    source_names = [s["file"].split("/")[-1].split("\\")[-1] for s in sources[:10]]
    theme_words = [t["theme"] for t in themes[:5]]
    modality_list = list(modalities.keys())
    
    prompt = f"""Generate a brief executive summary (3-4 sentences) of a knowledge base with:
- {len(sources)} documents across modalities: {', '.join(modality_list)}
- Key themes: {', '.join(theme_words)}
- Sample documents: {', '.join(source_names[:5])}

Content samples:
{chr(10).join(samples[:3])}

Write a professional summary that describes what this knowledge base contains and its main topics."""

    try:
        summary = await llm.generate(prompt, max_tokens=150, temperature=0.3)
        return summary.strip()
    except Exception as e:
        # Fallback to generated summary
        return f"This knowledge base contains {len(sources)} documents across {', '.join(modality_list)} modalities. Key topics include {', '.join(theme_words[:3])}. The repository includes files such as {', '.join(source_names[:3])}."


def _identify_knowledge_gaps(sources: list, modalities: dict) -> list:
    """Identify potential gaps in the knowledge base."""
    gaps = []
    
    # Check modality coverage
    if "image" not in modalities:
        gaps.append("📷 No images uploaded - visual information may be missing")
    if "audio" not in modalities:
        gaps.append("🎙️ No audio files - spoken content not captured")
    if "text" not in modalities:
        gaps.append("📄 No text documents - consider adding manuals or documentation")
    
    # Check document count
    if len(sources) < 3:
        gaps.append("📚 Limited sources - consider uploading more documents for comprehensive coverage")
    
    # Check chunk distribution
    total_chunks = sum(s["chunk_count"] for s in sources)
    if total_chunks < 10:
        gaps.append("📊 Low content density - documents may be too brief for detailed answers")
    
    # Check for diversity
    unique_modalities = len(modalities)
    if unique_modalities == 1:
        gaps.append(f"🔄 Single modality ({list(modalities.keys())[0]}) - consider multimodal content")
    
    return gaps


async def _detect_potential_conflicts(chunks: list) -> list:
    """Detect potential conflicting information across chunks."""
    conflicts = []
    
    # Look for numerical conflicts in similar content
    import re
    
    # Group chunks by similar topics
    topic_chunks = {}
    for chunk_id, content, metadata in chunks:
        # Extract numbers from content
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\s*(v|V|volt|volts|kg|Kg|KG|lbs|°C|°F|%|percent)\b', content)
        if numbers:
            source = metadata.get("source_file", "Unknown").split("/")[-1].split("\\")[-1]
            for num, unit in numbers:
                key = unit.lower()
                if key not in topic_chunks:
                    topic_chunks[key] = []
                topic_chunks[key].append({
                    "value": float(num),
                    "unit": unit,
                    "source": source,
                    "snippet": content[:100]
                })
    
    # Find conflicts (different values for same unit type)
    for unit, items in topic_chunks.items():
        if len(items) >= 2:
            values = [item["value"] for item in items]
            if max(values) != min(values):
                # There's a discrepancy
                conflicts.append({
                    "topic": f"Conflicting {unit} values",
                    "sources": [item["source"] for item in items[:2]],
                    "values": [f"{item['value']}{item['unit']}" for item in items[:2]],
                    "severity": "high" if abs(max(values) - min(values)) / max(values) > 0.5 else "medium"
                })
    
    return conflicts[:5]  # Limit to top 5 conflicts


# ============ Cloud Storage Integration Endpoints ============

@app.get("/cloud/providers")
async def get_cloud_providers():
    """Get list of supported and connected cloud storage providers."""
    return {
        "supported": [p.value for p in CloudProvider],
        "connected": cloud_storage_manager.get_connected_providers()
    }


@app.post("/cloud/connect")
async def connect_cloud_provider(
    provider: str,
    access_token: str = None,
    refresh_token: str = None,
    api_key: str = None,
    api_secret: str = None,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_region: str = None,
    s3_bucket: str = None
):
    """Connect to a cloud storage provider."""
    try:
        # Validate provider
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid provider: {provider}. Supported: {[p.value for p in CloudProvider]}"
            )
        
        # Create credentials
        credentials = CloudCredentials(
            provider=cloud_provider,
            access_token=access_token,
            refresh_token=refresh_token,
            api_key=api_key,
            api_secret=api_secret,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_bucket=s3_bucket
        )
        
        result = await cloud_storage_manager.connect_provider(credentials)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Connection failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud connect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/disconnect")
async def disconnect_cloud_provider(provider: str):
    """Disconnect from a cloud storage provider."""
    try:
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        result = await cloud_storage_manager.disconnect_provider(cloud_provider)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud disconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cloud/{provider}/files")
async def list_cloud_files(provider: str, folder_id: str = None):
    """List files from a cloud storage provider."""
    try:
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        if provider not in cloud_storage_manager.get_connected_providers():
            raise HTTPException(status_code=400, detail=f"Provider {provider} is not connected")
        
        files = await cloud_storage_manager.list_files(cloud_provider, folder_id)
        
        return {
            "provider": provider,
            "folder_id": folder_id,
            "file_count": len(files),
            "files": [f.to_dict() for f in files]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud list files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cloud/{provider}/search")
async def search_cloud_files(provider: str, query: str):
    """Search files in a cloud storage provider."""
    try:
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        if provider not in cloud_storage_manager.get_connected_providers():
            raise HTTPException(status_code=400, detail=f"Provider {provider} is not connected")
        
        files = await cloud_storage_manager.search_files(cloud_provider, query)
        
        return {
            "provider": provider,
            "query": query,
            "result_count": len(files),
            "files": [f.to_dict() for f in files]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cloud/search-all")
async def search_all_cloud_providers(query: str):
    """Search files across all connected cloud storage providers."""
    try:
        results = await cloud_storage_manager.search_all_providers(query)
        
        total_files = sum(len(files) for files in results.values())
        
        return {
            "query": query,
            "total_results": total_files,
            "providers": {
                provider: {
                    "count": len(files),
                    "files": [f.to_dict() for f in files]
                }
                for provider, files in results.items()
            }
        }
        
    except Exception as e:
        logger.logger.error(f"Cloud search all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/{provider}/import")
async def import_cloud_file(provider: str, file_id: str, auto_index: bool = False):
    """Import a file from cloud storage to the local knowledge base."""
    try:
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        if provider not in cloud_storage_manager.get_connected_providers():
            raise HTTPException(status_code=400, detail=f"Provider {provider} is not connected")
        
        # Import the file
        result = await cloud_storage_manager.import_file(
            cloud_provider, 
            file_id, 
            settings.cloud_import_dir
        )
        
        if not result or not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to import file")
        
        # Auto-index if requested
        if auto_index:
            local_path = Path(result["local_path"])
            file_ext = local_path.suffix.lower().lstrip('.')
            chunks = []
            
            try:
                if file_ext in ['pdf', 'docx', 'txt']:
                    chunks = text_processor.process_file(local_path)
                elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                    chunks = image_processor.process_file(local_path)
                elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'ogg', 'aac']:
                    chunks = audio_processor.process_file(local_path)
                
                if chunks:
                    chunks = embedding_manager.embed_chunks(chunks)
                    stored_count = vector_store.add_chunks(chunks)
                    result["auto_indexed"] = True
                    result["chunks_created"] = stored_count
            except Exception as e:
                logger.logger.error(f"Auto-index error: {e}")
                result["auto_indexed"] = False
                result["index_error"] = str(e)
        
        # Broadcast notification
        await ws_manager.broadcast({
            "type": "cloud_import",
            "provider": provider,
            "file_name": result["file_name"],
            "file_size": result["file_size"],
            "auto_indexed": result.get("auto_indexed", False)
        })
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/{provider}/import-batch")
async def import_cloud_files_batch(provider: str, file_ids: list[str], auto_index: bool = False):
    """Import multiple files from cloud storage."""
    try:
        try:
            cloud_provider = CloudProvider(provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")
        
        if provider not in cloud_storage_manager.get_connected_providers():
            raise HTTPException(status_code=400, detail=f"Provider {provider} is not connected")
        
        # Import files
        results = await cloud_storage_manager.batch_import(
            cloud_provider,
            file_ids,
            settings.upload_dir
        )
        
        # Auto-index if requested
        if auto_index:
            for result in results:
                if result.get("success") and result.get("local_path"):
                    local_path = Path(result["local_path"])
                    file_ext = local_path.suffix.lower().lstrip('.')
                    chunks = []
                    
                    try:
                        if file_ext in ['pdf', 'docx', 'txt']:
                            chunks = text_processor.process_file(local_path)
                        elif file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
                            chunks = image_processor.process_file(local_path)
                        elif file_ext in ['mp3', 'wav', 'm4a', 'mp4', 'flac', 'ogg', 'aac']:
                            chunks = audio_processor.process_file(local_path)
                        
                        if chunks:
                            chunks = embedding_manager.embed_chunks(chunks)
                            stored_count = vector_store.add_chunks(chunks)
                            result["auto_indexed"] = True
                            result["chunks_created"] = stored_count
                    except Exception as e:
                        result["auto_indexed"] = False
                        result["index_error"] = str(e)
        
        successful = sum(1 for r in results if r.get("success"))
        
        return {
            "total": len(file_ids),
            "successful": successful,
            "failed": len(file_ids) - successful,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Cloud batch import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cloud/reconnect")
async def reconnect_cloud_providers():
    """Reconnect to all saved cloud storage providers."""
    try:
        results = await cloud_storage_manager.load_saved_connections()
        
        successful = sum(1 for v in results.values() if v)
        
        return {
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results
        }
        
    except Exception as e:
        logger.logger.error(f"Cloud reconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Web Search API Endpoints ============

@app.get("/web-search/status")
async def get_web_search_status():
    """Get the current status of the web search service."""
    return web_search_service.get_status()


@app.post("/web-search/enable")
async def enable_web_search():
    """Enable the web search service."""
    web_search_service.enable()
    return {
        "message": "Web search enabled",
        "status": web_search_service.get_status()
    }


@app.post("/web-search/disable")
async def disable_web_search():
    """Disable the web search service."""
    web_search_service.disable()
    return {
        "message": "Web search disabled",
        "status": web_search_service.get_status()
    }


@app.post("/web-search/search")
async def perform_web_search(query: str, num_results: int = 5):
    """Perform a direct web search (independent of RAG query)."""
    try:
        results = await search_web(query, num_results)
        return {
            "query": query,
            "results": [r.to_dict() for r in results],
            "count": len(results)
        }
    except Exception as e:
        logger.logger.error(f"Web search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/web-search/clear-cache")
async def clear_web_search_cache():
    """Clear the web search cache."""
    web_search_service.clear_cache()
    return {
        "message": "Web search cache cleared",
        "status": web_search_service.get_status()
    }


# ============ Smart Email/Report Drafter Endpoints ============

from backend.generation.email_drafter import (
    EmailDrafter, DraftRequest, DraftResponse, 
    DocumentType, DraftTone
)

# Initialize email drafter
email_drafter = EmailDrafter(retriever)


@app.post("/draft", response_model=DraftResponse)
async def draft_document(request: DraftRequest):
    """
    Draft a professional email, report, or other document using knowledge base context.
    
    Example:
    POST /draft
    {
        "communication_goal": "Inform client about project delay due to resource constraints",
        "document_type": "email",
        "tone": "professional",
        "recipient": "client",
        "source_documents": ["project_status.pdf"],
        "include_sources": true,
        "sender_name": "Project Manager"
    }
    """
    try:
        response = await email_drafter.draft_document(request)
        logger.logger.info(
            f"📧 Drafted {request.document_type.value}: "
            f"{response.word_count} words, {len(response.sources_used)} sources"
        )
        return response
    except Exception as e:
        logger.logger.error(f"Draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/draft/templates")
async def get_draft_templates():
    """Get available document templates and their structures."""
    return {
        "templates": [
            {
                "type": "email",
                "name": "Email",
                "icon": "📧",
                "description": "Professional email with subject, greeting, body, and signature",
                "structure": ["subject", "greeting", "opening", "body", "closing", "signature"]
            },
            {
                "type": "report",
                "name": "Report",
                "icon": "📊",
                "description": "Formal report with executive summary, findings, and recommendations",
                "structure": ["title", "executive_summary", "findings", "recommendations", "conclusion"]
            },
            {
                "type": "memo",
                "name": "Memo",
                "icon": "📝",
                "description": "Internal memo with header, purpose, and action items",
                "structure": ["header", "purpose", "background", "key_points", "action_items"]
            },
            {
                "type": "summary",
                "name": "Summary",
                "icon": "📋",
                "description": "Concise summary with key points and overview",
                "structure": ["overview", "key_points", "conclusion"]
            },
            {
                "type": "letter",
                "name": "Letter",
                "icon": "✉️",
                "description": "Formal letter with date, greeting, body, and signature",
                "structure": ["date", "greeting", "opening", "body", "closing", "signature"]
            }
        ]
    }


@app.get("/draft/tones")
async def get_draft_tones():
    """Get available tone options for drafting."""
    return {
        "tones": [
            {"value": "formal", "label": "Formal", "icon": "🎩", "description": "Formal, professional language"},
            {"value": "professional", "label": "Professional", "icon": "💼", "description": "Clear, professional tone"},
            {"value": "friendly", "label": "Friendly", "icon": "😊", "description": "Warm, approachable language"},
            {"value": "urgent", "label": "Urgent", "icon": "⚡", "description": "Conveys urgency and importance"},
            {"value": "apologetic", "label": "Apologetic", "icon": "🙏", "description": "Sincere, humble tone"},
            {"value": "confident", "label": "Confident", "icon": "💪", "description": "Assertive, decisive language"}
        ]
    }


# ============ Automated Presentation Generator Endpoints ============

from backend.generation.presentation_generator import (
    PresentationGenerator, PresentationRequest, PresentationResponse,
    PresentationTheme
)
from fastapi.responses import FileResponse

# Initialize presentation generator
presentation_generator = PresentationGenerator(retriever)


@app.post("/presentation", response_model=PresentationResponse)
async def generate_presentation(request: PresentationRequest):
    """
    Generate an automated PowerPoint presentation from knowledge base.
    
    Example:
    POST /presentation
    {
        "topic": "Q4 2025 Results Summary",
        "source_documents": ["quarterly_report.pdf", "sales_data.xlsx"],
        "num_slides": 5,
        "theme": "professional",
        "include_title_slide": true,
        "include_summary_slide": true
    }
    """
    try:
        response = await presentation_generator.generate_presentation(request)
        logger.logger.info(
            f"📊 Generated presentation: {response.filename} "
            f"({response.num_slides} slides, {response.processing_time:.1f}s)"
        )
        return response
    except Exception as e:
        logger.logger.error(f"Presentation generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/presentations/{filename}")
async def download_presentation(filename: str):
    """Download a generated presentation file."""
    filepath = settings.upload_dir / "presentations" / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Presentation not found")
    
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@app.get("/presentation/themes")
async def get_presentation_themes():
    """Get available presentation themes."""
    return {
        "themes": [
            {
                "value": "professional",
                "name": "Professional",
                "icon": "💼",
                "description": "Classic dark blue with orange accents",
                "colors": ["#1E3A5F", "#F08030"]
            },
            {
                "value": "modern",
                "name": "Modern",
                "icon": "🎨",
                "description": "Purple and teal gradient style",
                "colors": ["#6C5CE7", "#00D2D3"]
            },
            {
                "value": "minimal",
                "name": "Minimal",
                "icon": "⬜",
                "description": "Clean grayscale with blue accents",
                "colors": ["#2D3A4B", "#007BFF"]
            },
            {
                "value": "corporate",
                "name": "Corporate",
                "icon": "🏢",
                "description": "Traditional corporate blue and gold",
                "colors": ["#00528A", "#FFB800"]
            },
            {
                "value": "creative",
                "name": "Creative",
                "icon": "✨",
                "description": "Vibrant pink and teal",
                "colors": ["#E04389", "#4ECEC3"]
            }
        ]
    }


@app.get("/presentation/list")
async def list_presentations():
    """List all generated presentations."""
    presentations_dir = settings.upload_dir / "presentations"
    presentations_dir.mkdir(exist_ok=True)
    
    files = []
    for f in presentations_dir.glob("*.pptx"):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "download_url": f"/presentations/{f.name}"
        })
    
    # Sort by creation time, newest first
    files.sort(key=lambda x: x["created"], reverse=True)
    
    return {
        "presentations": files,
        "count": len(files)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)

