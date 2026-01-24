export const MOCK_WEBHOOKS = [
  {
    id: "wh-1",
    name: "GitHub Global",
    provider: "github",
    status: "active",
    url: "https://hooks.machine.io/gh-global",
  },
  {
    id: "wh-2",
    name: "Jira Cloud",
    provider: "jira",
    status: "active",
    url: "https://hooks.machine.io/jira-cloud",
  },
  {
    id: "wh-3",
    name: "Sentry Alerts",
    provider: "sentry",
    status: "inactive",
    url: "https://hooks.machine.io/sentry",
  },
];

export const MOCK_WEBHOOK_EVENTS = [
  {
    id: "ev-1",
    webhook_id: "wh-1",
    event: "push",
    timestamp: "2026-01-22T20:55:00Z",
    status: "processed",
  },
  {
    id: "ev-2",
    webhook_id: "wh-1",
    event: "issue_created",
    timestamp: "2026-01-22T20:50:00Z",
    status: "processed",
  },
  {
    id: "ev-3",
    webhook_id: "wh-2",
    event: "issue_updated",
    timestamp: "2026-01-22T20:45:00Z",
    status: "error",
  },
];
