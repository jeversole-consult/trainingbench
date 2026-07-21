// API base URL - automatically detect and use current origin
const API_BASE = window.location.origin;

// Global user info
let currentUser = {
    username: null,
    user_type: null
};

// Track if there's a pending rating requirement (for training users)
let pendingRatingRequired = false;

// Monotonic counter so chat-message IDs are unique even when two messages
// are appended in the same millisecond (collisions caused the user bubble
// to be removed in place of the loading placeholder).
let _msgIdCounter = 0;

// Check authentication on load
async function checkAuth() {
    const token = sessionStorage.getItem('session_token');
    if (!token) {
        window.location.href = '/static/gate.html';
        return false;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            sessionStorage.removeItem('session_token');
            localStorage.removeItem('gate_token');
            window.location.href = '/static/gate.html';
            return false;
        }

        // Get user info including user_type
        const data = await response.json();
        currentUser.username = data.username;
        currentUser.user_type = data.user_type;

        console.log('User authenticated:', currentUser);

        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

// Logout function
async function logout() {
    const token = sessionStorage.getItem('session_token');

    // Call backend logout endpoint (optional - mainly for logging/tracking)
    if (token) {
        try {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
        } catch (error) {
            console.error('Logout API call failed:', error);
        }
    }

    // Clear both session and gate tokens
    sessionStorage.removeItem('session_token');
    localStorage.removeItem('gate_token');

    // Clear any stale training session data from localStorage
    localStorage.removeItem('training_session_state');
    localStorage.removeItem('training_session_name');
    localStorage.removeItem('training_session_count');
    localStorage.removeItem('completed_training_sessions');

    // Redirect to passphrase page
    window.location.href = '/static/gate.html';
}

// Apply role-based UI rendering
function applyRoleBasedUI() {
    const userType = currentUser.user_type;

    console.log('Applying role-based UI for user type:', userType);

    // Define which tabs are visible for each user type
    const tabPermissions = {
        'super': ['upload', 'scrape', 'chat', 'powersearch', 'compare', 'search', 'manage', 'history', 'databases'],
        'chat': ['chat'],  // Only Q&A interface
        'training': ['chat', 'history']  // Q&A and history for now
    };

    const allowedTabs = tabPermissions[userType] || [];

    // Hide/show tab buttons
    const allTabs = ['upload', 'scrape', 'chat', 'powersearch', 'compare', 'search', 'manage', 'history', 'databases'];

    allTabs.forEach(tabName => {
        const tabButtons = document.querySelectorAll(`.tab[onclick*="${tabName}"]`);
        tabButtons.forEach(button => {
            if (allowedTabs.includes(tabName)) {
                button.style.display = '';  // Show tab
            } else {
                button.style.display = 'none';  // Hide tab
            }
        });
    });

    // Chat user: Hide distracting elements and simplify interface
    if (userType === 'chat') {
        // Change subtitle to "AI Chat Agent" with larger font
        const headerSubtitle = document.querySelector('header .header-content p');
        if (headerSubtitle) {
            headerSubtitle.textContent = 'AI Chat Agent';
            headerSubtitle.style.fontSize = '1.3em';
            headerSubtitle.style.fontWeight = '500';
        }

        // Hide the entire database statistics section
        const statsSection = document.querySelector('.section[style*="border-bottom"]');
        if (statsSection) {
            statsSection.style.display = 'none';
        }
    } else if (userType === 'training') {
        console.log('🎓 TRAINING USER MODE ACTIVATED');

        // Training user: Change subtitle to "AI Training Agent" with larger font
        const headerSubtitle = document.querySelector('header .header-content p');
        if (headerSubtitle) {
            headerSubtitle.textContent = 'AI Training Agent';
            headerSubtitle.style.fontSize = '1.3em';
            headerSubtitle.style.fontWeight = '500';
        }

        // Hide the entire database statistics section for training users
        const statsSection = document.querySelector('.section[style*="border-bottom"]');
        if (statsSection) {
            statsSection.style.display = 'none';
        }

        // Change "Ask Questions" heading to "Training Question Entry"
        const chatHeading = document.querySelector('#chat-tab h2');
        if (chatHeading && chatHeading.textContent.trim() === 'Ask Questions') {
            chatHeading.textContent = 'Training Question Entry';
        }
        // Rename the tab button itself to "Training" for training users.
        const chatTabBtn = document.querySelector('.tab[onclick*="chat"]');
        if (chatTabBtn) chatTabBtn.textContent = 'Training';

        // Change the subtitle under the heading
        const chatSubtitle = document.querySelector('#chat-tab > div:first-child > div:first-child > p');
        if (chatSubtitle) {
            chatSubtitle.textContent = 'Enter questions and receive Agent-generated answers to evaluate and provide feedback';
        }

        // Hide Clear Screen button for training users
        const clearScreenBtn = document.getElementById('clear-screen-btn');
        if (clearScreenBtn) {
            clearScreenBtn.style.display = 'none';
        }

        // Lock model selector to Llama 3.1 8B for training users
        const changeModelBtn = document.getElementById('change-model-btn');
        if (changeModelBtn) {
            changeModelBtn.disabled = true;
            changeModelBtn.style.cursor = 'not-allowed';
            changeModelBtn.style.opacity = '0.5';
            changeModelBtn.title = 'Admin Privileges Required';
        }

        // Show the training help panel
        const trainingHelpPanel = document.getElementById('training-help-panel');
        if (trainingHelpPanel) {
            trainingHelpPanel.style.display = 'block';
        }

        // Show the training session status panel
        const trainingSessionStatus = document.getElementById('training-session-status');
        if (trainingSessionStatus) {
            trainingSessionStatus.style.display = 'block';
            // Load and display the current session state
            updateTrainingSessionDisplay();
        }

        // Change "Query History" tab to "My Training Sessions"
        const historyTabBtn = document.getElementById('history-tab-btn');
        console.log('📍 History Tab Button Element:', historyTabBtn);
        if (historyTabBtn) {
            console.log('✏️ Changing button text from:', historyTabBtn.textContent);
            historyTabBtn.textContent = 'My Training Sessions';
            console.log('✅ Changed button text to:', historyTabBtn.textContent);
        } else {
            console.error('❌ BUTTON NOT FOUND: history-tab-btn');
        }

        // Also change the heading inside the history tab
        const historyTabHeading = document.getElementById('history-tab-heading');
        if (historyTabHeading) {
            historyTabHeading.textContent = 'My Training Sessions';
        }

        // Hide irrelevant controls for training users
        const historyControls = document.querySelector('.history-controls');
        if (historyControls) {
            historyControls.style.display = 'none';
        }
    } else {
        // Restore original subtitle for super users
        const headerSubtitle = document.querySelector('header .header-content p');
        if (headerSubtitle) {
            headerSubtitle.textContent = 'Upload documents, scrape websites, and search through your knowledge base';
            headerSubtitle.style.fontSize = '';
            headerSubtitle.style.fontWeight = '';
        }

        const statsSection = document.querySelector('.section[style*="border-bottom"]');
        if (statsSection) {
            statsSection.style.display = '';
        }
    }

    // If current active tab is not allowed, switch to first allowed tab
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab && !allowedTabs.some(tab => activeTab.id === `${tab}-tab`)) {
        // Switch to first allowed tab
        const firstAllowedTab = allowedTabs[0];
        if (firstAllowedTab) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(btn => {
                btn.classList.remove('active');
            });

            // Show first allowed tab
            document.getElementById(`${firstAllowedTab}-tab`).classList.add('active');
            const firstTabButton = document.querySelector(`.tab[onclick*="${firstAllowedTab}"]`);
            if (firstTabButton) {
                firstTabButton.classList.add('active');
            }
        }
    }

    // For super users: show all features (default behavior - everything is visible)
    // For chat users: simplified interface (only chat, clean header, no stats)
    // For training users: chat + history (training feedback features will be added later)

    // Enable the question input for super users. The HTML markup ships the
    // input disabled because training users must start a session first.
    // Super users have no session prerequisite, so unlock immediately.
    if (userType === 'super' || userType === 'chat') {
        const qi = document.getElementById('question-input');
        if (qi) {
            qi.disabled = false;
            qi.placeholder = 'Ask a question about the active database...';
        }
        const askBtn = document.getElementById('ask-btn');
        if (askBtn) askBtn.disabled = false;
        const voiceBtn = document.getElementById('voice-input-btn');
        if (voiceBtn) voiceBtn.disabled = false;
    }

    console.log('Role-based UI applied. Allowed tabs:', allowedTabs);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication first
    const isAuthenticated = await checkAuth();
    if (isAuthenticated) {
        // Show logged-in user in header — works on any page that has this element
        const userDisplay = document.getElementById('current-user-display');
        if (userDisplay && currentUser.username) {
            userDisplay.textContent = `Signed in as ${currentUser.username}`;
        }
        const userMgmtBtn = document.getElementById('user-mgmt-btn');
        if (userMgmtBtn && currentUser.user_type === 'super') {
            userMgmtBtn.style.display = 'inline-block';
        }
        // Apply role-based UI after authentication
        applyRoleBasedUI();

        await loadDatabaseSelector();
        refreshStats();
        loadAvailableModels();
        loadModeIndicator();
    }
});

