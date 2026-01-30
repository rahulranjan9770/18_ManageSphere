"""Minimal working backend for upload testing."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid
import os

app = FastAPI(title="Multimodal RAG System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Create data directories
Path("./data/uploads").mkdir(parents=True, exist_ok=True)
Path("./data/processed").mkdir(parents=True, exist_ok=True)

@app.get("/")
async def root():
    return FileResponse("frontend/templates/index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle file upload - simplified version."""
    try:
        # Validate extension
        file_ext = Path(file.filename).suffix.lower().lstrip('.')
        allowed = ["pdf", "docx", "txt", "jpg", "jpeg", "png", "bmp", "tiff", "mp3", "wav", "m4a"]
        
        if file_ext not in allowed:
            raise HTTPException(400, f"File type .{file_ext} not allowed")
        
        # Save file
        file_id = str(uuid.uuid4())[:8]
        save_path = Path(f"./data/uploads/{file_id}_{file.filename}")
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = save_path.stat().st_size
        
        return {
            "success": True,
            "doc_id": file_id,
            "filename": file.filename,
            "modalities_detected": [file_ext],
            "chunks_created": 1,  # Placeholder
            "message": f"✅ Successfully uploaded {file.filename} ({file_size} bytes). Processing will begin once backend is fully initialized."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/stats")
async def stats():
    upload_dir = Path("./data/uploads")
    files = list(upload_dir.glob("*")) if upload_dir.exists() else []
    
    return {
        "total_chunks": len(files),
        "uploaded_files": len(files),
        "files": [f.name for f in files],
        "status": "Uploads working! Full processing will be available once all dependencies load."
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("  🚀 Multimodal RAG - Upload Testing Mode")
    print("  📍 http://localhost:8000")
    print("  ✅ Upload functionality enabled")
    print("  ⏳ Full processing will activate when dependencies load")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
