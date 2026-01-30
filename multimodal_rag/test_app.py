"""Preview server showing the full frontend design."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Multimodal RAG System - Frontend Preview")

# Mount static files
if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/")
async def root():
    """Serve the main frontend interface."""
    return FileResponse("frontend/templates/index.html")

@app.get("/health")
async def health():
    return {"status": "preview", "message": "Frontend preview mode"}

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("  🎨 Multimodal RAG System - Frontend Preview")
    print("  📍 http://localhost:8000")
    print("  Note: This is a UI preview. Backend features will be")
    print("        available once all dependencies are installed.")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