// ============================================================
// SL-003: demo / live mode indicator + super-user toggle
// ============================================================

let pendingModeValue = null;

async function loadModeIndicator() {
    const pill = document.getElementById('mode-pill');
    if (!pill) return;
    try {
        const token = sessionStorage.getItem('session_token');
        const resp = await fetch(`${API_BASE}/settings/mode`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) {
            renderModePillUnknown(`HTTP ${resp.status} from /settings/mode (restart backend?)`);
            return;
        }
        const data = await resp.json();
        renderModePill(data.demo_mode);
    } catch (err) {
        console.error('Failed to load mode:', err);
        renderModePillUnknown(err.message || 'network error');
    }
}

function renderModePillUnknown(reason) {
    const pill = document.getElementById('mode-pill');
    if (!pill) return;
    pill.style.display = 'inline-block';
    pill.textContent = 'MODE: ?';
    pill.style.background = '#6b7280';
    pill.style.color = 'white';
    pill.style.cursor = 'default';
    pill.title = `Could not load current mode: ${reason}`;
    pill.onclick = null;
}

function renderModePill(demoMode) {
    const pill = document.getElementById('mode-pill');
    if (!pill) return;
    pill.style.display = 'inline-block';
    if (demoMode) {
        pill.textContent = 'MODE: DEMO';
        pill.style.background = '#f59e0b';
        pill.style.color = '#1f1f1f';
    } else {
        pill.textContent = 'MODE: LIVE';
        pill.style.background = '#10b981';
        pill.style.color = 'white';
    }
    if (currentUser.user_type === 'super') {
        pill.style.cursor = 'pointer';
        pill.title = 'Click to toggle mode';
        pill.onclick = () => openModeToggleModal(demoMode);
    } else {
        pill.style.cursor = 'default';
        pill.title = demoMode ? 'System is in demo mode (writes disabled)' : 'System is live (writes enabled)';
        pill.onclick = null;
    }
}

function openModeToggleModal(currentlyDemo) {
    pendingModeValue = !currentlyDemo;
    const title = document.getElementById('mode-toggle-title');
    const body = document.getElementById('mode-toggle-body');
    const confirmBtn = document.getElementById('mode-toggle-confirm');
    if (pendingModeValue) {
        title.textContent = 'Switch to Demo mode?';
        body.textContent = 'Ingestion endpoints (scrape, crawl, clear) will be disabled. Other users will see the system is in demo mode.';
        confirmBtn.style.background = '#f59e0b';
    } else {
        title.textContent = 'Switch to Live mode?';
        body.textContent = 'Ingestion endpoints will be enabled. Super users will be able to scrape and modify the database.';
        confirmBtn.style.background = '#10b981';
    }
    document.getElementById('mode-toggle-modal').style.display = 'flex';
}

function closeModeToggleModal() {
    pendingModeValue = null;
    document.getElementById('mode-toggle-modal').style.display = 'none';
}

async function confirmModeToggle() {
    if (pendingModeValue === null) return;
    const newValue = pendingModeValue;
    closeModeToggleModal();
    try {
        const token = sessionStorage.getItem('session_token');
        const resp = await fetch(`${API_BASE}/settings/mode`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ demo_mode: newValue })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert('Failed to switch mode: ' + (err.detail || resp.statusText));
            return;
        }
        const data = await resp.json();
        renderModePill(data.demo_mode);
    } catch (err) {
        console.error('Mode toggle failed:', err);
        alert('Mode toggle failed: ' + err.message);
    }
}

// Load available LLM models
async function loadAvailableModels() {
    // Update model label to show default
    const label = document.getElementById('current-model-label');
    if (label) {
        label.textContent = 'Llama 3.1 8B';
    }

    // Always load active adapter regardless of model loading
    loadActiveAdapter();
}

// Load active adapter version
async function loadActiveAdapter() {
    try {
        const response = await fetch(`${API_BASE}/active-adapter`);
        const data = await response.json();

        if (response.ok && data.adapter) {
            updateAdapterLabel(data.adapter);
        } else {
            updateAdapterLabel('None');
        }
    } catch (error) {
        console.error('Failed to load active adapter:', error);
        updateAdapterLabel('None');
    }
}

// Toggle model selector dropdown visibility
function toggleModelSelector() {
    const selector = document.getElementById('llm-model-selector');
    const btn = document.getElementById('change-model-btn');
    if (selector.style.display === 'none') {
        selector.style.display = '';
        btn.textContent = 'Done';
    } else {
        selector.style.display = 'none';
        btn.textContent = 'Change';
    }
}

// Called when the user picks a model from the dropdown
function updateModelLabel(selector) {
    const label = document.getElementById('current-model-label');
    if (label && selector.options[selector.selectedIndex]) {
        label.textContent = selector.options[selector.selectedIndex].text;
    }
    // Collapse the dropdown after selection
    selector.style.display = 'none';
    const btn = document.getElementById('change-model-btn');
    if (btn) btn.textContent = 'Change';
}

