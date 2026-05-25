document.addEventListener("DOMContentLoaded", () => {
    // Only run this logic if we are on the group page
    if (typeof window.GROUP_ID !== 'undefined') {
        const chatMessages = document.getElementById('chat-messages');
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');
        
        // Scroll to bottom on load
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);

        // Construct WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${window.GROUP_ID}/${window.USERNAME}`;
        
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        const reconnectDelay = 3000;

        function connectWebSocket() {
            try {
                ws = new WebSocket(wsUrl);

                ws.onopen = function(event) {
                    console.log("WebSocket connected");
                    reconnectAttempts = 0;
                };

                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        appendMessage(data.username, data.content);
                    } catch(e) {
                        console.error("Error parsing message:", e);
                    }
                };

                ws.onerror = function(event) {
                    console.error("WebSocket error:", event);
                };

                ws.onclose = function(event) {
                    console.log("WebSocket closed. Attempting to reconnect...");
                    if (reconnectAttempts < maxReconnectAttempts) {
                        reconnectAttempts++;
                        setTimeout(connectWebSocket, reconnectDelay);
                    } else {
                        showConnectionError();
                    }
                };
            } catch(e) {
                console.error("WebSocket connection error:", e);
            }
        }

        connectWebSocket();

        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            
            // Validation
            if (!message) {
                messageInput.focus();
                return;
            }

            if (message.length > 2000) {
                alert('Message is too long (max 2000 characters)');
                return;
            }

            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(message);
                messageInput.value = '';
                messageInput.focus();
            } else {
                alert('Connection lost. Please wait for reconnection...');
            }
        });

        function appendMessage(username, content) {
            const isMine = username === window.USERNAME;
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isMine ? 'my-message' : 'other-message'}`;
            
            let html = '';
            if (!isMine) {
                html += `<div class="msg-author">${escapeHtml(username)}</div>`;
            }
            
            html += `<div class="msg-bubble">${escapeHtml(content)}</div>`;
            
            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                           now.getMinutes().toString().padStart(2, '0');
            html += `<div class="msg-time">${timeStr}</div>`;
            
            messageDiv.innerHTML = html;
            
            // Remove empty state if it exists
            const emptyState = chatMessages.querySelector('.empty-chat');
            if (emptyState) {
                emptyState.remove();
            }
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function escapeHtml(unsafe) {
            return unsafe
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        }

        function showConnectionError() {
            const errorDiv = document.createElement('div');
            errorDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #dc2626;
                color: white;
                padding: 1rem;
                border-radius: 8px;
                z-index: 1000;
            `;
            errorDiv.textContent = 'Connection lost. Please refresh the page.';
            document.body.appendChild(errorDiv);
        }
    }
});
