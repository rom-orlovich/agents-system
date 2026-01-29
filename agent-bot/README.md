# Agent Bot System

Production-ready microservices architecture for AI agent orchestration with webhook-driven task management.

## Architecture

This system implements a microservices architecture with the following components:

### Core Components

- **API Gateway** (Port 8080): Webhook receiver and task queue management
- **GitHub Service** (Port 8081): GitHub API integration microservice
- **Jira Service** (Port 8082): Jira API integration microservice
- **Slack Service** (Port 8083): Slack API integration microservice
- **Sentry Service** (Port 8084): Sentry API integration microservice
- **Agent Container**: Task execution and AI agent orchestration
- **Dashboard API Container** (Port 8090): Analytics, logs, and management API

### Infrastructure

- **Redis**: Task queue and caching
- **PostgreSQL**: Persistent storage

## Key Features

- **Standalone Components**: Each service is independent with its own Dockerfile and dependencies
- **TDD Approach**: All business logic implemented with test-first development
- **Strict Type Safety**: No `any` types, comprehensive Pydantic validation
- **Production Ready**: Error handling, logging, monitoring, health checks
- **Modular & Extensible**: Feature-based structure with dependency injection
- **Task Flow Logging**: Centralized logging system tracking complete task lifecycle

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Environment variables configured (copy `.env.example` to `.env`)

### Running the System

```bash
make build
make up
make logs
```

### Running Tests

```bash
make test
```

## Development

### Architecture Principles

1. **No Shared Code**: Components communicate only via API or Queue
2. **API Contracts**: Well-defined Pydantic schemas for all endpoints
3. **Self-Explanatory Code**: No comments, clear naming and structure
4. **Modular Design**: Single Responsibility Principle throughout
5. **Type Safety**: Explicit types, no `any`, proper optional handling

### Testing Strategy

- **TDD**: Write tests first for all business logic
- **Webhook Flow Testing**: End-to-end tests for complete webhook processing
- **Integration Tests**: Test component interactions
- **Contract Testing**: Verify API compliance

### Component Structure

Each component follows this structure:

```
component-name/
├── Dockerfile
├── main.py
├── requirements.txt
├── pyproject.toml
├── api/
├── core/
├── storage/
└── tests/
```

## API Documentation

Each service provides Swagger documentation at `/docs`:

- API Gateway: http://localhost:8080/docs
- GitHub Service: http://localhost:8081/docs
- Jira Service: http://localhost:8082/docs
- Slack Service: http://localhost:8083/docs
- Sentry Service: http://localhost:8084/docs
- Dashboard API: http://localhost:8090/docs

## Monitoring

Health check endpoints available at `/health` for all services.

## License

MIT
