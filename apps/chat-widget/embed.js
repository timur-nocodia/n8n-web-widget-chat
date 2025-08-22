/**
 * Modern AI Chat Widget - Embeddable Version
 * Add to any website with just 2 lines of JavaScript
 * 
 * Usage:
 * <script src="https://your-domain.com/embed.js"></script>
 * <script>VibeChat.init({ apiUrl: 'https://your-proxy-server.com' });</script>
 */

(function(window) {
    'use strict';

    // Prevent multiple initializations
    if (window.VibeChat) return;

    const VibeChat = {
        config: {
            apiUrl: 'http://localhost:8001',
            position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
            theme: 'dark', // dark, light, auto
            primaryColor: '#667eea',
            secondaryColor: '#764ba2',
            borderRadius: '16px',
            language: 'ru'
        },

        // Initialize the chat widget
        init(options = {}) {
            // Merge user options with defaults
            this.config = { ...this.config, ...options };
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.render());
            } else {
                this.render();
            }
        },

        // Render the chat widget
        render() {
            // Inject CSS styles
            this.injectStyles();
            
            // Create widget HTML
            const widgetHTML = this.createWidgetHTML();
            
            // Insert into DOM
            document.body.insertAdjacentHTML('beforeend', widgetHTML);
            
            // Initialize functionality
            this.initializeWidget();
        },

        // Inject CSS styles
        injectStyles() {
            const style = document.createElement('style');
            style.textContent = `
                /* Modern AI Chat Widget Embedded Styles */
                .vibe-chat-widget-container {
                    position: fixed;
                    ${this.getPositionStyles()}
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    --vibe-primary: ${this.config.primaryColor};
                    --vibe-secondary: ${this.config.secondaryColor};
                    --vibe-radius: ${this.config.borderRadius};
                }

                .vibe-chat-toggle {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    backdrop-filter: blur(10px);
                    position: relative;
                    overflow: hidden;
                }

                .vibe-chat-toggle:hover {
                    transform: scale(1.1) rotate(5deg);
                    box-shadow: 0 25px 50px rgba(102, 126, 234, 0.4);
                }

                .vibe-chat-toggle::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                    transition: left 0.6s;
                }

                .vibe-chat-toggle:hover::before {
                    left: 100%;
                }

                .vibe-chat-icon, .vibe-close-icon {
                    font-size: 24px;
                    color: white;
                    transition: all 0.3s ease;
                    position: absolute;
                }

                .vibe-close-icon {
                    opacity: 0;
                    transform: rotate(180deg);
                }

                .vibe-chat-widget.open .vibe-chat-icon {
                    opacity: 0;
                    transform: rotate(-180deg);
                }

                .vibe-chat-widget.open .vibe-close-icon {
                    opacity: 1;
                    transform: rotate(0deg);
                }

                .vibe-chat-window {
                    position: absolute;
                    ${this.getWindowPosition()}
                    width: 380px;
                    height: 600px;
                    background: rgba(30, 30, 46, 0.95);
                    backdrop-filter: blur(20px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: var(--vibe-radius);
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
                    transform: scale(0.8) translateY(20px);
                    opacity: 0;
                    visibility: hidden;
                    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }

                .vibe-chat-widget.open .vibe-chat-window {
                    transform: scale(1) translateY(0);
                    opacity: 1;
                    visibility: visible;
                }

                .vibe-chat-header {
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    padding: 20px;
                    color: white;
                    border-radius: var(--vibe-radius) var(--vibe-radius) 0 0;
                    position: relative;
                    overflow: hidden;
                }

                .vibe-chat-header::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                    animation: vibe-shimmer 3s infinite;
                }

                @keyframes vibe-shimmer {
                    0% { left: -100%; }
                    100% { left: 100%; }
                }

                .vibe-chat-header h3 {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                }

                .vibe-chat-status {
                    font-size: 12px;
                    opacity: 0.8;
                    margin-top: 4px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }

                .vibe-status-indicator {
                    width: 8px;
                    height: 8px;
                    background: #4ade80;
                    border-radius: 50%;
                    animation: vibe-pulse 2s infinite;
                }

                @keyframes vibe-pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .vibe-chat-messages {
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                    background: rgba(20, 20, 30, 0.5);
                    backdrop-filter: blur(10px);
                }

                .vibe-message {
                    margin-bottom: 16px;
                    animation: vibe-slideIn 0.3s ease-out;
                }

                @keyframes vibe-slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .vibe-message-bubble {
                    max-width: 85%;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 14px;
                    line-height: 1.4;
                    position: relative;
                    word-wrap: break-word;
                    word-break: break-word;
                    white-space: pre-wrap;
                    overflow-wrap: break-word;
                }

                .vibe-user-message .vibe-message-bubble {
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    color: white;
                    margin-left: auto;
                    border-bottom-right-radius: 4px;
                }

                .vibe-bot-message .vibe-message-bubble {
                    background: rgba(255, 255, 255, 0.1);
                    color: white;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-bottom-left-radius: 4px;
                }

                .vibe-typing-indicator {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px 16px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 18px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    max-width: 80px;
                }

                .vibe-typing-dots {
                    display: flex;
                    gap: 4px;
                }

                .vibe-dot {
                    width: 6px;
                    height: 6px;
                    background: white;
                    border-radius: 50%;
                    animation: vibe-typingDots 1.4s infinite;
                }

                .vibe-dot:nth-child(2) { animation-delay: 0.2s; }
                .vibe-dot:nth-child(3) { animation-delay: 0.4s; }

                @keyframes vibe-typingDots {
                    0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
                    30% { opacity: 1; transform: scale(1); }
                }

                .vibe-chat-input {
                    padding: 20px;
                    background: rgba(30, 30, 46, 0.8);
                    backdrop-filter: blur(20px);
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                    display: flex;
                    gap: 12px;
                    align-items: flex-end;
                }

                .vibe-input-container {
                    flex: 1;
                    position: relative;
                }

                .vibe-message-input {
                    width: 100%;
                    padding: 12px 16px;
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    color: white;
                    font-size: 14px;
                    outline: none;
                    backdrop-filter: blur(10px);
                    transition: all 0.3s ease;
                    resize: none;
                    min-height: 40px;
                    max-height: 120px;
                    font-family: inherit;
                }

                .vibe-message-input::placeholder {
                    color: rgba(255, 255, 255, 0.6);
                }

                .vibe-message-input:focus {
                    border-color: var(--vibe-primary);
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }

                .vibe-send-button {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    border: none;
                    color: white;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.3s ease;
                    flex-shrink: 0;
                    font-size: 16px;
                }

                .vibe-send-button:hover {
                    transform: scale(1.1);
                    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                }

                .vibe-send-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                    transform: none;
                }

                .vibe-suggestions {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin-top: 12px;
                    padding: 0 20px;
                }

                .vibe-suggestion-chip {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 8px 12px;
                    font-size: 12px;
                    color: white;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);
                }

                .vibe-suggestion-chip:hover {
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    border-color: transparent;
                    transform: translateY(-2px);
                }

                .vibe-streaming {
                    background: linear-gradient(-45deg, rgba(255,255,255,0.1), rgba(102,126,234,0.2), rgba(255,255,255,0.1));
                    background-size: 400% 400%;
                    animation: vibe-streamingGradient 2s ease infinite;
                }

                @keyframes vibe-streamingGradient {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }

                /* Mobile Responsive */
                @media (max-width: 480px) {
                    .vibe-chat-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 40px);
                        bottom: 0 !important;
                        right: 0 !important;
                        top: 0 !important;
                        left: 0 !important;
                        margin: 20px;
                    }
                }

                /* Scrollbar */
                .vibe-chat-messages::-webkit-scrollbar {
                    width: 6px;
                }

                .vibe-chat-messages::-webkit-scrollbar-track {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 3px;
                }

                .vibe-chat-messages::-webkit-scrollbar-thumb {
                    background: linear-gradient(135deg, var(--vibe-primary) 0%, var(--vibe-secondary) 100%);
                    border-radius: 3px;
                }
            `;
            document.head.appendChild(style);
        },

        // Get position styles based on config
        getPositionStyles() {
            const positions = {
                'bottom-right': 'bottom: 20px; right: 20px;',
                'bottom-left': 'bottom: 20px; left: 20px;',
                'top-right': 'top: 20px; right: 20px;',
                'top-left': 'top: 20px; left: 20px;'
            };
            return positions[this.config.position] || positions['bottom-right'];
        },

        // Get window position relative to button
        getWindowPosition() {
            const positions = {
                'bottom-right': 'bottom: 80px; right: 0;',
                'bottom-left': 'bottom: 80px; left: 0;',
                'top-right': 'top: 80px; right: 0;',
                'top-left': 'top: 80px; left: 0;'
            };
            return positions[this.config.position] || positions['bottom-right'];
        },

        // Create widget HTML
        createWidgetHTML() {
            return `
                <div class="vibe-chat-widget-container">
                    <div class="vibe-chat-widget" id="vibeChatWidget">
                        <button class="vibe-chat-toggle" id="vibeChatToggle">
                            <div class="vibe-chat-icon">💬</div>
                            <div class="vibe-close-icon">✕</div>
                        </button>

                        <div class="vibe-chat-window" id="vibeChatWindow">
                            <div class="vibe-chat-header">
                                <h3>AI Assistant</h3>
                                <div class="vibe-chat-status">
                                    <span class="vibe-status-indicator"></span>
                                    Online • Ready to help
                                </div>
                            </div>

                            <div class="vibe-chat-messages" id="vibeChatMessages">
                                <div class="vibe-message vibe-bot-message">
                                    <div class="vibe-message-bubble">
                                        👋 Привет! Я ваш AI ассистент. Чем могу помочь?
                                    </div>
                                </div>
                            </div>

                            <div class="vibe-suggestions" id="vibeSuggestions">
                                <div class="vibe-suggestion-chip" data-text="Что такое Vibe School?">Что такое Vibe School?</div>
                                <div class="vibe-suggestion-chip" data-text="Расскажи о курсах">Расскажи о курсах</div>
                                <div class="vibe-suggestion-chip" data-text="Как начать?">Как начать?</div>
                            </div>

                            <div class="vibe-chat-input">
                                <div class="vibe-input-container">
                                    <textarea 
                                        class="vibe-message-input" 
                                        id="vibeMessageInput" 
                                        placeholder="Введите сообщение..."
                                        rows="1"
                                    ></textarea>
                                </div>
                                <button class="vibe-send-button" id="vibeSendButton">
                                    ➤
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        // Initialize widget functionality
        initializeWidget() {
            this.widget = document.getElementById('vibeChatWidget');
            this.toggle = document.getElementById('vibeChatToggle');
            this.window = document.getElementById('vibeChatWindow');
            this.messages = document.getElementById('vibeChatMessages');
            this.input = document.getElementById('vibeMessageInput');
            this.sendButton = document.getElementById('vibeSendButton');
            this.suggestions = document.getElementById('vibeSuggestions');

            this.isOpen = false;
            this.isStreaming = false;
            this.sessionId = null;

            this.attachEventListeners();
            this.initializeSession();
        },

        // Attach event listeners
        attachEventListeners() {
            // Toggle chat
            this.toggle.addEventListener('click', () => this.toggleChat());
            
            // Send message
            this.sendButton.addEventListener('click', () => this.sendMessage());
            
            // Enter key handling
            this.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            this.input.addEventListener('input', () => this.autoResizeInput());

            // Suggestions
            this.suggestions.addEventListener('click', (e) => {
                if (e.target.classList.contains('vibe-suggestion-chip')) {
                    const text = e.target.getAttribute('data-text');
                    this.input.value = text;
                    this.sendMessage();
                }
            });
        },

        // Toggle chat open/close
        toggleChat() {
            this.isOpen = !this.isOpen;
            this.widget.classList.toggle('open', this.isOpen);
            
            if (this.isOpen && this.input) {
                setTimeout(() => this.input.focus(), 300);
            }
        },

        // Auto-resize input
        autoResizeInput() {
            this.input.style.height = 'auto';
            this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
        },

        // Initialize session
        async initializeSession() {
            try {
                const response = await fetch(`${this.config.apiUrl}/api/v1/session/create`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Origin': window.location.origin
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        origin_domain: window.location.hostname,
                        page_url: window.location.href
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    this.sessionId = data.session_id;
                    console.log('✅ VibeChat session created:', this.sessionId);
                } else {
                    throw new Error(`Session creation failed: ${response.status}`);
                }
            } catch (error) {
                console.error('❌ VibeChat session error:', error);
                this.addMessage('Не удалось подключиться к серверу. Попробуйте позже.', 'bot');
            }
        },

        // Send message
        async sendMessage() {
            const message = this.input.value.trim();
            if (!message || this.isStreaming) return;

            // Clear input and hide suggestions
            this.input.value = '';
            this.input.style.height = 'auto';
            this.suggestions.style.display = 'none';

            // Add user message
            this.addMessage(message, 'user');

            // Show typing indicator
            const typingElement = this.addTypingIndicator();
            this.isStreaming = true;

            try {
                const response = await fetch(`${this.config.apiUrl}/api/v1/chat/stream`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Origin': window.location.origin
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        message: message,
                        page_url: window.location.href
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                // Handle streaming (bot message will be created on first chunk)
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let streamedText = '';
                let botMessageElement = null;
                let messageBubble = null;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            
                            if (data === '[DONE]') {
                                if (messageBubble) {
                                    messageBubble.classList.remove('vibe-streaming');
                                }
                                this.isStreaming = false;
                                return;
                            }

                            if (data.trim() !== '') {
                                // Create bot message on first real chunk
                                if (!botMessageElement) {
                                    typingElement?.remove();
                                    botMessageElement = this.addMessage('', 'bot', true);
                                    messageBubble = botMessageElement.querySelector('.vibe-message-bubble');
                                }

                                try {
                                    const parsed = JSON.parse(data);
                                    if (parsed.error) {
                                        streamedText = `❌ ${parsed.error}`;
                                    } else {
                                        // Unknown JSON format - shouldn't happen with our server
                                        streamedText += JSON.stringify(parsed) + ' ';
                                    }
                                } catch (e) {
                                    // This is the complete accumulated text from server
                                    streamedText = data;
                                    console.log(`📝 Received text chunk (${data.length} chars):`, data);
                                }

                                // Update message content (preserve line breaks)
                                messageBubble.innerHTML = streamedText.replace(/\n/g, '<br>');
                                this.scrollToBottom();
                            }
                        }
                    }
                }

            } catch (error) {
                typingElement?.remove();
                this.addMessage(`Ошибка: ${error.message}`, 'bot');
                console.error('VibeChat error:', error);
            } finally {
                this.isStreaming = false;
            }
        },

        // Add message
        addMessage(text, type, isStreaming = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `vibe-message vibe-${type}-message`;
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = `vibe-message-bubble ${isStreaming ? 'vibe-streaming' : ''}`;
            bubbleDiv.textContent = text;
            
            messageDiv.appendChild(bubbleDiv);
            this.messages.appendChild(messageDiv);
            
            this.scrollToBottom();
            return messageDiv;
        },

        // Add typing indicator
        addTypingIndicator() {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'vibe-message vibe-bot-message';
            
            const indicatorDiv = document.createElement('div');
            indicatorDiv.className = 'vibe-typing-indicator';
            indicatorDiv.innerHTML = `
                <div class="vibe-typing-dots">
                    <div class="vibe-dot"></div>
                    <div class="vibe-dot"></div>
                    <div class="vibe-dot"></div>
                </div>
            `;
            
            messageDiv.appendChild(indicatorDiv);
            this.messages.appendChild(messageDiv);
            this.scrollToBottom();
            
            return messageDiv;
        },

        // Scroll to bottom
        scrollToBottom() {
            // Only auto-scroll if user is near the bottom (within 100px)
            const isNearBottom = this.messages.scrollHeight - this.messages.scrollTop - this.messages.clientHeight < 100;
            if (isNearBottom) {
                this.messages.scrollTop = this.messages.scrollHeight;
            }
        },

        // Public API methods
        open() { 
            if (!this.isOpen) this.toggleChat(); 
        },
        
        close() { 
            if (this.isOpen) this.toggleChat(); 
        },
        
        sendMessageProgrammatically(message) {
            if (this.input) {
                this.input.value = message;
                this.sendMessage();
            }
        }
    };

    // Expose to global scope
    window.VibeChat = VibeChat;

})(window);