// Scrape website
async function scrapeWebsite() {
    const urlInput = document.getElementById('url-input');
    const maxPages = document.getElementById('max-pages').value || 10;
    const maxDepth = document.getElementById('max-depth').value || 2;
    const statusDiv = document.getElementById('scrape-status');
    const scrapeBtn = document.getElementById('scrape-btn');

    const url = urlInput.value.trim();

    if (!url) {
        showStatus(statusDiv, 'Please enter a URL', 'error');
        return;
    }

    // Validate URL
    try {
        new URL(url);
    } catch (e) {
        showStatus(statusDiv, 'Please enter a valid URL (include http:// or https://)', 'error');
        return;
    }

    scrapeBtn.disabled = true;
    const pagesToScrape = parseInt(maxPages);
    showStatus(statusDiv, `Scraping website... This may take ${Math.ceil(pagesToScrape / 10)} to ${Math.ceil(pagesToScrape / 5)} minutes (${pagesToScrape} pages max, including PDFs).`, 'loading');

    try {
        const response = await fetch(`${API_BASE}/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                max_pages: pagesToScrape,
                max_depth: parseInt(maxDepth)
            })
        });

        const data = await response.json();

        if (response.ok) {
            const pdfCount = data.urls.filter(u => u.toLowerCase().endsWith('.pdf')).length;
            showStatus(statusDiv,
                `Success! Scraped ${data.pages_scraped} pages (${pdfCount} PDFs, ${data.pages_scraped - pdfCount} HTML). You can now ask questions.`,
                'success'
            );
            refreshStats();
        } else {
            showStatus(statusDiv, `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    } finally {
        scrapeBtn.disabled = false;
    }
}

// Ask question
async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const question = questionInput.value.trim();
    const askBtn = document.getElementById('ask-btn');
    const modelSelector = document.getElementById('llm-model-selector');
    const selectedModel = modelSelector ? modelSelector.value : null;

    if (!question) {
        return;
    }

    // For training users, ensure previous response was rated
    if (currentUser.user_type === 'training' && pendingRatingRequired) {
        alert('⚠️ Please rate the previous response before asking another question.\n\nClick either "✓ Acceptable" or "✗ Needs Improvement" on the response above.');
        return;
    }

    // Add user message
    addMessage(question, 'user');
    questionInput.value = '';

    // Show loading
    askBtn.disabled = true;
    const loadingId = addLoadingMessage();

    try {
        const requestBody = {
            question: question,
            k: 6  // Retrieve 6 chunks for more context
        };

        // Add model parameter if a specific model is selected
        if (selectedModel) {
            requestBody.model = selectedModel;
        }

        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${sessionStorage.getItem('session_token')}`
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        // Remove loading message
        removeMessage(loadingId);

        if (response.ok) {
            addMessage(data.answer, 'assistant', data.sources);
        } else {
            addMessage(`Error: ${data.detail}`, 'assistant');
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        askBtn.disabled = false;
    }
}

// Add message to chat
function addMessage(content, sender, sources = null) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${++_msgIdCounter}`;
    messageDiv.id = messageId;
    messageDiv.className = `message ${sender}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    // Preserve line breaks and formatting
    messageContent.style.whiteSpace = 'pre-wrap';
    messageContent.textContent = content;

    // Add speaker button for assistant messages
    if (sender === 'assistant') {
        const voiceBtn = document.createElement('button');
        voiceBtn.className = 'voice-btn';
        voiceBtn.innerHTML = '🔊';
        voiceBtn.title = 'Read aloud';
        voiceBtn.onclick = function() {
            toggleTextToSpeech(content, voiceBtn);
        };
        messageContent.appendChild(voiceBtn);
    }

    messageDiv.appendChild(messageContent);

    // Add sources if available
    if (sources && sources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        sourcesDiv.innerHTML = '<h4>Sources:</h4>';

        sources.forEach((source, index) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            sourceItem.innerHTML = `
                <strong>${index + 1}.</strong>
                <a href="${source.url}" target="_blank">${source.title}</a>
                ${source.relevance_score ? ` (Relevance: ${(source.relevance_score * 100).toFixed(1)}%)` : ''}
            `;
            sourcesDiv.appendChild(sourceItem);
        });

        messageDiv.appendChild(sourcesDiv);
    }

    // Add rating buttons for training users on assistant messages
    if (sender === 'assistant' && currentUser.user_type === 'training') {
        const ratingDiv = document.createElement('div');
        ratingDiv.className = 'rating-buttons';
        ratingDiv.style.cssText = 'margin-top: 15px; display: flex; gap: 10px;';

        const acceptableBtn = document.createElement('button');
        acceptableBtn.textContent = '✓ Acceptable';
        acceptableBtn.style.cssText = 'padding: 8px 20px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9em;';
        acceptableBtn.onclick = function() {
            rateResponse(messageId, 'acceptable', content);
            ratingDiv.style.display = 'none';
        };

        const needsImprovementBtn = document.createElement('button');
        needsImprovementBtn.textContent = '✗ Needs Improvement';
        needsImprovementBtn.style.cssText = 'padding: 8px 20px; background: linear-gradient(135deg, #f44336 0%, #e91e63 100%); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9em;';
        needsImprovementBtn.onclick = function() {
            // Show custom feedback modal
            showFeedbackModal(messageId, content, ratingDiv);
        };

        ratingDiv.appendChild(acceptableBtn);
        ratingDiv.appendChild(needsImprovementBtn);
        messageDiv.appendChild(ratingDiv);

        const ratingHint = document.createElement('div');
        ratingHint.style.cssText = 'margin-top: 8px; font-size: 0.82em; color: #777; font-style: italic;';
        ratingHint.textContent = 'Choose Acceptable or Needs Improvement before continuing. To change a previous entry, re-prompt with a new question.';
        messageDiv.appendChild(ratingHint);

        // Set flag to require rating before next question
        pendingRatingRequired = true;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Rate response (for training users)
async function rateResponse(messageId, rating, content, feedback = null) {
    console.log(`Rating message ${messageId} as ${rating}`);

    try {
        const token = sessionStorage.getItem('session_token');
        const requestBody = {
            message_id: messageId,
            rating: rating,
            content: content
        };

        // Add feedback if provided
        if (feedback) {
            requestBody.feedback = feedback;
        }

        const response = await fetch(`${API_BASE}/rate-response`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            console.log('Rating submitted successfully');

            // Clear the pending rating flag
            pendingRatingRequired = false;

            // Increment training session counter
            incrementTrainingSessionCount();

            // Show brief feedback
            const messageDiv = document.getElementById(messageId);
            if (messageDiv) {
                const feedback = document.createElement('div');
                feedback.style.cssText = 'margin-top: 10px; color: #4CAF50; font-size: 0.9em; font-weight: 500;';
                feedback.textContent = rating === 'acceptable' ? '✓ Marked as acceptable' : '✗ Marked as needs improvement';
                messageDiv.appendChild(feedback);
            }
        } else {
            console.error('Failed to submit rating');
        }
    } catch (error) {
        console.error('Error submitting rating:', error);
    }
}

// Add loading message
function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const id = `msg-${++_msgIdCounter}`;
    messageDiv.id = id;
    messageDiv.className = 'message assistant';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = 'Thinking<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>';

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return id;
}

// Remove message
function removeMessage(id) {
    const message = document.getElementById(id);
    if (message) {
        message.remove();
    }
}

// Refresh stats
async function refreshStats() {
    const statsDisplay = document.getElementById('stats-display');

    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        statsDisplay.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${data.webpage_count.toLocaleString()}</div>
                    <div style="font-size: 0.9em; opacity: 0.9;">Web Pages</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${data.uploaded_count.toLocaleString()}</div>
                    <div style="font-size: 0.9em; opacity: 0.9;">Uploaded Docs</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${data.vector_store.count.toLocaleString()}</div>
                    <div style="font-size: 0.9em; opacity: 0.9;">Document Chunks</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${data.query_logs.total_queries}</div>
                    <div style="font-size: 0.9em; opacity: 0.9;">Total Queries</div>
                </div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2em; font-weight: bold;">${data.query_logs.avg_response_time.toFixed(2)}s</div>
                    <div style="font-size: 0.9em; opacity: 0.9;">Avg Response Time</div>
                </div>
            </div>
        `;
    } catch (error) {
        statsDisplay.innerHTML = `<p style="color: red;">Error loading stats: ${error.message}</p>`;
    }
}

