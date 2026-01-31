# 🚀 How to Run the Multimodal RAG Project

## Project Architecture

This is a **unified application** where **one FastAPI server serves both the backend API and frontend UI**.

```
┌─────────────────────────────────────┐
│   FastAPI Server (Port 8000)        │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Backend API Endpoints       │   │
│   │  /upload, /query, etc.      │   │
│   └─────────────────────────────┘   │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Frontend (Static Files)     │   │
│   │  HTML, CSS, JavaScript      │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

**There is NO separate frontend and backend server** - everything runs on one server!

---

## 🎯 Quick Commands

### Method 1: Using PowerShell Script (Recommended)
```powershell
cd "c:\Users\Rahul kumar\gita\multimodal_rag"
.\start.ps1
```

**What it does:**
- Automatically finds an available port (8000-8010)
- Starts the unified server
- Serves both API and UI

---

### Method 2: Using Batch Script (Alternative)
```cmd
cd "c:\Users\Rahul kumar\gita\multimodal_rag"
start.bat
```

**What it does:**
- Starts the server on port 8000
- If port is busy, you'll get an error

---

### Method 3: Using Python Directly (Full Control)
```powershell
cd "c:\Users\Rahul kumar\gita\multimodal_rag"
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

**What it does:**
- Starts FastAPI server
- `--reload`: Auto-restarts on code changes (development mode)
- `--host 0.0.0.0`: Makes it accessible from other devices on your network

---

### Method 4: Using Custom Port
```powershell
cd "c:\Users\Rahul kumar\gita\multimodal_rag"
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

**Use this if:**
- Port 8000 is already in use
- You want to run on a different port

---

## 🌐 Accessing the Application

Once the server starts, you'll see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Access points:
- **Main Application:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs (FastAPI auto-generated docs)
- **Alternative API Docs:** http://localhost:8000/redoc

---

## 🛠️ Current Running Status

**Backend is already running!**

According to your terminal:
```
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
Running for: 2m49s
```

✅ **You can access it now at:** http://localhost:8000

---

## 🔄 Managing the Server

### Stop the Server
```
Press Ctrl+C in the terminal
```

### Restart the Server
```powershell
# Stop with Ctrl+C first, then:
cd "c:\Users\Rahul kumar\gita\multimodal_rag"
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📋 Complete Workflow

### 1. **First Time Setup**
```powershell
# Navigate to project
cd "c:\Users\Rahul kumar\gita\multimodal_rag"

# Install dependencies (if not done)
pip install -r requirements.txt

# Configure environment (if needed)
# Edit .env file with your settings
```

### 2. **Start the Server**
```powershell
# Using PowerShell script (recommended)
.\start.ps1

# OR using Python directly
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. **Access the Application**
- Open browser: http://localhost:8000
- Upload documents
- Ask questions

### 4. **Stop the Server**
- Press `Ctrl+C` in terminal

---

## 🔍 Troubleshooting

### Port Already in Use
```powershell
# Option 1: Use PowerShell script (auto-finds available port)
.\start.ps1

# Option 2: Manually specify different port
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

### Module Not Found Errors
```powershell
# Ensure you're in the right directory
cd "c:\Users\Rahul kumar\gita\multimodal_rag"

# Reinstall dependencies
pip install -r requirements.txt
```

### Python Not Found
```powershell
# Check Python installation
python --version

# Or try
python3 --version
```

---

## 📦 What Gets Served?

When you run the server:

### Backend API (FastAPI)
- `/upload` - Upload documents
- `/query` - Query knowledge base
- `/stats` - System statistics
- `/reset` - Reset database
- `/sync/*` - File sync endpoints
- `/language/*` - Translation endpoints
- And many more...

### Frontend UI
- Static files from `frontend/static/`
- Templates from `frontend/templates/`
- Served at root `/`

---

## 💡 Key Points

1. **Single Server**: One command runs everything
2. **No Separate Frontend**: Frontend is served by FastAPI
3. **Port 8000**: Default port (configurable)
4. **Auto-Reload**: Use `--reload` flag for development
5. **Already Running**: Your server is currently active!

---

## 🎨 Features Available

Once running, you can:
- ✅ Upload multimodal documents (PDF, DOCX, Images, Audio)
- ✅ Query in 30+ languages
- ✅ Get evidence-based responses
- ✅ View conflict detection
- ✅ Manage conversation context
- ✅ Sync files in real-time
- ✅ Generate presentations
- ✅ And much more!

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| **Start Server (Easy)** | `.\start.ps1` |
| **Start Server (Manual)** | `python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000` |
| **Start with Auto-Reload** | `python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload` |
| **Stop Server** | `Ctrl+C` |
| **Access UI** | http://localhost:8000 |
| **Access API Docs** | http://localhost:8000/docs |

---

**Built by Team ManageSphere | Table No. 18**
