# 🧠 Multimodal RAG System

> **Table No. 18 | Team: ManageSphere**
>
> **Evidence-Based Multimodal Retrieval-Augmented Generation**
> 
> A production-ready system for ingesting, retrieving, and reasoning across text, images, and audio with explicit uncertainty handling and conflict detection.

## 🎯 Features

### Core Capabilities
- ✅ **Multimodal Data Ingestion**: PDF, DOCX, TXT, Images (JPG, PNG), Audio (MP3, WAV)
- ✅ **Unified Cross-Modal Retrieval**: Semantic search across all modalities
- ✅ **Evidence-Grounded Generation**: All responses cite sources
- ✅ **Conflict Detection**: Identifies and presents contradictory information
- ✅ **Uncertainty Awareness**: Explicitly acknowledges gaps and low confidence
- ✅ **Adaptive Retrieval**: Dynamically adjusts search strategy
- ✅ **Hallucination Suppression**: Refuses to answer without evidence
- ✅ **🌍 Auto-Translate Knowledge Base**: Ask in 30+ languages, get answers in your language

### System Design
- **No heavy resources**: Uses lightweight models (Llama 3.2 3B, CLIP ViT-B/32, Whisper Tiny)
- **No blind vector search**: Every retrieval decision is logged and justified
- **Explainable pipeline**: Transparent confidence scoring and conflict detection
- **Failure-tolerant**: Graceful degradation when components unavailable

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- 8GB RAM minimum
- ~5GB disk space for models
- (Optional) Ollama installed for local LLM

### Installation

1. **Clone the repository**
```bash
cd multimodal_rag
```

2. **Create virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env to configure:
# - OLLAMA_BASE_URL (if using Ollama)
# - OPENROUTER_API_KEY (if using fallback API)
```

5. **Install Ollama (recommended for local LLM)**
```bash
# Windows: Download from https://ollama.ai
# Then pull the model:
ollama pull llama3.2:3b
```

### Running the System

```bash
# Start the server
cd backend
python app.py

# Or using uvicorn directly
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 in your browser.

## 📖 Usage

### 1. Upload Documents

Drag and drop or click to upload:
- **Text**: PDF, DOCX, TXT files
- **Images**: JPG, PNG, diagrams, charts
- **Audio**: MP3, WAV recordings

The system will:
- Extract content and metadata
- Generate embeddings
- Store in vector database
- Display chunk count

### 2. Query the Knowledge Base

Ask questions naturally:
- "What are the main findings about X?"
- "Show me diagrams related to Y"
- "What was said about Z in the audio?"
- "Compare the perspectives on W"

**Or ask in your language** 🌍:
- 🇮🇳 "यह मशीन कैसे काम करती है?" (Hindi)
- 🇪🇸 "¿Cómo funciona esto?" (Spanish)
- 🇫🇷 "Comment ça marche?" (French)
- 🇯🇵 "これはどのように機能しますか？" (Japanese)

The system automatically detects your language and responds accordingly! See [AUTO_TRANSLATE_FEATURE.md](AUTO_TRANSLATE_FEATURE.md) for details.

### 3. Interpret Responses

**High Confidence** (Green Badge):
- Strong evidence from multiple sources
- Cross-modal agreement
- Full citations provided

**Medium Confidence** (Yellow Badge):
- Limited sources or single modality
- Explicit caveats about uncertainty
- Distinguishes facts from inferences

**Low Confidence / Refusal** (Red Badge):
- Insufficient evidence
- Lists missing information
- Suggests next steps

**Conflicts Detected** (Orange Warning):
- Contradictory sources identified
- Multiple perspectives presented
- User decides which to trust

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                         │
│                    (HTML + CSS + JavaScript)                  │
└────────────┬──────────────────────────────────┬──────────────┘
             │                                  │
             ▼                                  ▼
┌─────────────────────┐           ┌─────────────────────────┐
│   Upload Endpoint   │           │    Query Endpoint       │
│   /upload (POST)    │           │    /query (POST)        │
└──────────┬──────────┘           └──────────┬──────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────┐           ┌─────────────────────────┐
│  Ingestion Pipeline │           │   RAG Generator         │
│  - Text Processor   │      ┌────┤  - Query Analyzer       │
│  - Image Processor  │      │    │  - Cross-Modal Retriever│
│  - Audio Processor  │      │    │  - Confidence Scorer    │
└──────────┬──────────┘      │    │  - Conflict Detector    │
           │                 │    │  - LLM Client           │
           ▼                 │    └─────────┬───────────────┘
┌─────────────────────┐      │              │
│ Embedding Manager   │      │              │
│  - Text Embedder    │      │              │
│  - Image Embedder   │      │              │
│  (Cross-Modal Align)│      │              │
└──────────┬──────────┘      ▼              ▼
           │           ┌─────────────────────────┐
           └──────────▶│    Vector Store         │
                       │    (ChromaDB)           │
                       │  - HNSW Index           │
                       │  - Metadata Filtering   │
                       └─────────────────────────┘
