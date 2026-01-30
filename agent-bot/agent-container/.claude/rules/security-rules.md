# Security Rules

## Enforcement Level
CRITICAL - Must be followed at all times

## Core Principles
1. Never commit secrets or credentials
2. Validate all external input
3. Use principle of least privilege
4. Sanitize all output
5. Fail securely

## Secrets Management

### Prohibited
- Hardcoded API keys, tokens, passwords
- Credentials in environment variables committed to git
- Secrets in configuration files
- Private keys in codebase

### Required
- Use secret management service (HashiCorp Vault, AWS Secrets Manager)
- Rotate secrets regularly
- Encrypt secrets at rest
- Never log secrets

### Detection
```python
SECRET_PATTERNS = [
    r'api[_-]?key\s*=\s*["\']([^"\']+)["\']',
    r'password\s*=\s*["\']([^"\']+)["\']',
    r'token\s*=\s*["\']([^"\']+)["\']',
    r'(ghp|gho|github)_[A-Za-z0-9]{36}',
]
```

## Input Validation

### All External Input
- GitHub webhook payloads
- Jira webhook payloads
- User commands
- File uploads
- API parameters

### Validation Requirements
```python
from pydantic import BaseModel, ConfigDict, Field

class WebhookPayload(BaseModel):
    model_config = ConfigDict(strict=True)

    repository: str = Field(pattern=r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$')
    action: Literal["opened", "synchronize", "closed"]
    pr_number: int = Field(gt=0, lt=100000)
```

### SQL Injection Prevention
- NEVER use string concatenation for SQL
- ALWAYS use parameterized queries
- Use ORM (SQLAlchemy) with proper escaping

## Command Injection Prevention

### Prohibited
```python
os.system(f"git clone {user_input}")
subprocess.run(f"rm -rf {user_input}", shell=True)
```

### Required
```python
subprocess.run(["git", "clone", validated_url], shell=False)
subprocess.run(["rm", "-rf", validated_path], shell=False)
```

## XSS Prevention

### Output Sanitization
- Escape all user-provided content in markdown
- Sanitize before posting to GitHub/Jira/Slack
- Use proper markdown escaping functions

### Prohibited
```python
comment = f"## Result\n\n{user_input}"
```

### Required
```python
from markupsafe import escape
comment = f"## Result\n\n{escape(user_input)}"
```

## Authentication & Authorization

### Token Handling
- Tokens stored encrypted
- Tokens scoped to minimum required permissions
- Token expiration enforced
- Refresh tokens rotated

### Access Control
- Verify installation is active before processing
- Check organization membership
- Validate webhook signatures
- Enforce rate limits per organization

## File Access Security

### Allowed Paths
```python
ALLOWED_PATHS = [
    "/data/repos/*",
    "/data/logs/*",
    "/app/tmp/*"
]
```

### Prohibited
- Access to system directories (/etc, /root, /home)
- Reading arbitrary files
- Following symlinks outside allowed paths
- Executing arbitrary binaries

## Dependency Security

### Required
- Regular dependency scans
- Pin all dependency versions
- No dependencies with known CVEs (Critical/High)
- License compliance checks

### Prohibited
- Using deprecated packages
- Packages without recent updates (> 2 years)
- Packages with < 1000 downloads (suspicious)

## Safe Operations

### Git Operations
- Validate repository URLs
- Use HTTPS only (no git:// protocol)
- Limit clone depth
- Timeout git operations
- Verify signatures when applicable

### File Operations
- Validate file paths
- Check file sizes before reading
- Limit concurrent file operations
- Use temporary directories with cleanup

## Error Handling

### Never Expose
- Stack traces to users
- Internal system paths
- Database connection strings
- Secret values in logs

### Required
- Generic error messages to users
- Detailed logs internally (without secrets)
- Structured error responses

## Logging Security

### Never Log
```python
logger.info("user_login", password=password)  # WRONG
logger.info("api_call", api_key=api_key)     # WRONG
```

### Required
```python
logger.info("user_login", user_id=user_id)
logger.info("api_call", endpoint=endpoint)
```

### Sanitize Logged Data
```python
def sanitize_for_logging(data: dict) -> dict:
    sensitive_keys = ["password", "token", "api_key", "secret"]
    return {
        k: "***REDACTED***" if k in sensitive_keys else v
        for k, v in data.items()
    }
```

## Rate Limiting

### Enforce Limits
- Per organization: 100 requests/hour
- Per endpoint: 20 requests/minute
- Burst allowance: 10 requests
- Block on excessive failures: 5 failures in 10 minutes

## Security Headers

### Required for API Responses
```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000",
}
```

## Escalation

### Immediate Block & Alert
- Hardcoded secret detected
- SQL injection attempt
- Path traversal attempt
- Unauthorized access attempt

### Security Review Required
- New external integrations
- Changes to authentication logic
- Privilege escalation
- Cryptographic changes