// Clear database
async function clearDatabase() {
    if (!confirm('Are you sure you want to clear all data from the database?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/clear`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            alert('Database cleared successfully');
            refreshStats();
            document.getElementById('chat-messages').innerHTML = '';
        } else {
            alert(`Error: ${data.detail}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Clear chat window
function clearChat() {
    // Context-aware confirmation message based on user type
    let confirmMessage;
    if (currentUser.user_type === 'training') {
        confirmMessage = 'Clear the display?\n\nThis will only remove messages from view. Your rated responses and training data are saved and will not be affected.';
    } else {
        confirmMessage = 'Clear the display?\n\nThis will remove messages from view but will not delete any saved data.';
    }

    if (!confirm(confirmMessage)) {
        return;
    }

    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }
}

// Show status message
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
}

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        askQuestion();
    }
}

// Load query history
async function loadQueryHistory() {
    const historyContainer = document.getElementById('history-container');
    const limit = document.getElementById('history-limit').value;

    // Show loading
    historyContainer.innerHTML = '<p class="history-loading">Loading...</p>';

    // For training users, show training sessions instead of query history
    if (currentUser.user_type === 'training') {
        loadTrainingSessions();
        return;
    }

    try {
        // Fetch both queries and database list in parallel
        let endpoint = `${API_BASE}/logs/recent?n=${limit}`;
        if (limit === 'all') {
            endpoint = `${API_BASE}/logs/all`;
        }

        const token = sessionStorage.getItem('session_token');
        const [queriesResponse, dbResponse] = await Promise.all([
            fetch(endpoint),
            fetch(`${API_BASE}/databases`, {
                headers: {'Authorization': `Bearer ${token}`}
            })
        ]);

        const queriesData = await queriesResponse.json();
        const dbData = await dbResponse.json();

        // Handle both array response and object with queries property
        const queries = Array.isArray(queriesData) ? queriesData : (queriesData.queries || []);

        // Create database ID to name mapping
        const dbMap = {};
        if (dbData.databases) {
            dbData.databases.forEach(db => {
                dbMap[db.id] = db.name;
            });
        }

        if (queriesResponse.ok && queries.length > 0) {
            displayQueryHistory(queries, dbMap);
        } else if (queriesResponse.ok && queries.length === 0) {
            historyContainer.innerHTML = '<p class="history-empty">No query history found. Ask some questions to see them here!</p>';
        } else {
            historyContainer.innerHTML = '<p class="history-error">Error loading history. Please try again.</p>';
        }
    } catch (error) {
        historyContainer.innerHTML = `<p class="history-error">Error: ${error.message}</p>`;
    }
}

// Display query history
function displayQueryHistory(queries, dbMap = {}) {
    const historyContainer = document.getElementById('history-container');
    historyContainer.innerHTML = '';

    queries.forEach((query, index) => {
        const queryCard = document.createElement('div');
        queryCard.className = 'history-item';

        // Format timestamp
        const date = new Date(query.timestamp);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        // Show full answer (no truncation)
        const answerText = query.answer || 'No answer';

        // Get database name from mapping, fallback to ID if not found
        const dbName = query.database_id ? (dbMap[query.database_id] || query.database_id) : '';

        queryCard.innerHTML = `
            <div class="history-header">
                <span class="history-number">#${queries.length - index}</span>
                <span class="history-time">${dateStr}</span>
                <span class="history-response-time">${query.response_time ? query.response_time.toFixed(2) + 's' : 'N/A'}</span>
                ${query.llm_model ? `<span class="history-llm-model">🤖 ${escapeHtml(query.llm_model)}</span>` : ''}
                ${dbName ? `<span class="history-database">🗄️ ${escapeHtml(dbName)}</span>` : ''}
            </div>
            <div class="history-question">
                <strong>Q:</strong> ${escapeHtml(query.question)}
            </div>
            <div class="history-answer">
                <strong>A:</strong> ${escapeHtml(answerText)}
            </div>
            ${query.sources && query.sources.length > 0 ? `
                <div class="history-sources">
                    <strong>Sources:</strong> ${query.sources.length} document(s)
                </div>
            ` : ''}
            ${query.error ? `
                <div class="history-error-msg">
                    <strong>Error:</strong> ${escapeHtml(query.error)}
                </div>
            ` : ''}
        `;

        historyContainer.appendChild(queryCard);
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export history as CSV
async function exportHistory() {
    try {
        const response = await fetch(`${API_BASE}/logs/export`);

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'query_logs.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } else {
            alert('Error exporting history');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Upload document
async function uploadDocument() {
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');

    if (!fileInput.files || fileInput.files.length === 0) {
        uploadStatus.textContent = '⚠️ Please select a file to upload';
        uploadStatus.className = 'status-message error';
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    uploadBtn.disabled = true;
    uploadStatus.textContent = `📤 Uploading ${file.name}...`;
    uploadStatus.className = 'status-message';

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            uploadStatus.textContent = `✅ ${data.message} (${data.chunks_created} chunks created)`;
            uploadStatus.className = 'status-message success';
            fileInput.value = ''; // Clear the file input
            refreshStats(); // Update stats
        } else {
            uploadStatus.textContent = `❌ Error: ${data.detail}`;
            uploadStatus.className = 'status-message error';
        }
    } catch (error) {
        uploadStatus.textContent = `❌ Error: ${error.message}`;
        uploadStatus.className = 'status-message error';
    } finally {
        uploadBtn.disabled = false;
    }
}

// Database Management Functions
async function loadDatabaseSelector() {
    const selector = document.getElementById('database-selector');
    if (!selector) return;

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok && data.databases) {
            selector.innerHTML = '';
            let activeDatabaseName = 'Default Database';

            data.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db.id;
                option.textContent = db.name;
                if (db.is_active) {
                    option.selected = true;
                    activeDatabaseName = db.name;
                }
                selector.appendChild(option);
            });

            // Update the database label in the chat tab
            updateDatabaseLabel(activeDatabaseName);
        }
    } catch (error) {
        console.error('Failed to load databases:', error);
        selector.innerHTML = '<option value="">Error loading databases</option>';
    }
}

// Update the database label display in the chat tab
function updateDatabaseLabel(databaseName) {
    const label = document.getElementById('current-database-label');
    if (label) {
        label.textContent = databaseName || 'Default Database';
    }
}

// Update the adapter label display in the chat tab
function updateAdapterLabel(adapterName) {
    const label = document.getElementById('current-adapter-label');
    if (label) {
        label.textContent = adapterName || 'None';
    }
}

async function switchActiveDatabase() {
    const selector = document.getElementById('database-selector');
    const dbId = selector.value;

    if (!dbId) return;

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ db_id: dbId })
        });

        const data = await response.json();

        if (response.ok) {
            // Update the database label in the chat tab
            updateDatabaseLabel(data.name);

            // Refresh stats to show new database
            refreshStats();

            // Check if we're on the databases tab and refresh the list
            const databasesTab = document.getElementById('databases-tab');
            if (databasesTab && databasesTab.classList.contains('active')) {
                await loadDatabases();
            }

            alert(`Switched to database: ${data.name}`);
        } else {
            alert(`Error switching database: ${data.detail}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function loadDatabases() {
    const loader = document.getElementById('databases-loader');
    const listDiv = document.getElementById('databases-list');

    loader.style.display = 'block';
    listDiv.innerHTML = '';

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            // Show the actual error instead of "No databases found"
            listDiv.innerHTML = `<p style="color: red;">Error loading databases: ${data.detail || 'Authentication failed'}</p>
                                 <p>Try refreshing the page or logging in again.</p>`;
            return;
        }

        if (data.databases && data.databases.length > 0) {
            data.databases.forEach(db => {
                const dbCard = document.createElement('div');
                dbCard.className = 'document-item';
                dbCard.style.borderLeft = db.is_active ? '4px solid #4CAF50' : '4px solid #667eea';

                dbCard.innerHTML = `
                    <div class="document-info">
                        <strong>${escapeHtml(db.name)}</strong>
                        ${db.is_active ? ' <span style="color: #4CAF50; font-weight: bold;">● ACTIVE</span>' : ''}
                        ${db.is_default ? ' <span style="color: #667eea;">[Default]</span>' : ''}
                        <small>
                            ID: ${escapeHtml(db.id)} |
                            Web Pages: ${db.webpage_count || 0} |
                            Uploaded Docs: ${db.uploaded_count || 0} |
                            Chunks: ${db.chunk_count} |
                            ${db.description ? escapeHtml(db.description) : 'No description'}
                        </small>
                    </div>
                    <div class="document-actions">
                        ${!db.is_active ? `<button onclick="switchToDatabaseFromList('${escapeHtml(db.id)}')" style="background: #4CAF50;">Switch To</button>` : ''}
                        <button onclick="duplicateDatabase('${escapeHtml(db.id)}', '${escapeHtml(db.name)}')" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">Duplicate</button>
                        ${!db.is_default ? `<button class="delete-btn" onclick="deleteDatabase('${escapeHtml(db.id)}')">Delete</button>` : ''}
                    </div>
                `;
                listDiv.appendChild(dbCard);
            });
        } else {
            listDiv.innerHTML = '<p>No databases found.</p>';
        }
    } catch (error) {
        listDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    } finally {
        loader.style.display = 'none';
    }
}

async function createNewDatabase() {
    const dbId = document.getElementById('new-db-id').value.trim();
    const dbName = document.getElementById('new-db-name').value.trim();
    const dbDescription = document.getElementById('new-db-description').value.trim();
    const statusDiv = document.getElementById('database-status');

    if (!dbId || !dbName) {
        showStatus(statusDiv, 'Please provide both Database ID and Name', 'error');
        return;
    }

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                db_id: dbId,
                name: dbName,
                description: dbDescription,
                set_as_default: false
            })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(statusDiv, `Database "${dbName}" created successfully!`, 'success');
            document.getElementById('new-db-id').value = '';
            document.getElementById('new-db-name').value = '';
            document.getElementById('new-db-description').value = '';
            loadDatabases();
            loadDatabaseSelector();
        } else {
            showStatus(statusDiv, `Error: ${data.detail || data.error}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    }
}

async function switchToDatabaseFromList(dbId) {
    const statusDiv = document.getElementById('database-status');

    try {
        const token = sessionStorage.getItem('session_token');
        console.log('Switching to database:', dbId);

        const response = await fetch(`${API_BASE}/databases/switch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ db_id: dbId })
        });

        const data = await response.json();
        console.log('Switch response:', data);

        if (response.ok) {
            showStatus(statusDiv, `Switched to database: ${data.name}`, 'success');
            console.log('Reloading database list...');
            // Await the database list reload to ensure the UI updates
            await loadDatabases();
            await loadDatabaseSelector();
            refreshStats();
            console.log('Database list reloaded');
        } else {
            showStatus(statusDiv, `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    }
}

async function deleteDatabase(dbId) {
    if (!confirm(`Are you sure you want to delete this database?\n\nThis will remove the configuration but NOT delete the actual database files.`)) {
        return;
    }

    const statusDiv = document.getElementById('database-status');

    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases/${encodeURIComponent(dbId)}?delete_files=false`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(statusDiv, 'Database configuration deleted successfully', 'success');
            loadDatabases();
            loadDatabaseSelector();
        } else {
            showStatus(statusDiv, `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    }
}

async function duplicateDatabase(sourceDbId, sourceName) {
    // Prompt for new database details
    const newDbId = prompt(`Enter ID for the duplicated database:\n(Duplicating: ${sourceName})`);
    if (!newDbId || !newDbId.trim()) {
        return; // User cancelled
    }

    const newDbName = prompt(`Enter name for the duplicated database:`, `Copy of ${sourceName}`);
    if (!newDbName || !newDbName.trim()) {
        return; // User cancelled
    }

    const newDescription = prompt(`Enter description (optional):`, `Duplicate of ${sourceName}`);

    const statusDiv = document.getElementById('database-status');
    const loader = document.getElementById('databases-loader');

    try {
        loader.style.display = 'block';
        showStatus(statusDiv, 'Duplicating database... This may take a moment depending on database size.', 'loading');

        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/databases/duplicate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                source_db_id: sourceDbId,
                new_db_id: newDbId.trim(),
                new_name: newDbName.trim(),
                description: newDescription || ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(statusDiv, `Database "${newDbName}" duplicated successfully!`, 'success');
            loadDatabases();
            loadDatabaseSelector();
        } else {
            showStatus(statusDiv, `Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    } finally {
        loader.style.display = 'none';
    }
}

// Comparison functionality
let comparisonData = null;

async function loadCompareOptions() {
    try {
        const token = sessionStorage.getItem('session_token');
        console.log('Loading compare options...');

        // Load databases
        const dbResponse = await fetch(`${API_BASE}/databases`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        const dbData = await dbResponse.json();
        console.log('Database data:', dbData);

        // Load models
        const modelResponse = await fetch(`${API_BASE}/models`);
        const modelData = await modelResponse.json();
        console.log('Model data:', modelData);

        // Populate database dropdowns
        const db1 = document.getElementById('compare-db-1');
        const db2 = document.getElementById('compare-db-2');

        if (!db1 || !db2) {
            console.error('Database dropdown elements not found!');
            return;
        }

        db1.innerHTML = '<option value="">Select database...</option>';
        db2.innerHTML = '<option value="">Select database...</option>';

        if (dbData.databases) {
            console.log(`Populating ${dbData.databases.length} databases`);
            dbData.databases.forEach(db => {
                const option1 = document.createElement('option');
                option1.value = db.id;
                option1.textContent = `${db.name} (${db.document_count} docs)`;
                db1.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = db.id;
                option2.textContent = `${db.name} (${db.document_count} docs)`;
                db2.appendChild(option2);
            });
        } else {
            console.error('No databases found in response');
        }

        // Populate model dropdowns
        const model1 = document.getElementById('compare-model-1');
        const model2 = document.getElementById('compare-model-2');

        model1.innerHTML = '<option value="">Default Model (llama3.1:8b)</option>';
        model2.innerHTML = '<option value="">Default Model (llama3.1:8b)</option>';

        if (modelData.models) {
            modelData.models.forEach(model => {
                const option1 = document.createElement('option');
                option1.value = model.name;
                option1.textContent = model.display_name || model.name;
                model1.appendChild(option1);

                const option2 = document.createElement('option');
                option2.value = model.name;
                option2.textContent = model.display_name || model.name;
                model2.appendChild(option2);
            });
        }
    } catch (error) {
        console.error('Failed to load comparison options:', error);
    }
}

async function runComparison() {
    const question = document.getElementById('compare-question').value.trim();
    const db1 = document.getElementById('compare-db-1').value;
    const model1 = document.getElementById('compare-model-1').value;
    const label1 = document.getElementById('compare-label-1').value.trim();
    const db2 = document.getElementById('compare-db-2').value;
    const model2 = document.getElementById('compare-model-2').value;
    const label2 = document.getElementById('compare-label-2').value.trim();

    const statusDiv = document.getElementById('compare-status');
    const loader = document.getElementById('compare-loader');

    // Validation
    if (!question) {
        showStatus(statusDiv, 'Please enter a research question', 'error');
        return;
    }
    if (!db1 || !db2) {
        showStatus(statusDiv, 'Please select databases for both configurations', 'error');
        return;
    }
    if (!label1 || !label2) {
        showStatus(statusDiv, 'Please provide labels for both configurations', 'error');
        return;
    }

    loader.style.display = 'block';
    document.getElementById('compare-results').style.display = 'none';

    // Start elapsed timer
    const startTime = Date.now();
    let timerInterval = setInterval(() => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        showStatus(statusDiv, `Running comparison... ${elapsed}s elapsed`, 'loading');
    }, 100);

    try {
        const token = sessionStorage.getItem('session_token');

        // Run Query 1
        showStatus(statusDiv, `Query 1/2: Switching to database "${label1}"... 0.0s elapsed`, 'loading');
        const query1Start = Date.now();
        const result1 = await queryWithConfig(question, db1, model1, token, (msg) => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            showStatus(statusDiv, `Query 1/2: ${msg} ${elapsed}s elapsed`, 'loading');
        });
        const query1Time = ((Date.now() - query1Start) / 1000).toFixed(2);

        // Run Query 2
        const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        showStatus(statusDiv, `Query 2/2: Switching to database "${label2}"... ${totalElapsed}s elapsed`, 'loading');
        const query2Start = Date.now();
        const result2 = await queryWithConfig(question, db2, model2, token, (msg) => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            showStatus(statusDiv, `Query 2/2: ${msg} ${elapsed}s elapsed`, 'loading');
        });
        const query2Time = ((Date.now() - query2Start) / 1000).toFixed(2);

        const totalTime = ((Date.now() - startTime) / 1000).toFixed(2);

        // Store comparison data with timing info
        comparisonData = {
            question,
            timestamp: new Date().toISOString(),
            config1: {database: db1, model: model1 || 'llama3.1:8b', label: label1, responseTime: query1Time},
            config2: {database: db2, model: model2 || 'llama3.1:8b', label: label2, responseTime: query2Time},
            result1,
            result2,
            totalTime
        };

        // Display results
        displayComparisonResults();

        showStatus(statusDiv, `Comparison completed in ${totalTime}s (Query 1: ${query1Time}s, Query 2: ${query2Time}s)`, 'success');
        document.getElementById('export-compare-btn').disabled = false;

    } catch (error) {
        showStatus(statusDiv, `Error: ${error.message}`, 'error');
    } finally {
        clearInterval(timerInterval);
        loader.style.display = 'none';
    }
}

