import '../css/input.css';

import { createIcons, Bot, User, Send, Copy, ExternalLink, Check } from 'lucide';

import { marked } from 'marked';
import DOMPurify from 'dompurify';
import '../css/input.css';
//import { createIcons, Bot, User, Send } from 'lucide';

// ==================================================
// ICONS
// ==================================================

function refreshIcons() {
    createIcons({
        icons: {
            Bot,
            User,
            Send,
            ExternalLink,
            Copy,
            Check
        }
    });
}

// ==================================================
// MARKDOWN RENDERING
// ==================================================

function renderMarkdown(content) {
    const rawHTML = marked.parse(content);

    return DOMPurify.sanitize(rawHTML);
}

// ==================================================
// ELEMENTS
// ==================================================

const landingView = document.getElementById('landing-view');
const chatView = document.getElementById('chat-view');

const messagesContainer = document.getElementById('messages-container');
const messages = document.getElementById('messages');
const welcomeScreen = document.getElementById('welcome-screen');

const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const backHomeButton = document.getElementById('back-home');

// ==================================================
// ANONYMOUS USER IDENTITY
// ==================================================

const USER_ID_KEY = 'willard_user_id';
const HISTORY_KEY = 'willard_chat_history';

function getUserId() {
    let userId = localStorage.getItem(USER_ID_KEY);

    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem(USER_ID_KEY, userId);
    }

    return userId;
}

const userId = getUserId();

// ==================================================
// CONVERSATION HISTORY
// ==================================================

function loadHistory() {
    try {
        const storedHistory = JSON.parse(
            localStorage.getItem(HISTORY_KEY) || '[]'
        );

        if (!Array.isArray(storedHistory)) return [];

        return storedHistory.filter(message =>
            message &&
            ['user', 'assistant'].includes(message.role) &&
            typeof message.content === 'string'
        );

    } catch (error) {
        console.error('Could not load conversation history:', error);
        return [];
    }
}

let conversationHistory = loadHistory();

function saveHistory() {
    localStorage.setItem(
        HISTORY_KEY,
        JSON.stringify(conversationHistory)
    );
}

// ==================================================
// NAVIGATION
// ==================================================

function showView(view) {
    const showChat = view === 'chat';

    landingView.classList.toggle('hidden', showChat);
    chatView.classList.toggle('hidden', !showChat);
    chatView.classList.toggle('flex', showChat);
}

document.querySelectorAll('[data-open-chat]').forEach(button => {
    button.addEventListener('click', () => {
        showView('chat');
        refreshIcons();
        chatInput.focus();
    });
});

backHomeButton.addEventListener('click', () => {
    showView('landing');
});

// ==================================================
// MESSAGE RENDERING
// ==================================================