```

## 🔬 Technical Details

### Embedding Strategy
- **Text**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Images**: CLIP ViT-B/32 → PCA projection to 384-dim
- **Audio**: Whisper Tiny transcription → Text embedding
- **Cross-Modal**: Unified 384-dim space for semantic alignment

### Retrieval Pipeline
1. **Query Analysis**: Detect required modalities and complexity
2. **Multi-Modal Retrieval**: Search each modality independently
3. **Cross-Modal Scoring**: Boost results with multi-modal support
4. **Re-Ranking**: Combine relevance × confidence, remove duplicates

### Confidence Scoring
```
Confidence = (0.5 × avg_relevance) + (0.5 × avg_source_quality)
           + cross_modal_bonus + diversity_bonus

High:   ≥ 0.8
Medium: 0.6 - 0.8
Low:    < 0.6 (triggers refusal or caveats)
```

### Conflict Detection
1. Extract factual claims from each source
2. Compute pairwise semantic similarity
3. Detect contradictions via negation patterns or numerical differences
4. Present all perspectives without collapsing

## 📊 Evaluation Criteria Met

| Requirement | Implementation | Status |
|------------|----------------|--------|
| Multimodal ingestion | PDF, DOCX, TXT, JPG, PNG, MP3, WAV | ✅ |
| Unified storage | Single ChromaDB collection with modality tags | ✅ |
| Cross-modal retrieval | CLIP-based shared embedding space | ✅ |
| Intent-aware strategy | Query analyzer with logged reasoning | ✅ |
| Evidence-based generation | All responses cite [Source X] | ✅ |
| Uncertainty awareness | Confidence scoring + refusal logic | ✅ |
| Conflict detection | Claim extraction + semantic comparison | ✅ |
| Adaptive retrieval | Iterative refinement logged | ✅ |
| Hallucination suppression | Refuses when confidence < threshold | ✅ |
| Failure tolerance | Graceful degradation, error handling | ✅ |

## 🧪 Testing

```bash
# Run unit tests
pytest tests/ -v

# Test ingestion
pytest tests/test_ingestion.py -v

# Test retrieval
pytest tests/test_retrieval.py -v

# Test generation
pytest tests/test_generation.py -v
```

## 📁 Project Structure

```
multimodal_rag/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── config.py              # Configuration
│   ├── models/                # Data models
│   ├── ingestion/             # File processors
│   ├── embeddings/            # Embedding generators
│   ├── storage/               # Vector database
│   ├── retrieval/             # Search logic
│   ├── generation/            # RAG pipeline
│   └── utils/                 # Logging, metrics
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       └── index.html
├── data/
│   ├── uploads/               # Uploaded files
│   ├── processed/             # Processed data
│   └── chroma_db/             # Vector database
├── tests/                     # Test suite
├── requirements.txt           # Dependencies
├── .env.example               # Environment template
└── README.md
```

## 🔧 Configuration

Edit `.env` to customize:

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OPENROUTER_API_KEY=your_key_here  # Fallback

# Retrieval
DEFAULT_TOP_K=10
CONFIDENCE_THRESHOLD=0.6
MAX_RETRIEVAL_ITERATIONS=3

# Upload Limits
MAX_FILE_SIZE_MB=50
```

## 🎓 Example Queries

### Simple Text Query
```
Q: "What is photosynthesis?"
A: [High Confidence] Photosynthesis is the process by which plants convert light 
   energy to chemical energy [Source 1]. It occurs in chloroplasts [Source 2].
```

### Cross-Modal Query
```
Q: "Show me diagrams of the water cycle"
A: [Medium Confidence] Retrieved 3 images showing evaporation, condensation, and 
   precipitation [Source 1 - image], with supporting text descriptions [Source 2, 3].
```

### Conflict Query
```
Q: "What is the optimal temperature for enzyme activity?"
A: [Conflict Detected] Source 1 indicates 37°C for human enzymes, while Source 2 
   states thermophilic enzymes work at 70-90°C. Both are correct for different contexts.
```

### Refusal Example
```
Q: "What is the stock price of company X?"
A: [Unable to Answer] No evidence found. Please upload financial documents or 
   market data to enable this query.
```

## 🤝 Contributing

**Team ManageSphere | Table No. 18**

Built for the **Multimodal RAG System Hackathon**.

GitHub: [rahulranjan9770](https://github.com/rahulranjan9770)

## 📄 License

MIT License

## 🙏 Acknowledgments

- **Sentence Transformers**: Text embeddings
- **OpenAI CLIP**: Image-text alignment
- **Whisper**: Audio transcription
- **ChromaDB**: Vector database
- **Ollama**: Local LLM inference

---

**Built with ❤️ for responsible, evidence-based AI**
