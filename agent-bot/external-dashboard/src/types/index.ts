export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Task {
  task_id: string;
  source: 'github' | 'jira' | 'slack' | 'sentry';
  event_type: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  repository?: string;
  issue_key?: string;
  channel?: string;
  output?: string;
  error?: string;
}

export interface TaskStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  success_rate: number;
}

export interface Agent {
  name: string;
  type: string;
  status: 'active' | 'idle' | 'error';
  last_activity: string;
  tasks_processed: number;
}

export interface AgentHealth {
  agent: string;
  healthy: boolean;
  uptime: number;
  last_check: string;
}

export interface Metrics {
  tasks: TaskStats;
  queue_length: number;
  agents_active: number;
  avg_processing_time: number;
  error_rate: number;
}

export interface WebSocketMessage {
  type: 'task_update' | 'agent_update' | 'metrics_update';
  data: Task | Agent | Metrics;
}
