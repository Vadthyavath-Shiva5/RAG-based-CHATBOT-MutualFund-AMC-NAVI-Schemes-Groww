// Chat Widget Functionality
class ChatWidget {
    constructor() {
        this.chatBox = document.getElementById('chatBox');
        this.chatToggle = document.getElementById('chatToggle');
        this.closeBtn = document.querySelector('.close-btn');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatMessages = document.getElementById('chatMessages');
        this.messageCount = 0;
        
        this.init();
    }

    init() {
        // Event listeners
        this.chatToggle.addEventListener('click', () => this.toggleChat());
        this.closeBtn.addEventListener('click', () => this.toggleChat());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Focus on input when chat opens
        this.chatBox.addEventListener('animationend', () => {
            if (this.chatBox.classList.contains('active')) {
                this.chatInput.focus();
            }
        });
    }

    toggleChat() {
        this.chatBox.classList.toggle('active');
        this.chatToggle.classList.toggle('active');
        
        if (this.chatBox.classList.contains('active')) {
            setTimeout(() => this.chatInput.focus(), 100);
            // Remove badge when chat is opened
            const badge = this.chatToggle.querySelector('.chat-badge');
            if (badge) {
                badge.remove();
            }
            // show intro if no messages yet
            if (this.chatMessages.children.length === 0) {
                this.showIntro();
            }
        }
    }

    async sendMessage(customMessage = null) {
        const message = (customMessage || this.chatInput.value).trim();
        
        if (!message) return;

        // remove any intro menu if present
        const menus = this.chatMessages.querySelectorAll('.bot-menu');
        menus.forEach(m => m.remove());

        // Disable input and button
        this.chatInput.disabled = true;
        this.sendBtn.disabled = true;

        // Add user message
        this.addMessage(message, 'user');
        this.chatInput.value = '';

        // Show loading indicator
        this.showLoading();

        try {
            // Send to backend
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context_type: 'mutual_funds'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Remove loading indicator
            this.removeLoading();

            console.log('Chat response received:', data);

            // Add bot response
            if (data.success !== false) {
                const answerText = data.answer || data.response || 'No answer provided.';
                console.log('Displaying answer:', answerText);
                this.addMessage(answerText, 'bot', data.citations || data.sources);

                // Increment unread count if chat is not active
                if (!this.chatBox.classList.contains('active')) {
                    this.incrementBadge();
                }
            } else {
                console.log('Response was not successful');
                this.addMessage(
                    'Sorry, I encountered an error processing your question. Please try again.',
                    'bot'
                );
            }
        } catch (error) {
            console.error('Error:', error);
            this.removeLoading();
            this.addMessage(
                'Connection error. Please check your internet and try again.',
                'bot'
            );
        } finally {
            // Re-enable input and button
            this.chatInput.disabled = false;
            this.sendBtn.disabled = false;
            this.chatInput.focus();
        }
    }

    addMessage(content, type, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (type === 'bot') {
            // Format bot message with paragraphs
            const p = document.createElement('p');
            p.textContent = content;
            contentDiv.appendChild(p);

            // Add citations if available
            if (sources && sources.length > 0) {
                const citationsDiv = document.createElement('div');
                citationsDiv.className = 'citations';
                
                sources.forEach((source, index) => {
                    const a = document.createElement('a');
                    a.href = '#';
                    a.textContent = `[Source ${index + 1}]`;
                    a.title = source;
                    a.onclick = (e) => {
                        e.preventDefault();
                        alert(`Source: ${source}`);
                    };
                    citationsDiv.appendChild(a);
                });
                
                contentDiv.appendChild(citationsDiv);
            }
        } else {
            const p = document.createElement('p');
            p.textContent = content;
            contentDiv.appendChild(p);
        }

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showLoading() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.id = 'loadingMessage';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-dots';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'loading-dot';
            loadingDiv.appendChild(dot);
        }

        contentDiv.appendChild(loadingDiv);
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);

        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    removeLoading() {
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    showIntro() {
        const introText = "Hi! I'm Groww AI assistant. How can I help you with Navi today?";
        this.addMessage(introText, 'bot');

        const queries = [
            "What is Navi AMC?",
            "What are mutual funds?"
        ];

        const menuDiv = document.createElement('div');
        menuDiv.className = 'bot-menu';

        queries.forEach(q => {
            const btn = document.createElement('button');
            btn.className = 'menu-query';
            btn.textContent = q;
            btn.onclick = (e) => {
                e.preventDefault();
                console.log('Menu query clicked:', q);
                this.sendMessage(q);
                return false;
            };
            menuDiv.appendChild(btn);
        });

        const wrapper = document.createElement('div');
        wrapper.className = 'message bot-message';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.appendChild(menuDiv);
        wrapper.appendChild(contentDiv);
        this.chatMessages.appendChild(wrapper);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    incrementBadge() {
        let badge = this.chatToggle.querySelector('.chat-badge');
        
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'chat-badge';
            badge.textContent = '1';
            this.chatToggle.appendChild(badge);
        } else {
            badge.textContent = parseInt(badge.textContent) + 1;
        }
    }
}

// Initialize chat widget when DOM is ready
let chatWidgetInstance = null;

window.openChat = function() {
    console.log('openChat called');
    if (chatWidgetInstance) {
        chatWidgetInstance.toggleChat();
    } else {
        console.warn('Chat widget not yet initialized');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    chatWidgetInstance = new ChatWidget();
    console.log('Chat widget initialized');
});