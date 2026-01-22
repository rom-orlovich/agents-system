// Enhanced Dashboard Application with Analytics, Credentials, and Registry

class DashboardApp {
    constructor() {
        this.ws = null;
        this.sessionId = this.generateSessionId();
        this.tasks = new Map();
        this.currentTab = 'overview';
        this.currentPage = 1;
        this.pageSize = 20;
        this.sortBy = 'created_at';
        this.sortOrder = 'desc';
        this.filters = {
            session_id: null,
            status: null,
            subagent: null
        };
        this.charts = {
            dailyCosts: null,
            subagentCosts: null
        };

        this.init();
    }

    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    async init() {
        this.setupEventListeners();
        await this.connectWebSocket();
        await this.loadStatus();
        this.startStatusPolling();
        this.loadSubagents();

        // Initialize conversation manager when available
        if (typeof conversationManager !== 'undefined') {
            await conversationManager.init();
        }
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

    async loadAnalyticsSummary() {
        try {
            const response = await fetch('/api/analytics/summary');
            const data = await response.json();

            document.getElementById('today-cost').textContent = `$${data.today_cost.toFixed(2)}`;
            document.getElementById('total-tasks').textContent = data.total_tasks;
            document.getElementById('total-cost').textContent = `$${data.total_cost.toFixed(2)}`;
        } catch (error) {
            console.error('Failed to load analytics summary:', error);
        }
    }

    startStatusPolling() {
        setInterval(() => {
            this.loadStatus();
            this.loadAnalyticsSummary();

            // Auto-refresh webhook events if on webhooks tab
            if (this.currentTab === 'webhooks') {
                this.loadWebhookEvents();
                this.loadWebhookStatus();
            }
        }, 5000);
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

    async completeTask(taskId, result, cost) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'completed';
            task.result = result;
            task.cost = cost;
            this.renderTasks();

            // Add to conversation if tracked
            if (this.taskConversationMap && this.taskConversationMap.has(taskId)) {
                const conversationId = this.taskConversationMap.get(taskId);
                if (typeof conversationManager !== 'undefined') {
                    const fullResponse = result
                        ? `${result}\n\n✅ Task completed! Cost: $${cost.toFixed(4)}`
                        : `✅ Task completed! Cost: $${cost.toFixed(4)}`;
                    await conversationManager.addAssistantMessage(fullResponse, taskId);
                    this.taskConversationMap.delete(taskId);
                    return;
                }
            }

            // Fallback to old behavior
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
            this.addChatMessage('assistant', `❌ Task ${taskId} failed: ${error}`);
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

        // Task table filters
        document.getElementById('filter-session').oninput = (e) => {
            this.filters.session_id = e.target.value || null;
            this.currentPage = 1;
            this.refreshTaskTable();
        };
        document.getElementById('filter-status').onchange = (e) => {
            this.filters.status = e.target.value || null;
            this.currentPage = 1;
            this.refreshTaskTable();
        };
        document.getElementById('filter-subagent').onchange = (e) => {
            this.filters.subagent = e.target.value || null;
            this.currentPage = 1;
            this.refreshTaskTable();
        };

        // Skill upload form
        const skillForm = document.getElementById('skill-upload-form');
        if (skillForm) {
            skillForm.onsubmit = (e) => {
                e.preventDefault();
                this.uploadSkill();
            };
        }

        // Agent upload form
        const agentForm = document.getElementById('agent-upload-form');
        if (agentForm) {
            agentForm.onsubmit = (e) => {
                e.preventDefault();
                this.uploadAgent();
            };
        }

        // Webhook create form
        const webhookForm = document.getElementById('webhook-create-form');
        if (webhookForm) {
            webhookForm.onsubmit = (e) => {
                e.preventDefault();
                this.createWebhook(e);
            };
        }
    }

    // Tab Switching
    async switchTab(tabName) {
        this.currentTab = tabName;

        if (tabName === 'webhooks') {
            await this.refreshWebhookStatus();
        } else if (tabName === 'analytics') {
            await this.loadDailyCostsChart();
            await this.loadSubagentCostsChart();
        }

        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');
    }

    async loadDailyCostsChart() {
        try {
            const response = await fetch('/api/analytics/costs/daily?days=30');
            const data = await response.json();

            const ctx = document.getElementById('daily-costs-chart').getContext('2d');

            if (this.charts.dailyCosts) {
                this.charts.dailyCosts.destroy();
            }

            this.charts.dailyCosts = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Cost (USD)',
                        data: data.costs,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: (value) => `$${value.toFixed(2)}`
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Failed to load daily costs chart:', error);
        }
    }

    async loadSubagentCostsChart() {
        try {
            const response = await fetch('/api/analytics/costs/by-subagent?days=30');
            const data = await response.json();

            const ctx = document.getElementById('subagent-costs-chart').getContext('2d');

            if (this.charts.subagentCosts) {
                this.charts.subagentCosts.destroy();
            }

            this.charts.subagentCosts = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.subagents,
                    datasets: [{
                        data: data.costs,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)',
                            'rgba(255, 159, 64, 0.8)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return `${context.label}: $${context.parsed.toFixed(2)}`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Failed to load subagent costs chart:', error);
        }
    }

    // Task Table
    async refreshTaskTable() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.pageSize,
                sort_by: this.sortBy,
                sort_order: this.sortOrder
            });

            if (this.filters.session_id) params.append('session_id', this.filters.session_id);
            if (this.filters.status) params.append('status', this.filters.status);
            if (this.filters.subagent) params.append('subagent', this.filters.subagent);

            const response = await fetch(`/api/tasks/table?${params}`);
            const data = await response.json();

            this.renderTaskTable(data);
        } catch (error) {
            console.error('Failed to load task table:', error);
        }
    }

    renderTaskTable(data) {
        const tbody = document.getElementById('tasks-table-body');

        if (data.tasks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No tasks found</td></tr>';
            return;
        }

        tbody.innerHTML = data.tasks.map(task => `
            <tr onclick="app.viewTask('${task.task_id}')" style="cursor: pointer;">
                <td>${task.task_id}</td>
                <td>${task.session_id.substring(0, 12)}...</td>
                <td>${task.assigned_agent || 'N/A'}</td>
                <td><span class="status-badge status-${task.status}">${task.status}</span></td>
                <td>$${task.cost_usd.toFixed(4)}</td>
                <td>${task.duration_seconds ? `${task.duration_seconds}s` : 'N/A'}</td>
                <td>${new Date(task.created_at).toLocaleString()}</td>
            </tr>
        `).join('');

        // Update pagination
        document.getElementById('page-info').textContent = `Page ${data.page} of ${data.total_pages}`;
        document.getElementById('prev-page-btn').disabled = data.page <= 1;
        document.getElementById('next-page-btn').disabled = data.page >= data.total_pages;
    }

    sortTable(column) {
        if (this.sortBy === column) {
            this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortBy = column;
            this.sortOrder = 'desc';
        }
        this.refreshTaskTable();
    }

    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.refreshTaskTable();
        }
    }

    nextPage() {
        this.currentPage++;
        this.refreshTaskTable();
    }

    // Credentials Management
    async showCredentials() {
        // Load status first to check if we should show the modal
        try {
            const response = await fetch('/api/credentials/status');
            const data = await response.json();

            // Only show modal if:
            // 1. CLI is unavailable, OR
            // 2. Credentials are expired, OR
            // 3. Rate limited, OR
            // 4. User explicitly wants to see it (always show on button click)
            const shouldShow = !data.cli_available ||
                data.status === 'expired' ||
                data.status === 'rate_limited' ||
                data.status === 'cli_unavailable';

            if (shouldShow || event?.isTrusted) {
                // Show modal if there's an issue OR user clicked the button
                document.getElementById('credentials-modal').classList.remove('hidden');
                await this.loadCredentialStatus();
            } else if (data.status === 'valid') {
                // If credentials are valid, just show a success message
                alert(`✅ Credentials are valid!\n\nAccount: ${data.account_email}\nExpires: ${new Date(data.expires_at).toLocaleString()}`);
            }
        } catch (error) {
            console.error('Failed to check credentials:', error);
            // On error, show the modal
            document.getElementById('credentials-modal').classList.remove('hidden');
            await this.loadCredentialStatus();
        }
    }

    hideCredentials() {
        document.getElementById('credentials-modal').classList.add('hidden');
    }

    async loadCredentialStatus() {
        try {
            const response = await fetch('/api/credentials/status');
            const data = await response.json();

            const statusDisplay = document.getElementById('cred-status-display');
            const statusClass = data.status.replace('_', '-');

            statusDisplay.innerHTML = `
                <div class="cred-status ${statusClass}">
                    <strong>Status:</strong> ${data.status.toUpperCase()}<br>
                    <strong>Message:</strong> ${data.message}<br>
                    ${data.cli_available ? `<strong>CLI Version:</strong> ${data.cli_version || 'Unknown'}<br>` : ''}
                    ${data.account_email ? `<strong>Account:</strong> ${data.account_email}<br>` : ''}
                    ${data.account_id ? `<strong>User ID:</strong> ${data.account_id}<br>` : ''}
                    ${data.expires_at ? `<strong>Expires:</strong> ${new Date(data.expires_at).toLocaleString()}` : ''}
                </div>
            `;
        } catch (error) {
            console.error('Failed to load credential status:', error);
            document.getElementById('cred-status-display').innerHTML = '<p class="error">Failed to load status</p>';
        }
    }

    async uploadCredentials() {
        const fileInput = document.getElementById('cred-file-input');
        const file = fileInput.files[0];

        if (!file) {
            alert('Please select a file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/credentials/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                alert('Credentials uploaded successfully!');
                await this.loadCredentialStatus();
                fileInput.value = '';
            } else {
                alert(`Upload failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to upload credentials:', error);
            alert('Upload failed: Network error');
        }
    }

    // Registry Management
    async showRegistry() {
        document.getElementById('registry-modal').classList.remove('hidden');
        await this.loadSkills();
        await this.loadAgents();
    }

    hideRegistry() {
        document.getElementById('registry-modal').classList.add('hidden');
    }

    switchRegistryTab(tab) {
        document.querySelectorAll('.registry-tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.registry-content').forEach(content => {
            content.classList.remove('active');
        });

        event.target.classList.add('active');
        document.getElementById(`registry-${tab}`).classList.add('active');
    }

    async loadSkills() {
        try {
            const response = await fetch('/api/registry/skills');
            const skills = await response.json();

            const container = document.getElementById('skills-list');

            if (skills.length === 0) {
                container.innerHTML = '<p class="empty-state">No skills found</p>';
                return;
            }

            container.innerHTML = skills.map(skill => `
                <div class="registry-item">
                    <div class="registry-item-header">
                        <h4>${skill.name}</h4>
                        ${skill.is_builtin ? '<span class="badge">Built-in</span>' : `<button onclick="app.deleteSkill('${skill.name}')" class="delete-btn">Delete</button>`}
                    </div>
                    <p>${skill.description}</p>
                    <small>Path: ${skill.path}</small>
                    ${skill.has_scripts ? '<span class="badge">Has Scripts</span>' : ''}
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load skills:', error);
            document.getElementById('skills-list').innerHTML = '<p class="error">Failed to load skills</p>';
        }
    }

    async loadAgents() {
        try {
            const response = await fetch('/api/registry/agents');
            const agents = await response.json();

            const container = document.getElementById('agents-list');

            if (agents.length === 0) {
                container.innerHTML = '<p class="empty-state">No agents found</p>';
                return;
            }

            container.innerHTML = agents.map(agent => `
                <div class="registry-item">
                    <div class="registry-item-header">
                        <h4>${agent.name}</h4>
                        ${agent.is_builtin ? '<span class="badge">Built-in</span>' : `<button onclick="app.deleteAgent('${agent.name}')" class="delete-btn">Delete</button>`}
                    </div>
                    <p>${agent.description}</p>
                    <small>Type: ${agent.agent_type} | Path: ${agent.path}</small>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load agents:', error);
            document.getElementById('agents-list').innerHTML = '<p class="error">Failed to load agents</p>';
        }
    }

    showSkillUpload() {
        document.getElementById('skill-upload-modal').classList.remove('hidden');
    }

    hideSkillUpload() {
        document.getElementById('skill-upload-modal').classList.add('hidden');
    }

    async uploadSkill() {
        const name = document.getElementById('skill-name').value;
        const filesInput = document.getElementById('skill-files');
        const files = filesInput.files;

        if (!name || files.length === 0) {
            alert('Please provide skill name and files');
            return;
        }

        const formData = new FormData();
        formData.append('name', name);

        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch('/api/registry/skills/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                alert('Skill uploaded successfully!');
                this.hideSkillUpload();
                await this.loadSkills();
                document.getElementById('skill-upload-form').reset();
            } else {
                alert(`Upload failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to upload skill:', error);
            alert('Upload failed: Network error');
        }
    }

    async deleteSkill(skillName) {
        if (!confirm(`Delete skill "${skillName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/registry/skills/${skillName}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                alert('Skill deleted successfully!');
                await this.loadSkills();
            } else {
                alert(`Delete failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to delete skill:', error);
            alert('Delete failed: Network error');
        }
    }

    showAgentUpload() {
        document.getElementById('agent-upload-modal').classList.remove('hidden');
    }

    hideAgentUpload() {
        document.getElementById('agent-upload-modal').classList.add('hidden');
    }

    async uploadAgent() {
        const name = document.getElementById('agent-name').value;
        const filesInput = document.getElementById('agent-files');
        const files = filesInput.files;

        if (!name || files.length === 0) {
            alert('Please provide agent name and files');
            return;
        }

        const formData = new FormData();
        formData.append('name', name);

        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch('/api/registry/agents/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                alert('Agent uploaded successfully!');
                this.hideAgentUpload();
                await this.loadAgents();
                document.getElementById('agent-upload-form').reset();
            } else {
                alert(`Upload failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to upload agent:', error);
            alert('Upload failed: Network error');
        }
    }

    async deleteAgent(agentName) {
        if (!confirm(`Delete agent "${agentName}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/registry/agents/${agentName}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                alert('Agent deleted successfully!');
                await this.loadAgents();
            } else {
                alert(`Delete failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to delete agent:', error);
            alert('Delete failed: Network error');
        }
    }

    // Chat
    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();

        if (!message) return;

        // Use conversation manager if available
        let conversationId = null;
        if (typeof conversationManager !== 'undefined') {
            conversationId = await conversationManager.sendMessage(message);
            if (!conversationId) return; // Conversation manager will show error
        } else {
            this.addChatMessage('user', message);
        }

        input.value = '';

        try {
            const url = conversationId
                ? `/api/chat?session_id=${this.sessionId}&conversation_id=${conversationId}`
                : `/api/chat?session_id=${this.sessionId}`;

            const response = await fetch(url, {
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

                this.tasks.set(taskId, {
                    id: taskId,
                    agent: 'brain',
                    status: 'pending',
                    output: '',
                    cost: 0
                });
                this.renderTasks();

                // Track task for conversation updates
                if (conversationId && typeof conversationManager !== 'undefined') {
                    this.trackTaskForConversation(taskId, conversationId);
                }
            } else {
                const errorMsg = `Error: ${data.message}`;
                if (typeof conversationManager !== 'undefined' && conversationId) {
                    await conversationManager.addAssistantMessage(errorMsg, null);
                } else {
                    this.addChatMessage('assistant', errorMsg);
                }
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            const errorMsg = 'Failed to send message';
            if (typeof conversationManager !== 'undefined' && conversationId) {
                await conversationManager.addAssistantMessage(errorMsg, null);
            } else {
                this.addChatMessage('assistant', errorMsg);
            }
        }
    }

    trackTaskForConversation(taskId, conversationId) {
        // Store mapping for when task completes
        if (!this.taskConversationMap) {
            this.taskConversationMap = new Map();
        }
        this.taskConversationMap.set(taskId, conversationId);
    }

    addChatMessage(role, content) {
        const container = document.getElementById('chat-messages');

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

            const isRunning = task.status === 'running';

            document.getElementById('modal-body').innerHTML = `
                <h3>Task: ${task.task_id}</h3>
                <p><strong>Agent:</strong> ${task.assigned_agent}</p>
                <p><strong>Status:</strong> <span class="status-badge status-${task.status}">${task.status}</span></p>
                <p><strong>Cost:</strong> $${(task.cost_usd || 0).toFixed(4)}</p>
                <p><strong>Tokens:</strong> ${task.input_tokens || 0} in / ${task.output_tokens || 0} out</p>
                <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
                ${task.completed_at ? `<p><strong>Completed:</strong> ${new Date(task.completed_at).toLocaleString()}</p>` : ''}
                <h4>Input:</h4>
                <div class="task-input">${task.input_message || 'N/A'}</div>
                <h4>Logs: ${isRunning ? '<span class="live-indicator">🔴 LIVE</span>' : ''}</h4>
                <div class="logs-controls">
                    <button onclick="app.refreshTaskLogs('${taskId}')" class="refresh-btn-small">🔄 Refresh Logs</button>
                    ${isRunning ? '<span class="auto-refresh-notice">Auto-refreshing every 2s</span>' : ''}
                </div>
                <div class="task-logs" id="task-logs-${taskId}">Loading logs...</div>
                ${task.error ? `<h4>Error:</h4><div class="task-error">${task.error}</div>` : ''}
            `;
            document.getElementById('modal').classList.remove('hidden');

            // Load logs
            await this.refreshTaskLogs(taskId);

            // Auto-refresh logs for running tasks
            if (isRunning) {
                this.startTaskLogsPolling(taskId);
            }
        } catch (error) {
            console.error('Failed to load task:', error);
        }
    }

    async refreshTaskLogs(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/logs`);
            const data = await response.json();

            const logsElement = document.getElementById(`task-logs-${taskId}`);
            if (logsElement) {
                logsElement.innerHTML = `<pre>${data.output || 'No logs available'}</pre>`;
                // Auto-scroll to bottom
                logsElement.scrollTop = logsElement.scrollHeight;
            }
        } catch (error) {
            console.error('Failed to refresh task logs:', error);
            const logsElement = document.getElementById(`task-logs-${taskId}`);
            if (logsElement) {
                logsElement.innerHTML = '<p class="error">Failed to load logs</p>';
            }
        }
    }

    startTaskLogsPolling(taskId) {
        // Clear any existing interval
        if (this.logsPollingInterval) {
            clearInterval(this.logsPollingInterval);
        }

        // Poll every 2 seconds
        this.logsPollingInterval = setInterval(async () => {
            const logsElement = document.getElementById(`task-logs-${taskId}`);
            if (!logsElement) {
                // Modal closed, stop polling
                clearInterval(this.logsPollingInterval);
                this.logsPollingInterval = null;
                return;
            }

            await this.refreshTaskLogs(taskId);
        }, 2000);
    }

    hideModal() {
        document.getElementById('modal').classList.add('hidden');

        // Stop logs polling if active
        if (this.logsPollingInterval) {
            clearInterval(this.logsPollingInterval);
            this.logsPollingInterval = null;
        }
    }

    // Webhook Status & Monitoring
    async refreshWebhookStatus() {
        await this.loadWebhookStatus();
        await this.loadWebhooks();
        await this.loadWebhookEvents();
    }

    async loadWebhookStatus() {
        try {
            const statsResponse = await fetch('/api/webhooks/stats');
            const stats = await statsResponse.json();

            const webhooksResponse = await fetch('/api/webhooks');
            const webhooks = await webhooksResponse.json();

            // Fetch webhook status to get public domain
            const statusResponse = await fetch('/api/webhooks-status');
            const statusData = await statusResponse.json();
            const publicDomain = statusData.data?.public_domain || null;

            // Update stats
            document.getElementById('total-webhooks').textContent = stats.total_webhooks || 0;
            document.getElementById('active-webhooks').textContent = stats.active_webhooks || 0;

            // Display public domain or warning
            if (publicDomain) {
                document.getElementById('webhook-domain').textContent = publicDomain;
            } else {
                document.getElementById('webhook-domain').innerHTML = '<span style="color: #e74c3c;">Not Set - Add WEBHOOK_PUBLIC_DOMAIN to .env</span>';
            }

            // Display webhook URLs
            const urlsList = document.getElementById('webhook-urls-list');

            if (webhooks.length === 0) {
                urlsList.innerHTML = '<div class="empty-state">No webhooks available</div>';
                return;
            }

            urlsList.innerHTML = webhooks.map(webhook => {
                const publicUrl = publicDomain ? `https://${publicDomain}${webhook.endpoint}` : `http://localhost:8000${webhook.endpoint}`;
                const eventCount = stats.events_by_webhook[webhook.name] || 0;

                return `
                <div class="webhook-url-card ${webhook.enabled === false ? 'disabled' : ''}">
                    <div class="webhook-url-header">
                        <span class="webhook-name">${webhook.name}</span>
                        <span class="webhook-badge ${webhook.is_builtin ? 'builtin' : 'custom'}">${webhook.is_builtin ? 'Built-in' : 'Custom'}</span>
                        ${webhook.enabled === false ? '<span class="webhook-badge disabled">disabled</span>' : ''}
                    </div>
                    <div class="webhook-url-content">
                        <div class="url-row">
                            <strong>Provider:</strong> <span>${webhook.provider}</span>
                        </div>
                        <div class="url-row">
                            <strong>Endpoint:</strong>
                            <code>${webhook.endpoint}</code>
                        </div>
                        <div class="url-row">
                            <strong>Public URL:</strong>
                            <code class="public-url">${publicUrl}</code>
                            <button onclick="app.copyToClipboard('${publicUrl}')" class="copy-btn">📋 Copy</button>
                        </div>
                        <div class="url-row">
                            <strong>Events Received:</strong> <span class="event-count">${eventCount}</span>
                        </div>
                    </div>
                </div>
            `}).join('');

        } catch (error) {
            console.error('Failed to load webhook status:', error);
        }
    }

    async loadWebhookEvents() {
        try {
            const response = await fetch('/api/webhooks/events?limit=50');
            const events = await response.json();

            const eventsList = document.getElementById('webhook-events-list');

            if (!events || events.length === 0) {
                eventsList.innerHTML = '<div class="empty-state">No recent events</div>';
                return;
            }

            eventsList.innerHTML = events.map(event => {
                const timeAgo = this.getTimeAgo(new Date(event.created_at));
                return `
                <div class="event-item" onclick="app.viewWebhookEvent('${event.event_id}')" style="cursor: pointer;">
                    <div class="event-header">
                        <span class="event-provider">${event.provider}</span>
                        <span class="event-type">${event.event_type}</span>
                        <span class="event-time" title="${new Date(event.created_at).toLocaleString()}">${timeAgo}</span>
                    </div>
                    <div class="event-details">
                        <span><strong>Webhook:</strong> ${event.webhook_id}</span>
                        ${event.matched_command ? `<span><strong>Command:</strong> ${event.matched_command}</span>` : ''}
                        ${event.task_id ? `<span><strong>Task:</strong> <a href="#" onclick="event.stopPropagation(); app.viewTask('${event.task_id}'); return false;">${event.task_id}</a></span>` : '<span class="no-task">No task created</span>'}
                        ${event.response_sent ? '<span class="badge success">✓ Processed</span>' : '<span class="badge pending">⏳ Pending</span>'}
                    </div>
                </div>
            `}).join('');

        } catch (error) {
            console.error('Failed to load webhook events:', error);
            document.getElementById('webhook-events-list').innerHTML = '<div class="error-state">Failed to load events</div>';
        }
    }

    getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    }

    async refreshWebhookEvents() {
        await this.loadWebhookEvents();
    }

    async viewWebhookEvent(eventId) {
        try {
            const response = await fetch(`/api/webhooks/events/${eventId}`);
            const event = await response.json();

            let payload;
            try {
                payload = JSON.stringify(JSON.parse(event.payload), null, 2);
            } catch {
                payload = event.payload;
            }

            document.getElementById('modal-body').innerHTML = `
                <h3>Webhook Event: ${event.event_id}</h3>
                <p><strong>Provider:</strong> ${event.provider}</p>
                <p><strong>Event Type:</strong> ${event.event_type}</p>
                <p><strong>Webhook ID:</strong> ${event.webhook_id}</p>
                <p><strong>Created:</strong> ${new Date(event.created_at).toLocaleString()}</p>
                ${event.matched_command ? `<p><strong>Matched Command:</strong> ${event.matched_command}</p>` : '<p><strong>Status:</strong> No command matched</p>'}
                ${event.task_id ? `<p><strong>Task Created:</strong> <a href="#" onclick="app.viewTask('${event.task_id}'); return false;">${event.task_id}</a></p>` : ''}
                <p><strong>Response Sent:</strong> ${event.response_sent ? '✓ Yes' : '✗ No'}</p>
                <h4>Webhook Payload:</h4>
                <div class="logs-controls">
                    <button onclick="app.copyToClipboard(\`${payload.replace(/`/g, '\\`')}\`)" class="refresh-btn-small">📋 Copy Payload</button>
                </div>
                <div class="task-logs">
                    <pre>${payload}</pre>
                </div>
            `;
            document.getElementById('modal').classList.remove('hidden');
        } catch (error) {
            console.error('Failed to load webhook event:', error);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    // Webhook Management
    async loadWebhooks() {
        try {
            const response = await fetch('/api/webhooks');
            const webhooks = await response.json();

            const container = document.getElementById('webhooks-list');

            if (!webhooks || webhooks.length === 0) {
                container.innerHTML = '<p class="empty-state">No webhooks registered. Use "Create Webhook" from the side menu to get started.</p>';
                return;
            }

            container.innerHTML = webhooks.map(webhook => `
                <div class="webhook-card">
                    <div class="webhook-header">
                        <h3>${webhook.name}</h3>
                        ${webhook.is_builtin ? '<span class="badge">Built-in</span>' : ''}
                        ${webhook.enabled !== undefined ? `
                            <span class="webhook-status ${webhook.enabled ? 'enabled' : 'disabled'}">
                                ${webhook.enabled ? '✓ Enabled' : '✗ Disabled'}
                            </span>
                        ` : ''}
                    </div>
                    <div class="webhook-info">
                        <p><strong>Provider:</strong> ${webhook.provider || webhook.source || 'N/A'}</p>
                        <p><strong>Endpoint:</strong> <code>${webhook.endpoint}</code></p>
                        ${webhook.commands ? `<p><strong>Commands:</strong> ${webhook.commands.length}</p>` : ''}
                    </div>
                    ${!webhook.is_builtin && webhook.webhook_id ? `
                        <div class="webhook-actions">
                            <button onclick="app.toggleWebhook('${webhook.webhook_id}', ${!webhook.enabled})" class="btn-sm">
                                ${webhook.enabled ? 'Disable' : 'Enable'}
                            </button>
                            <button onclick="app.viewWebhook('${webhook.webhook_id}')" class="btn-sm">View</button>
                            <button onclick="app.deleteWebhook('${webhook.webhook_id}')" class="btn-sm btn-danger">Delete</button>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load webhooks:', error);
        }
    }

    showWebhookCreate() {
        document.getElementById('webhook-create-modal').classList.remove('hidden');
        document.getElementById('webhook-commands-list').innerHTML = '';
        this.addWebhookCommand();
    }

    hideWebhookCreate() {
        document.getElementById('webhook-create-modal').classList.add('hidden');
        document.getElementById('webhook-create-form').reset();
    }

    addWebhookCommand() {
        const container = document.getElementById('webhook-commands-list');
        const commandId = Date.now();

        const commandHtml = `
            <div class="webhook-command" data-command-id="${commandId}">
                <h4>Command ${container.children.length + 1}</h4>
                <div class="form-group">
                    <label>Trigger (event type):</label>
                    <input type="text" class="cmd-trigger" placeholder="issues.opened" required>
                </div>
                <div class="form-group">
                    <label>Action:</label>
                    <select class="cmd-action" required>
                        <option value="create_task">Create Task</option>
                        <option value="comment">Comment</option>
                        <option value="ask">Ask</option>
                        <option value="respond">Respond</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Agent:</label>
                    <select class="cmd-agent">
                        <option value="planning">Planning</option>
                        <option value="executor">Executor</option>
                        <option value="brain">Brain</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Template:</label>
                    <textarea class="cmd-template" placeholder="New issue: {{issue.title}}" required></textarea>
                </div>
                <button type="button" onclick="app.removeWebhookCommand(${commandId})" class="btn-sm btn-danger">Remove Command</button>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', commandHtml);
    }

    removeWebhookCommand(commandId) {
        const command = document.querySelector(`[data-command-id="${commandId}"]`);
        if (command) {
            command.remove();
        }
    }

    async createWebhook(event) {
        event.preventDefault();

        const name = document.getElementById('webhook-name').value;
        const provider = document.getElementById('webhook-provider').value;
        const secret = document.getElementById('webhook-secret').value;
        const enabled = document.getElementById('webhook-enabled').checked;

        const commandElements = document.querySelectorAll('.webhook-command');
        const commands = Array.from(commandElements).map(cmd => ({
            trigger: cmd.querySelector('.cmd-trigger').value,
            action: cmd.querySelector('.cmd-action').value,
            agent: cmd.querySelector('.cmd-agent').value,
            template: cmd.querySelector('.cmd-template').value
        }));

        try {
            const response = await fetch('/api/webhooks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    provider,
                    secret: secret || undefined,
                    enabled,
                    commands
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert(`Webhook created successfully!\n\nEndpoint: ${data.data.endpoint}`);
                this.hideWebhookCreate();
                if (this.currentTab === 'webhooks') {
                    await this.loadWebhooks();
                }
            } else {
                alert(`Failed to create webhook: ${data.detail || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to create webhook:', error);
            alert('Failed to create webhook: Network error');
        }
    }

    async toggleWebhook(webhookId, enable) {
        try {
            const endpoint = enable ? 'enable' : 'disable';
            const response = await fetch(`/api/webhooks/${webhookId}/${endpoint}`, {
                method: 'POST'
            });

            if (response.ok) {
                await this.loadWebhooks();
            }
        } catch (error) {
            console.error('Failed to toggle webhook:', error);
        }
    }

    async deleteWebhook(webhookId) {
        if (!confirm('Are you sure you want to delete this webhook?')) {
            return;
        }

        try {
            const response = await fetch(`/api/webhooks/${webhookId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadWebhooks();
            }
        } catch (error) {
            console.error('Failed to delete webhook:', error);
        }
    }

    async viewWebhook(webhookId) {
        try {
            const response = await fetch(`/api/webhooks/${webhookId}`);
            const webhook = await response.json();

            const commandsHtml = webhook.commands.map(cmd => `
                <div class="command-detail">
                    <p><strong>Trigger:</strong> ${cmd.trigger}</p>
                    <p><strong>Action:</strong> ${cmd.action}</p>
                    <p><strong>Agent:</strong> ${cmd.agent || 'N/A'}</p>
                    <p><strong>Template:</strong> <code>${cmd.template}</code></p>
                </div>
            `).join('');

            document.getElementById('modal-body').innerHTML = `
                <h3>${webhook.name}</h3>
                <p><strong>Provider:</strong> ${webhook.provider}</p>
                <p><strong>Endpoint:</strong> <code>${webhook.endpoint}</code></p>
                <p><strong>Status:</strong> ${webhook.enabled ? '✓ Enabled' : '✗ Disabled'}</p>
                <p><strong>Created:</strong> ${new Date(webhook.created_at).toLocaleString()}</p>
                <h4>Commands (${webhook.commands.length})</h4>
                ${commandsHtml || '<p>No commands configured</p>'}
            `;
            document.getElementById('modal').classList.remove('hidden');
        } catch (error) {
            console.error('Failed to load webhook:', error);
        }
    }
}

// Initialize app
const app = new DashboardApp();
