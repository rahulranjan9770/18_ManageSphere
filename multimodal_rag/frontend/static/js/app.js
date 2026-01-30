// Frontend logic for Multimodal RAG System

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const totalChunksEl = document.getElementById('totalChunks');
const queryInput = document.getElementById('queryInput');
const queryBtn = document.getElementById('queryBtn');
const responseSection = document.getElementById('responseSection');

// Persona selection state
let selectedPersona = 'standard';

// Conversation Context State
let sessionId = null;
let contextEnabled = false;

// Web Search State
let webSearchEnabled = false;

// Persona display names for UI
const personaDisplayNames = {
    'standard': '⚖️ Standard',
    'academic': '🎓 Academic',
    'executive': '💼 Executive',
    'eli5': '🧒 Simple (ELI5)',
    'technical': '⚙️ Technical',
    'debate': '⚔️ Debate',
    'legal': '⚖️ Legal',
    'medical': '🏥 Medical',
    'creative': '✨ Creative'
};

// Toast Notification Function
function showToast(title, message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-notification ${type}`;
    toast.innerHTML = `
        <div class="toast-header">${title}</div>
        <div class="toast-body">${message}</div>
    `;

    document.body.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// Voice Query & Response (Web Speech API)
// ============================================

// Speech Recognition (STT)
let recognition = null;
let isListening = false;

// Check browser support for Speech Recognition
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Silence timeout for stopping recognition after pause
let silenceTimeout = null;
const SILENCE_DURATION = 2000; // 2 seconds of silence before stopping

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true;  // Keep listening until explicitly stopped
    recognition.interimResults = true;
    recognition.lang = 'en-IN';  // English (India) - recognizes English with Indian accent support

    recognition.onstart = () => {
        isListening = true;
        document.getElementById('voiceInputBtn').classList.add('recording');
        document.getElementById('voiceStatus').style.display = 'flex';
        document.getElementById('voiceStatusText').textContent = 'Listening... Speak your full query';
    };

    recognition.onresult = (event) => {
        // Clear any existing silence timeout
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }

        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }

        // Show combined transcript in input
        const fullTranscript = finalTranscript + interimTranscript;
        document.getElementById('queryInput').value = fullTranscript;

        if (finalTranscript) {
            document.getElementById('voiceStatusText').textContent = 'Heard: ' + finalTranscript.substring(0, 30) + '... (keep speaking or wait)';

            // Start silence timeout after final result
            silenceTimeout = setTimeout(() => {
                if (isListening && recognition) {
                    recognition.stop();
                }
            }, SILENCE_DURATION);
        } else if (interimTranscript) {
            document.getElementById('voiceStatusText').textContent = 'Listening: ' + interimTranscript.substring(0, 40) + '...';
        }
    };

    recognition.onend = () => {
        // Clear silence timeout
        if (silenceTimeout) {
            clearTimeout(silenceTimeout);
            silenceTimeout = null;
        }

        isListening = false;
        document.getElementById('voiceInputBtn').classList.remove('recording');
        document.getElementById('voiceStatus').style.display = 'none';

        // Auto-submit if we got a transcript
        const query = document.getElementById('queryInput').value.trim();
        if (query) {
            showToast('🎙️ Voice Query', 'Captured: "' + query.substring(0, 50) + '"', 'info');
        }
    };

    recognition.onerror = (event) => {
        isListening = false;
        document.getElementById('voiceInputBtn').classList.remove('recording');
        document.getElementById('voiceStatus').style.display = 'none';

        let errorMessage = 'Speech recognition error';
        switch (event.error) {
            case 'no-speech':
                errorMessage = 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                errorMessage = 'Microphone not available. Check permissions.';
                break;
            case 'not-allowed':
                errorMessage = 'Microphone access denied. Please allow microphone access.';
                break;
            default:
                errorMessage = `Error: ${event.error}`;
        }
        showToast('🎙️ Voice Error', errorMessage, 'error');
    };
}

// Voice Input Button Handler
document.getElementById('voiceInputBtn')?.addEventListener('click', () => {
    if (!SpeechRecognition) {
        showToast('🎙️ Not Supported', 'Speech recognition is not supported in this browser. Try Chrome or Edge.', 'warning');
        return;
    }

    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
});

// Speech Synthesis (TTS)
let currentUtterance = null;
let isSpeaking = false;

// Store current response text for TTS
let currentResponseText = '';

// Store current confidence breakdown for explainability dashboard
let currentConfidenceBreakdown = null;

// Voice Output Button Handler
document.getElementById('voiceOutputBtn')?.addEventListener('click', () => {
    const voiceBtn = document.getElementById('voiceOutputBtn');

    if (!('speechSynthesis' in window)) {
        showToast('🔊 Not Supported', 'Text-to-speech is not supported in this browser.', 'warning');
        return;
    }

    if (isSpeaking) {
        // Stop speaking
        speechSynthesis.cancel();
        voiceBtn.classList.remove('speaking');
        voiceBtn.innerHTML = '🔊 Listen';
        isSpeaking = false;
        showToast('🔊 Stopped', 'Stopped reading response', 'info');
        return;
    }

    if (!currentResponseText) {
        showToast('🔊 No Response', 'No response to read aloud', 'warning');
        return;
    }

    // Clean text for better TTS
    let textToSpeak = currentResponseText
        .replace(/\*\*/g, '')
        .replace(/\n/g, '. ')
        .replace(/- /g, ', ')
        .replace(/#+/g, '')
        .substring(0, 3000); // Limit length

    currentUtterance = new SpeechSynthesisUtterance(textToSpeak);
    currentUtterance.rate = 1.0;
    currentUtterance.pitch = 1.0;
    currentUtterance.volume = 1.0;

    // Try to use a natural voice
    const voices = speechSynthesis.getVoices();
    const preferredVoice = voices.find(v =>
        v.name.includes('Google') ||
        v.name.includes('Natural') ||
        v.name.includes('Microsoft')
    );
    if (preferredVoice) {
        currentUtterance.voice = preferredVoice;
    }

    currentUtterance.onstart = () => {
        isSpeaking = true;
        voiceBtn.classList.add('speaking');
        voiceBtn.innerHTML = '⏹️ Stop';
    };

    currentUtterance.onend = () => {
        isSpeaking = false;
        voiceBtn.classList.remove('speaking');
        voiceBtn.innerHTML = '🔊 Listen';
    };

    currentUtterance.onerror = (event) => {
        isSpeaking = false;
        voiceBtn.classList.remove('speaking');
        voiceBtn.innerHTML = '🔊 Listen';
        if (event.error !== 'interrupted') {
            showToast('🔊 TTS Error', 'Failed to read response: ' + event.error, 'error');
        }
    };

    speechSynthesis.speak(currentUtterance);
    showToast('🔊 Reading', 'Reading response aloud...', 'info');
});

// Initialize voices (some browsers need this)
if ('speechSynthesis' in window) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}

// Persona Selector functionality
const personaBtns = document.querySelectorAll('.persona-btn');

personaBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all buttons
        personaBtns.forEach(b => b.classList.remove('active'));
        // Add active class to clicked button
        btn.classList.add('active');
        // Update selected persona
        selectedPersona = btn.dataset.persona;

        // Show toast notification for persona change
        const personaName = btn.querySelector('.persona-name').textContent;
        showToast(
            '🎭 Response Style Changed',
            `Now using: ${personaName}`,
            'info'
        );
    });
});

// Language Selector Handler
const languageSelect = document.getElementById('languageSelect');
const languageBadge = document.getElementById('languageSelectorBadge');

if (languageSelect && languageBadge) {
    languageSelect.addEventListener('change', () => {
        const selectedOption = languageSelect.options[languageSelect.selectedIndex];

        if (languageSelect.value) {
            // Language selected
            // Extract flag and name safely
            const textParts = selectedOption.text.split(' ');
            const displayText = textParts.length >= 2 ? textParts[0] + ' ' + textParts[1] : selectedOption.text;

            languageBadge.textContent = displayText;
            languageBadge.className = 'language-selector-badge selected';

            showToast(
                '🌍 Language Set',
                `Output forcing: ${selectedOption.text}`,
                'info'
            );
        } else {
            // Auto-detect
            languageBadge.textContent = 'Auto-Detect';
            languageBadge.className = 'language-selector-badge';

            showToast(
                '🤖 Auto-Detect',
                'System will detect language from your query',
                'info'
            );
        }
    });
}

// Upload functionality
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

async function handleFiles(files) {
    for (let file of files) {
        await uploadFile(file);
    }
    updateStats();
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    uploadStatus.textContent = `Uploading ${file.name}...`;
    uploadStatus.className = 'upload-status';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            uploadStatus.textContent = `✓ ${data.message} - ${data.chunks_created} chunks created`;
            uploadStatus.className = 'upload-status success';
        } else {
            uploadStatus.textContent = `✗ Error: ${data.detail}`;
            uploadStatus.className = 'upload-status error';
        }
    } catch (error) {
        uploadStatus.textContent = `✗ Upload failed: ${error.message}`;
        uploadStatus.className = 'upload-status error';
    }
}

async function updateStats() {
    try {
        const response = await fetch('/stats');
        const data = await response.json();
        totalChunksEl.textContent = data.total_chunks;
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

// Query functionality
queryBtn.addEventListener('click', async () => {
    const query = queryInput.value.trim();

    if (!query) {
        alert('Please enter a question');
        return;
    }

    // UI Loading State
    queryBtn.disabled = true;
    queryBtn.textContent = 'Searching...';
    responseSection.style.display = 'block';
    document.getElementById('answerContent').innerHTML = '<div class="skeleton-text">Analyzing documents...</div>';
    document.getElementById('evidenceSources').innerHTML = '<div class="skeleton-text">Retrieving evidence...</div>';

    try {
        // Build request body with optional session_id
        const requestBody = {
            query: query,
            persona: selectedPersona
        };

        // Add session_id if context is enabled
        if (contextEnabled && sessionId) {
            requestBody.session_id = sessionId;
        }

        // Add web search if enabled
        if (webSearchEnabled) {
            requestBody.enable_web_search = true;
            requestBody.web_results_count = 3;
        }

        // Add target language if selected
        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect && languageSelect.value) {
            requestBody.target_language = languageSelect.value;
        }

        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();
        displayResponse(data);

        // Update context UI after response
        if (contextEnabled && data.session_id) {
            sessionId = data.session_id;
            updateContextDisplay();

            // Show context resolution notice if context was used
            if (data.context_used && data.resolved_query) {
                showContextResolutionNotice(data.query, data.resolved_query);
            }
        }
    } catch (error) {
        alert(`Query failed: ${error.message}`);
        responseSection.style.display = 'none';
    } finally {
        queryBtn.disabled = false;
        queryBtn.textContent = 'Search Knowledge Base';
    }
});

function displayResponse(data) {
    responseSection.style.display = 'block';

    // Confidence badge
    const badge = document.getElementById('confidenceBadge');
    badge.textContent = `Confidence: ${data.confidence}`;
    badge.className = `confidence-badge confidence-${data.confidence.toLowerCase()}`;

    // Persona badge
    const personaBadgeContainer = document.getElementById('personaBadge');
    if (personaBadgeContainer) {
        const persona = data.persona || 'standard';
        const personaDisplay = personaDisplayNames[persona] || personaDisplayNames['standard'];
        personaBadgeContainer.textContent = personaDisplay;
        personaBadgeContainer.className = `persona-badge persona-${persona}`;
        personaBadgeContainer.style.display = 'inline-flex';
    }

    // Answer with basic formatting
    const formattedAnswer = data.answer
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\n/g, '<br>'); // Newlines
    document.getElementById('answerContent').innerHTML = formattedAnswer;

    // Store for TTS
    currentResponseText = data.answer;

    // Store and setup confidence breakdown
    currentConfidenceBreakdown = data.confidence_breakdown;
    document.getElementById('confidenceDashboard').style.display = 'none';

    // Conflicts
    const conflictWarning = document.getElementById('conflictWarning');
    const conflictDetails = document.getElementById('conflictDetails');
    if (data.conflicts) {
        conflictWarning.style.display = 'block';
        conflictDetails.innerHTML = `
            <p>${data.conflicts.description}</p>
            <ul>
                ${data.conflicts.perspectives.map(p => `
                    <li><strong>${p.source}:</strong> ${p.claim}</li>
                `).join('')}
            </ul>
        `;
    } else {
        conflictWarning.style.display = 'none';
    }

    // Refusal
    const refusalWarning = document.getElementById('refusalWarning');
    const refusalReason = document.getElementById('refusalReason');
    if (data.refusal_reason) {
        refusalWarning.style.display = 'block';
        refusalReason.textContent = data.refusal_reason;
    } else {
        refusalWarning.style.display = 'none';
    }

    // Evidence sources with visual annotations for images
    document.getElementById('sourceCount').textContent = data.sources.length;
    const evidenceSources = document.getElementById('evidenceSources');

    // Collect image sources for comparison panel
    const imageSources = data.sources.filter(s => s.modality.toLowerCase() === 'image');

    evidenceSources.innerHTML = data.sources.map((source, i) => {
        // Check for special boosts
        const boosts = [];
        if (source.metadata.keyword_boost) boosts.push('Keyword Boost');
        if (source.metadata.cross_modal_boost) boosts.push('Multimodal Boost');
        const badgeHtml = boosts.map(b => `<span class="boost-badge">${b}</span>`).join('');

        // Check if this is an image source
        const isImage = source.modality.toLowerCase() === 'image';
        const sourceFile = source.source_file || '';
        const isImageFile = /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(sourceFile);

        // Generate annotated image display
        let contentHtml = '';
        if (isImage || isImageFile) {
            // Extract key terms from content for annotations
            const keyTerms = extractKeyTerms(source.content, data.query);
            const annotationsHtml = keyTerms.slice(0, 4).map((term, idx) => `
                <div class="image-annotation" style="--annotation-index: ${idx}">
                    <span class="annotation-marker">${idx + 1}</span>
                    <span class="annotation-text">${term}</span>
                </div>
            `).join('');

            const highlightRegionsHtml = generateHighlightRegions(source.relevance_score, keyTerms.length);

            contentHtml = `
                <div class="image-evidence-container">
                    <div class="image-with-overlays">
                        <div class="image-placeholder">
                            <div class="image-placeholder-icon">🖼️</div>
                            <div class="image-placeholder-name">${sourceFile.split('/').pop().split('\\').pop()}</div>
                        </div>
                        ${highlightRegionsHtml}
                        <div class="image-annotations-layer">
                            ${annotationsHtml}
                        </div>
                        <div class="image-relevance-indicator" style="--relevance: ${source.relevance_score * 100}%">
                            <span>${(source.relevance_score * 100).toFixed(0)}% relevant</span>
                        </div>
                    </div>
                    <div class="image-ocr-content">
                        <div class="ocr-header">
                            <span class="ocr-icon">📝</span>
                            <span>Extracted Text & Annotations</span>
                        </div>
                        <div class="ocr-text">${source.content}</div>
                        ${keyTerms.length > 0 ? `
                            <div class="key-terms-section">
                                <span class="key-terms-label">🔑 Key Terms Found:</span>
                                <div class="key-terms-list">
                                    ${keyTerms.map((t, idx) => `<span class="key-term" style="--term-index: ${idx}">${idx + 1}. ${t}</span>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } else {
            contentHtml = `<div class="source-content">${source.content}</div>`;
        }

        // Get language info from metadata
        const langCode = source.metadata?.language || '';
        const langName = source.metadata?.language_name || '';
        const langFlag = source.metadata?.language_flag || '🌐';
        const crossLingual = source.metadata?.cross_lingual_match || false;
        const languageBadge = langCode ?
            `<span class="language-badge${crossLingual ? ' cross-lingual' : ''}" title="${langName}">${langFlag} ${langCode.toUpperCase()}</span>` : '';

        return `
        <div class="evidence-source ${isImage || isImageFile ? 'image-source' : ''}">
            <div class="source-meta">
                <span>Source ${i + 1}</span>
                <span class="modality-tag ${source.modality.toLowerCase()}">${source.modality}</span>
                ${languageBadge}
                <span>${source.source_file}</span>
                <span class="score">Relevance: ${(source.relevance_score * 100).toFixed(1)}%</span>
                ${badgeHtml}
                ${(isImage || isImageFile) ? '<span class="visual-badge">📸 Visual Evidence</span>' : ''}
            </div>
            ${contentHtml}
        </div>
    `}).join('');

    // Render image comparison panel if multiple images
    renderImageComparisonPanel(imageSources, data.query);

    // Processing time
    document.getElementById('processingTime').textContent = data.processing_time.toFixed(2);

    // Reasoning Chain
    if (data.reasoning_chain) {
        renderReasoningChain(data.reasoning_chain, data.sources);
    } else {
        document.getElementById('reasoningChainPanel').style.display = 'none';
    }

    // Smart Suggestions
    if (data.suggestions) {
        renderSmartSuggestions(data.suggestions);
    } else {
        document.getElementById('suggestionsPanel').style.display = 'none';
    }

    // Web Sources (Live Web Integration)
    renderWebSources(data.web_sources, data.web_search_enabled);

    // Scroll to response
    responseSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================