function addMessage(role, content) {
    welcomeScreen.classList.add('hidden');
    messages.classList.remove('hidden');

    const isUser = role === 'user';

    const message = document.createElement('div');

    message.className = `flex items-start gap-3 ${
        isUser ? 'flex-row-reverse' : ''
    }`;

    const avatar = document.createElement('div');

    avatar.className = `flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
        isUser
            ? 'bg-[#E7EDF5] text-[#173B70]'
            : 'bg-[#173B70] text-white'
    }`;

    const icon = document.createElement('i');

    icon.setAttribute('data-lucide', isUser ? 'user' : 'bot');
    icon.className = 'h-5 w-5';

    avatar.appendChild(icon);

    const bubble = document.createElement('div');

    // Preserve the existing user message styling.
    // Assistant responses use a plain-text presentation.
    bubble.className = isUser
        ? 'max-w-[85%] rounded-2xl rounded-tr-sm bg-[#173B70] px-4 py-3 text-sm leading-7 text-white'
        : 'w-full text-sm leading-7 text-[#243449] markdown-content';

    if (isUser) {
        bubble.textContent = content;
    } else {
        bubble.innerHTML = renderMarkdown(content);
    }

    message.appendChild(avatar);

    const contentWrapper = document.createElement('div');

    contentWrapper.className = isUser
        ? 'flex min-w-0 max-w-[85%] flex-col gap-2'
        : 'flex min-w-0 w-full flex-col gap-2';

    contentWrapper.appendChild(bubble);

    // Copy response button (assistant only)
    if (!isUser) {
        const actions = document.createElement('div');

        actions.className = 'flex items-center justify-start';

        const copyButton = document.createElement('button');

        copyButton.type = 'button';
        copyButton.className =
            'flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-[#718096] transition hover:bg-[#EAF0F8] hover:text-[#173B70]';

        copyButton.innerHTML = `
            <i data-lucide="copy" class="h-3.5 w-3.5"></i>
            <span>Copy</span>
        `;

        copyButton.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(
                    bubble.innerText
                );

                copyButton.innerHTML = `
                    <i data-lucide="check" class="h-3.5 w-3.5"></i>
                    <span>Copied</span>
                `;

                refreshIcons();

            } catch (error) {
                console.error('Copy failed:', error);
            }
        });

        actions.appendChild(copyButton);
        contentWrapper.appendChild(actions);
    }

    message.appendChild(contentWrapper);
    messages.appendChild(message);

    refreshIcons();
    scrollToBottom();

    return bubble;
}



// ==================================================
// THINKING INDICATOR
// ==================================================

function showThinking() {
    const indicator = document.createElement('div');

    indicator.id = 'thinking-indicator';
    indicator.className = 'flex items-center gap-3';

    const avatar = document.createElement('div');

    avatar.className =
        'flex h-9 w-9 items-center justify-center rounded-xl bg-[#173B70] text-white';

    const icon = document.createElement('i');

    icon.setAttribute('data-lucide', 'bot');
    icon.className = 'h-5 w-5';

    avatar.appendChild(icon);

    const bubble = document.createElement('div');

    bubble.className =
        'rounded-2xl rounded-tl-sm border border-[#DCE4EF] bg-white px-4 py-3 text-sm text-[#718096]';

    const text = document.createElement('span');

    text.className = 'animate-pulse';
    text.textContent = 'Thinking...';

    bubble.appendChild(text);

    indicator.appendChild(avatar);
    indicator.appendChild(bubble);

    messages.appendChild(indicator);

    refreshIcons();
    scrollToBottom();
}

function removeThinking() {
    document.getElementById('thinking-indicator')?.remove();
}

// ==================================================
// SCROLLING
// ==================================================

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ==================================================
// API STREAMING
// ==================================================

let isSending = false;
const CHAT_ERROR_MESSAGE = "Something went wrong. I'm sorry for that dear";
const CHAT_TIMEOUT_MS = 20000;
const STREAM_COMPLETE_MARKER = 'WONKA_COMPLETE';
const STREAM_ERROR_MARKER = 'WONKA_ERROR';

