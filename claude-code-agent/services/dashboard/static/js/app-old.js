// Dashboard Application

class DashboardApp {
    constructor() {
        this.ws = null;
        this.sessionId = this.generateSessionId();
        this.tasks = new Map();

        this.init();
    }

    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    async init() {
        await this.loadStatus();
        this.connectWebSocket();
        this.setupEventListeners();
        this.startStatusPolling();
    }

    async loadStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            document.getElementById('machine-id').textContent = data.machine_id;
            document.getElementById('queue-length').textContent = data.queue_length;
            document.getElementById('active-sessions').textContent = data.sessions;
            document.getElementById('connections').textContent = data.connections;
            document.getElementById('machine-status').classList.add('online');
        } catch (error) {
            console.error('Failed to load status:', error);
            document.getElementById('machine-status').classList.add('offline');
        }
    }

    startStatusPolling() {
        setInterval(() => this.loadStatus(), 5000);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.sessionId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(message) {
        switch (message.type) {
            case 'task.created':
                this.addTask(message);
                break;
            case 'task.output':
                this.updateTaskOutput(message.task_id, message.chunk);
                break;
            case 'task.metrics':
                this.updateTaskMetrics(message.task_id, message);
                break;
            case 'task.completed':
                this.completeTask(message.task_id, message.result, message.cost_usd);
                break;
            case 'task.failed':
                this.failTask(message.task_id, message.error);
                break;
        }
    }

    addTask(data) {
        this.tasks.set(data.task_id, {
            id: data.task_id,
            agent: data.agent,
            status: data.status,
            output: '',
            cost: 0
        });
        this.renderTasks();
    }

    updateTaskOutput(taskId, chunk) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.output += chunk;
            this.renderTaskOutput(taskId);
        }
    }

    updateTaskMetrics(taskId, metrics) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.cost = metrics.cost_usd;
            this.renderTasks();
        }
    }

    completeTask(taskId, result, cost) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'completed';
            task.result = result;
            task.cost = cost;
            this.renderTasks();
            // Show the actual result in chat
            if (result) {
                this.addChatMessage('assistant', result);
            }
            this.addChatMessage('assistant', `✅ Task completed! Cost: $${cost.toFixed(4)}`);
        }
    }

    failTask(taskId, error) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'failed';
            task.error = error;
            this.renderTasks();
            this.addChatMessage('assistant', `Task ${taskId} failed: ${error}`);
        }
    }

    renderTasks() {
        const container = document.getElementById('tasks-list');

        if (this.tasks.size === 0) {
            container.innerHTML = '<p class="empty-state">No active tasks</p>';
            return;
        }

        container.innerHTML = '';

        for (const [taskId, task] of this.tasks) {
            const el = document.createElement('div');
            el.className = `task-card status-${task.status}`;
            el.innerHTML = `
                <div class="task-header">
                    <span class="task-id">${taskId}</span>
                    <span class="task-agent">${task.agent}</span>
                    <span class="task-cost">$${task.cost.toFixed(4)}</span>
                </div>
                <div class="task-status">${task.status}</div>
                <div class="task-actions">
                    <button onclick="app.viewTask('${taskId}')">View</button>
                    ${task.status === 'running' ? `<button onclick="app.stopTask('${taskId}')">Stop</button>` : ''}
                </div>
            `;
            container.appendChild(el);
        }
    }

    renderTaskOutput(taskId) {
        const outputEl = document.getElementById(`task-output-${taskId}`);
        if (outputEl) {
            const task = this.tasks.get(taskId);
            outputEl.textContent = task.output;
            outputEl.scrollTop = outputEl.scrollHeight;
        }
    }

    setupEventListeners() {
        document.getElementById('send-button').onclick = () => this.sendMessage();

        document.getElementById('chat-input').onkeypress = (e) => {
            if (e.key === 'Enter') this.sendMessage();
        };
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message) return;

        // Add to chat display
        this.addChatMessage('user', message);
        input.value = '';

        try {
            // Send via API
            const response = await fetch(`/api/chat?session_id=${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: 'chat.message',
                    message: message
                })
            });

            const data = await response.json();

            if (data.success) {
                const taskId = data.data.task_id;
                this.addChatMessage('assistant', `Task created: ${taskId}`);

                // Add task to local tracking so we can receive WebSocket updates
                this.tasks.set(taskId, {
                    id: taskId,
                    agent: 'brain',
                    status: 'pending',
                    output: '',
                    cost: 0
                });
                this.renderTasks();
            } else {
                this.addChatMessage('assistant', `Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            this.addChatMessage('assistant', 'Failed to send message');
        }
    }

    addChatMessage(role, content) {
        const container = document.getElementById('chat-messages');

        // Remove welcome message if present
        const welcome = container.querySelector('.welcome-message');
        if (welcome) {
            welcome.remove();
        }

        const el = document.createElement('div');
        el.className = `chat-message ${role}`;
        el.textContent = content;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
    }

    async stopTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });
            const data = await response.json();
            if (data.success) {
                this.addChatMessage('assistant', `Task ${taskId} stopped`);
            }
        } catch (error) {
            console.error('Failed to stop task:', error);
        }
    }

    async viewTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const task = await response.json();

            document.getElementById('modal-body').innerHTML = `
                <h3>Task: ${task.task_id}</h3>
                <p><strong>Agent:</strong> ${task.assigned_agent}</p>
                <p><strong>Status:</strong> ${task.status}</p>
                <p><strong>Cost:</strong> $${task.cost_usd.toFixed(4)}</p>
                <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
                <h4>Input:</h4>
                <div class="task-input">${task.input_message}</div>
                <h4>Output:</h4>
                <div class="task-output" id="task-output-${taskId}">${task.output_stream}</div>
                ${task.error ? `<h4>Error:</h4><div class="task-error">${task.error}</div>` : ''}
            `;
            document.getElementById('modal').classList.remove('hidden');
        } catch (error) {
            console.error('Failed to load task:', error);
        }
    }
}

// Modal functions
function hideModal() {
    document.getElementById('modal').classList.add('hidden');
}

// Initialize app
const app = new DashboardApp();