async function queryWithConfig(question, dbId, model, token, progressCallback) {
    // Switch to the specified database
    if (progressCallback) progressCallback('Switching database...');

    const switchResponse = await fetch(`${API_BASE}/databases/switch`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ db_id: dbId })
    });

    if (!switchResponse.ok) {
        const switchError = await switchResponse.json();
        throw new Error(`Failed to switch database: ${switchError.detail || switchResponse.statusText}`);
    }

    // Run the query
    if (progressCallback) progressCallback('Running query...');

    const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            question: question,
            k: 6,
            model: model || null
        })
    });

    if (!response.ok) {
        let errorMessage = response.statusText;
        try {
            const queryError = await response.json();
            errorMessage = queryError.detail || response.statusText;
        } catch (e) {
            // Response wasn't JSON, use status text
            errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(`Query failed: ${errorMessage}`);
    }

    if (progressCallback) progressCallback('Processing response...');

    try {
        return await response.json();
    } catch (e) {
        throw new Error(`Invalid JSON response from server: ${e.message}`);
    }
}

function displayComparisonResults() {
    try {
        const resultsDiv = document.getElementById('compare-results');
        if (!resultsDiv) {
            throw new Error('Results container not found');
        }
        resultsDiv.style.display = 'block';

        // Display labels
        const label1Elem = document.getElementById('result-label-1');
        const label2Elem = document.getElementById('result-label-2');
        if (!label1Elem || !label2Elem) {
            throw new Error('Label elements not found');
        }
        label1Elem.textContent = comparisonData.config1.label;
        label2Elem.textContent = comparisonData.config2.label;

        // Display response times
        const time1Elem = document.getElementById('result-time-1');
        const time2Elem = document.getElementById('result-time-2');
        if (time1Elem && time2Elem) {
            time1Elem.textContent = `⏱️ Response time: ${comparisonData.config1.responseTime}s | Model: ${comparisonData.config1.model}`;
            time2Elem.textContent = `⏱️ Response time: ${comparisonData.config2.responseTime}s | Model: ${comparisonData.config2.model}`;
        }

        // Display answers
        const content1Elem = document.getElementById('result-content-1');
        const content2Elem = document.getElementById('result-content-2');
        if (!content1Elem || !content2Elem) {
            throw new Error('Content elements not found');
        }
        content1Elem.textContent = comparisonData.result1.answer || 'No answer provided';
        content2Elem.textContent = comparisonData.result2.answer || 'No answer provided';

    // Display sources with content
    const sources1 = comparisonData.result1.sources || [];
    const sources2 = comparisonData.result2.sources || [];

    // Format sources for Result 1
    if (sources1.length > 0) {
        let sourcesHTML = '<div style="margin-top: 20px;"><strong>Sources:</strong></div>';
        sourcesHTML += '<div style="margin-top: 10px;">';
        sources1.forEach((source, index) => {
            const displayTitle = (source.title && source.title !== 'Unknown') ? source.title : (source.url || 'Unknown Source');
            const isWebUrl = source.url && (source.url.startsWith('http://') || source.url.startsWith('https://'));

            if (isWebUrl) {
                sourcesHTML += `
                    <div style="margin: 5px 0;">
                        ${index + 1}. <a href="${escapeHtml(source.url)}" target="_blank" style="color: #667eea;">${escapeHtml(displayTitle)}</a>
                        ${source.relevance_score ? ` <span style="color: #666; font-size: 0.9em;">(${(source.relevance_score * 100).toFixed(1)}%)</span>` : ''}
                    </div>
                `;
            } else {
                sourcesHTML += `
                    <div style="margin: 5px 0;">
                        ${index + 1}. <span style="color: #667eea;">${escapeHtml(displayTitle)}</span>
                        ${source.relevance_score ? ` <span style="color: #666; font-size: 0.9em;">(${(source.relevance_score * 100).toFixed(1)}%)</span>` : ''}
                    </div>
                `;
            }
        });
        sourcesHTML += '</div>';
        document.getElementById('result-sources-1').innerHTML = sourcesHTML;
    } else {
        document.getElementById('result-sources-1').innerHTML = '<div style="margin-top: 20px;"><strong>Sources:</strong> No sources</div>';
    }

    // Format sources for Result 2
    if (sources2.length > 0) {
        let sourcesHTML = '<div style="margin-top: 20px;"><strong>Sources:</strong></div>';
        sourcesHTML += '<div style="margin-top: 10px;">';
        sources2.forEach((source, index) => {
            const displayTitle = (source.title && source.title !== 'Unknown') ? source.title : (source.url || 'Unknown Source');
            const isWebUrl = source.url && (source.url.startsWith('http://') || source.url.startsWith('https://'));

            if (isWebUrl) {
                sourcesHTML += `
                    <div style="margin: 5px 0;">
                        ${index + 1}. <a href="${escapeHtml(source.url)}" target="_blank" style="color: #764ba2;">${escapeHtml(displayTitle)}</a>
                        ${source.relevance_score ? ` <span style="color: #666; font-size: 0.9em;">(${(source.relevance_score * 100).toFixed(1)}%)</span>` : ''}
                    </div>
                `;
            } else {
                sourcesHTML += `
                    <div style="margin: 5px 0;">
                        ${index + 1}. <span style="color: #764ba2;">${escapeHtml(displayTitle)}</span>
                        ${source.relevance_score ? ` <span style="color: #666; font-size: 0.9em;">(${(source.relevance_score * 100).toFixed(1)}%)</span>` : ''}
                    </div>
                `;
            }
        });
        sourcesHTML += '</div>';
        document.getElementById('result-sources-2').innerHTML = sourcesHTML;
    } else {
        document.getElementById('result-sources-2').innerHTML = '<div style="margin-top: 20px;"><strong>Sources:</strong> No sources</div>';
    }

        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        console.error('Error displaying comparison results:', error);
        alert(`Failed to display comparison results: ${error.message}`);
    }
}

