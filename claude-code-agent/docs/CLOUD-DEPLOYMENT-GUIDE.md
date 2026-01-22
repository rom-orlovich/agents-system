# Cloud Deployment Guide

**Target Platform**: Claude Code (https://code.claude.com), Kubernetes, Cloud Run, ECS, etc.
**Date**: January 22, 2026
**Critical**: Read this BEFORE deploying to production cloud environments

---

## 🚨 Critical Difference: Docker vs. Cloud

### Docker Deployment (Local/Single-Node) ✅
```yaml
volumes:
  - machine_data:/data  # Named volume persists on local disk
```
**Persistence**: Files in `/data` survive container restarts ✅

### Cloud Deployment (Kubernetes/Cloud Run/ECS) ❌
```yaml
# NO persistent volumes by default!
# Container restart = ALL DATA LOST
```
**Persistence**: Files in `/data` are **EPHEMERAL** ❌

---

## Problem: Current Architecture Assumes Local Volumes

### What Breaks in Cloud Deployment

| Component | Docker | Cloud Platform | Issue |
|-----------|--------|----------------|-------|
| **Database** | `/data/db/machine.db` ✅ | Lost on restart ❌ | Need external DB |
| **Credentials** | `/data/credentials/claude.json` ✅ | Lost on restart ❌ | Need secrets manager |
| **User Agents** | `/data/config/agents/` ✅ | Lost on restart ❌ | Need object storage |
| **User Skills** | `/data/config/skills/` ✅ | Lost on restart ❌ | Need object storage |

### Example Failure Scenario

```bash
# User uploads custom agent via API
POST /api/agents/upload {"name": "my-agent", ...}
# ✅ Saved to /data/config/agents/my-agent/

# Kubernetes pod restarts (auto-scaling, node failure, deployment)
# ❌ ALL DATA LOST - my-agent no longer exists!

# User tries to run task with my-agent
# ❌ Error: Agent not found
```

---

## ✅ Solution: Storage Backend Abstraction

### Architecture

```
Application Layer
       ↓
Storage Backend Interface (core/storage_backend.py)
       ↓
   ┌───┴───┬───────┬──────────┐
   │       │       │          │
 Local   S3    PostgreSQL   (Future: GCS, Azure Blob)
```

### Supported Backends

#### 1. **Local Filesystem** (Docker only)
```python
# Environment
STORAGE_BACKEND=local
DATA_DIR=/data

# Use Case: Docker Compose, single-node deployments
# Persistence: Named volumes
```

#### 2. **S3-Compatible Storage** (Cloud recommended)
```python
# Environment
STORAGE_BACKEND=s3
S3_BUCKET=my-claude-agent-bucket
S3_PREFIX=production
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# Compatible Services:
# - AWS S3
# - MinIO (self-hosted)
# - DigitalOcean Spaces
# - Backblaze B2
# - Cloudflare R2
```

#### 3. **PostgreSQL BLOB Storage** (Cloud alternative)
```python
# Environment
STORAGE_BACKEND=postgresql
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Use Case: When S3 is not available, small files only
# Limitation: Not recommended for files > 100MB
```

---

## Cloud Deployment Configurations

### Deployment Option 1: Kubernetes + S3

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: claude-agent
spec:
  replicas: 3  # ✅ Horizontal scaling supported
  template:
    spec:
      containers:
      - name: app
        image: claude-agent:latest
        env:
          # Storage Configuration
          - name: STORAGE_BACKEND
            value: "s3"
          - name: S3_BUCKET
            value: "claude-agent-production"
          - name: S3_PREFIX
            value: "agents"

          # AWS Credentials (use secrets!)
          - name: AWS_ACCESS_KEY_ID
            valueFrom:
              secretKeyRef:
                name: aws-credentials
                key: access_key_id
          - name: AWS_SECRET_ACCESS_KEY
            valueFrom:
              secretKeyRef:
                name: aws-credentials
                key: secret_access_key

          # Database (external)
          - name: DATABASE_URL
            value: "postgresql+asyncpg://user:pass@postgres.svc:5432/claude_db"

          # Redis (external)
          - name: REDIS_URL
            value: "redis://redis.svc:6379/0"

          # Claude CLI Configuration
          - name: DEFAULT_MODEL
            value: "sonnet"
          - name: DEFAULT_ALLOWED_TOOLS
            value: "Read,Edit,Bash,Glob,Grep,Write"

---
# kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
type: Opaque
stringData:
  access_key_id: "AKIAIOSFODNN7EXAMPLE"
  secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

### Deployment Option 2: Google Cloud Run + GCS

```yaml
# cloud-run.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: claude-agent
spec:
  template:
    spec:
      containers:
      - image: gcr.io/project/claude-agent:latest
        env:
          # Storage Configuration
          - name: STORAGE_BACKEND
            value: "s3"  # GCS is S3-compatible via interoperability API
          - name: S3_BUCKET
            value: "claude-agent-bucket"
          - name: AWS_ACCESS_KEY_ID
            valueFrom:
              secretKeyRef:
                name: gcs-credentials
                key: access_key
          - name: AWS_SECRET_ACCESS_KEY
            valueFrom:
              secretKeyRef:
                name: gcs-credentials
                key: secret_key

          # Cloud SQL PostgreSQL
          - name: DATABASE_URL
            value: "postgresql+asyncpg://user:pass@/db?host=/cloudsql/project:region:instance"

          # Cloud Memorystore Redis
          - name: REDIS_URL
            value: "redis://10.0.0.3:6379/0"
```

### Deployment Option 3: AWS ECS + S3

```json
// ecs-task-definition.json
{
  "family": "claude-agent",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/claude-agent:latest",
      "environment": [
        {"name": "STORAGE_BACKEND", "value": "s3"},
        {"name": "S3_BUCKET", "value": "claude-agent-production"},
        {"name": "DATABASE_URL", "value": "postgresql+asyncpg://user:pass@rds.amazonaws.com:5432/db"},
        {"name": "REDIS_URL", "value": "redis://elasticache.amazonaws.com:6379/0"}
      ],
      "secrets": [
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:claude-agent/aws-creds:access_key_id"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:claude-agent/aws-creds:secret_access_key"
        }
      ]
    }
  ],
  "taskRoleArn": "arn:aws:iam::123456789:role/claude-agent-task-role"
}
```

---

## Migration from Docker to Cloud

### Step-by-Step Migration

#### Step 1: Export Docker Data

```bash
# Backup database
docker exec claude-agent sqlite3 /data/db/machine.db .dump > backup.sql

# Export credentials
docker cp claude-agent:/data/credentials/claude.json ./credentials.json

# Export user-uploaded agents
docker cp claude-agent:/data/config/agents ./agents_backup/

# Export user-uploaded skills
docker cp claude-agent:/data/config/skills ./skills_backup/
```

#### Step 2: Set Up Cloud Storage

```bash
# Create S3 bucket
aws s3 mb s3://claude-agent-production

# Upload agents to S3
aws s3 sync ./agents_backup/ s3://claude-agent-production/agents/

# Upload skills to S3
aws s3 sync ./skills_backup/ s3://claude-agent-production/skills/
```

#### Step 3: Set Up Cloud Database

```bash
# Create PostgreSQL database (AWS RDS)
aws rds create-db-instance \
  --db-instance-identifier claude-agent-db \
  --engine postgres \
  --engine-version 15.3 \
  --db-instance-class db.t3.medium \
  --allocated-storage 20

# Import backup
psql postgresql://user:pass@rds.amazonaws.com:5432/claude_db < backup.sql
```

#### Step 4: Deploy to Cloud

```bash
# Build and push image
docker build -t claude-agent:latest .
docker tag claude-agent:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/claude-agent:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/claude-agent:latest

# Deploy to Kubernetes
kubectl apply -f kubernetes/deployment.yaml

# Verify deployment
kubectl get pods
kubectl logs -f deployment/claude-agent
```

---

## Code Changes Required

### Update Credential Loading

**Before (Docker only)**:
```python
# core/credentials.py
def load_credentials():
    path = Path("/data/credentials/claude.json")
    return json.loads(path.read_text())
```

**After (Cloud-compatible)**:
```python
# core/credentials.py
from core.storage_backend import get_storage_backend

async def load_credentials():
    storage = get_storage_backend()
    content = await storage.read_file("credentials/claude.json")
    if not content:
        raise FileNotFoundError("Credentials not found")
    return json.loads(content.decode())
```

### Update Agent Upload API

**Before (Docker only)**:
```python
# api/agents.py
@router.post("/agents/upload")
async def upload_agent(name: str, claude_md: str):
    path = Path(f"/data/config/agents/{name}/CLAUDE.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(claude_md)
```

**After (Cloud-compatible)**:
```python
# api/agents.py
from core.storage_backend import get_storage_backend

@router.post("/agents/upload")
async def upload_agent(name: str, claude_md: str):
    storage = get_storage_backend()
    await storage.write_file(
        f"config/agents/{name}/CLAUDE.md",
        claude_md.encode()
    )
```

---

## Environment Variables Reference

### Storage Configuration

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `STORAGE_BACKEND` | `local` | Storage backend: `local`, `s3`, `postgresql` | All |
| `DATA_DIR` | `/data` | Local filesystem base directory | Local only |
| `S3_BUCKET` | - | S3 bucket name | S3 only |
| `S3_PREFIX` | `claude-agent` | S3 key prefix | S3 only |
| `AWS_ACCESS_KEY_ID` | - | AWS access key | S3 only |
| `AWS_SECRET_ACCESS_KEY` | - | AWS secret key | S3 only |
| `AWS_REGION` | `us-east-1` | AWS region | S3 only |

### Claude CLI Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | (none) | Default model: `opus`, `sonnet`, etc. |
| `DEFAULT_ALLOWED_TOOLS` | `Read,Edit,Bash,Glob,Grep,Write` | Pre-approved tools for headless mode |
| `ENABLE_SUBAGENTS` | `true` | Enable sub-agent execution |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:////data/db/machine.db` | Database connection string |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |

---

## Performance Considerations

### Latency Comparison

| Operation | Local Filesystem | S3 | PostgreSQL |
|-----------|-----------------|-----|------------|
| **Write 1KB file** | <1ms | ~50ms | ~10ms |
| **Read 1KB file** | <1ms | ~30ms | ~5ms |
| **List 1000 files** | ~10ms | ~100ms | ~20ms |
| **Delete file** | <1ms | ~30ms | ~5ms |

### Optimization Tips

1. **Cache frequently accessed files** in Redis
2. **Use S3 Transfer Acceleration** for large files
3. **Enable S3 versioning** for audit trail
4. **Use PostgreSQL for small metadata**, S3 for large files
5. **Implement read-through cache** for agent definitions

---

## Cost Estimation

### AWS S3 Storage (Example)

```
Assumptions:
- 1000 user-uploaded agents (avg 10KB each) = 10MB
- 500 user-uploaded skills (avg 5KB each) = 2.5MB
- 10GB database backups per month
- Total: ~12.5GB storage

Costs:
- S3 Storage: $0.023/GB/month × 12.5GB = $0.29/month
- S3 Requests: ~100k requests/month = $0.50/month
- Data Transfer: ~1GB out = $0.09/GB = $0.09/month

Total: ~$0.88/month for storage
```

### Database Storage

```
AWS RDS PostgreSQL db.t3.micro:
- Instance: $14.60/month
- Storage (20GB): $2.30/month
- Backups: $0 (first 20GB free)

Total: ~$17/month for database
```

**Grand Total**: ~$18/month for cloud infrastructure (excluding compute)

---

## Monitoring & Observability

### Key Metrics to Track

```python
# Example Prometheus metrics
storage_backend_operation_duration_seconds{backend="s3",operation="read"}
storage_backend_operation_total{backend="s3",operation="read",status="success"}
storage_backend_errors_total{backend="s3",operation="read",error_type="not_found"}
```

### Health Checks

```python
# main.py
@app.get("/health")
async def health_check():
    storage = get_storage_backend()

    # Test storage backend
    try:
        test_file = "health-check/test.txt"
        await storage.write_file(test_file, b"test")
        content = await storage.read_file(test_file)
        await storage.delete_file(test_file)

        if content != b"test":
            raise Exception("Storage backend read/write mismatch")

    except Exception as e:
        return {"status": "unhealthy", "storage": str(e)}

    return {"status": "healthy", "storage": type(storage).__name__}
```

---

## Troubleshooting

### Issue 1: "Agent not found after deployment"

**Cause**: Agent files not migrated to cloud storage

**Solution**:
```bash
# Check if agents exist in S3
aws s3 ls s3://claude-agent-production/config/agents/

# If empty, upload from backup
aws s3 sync ./agents_backup/ s3://claude-agent-production/config/agents/
```

### Issue 2: "Permission denied writing to S3"

**Cause**: IAM role missing S3 permissions

**Solution**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::claude-agent-production/*",
        "arn:aws:s3:::claude-agent-production"
      ]
    }
  ]
}
```

### Issue 3: "Database connection timeout"

**Cause**: Network policy blocking database access

**Solution**:
```yaml
# Kubernetes: Add network policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgres
spec:
  podSelector:
    matchLabels:
      app: claude-agent
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

---

## Security Best Practices

### 1. Never Commit Secrets

```bash
# .gitignore
.env
*.json  # credentials
aws-credentials.yaml
secrets/
```

### 2. Use Secrets Manager

```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name claude-agent/aws-creds \
  --secret-string '{"access_key":"...","secret_key":"..."}'

# Kubernetes Secret
kubectl create secret generic aws-credentials \
  --from-literal=access_key_id=AKIA... \
  --from-literal=secret_access_key=wJal...
```

### 3. Enable Encryption at Rest

```bash
# S3 bucket encryption
aws s3api put-bucket-encryption \
  --bucket claude-agent-production \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 4. Implement IAM Roles (Not Access Keys)

```yaml
# EKS: Use IAM roles for service accounts (IRSA)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: claude-agent
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789:role/claude-agent-role
```

---

## Testing Cloud Deployment Locally

### MinIO (S3-Compatible Local Storage)

```bash
# Start MinIO locally
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Configure app to use MinIO
export STORAGE_BACKEND=s3
export S3_BUCKET=test-bucket
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
export AWS_ENDPOINT_URL=http://localhost:9000

# Test storage backend
python -c "
from core.storage_backend import get_storage_backend
import asyncio

async def test():
    storage = get_storage_backend()
    await storage.write_file('test.txt', b'hello world')
    content = await storage.read_file('test.txt')
    print(f'Read: {content.decode()}')

asyncio.run(test())
"
```

---

## Summary

### ✅ What You Need for Cloud Deployment

1. **External Database**: PostgreSQL (not SQLite)
2. **External Redis**: Elasticache, Cloud Memorystore, etc.
3. **Object Storage**: S3, GCS, Azure Blob
4. **Secrets Manager**: AWS Secrets Manager, Vault, etc.
5. **Update Environment Variables**: `STORAGE_BACKEND=s3`, etc.

### ❌ What Won't Work in Cloud

1. **Local filesystem** (`/data/`) - ephemeral
2. **Named volumes** - not shared across pods
3. **SQLite** - file-based, not suitable for multi-instance

### 🔑 Key Takeaway

**Docker with volumes** ≠ **Cloud deployment**

You MUST use external storage (S3, etc.) for cloud deployments, or ALL user data will be lost on pod restarts.

---

**Last Updated**: 2026-01-22
**Reviewed By**: Claude Code Agent
**Version**: 1.0.0
