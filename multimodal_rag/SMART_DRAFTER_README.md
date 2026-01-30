# Smart Email/Report Drafter Feature

## Overview

The Smart Email/Report Drafter is an AI-powered feature that allows users to generate professional emails, reports, memos, summaries, and letters using the knowledge base context. It leverages the RAG (Retrieval-Augmented Generation) system to create contextually relevant documents with automatic source references.

## Features

### 📧 Document Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Email** | Professional email with subject, greeting, body, and signature | Client communication, updates, requests |
| **Report** | Formal report with executive summary, findings, and recommendations | Project status, analysis, reviews |
| **Memo** | Internal memo with header, purpose, and action items | Team announcements, policies |
| **Summary** | Concise summary with key points and overview | Executive briefings, quick updates |
| **Letter** | Formal letter with date, greeting, body, and signature | Official correspondence |

### 🎭 Tone Options

| Tone | Description | Best For |
|------|-------------|----------|
| **Formal** | Formal, professional language without contractions | Legal, executive communications |
| **Professional** | Clear, direct, and polite | Standard business communications |
| **Friendly** | Warm, approachable but professional | Team updates, casual follow-ups |
| **Urgent** | Conveys urgency and importance | Time-sensitive matters |
| **Apologetic** | Sincere, humble, solution-focused | Delays, issues, apologies |
| **Confident** | Assertive, decisive language | Decisions, announcements |

## How to Use

### Basic Usage

1. **Select Document Type**: Click on the desired template (Email, Report, etc.)
2. **Choose Tone**: Select the appropriate tone for your audience
3. **Enter Communication Goal**: Describe what you want to communicate
   - Example: "Inform client about project delay due to resource constraints"
4. **Click Generate Draft**: The AI will generate a professional document

### Advanced Options

#### Reference Documents
Add specific documents from your knowledge base to reference:
- Type the document name and press Enter
- The drafter will prioritize content from these documents
- Source references will be included in the generated draft

#### Recipient & Sender
- **Recipient**: Specify who the document is for (e.g., "client", "John Smith")
- **Sender Name**: Your name or title for the signature

#### Additional Context
Add any extra details, specific points to include, or special instructions.

## Example Usage

### Email Example

**Input:**
- Communication Goal: "Inform client about project delay, use reasons from project_status.pdf"
- Document Type: Email
- Tone: Professional
- Recipient: Client
- Source Documents: project_status.pdf

**Generated Output:**
```
Subject: Project Timeline Update

Dear [Client],

I wanted to inform you about a timeline adjustment for our current project.

As noted in our internal assessment, the delay is due to:
1. Resource constraints (ref: project_status.pdf, page 5)
2. Additional testing requirements (ref: project_status.pdf, page 12)

New expected delivery: March 2026

We remain committed to delivering a high-quality solution and appreciate your understanding.

Best regards,
[Name]
```

### Report Example

**Input:**
- Communication Goal: "Summarize quarterly performance and recommend improvements"
- Document Type: Report
- Tone: Formal
- Source Documents: q4_metrics.pdf, sales_data.xlsx

**Generated Output:**
```
Title: Q4 Performance Review and Recommendations

Executive Summary:
This report presents an analysis of Q4 2025 performance metrics...

Key Findings:
1. Revenue exceeded targets by 12% (Source: q4_metrics.pdf, page 3)
2. Customer retention improved to 94% (Source: q4_metrics.pdf, page 7)
3. Regional performance varied significantly...

Recommendations:
1. Expand successful regional strategies
2. Invest in customer success programs
...
```

## API Endpoints

### POST /draft

Generate a professional document draft.

**Request Body:**
```json
{
  "communication_goal": "Inform client about project delay",
  "document_type": "email",
  "tone": "professional",
  "recipient": "client",
  "source_documents": ["project_status.pdf"],
  "sender_name": "Project Manager",
  "additional_context": "Include timeline for resolution",
  "include_sources": true
}
```

**Response:**
```json
{
  "draft_id": "a1b2c3d4",
  "document_type": "email",
  "subject": "Project Timeline Update",
  "body": "Dear [Client],...",
  "sources_used": [
    {
      "source_file": "project_status.pdf",
      "page_reference": "page 5",
      "content": "Resource constraints identified...",
      "relevance_score": 0.89
    }
  ],
  "tone": "professional",
  "word_count": 156,
  "processing_time": 2.34,
  "suggestions": [
    "💡 Consider adding more source references to strengthen credibility"
  ]
}
```

### GET /draft/templates

Get available document templates.

### GET /draft/tones

Get available tone options.

## Source Traceability

All generated drafts include source references:
- Automatically cites relevant documents from your knowledge base
- Includes page/section references when available
- Displays source relevance scores
- Shows content previews from each source

## Improvement Suggestions

The drafter provides actionable suggestions:
- 💡 Add more source references
- ✂️ Shorten for better readability
- ✅ Add clear action items
- ⚡ Emphasize urgency
- 📋 Fill in placeholders

## Technical Details

### Backend Components
- `EmailDrafter` class in `backend/generation/email_drafter.py`
- Uses `CrossModalRetriever` for context retrieval
- Uses `LLMClient` for generation

### Frontend Components
- HTML section in `frontend/templates/index.html`
- CSS styles in `frontend/static/css/drafter.css`
- JavaScript in `frontend/static/js/app.js` (Smart Email/Report Drafter section)

## Compatibility

This feature integrates seamlessly with existing functionality:
- ✅ Works with all document types in knowledge base (PDF, DOCX, TXT, images, audio)
- ✅ Compatible with conversation memory
- ✅ Uses the same LLM infrastructure
- ✅ Respects language settings
- ✅ No breaking changes to existing features

## Future Enhancements

Potential improvements:
- Template customization
- Draft history/saving
- Multi-language generation
- Email integration (send directly)
- Template library