function exportComparison() {
    if (!comparisonData) {
        alert('No comparison data to export');
        return;
    }

    const timestamp = new Date(comparisonData.timestamp).toLocaleString();
    const filename = `comparison_${Date.now()}.md`;

    // Create Markdown content
    const markdown = `# RAG Comparison Results

**Date:** ${timestamp}

---

## Research Question

${comparisonData.question}

---

## Configuration A: ${comparisonData.config1.label}

- **Database:** ${comparisonData.config1.database}
- **Model:** ${comparisonData.config1.model}

### Answer

${comparisonData.result1.answer}

### Sources

${comparisonData.result1.sources && comparisonData.result1.sources.length > 0
    ? comparisonData.result1.sources.map((s, i) => `${i + 1}. ${s.title || s.url || 'Unknown source'}`).join('\n')
    : 'No sources'}

---

## Configuration B: ${comparisonData.config2.label}

- **Database:** ${comparisonData.config2.database}
- **Model:** ${comparisonData.config2.model}

### Answer

${comparisonData.result2.answer}

### Sources

${comparisonData.result2.sources && comparisonData.result2.sources.length > 0
    ? comparisonData.result2.sources.map((s, i) => `${i + 1}. ${s.title || s.url || 'Unknown source'}`).join('\n')
    : 'No sources'}

---

*Generated by TrainingBench RAG Comparison Tool*
`;

    // Create download link
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    a.remove();

    alert(`Comparison exported as ${filename}`);
}

// Voice Interface Functions
let recognition = null;
let isListening = false;
let speechSynthesis = window.speechSynthesis;
let currentUtterance = null;

// Initialize speech recognition if available
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = function() {
            isListening = true;
            const voiceBtn = document.getElementById('voice-input-btn');
            const micIcon = document.getElementById('mic-icon');
            voiceBtn.classList.add('listening');
            micIcon.textContent = '🎙️';
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            const questionInput = document.getElementById('question-input');
            questionInput.value = transcript;
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            const voiceBtn = document.getElementById('voice-input-btn');
            const micIcon = document.getElementById('mic-icon');
            voiceBtn.classList.remove('listening');
            micIcon.textContent = '🎤';
            isListening = false;

            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access in your browser settings.');
            }
        };

        recognition.onend = function() {
            isListening = false;
            const voiceBtn = document.getElementById('voice-input-btn');
            const micIcon = document.getElementById('mic-icon');
            voiceBtn.classList.remove('listening');
            micIcon.textContent = '🎤';
        };

        return true;
    }
    return false;
}

// Toggle voice input
function toggleVoiceInput() {
    if (!recognition) {
        const initialized = initSpeechRecognition();
        if (!initialized) {
            alert('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
            return;
        }
    }

    if (isListening) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch (error) {
            console.error('Error starting speech recognition:', error);
        }
    }
}


// Toggle text-to-speech
function toggleTextToSpeech(text, button) {
    // Stop any currently playing speech
    if (speechSynthesis.speaking) {
        speechSynthesis.cancel();

        // Remove speaking class from all voice buttons
        document.querySelectorAll('.voice-btn').forEach(btn => {
            btn.classList.remove('speaking');
            btn.innerHTML = '🔊';
        });

        // If clicking the same button that was speaking, just stop
        if (currentUtterance && button.classList.contains('speaking')) {
            currentUtterance = null;
            return;
        }
    }

    // Start new speech
    currentUtterance = new SpeechSynthesisUtterance(text);

    // Configure voice settings
    currentUtterance.rate = 1.0;
    currentUtterance.pitch = 1.0;
    currentUtterance.volume = 1.0;

    // Add event listeners
    currentUtterance.onstart = function() {
        button.classList.add('speaking');
        button.innerHTML = '🔇';
    };

    currentUtterance.onend = function() {
        button.classList.remove('speaking');
        button.innerHTML = '🔊';
        currentUtterance = null;
    };

    currentUtterance.onerror = function(event) {
        console.error('Speech synthesis error:', event);
        button.classList.remove('speaking');
        button.innerHTML = '🔊';
        currentUtterance = null;
    };

    speechSynthesis.speak(currentUtterance);
}

// Initialize speech recognition on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize speech recognition (lazy - will init on first use)
    // This allows the user to grant permission when they first click the mic button
});

// Feedback Modal Functions
let feedbackContext = {
    messageId: null,
    content: null,
    ratingDiv: null
};

function showFeedbackModal(messageId, content, ratingDiv) {
    feedbackContext.messageId = messageId;
    feedbackContext.content = content;
    feedbackContext.ratingDiv = ratingDiv;

    const modal = document.getElementById('feedback-modal');
    const textarea = document.getElementById('feedback-text');

    modal.style.display = 'flex';
    textarea.value = '';
    textarea.focus();
}

function cancelFeedback() {
    const modal = document.getElementById('feedback-modal');
    modal.style.display = 'none';
    feedbackContext = { messageId: null, content: null, ratingDiv: null };
}

function submitFeedback() {
    const textarea = document.getElementById('feedback-text');
    const feedback = textarea.value.trim();

    if (!feedback) {
        alert('Please enter feedback before submitting.');
        return;
    }

    // Clear the pending rating flag (will be set again by rateResponse if successful)
    pendingRatingRequired = false;

    // Submit the rating with feedback
    rateResponse(
        feedbackContext.messageId,
        'needs_improvement',
        feedbackContext.content,
        feedback
    );

    // Hide the rating buttons
    if (feedbackContext.ratingDiv) {
        feedbackContext.ratingDiv.style.display = 'none';
    }

    // Close the modal
    cancelFeedback();
}

