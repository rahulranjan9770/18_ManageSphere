# Quick Start Guide

## Installation Steps

### 1. Install Dependencies (One-Time Setup)

Due to the large ML model downloads, we'll install in stages:

**Stage 1: Core Web Framework** (✅ Completed)
```powershell
cd multimodal_rag
python -m pip install fastapi uvicorn python-multipart aiofiles jinja2 pydantic pydantic-settings python-dotenv httpx
```

**Stage 2: ML & Vector Database** (Installing now...)
```powershell
python -m pip install chromadb sentence-transformers torch torchvision pypdf python-docx pillow numpy scikit-learn
```

**Stage 3: Optional Audio Support**
```powershell
python -m pip install openai-whisper transformers chardet
```

### 2. Start the Server

**Option A: Use the startup script (Recommended)**
```powershell
.\start.ps1
# Or double-click start.bat
```

**Option B: Manual start**
```powershell
cd backend
python app.py
```

### 3. Access the Application

Open your browser to: **http://localhost:8000**

---

## First Time Usage

### Without Ollama (Simplified Mode)

The system will work without Ollama, but will show error messages for LLM generation. You can still:
- Upload documents ✅
- Create embeddings ✅
- Retrieve results ✅

But generation will fail until you either:
1. Install Ollama (see below)
2. Configure an API fallback in `.env`

### With Ollama (Full Features)

1. **Download Ollama**: https://ollama.ai
2. **Install the model**:
   ```powershell
   ollama pull llama3.2:3b
   ```
3. **Verify it's running**:
   ```powershell
   ollama list
   ```

---

## Troubleshooting

### Issue: "Module not found" errors

**Solution**: Make sure you're in the `multimodal_rag` directory when running Python:
```powershell
cd "C:\Users\Rahul kumar\gita\multimodal_rag"
python backend/app.py
```

### Issue: Port 8000 already in use

**Solution**: Change the port in `.env`:
```
PORT=8001
```

### Issue: Large download times

**Solution**: The first installation downloads ~3-5GB of models. This is normal. Go get coffee ☕

### Issue: Ollama not connecting

**Solution**: 
1. Check Ollama is running: `ollama list`
2. Verify URL in `.env`: `OLLAMA_BASE_URL=http://localhost:11434`
3. Or configure API fallback in `.env`

---

## Testing Without Full Installation

If you want to test the basic structure before installing all ML dependencies:

1. **Test Upload Endpoint**:
   ```powershell
   # Start server (will have import errors for ML libs, that's OK)
   cd backend
   python -c "from fastapi import FastAPI; print('FastAPI works!')"
   ```

2. **Test File Structure**:
   ```powershell
   ls backend/*.py
   ls backend/*/
   ```

---

## What's Installed So Far

- ✅ FastAPI (web framework)
- ✅ Pydantic (data validation)
- ✅ Basic dependencies
- ⏳ ChromaDB (vector database) - Installing...
- ⏳ Sentence Transformers (embeddings) - Installing...
- ⏳ PyTorch (ML backend) - Installing...
- ⏳ CLIP (image embeddings) - Will download on first use

**Estimated total install time**: 5-10 minutes (depending on internet speed)

---

## Next Steps After Installation

1. ✅ Wait for ML dependencies to finish installing
2. Run: `.\start.ps1` or `python backend/app.py`
3. Open http://localhost:8000
4. Upload a test document (PDF or text file)
5. Ask a question about it
6. See the system retrieve and cite evidence!

---

## Minimal Test (No Ollama Required)

You can test the ingestion and retrieval without Ollama:

1. Upload a PDF document
2. Check `/stats` endpoint: http://localhost:8000/stats
3. See chunk count increase
4. Query will fail at generation step (expected without LLM)

## Full Demo (With Ollama)

1. Install Ollama + llama3.2:3b
2. Upload multiple documents (text, images if available)
3. Ask: "What are the main topics in the uploaded documents?"
4. See evidence-based response with citations!

---

**Current Status**: Installing ML dependencies...  
**Time**: ~3-8 minutes remaining  
**Next**: Wait for installation, then run `.\start.ps1`
