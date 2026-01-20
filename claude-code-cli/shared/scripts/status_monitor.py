#!/usr/bin/env python3
import sys
import json
import os
import redis
from datetime import datetime

def main():
    # Read stdin
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return
        data = json.loads(input_data)
    except json.JSONDecodeError:
        return

    # Extract metrics
    context_usage = data.get("context_window", {})
    cost_usage = data.get("cost", {})
    
    # Get Task ID from env
    task_id = os.environ.get("CLAUDE_TASK_ID")
    if not task_id:
        # Fallback: try to infer from data or just exit
        # If we can't associate with a task, we can't do much
        return

    # Connect to Redis
    # Assuming REDIS_HOST is set in env (which it is for the worker)
    redis_host = os.environ.get("REDIS_HOST", "redis")
    try:
        r = redis.Redis(host=redis_host, port=6379, db=0)
    except Exception:
        return

    # Update session stats key
    # We use a hash to store the latest stats for the task
    stats_key = f"task:{task_id}:session_stats"
    
    # Prepare data
    stats_data = {
        "context_used_pct": str(context_usage.get("used_percentage", 0)),
        "context_remaining_pct": str(context_usage.get("remaining_percentage", 0)),
        "total_cost": str(cost_usage.get("total_cost_usd", 0)),
        "input_tokens": str(context_usage.get("current_usage", {}).get("input_tokens", 0)),
        "output_tokens": str(context_usage.get("current_usage", {}).get("output_tokens", 0)),
        "execution_duration_ms": str(cost_usage.get("total_duration_ms", 0)),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        r.hset(stats_key, mapping=stats_data)
        # Set expiry for 24 hours to avoid clutter
        r.expire(stats_key, 86400)
    except Exception:
        pass

    # Print a simple status line for the CLI
    # This is what will show up in the terminal if configured
    cost = float(stats_data['total_cost'])
    used = float(stats_data['context_used_pct'])
    
    # NEW: Store account-level metrics if available
    account_id = os.environ.get("CLAUDE_ACCOUNT_ID")
    if account_id:
        try:
            # Create a separate hash for account stats
            account_key = f"account:{account_id}:usage"
            
            # The user provided JSON example showed "usage limits" might be in the JSON
            # We'll try to extract them if they exist in standard fields or specific structure
            # Based on user screenshot: "Plan usage limits" -> "Current session", "Weekly limits"
            
            # Extract whatever looks relevant to account limits
            # The structure might be in 'cost', 'context_window', or a separate 'usage_limits' field
            # We store the raw interesting bits plus our aggregated session cost
            
            account_data = {
                "last_updated": stats_data["updated_at"],
                "active_task_id": task_id,
                "current_cost_usd": str(cost),
                "current_context_pct": str(used)
            }
            
            # Try to find limits in data
            if "usage_limits" in data:
                account_data["limits"] = json.dumps(data["usage_limits"])
            
            # Update Redis
            r.hset(account_key, mapping=account_data)
            r.expire(account_key, 604800) # 1 week retention
        except Exception:
            pass

    print(f"Ctx: {used}% | Cost: ${cost:.4f}")

if __name__ == "__main__":
    main()