// Training Help Modal Functions
function openTrainingHelpModal() {
    const modal = document.getElementById('training-help-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeTrainingHelpModal() {
    const modal = document.getElementById('training-help-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Workflow Modal Functions
function openWorkflowModal() {
    const modal = document.getElementById('workflow-modal');
    if (modal) {
        // Populate dynamic database name
        const dbSelector = document.getElementById('database-selector');
        const dbNameSpan = document.getElementById('workflow-db-name');
        if (dbSelector && dbNameSpan) {
            const selectedOption = dbSelector.options[dbSelector.selectedIndex];
            dbNameSpan.textContent = selectedOption ? selectedOption.text : 'Default Database';
        }

        // Populate dynamic model name
        const modelLabel = document.getElementById('current-model-label');
        const llmNameSpan = document.getElementById('workflow-llm-name');
        if (modelLabel && llmNameSpan) {
            llmNameSpan.textContent = modelLabel.textContent;
        }

        modal.style.display = 'flex';
    }
}

function closeWorkflowModal() {
    const modal = document.getElementById('workflow-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    const trainingModal = document.getElementById('training-help-modal');
    const feedbackModal = document.getElementById('feedback-modal');
    const workflowModal = document.getElementById('workflow-modal');

    if (event.target === trainingModal) {
        closeTrainingHelpModal();
    }
    if (event.target === feedbackModal) {
        cancelFeedback();
    }
    if (event.target === workflowModal) {
        closeWorkflowModal();
    }
};

// Training Session Management Functions

// In-memory cache for training session (loaded from server)
let trainingSessionCache = {
    active_session: null,
    completed_sessions: []
};

// Load training session from server
async function loadTrainingSession() {
    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/training/session`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            trainingSessionCache = data;
            return data;
        }
    } catch (error) {
        console.error('Error loading training session:', error);
    }
    return { active_session: null, completed_sessions: [] };
}

// Save training session to server
async function saveTrainingSession(sessionName, sessionState, recordCount) {
    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/training/session`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                session_name: sessionName,
                session_state: sessionState,
                record_count: recordCount
            })
        });

        if (response.ok) {
            // Update local cache
            trainingSessionCache.active_session = {
                session_name: sessionName,
                session_state: sessionState,
                record_count: recordCount
            };
            return true;
        }
    } catch (error) {
        console.error('Error saving training session:', error);
    }
    return false;
}

// Complete training session on server
async function completeTrainingSessionOnServer(sessionName, recordCount) {
    try {
        const token = sessionStorage.getItem('session_token');
        const response = await fetch(`${API_BASE}/training/session/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                session_name: sessionName,
                session_state: 'completed',
                record_count: recordCount
            })
        });

        if (response.ok) {
            const data = await response.json();
            // Update local cache
            trainingSessionCache.active_session = null;
            trainingSessionCache.completed_sessions.push(data.completed_session);
            return true;
        }
    } catch (error) {
        console.error('Error completing training session:', error);
    }
    return false;
}

// Session state: 'not_started', 'active', 'completed'
function getTrainingSessionState() {
    if (trainingSessionCache.active_session) {
        return trainingSessionCache.active_session.session_state || 'not_started';
    }
    return 'not_started';
}

async function setTrainingSessionState(state) {
    const sessionName = getTrainingSessionName();
    const recordCount = getTrainingSessionCount();
    await saveTrainingSession(sessionName, state, recordCount);
    await updateTrainingSessionDisplay();
}

function getTrainingSessionName() {
    if (trainingSessionCache.active_session) {
        return trainingSessionCache.active_session.session_name || 'Untitled Session';
    }
    return 'Untitled Session';
}

async function setTrainingSessionName(name) {
    const state = getTrainingSessionState();
    const count = getTrainingSessionCount();
    await saveTrainingSession(name, state, count);
    await updateTrainingSessionDisplay();
}

function getTrainingSessionCount() {
    if (trainingSessionCache.active_session) {
        return trainingSessionCache.active_session.record_count || 0;
    }
    return 0;
}

async function setTrainingSessionCount(count) {
    const name = getTrainingSessionName();
    const state = getTrainingSessionState();
    await saveTrainingSession(name, state, count);
    await updateTrainingSessionDisplay();
}

async function incrementTrainingSessionCount() {
    const currentCount = getTrainingSessionCount();
    await setTrainingSessionCount(currentCount + 1);
}

async function updateTrainingSessionDisplay() {
    // Load session from server on first call or when needed
    if (currentUser.user_type === 'training' && !trainingSessionCache.active_session && getTrainingSessionState() === 'not_started') {
        await loadTrainingSession();
    }

    const state = getTrainingSessionState();
    const notStartedDiv = document.getElementById('session-not-started');
    const activeDiv = document.getElementById('session-active');
    const countElement = document.getElementById('session-record-count');
    const nameElement = document.getElementById('session-name');

    // Hide both initially
    if (notStartedDiv) notStartedDiv.style.display = 'none';
    if (activeDiv) activeDiv.style.display = 'none';

    if (state === 'not_started') {
        if (notStartedDiv) notStartedDiv.style.display = 'block';
        // Disable input controls when no session is active
        if (currentUser.user_type === 'training') {
            disableTrainingInput();
        }
    } else if (state === 'active') {
        if (activeDiv) activeDiv.style.display = 'block';
        if (nameElement) nameElement.textContent = getTrainingSessionName();
        if (countElement) countElement.textContent = getTrainingSessionCount();
        // Enable input controls when session is active
        if (currentUser.user_type === 'training') {
            enableTrainingInput();
        }
    }
}

// Enable training input controls
function enableTrainingInput() {
    const questionInput = document.getElementById('question-input');
    const voiceBtn = document.getElementById('voice-input-btn');
    const askBtn = document.getElementById('ask-btn');

    if (questionInput) {
        questionInput.disabled = false;
        questionInput.placeholder = 'Ask a question about the scraped content...';
    }
    if (voiceBtn) {
        voiceBtn.disabled = false;
    }
    if (askBtn) {
        askBtn.disabled = false;
    }
}

// Disable training input controls
function disableTrainingInput() {
    const questionInput = document.getElementById('question-input');
    const voiceBtn = document.getElementById('voice-input-btn');
    const askBtn = document.getElementById('ask-btn');

    if (questionInput) {
        questionInput.disabled = true;
        questionInput.placeholder = 'Start a training session above to begin entering prompts...';
    }
    if (voiceBtn) {
        voiceBtn.disabled = true;
    }
    if (askBtn) {
        askBtn.disabled = true;
    }
}

async function startNewTrainingSession() {
    // Generate default name with timestamp
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD
    const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, ''); // HHMMSS
    const defaultName = `Training_${dateStr}_${timeStr}`;

    // Prompt user for training set name
    const sessionName = prompt(
        'Enter a name for this training set:\n\n(This will help you identify it later when reviewing training data)',
        defaultName
    );

    if (!sessionName || !sessionName.trim()) {
        // User cancelled or entered empty name
        return;
    }

    // Initialize new session
    await setTrainingSessionName(sessionName.trim());
    await setTrainingSessionCount(0);
    await setTrainingSessionState('active');

    // Clear the chat display
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    // Show feedback
    alert(`Training session started!\n\nSet Name: ${sessionName.trim()}\n\nYou can now start asking questions and rating responses.`);
}

async function completeTrainingSession() {
    const count = getTrainingSessionCount();
    const sessionName = getTrainingSessionName();

    if (count === 0) {
        if (!confirm('You haven\'t rated any responses yet.\n\nAre you sure you want to complete this session with 0 training records?')) {
            return;
        }
    }

    if (confirm(`Complete training session?\n\nSet Name: ${sessionName}\nRecords Created: ${count}\n\nThis will finalize the training set. You can start a new session afterward.`)) {
        // Complete the session on the server
        const success = await completeTrainingSessionOnServer(sessionName, count);

        if (success) {
            alert(`Training session completed!\n\n${count} training records have been saved.\n\nYou can now start a new training session.`);
            // The cache is already updated by completeTrainingSessionOnServer
            await updateTrainingSessionDisplay();
        } else {
            alert('Error completing training session. Please try again.');
        }
    }
}

async function cancelTrainingSession() {
    const count = getTrainingSessionCount();
    const sessionName = getTrainingSessionName();

    if (confirm(`Cancel this training session?\n\nSet Name: ${sessionName}\nRecords Created: ${count}\n\nWARNING: All ${count} training records from this session will be discarded.`)) {
        // Clear the active session on server
        trainingSessionCache.active_session = null;
        await setTrainingSessionState('not_started');

        // Clear the chat display
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }

        alert('Training session cancelled.');
    }
}

// Load training sessions for training users
async function loadTrainingSessions() {
    const historyContainer = document.getElementById('history-container');

    // Load session data from server
    await loadTrainingSession();

    // Clear container and build training sessions view
    historyContainer.innerHTML = '';

    // Header section
    const headerDiv = document.createElement('div');
    headerDiv.style.cssText = 'margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px;';
    headerDiv.innerHTML = `
        <h3 style="margin: 0 0 5px 0; font-size: 1.2em;">📚 My Training Sessions</h3>
        <p style="margin: 0; font-size: 0.9em; opacity: 0.9;">Track your training progress and review completed sessions</p>
    `;
    historyContainer.appendChild(headerDiv);

    // Current session status
    const state = getTrainingSessionState();
    const currentSessionDiv = document.createElement('div');
    currentSessionDiv.style.cssText = 'margin-bottom: 20px; padding: 15px; background: white; border: 2px solid #11998e; border-radius: 8px;';

    if (state === 'active') {
        const sessionName = getTrainingSessionName();
        const recordCount = getTrainingSessionCount();

        currentSessionDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span style="font-size: 1.5em;">⚡</span>
                <div style="flex: 1;">
                    <div style="font-size: 1.1em; font-weight: bold; color: #11998e;">Active Training Session</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 3px;">Currently in progress</div>
                </div>
            </div>
            <div style="background: #f5f5f5; padding: 12px; border-radius: 5px; margin-top: 10px;">
                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Session Name:</div>
                <div style="font-size: 1em; font-weight: 500; color: #333; margin-bottom: 10px;">${escapeHtml(sessionName)}</div>
                <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">Training Records:</div>
                <div style="font-size: 1.3em; font-weight: bold; color: #11998e;">${recordCount}</div>
            </div>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                💡 Switch to the <strong>Q&A</strong> tab to continue training
            </div>
        `;
    } else {
        currentSessionDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <span style="font-size: 1.5em;">💤</span>
                <div style="flex: 1;">
                    <div style="font-size: 1.1em; font-weight: bold; color: #666;">No Active Session</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 3px;">Start a new training session to begin</div>
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                💡 Switch to the <strong>Q&A</strong> tab to start a new training session
            </div>
        `;
    }

    historyContainer.appendChild(currentSessionDiv);

    // Completed sessions section
    const completedSessions = getCompletedTrainingSessions();

    const completedHeaderDiv = document.createElement('div');
    completedHeaderDiv.style.cssText = 'margin: 20px 0 10px 0; padding: 10px 0; border-bottom: 2px solid #e0e0e0;';
    completedHeaderDiv.innerHTML = `
        <h4 style="margin: 0; font-size: 1.1em; color: #333;">📋 Completed Sessions (${completedSessions.length})</h4>
    `;
    historyContainer.appendChild(completedHeaderDiv);

    if (completedSessions.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.style.cssText = 'padding: 30px; text-align: center; background: #f9f9f9; border-radius: 8px; color: #999;';
        emptyDiv.innerHTML = `
            <div style="font-size: 3em; margin-bottom: 10px;">📝</div>
            <div style="font-size: 1.1em; margin-bottom: 5px;">No completed training sessions yet</div>
            <div style="font-size: 0.9em;">Complete a training session to see it here</div>
        `;
        historyContainer.appendChild(emptyDiv);
    } else {
        // Display completed sessions (newest first)
        completedSessions.reverse().forEach((session, index) => {
            const sessionCard = document.createElement('div');
            sessionCard.className = 'history-item';
            sessionCard.style.cssText = 'margin-bottom: 15px; padding: 15px; background: white; border-left: 4px solid #667eea; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);';

            const date = new Date(session.completed_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
            const displayName = session.session_name || session.name || 'Untitled Session';

            let footerHtml = '';
            if (session.training_set_id) {
                const entryCount = session.entries_in_set != null ? session.entries_in_set : session.record_count;
                footerHtml = `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #f9f9f9; border-radius: 5px; font-size: 0.9em; color: #666;">
                        <span>Training set saved (${entryCount} entries)</span>
                        <button onclick="openTrainingSetViewer(${session.training_set_id})" style="padding: 6px 14px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">View Training Set</button>
                    </div>
                `;
            } else if (session.training_set_error) {
                footerHtml = `
                    <div style="padding: 10px; background: #fff4e5; border-radius: 5px; font-size: 0.9em; color: #b25f00;">
                        Training set not created: ${escapeHtml(session.training_set_error)}
                    </div>
                `;
            } else {
                footerHtml = `
                    <div style="padding: 10px; background: #f9f9f9; border-radius: 5px; font-size: 0.9em; color: #666;">
                        Session saved.
                    </div>
                `;
            }

            sessionCard.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <div style="font-size: 1.1em; font-weight: bold; color: #667eea; margin-bottom: 5px;">
                            ${escapeHtml(displayName)}
                        </div>
                        <div style="font-size: 0.85em; color: #999;">
                            Completed: ${dateStr}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.5em; font-weight: bold; color: #11998e;">${session.record_count}</div>
                        <div style="font-size: 0.8em; color: #666;">Training Records</div>
                    </div>
                </div>
                ${footerHtml}
            `;

            historyContainer.appendChild(sessionCard);
        });
    }
}

