/**
 * Conversation Management Module
 * Handles conversation CRUD operations and UI interactions
 */

class ConversationManager {
    constructor() {
        this.currentConversationId = null;
        this.conversations = [];
        this.currentMessages = [];
    }

    async init() {
        await this.loadConversations();
        this.setupEventListeners();
        this.enableChatInput();
    }

    setupEventListeners() {
        const newConvBtn = document.getElementById('new-conversation-btn');
        if (newConvBtn) {
            newConvBtn.addEventListener('click', () => this.createNewConversation());
        }

        const clearHistoryBtn = document.getElementById('clear-history-btn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearCurrentConversation());
        }
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations?limit=50');
            if (!response.ok) throw new Error('Failed to load conversations');

            this.conversations = await response.json();
            this.renderConversationList();

            // Auto-select first conversation or create new one
            if (this.conversations.length > 0 && !this.currentConversationId) {
                await this.selectConversation(this.conversations[0].conversation_id);
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            this.showError('Failed to load conversations');
        }
    }

    renderConversationList() {
        const listContainer = document.getElementById('conversation-list');
        if (!listContainer) return;

        if (this.conversations.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">No conversations yet. Start a new one!</div>';
            return;
        }

        listContainer.innerHTML = this.conversations.map(conv => {
            const isActive = conv.conversation_id === this.currentConversationId;
            const cost = conv.total_cost_usd || 0;
            const tasks = conv.total_tasks || 0;
            const duration = conv.total_duration_seconds || 0;
            const durationFormatted = duration > 0 ? this.formatDuration(duration) : '-';

            return `
                <div class="conversation-item ${isActive ? 'active' : ''}" 
                     data-id="${conv.conversation_id}"
                     onclick="conversationManager.selectConversation('${conv.conversation_id}')">
                    <div class="conversation-body">
                        <div class="conversation-header">
                            <span class="conversation-title">${this.escapeHtml(conv.title)}</span>
                            <span class="conversation-count">${conv.message_count} msgs</span>
                        </div>
                        <div class="conversation-meta">
                            <span class="conversation-date">${this.formatDate(conv.updated_at)}</span>
                        </div>
                        <div class="conversation-metrics">
                            <span class="metric-item" title="Total Cost">$${cost.toFixed(4)}</span>
                            <span class="metric-item" title="Total Tasks">${tasks} tasks</span>
                            <span class="metric-item" title="Total Duration">${durationFormatted}</span>
                        </div>
                    </div>
                    <div class="conversation-actions">
                        <button class="action-btn" onclick="event.stopPropagation(); conversationManager.renameConversation('${conv.conversation_id}')" title="Rename">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>
                        </button>
                        <button class="action-btn delete" onclick="event.stopPropagation(); conversationManager.deleteConversation('${conv.conversation_id}')" title="Delete">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async selectConversation(conversationId) {
        try {
            this.currentConversationId = conversationId;

            // Update UI
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.toggle('active', item.dataset.id === conversationId);
            });

            const response = await fetch(`/api/conversations/${conversationId}?include_messages=true`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Failed to load conversation:', response.status, errorText);
                throw new Error('Failed to load conversation');
            }

            const conversation = await response.json();
            console.log('Conversation response:', conversation);
            this.currentMessages = conversation.messages || [];
            
            console.log('Loaded conversation:', conversationId, 'Messages:', this.currentMessages.length);
            if (this.currentMessages.length > 0) {
                console.log('First message:', this.currentMessages[0]);
            }

            // Update title with metrics
            const titleEl = document.getElementById('current-conversation-title');
            if (titleEl) {
                const cost = conversation.total_cost_usd || 0;
                const tasks = conversation.total_tasks || 0;
                const duration = conversation.total_duration_seconds || 0;
                const durationFormatted = duration > 0 ? this.formatDuration(duration) : '';
                const metricsText = tasks > 0 ? ` | $${cost.toFixed(4)} | ${tasks} tasks${durationFormatted ? ' | ' + durationFormatted : ''}` : '';
                titleEl.textContent = conversation.title + metricsText;
            }

            this.enableChatInput();
            
            // Render messages and ensure scroll happens
            setTimeout(() => {
                this.renderMessages();
            }, 50);
        } catch (error) {
            console.error('Error selecting conversation:', error);
            this.showError('Failed to load conversation');
        }
    }

    renderMessages() {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) {
            console.error('chat-messages container not found');
            return;
        }

        console.log('Rendering messages:', this.currentMessages.length, this.currentMessages);

        if (this.currentMessages.length === 0) {
            messagesContainer.innerHTML = '<p class="welcome-message">Start the conversation by sending a message below.</p>';
            return;
        }

        const html = this.currentMessages.map(msg => {
            if (!msg || !msg.role || !msg.content) {
                console.warn('Invalid message format:', msg);
                return '';
            }
            
            const roleClass = msg.role === 'user' ? 'user-message' : 'assistant-message';
            const roleLabel = msg.role === 'user' ? 'You' : 'Brain';

            return `
                <div class="message ${roleClass}">
                    <div class="message-header">
                        <span class="message-role">${roleLabel}</span>
                        <span class="message-time">${this.formatTime(msg.created_at)}</span>
                    </div>
                    <div class="message-content">${this.formatMessageContent(msg.content)}</div>
                    ${msg.task_id ? `<div class="message-task-link"><a href="#" onclick="app.viewTask('${msg.task_id}'); return false;">View Task: ${msg.task_id}</a></div>` : ''}
                </div>
            `;
        }).join('');

        messagesContainer.innerHTML = html;

        // Scroll to bottom with multiple attempts to ensure it works
        const scrollToBottom = () => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        };

        // Use requestAnimationFrame for better timing
        requestAnimationFrame(() => {
            scrollToBottom();
            // Also try after a short delay to catch any layout changes
            setTimeout(() => {
                scrollToBottom();
            }, 50);
            // Final attempt after images/content might load
            setTimeout(() => {
                scrollToBottom();
            }, 200);
        });
    }

    async createNewConversation() {
        if (typeof app !== 'undefined' && app.showInputModal) {
            app.showInputModal(
                'INITIALIZE_COMMS',
                'CHANNEL_IDENTIFIER:',
                `Conversation ${new Date().toLocaleDateString()}`,
                'Enter title...',
                async (title) => {
                    await this._performCreate(title);
                }
            );
        } else {
            const title = prompt('Enter conversation title:', `Conversation ${new Date().toLocaleDateString()}`);
            if (title) await this._performCreate(title);
        }
    }

    async _performCreate(title) {
        try {
            const response = await fetch('/api/conversations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title,
                    user_id: 'default-user'
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to create conversation');
            }

            const newConv = await response.json();
            this.conversations.unshift(newConv);
            this.renderConversationList();
            await this.selectConversation(newConv.conversation_id);

            this.showSuccess('Conversation initialized');
        } catch (error) {
            console.error('Error creating conversation:', error);
            this.showError(`Init failed: ${error.message}`);
        }
    }

    async renameConversation(conversationId) {
        const conv = this.conversations.find(c => c.conversation_id === conversationId);
        if (!conv) return;

        if (typeof app !== 'undefined' && app.showInputModal) {
            app.showInputModal(
                'REDEFINE_IDENTIFIER',
                'NEW_TITLE:',
                conv.title,
                'Enter new title...',
                async (newTitle) => {
                    await this._performRename(conversationId, newTitle);
                }
            );
        } else {
            const newTitle = prompt('Enter new title:', conv.title);
            if (newTitle && newTitle !== conv.title) {
                await this._performRename(conversationId, newTitle);
            }
        }
    }

    async _performRename(conversationId, newTitle) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });

            if (!response.ok) throw new Error('Failed to rename conversation');

            const conv = this.conversations.find(c => c.conversation_id === conversationId);
            if (conv) conv.title = newTitle;

            this.renderConversationList();

            if (conversationId === this.currentConversationId) {
                const titleEl = document.getElementById('current-conversation-title');
                if (titleEl) titleEl.textContent = newTitle;
            }

            this.showSuccess('Identifier updated');
        } catch (error) {
            console.error('Error renaming conversation:', error);
            this.showError('Rename failed');
        }
    }

    async deleteConversation(conversationId) {
        console.log('Deleting conversation:', conversationId);
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            console.log('Delete response status:', response.status);

            if (!response.ok) throw new Error('Failed to delete conversation');

            const initialCount = this.conversations.length;
            this.conversations = this.conversations.filter(c => c.conversation_id !== conversationId);
            console.log(`Filtered conversations: ${initialCount} -> ${this.conversations.length}`);

            this.renderConversationList();

            if (conversationId === this.currentConversationId) {
                this.currentConversationId = null;
                this.currentMessages = [];

                if (this.conversations.length > 0) {
                    await this.selectConversation(this.conversations[0].conversation_id);
                } else {
                    this.enableChatInput();
                    document.getElementById('chat-messages').innerHTML = '<p class="welcome-message">No conversations. Type a message and click EXECUTE to start a new conversation!</p>';
                    const titleEl = document.getElementById('current-conversation-title');
                    if (titleEl) titleEl.textContent = 'Select Channel';
                }
            }

            this.showSuccess('Conversation deleted');
        } catch (error) {
            console.error('Error deleting conversation:', error);
            this.showError('Failed to delete conversation');
        }
    }

    async clearCurrentConversation() {
        if (!this.currentConversationId) return;

        if (!confirm('Clear all messages in this conversation?')) {
            return;
        }

        try {
            const response = await fetch(`/api/conversations/${this.currentConversationId}/clear`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to clear conversation');
            }

            this.currentMessages = [];
            this.renderMessages();

            // Update conversation list
            const conv = this.conversations.find(c => c.conversation_id === this.currentConversationId);
            if (conv) {
                conv.message_count = 0;
                this.renderConversationList();
            }

            this.showSuccess('History cleared');
        } catch (error) {
            console.error('Error clearing conversation:', error);
            this.showError(`Clear failed: ${error.message}`);
        }
    }

    async sendMessage(message) {
        if (!this.currentConversationId) {
            return null;
        }

        const userMessage = {
            role: 'user',
            content: message,
            created_at: new Date().toISOString()
        };
        this.currentMessages.push(userMessage);
        this.renderMessages();

        return this.currentConversationId;
    }

    async addAssistantMessage(content, taskId) {
        if (!this.currentConversationId) return;

        try {
            const response = await fetch(`/api/conversations/${this.currentConversationId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    role: 'assistant',
                    content: content,
                    task_id: taskId
                })
            });

            if (!response.ok) throw new Error('Failed to add message');

            const message = await response.json();
            this.currentMessages.push(message);
            this.renderMessages();
        } catch (error) {
            console.error('Error adding assistant message:', error);
        }
    }

    enableChatInput() {
        const input = document.getElementById('chat-input');
        const button = document.getElementById('send-button');
        if (input) input.disabled = false;
        if (button) button.disabled = false;
    }

    disableChatInput() {
        const input = document.getElementById('chat-input');
        const button = document.getElementById('send-button');
        if (input) input.disabled = true;
        if (button) button.disabled = true;
    }

    formatMessageContent(content) {
        // Basic markdown-like formatting
        return this.escapeHtml(content)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    formatTime(dateStr) {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return '';
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            console.error('Error formatting time:', dateStr, e);
            return '';
        }
    }

    formatDuration(seconds) {
        if (seconds < 60) return `${seconds.toFixed(1)}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${mins}m`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Global instance
const conversationManager = new ConversationManager();