// Live Web Search Results Display
// ============================================

function renderWebSources(webSources, webSearchEnabled) {
    // Get or create web sources container
    let webSourcesPanel = document.getElementById('webSourcesPanel');

    if (!webSourcesPanel) {
        // Create the panel if it doesn't exist
        const responseSection = document.getElementById('responseSection');
        webSourcesPanel = document.createElement('div');
        webSourcesPanel.id = 'webSourcesPanel';
        webSourcesPanel.className = 'web-sources-panel';

        // Insert after evidence sources
        const evidenceSection = document.querySelector('.evidence-section');
        if (evidenceSection) {
            evidenceSection.after(webSourcesPanel);
        } else {
            responseSection.appendChild(webSourcesPanel);
        }
    }

    if (!webSearchEnabled || !webSources || webSources.length === 0) {
        webSourcesPanel.style.display = 'none';
        return;
    }

    // Calculate average credibility
    const avgCredibility = webSources.reduce((sum, s) => sum + (s.credibility_score || 0.5), 0) / webSources.length;
    const credibilityLabel = avgCredibility >= 0.75 ? 'High Trust' : (avgCredibility >= 0.5 ? 'Medium Trust' : 'Low Trust');
    const credibilityClass = avgCredibility >= 0.75 ? 'trust-high' : (avgCredibility >= 0.5 ? 'trust-medium' : 'trust-low');

    webSourcesPanel.style.display = 'block';
    webSourcesPanel.innerHTML = `
        <div class="web-sources-header">
            <span class="web-sources-icon">🌐</span>
            <span class="web-sources-title">Live Web Results</span>
            <span class="web-sources-count">${webSources.length} sources</span>
            <span class="web-sources-credibility ${credibilityClass}">${credibilityLabel} (${(avgCredibility * 100).toFixed(0)}%)</span>
            <span class="web-sources-notice">⚠️ Supplementary - verify with documents</span>
        </div>
        <div class="web-sources-priority-note">
            📁 Document sources take priority • Web sources provide supplementary context
        </div>
        <div class="web-sources-list">
            ${webSources.map((source, i) => {
        const credScore = source.credibility_score || 0.5;
        const credClass = credScore >= 0.75 ? 'trust-high' : (credScore >= 0.5 ? 'trust-medium' : 'trust-low');
        const credLabel = credScore >= 0.75 ? '✓ Trusted' : (credScore >= 0.5 ? '○ Moderate' : '△ Unverified');
        return `
                <div class="web-source-item ${credClass}">
                    <div class="web-source-header">
                        <span class="web-source-number">[Web ${i + 1}]</span>
                        <span class="web-source-name">${source.source_name}</span>
                        <span class="web-source-credibility-badge ${credClass}" title="Source credibility: ${(credScore * 100).toFixed(0)}%">
                            ${credLabel}
                        </span>
                        <span class="web-source-relevance">${(source.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                    <a class="web-source-title" href="${source.url}" target="_blank" rel="noopener noreferrer">
                        ${source.title}
                        <span class="external-link-icon">↗</span>
                    </a>
                    <div class="web-source-snippet">${source.snippet}</div>
                    <div class="web-source-url">${source.url}</div>
                </div>
            `}).join('')}
        </div>
    `;
}

// ============================================
// Smart Follow-up Suggestions
// ============================================

function renderSmartSuggestions(suggestions) {
    const panel = document.getElementById('suggestionsPanel');

    // Check if there are any suggestions
    const hasSuggestions =
        suggestions.related_questions?.length > 0 ||
        suggestions.knowledge_gaps?.length > 0 ||
        suggestions.deep_dives?.length > 0 ||
        suggestions.cross_modal?.length > 0;

    if (!hasSuggestions) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';

    // Render Knowledge Gaps (highest priority)
    renderSuggestionGroup(
        'knowledgeGapsGroup',
        'knowledgeGapsChips',
        suggestions.knowledge_gaps
    );

    // Render Deep Dives
    renderSuggestionGroup(
        'deepDivesGroup',
        'deepDivesChips',
        suggestions.deep_dives
    );

    // Render Cross-Modal
    renderSuggestionGroup(
        'crossModalGroup',
        'crossModalChips',
        suggestions.cross_modal
    );

    // Render Related Questions
    renderSuggestionGroup(
        'relatedQuestionsGroup',
        'relatedQuestionsChips',
        suggestions.related_questions
    );
}

function renderSuggestionGroup(groupId, chipsId, items) {
    const group = document.getElementById(groupId);
    const chips = document.getElementById(chipsId);

    if (!items || items.length === 0) {
        group.style.display = 'none';
        return;
    }

    group.style.display = 'block';
    chips.innerHTML = items.map(item => {
        const isUploadAction = !item.query && item.suggestion_type === 'knowledge_gap';
        const extraClass = isUploadAction ? 'upload-action' : '';

        return `
            <button class="suggestion-chip ${item.suggestion_type} ${extraClass}" 
                    data-query="${item.query || ''}"
                    data-type="${item.suggestion_type}"
                    title="${item.text}">
                ${item.icon} ${item.text}
            </button>
        `;
    }).join('');

    // Add click handlers
    chips.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => handleSuggestionClick(chip));
    });
}

function handleSuggestionClick(chip) {
    const query = chip.dataset.query;
    const type = chip.dataset.type;

    if (!query) {
        // This is an upload suggestion - scroll to upload area
        if (type === 'knowledge_gap') {
            const uploadArea = document.getElementById('uploadArea');
            uploadArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
            uploadArea.classList.add('pulse-highlight');
            setTimeout(() => uploadArea.classList.remove('pulse-highlight'), 2000);
            showToast('📤 Upload Files', 'Upload more documents to improve results', 'info');
        }
        return;
    }

    // Fill the query input with the suggestion
    const queryInput = document.getElementById('queryInput');
    queryInput.value = query;
    queryInput.focus();

    // Scroll to query section
    queryInput.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Highlight effect
    queryInput.classList.add('highlight-input');
    setTimeout(() => queryInput.classList.remove('highlight-input'), 1500);

    showToast('💡 Suggestion Applied', 'Press Enter or click Search to query', 'info');
}

// Store current reasoning chain for export
let currentReasoningChain = null;
let currentSources = [];

// Reasoning Chain Visualization
function renderReasoningChain(chain, sources) {
    currentReasoningChain = chain;
    currentSources = sources;

    const panel = document.getElementById('reasoningChainPanel');
    panel.style.display = 'block';

    // Display chain ID
    document.getElementById('chainIdDisplay').textContent = `Chain ID: ${chain.chain_id}`;

    // Render Key Insights
    const insightsList = document.getElementById('insightsList');
    insightsList.innerHTML = chain.key_insights.map(insight =>
        `<li>${insight}</li>`
    ).join('');

    // Render Pipeline Steps
    const pipelineSteps = document.getElementById('pipelineSteps');
    pipelineSteps.innerHTML = chain.steps.map(step => createPipelineStepHTML(step)).join('');

    // Add click handlers for expandable steps
    pipelineSteps.querySelectorAll('.pipeline-step').forEach(stepEl => {
        stepEl.addEventListener('click', (e) => {
            // Don't toggle if clicking on a source chip
            if (e.target.closest('.source-chip')) return;
            stepEl.classList.toggle('expanded');
        });
    });

    // Add click handlers for source chips
    pipelineSteps.querySelectorAll('.source-chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            e.stopPropagation();
            const sourceId = chip.dataset.sourceId;
            const source = sources.find(s => s.source_id === sourceId);
            if (source) {
                displaySourceModal(source);
            }
        });
    });
}