// Get completed training sessions from cache (loaded from server)
function getCompletedTrainingSessions() {
    return trainingSessionCache.completed_sessions || [];
}

// Training Set Viewer Modal

async function openTrainingSetViewer(trainingSetId) {
    const modal = document.getElementById('trainingset-viewer-modal');
    const title = document.getElementById('trainingset-viewer-title');
    const meta = document.getElementById('trainingset-viewer-meta');
    const body = document.getElementById('trainingset-viewer-body');

    title.textContent = 'Training Set';
    meta.textContent = '';
    body.innerHTML = '<p style="color: #999;">Loading...</p>';
    modal.style.display = 'flex';

    const token = sessionStorage.getItem('session_token');
    try {
        const [detailResp, dataResp] = await Promise.all([
            fetch(`${API_BASE}/training/sets/${trainingSetId}`, { headers: { 'Authorization': `Bearer ${token}` } }),
            fetch(`${API_BASE}/training/sets/${trainingSetId}/data`, { headers: { 'Authorization': `Bearer ${token}` } })
        ]);

        if (!detailResp.ok || !dataResp.ok) {
            const errBody = await (detailResp.ok ? dataResp : detailResp).json().catch(() => ({}));
            body.innerHTML = `<p style="color: #c0392b;">Failed to load: ${escapeHtml(errBody.detail || 'unknown error')}</p>`;
            return;
        }

        const detail = await detailResp.json();
        const dataPayload = await dataResp.json();
        const entries = dataPayload.data || [];

        title.textContent = detail.name || 'Training Set';
        const createdAt = detail.created_at ? new Date(detail.created_at).toLocaleString() : 'unknown';
        meta.textContent = `Created by ${detail.created_by} on ${createdAt} • ${entries.length} entries`;

        if (entries.length === 0) {
            body.innerHTML = '<p style="color: #999;">This training set has no entries.</p>';
            return;
        }

        body.innerHTML = '';
        entries.forEach((entry, idx) => {
            const card = document.createElement('div');
            card.style.cssText = 'margin-bottom: 16px; padding: 14px; border: 1px solid #e0e0e0; border-radius: 6px; background: #fafafa;';
            const rating = entry.rating || (entry.metadata && entry.metadata.rating) || 'unrated';
            const ratingColor = rating === 'acceptable' ? '#11998e' : (rating === 'needs_improvement' ? '#e67e22' : '#999');
            const ratingLabel = rating === 'acceptable' ? 'Acceptable' : (rating === 'needs_improvement' ? 'Needs Improvement (corrected)' : rating);

            let answerBlock = '';
            if (rating === 'needs_improvement' && entry.baseline_answer) {
                answerBlock = `
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 0.8em; color: #777; margin-bottom: 3px;">Original AI Answer</div>
                        <div style="padding: 8px; background: #fff3f3; border-left: 3px solid #e91e63; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(entry.baseline_answer)}</div>
                    </div>
                    <div>
                        <div style="font-size: 0.8em; color: #777; margin-bottom: 3px;">User Correction (training output)</div>
                        <div style="padding: 8px; background: #f0fff4; border-left: 3px solid #11998e; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(entry.output || '')}</div>
                    </div>
                `;
            } else {
                answerBlock = `
                    <div>
                        <div style="font-size: 0.8em; color: #777; margin-bottom: 3px;">Training Output ${rating === 'needs_improvement' ? '(user correction)' : '(AI answer)'}</div>
                        <div style="padding: 8px; background: white; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(entry.output || '')}</div>
                    </div>
                `;
            }

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #555;">Entry ${idx + 1}</strong>
                    <span style="font-size: 0.85em; color: white; background: ${ratingColor}; padding: 3px 10px; border-radius: 12px;">${escapeHtml(ratingLabel)}</span>
                </div>
                <div style="margin-bottom: 10px;">
                    <div style="font-size: 0.8em; color: #777; margin-bottom: 3px;">Prompt</div>
                    <div style="padding: 8px; background: white; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(entry.instruction || '')}</div>
                </div>
                ${answerBlock}
            `;
            body.appendChild(card);
        });
    } catch (e) {
        body.innerHTML = `<p style="color: #c0392b;">Error: ${escapeHtml(e.message)}</p>`;
    }
}

function closeTrainingSetViewer() {
    const modal = document.getElementById('trainingset-viewer-modal');
    if (modal) modal.style.display = 'none';
}
