// Chat Interface JavaScript for Family Wiki RAG System

class ChatInterface {
    constructor() {
        this.conversationId = null;
        this.isLoading = false;
        this.messageSequence = 1;
        this.chatForm = document.getElementById('chat-form');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatTextarea = document.getElementById('chat-textarea');
        this.sendButton = document.getElementById('send-button');
        this.newConversationBtn = document.getElementById('new-conversation-btn');
        this.clearChatBtn = document.getElementById('clear-chat-btn');
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.adjustTextareaHeight();
        this.focusInput();
    }
    
    bindEvents() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Auto-resize textarea
        this.chatTextarea.addEventListener('input', () => {
            this.adjustTextareaHeight();
        });
        
        // Send on Ctrl+Enter
        this.chatTextarea.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // New conversation button
        if (this.newConversationBtn) {
            this.newConversationBtn.addEventListener('click', () => {
                this.startNewConversation();
            });
        }
        
        // Clear chat button  
        if (this.clearChatBtn) {
            this.clearChatBtn.addEventListener('click', () => {
                this.clearChat();
            });
        }
    }
    
    adjustTextareaHeight() {
        const textarea = this.chatTextarea;
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }
    
    focusInput() {
        this.chatTextarea.focus();
    }
    
    async sendMessage() {
        const question = this.chatTextarea.value.trim();
        if (!question || this.isLoading) return;
        
        const corpusId = document.getElementById('corpus_id').value;
        const promptId = document.getElementById('prompt_id').value;
        const similarityThreshold = document.getElementById('similarity_threshold').value;
        
        if (!corpusId || !promptId) {
            this.showError('Please select a corpus and prompt before asking a question.');
            return;
        }
        
        // Add user message to chat
        this.addMessage('user', question);
        
        // Clear input and disable form
        this.chatTextarea.value = '';
        this.adjustTextareaHeight();
        this.setLoading(true);
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await this.submitQuestion(question, corpusId, promptId, similarityThreshold);
            this.handleResponse(response);
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
        } finally {
            this.setLoading(false);
            this.hideTypingIndicator();
            this.focusInput();
        }
    }
    
    async submitQuestion(question, corpusId, promptId, similarityThreshold) {
        const formData = new FormData();
        formData.append('question', question);
        formData.append('corpus_id', corpusId);
        formData.append('prompt_id', promptId);
        formData.append('similarity_threshold', similarityThreshold);
        
        // Add conversation context if available
        if (this.conversationId) {
            formData.append('conversation_id', this.conversationId);
            formData.append('message_sequence', this.messageSequence);
        }
        
        const response = await fetch('/rag/chat/ask', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    handleResponse(data) {
        if (data.success) {
            // Set conversation ID if this is the first message
            if (!this.conversationId && data.conversation_id) {
                this.conversationId = data.conversation_id;
            }
            
            // Add assistant response to chat
            this.addMessage('assistant', data.answer, {
                sources: data.retrieved_chunks || [],
                similarities: data.similarity_scores || [],
                chunkCount: data.retrieved_chunks ? data.retrieved_chunks.length : 0,
                avgSimilarity: data.similarity_scores && data.similarity_scores.length > 0 
                    ? (data.similarity_scores.reduce((a, b) => a + b, 0) / data.similarity_scores.length).toFixed(2)
                    : null
            });
            
            this.messageSequence += 2; // Increment by 2 (user + assistant)
        } else {
            this.showError(data.error || 'An error occurred while processing your question.');
        }
    }
    
    addMessage(sender, content, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} message-enter`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let sourcesHtml = '';
        if (sender === 'assistant' && metadata.sources && metadata.sources.length > 0) {
            sourcesHtml = `
                <div class="message-sources">
                    <h6>Sources (${metadata.chunkCount} chunks, avg similarity: ${metadata.avgSimilarity})</h6>
                    <ul class="source-list">
                        ${metadata.sources.map((source, index) => `
                            <li class="source-item">
                                <span>${source}</span>
                                ${metadata.similarities && metadata.similarities[index] 
                                    ? `<span class="source-similarity">${(metadata.similarities[index]).toFixed(2)}</span>`
                                    : ''
                                }
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }
        
        messageDiv.innerHTML = `
            <div class="message-bubble">${this.formatMessageContent(content)}</div>
            <div class="message-meta">
                <span class="message-timestamp">${timestamp}</span>
            </div>
            ${sourcesHtml}
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Remove the empty state if it exists
        const emptyState = document.querySelector('.conversation-empty');
        if (emptyState) {
            emptyState.remove();
        }
    }
    
    formatMessageContent(content) {
        // Basic HTML escaping and line break handling
        return content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <span>Assistant is thinking...</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message assistant message-enter';
        errorDiv.innerHTML = `
            <div class="message-bubble" style="background: #f8d7da; color: #721c24; border-color: #f5c6cb;">
                ⚠️ ${message}
            </div>
            <div class="message-meta">
                <span class="message-timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        `;
        
        this.chatMessages.appendChild(errorDiv);
        this.scrollToBottom();
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.sendButton.textContent = loading ? 'Sending...' : 'Send';
        this.chatTextarea.disabled = loading;
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    startNewConversation() {
        this.conversationId = null;
        this.messageSequence = 1;
        this.clearChat();
        this.showEmptyState();
        this.focusInput();
    }
    
    clearChat() {
        this.chatMessages.innerHTML = '';
    }
    
    showEmptyState() {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'conversation-empty';
        emptyDiv.innerHTML = `
            <h3>Start a Conversation</h3>
            <p>Ask questions about your family history corpus. You can ask follow-up questions and I'll remember the context of our conversation.</p>
        `;
        
        this.chatMessages.appendChild(emptyDiv);
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the chat page
    if (document.getElementById('chat-form')) {
        const chat = new ChatInterface();
        window.familyWikiChat = chat; // Make it globally accessible for debugging
    }
});

// Helper function to format timestamps
function formatTimestamp(date) {
    return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
    });
}

// Helper function to validate form inputs
function validateChatForm() {
    const corpusId = document.getElementById('corpus_id')?.value;
    const promptId = document.getElementById('prompt_id')?.value;
    
    if (!corpusId) {
        alert('Please select a corpus to query.');
        return false;
    }
    
    if (!promptId) {
        alert('Please select a RAG prompt to use.');
        return false;
    }
    
    return true;
}