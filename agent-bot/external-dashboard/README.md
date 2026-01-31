# External Dashboard (React)

> Modern React-based dashboard for monitoring and managing agent-bot tasks, analytics, and conversations.

## Purpose

The External Dashboard is a React + TypeScript frontend that provides a modern UI for monitoring agent-bot operations. It consumes the Dashboard API and displays real-time task updates, analytics, conversations, webhook status, and system metrics.

## Architecture

```
User Browser
     │
     │ HTTP + WebSocket
     ▼
┌─────────────────────────────────────┐
│   External Dashboard :3002          │
│   (React + TypeScript + Vite)       │
│                                     │
│  Features:                          │
│  - Overview (metrics, recent tasks) │
│  - Analytics (costs, performance)   │
│  - Ledger (task log with filters)   │
│  - Webhooks (config & events)       │
│  - Chat (conversations)             │
│  - Registry (agents & status)       │
└─────────────────────────────────────┘
         │
         │ HTTP + WebSocket
         ▼
┌─────────────────────────────────────┐
│   Dashboard API :5000              │
│   (Backend API)                    │
└─────────────────────────────────────┘
```

## Folder Structure

```
external-dashboard/
├── src/
│   ├── App.tsx                 # Main application
│   ├── main.tsx                # Entry point
│   ├── components/
│   │   ├── ui/                 # UI components
│   │   └── TaskStatusModal.tsx # Task modal
│   ├── features/
│   │   ├── overview/           # Overview feature
│   │   ├── analytics/          # Analytics feature
│   │   ├── ledger/             # Ledger feature
│   │   ├── webhooks/           # Webhooks feature
│   │   ├── chat/               # Chat feature
│   │   └── registry/           # Registry feature
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WebSocket hook
│   │   ├── useCLIStatus.ts     # CLI status hook
│   │   └── useTaskModal.ts     # Task modal hook
│   └── layouts/
│       └── DashboardLayout.tsx # Main layout
├── public/                     # Static assets
└── package.json                # Dependencies
```

## Features

### Overview

- System metrics dashboard
- Recent tasks list
- Quick statistics
- Task status breakdown

### Analytics

- Cost tracking over time
- Performance metrics
- Usage histograms
- Token usage breakdown

### Ledger

- Complete task log
- Filtering and search
- Task details view
- Export capabilities

### Webhooks

- Webhook configuration management
- Event history
- Status monitoring
- Create/edit webhooks

### Chat

- Conversation interface
- Agent interactions
- Message history
- Real-time updates

### Registry

- Agent registry
- Agent status
- Agent capabilities
- Agent configuration

## Environment Variables

```bash
VITE_DASHBOARD_API_URL=http://localhost:5000
VITE_WEBSOCKET_URL=ws://localhost:5000/ws
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_WEBHOOKS=true
```

## Development

```bash
pnpm install
pnpm dev          # Development server
pnpm build        # Production build
pnpm preview      # Preview production build
```

## Docker

Served via nginx in production:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## Related Services

- **dashboard-api**: Backend API consumed by this dashboard
- **agent-engine**: Publishes task updates via WebSocket
- **api-gateway**: Creates tasks visible in dashboard
