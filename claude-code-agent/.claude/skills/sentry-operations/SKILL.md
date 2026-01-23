---
name: sentry-operations
description: Sentry CLI commands for error analysis, releases, and performance monitoring
user-invocable: false
---

Sentry operations using `sentry-cli` and Sentry API.

## Environment
- `SENTRY_AUTH_TOKEN` - Sentry authentication token
- `SENTRY_ORG` - Sentry organization slug
- `SENTRY_PROJECT` - Default project slug (optional)

## Common Commands

### Error Management
```bash
sentry-cli issues list --project myproject
sentry-cli issues show ISSUE-ID
sentry-cli issues resolve ISSUE-ID
sentry-cli issues list --query "is:unresolved level:error"
```

### Release Management
```bash
sentry-cli releases new v1.0.0
sentry-cli releases set-commits v1.0.0 --auto
sentry-cli releases finalize v1.0.0
sentry-cli releases list
sentry-cli releases deploys v1.0.0 new -e production
```

### Event Analysis
```bash
sentry-cli send-event -m "Test event" --level error
sentry-cli events list --project myproject --max 10
```

### Organization & Project Info
```bash
sentry-cli projects list
sentry-cli info
sentry-cli login --auth-token $SENTRY_AUTH_TOKEN
```

## Error Analysis Workflows

### Identify Error Spike
```bash
sentry-cli issues list --query "is:unresolved" --project myproject
sentry-cli issues list --query "firstSeen:>2024-01-01"
sentry-cli issues list --query "is:unresolved" | jq 'group_by(.type)'
```

### Root Cause Analysis
```bash
sentry-cli issues show ISSUE-ID --full
sentry-cli events list --issue ISSUE-ID --max 50
sentry-cli issues show ISSUE-ID | jq '.userCount'
```

### Release Health Check
```bash
sentry-cli releases list --max 5
sentry-cli releases info v1.0.0
sentry-cli issues list --query "firstRelease:v1.0.0"
```

## Helper Script

Use `scripts/analyze_sentry_error.sh` to analyze Sentry errors:
```bash
./scripts/analyze_sentry_error.sh SENTRY-ISSUE-ID
```

This creates SENTRY_ANALYSIS.md with investigation template.
