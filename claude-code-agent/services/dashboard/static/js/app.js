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
        await this.loadStatus();
        await this.loadAnalyticsSummary();
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

    completeTask(taskId, result, cost) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.status = 'completed';
            task.result = result;
            task.cost = cost;
            this.renderTasks();
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
    }

    // Tab Switching
    switchTab(tabName) {
        this.currentTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');

        // Load data for specific tabs
        if (tabName === 'analytics') {
            this.loadAnalyticsCharts();
        } else if (tabName === 'tasks') {
            this.refreshTaskTable();
        }
    }

    // Analytics Charts
    async loadAnalyticsCharts() {
        await this.loadDailyCostsChart();
        await this.loadSubagentCostsChart();
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
        document.getElementById('credentials-modal').classList.remove('hidden');
        await this.loadCredentialStatus();
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

        this.addChatMessage('user', message);
        input.value = '';

        try {
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
                <p><strong>Cost:</strong> $${(task.cost_usd || 0).toFixed(4)}</p>
                <p><strong>Tokens:</strong> ${task.input_tokens || 0} in / ${task.output_tokens || 0} out</p>
                <p><strong>Created:</strong> ${new Date(task.created_at).toLocaleString()}</p>
                ${task.completed_at ? `<p><strong>Completed:</strong> ${new Date(task.completed_at).toLocaleString()}</p>` : ''}
                <h4>Input:</h4>
                <div class="task-input">${task.input_message || 'N/A'}</div>
                <h4>Output:</h4>
                <div class="task-output" id="task-output-${taskId}">${task.output_stream || 'N/A'}</div>
                ${task.error ? `<h4>Error:</h4><div class="task-error">${task.error}</div>` : ''}
            `;
            document.getElementById('modal').classList.remove('hidden');
        } catch (error) {
            console.error('Failed to load task:', error);
        }
    }

    hideModal() {
        document.getElementById('modal').classList.add('hidden');
    }
}

// Initialize app
const app = new DashboardApp();
