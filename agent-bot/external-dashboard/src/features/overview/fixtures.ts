export const MOCK_METRICS = {
  queue_depth: 12,
  active_sessions: 4,
  wires_connected: 25,
  daily_burn: 45.32,
  total_jobs: 1450,
  cumulative_cost: 1250.45,
  oauth_session_used: 100,
  oauth_session_limit: 1000,
  oauth_session_percentage: 10.0,
  oauth_weekly_used: 500,
  oauth_weekly_limit: 5000,
  oauth_weekly_percentage: 10.0,
};

export const MOCK_TASKS = [
  {
    id: "task-1",
    name: "PROCESS_LOGS",
    status: "completed",
    cost: 0.05,
    timestamp: "2026-01-22T20:00:00Z",
  },
  {
    id: "task-2",
    name: "GENERATE_REPORT",
    status: "running",
    cost: 0.12,
    timestamp: "2026-01-22T20:45:00Z",
  },
  {
    id: "task-3",
    name: "VECTOR_EMBEDDING",
    status: "queued",
    cost: 0.0,
    timestamp: "2026-01-22T20:50:00Z",
  },
];
