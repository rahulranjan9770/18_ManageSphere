# 🎭 Multi-Persona Response Feature

> **Same knowledge, different audiences — personalized communication**

## Overview

The Multi-Persona Response feature allows users to choose how the AI responds to their queries. Instead of a one-size-fits-all approach, users can select from 6 distinct response styles tailored for different audiences and use cases.

## Available Personas

| Persona | Icon | Description | Best For |
|---------|------|-------------|----------|
| **Standard** | ⚖️ | Balanced, concise response | General queries |
| **Academic** | 🎓 | Formal, citation-heavy, detailed | Research, academic work |
| **Executive** | 💼 | Brief bullet points, key takeaways | Decision-makers, quick summaries |
| **Simple (ELI5)** | 🧒 | Simple language for beginners | Non-experts, learning |
| **Technical** | ⚙️ | Deep-dive with code/formulas | Developers, engineers |
| **Debate** | ⚔️ | Present all viewpoints side-by-side | Controversial topics, research |

## How It Works

### Frontend
1. User selects a persona using the pill-button selector above the query input
2. A toast notification confirms the selection
3. The selected persona is sent with the query to the backend
4. The response displays a badge showing which persona style was used

### Backend
1. `QueryRequest` model includes `persona` field (defaults to "standard")
2. `RAGGenerator` uses persona-specific configurations for:
   - **max_tokens**: Controls response length
   - **temperature**: Controls creativity/determinism
3. Persona-specific prompts guide the LLM to respond appropriately

## Persona Configurations

```python
PERSONA_CONFIGS = {
    "academic": {
        "max_tokens": 200,      # Longer for detailed responses
        "temperature": 0.2,     # More deterministic
        "description": "Academic/Formal"
    },
    "executive": {
        "max_tokens": 80,       # Short and concise
        "temperature": 0.1,     # Very focused
        "description": "Executive Summary"
    },
    "eli5": {
        "max_tokens": 120,      # Moderate length
        "temperature": 0.4,     # Slightly creative for analogies
        "description": "Simple (ELI5)"
    },
    "technical": {
        "max_tokens": 250,      # Longest for comprehensive detail
        "temperature": 0.2,     # Precise
        "description": "Technical Deep-Dive"
    },
    "debate": {
        "max_tokens": 180,      # Room for multiple perspectives
        "temperature": 0.3,     # Balanced
        "description": "Debate Mode"
    },
    "standard": {
        "max_tokens": 100,      # Default balanced
        "temperature": 0.3,
        "description": "Standard"
    }
}
```

## Example Outputs

### Same Query, Different Personas

**Query:** "What causes climate change?"

---

**⚖️ Standard:**
> Climate change is primarily caused by greenhouse gas emissions from human activities [1]. Burning fossil fuels and deforestation are major contributors [2].

---

**🎓 Academic:**
> According to the available literature, anthropogenic climate change is driven by the accumulation of greenhouse gases (GHGs) in the atmosphere, particularly CO₂, CH₄, and N₂O [1]. The Intergovernmental Panel on Climate Change (IPCC) has established with high confidence that human activities since pre-industrial times have increased atmospheric CO₂ concentrations by over 45% [2]. However, it should be noted that natural climate variability also plays a role, albeit minor compared to anthropogenic forcing [3]. Further research is needed to quantify regional impacts precisely.

---

**💼 Executive:**
> **Key Takeaways:**
> - Primary driver: Human-generated greenhouse gas emissions
> - Main sources: Fossil fuels, deforestation
> - Action needed: Reduce emissions by 45% by 2030
> - Bottom line: Immediate action required for 1.5°C target

---

**🧒 Simple (ELI5):**
> Imagine Earth wearing a cozy blanket. When we burn things like gas in cars or coal in power plants, we make that blanket thicker. A thicker blanket traps more heat, making Earth warmer than it should be. It's like wearing a winter coat in summer!

---

**⚙️ Technical:**
> Climate change is driven by radiative forcing imbalances. Key factors:
> - CO₂ forcing: ~2.0 W/m² (current concentration: 420 ppm)
> - Methane (CH₄): 1.8 ppm, GWP = 28 over 100 years
> - Feedback mechanisms: Ice-albedo, water vapor amplification
> - Climate sensitivity: 2.5-4.0°C per doubling of CO₂
> See CMIP6 models for detailed projections.

---

**⚔️ Debate:**
> **Majority Scientific View:**
> - Human activities are the dominant cause (IPCC AR6)
> - 97%+ scientific consensus
> 
> **Skeptical Position:**
> - Some argue natural cycles play larger role
> - Solar variability theories (minority view)
> 
> **Bottom Line:** The evidence strongly supports anthropogenic causation, though readers should evaluate sources directly.

---

## API Usage

```python
# Query with persona
import requests

response = requests.post('/query', json={
    "query": "What is machine learning?",
    "persona": "eli5"  # Options: standard, academic, executive, eli5, technical, debate
})
```

## Files Modified

- `backend/models/query.py` - Added `ResponsePersona` enum and `persona` field
- `backend/generation/rag_generator.py` - Added persona-specific prompts and configurations
- `frontend/templates/index.html` - Added persona selector UI and badge display
- `frontend/static/css/styles.css` - Added persona button and badge styles
- `frontend/static/js/app.js` - Added persona selection logic

## Backwards Compatibility

- Default persona is "standard" if not specified
- Existing queries without persona work unchanged
- Legacy prompt methods still available for backwards compatibility

---

**Built with ❤️ for personalized, audience-aware AI responses**
