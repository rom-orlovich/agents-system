#!/bin/bash

# Health check for ECS/Load Balancer

# Check if init completed
if [ ! -f /tmp/healthy ]; then
    echo "Init not complete"
    exit 1
fi

# Check Claude CLI
if ! claude --version >/dev/null 2>&1; then
    echo "Claude CLI not working"
    exit 1
fi

# Check token validity (< 10 minutes = unhealthy) if using OAuth
CREDS="/root/.claude/.credentials.json"
if [ -f "$CREDS" ]; then
    EXPIRES=$(python3 -c "
import json
import time
from datetime import datetime
try:
    with open('$CREDS') as f:
        data = json.load(f)
        # Handle nested structure if present
        creds = data.get('claudeAiOauth', data)
        expires_at = creds.get('expiresAt', creds.get('expires_at', 0))
        # Support both ms and s timestamps
        if expires_at > 1000000000000:
            expires_at = expires_at / 1000
        now = time.time()
        print(int(expires_at - now))
except Exception:
    print(0)
")
    
    if [ "$EXPIRES" -lt 600 ]; then
        echo "Token expiring soon or invalid: $EXPIRES seconds"
        exit 1
    fi
fi

# Check process life
if [ -n "$CHECK_PROCESS" ]; then
    if ! pgrep -f "$CHECK_PROCESS" > /dev/null; then
        echo "Worker process $CHECK_PROCESS not found"
        exit 1
    fi
fi

echo "Healthy"
exit 0
