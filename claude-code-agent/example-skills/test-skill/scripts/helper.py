#!/usr/bin/env python3
"""Example helper script for test-skill."""

def process_task(task_name):
    """Process a task and return results."""
    print(f"Processing task: {task_name}")
    return {"status": "success", "task": task_name}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = process_task(sys.argv[1])
        print(f"Result: {result}")
    else:
        print("Usage: helper.py <task_name>")
