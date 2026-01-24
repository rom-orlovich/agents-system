export const MOCK_LEDGER_TASKS = Array.from({ length: 15 }).map((_, i) => ({
  id: `task-${i + 1}`,
  session_id: `session-${Math.floor(i / 5) + 1}`,
  assigned_agent: ["orchestrator", "backend-specialist", "frontend-specialist"][i % 3],
  status: ["completed", "running", "failed", "queued"][i % 4],
  cost_usd: (Math.random() * 0.5).toFixed(2),
  duration_seconds: Math.floor(Math.random() * 120),
  created_at: new Date(Date.now() - i * 3600000).toISOString(),
}));

export const MOCK_AGENTS = [
  "orchestrator",
  "backend-specialist",
  "frontend-specialist",
  "debugger",
  "security-auditor",
];