function createPipelineStepHTML(step) {
    const statusClass = `status-${step.status}`;
    const statusIcon = step.status === 'completed' ? '✓' : step.status === 'warning' ? '!' : '×';

    // Format details
    let detailsHTML = '';
    if (step.details && Object.keys(step.details).length > 0) {
        detailsHTML = Object.entries(step.details).map(([key, value]) => {
            const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            return `
                <div class="step-details-row">
                    <span class="step-details-label">${formattedKey}:</span>
                    <span>${displayValue}</span>
                </div>
            `;
        }).join('');
    }

    // Format source chips
    let sourcesHTML = '';
    if (step.sources_used && step.sources_used.length > 0) {
        sourcesHTML = `
            <div class="step-sources">
                ${step.sources_used.map(src => `
                    <span class="source-chip" data-source-id="${src.source_id}" title="${src.content_snippet}">
                        <span class="chip-icon">📄</span>
                        ${src.source_file.split('/').pop().split('\\').pop().substring(0, 20)}...
                    </span>
                `).join('')}
            </div>
        `;
    }

    return `
        <div class="pipeline-step" data-step-type="${step.step_type}">
            <div class="step-number ${statusClass}">${step.step_number}</div>
            <div class="step-content">
                <div class="step-header">
                    <span class="step-title">${step.title}</span>
                    <span class="step-duration">${step.duration_ms.toFixed(1)}ms</span>
                </div>
                <div class="step-description">${step.description}</div>
                ${sourcesHTML}
                <div class="step-details">
                    ${detailsHTML}
                </div>
            </div>
        </div>
    `;
}

function displaySourceModal(source) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'source-modal-overlay';
    overlay.innerHTML = `
        <div class="source-modal">
            <div class="source-modal-header">
                <span class="source-modal-title">📄 ${source.source_file}</span>
                <button class="source-modal-close">&times;</button>
            </div>
            <div class="source-modal-meta">
                <span>📁 ${source.modality}</span>
                <span>📊 Relevance: ${(source.relevance_score * 100).toFixed(1)}%</span>
                <span>🎯 Confidence: ${(source.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="source-modal-content">
                ${source.content}
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    // Show with animation
    requestAnimationFrame(() => {
        overlay.classList.add('active');
    });

    // Close handlers
    overlay.querySelector('.source-modal-close').addEventListener('click', () => {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300);
    });

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 300);
        }
    });
}

// ============================================
// Export Dropdown and Multi-Format Export
// ============================================

// Toggle export dropdown
document.getElementById('exportDropdownBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const dropdown = document.querySelector('.export-dropdown');
    dropdown.classList.toggle('open');
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.querySelector('.export-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

// Generate content for export
function generateExportContent(format) {
    if (!currentReasoningChain) return null;

    const chain = currentReasoningChain;

    if (format === 'markdown') {
        let md = `# Reasoning Chain Report\n\n`;
        md += `**Query:** ${chain.query}\n`;
        md += `**Chain ID:** ${chain.chain_id}\n`;
        md += `**Timestamp:** ${chain.timestamp}\n`;
        md += `**Total Processing Time:** ${chain.total_duration_ms.toFixed(2)}ms\n`;
        md += `**Final Decision:** ${chain.final_decision}\n\n`;
        md += `---\n\n`;
        md += `## Key Insights\n\n`;
        chain.key_insights.forEach(insight => {
            md += `- ${insight}\n`;
        });
        md += `\n## Pipeline Steps\n\n`;
        chain.steps.forEach(step => {
            const statusIcon = step.status === 'completed' ? '✅' : step.status === 'warning' ? '⚠️' : '❌';
            md += `### Step ${step.step_number}: ${step.title} ${statusIcon}\n\n`;
            md += `**Type:** ${step.step_type}\n`;
            md += `**Duration:** ${step.duration_ms.toFixed(2)}ms\n\n`;
            md += `${step.description}\n\n`;

            if (step.details && Object.keys(step.details).length > 0) {
                md += `**Details:**\n`;
                Object.entries(step.details).forEach(([key, value]) => {
                    const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
                    md += `- ${key}: ${displayValue}\n`;
                });
                md += '\n';
            }

            if (step.sources_used && step.sources_used.length > 0) {
                md += `**Sources Referenced:**\n`;
                step.sources_used.forEach(src => {
                    md += `- [${src.source_file}] (relevance: ${src.relevance_score.toFixed(2)})\n`;
                });
                md += '\n';
            }

            md += `---\n\n`;
        });
        return md;
    }

    if (format === 'text') {
        let txt = `REASONING CHAIN REPORT\n`;
        txt += `${'='.repeat(50)}\n\n`;
        txt += `Query: ${chain.query}\n`;
        txt += `Chain ID: ${chain.chain_id}\n`;
        txt += `Timestamp: ${chain.timestamp}\n`;
        txt += `Total Processing Time: ${chain.total_duration_ms.toFixed(2)}ms\n`;
        txt += `Final Decision: ${chain.final_decision}\n\n`;
        txt += `${'='.repeat(50)}\n`;
        txt += `KEY INSIGHTS\n`;
        txt += `${'='.repeat(50)}\n\n`;
        chain.key_insights.forEach(insight => {
            txt += `* ${insight}\n`;
        });
        txt += `\n${'='.repeat(50)}\n`;
        txt += `PIPELINE STEPS\n`;
        txt += `${'='.repeat(50)}\n\n`;
        chain.steps.forEach(step => {
            const status = step.status === 'completed' ? '[OK]' : step.status === 'warning' ? '[WARN]' : '[ERR]';
            txt += `STEP ${step.step_number}: ${step.title} ${status}\n`;
            txt += `${'-'.repeat(40)}\n`;
            txt += `Type: ${step.step_type}\n`;
            txt += `Duration: ${step.duration_ms.toFixed(2)}ms\n\n`;
            txt += `${step.description}\n\n`;

            if (step.details && Object.keys(step.details).length > 0) {
                txt += `Details:\n`;
                Object.entries(step.details).forEach(([key, value]) => {
                    const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
                    txt += `  - ${key}: ${displayValue}\n`;
                });
                txt += '\n';
            }

            if (step.sources_used && step.sources_used.length > 0) {
                txt += `Sources Referenced:\n`;
                step.sources_used.forEach(src => {
                    txt += `  - ${src.source_file} (relevance: ${src.relevance_score.toFixed(2)})\n`;
                });
                txt += '\n';
            }

            txt += `\n`;
        });
        return txt;
    }

    return null;
}

