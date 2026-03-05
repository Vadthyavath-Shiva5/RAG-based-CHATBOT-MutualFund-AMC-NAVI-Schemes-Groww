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
        this.closeBtn.addEventListener('click', () => this.closeChat());
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
        if (this.chatBox.classList.contains('active')) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        this.chatBox.classList.add('active');
        this.chatToggle.classList.add('active');
        setTimeout(() => this.chatInput.focus(), 100);

        // Remove badge when chat is opened
        const badge = this.chatToggle.querySelector('.chat-badge');
        if (badge) {
            badge.remove();
        }

        // Show intro only on first open with empty conversation
        if (this.chatMessages.children.length === 0) {
            this.showIntro();
        }
    }

    closeChat() {
        this.chatBox.classList.remove('active');
        this.chatToggle.classList.remove('active');
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
            const configuredBase = (window.BACKEND_API_BASE_URL || '').replace(/\/$/, '');
            const chatUrl = configuredBase ? `${configuredBase}/chat` : '/api/chat';
            // Send to backend (direct or via phase6 proxy)
            const response = await fetch(chatUrl, {
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
                let backendError = `Request failed (${response.status})`;
                try {
                    const errBody = await response.json();
                    if (errBody && errBody.error) {
                        backendError = errBody.error;
                    }
                } catch (_) {
                    // Ignore JSON parse error and keep generic error text.
                }
                throw new Error(backendError);
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
            const msg = (error && error.message && error.message.toLowerCase().includes('failed to fetch'))
                ? 'Unable to reach chatbot backend. Please start phase4/app.py on port 8000.'
                : `Unable to generate response right now. ${error.message || ''}`.trim();
            this.addMessage(
                msg,
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
            const renderedHtml = this.formatResponseToHtml(content);
            if (renderedHtml) {
                const richDiv = document.createElement('div');
                richDiv.className = 'bot-markdown';
                richDiv.innerHTML = renderedHtml;
                contentDiv.appendChild(richDiv);
            } else {
                const p = document.createElement('p');
                p.textContent = content;
                contentDiv.appendChild(p);
            }

            // Add citations if available
            if (sources && sources.length > 0) {
                const citationsDiv = document.createElement('div');
                citationsDiv.className = 'citations';
                
                sources.forEach((source, index) => {
                    const a = document.createElement('a');
                    const sourceUrl = typeof source === 'string' ? source : source.url;
                    if (!sourceUrl) {
                        return;
                    }
                    a.href = sourceUrl;
                    a.textContent = `[Source ${index + 1}]`;
                    a.title = sourceUrl;
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';
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

    formatResponseToHtml(text) {
        const normalized = this.normalizeResponseText(text);
        if (!normalized) {
            return '';
        }

        const lines = normalized.split('\n');
        const blocks = [];
        let i = 0;

        while (i < lines.length) {
            const line = lines[i];
            const trimmed = line.trim();

            if (!trimmed) {
                i++;
                continue;
            }

            // Markdown table block: header + separator + rows
            if (
                i + 1 < lines.length &&
                line.includes('|') &&
                this.isMarkdownTableSeparator(lines[i + 1].trim())
            ) {
                const headerLine = line;
                i += 2;

                const bodyLines = [];
                while (i < lines.length) {
                    const row = lines[i];
                    if (!row.trim() || !row.includes('|')) {
                        break;
                    }
                    bodyLines.push(row);
                    i++;
                }

                blocks.push(this.renderMarkdownTable(headerLine, bodyLines));
                continue;
            }

            // Unordered list
            if (/^[-*]\s+/.test(trimmed)) {
                const items = [];
                while (i < lines.length) {
                    const match = lines[i].trim().match(/^[-*]\s+(.+)$/);
                    if (!match) {
                        break;
                    }
                    items.push(`<li>${this.formatInline(match[1])}</li>`);
                    i++;
                }
                blocks.push(`<ul class="chat-list">${items.join('')}</ul>`);
                continue;
            }

            // Ordered list
            if (/^\d+\.\s+/.test(trimmed)) {
                const items = [];
                while (i < lines.length) {
                    const match = lines[i].trim().match(/^\d+\.\s+(.+)$/);
                    if (!match) {
                        break;
                    }
                    items.push(`<li>${this.formatInline(match[1])}</li>`);
                    i++;
                }
                blocks.push(`<ol class="chat-list chat-list-ordered">${items.join('')}</ol>`);
                continue;
            }

            // Paragraph block
            const paragraphLines = [trimmed];
            i++;
            while (i < lines.length) {
                const nextTrimmed = lines[i].trim();
                if (!nextTrimmed) {
                    break;
                }
                if (/^[-*]\s+/.test(nextTrimmed) || /^\d+\.\s+/.test(nextTrimmed)) {
                    break;
                }
                if (
                    i + 1 < lines.length &&
                    lines[i].includes('|') &&
                    this.isMarkdownTableSeparator(lines[i + 1].trim())
                ) {
                    break;
                }
                paragraphLines.push(nextTrimmed);
                i++;
            }

            const paragraphHtml = paragraphLines
                .map((entry) => this.formatInline(entry))
                .join('<br>');
            blocks.push(`<p>${paragraphHtml}</p>`);
        }

        return blocks.join('');
    }

    renderMarkdownTable(headerLine, bodyLines) {
        const headers = this.splitTableRow(headerLine);
        if (headers.length === 0) {
            return `<p>${this.formatInline(headerLine)}</p>`;
        }

        const headerHtml = headers.map((cell) => `<th>${this.formatInline(cell)}</th>`).join('');
        const bodyHtml = bodyLines.map((rowLine) => {
            const cells = this.splitTableRow(rowLine);
            const fixedCells = headers.map((_, index) => cells[index] || '');
            const cellHtml = fixedCells.map((cell) => `<td>${this.formatInline(cell)}</td>`).join('');
            return `<tr>${cellHtml}</tr>`;
        }).join('');

        return `
            <div class="chat-table-wrap">
                <table class="chat-table">
                    <thead><tr>${headerHtml}</tr></thead>
                    <tbody>${bodyHtml}</tbody>
                </table>
            </div>
        `;
    }

    splitTableRow(rowLine) {
        const trimmed = rowLine.trim().replace(/^\|/, '').replace(/\|$/, '');
        return trimmed.split('|').map((cell) => cell.trim()).filter((_, idx, arr) => arr.length > 1 || trimmed.length > 0);
    }

    isMarkdownTableSeparator(line) {
        return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
    }

    normalizeResponseText(text) {
        return String(text || '')
            .replace(/\r\n/g, '\n')
            .replace(/\u2022/g, '- ')
            .trim();
    }

    escapeHtml(text) {
        return String(text || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    formatInline(text) {
        let formatted = this.escapeHtml(text);

        formatted = formatted.replace(
            /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
            (_match, label, url) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`
        );
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/__([^_]+)__/g, '<strong>$1</strong>');
        // Remove unmatched markdown emphasis markers to keep UI clean.
        formatted = formatted.replace(/\*\*/g, '').replace(/__/g, '');

        return formatted;
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
        const introText = "Welcome. I am the Navi Mutual Fund Assistant and can help with Navi scheme details and general mutual fund information.";
        this.addMessage(introText, 'bot');

        const queries = [
            { label: "about Navi?", query: "What is Navi AMC?" },
            { label: "about mutual fund?", query: "What are mutual funds?" }
        ];

        const menuDiv = document.createElement('div');
        menuDiv.className = 'bot-menu';

        queries.forEach(({ label, query }) => {
            const btn = document.createElement('button');
            btn.className = 'menu-query';
            btn.textContent = label;
            btn.onclick = (e) => {
                e.preventDefault();
                console.log('Menu query clicked:', query);
                this.sendMessage(query);
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
        chatWidgetInstance.openChat();
    } else {
        console.warn('Chat widget not yet initialized');
    }
}

window.sendChatMessage = function(message) {
    if (!chatWidgetInstance) {
        return;
    }
    chatWidgetInstance.openChat();
    chatWidgetInstance.sendMessage(message);
}

document.addEventListener('DOMContentLoaded', () => {
    chatWidgetInstance = new ChatWidget();
    console.log('Chat widget initialized');
});
