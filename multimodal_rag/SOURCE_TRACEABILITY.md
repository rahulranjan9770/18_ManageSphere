# 🔗 Source Chain Traceability (Evidence Provenance)

> **See exactly HOW your answer was derived — full transparency into the RAG pipeline**

## Overview

The Source Chain Traceability feature provides complete visibility into how the RAG system derives its answers. Every step of the pipeline is tracked, timed, and made visible to users, building trust through transparency.

## Key Features

### 1. 📊 Key Insights Panel
At a glance summary of what happened during query processing:
- ✓ Success indicators (green)
- ⚠️ Warnings (yellow)
- ❌ Errors (red)

### 2. 🔄 Pipeline Visualization
Interactive step-by-step visualization of the 6-stage RAG pipeline:

| Stage | Name | Description |
|-------|------|-------------|
| 1 | **Query Analysis** | Detects query intent (explanation, procedural, comparison, causal, visual) |
| 2 | **Evidence Retrieval** | Semantic search across the knowledge base |
| 3 | **Confidence Assessment** | Evaluates evidence quality and coverage |
| 4 | **Conflict Detection** | Identifies contradictions between sources |
| 5 | **Response Strategy** | Decides: answer, refuse, or present conflicts |
| 6 | **Response Generation** | LLM generates the final answer |

### 3. 📄 Clickable Source Chips
- Each step shows which sources were used
- Click any source chip to view the full content in a modal
- See relevance scores and confidence metrics

### 4. 📥 Export as Documentation
- Export the entire reasoning chain as a markdown file
- Perfect for audits, documentation, or debugging
- Includes all details, timings, and source references

## How to Use

### Viewing the Reasoning Chain
1. Ask a question in the RAG system
2. After receiving an answer, look for the **"🔗 View Reasoning Chain"** panel
3. Click to expand and see the full pipeline

### Expanding Step Details
- Click on any pipeline step card to expand it
- View detailed metrics and parameters
- See exactly what data was used at each stage

### Viewing Source Content
- Look for the source chips (📄 icons) in retrieval and generation steps
- Click any chip to open a modal with the full source content
- Check relevance and confidence scores

### Exporting for Documentation
1. Open the Reasoning Chain panel
2. Click **"📄 Export as Documentation"**
3. A markdown file will download automatically
4. Use for audits, reports, or debugging

## Technical Implementation

### Backend Models

```python
class ReasoningStepType(str, Enum):
    QUERY_ANALYSIS = "query_analysis"
    RETRIEVAL = "retrieval"
    CONFIDENCE_ASSESSMENT = "confidence_assessment"
    CONFLICT_DETECTION = "conflict_detection"
    RESPONSE_STRATEGY = "response_strategy"
    GENERATION = "generation"

class ReasoningStep(BaseModel):
    step_number: int
    step_type: ReasoningStepType
    title: str
    description: str
    details: Dict[str, Any]
    sources_used: List[SourceReference]
    duration_ms: float
    status: str  # "completed", "warning", "error"

class ReasoningChain(BaseModel):
    chain_id: str
    query: str
    timestamp: str
    total_duration_ms: float
    steps: List[ReasoningStep]
    final_decision: str
    key_insights: List[str]
```

### API Response

The `QueryResponse` now includes an optional `reasoning_chain` field:

```json
{
  "query": "What is AI?",
  "answer": "...",
  "confidence": "High",
  "reasoning_chain": {
    "chain_id": "abc123",
    "steps": [...],
    "key_insights": [
      "✓ Retrieved 5 sources with avg relevance 0.82",
      "✓ High confidence (0.85) - proceeding with full answer"
    ],
    "final_decision": "answered"
  }
}
```

### Export Endpoint

```
POST /export-reasoning-chain
```

Request body:
```json
{
  "query": "Your question here",
  "persona": "standard"
}
```

Response:
```json
{
  "success": true,
  "chain_id": "abc123",
  "markdown": "# Reasoning Chain Report...",
  "timestamp": "2026-01-17T10:30:00"
}
```

## Example Reasoning Chain

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Query Analysis                              ✅ 2ms  │
│ Detected intents: explanation, general                      │
│ Persona: creative                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Evidence Retrieval                         ✅ 45ms  │
│ Retrieved 5 sources with avg relevance 0.78                 │
│ Modalities: text, image                                     │
│ [📄 doc1.pdf] [📄 manual.txt] [🖼️ diagram.png]             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Confidence Assessment                       ✅ 5ms  │
│ Confidence: 0.72 (Medium)                                   │
│ Scoring: relevance 0.78 + diversity bonus 0.10              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Conflict Detection                         ⚠️ 12ms  │
│ 1 conflict detected between sources                         │
│ doc1.pdf vs manual.txt                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Response Strategy                           ✅ 1ms  │
│ Strategy: CONFLICT_PRESENTATION                             │
│ Reason: Conflicting sources detected                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Response Generation                      ✅ 2500ms  │
│ Generated response with 3 source citations                  │
│ [📄 doc1.pdf] [📄 manual.txt] [🖼️ diagram.png]             │
└─────────────────────────────────────────────────────────────┘
```

## Files Modified

| File | Changes |
|------|---------|
| `backend/models/query.py` | Added `ReasoningStepType`, `SourceReference`, `ReasoningStep`, `ReasoningChain` models |
| `backend/generation/rag_generator.py` | Tracking all 6 pipeline stages with timing |
| `backend/app.py` | Added `/export-reasoning-chain` endpoint |
| `frontend/templates/index.html` | Added reasoning chain panel UI |
| `frontend/static/css/styles.css` | Added 370+ lines of styling |
| `frontend/static/js/app.js` | Added 200+ lines for visualization |

## Benefits

1. **Trust Building** - Users can see exactly how answers are derived
2. **Debugging** - Easily identify which step caused issues
3. **Auditing** - Export chains for compliance documentation
4. **Education** - Understand how RAG systems work
5. **Quality Control** - Monitor relevance scores and confidence

---

**Built with ❤️ for transparent, trustworthy AI**