// Export as PDF using print
function exportAsPDF() {
    if (!currentReasoningChain) {
        showToast('No Chain', 'No reasoning chain to export', 'warning');
        return;
    }

    const chain = currentReasoningChain;

    // Create a styled HTML document for PDF
    const pdfWindow = window.open('', '_blank');
    pdfWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reasoning Chain - ${chain.chain_id}</title>
            <style>
                body { font-family: 'Segoe UI', Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
                h1 { color: #4f46e5; border-bottom: 3px solid #4f46e5; padding-bottom: 10px; }
                h2 { color: #6366f1; margin-top: 30px; }
                h3 { color: #374151; margin-top: 20px; }
                .meta { background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; }
                .meta p { margin: 5px 0; }
                .insight { padding: 8px 15px; margin: 5px 0; background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border-left: 4px solid #6366f1; border-radius: 4px; }
                .step { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 15px 0; }
                .step-header { display: flex; justify-content: space-between; align-items: center; }
                .step-number { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 10px; }
                .step-number.warning { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
                .step-number.error { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
                .duration { background: #f3f4f6; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
                .details { background: #f9fafb; padding: 15px; border-radius: 6px; margin-top: 15px; font-size: 14px; }
                .source { display: inline-block; background: #e0f2fe; padding: 4px 10px; border-radius: 15px; margin: 3px 5px 3px 0; font-size: 12px; }
                @media print { body { padding: 20px; } }
            </style>
        </head>
        <body>
            <h1>🔗 Reasoning Chain Report</h1>
            
            <div class="meta">
                <p><strong>Query:</strong> ${chain.query}</p>
                <p><strong>Chain ID:</strong> ${chain.chain_id}</p>
                <p><strong>Timestamp:</strong> ${chain.timestamp}</p>
                <p><strong>Processing Time:</strong> ${chain.total_duration_ms.toFixed(2)}ms</p>
                <p><strong>Final Decision:</strong> ${chain.final_decision}</p>
            </div>
            
            <h2>📊 Key Insights</h2>
            ${chain.key_insights.map(i => `<div class="insight">${i}</div>`).join('')}
            
            <h2>🔄 Pipeline Steps</h2>
            ${chain.steps.map(step => {
        const statusClass = step.status === 'warning' ? 'warning' : step.status === 'error' ? 'error' : '';
        return `
                    <div class="step">
                        <div class="step-header">
                            <h3><span class="step-number ${statusClass}">${step.step_number}</span> ${step.title}</h3>
                            <span class="duration">${step.duration_ms.toFixed(1)}ms</span>
                        </div>
                        <p>${step.description}</p>
                        ${step.details && Object.keys(step.details).length > 0 ? `
                            <div class="details">
                                <strong>Details:</strong><br>
                                ${Object.entries(step.details).map(([k, v]) =>
            `• ${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`
        ).join('<br>')}
                            </div>
                        ` : ''}
                        ${step.sources_used && step.sources_used.length > 0 ? `
                            <div style="margin-top: 10px;">
                                <strong>Sources:</strong><br>
                                ${step.sources_used.map(s => `<span class="source">📄 ${s.source_file.split('/').pop().split('\\\\').pop()}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                `;
    }).join('')}
            
            <p style="color: #9ca3af; text-align: center; margin-top: 40px; font-size: 12px;">
                Generated by Multimodal RAG System • ${new Date().toLocaleString()}
            </p>
        </body>
        </html>
    `);
    pdfWindow.document.close();

    // Trigger print dialog (which can save as PDF)
    setTimeout(() => {
        pdfWindow.print();
    }, 500);

    showToast('📕 PDF Ready', 'Use the print dialog to save as PDF', 'success');
}

// Handle export option clicks
document.querySelectorAll('.export-option').forEach(btn => {
    btn.addEventListener('click', () => {
        const format = btn.dataset.format;
        const dropdown = document.querySelector('.export-dropdown');
        dropdown.classList.remove('open');

        if (!currentReasoningChain) {
            showToast('No Chain', 'No reasoning chain to export', 'warning');
            return;
        }

        try {
            if (format === 'pdf') {
                exportAsPDF();
                return;
            }

            const content = generateExportContent(format);
            if (!content) {
                showToast('Export Failed', 'Could not generate content', 'error');
                return;
            }

            // Determine file extension and MIME type
            let extension, mimeType, formatName;
            if (format === 'markdown') {
                extension = 'md';
                mimeType = 'text/markdown';
                formatName = 'Markdown';
            } else if (format === 'text') {
                extension = 'txt';
                mimeType = 'text/plain';
                formatName = 'Text';
            }

            // Download file
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reasoning_chain_${currentReasoningChain.chain_id}.${extension}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast('✅ Exported!', `Reasoning chain saved as ${formatName}`, 'success');
        } catch (error) {
            showToast('Export Failed', error.message, 'error');
        }
    });
});

// Clear Database functionality with custom modal confirmation
const clearDbBtn = document.getElementById('clearDbBtn');

// Create custom confirmation modal
function showClearDatabaseModal() {
    return new Promise((resolve) => {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            animation: slideIn 0.3s ease;
        `;

        modal.innerHTML = `
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 48px; margin-bottom: 15px;">🗑️</div>
                <h2 style="margin: 0 0 10px 0; color: #d32f2f; font-size: 24px;">Clear Database?</h2>
            </div>
            
            <div style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <p style="margin: 0 0 10px 0; font-weight: bold; color: #e65100;">⚠️ WARNING: This action cannot be undone!</p>
                <p style="margin: 0; color: #666; font-size: 14px;">This will permanently delete:</p>
                <ul style="margin: 10px 0 0 20px; color: #666; font-size: 14px;">
                    <li>All uploaded documents</li>
                    <li>All generated chunks</li>
                    <li>All embeddings</li>
                </ul>
            </div>

            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="cancelClearBtn" style="
                    padding: 12px 24px;
                    border: 2px solid #ddd;
                    background: white;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 500;
                    color: #666;
                    transition: all 0.2s;
                ">Cancel</button>
                <button id="confirmClearBtn" style="
                    padding: 12px 24px;
                    border: none;
                    background: #d32f2f;
                    color: white;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 500;
                    transition: all 0.2s;
                ">Yes, Clear Database</button>
            </div>
        `;

        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);

        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes slideIn {
                from { transform: translateY(-20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            #cancelClearBtn:hover {
                background: #f5f5f5;
                border-color: #999;
            }
            #confirmClearBtn:hover {
                background: #b71c1c;
                transform: scale(1.02);
            }
        `;
        document.head.appendChild(style);

        // Handle button clicks
        const confirmBtn = modal.querySelector('#confirmClearBtn');
        const cancelBtn = modal.querySelector('#cancelClearBtn');

        confirmBtn.addEventListener('click', () => {
            backdrop.remove();
            style.remove();
            resolve(true);
        });

        cancelBtn.addEventListener('click', () => {
            backdrop.remove();
            style.remove();
            resolve(false);
        });

        // Close on backdrop click
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.remove();
                style.remove();
                resolve(false);
            }
        });

        // Close on Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                backdrop.remove();
                style.remove();
                resolve(false);
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
    });
}

clearDbBtn.addEventListener('click', async () => {
    // Show custom confirmation modal
    const confirmed = await showClearDatabaseModal();

    if (!confirmed) {
        showToast(
            'ℹ️ Action Cancelled',
            'Database clear operation was cancelled',
            'info'
        );
        return;
    }

    // UI feedback - Make button more visually distinct during clearing
    clearDbBtn.disabled = true;
    clearDbBtn.style.opacity = '0.6';
    clearDbBtn.textContent = '🗑️ Clearing...';
    uploadStatus.textContent = '⏳ Clearing database...';
    uploadStatus.className = 'upload-status';

    // Show progress toast
    showToast(
        '⏳ Processing',
        'Clearing all database contents...',
        'warning'
    );

    try {
        const response = await fetch('/reset', {
            method: 'DELETE'
        });

        if (response.ok) {
            const data = await response.json();
            uploadStatus.textContent = '✓ Database cleared successfully!';
            uploadStatus.className = 'upload-status success';
            totalChunksEl.textContent = '0';

            // Show prominent success toast
            showToast(
                '✅ Success!',
                'All database contents have been permanently deleted. Total chunks: 0',
                'success'
            );

            // Hide response section if visible
            responseSection.style.display = 'none';

            // Clear query input
            queryInput.value = '';

            // ========= FULL UI RESET =========
            // Reset file input to allow re-upload of same files
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';

            // Clear any pending uploads display
            const selectedFiles = document.getElementById('selectedFiles');
            if (selectedFiles) selectedFiles.innerHTML = '';

            // Reset upload progress
            const uploadProgress = document.querySelector('.upload-progress');
            if (uploadProgress) uploadProgress.style.display = 'none';

            // Reset drag-drop zone
            const dropZone = document.getElementById('dropZone');
            if (dropZone) {
                dropZone.classList.remove('dragover', 'uploading');
            }

            // Clear sync notifications
            const notificationsList = document.getElementById('notificationsList');
            if (notificationsList) {
                notificationsList.innerHTML = '<div class="notification-placeholder">No notifications yet. Start watching a folder to see live updates.</div>';
            }

            // Reset sync tracking counts display
            const trackedFilesEl = document.getElementById('trackedFilesCount');
            const changesEl = document.getElementById('changesDetectedCount');
            if (trackedFilesEl) trackedFilesEl.textContent = '0';
            if (changesEl) changesEl.textContent = '0';

            // Clear stored sync notifications array
            if (typeof syncNotifications !== 'undefined') {
                syncNotifications.length = 0;
            }

            // Clear chat history display
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) chatMessages.innerHTML = '';

            // Clear any evidence sections
            const evidenceContainer = document.querySelector('.evidence-cards-grid');
            if (evidenceContainer) evidenceContainer.innerHTML = '';

            // ========= END UI RESET =========

            // Flash the total chunks to draw attention
            totalChunksEl.style.transition = 'all 0.3s';
            totalChunksEl.style.transform = 'scale(1.5)';
            totalChunksEl.style.color = '#4caf50';
            setTimeout(() => {
                totalChunksEl.style.transform = 'scale(1)';
                totalChunksEl.style.color = '';
            }, 500);

            // Clear status message after delay
            setTimeout(() => {
                uploadStatus.textContent = '';
                uploadStatus.className = 'upload-status';
            }, 3000);
        } else {
            const data = await response.json();
            uploadStatus.textContent = `✗ Error: ${data.detail || 'Unknown error'}`;
            uploadStatus.className = 'upload-status error';

            // Show error toast
            showToast(
                '❌ Error',
                `Failed to clear database: ${data.detail || 'Unknown error'}`,
                'error'
            );
        }
    } catch (error) {
        uploadStatus.textContent = `✗ Failed: ${error.message}`;
        uploadStatus.className = 'upload-status error';

        // Show error toast
        showToast(
            '❌ Error',
            `Failed to clear database: ${error.message}`,
            'error'
        );
    } finally {
        clearDbBtn.disabled = false;
        clearDbBtn.style.opacity = '1';
        clearDbBtn.textContent = '🗑️ Clear Database';

        // Update stats after clearing
        setTimeout(updateStats, 500);
    }
});

// ============================================
// Summarize Repository Feature
// ============================================

const summarizeBtn = document.getElementById('summarizeBtn');
const summaryModal = document.getElementById('summaryModal');
const closeSummaryModal = document.getElementById('closeSummaryModal');
const summaryContent = document.getElementById('summaryContent');

// Open summary modal and fetch data
summarizeBtn?.addEventListener('click', async () => {
    summaryModal.classList.add('active');

    // Show loading state
    summaryContent.innerHTML = `
        <div class="summary-loading">
            <div class="loading-spinner"></div>
            <p>Analyzing your knowledge base...</p>
        </div>
    `;

    try {
        const response = await fetch('/summarize');
        const data = await response.json();

        if (data.success) {
            renderSummary(data.summary);
        } else {
            summaryContent.innerHTML = `
                <div class="summary-loading">
                    <p>❌ Failed to generate summary: ${data.error || 'Unknown error'}</p>
                </div>
            `;
        }
    } catch (error) {
        summaryContent.innerHTML = `
            <div class="summary-loading">
                <p>❌ Error: ${error.message}</p>
            </div>
        `;
    }
});

// Close modal
closeSummaryModal?.addEventListener('click', () => {
    summaryModal.classList.remove('active');
});

// Close on overlay click
summaryModal?.addEventListener('click', (e) => {
    if (e.target === summaryModal) {
        summaryModal.classList.remove('active');
    }
});

// Render summary content
function renderSummary(summary) {
    const modalityIcons = {
        'text': '📄',
        'image': '🖼️',
        'audio': '🎙️'
    };

    let html = '';

    // Executive Summary
    html += `
        <div class="summary-section">
            <h3>📋 Executive Summary</h3>
            <div class="executive-summary">${summary.executive_summary}</div>
        </div>
    `;

    // Stats Grid
    html += `
        <div class="summary-section">
            <h3>📊 Knowledge Base Stats</h3>
            <div class="summary-stats-grid">
                <div class="summary-stat-card">
                    <div class="summary-stat-value">${summary.total_documents}</div>
                    <div class="summary-stat-label">Documents</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-value">${summary.total_chunks}</div>
                    <div class="summary-stat-label">Chunks</div>
                </div>
                ${summary.modalities.map(m => `
                    <div class="summary-stat-card">
                        <div class="summary-stat-value">${m.count}</div>
                        <div class="summary-stat-label">${modalityIcons[m.name] || '📁'} ${m.name} (${m.percentage}%)</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    // Themes
    if (summary.themes && summary.themes.length > 0) {
        html += `
            <div class="summary-section">
                <h3>🏷️ Main Themes</h3>
                <div class="themes-container">
                    ${summary.themes.map(t => `
                        <span class="theme-tag ${t.importance}">${t.theme} (${t.frequency})</span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Table of Contents
    if (summary.sources && summary.sources.length > 0) {
        html += `
            <div class="summary-section">
                <h3>📚 Table of Contents</h3>
                <ul class="toc-list">
                    ${summary.sources.map(s => {
            const fileName = s.file.split('/').pop().split('\\').pop();
            const icon = modalityIcons[s.modality] || '📁';
            return `
                            <li class="toc-item">
                                <span class="toc-icon">${icon}</span>
                                <div class="toc-details">
                                    <div class="toc-name">${fileName}</div>
                                    <div class="toc-meta">${s.chunk_count} chunks • ${s.modality}</div>
                                </div>
                            </li>
                        `;
        }).join('')}
                </ul>
            </div>
        `;
    }

    // Knowledge Gaps
    if (summary.potential_gaps && summary.potential_gaps.length > 0) {
        html += `
            <div class="summary-section">
                <h3>⚠️ Knowledge Gaps</h3>
                ${summary.potential_gaps.map(gap => `
                    <div class="gap-item">${gap}</div>
                `).join('')}
            </div>
        `;
    }

    // Conflicts
    if (summary.potential_conflicts && summary.potential_conflicts.length > 0) {
        html += `
            <div class="summary-section">
                <h3>⚔️ Potential Conflicts Detected</h3>
                ${summary.potential_conflicts.map(c => `
                    <div class="conflict-item ${c.severity}">
                        <div>
                            <strong>${c.topic}</strong>: ${c.values.join(' vs ')}
                            <div class="conflict-sources">Sources: ${c.sources.join(', ')}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    summaryContent.innerHTML = html;
}

// ============================================
// Confidence Explainability Dashboard
// ============================================

// Toggle dashboard on confidence badge click
document.getElementById('confidenceBadge')?.addEventListener('click', () => {
    const dashboard = document.getElementById('confidenceDashboard');

    if (!currentConfidenceBreakdown) {
        showToast('🔒 No Data', 'Confidence breakdown not available', 'warning');
        return;
    }

    if (dashboard.style.display === 'none' || dashboard.style.display === '') {
        renderConfidenceDashboard(currentConfidenceBreakdown);
        dashboard.style.display = 'block';
    } else {
        dashboard.style.display = 'none';
    }
});

// Close dashboard button
document.getElementById('closeDashboard')?.addEventListener('click', () => {
    document.getElementById('confidenceDashboard').style.display = 'none';
});

function renderConfidenceDashboard(breakdown) {
    const factorGauges = document.getElementById('factorGauges');
    const tipsSection = document.getElementById('tipsSection');
    const actionableTips = document.getElementById('actionableTips');
    const strongestFactor = document.getElementById('strongestFactor');
    const weakestFactor = document.getElementById('weakestFactor');

    // Render factor gauges
    factorGauges.innerHTML = breakdown.factors.map(factor => {
        const percentage = Math.round(factor.score * 100);
        const level = percentage >= 70 ? 'high' : percentage >= 40 ? 'medium' : 'low';

        return `
            <div class="factor-gauge">
                <div class="factor-header">
                    <span class="factor-name">${factor.icon} ${factor.name}</span>
                    <span class="factor-score ${level}">${percentage}%</span>
                </div>
                <div class="gauge-track">
                    <div class="gauge-fill ${level}" style="width: ${percentage}%"></div>
                </div>
                <div class="factor-description">${factor.description}</div>
            </div>
        `;
    }).join('');

    // Render actionable tips
    if (breakdown.actionable_tips && breakdown.actionable_tips.length > 0) {
        tipsSection.style.display = 'block';
        actionableTips.innerHTML = breakdown.actionable_tips.map(tip => `
            <div class="tip-item">${tip}</div>
        `).join('');
    } else {
        tipsSection.style.display = 'none';
    }

    // Render strongest/weakest factors
    if (breakdown.strongest_factor) {
        strongestFactor.innerHTML = `
            <div class="insight-label">💪 Strongest Factor</div>
            <div class="insight-value">${breakdown.strongest_factor}</div>
        `;
    }

    if (breakdown.weakest_factor) {
        weakestFactor.innerHTML = `
            <div class="insight-label">⚠️ Needs Improvement</div>
            <div class="insight-value">${breakdown.weakest_factor}</div>
        `;
    }
}

// ============================================
// Visual Answer Annotations Helpers
// ============================================

/**
 * Extract key terms from image content/OCR text relevant to the query
 */
function extractKeyTerms(content, query) {
    if (!content || !query) return [];

    const queryWords = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    const contentWords = content.toLowerCase().split(/\s+/);

    // Find terms that match or relate to query
    const relevantTerms = [];
    const seen = new Set();

    // Pattern for important values (numbers with units)
    const valuePatterns = /\b(\d+(?:\.\d+)?)\s*(v|V|volt|volts|kg|Kg|lbs|°C|°F|%|mm|cm|m|A|amp|W|watt)\b/g;
    let match;
    while ((match = valuePatterns.exec(content)) !== null) {
        const term = `${match[1]}${match[2]}`;
        if (!seen.has(term.toLowerCase())) {
            relevantTerms.push(term);
            seen.add(term.toLowerCase());
        }
    }

    // Find query-related words in content
    for (const word of queryWords) {
        const regex = new RegExp(`\\b${word}\\w*\\b`, 'gi');
        const matches = content.match(regex);
        if (matches) {
            for (const m of matches) {
                if (!seen.has(m.toLowerCase()) && m.length > 2) {
                    relevantTerms.push(m);
                    seen.add(m.toLowerCase());
                }
            }
        }
    }

    // Add any capitalized terms (likely labels/titles)
    const capitalizedTerms = content.match(/\b[A-Z][A-Z0-9]+\b/g) || [];
    for (const term of capitalizedTerms) {
        if (!seen.has(term.toLowerCase()) && term.length > 1) {
            relevantTerms.push(term);
            seen.add(term.toLowerCase());
        }
    }

    return relevantTerms.slice(0, 6);
}

/**
 * Generate visual highlight regions based on relevance
 */
function generateHighlightRegions(relevanceScore, termCount) {
    const regions = [];
    const count = Math.min(termCount, 3);

    // Generate pseudo-random but consistent positions
    const positions = [
        { top: '15%', left: '10%', width: '35%', height: '25%' },
        { top: '45%', left: '55%', width: '40%', height: '30%' },
        { top: '70%', left: '15%', width: '30%', height: '22%' }
    ];

    for (let i = 0; i < count; i++) {
        const pos = positions[i];
        const opacity = 0.3 + (relevanceScore * 0.3);
        regions.push(`
            <div class="highlight-region" style="
                top: ${pos.top}; 
                left: ${pos.left}; 
                width: ${pos.width}; 
                height: ${pos.height};
                --region-opacity: ${opacity};
                --region-index: ${i};
            ">
                <span class="region-label">${i + 1}</span>
            </div>
        `);
    }

    return regions.join('');
}

/**
 * Render side-by-side image comparison panel
 */
function renderImageComparisonPanel(imageSources, query) {
    // Find or create comparison panel container
    let comparisonPanel = document.getElementById('imageComparisonPanel');

    if (imageSources.length < 2) {
        if (comparisonPanel) comparisonPanel.style.display = 'none';
        return;
    }

    // Create panel if it doesn't exist
    if (!comparisonPanel) {
        comparisonPanel = document.createElement('div');
        comparisonPanel.id = 'imageComparisonPanel';
        comparisonPanel.className = 'image-comparison-panel';
        // Insert before evidence sources
        const evidencePanel = document.querySelector('.evidence-panel');
        if (evidencePanel) {
            evidencePanel.parentNode.insertBefore(comparisonPanel, evidencePanel);
        }
    }

    comparisonPanel.style.display = 'block';
    comparisonPanel.innerHTML = `
        <div class="comparison-header">
            <h4>📸 Visual Evidence Comparison</h4>
            <span class="comparison-count">${imageSources.length} images found</span>
        </div>
        <div class="comparison-description">
            Compare visual evidence across multiple sources for "${query}"
        </div>
        <div class="comparison-grid">
            ${imageSources.map((source, idx) => {
        const keyTerms = extractKeyTerms(source.content, query);
        const fileName = (source.source_file || 'Unknown').split('/').pop().split('\\').pop();

        return `
                    <div class="comparison-card">
                        <div class="comparison-card-header">
                            <span class="comparison-index">${idx + 1}</span>
                            <span class="comparison-filename">${fileName}</span>
                            <span class="comparison-relevance ${source.relevance_score > 0.5 ? 'high' : 'medium'}">
                                ${(source.relevance_score * 100).toFixed(0)}%
                            </span>
                        </div>
                        <div class="comparison-image-box">
                            <div class="comparison-placeholder">🖼️</div>
                        </div>
                        <div class="comparison-insights">
                            ${keyTerms.slice(0, 3).map(t => `<span class="comparison-term">${t}</span>`).join('')}
                        </div>
                        <div class="comparison-summary">
                            ${source.content.substring(0, 100)}${source.content.length > 100 ? '...' : ''}
                        </div>
                    </div>
                `;
    }).join('')}
        </div>
    `;
}

// ============================================
// Conversation Context Management
// ============================================

// Generate a session ID
function generateSessionId() {
    return 'sess_' + Math.random().toString(36).substring(2, 10);
}

// Toggle context on/off
document.getElementById('contextToggle')?.addEventListener('click', () => {
    contextEnabled = !contextEnabled;

    const toggleBtn = document.getElementById('contextToggle');
    const badge = document.getElementById('contextBadge');
    const details = document.getElementById('contextDetails');

    if (contextEnabled) {
        // Enable context
        if (!sessionId) {
            sessionId = generateSessionId();
        }
        toggleBtn.textContent = 'Disable';
        toggleBtn.classList.add('active');
        badge.textContent = 'Active';
        badge.classList.add('active');
        details.style.display = 'block';

        updateContextDisplay();
        showToast('🧠 Semantic Memory', 'Conversation context enabled. I\'ll remember our conversation!', 'success');
    } else {
        // Disable context
        toggleBtn.textContent = 'Enable';
        toggleBtn.classList.remove('active');
        badge.textContent = 'Off';
        badge.classList.remove('active');
        details.style.display = 'none';

        showToast('🧠 Semantic Memory', 'Conversation context disabled.', 'info');
    }
});

// Update context display with current session info
async function updateContextDisplay() {
    if (!sessionId) return;

    try {
        const response = await fetch(`/context/${sessionId}`);
        const data = await response.json();

        document.getElementById('sessionIdDisplay').textContent = data.session_id.substring(0, 8) + '...';
        document.getElementById('messageCount').textContent = data.message_count;
        document.getElementById('entityCount').textContent = data.entity_count;

        // Update entities list
        const entitiesList = document.getElementById('entitiesList');
        if (data.entities && data.entities.length > 0) {
            entitiesList.innerHTML = data.entities.map(e => `
                <span class="entity-chip">
                    <span class="entity-type">${getEntityIcon(e.type)}</span>
                    ${e.name}
                </span>
            `).join('');
        } else {
            entitiesList.innerHTML = '<span class="entities-placeholder">No entities tracked yet</span>';
        }
    } catch (error) {
        console.error('Failed to update context display:', error);
    }
}

// Get icon for entity type
function getEntityIcon(type) {
    const icons = {
        'value': '📊',
        'machine': '⚙️',
        'document': '📄',
        'person': '👤',
        'concept': '💡',
        'unknown': '🔹'
    };
    return icons[type] || icons['unknown'];
}

// Clear context with popup confirmation
document.getElementById('clearContextBtn')?.addEventListener('click', () => {
    if (!sessionId) return;

    showClearContextPopup();
});

// Show clear context confirmation popup
function showClearContextPopup() {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'popup-overlay';
    overlay.id = 'clearContextOverlay';

    // Create popup
    const popup = document.createElement('div');
    popup.className = 'popup-modal context-popup';
    popup.innerHTML = `
        <div class="popup-header">
            <span class="popup-icon">🧠</span>
            <h3>Clear Conversation Context?</h3>
        </div>
        <div class="popup-body">
            <p>This will reset:</p>
            <ul class="clear-list">
                <li>📝 All conversation history</li>
                <li>🔖 Tracked entities (${document.getElementById('entityCount')?.textContent || 0} items)</li>
                <li>💬 Message context (${document.getElementById('messageCount')?.textContent || 0} messages)</li>
            </ul>
            <p class="warning-text">A new session will be started.</p>
        </div>
        <div class="popup-actions">
            <button class="popup-btn cancel" id="cancelClearContext">Cancel</button>
            <button class="popup-btn confirm danger" id="confirmClearContext">🗑️ Clear Context</button>
        </div>
    `;

    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
        overlay.classList.add('visible');
        popup.classList.add('visible');
    });

    // Cancel button
    document.getElementById('cancelClearContext').addEventListener('click', () => {
        closeClearContextPopup();
        showToast('✅ Cancelled', 'Conversation context preserved.', 'info');
    });

    // Confirm button
    document.getElementById('confirmClearContext').addEventListener('click', async () => {
        try {
            await fetch(`/context/${sessionId}`, { method: 'DELETE' });

            // Generate new session
            sessionId = generateSessionId();
            updateContextDisplay();

            closeClearContextPopup();
            showToast('🗑️ Context Cleared', 'Conversation history has been reset. New session started!', 'success');
        } catch (error) {
            closeClearContextPopup();
            showToast('❌ Error', 'Failed to clear context.', 'error');
        }
    });

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeClearContextPopup();
        }
    });
}

// Close clear context popup
function closeClearContextPopup() {
    const overlay = document.getElementById('clearContextOverlay');
    if (overlay) {
        overlay.classList.remove('visible');
        setTimeout(() => overlay.remove(), 300);
    }
}

// Show context resolution notice
function showContextResolutionNotice(originalQuery, resolvedQuery) {
    // Remove any existing notice
    const existingNotice = document.querySelector('.context-resolution-notice');
    if (existingNotice) existingNotice.remove();

    // Create notice
    const notice = document.createElement('div');
    notice.className = 'context-resolution-notice';
    notice.innerHTML = `
        <span class="resolution-icon">🧠</span>
        <span>Understood "<em>${originalQuery}</em>" as: <span class="resolved-query">"${resolvedQuery}"</span></span>
    `;

    // Insert before answer content
    const answerContent = document.getElementById('answerContent');
    answerContent.parentNode.insertBefore(notice, answerContent);
}

// ============================================
// Knowledge Graph Visualization
// ============================================

let graphData = null;
let graphNodes = [];
let graphVisible = false;
let selectedNode = null;
let hoveredNode = null;

// Node colors by type
const nodeColors = {
    document: { fill: '#3b82f6', stroke: '#1d4ed8' },
    value: { fill: '#10b981', stroke: '#047857' },
    machine: { fill: '#f59e0b', stroke: '#d97706' },
    concept: { fill: '#8b5cf6', stroke: '#6d28d9' },
    year: { fill: '#ec4899', stroke: '#be185d' },
    unknown: { fill: '#6b7280', stroke: '#4b5563' }
};

// Toggle graph visibility
document.getElementById('toggleGraphBtn')?.addEventListener('click', async () => {
    const container = document.getElementById('graphContainer');
    const btn = document.getElementById('toggleGraphBtn');

    graphVisible = !graphVisible;

    if (graphVisible) {
        container.style.display = 'block';
        btn.textContent = '📉 Hide Graph';
        btn.classList.add('active');
        await loadKnowledgeGraph();
    } else {
        container.style.display = 'none';
        btn.textContent = '📈 Show Graph';
        btn.classList.remove('active');
    }
});

// Refresh graph
document.getElementById('refreshGraphBtn')?.addEventListener('click', async () => {
    if (graphVisible) {
        await loadKnowledgeGraph();
        showToast('📊 Graph Refreshed', 'Knowledge graph has been updated.', 'success');
    }
});

// Load knowledge graph data
async function loadKnowledgeGraph() {
    const loading = document.getElementById('graphLoading');
    loading.style.display = 'flex';

    try {
        const response = await fetch('/graph');
        graphData = await response.json();

        // Update stats
        document.getElementById('graphDocCount').textContent = graphData.stats.document_count;
        document.getElementById('graphEntityCount').textContent = graphData.stats.entity_count;
        document.getElementById('graphEdgeCount').textContent = graphData.stats.edge_count;

        if (graphData.nodes.length === 0) {
            showEmptyGraph();
        } else {
            initializeGraphLayout();
            renderGraph();
        }
    } catch (error) {
        console.error('Failed to load knowledge graph:', error);
        showToast('❌ Error', 'Failed to load knowledge graph.', 'error');
    } finally {
        loading.style.display = 'none';
    }
}

// Show empty graph state
function showEmptyGraph() {
    const wrapper = document.querySelector('.graph-canvas-wrapper');
    wrapper.innerHTML = `
        <div class="graph-empty">
            <div class="empty-icon">📭</div>
            <p>No documents uploaded yet.</p>
            <p>Upload some documents to visualize the knowledge graph!</p>
        </div>
    `;
}

// Initialize node positions using force-directed layout
function initializeGraphLayout() {
    const canvas = document.getElementById('graphCanvas');
    const width = canvas.offsetWidth || 800;
    const height = canvas.offsetHeight || 450;

    // Create node positions
    graphNodes = graphData.nodes.map((node, i) => {
        // Initial positions in a circle
        const angle = (2 * Math.PI * i) / graphData.nodes.length;
        const radius = Math.min(width, height) * 0.35;

        return {
            ...node,
            x: width / 2 + radius * Math.cos(angle),
            y: height / 2 + radius * Math.sin(angle),
            vx: 0,
            vy: 0,
            radius: node.type === 'document' ? 20 : 12
        };
    });

    // Simple force simulation
    for (let iteration = 0; iteration < 100; iteration++) {
        applyForces(width, height);
    }
}

// Apply forces for layout
function applyForces(width, height) {
    const repulsion = 2000;
    const attraction = 0.01;
    const damping = 0.8;

    // Repulsion between all nodes
    for (let i = 0; i < graphNodes.length; i++) {
        for (let j = i + 1; j < graphNodes.length; j++) {
            const dx = graphNodes[j].x - graphNodes[i].x;
            const dy = graphNodes[j].y - graphNodes[i].y;
            const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
            const force = repulsion / (dist * dist);

            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            graphNodes[i].vx -= fx;
            graphNodes[i].vy -= fy;
            graphNodes[j].vx += fx;
            graphNodes[j].vy += fy;
        }
    }

    // Attraction along edges
    for (const edge of graphData.edges) {
        const sourceNode = graphNodes.find(n => n.id === edge.source);
        const targetNode = graphNodes.find(n => n.id === edge.target);

        if (sourceNode && targetNode) {
            const dx = targetNode.x - sourceNode.x;
            const dy = targetNode.y - sourceNode.y;

            sourceNode.vx += dx * attraction;
            sourceNode.vy += dy * attraction;
            targetNode.vx -= dx * attraction;
            targetNode.vy -= dy * attraction;
        }
    }

    // Apply velocities and boundary constraints
    for (const node of graphNodes) {
        node.vx *= damping;
        node.vy *= damping;

        node.x += node.vx;
        node.y += node.vy;

        // Keep within bounds
        const margin = 40;
        node.x = Math.max(margin, Math.min(width - margin, node.x));
        node.y = Math.max(margin, Math.min(height - margin, node.y));
    }
}

// Render the graph on canvas
function renderGraph() {
    const canvas = document.getElementById('graphCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();

    // Set canvas size
    canvas.width = rect.width;
    canvas.height = rect.height;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw edges first
    ctx.lineWidth = 1;
    for (const edge of graphData.edges) {
        const sourceNode = graphNodes.find(n => n.id === edge.source);
        const targetNode = graphNodes.find(n => n.id === edge.target);

        if (sourceNode && targetNode) {
            // Highlight if connected to selected node
            if (selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id)) {
                ctx.strokeStyle = '#6366f1';
                ctx.lineWidth = 2;
            } else {
                ctx.strokeStyle = '#e5e7eb';
                ctx.lineWidth = 1;
            }

            ctx.beginPath();
            ctx.moveTo(sourceNode.x, sourceNode.y);
            ctx.lineTo(targetNode.x, targetNode.y);
            ctx.stroke();

            // Draw relationship label on hover
            if (hoveredNode && (edge.source === hoveredNode.id || edge.target === hoveredNode.id)) {
                const midX = (sourceNode.x + targetNode.x) / 2;
                const midY = (sourceNode.y + targetNode.y) / 2;

                ctx.font = '10px sans-serif';
                ctx.fillStyle = '#6b7280';
                ctx.textAlign = 'center';
                ctx.fillText(edge.relationship.replace(/_/g, ' '), midX, midY - 5);
            }
        }
    }

    // Draw nodes
    for (const node of graphNodes) {
        const colors = nodeColors[node.type] || nodeColors.unknown;
        const isSelected = selectedNode && selectedNode.id === node.id;
        const isHovered = hoveredNode && hoveredNode.id === node.id;

        // Draw node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + (isHovered ? 3 : 0), 0, Math.PI * 2);

        if (isSelected) {
            ctx.fillStyle = '#4f46e5';
            ctx.strokeStyle = '#312e81';
            ctx.lineWidth = 3;
        } else {
            ctx.fillStyle = colors.fill;
            ctx.strokeStyle = colors.stroke;
            ctx.lineWidth = 2;
        }

        ctx.fill();
        ctx.stroke();

        // Draw label
        ctx.font = node.type === 'document' ? 'bold 11px sans-serif' : '10px sans-serif';
        ctx.fillStyle = '#1f2937';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const label = node.label.length > 15 ? node.label.substring(0, 12) + '...' : node.label;
        ctx.fillText(label, node.x, node.y + node.radius + 4);
    }
}

// Canvas mouse interaction
const graphCanvas = document.getElementById('graphCanvas');
if (graphCanvas) {
    graphCanvas.addEventListener('click', (e) => {
        const rect = graphCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Find clicked node
        const clickedNode = graphNodes.find(node => {
            const dx = node.x - x;
            const dy = node.y - y;
            return Math.sqrt(dx * dx + dy * dy) <= node.radius + 5;
        });

        if (clickedNode) {
            selectNode(clickedNode);
        } else {
            hideNodeDetails();
        }
    });

    graphCanvas.addEventListener('mousemove', (e) => {
        const rect = graphCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Find hovered node
        const newHovered = graphNodes.find(node => {
            const dx = node.x - x;
            const dy = node.y - y;
            return Math.sqrt(dx * dx + dy * dy) <= node.radius + 5;
        });

        if (newHovered !== hoveredNode) {
            hoveredNode = newHovered;
            graphCanvas.style.cursor = hoveredNode ? 'pointer' : 'grab';
            renderGraph();
        }
    });
}

// Select a node and show details
async function selectNode(node) {
    selectedNode = node;
    renderGraph();

    const panel = document.getElementById('nodeDetailsPanel');
    const badge = document.getElementById('nodeTypeBadge');
    const label = document.getElementById('nodeLabel');
    const body = document.getElementById('nodeDetailsBody');

    badge.textContent = node.type;
    badge.className = `node-type-badge ${node.type}`;
    label.textContent = node.label;

    body.innerHTML = '<div class="loading-spinner"></div>';
    panel.style.display = 'block';

    try {
        const response = await fetch(`/graph/node/${encodeURIComponent(node.id)}`);
        const details = await response.json();

        if (details.connections && details.connections.length > 0) {
            body.innerHTML = `
                <p style="margin: 0 0 0.5rem; font-size: 0.85rem; color: #6b7280;">
                    ${details.connection_count} connection(s)
                </p>
                <ul class="connection-list">
                    ${details.connections.map(conn => `
                        <li>
                            <span class="connection-arrow">${conn.direction === 'outgoing' ? '→' : '←'}</span>
                            <span class="connection-type">${conn.relationship.replace(/_/g, ' ')}</span>
                            <span class="connection-label">${conn.node.label}</span>
                        </li>
                    `).join('')}
                </ul>
            `;
        } else {
            body.innerHTML = '<p style="color: #6b7280; font-size: 0.85rem;">No connections found.</p>';
        }
    } catch (error) {
        body.innerHTML = '<p style="color: #ef4444;">Failed to load details.</p>';
    }
}

// Hide node details panel
function hideNodeDetails() {
    selectedNode = null;
    document.getElementById('nodeDetailsPanel').style.display = 'none';
    renderGraph();
}

// Close node details
document.getElementById('closeNodeDetails')?.addEventListener('click', hideNodeDetails);

// ============================================
// Real-Time Document Sync (Polling-based)
// ============================================

let syncWatching = false;
let syncPollingInterval = null;
let syncNotifications = [];

// Start watching for file changes
async function startSyncWatching() {
    try {
        const response = await fetch('/sync/start', { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            syncWatching = true;
            updateSyncStatus('watching');
            showToast('🔄 Sync Started', 'Now watching for file changes', 'success');

            // Update watch folder path
            document.getElementById('watchFolderPath').textContent =
                data.watch_path ? data.watch_path.split('\\').pop() || data.watch_path.split('/').pop() : 'watch';

            // Start polling for changes every 2 seconds
            startSyncPolling();

            // Immediately poll once to catch any existing changes
            await pollForChanges();
        } else {
            showToast('❌ Error', data.detail || 'Failed to start', 'error');
        }
    } catch (error) {
        showToast('❌ Error', error.message, 'error');
    }
}

// Stop watching
async function stopSyncWatching() {
    try {
        const response = await fetch('/sync/stop', { method: 'POST' });

        if (response.ok) {
            syncWatching = false;
            updateSyncStatus('offline');
            stopSyncPolling();
            showToast('⏹️ Sync Stopped', 'File watching paused', 'info');
        }
    } catch (error) {
        console.error('Stop sync error:', error);
    }
}

// Single poll for changes
async function pollForChanges() {
    try {
        const response = await fetch('/sync/changes');
        const data = await response.json();

        console.log('Sync poll result:', data);

        // Update status
        updateSyncInfo(data.watcher_status);

        // Process any new changes
        if (data.changes && data.changes.length > 0) {
            console.log('Got sync changes:', data.changes);
            for (const change of data.changes) {
                addSyncNotification(change);
            }
        }
    } catch (error) {
        console.error('Polling error:', error);
    }
}

// Start polling for changes
function startSyncPolling() {
    if (syncPollingInterval) return;

    syncPollingInterval = setInterval(pollForChanges, 2000);
}

// Stop polling
function stopSyncPolling() {
    if (syncPollingInterval) {
        clearInterval(syncPollingInterval);
        syncPollingInterval = null;
    }
}

// Update sync status indicator
function updateSyncStatus(status) {
    const indicator = document.getElementById('syncStatusIndicator');
    if (!indicator) return;

    const dot = indicator.querySelector('.status-dot');
    const text = indicator.querySelector('.status-text');
    const btn = document.getElementById('toggleSyncBtn');

    dot.className = 'status-dot';

    switch (status) {
        case 'offline':
            dot.classList.add('offline');
            text.textContent = 'Offline';
            btn.textContent = '▶️ Start Watching';
            btn.classList.remove('active');
            break;

        case 'watching':
            dot.classList.add('watching');
            text.textContent = 'Watching';
            btn.textContent = '⏹️ Stop Watching';
            btn.classList.add('active');
            break;
    }
}

// Update sync info display
function updateSyncInfo(status) {
    if (!status) return;

    const pathEl = document.getElementById('watchFolderPath');
    const trackedEl = document.getElementById('trackedFilesCount');
    const changesEl = document.getElementById('changesDetectedCount');

    if (pathEl) {
        pathEl.textContent = status.watch_path ?
            status.watch_path.split('\\').pop() || status.watch_path.split('/').pop() : 'watch';
    }
    if (trackedEl) trackedEl.textContent = status.tracked_files || 0;
    if (changesEl) changesEl.textContent = status.total_changes_detected || 0;

    if (status.is_running && !syncWatching) {
        syncWatching = true;
        updateSyncStatus('watching');
        startSyncPolling();
    }
}

// Add sync notification
function addSyncNotification(data) {
    const list = document.getElementById('notificationsList');
    if (!list) return;

    // Remove placeholder if exists
    const placeholder = list.querySelector('.notification-placeholder');
    if (placeholder) placeholder.remove();

    // Create notification item
    const item = document.createElement('div');
    item.className = `notification-item ${data.change_type}`;

    // Icon mapping with better icons
    const icons = {
        created: '✨',
        modified: '📝',
        deleted: '🗑️',
        indexed: '📥',
        uploaded: '📤',
        auto_indexed: '🤖'  // Auto-indexed files
    };

    // Format file size
    const formatSize = (bytes) => {
        if (!bytes) return '';
        if (bytes < 1024) return `${bytes}B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
    };

    // Parse timestamp or use current time
    let time;
    if (data.timestamp) {
        try {
            const date = new Date(data.timestamp);
            time = date.toLocaleTimeString();
        } catch {
            time = new Date().toLocaleTimeString();
        }
    } else {
        time = new Date().toLocaleTimeString();
    }

    const filePath = data.path ? data.path.replace(/\\/g, '\\\\') : '';
    const fileSize = data.file_size ? formatSize(data.file_size) : '';

    // Different labels for different change types
    const changeLabels = {
        created: 'created',
        modified: 'modified',
        deleted: 'deleted',
        indexed: 'indexed',
        uploaded: 'uploaded',
        auto_indexed: 'auto-indexed'
    };

    // Check if auto-index is enabled
    const autoIndexEnabled = document.getElementById('autoIndexToggle')?.checked || false;

    // Determine if we should show the Index button
    // Don't show for: deleted, indexed, auto_indexed
    // Don't show for uploaded if auto-index is ON (will be auto-processed)
    const shouldShowIndexButton =
        (data.change_type === 'created' || data.change_type === 'modified') ||
        (data.change_type === 'uploaded' && !autoIndexEnabled);

    item.innerHTML = `
        <span class="notification-icon">${icons[data.change_type] || '📄'}</span>
        <div class="notification-content">
            <div class="notification-file">${data.file_name || 'Unknown file'}</div>
            <div class="notification-time">${changeLabels[data.change_type] || data.change_type} at ${time} ${fileSize ? `• ${fileSize}` : ''}</div>
        </div>
        ${shouldShowIndexButton ?
            `<button class="notification-action" data-path="${filePath}">Index</button>` :
            (data.change_type === 'uploaded' && autoIndexEnabled ?
                `<span class="notification-status">⏳ Queued</span>` :
                (data.change_type === 'auto_indexed' ?
                    `<span class="notification-status">✓ Done</span>` :
                    '')
            )
        }
    `;

    // Add click handler for index button
    const indexBtn = item.querySelector('.notification-action');
    if (indexBtn) {
        indexBtn.addEventListener('click', () => {
            indexWatchedFile(data.path);
        });
    }

    // Add to top of list
    list.insertBefore(item, list.firstChild);

    // Limit to 20 notifications
    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }

    // Store notification
    syncNotifications.unshift(data);
    if (syncNotifications.length > 20) syncNotifications.pop();

    // Show toast for important changes
    if (data.change_type === 'created') {
        showToast('📄 New File', `${data.file_name} detected`, 'success');
    } else if (data.change_type === 'uploaded') {
        showToast('📤 File Uploaded', `${data.file_name} ready to index`, 'success');
    }
}

// Index a watched file
async function indexWatchedFile(filePath) {
    if (!filePath) {
        showToast('❌ Error', 'No file path provided', 'error');
        return;
    }

    try {
        showToast('⏳ Indexing...', 'Processing file', 'info');

        const response = await fetch(`/sync/index-file?file_path=${encodeURIComponent(filePath)}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            showToast('✅ Indexed', data.message, 'success');
            updateStats();

            // Add indexed notification
            addSyncNotification({
                file_name: filePath.split('\\').pop() || filePath.split('/').pop(),
                change_type: 'indexed',
                chunks_created: data.chunks_created
            });
        } else {
            showToast('❌ Error', data.detail || 'Failed to index', 'error');
        }
    } catch (error) {
        showToast('❌ Error', error.message, 'error');
    }
}

// Toggle sync watching
document.getElementById('toggleSyncBtn')?.addEventListener('click', async () => {
    if (syncWatching) {
        await stopSyncWatching();
    } else {
        await startSyncWatching();
    }
});

// Clear notifications
document.getElementById('clearNotificationsBtn')?.addEventListener('click', () => {
    const list = document.getElementById('notificationsList');
    if (list) {
        list.innerHTML = `
            <div class="notification-placeholder">
                No notifications yet. Start watching a folder to see live updates.
            </div>
        `;
    }
    syncNotifications = [];
    showToast('🧹 Cleared', 'Notifications cleared', 'info');
});

// Auto-Index Toggle Handler
document.getElementById('autoIndexToggle')?.addEventListener('change', async (e) => {
    const enabled = e.target.checked;
    const statusEl = document.getElementById('autoIndexStatus');

    try {
        const response = await fetch(`/sync/auto-index?enabled=${enabled}`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            if (statusEl) {
                statusEl.textContent = enabled ? 'On' : 'Off';
                statusEl.classList.toggle('active', enabled);
            }
            showToast(
                enabled ? '🤖 Auto-Index ON' : '🛑 Auto-Index OFF',
                enabled ? 'New files will be indexed automatically' : 'Auto-indexing disabled',
                enabled ? 'success' : 'info'
            );
        }
    } catch (error) {
        console.error('Auto-index toggle error:', error);
        e.target.checked = !enabled; // Revert toggle
        showToast('❌ Error', 'Failed to toggle auto-index', 'error');
    }
});

// Process auto-index queue
async function processAutoIndexQueue() {
    try {
        const response = await fetch('/sync/auto-index/process', { method: 'POST' });
        const data = await response.json();

        if (data.processed > 0) {
            showToast('🤖 Auto-Indexed', `${data.processed} file(s) processed`, 'success');
            updateStats();
        }
    } catch (error) {
        console.error('Auto-index process error:', error);
    }
}

// Update pollForChanges to also process auto-index queue
const originalPollForChanges = pollForChanges;
pollForChanges = async function () {
    await originalPollForChanges();

    // Also process auto-index queue if enabled
    const toggle = document.getElementById('autoIndexToggle');
    if (toggle && toggle.checked) {
        await processAutoIndexQueue();
    }
};

// Initialize sync on page load
async function initSync() {
    try {
        const response = await fetch('/sync/status');
        const data = await response.json();
        updateSyncInfo(data.watcher_status);

        // Update auto-index toggle state
        const toggle = document.getElementById('autoIndexToggle');
        const statusEl = document.getElementById('autoIndexStatus');
        if (toggle && data.auto_index_enabled !== undefined) {
            toggle.checked = data.auto_index_enabled;
            if (statusEl) {
                statusEl.textContent = data.auto_index_enabled ? 'On' : 'Off';
                statusEl.classList.toggle('active', data.auto_index_enabled);
            }
        }
    } catch (error) {
        console.log('Sync status unavailable');
    }
}

initSync();

// Load initial stats
updateStats();

// ============================================
// Live Web Search Toggle Handler
// ============================================

document.getElementById('webSearchToggle')?.addEventListener('click', () => {
    webSearchEnabled = !webSearchEnabled;

    const toggleBtn = document.getElementById('webSearchToggle');
    const badge = document.getElementById('webSearchBadge');

    if (webSearchEnabled) {
        toggleBtn.textContent = 'Disable';
        toggleBtn.classList.add('active');
        badge.textContent = 'On';
        badge.classList.add('active');
        showToast('🌐 Web Search Enabled', 'Your queries will now search the internet for latest information', 'success');
    } else {
        toggleBtn.textContent = 'Enable';
        toggleBtn.classList.remove('active');
        badge.textContent = 'Off';
        badge.classList.remove('active');
        showToast('🌐 Web Search Disabled', 'Queries will only search your uploaded documents', 'info');
    }
});

// Initialize web search status on page load
async function initWebSearchStatus() {
    try {
        const response = await fetch('/web-search/status');
        const data = await response.json();

        // Web search is disabled by default for each session
        webSearchEnabled = false;

        const toggleBtn = document.getElementById('webSearchToggle');
        const badge = document.getElementById('webSearchBadge');
        const hint = document.querySelector('.web-search-hint');

        if (toggleBtn) {
            toggleBtn.textContent = 'Enable';
            toggleBtn.classList.remove('active');
        }
        if (badge) {
            badge.textContent = 'Off';
            badge.classList.remove('active');
        }

        // Update hint to show current provider
        if (hint && data.provider_name) {
            const providerInfo = data.has_api_key
                ? `✅ Using ${data.provider_name}`
                : `⚠️ Using ${data.provider_name} - Add API key for better results`;
            hint.innerHTML = `💡 ${providerInfo}`;
        }
    } catch (error) {
        console.log('Web search status unavailable');
    }
}

initWebSearchStatus();


// ============================================
// Smart Email/Report Drafter
// ============================================

// Drafter state
let selectedDocumentType = 'email';
let selectedTone = 'professional';
let sourceDocuments = [];
let currentDraft = null;

// Template selector handler
document.querySelectorAll('#templateSelector .template-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active from all
        document.querySelectorAll('#templateSelector .template-btn').forEach(b => b.classList.remove('active'));
        // Add active to clicked
        btn.classList.add('active');
        selectedDocumentType = btn.dataset.type;

        // Show feedback
        showToast(`📄 ${btn.querySelector('.template-name').textContent}`, `Selected document type`, 'info');
    });
});

// Tone selector handler
document.querySelectorAll('#toneSelector .tone-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active from all
        document.querySelectorAll('#toneSelector .tone-btn').forEach(b => b.classList.remove('active'));
        // Add active to clicked
        btn.classList.add('active');
        selectedTone = btn.dataset.tone;
    });
});

// Source document tags
const sourceDocInput = document.getElementById('sourceDocInput');
const sourceTagsContainer = document.getElementById('sourceTagsContainer');

if (sourceDocInput) {
    sourceDocInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const value = sourceDocInput.value.trim();
            if (value && !sourceDocuments.includes(value)) {
                addSourceTag(value);
            }
            sourceDocInput.value = '';
        }
    });
}

function addSourceTag(name) {
    sourceDocuments.push(name);

    const tag = document.createElement('span');
    tag.className = 'source-tag';
    tag.innerHTML = `
        📄 ${name}
        <span class="remove-tag" title="Remove">×</span>
    `;

    tag.querySelector('.remove-tag').addEventListener('click', () => {
        sourceDocuments = sourceDocuments.filter(d => d !== name);
        tag.remove();
    });

    // Insert before the input
    sourceTagsContainer.insertBefore(tag, sourceDocInput);
}

// Drafter toggle (collapse/expand)
const drafterToggle = document.getElementById('drafterToggle');
const drafterContent = document.getElementById('drafterContent');

if (drafterToggle && drafterContent) {
    drafterToggle.addEventListener('click', () => {
        const isExpanded = drafterContent.classList.contains('expanded');

        if (isExpanded) {
            drafterContent.classList.remove('expanded');
            drafterToggle.classList.remove('expanded');
            drafterToggle.querySelector('span:first-child').textContent = 'Show';
        } else {
            drafterContent.classList.add('expanded');
            drafterToggle.classList.add('expanded');
            drafterToggle.querySelector('span:first-child').textContent = 'Hide';
        }
    });
}

// Generate Draft button
document.getElementById('generateDraftBtn')?.addEventListener('click', async () => {
    const communicationGoal = document.getElementById('communicationGoal')?.value.trim();

    if (!communicationGoal) {
        showToast('⚠️ Missing Goal', 'Please describe what you want to communicate', 'warning');
        return;
    }

    await generateDraft();
});

// Generate the draft
async function generateDraft() {
    const btn = document.getElementById('generateDraftBtn');
    const communicationGoal = document.getElementById('communicationGoal')?.value.trim();
    const recipient = document.getElementById('recipientInput')?.value.trim();
    const senderName = document.getElementById('senderInput')?.value.trim();
    const additionalContext = document.getElementById('additionalContext')?.value.trim();

    if (!communicationGoal) {
        showToast('⚠️ Missing Goal', 'Please describe what you want to communicate', 'warning');
        return;
    }

    // Update button to loading state
    btn.disabled = true;
    btn.innerHTML = `
        <span class="loading-spinner"></span>
        <span>Generating...</span>
    `;

    try {
        const requestBody = {
            communication_goal: communicationGoal,
            document_type: selectedDocumentType,
            tone: selectedTone,
            recipient: recipient || null,
            sender_name: senderName || null,
            source_documents: sourceDocuments,
            additional_context: additionalContext || null,
            include_sources: true
        };

        const response = await fetch('/draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate draft');
        }

        const data = await response.json();
        currentDraft = data;

        displayDraft(data);
        showToast('✨ Draft Generated', `${data.document_type} created with ${data.word_count} words`, 'success');

    } catch (error) {
        console.error('Draft generation error:', error);
        showToast('❌ Error', error.message || 'Failed to generate draft', 'error');
    } finally {
        // Reset button
        btn.disabled = false;
        btn.innerHTML = `
            <span class="btn-icon">✨</span>
            <span>Generate Draft</span>
        `;
    }
}

// Display the generated draft
function displayDraft(data) {
    const outputSection = document.getElementById('draftOutputSection');
    const subjectEl = document.getElementById('draftSubject');
    const subjectTextEl = document.getElementById('draftSubjectText');
    const bodyEl = document.getElementById('draftBody');
    const sourcesEl = document.getElementById('draftSources');
    const sourceListEl = document.getElementById('sourceRefList');
    const suggestionsEl = document.getElementById('draftSuggestions');
    const suggestionListEl = document.getElementById('suggestionList');

    // Show output section
    outputSection.style.display = 'block';

    // Handle subject/title
    if (data.subject || data.title) {
        subjectEl.style.display = 'block';
        subjectEl.querySelector('span:first-child').textContent = data.document_type === 'email' ? 'Subject:' : 'Title:';
        subjectTextEl.textContent = data.subject || data.title;
    } else {
        subjectEl.style.display = 'none';
    }

    // Display body
    bodyEl.innerHTML = formatDraftBody(data.body);
    bodyEl.contentEditable = 'false';

    // Display sources
    if (data.sources_used && data.sources_used.length > 0) {
        sourcesEl.style.display = 'block';
        sourceListEl.innerHTML = data.sources_used.map(source => `
            <div class="source-ref-item">
                <span class="source-icon">📄</span>
                <div>
                    <span class="source-file">${source.source_file}</span>
                    ${source.page_reference ? `<span class="source-page">(${source.page_reference})</span>` : ''}
                    <div class="source-preview">${source.content}</div>
                </div>
            </div>
        `).join('');
    } else {
        sourcesEl.style.display = 'none';
    }

    // Display suggestions
    if (data.suggestions && data.suggestions.length > 0) {
        suggestionsEl.style.display = 'block';
        suggestionListEl.innerHTML = data.suggestions.map(s => `
            <div class="suggestion-item">${s}</div>
        `).join('');
    } else {
        suggestionsEl.style.display = 'none';
    }

    // Update stats
    document.getElementById('draftTime').textContent = `${data.processing_time.toFixed(1)}s`;
    document.getElementById('draftWordCount').textContent = data.word_count;
    document.getElementById('draftSourceCount').textContent = data.sources_used?.length || 0;

    // Scroll to output
    outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Format draft body with proper styling
function formatDraftBody(body) {
    // Convert line breaks to proper paragraphs
    let formatted = body
        .replace(/\n\n+/g, '</p><p>')  // Double line breaks = new paragraph
        .replace(/\n/g, '<br>')  // Single line break = br
        .replace(/^/, '<p>')  // Start with paragraph
        .replace(/$/, '</p>');  // End with paragraph

    // Highlight source references
    formatted = formatted.replace(
        /\((?:ref|source|Source):\s*([^)]+)\)/gi,
        '<span style="color: #6366f1; font-size: 0.85em; background: rgba(99, 102, 241, 0.1); padding: 2px 6px; border-radius: 4px;">📚 $1</span>'
    );

    // Style numbered lists
    formatted = formatted.replace(
        /(\d+)\.\s+/g,
        '<strong>$1.</strong> '
    );

    // Style bullet points
    formatted = formatted.replace(
        /^[-•]\s+/gm,
        '• '
    );

    return formatted;
}

// Copy draft to clipboard
document.getElementById('copyDraftBtn')?.addEventListener('click', async () => {
    const bodyEl = document.getElementById('draftBody');
    const subjectEl = document.getElementById('draftSubjectText');

    let textToCopy = '';

    if (subjectEl && subjectEl.textContent) {
        textToCopy += `Subject: ${subjectEl.textContent}\n\n`;
    }

    // Get plain text from HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = bodyEl.innerHTML;
    textToCopy += tempDiv.textContent || tempDiv.innerText;

    try {
        await navigator.clipboard.writeText(textToCopy);
        showToast('📋 Copied', 'Draft copied to clipboard', 'success');
    } catch (error) {
        console.error('Copy failed:', error);
        showToast('❌ Error', 'Failed to copy to clipboard', 'error');
    }
});

// Edit draft toggle
let isEditing = false;
document.getElementById('editDraftBtn')?.addEventListener('click', () => {
    const bodyEl = document.getElementById('draftBody');
    const editBtn = document.getElementById('editDraftBtn');

    isEditing = !isEditing;

    if (isEditing) {
        bodyEl.contentEditable = 'true';
        bodyEl.focus();
        editBtn.innerHTML = '💾 Save';
        editBtn.classList.add('active');
        showToast('✏️ Edit Mode', 'You can now edit the draft directly', 'info');
    } else {
        bodyEl.contentEditable = 'false';
        editBtn.innerHTML = '✏️ Edit';
        editBtn.classList.remove('active');
        showToast('💾 Saved', 'Changes saved', 'success');
    }
});

// Regenerate draft
document.getElementById('regenerateDraftBtn')?.addEventListener('click', async () => {
    const communicationGoal = document.getElementById('communicationGoal')?.value.trim();

    if (!communicationGoal) {
        showToast('⚠️ Missing Goal', 'Please describe what you want to communicate', 'warning');
        return;
    }

    await generateDraft();
});


// ============================================
// Automated Presentation Generator
// ============================================

// Presentation state
let selectedTheme = 'professional';
let presSourceDocuments = [];
let currentPresentation = null;

// Theme selector handler
document.querySelectorAll('#themeSelector .theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active from all
        document.querySelectorAll('#themeSelector .theme-btn').forEach(b => b.classList.remove('active'));
        // Add active to clicked
        btn.classList.add('active');
        selectedTheme = btn.dataset.theme;

        // Show feedback
        showToast(`🎨 ${btn.querySelector('.theme-name').textContent}`, `Theme selected`, 'info');
    });
});

// Source document tags for presentations
const presSourceDocInput = document.getElementById('presSourceDocInput');
const presSourceTagsContainer = document.getElementById('presSourceTagsContainer');

if (presSourceDocInput) {
    presSourceDocInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const value = presSourceDocInput.value.trim();
            if (value && !presSourceDocuments.includes(value)) {
                addPresSourceTag(value);
            }
            presSourceDocInput.value = '';
        }
    });
}

function addPresSourceTag(name) {
    presSourceDocuments.push(name);

    const tag = document.createElement('span');
    tag.className = 'source-tag';
    tag.innerHTML = `
        📄 ${name}
        <span class="remove-tag" title="Remove">×</span>
    `;

    tag.querySelector('.remove-tag').addEventListener('click', () => {
        presSourceDocuments = presSourceDocuments.filter(d => d !== name);
        tag.remove();
    });

    // Insert before the input
    presSourceTagsContainer.insertBefore(tag, presSourceDocInput);
}

// Presentation toggle (collapse/expand)
const presentationToggle = document.getElementById('presentationToggle');
const presentationContent = document.getElementById('presentationContent');

if (presentationToggle && presentationContent) {
    presentationToggle.addEventListener('click', () => {
        const isExpanded = presentationContent.classList.contains('expanded');

        if (isExpanded) {
            presentationContent.classList.remove('expanded');
            presentationToggle.classList.remove('expanded');
            presentationToggle.querySelector('span:first-child').textContent = 'Show';
        } else {
            presentationContent.classList.add('expanded');
            presentationToggle.classList.add('expanded');
            presentationToggle.querySelector('span:first-child').textContent = 'Hide';
        }
    });
}

// Generate Presentation button
document.getElementById('generatePresBtn')?.addEventListener('click', async () => {
    const topic = document.getElementById('presentationTopic')?.value.trim();

    if (!topic) {
        showToast('⚠️ Missing Topic', 'Please enter a presentation topic', 'warning');
        return;
    }

    await generatePresentation();
});

// Generate the presentation
async function generatePresentation() {
    const btn = document.getElementById('generatePresBtn');
    const topic = document.getElementById('presentationTopic')?.value.trim();
    const slideCount = parseInt(document.getElementById('slideCount')?.value) || 5;
    const includeTitleSlide = document.getElementById('includeTitleSlide')?.checked ?? true;
    const includeSummarySlide = document.getElementById('includeSummarySlide')?.checked ?? true;
    const includeSources = document.getElementById('includeSources')?.checked ?? true;
    const instructions = document.getElementById('presInstructions')?.value.trim();

    if (!topic) {
        showToast('⚠️ Missing Topic', 'Please enter a presentation topic', 'warning');
        return;
    }

    // Update button to loading state
    btn.disabled = true;
    btn.innerHTML = `
        <span class="loading-spinner"></span>
        <span>Generating Presentation...</span>
    `;

    try {
        const requestBody = {
            topic: topic,
            source_documents: presSourceDocuments,
            num_slides: slideCount,
            theme: selectedTheme,
            include_title_slide: includeTitleSlide,
            include_summary_slide: includeSummarySlide,
            include_sources: includeSources,
            additional_instructions: instructions || null
        };

        const response = await fetch('/presentation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate presentation');
        }

        const data = await response.json();
        currentPresentation = data;

        displayPresentation(data);
        showToast('📊 Presentation Ready', `${data.num_slides} slides generated!`, 'success');

        // Load previous presentations
        loadPreviousPresentations();

    } catch (error) {
        console.error('Presentation generation error:', error);
        showToast('❌ Error', error.message || 'Failed to generate presentation', 'error');
    } finally {
        // Reset button
        btn.disabled = false;
        btn.innerHTML = `
            <span class="btn-icon">🎬</span>
            <span>Generate Presentation</span>
        `;
    }
}

// Display the generated presentation
function displayPresentation(data) {
    const outputSection = document.getElementById('presOutputSection');
    const slidesPreview = document.getElementById('slidesPreview');
    const fileNameEl = document.getElementById('presFileName');
    const fileMetaEl = document.getElementById('presFileMeta');
    const downloadBtn = document.getElementById('presDownloadBtn');
    const sourcesEl = document.getElementById('presSources');
    const sourcesListEl = document.getElementById('presSourcesList');

    // Show output section
    outputSection.style.display = 'block';

    // Generate slide previews
    slidesPreview.innerHTML = data.slides.map((slide, index) => `
        <div class="slide-preview-card">
            <div class="slide-preview-header">
                Slide ${index + 1}: ${slide.slide_type.replace('_', ' ')}
            </div>
            <div class="slide-preview-content">
                <div class="slide-preview-title">${slide.title}</div>
                ${slide.bullet_points && slide.bullet_points.length > 0 ? `
                    <ul class="slide-preview-bullets">
                        ${slide.bullet_points.slice(0, 3).map(b => `<li>${b.substring(0, 50)}${b.length > 50 ? '...' : ''}</li>`).join('')}
                    </ul>
                ` : ''}
            </div>
        </div>
    `).join('');

    // Update download info
    fileNameEl.textContent = data.filename;
    fileMetaEl.textContent = `${data.num_slides} slides • Generated just now`;
    downloadBtn.href = data.download_url;

    // Update stats
    document.getElementById('presTime').textContent = `${data.processing_time.toFixed(1)}s`;
    document.getElementById('presSlideCount').textContent = data.num_slides;
    document.getElementById('presSourceCount').textContent = data.sources_used?.length || 0;

    // Display sources
    if (data.sources_used && data.sources_used.length > 0) {
        sourcesEl.style.display = 'block';
        sourcesListEl.innerHTML = data.sources_used.map(s =>
            `<span class="pres-source-tag">📄 ${s}</span>`
        ).join('');
    } else {
        sourcesEl.style.display = 'none';
    }

    // Scroll to output
    outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Load previous presentations
async function loadPreviousPresentations() {
    try {
        const response = await fetch('/presentation/list');
        const data = await response.json();

        const container = document.getElementById('previousPresentations');
        const list = document.getElementById('previousList');

        if (data.presentations && data.presentations.length > 0) {
            container.style.display = 'block';

            list.innerHTML = data.presentations.slice(0, 5).map(pres => `
                <div class="previous-item">
                    <div class="previous-item-info">
                        <span class="previous-item-icon">📊</span>
                        <div>
                            <div class="previous-item-name">${pres.filename}</div>
                            <div class="previous-item-meta">
                                ${formatFileSize(pres.size_bytes)} • ${formatDate(pres.created)}
                            </div>
                        </div>
                    </div>
                    <a href="${pres.download_url}" class="previous-item-download" download>
                        ⬇️ Download
                    </a>
                </div>
            `).join('');
        } else {
            container.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to load previous presentations:', error);
    }
}

// Helper: Format file size
function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

// Helper: Format date
function formatDate(isoString) {
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return date.toLocaleDateString();
    } catch {
        return 'Unknown';
    }
}

// Load previous presentations on page load
loadPreviousPresentations();