async function sendMessage(text) {
    const query = text.trim();

    if (!query || isSending) return;

    isSending = true;
    let assistantBubble = null;
    let assistantResponse = '';
    let userMessage = null;
    let userMessageAdded = false;
    let timeoutId = null;
    let controller = null;
    let offlineHandler = null;
    let failureDisplayed = false;

    try {
        sendButton.disabled = true;

        if (typeof navigator !== 'undefined' && navigator.onLine === false) {
            throw new Error('Browser reports that it is offline.');
        }

        controller = new AbortController();
        offlineHandler = () => controller.abort();
        window.addEventListener('offline', offlineHandler);

        if (typeof navigator !== 'undefined' && navigator.onLine === false) {
            controller.abort();
        }

        // Display user message
        addMessage('user', query);

        chatInput.value = '';

        // Keep previous history separate from the current query
        const historyForRequest = [...conversationHistory];

        // Save current user message
        userMessage = {
            role: 'user',
            content: query
        };

        conversationHistory.push(userMessage);
        userMessageAdded = true;
        saveHistory();

        showThinking();

        timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

        if (controller.signal.aborted) {
            throw new Error('The chat request was aborted because the browser went offline.');
        }

        const response = await fetch('/api/chat', {
            method: 'POST',

            headers: {
                'Content-Type': 'application/json'
            },

            body: JSON.stringify({
                user_id: userId,
                query: query,
                history: historyForRequest
            }),
            signal: controller.signal
        });

        if (!response.ok) {
            throw new Error(`Chat request failed with HTTP ${response.status}.`);
        }

        const contentType = response.headers.get('content-type');

        if (!contentType || !contentType.toLowerCase().startsWith('text/plain')) {
            throw new Error('The server returned an unexpected response format.');
        }

        if (!response.body || typeof response.body.getReader !== 'function') {
            throw new Error('The server did not provide a readable response stream.');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const markerLength = Math.max(
            STREAM_COMPLETE_MARKER.length,
            STREAM_ERROR_MARKER.length
        );
        let pendingText = '';

        const renderResponseText = textChunk => {
            if (!textChunk) return;

            if (!assistantBubble) {
                removeThinking();
                assistantBubble = addMessage('assistant', '');
            }

            assistantResponse += textChunk;
            assistantBubble.innerHTML = renderMarkdown(assistantResponse);
            scrollToBottom();
        };

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                pendingText += decoder.decode();
                break;
            }

            pendingText += decoder.decode(value, {
                stream: true
            });

            const safeLength = pendingText.length - markerLength;

            if (safeLength > 0) {
                renderResponseText(pendingText.slice(0, safeLength));
                pendingText = pendingText.slice(safeLength);
            }
        }

        if (pendingText.endsWith(STREAM_ERROR_MARKER)) {
            throw new Error('The server reported a streaming failure.');
        }

        if (!pendingText.endsWith(STREAM_COMPLETE_MARKER)) {
            throw new Error('The response stream ended without a completion marker.');
        }

        renderResponseText(
            pendingText.slice(0, -STREAM_COMPLETE_MARKER.length)
        );

        if (!assistantResponse.trim()) {
            throw new Error('The server returned an empty response.');
        }

        // Save completed assistant response
        conversationHistory.push({
            role: 'assistant',
            content: assistantResponse
        });

        try {
            saveHistory();
        } catch (error) {
            console.error('Could not save conversation history:', error);
        }

    } catch (error) {
        console.error('Wonka API error:', error);

        if (!failureDisplayed) {
            failureDisplayed = true;
            removeThinking();

            if (assistantBubble) {
                assistantBubble.textContent = CHAT_ERROR_MESSAGE;
            } else {
                assistantBubble = addMessage('assistant', CHAT_ERROR_MESSAGE);
            }

            if (
                userMessageAdded &&
                conversationHistory[conversationHistory.length - 1] === userMessage
            ) {
                conversationHistory.pop();
            }

            try {
                saveHistory();
            } catch (historyError) {
                console.error('Could not save conversation history:', historyError);
            }
        }

    } finally {
        clearTimeout(timeoutId);
        if (offlineHandler) {
            window.removeEventListener('offline', offlineHandler);
        }
        removeThinking();

        isSending = false;
        sendButton.disabled = false;

        chatInput.focus();
    }
}

// ==================================================
// FORM SUBMISSION
// ==================================================

chatForm.addEventListener('submit', event => {
    event.preventDefault();
    sendMessage(chatInput.value);
});

// ==================================================
// SUGGESTED QUESTIONS
// ==================================================

document.querySelectorAll('.suggestion').forEach(button => {
    button.addEventListener('click', () => {
        sendMessage(button.textContent);
    });
});

// ==================================================
// KEYBOARD SHORTCUTS
// ==================================================

chatInput.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

// ==================================================
// INITIALIZATION
// ==================================================

refreshIcons();

console.log('Wonka frontend initialized!');
console.log('Anonymous user ID:', userId);
console.log('Previous messages loaded:', conversationHistory.length);
