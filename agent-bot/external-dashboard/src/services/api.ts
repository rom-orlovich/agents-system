import type { Task, TaskStats, Agent, AgentHealth, Metrics } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8090';

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export const api = {
  tasks: {
    list: (params?: { status?: string; limit?: number; offset?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set('status', params.status);
      if (params?.limit) searchParams.set('limit', params.limit.toString());
      if (params?.offset) searchParams.set('offset', params.offset.toString());
      const query = searchParams.toString();
      return fetchJson<{ tasks: Task[]; count: number }>(
        `/api/v1/tasks${query ? `?${query}` : ''}`
      );
    },
    get: (taskId: string) => fetchJson<Task>(`/api/v1/tasks/${taskId}`),
    getStats: () => fetchJson<TaskStats>('/api/v1/tasks/stats'),
    getQueueLength: () => fetchJson<{ queue_length: number }>('/api/v1/tasks/queue'),
    cancel: async (taskId: string) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to cancel task');
      return response.json();
    },
  },

  agents: {
    list: () => fetchJson<Agent[]>('/api/v1/agents'),
    getStatus: () => fetchJson<Record<string, Agent>>('/api/v1/agents/status'),
    getHealth: () => fetchJson<AgentHealth[]>('/api/v1/agents/health'),
    getMetrics: () => fetchJson<Record<string, number>>('/api/v1/agents/metrics'),
  },

  metrics: {
    get: () => fetchJson<Metrics>('/api/v1/metrics'),
  },
};

export function createWebSocket(onMessage: (msg: unknown) => void): WebSocket {
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8090/ws';
  const ws = new WebSocket(wsUrl);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('WebSocket parse error:', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  return ws;
}
