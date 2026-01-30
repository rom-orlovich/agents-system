# Agent Bot Production Deployment Guide

## Overview

This guide covers the complete production deployment of the agent-bot system with the new architecture.

## Architecture

The system consists of 4 main components:

1. **PostgreSQL** - Persistent storage for installations and tasks
2. **Redis** - Task queue and caching
3. **API Gateway** - OAuth and webhook handling
4. **Agent Container** - Task processing workers

## Prerequisites

- Docker and Docker Compose
- GitHub OAuth App credentials
- Anthropic API key
- Domain with SSL certificate (for production)

## Environment Variables

Create a `.env` file in the `agent-bot` directory:

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# Anthropic
ANTHROPIC_API_KEY=your_api_key

# Database
DATABASE_URL=postgresql://agent:agent@postgres:5432/agent_bot

# Redis
REDIS_URL=redis://redis:6379

# Optional
LOG_LEVEL=INFO
```

## Quick Start

### 1. Start the Stack

```bash
cd agent-bot
docker compose up -d
```

### 2. Verify Services

```bash
# Check all services are running
docker compose ps

# Check logs
docker compose logs -f api-gateway
docker compose logs -f agent-container
```

### 3. Run Validation

```bash
./scripts/validate_deployment.sh
```

## Architecture Components

### API Gateway (Port 8080)

**Endpoints:**
- `GET /health` - Comprehensive health check
- `GET /metrics` - System metrics
- `GET /oauth/github/authorize` - Start OAuth flow
- `GET /oauth/github/callback` - OAuth callback
- `POST /webhooks/{provider}` - Webhook receiver

**Features:**
- Redis queue adapter for task management
- PostgreSQL repository for installation storage
- GitHub OAuth handler
- Webhook registry with signature validation
- CORS middleware
- Structured logging

### Agent Container

**Features:**
- Redis queue consumer
- Claude CLI adapter for command execution
- Repository manager for git operations
- Knowledge graph indexer
- Result poster for webhook responses
- Streaming logger for real-time updates

### Database Schema

**installations table:**
- id (VARCHAR PK)
- platform (VARCHAR)
- organization_id (VARCHAR)
- organization_name (VARCHAR)
- access_token (TEXT)
- refresh_token (TEXT)
- scopes (TEXT[])
- webhook_secret (VARCHAR)
- installed_by (VARCHAR)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

**tasks table:**
- id (VARCHAR PK)
- installation_id (VARCHAR FK)
- provider (VARCHAR)
- status (ENUM: pending, processing, completed, failed, cancelled)
- priority (ENUM: critical, high, normal, low)
- input_message (TEXT)
- output (TEXT)
- error (TEXT)
- source_metadata (JSONB)
- execution_metadata (JSONB)
- tokens_used (INTEGER)
- cost_usd (DECIMAL)
- started_at (TIMESTAMP)
- completed_at (TIMESTAMP)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

## Production Checklist

### Security

- [ ] Use strong PostgreSQL password
- [ ] Enable SSL for database connections
- [ ] Use HTTPS for API Gateway
- [ ] Rotate webhook secrets regularly
- [ ] Store API keys in secrets manager
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Use firewall rules to restrict access

### Monitoring

- [ ] Set up application metrics collection
- [ ] Configure alerts for service health
- [ ] Monitor queue size and task latency
- [ ] Track token usage and costs
- [ ] Set up log aggregation
- [ ] Monitor database performance
- [ ] Track error rates

### Scaling

- [ ] Configure agent-container replicas (default: 2)
- [ ] Set up database connection pooling
- [ ] Configure Redis persistence
- [ ] Enable database backups
- [ ] Set up load balancer for API Gateway
- [ ] Configure resource limits in Docker

### Backup and Recovery

- [ ] Schedule PostgreSQL backups
- [ ] Test restore procedures
- [ ] Document recovery processes
- [ ] Maintain disaster recovery plan
- [ ] Back up environment configuration

## Troubleshooting

### Services Won't Start

```bash
# Check Docker resources
docker system df

# View detailed logs
docker compose logs --tail=100

# Restart services
docker compose restart
```

### Database Connection Issues

```bash
# Test database connection
docker compose exec postgres psql -U agent -d agent_bot -c "SELECT 1"

# Check database logs
docker compose logs postgres
```

### Redis Connection Issues

```bash
# Test Redis connection
docker compose exec redis redis-cli ping

# Check Redis logs
docker compose logs redis
```

### Queue Not Processing

```bash
# Check queue size
docker compose exec redis redis-cli ZCARD "agent:tasks"

# Check worker logs
docker compose logs agent-container

# Restart workers
docker compose restart agent-container
```

## Maintenance

### Database Migrations

```bash
# Run migrations
cd database/migrations/versions
docker compose exec -T postgres psql -U agent -d agent_bot -f 002_new_migration.sql
```

### Scaling Workers

```bash
# Edit docker-compose.yml
# Change replicas under agent-container.deploy.replicas

# Restart stack
docker compose up -d --scale agent-container=5
```

### Updating Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose build
docker compose up -d
```

## Health Checks

### Manual Health Check

```bash
curl http://localhost:8080/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "timestamp": "2026-01-30T17:00:00Z",
  "checks": {
    "redis": {
      "healthy": true,
      "latency_ms": 1.23
    },
    "database": {
      "healthy": true,
      "latency_ms": 2.45
    },
    "queue": {
      "healthy": true,
      "queue_size": 5
    }
  }
}
```

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics | jq
```

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Run validation: `./scripts/validate_deployment.sh`
3. Review this documentation
4. Check GitHub issues

## License

[Your License]
