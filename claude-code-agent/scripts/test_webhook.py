#!/usr/bin/env python3
"""Test webhook functionality with sample payloads."""

import json
import hmac
import hashlib
import httpx
import asyncio
from pathlib import Path


def generate_github_signature(payload: bytes, secret: str) -> str:
    """Generate GitHub HMAC signature."""
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


async def test_issue_comment_webhook(base_url: str, secret: str = None):
    """Test issue comment webhook."""
    payload = {
        "action": "created",
        "issue": {
            "number": 1,
            "title": "Test Issue",
            "body": "This is a test issue"
        },
        "comment": {
            "id": 123456,
            "body": "@agent please help with this issue"
        },
        "repository": {
            "full_name": "test-owner/test-repo"
        }
    }
    
    payload_bytes = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issue_comment"
    }
    
    if secret:
        headers["X-Hub-Signature-256"] = generate_github_signature(payload_bytes, secret)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/webhooks/github",
            content=payload_bytes,
            headers=headers,
            timeout=30.0
        )
        
        print(f"Issue Comment Webhook Test:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        print()


async def test_issue_opened_webhook(base_url: str, secret: str = None):
    """Test issue opened webhook."""
    payload = {
        "action": "opened",
        "issue": {
            "number": 2,
            "title": "Bug: Login not working",
            "body": "Users are unable to log in to the application"
        },
        "repository": {
            "full_name": "test-owner/test-repo"
        }
    }
    
    payload_bytes = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "issues"
    }
    
    if secret:
        headers["X-Hub-Signature-256"] = generate_github_signature(payload_bytes, secret)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/webhooks/github",
            content=payload_bytes,
            headers=headers,
            timeout=30.0
        )
        
        print(f"Issue Opened Webhook Test:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        print()


async def test_pr_opened_webhook(base_url: str, secret: str = None):
    """Test PR opened webhook."""
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 3,
            "title": "Fix: Resolve login issue",
            "body": "This PR fixes the login bug by updating authentication logic"
        },
        "repository": {
            "full_name": "test-owner/test-repo"
        }
    }
    
    payload_bytes = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request"
    }
    
    if secret:
        headers["X-Hub-Signature-256"] = generate_github_signature(payload_bytes, secret)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/webhooks/github",
            content=payload_bytes,
            headers=headers,
            timeout=30.0
        )
        
        print(f"PR Opened Webhook Test:")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.json()}")
        print()


async def main():
    """Run all webhook tests."""
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    secret = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Testing webhooks at: {base_url}")
    print(f"Using secret: {'Yes' if secret else 'No'}")
    print("=" * 60)
    print()
    
    await test_issue_comment_webhook(base_url, secret)
    await test_issue_opened_webhook(base_url, secret)
    await test_pr_opened_webhook(base_url, secret)
    
    print("=" * 60)
    print("✓ All webhook tests completed")


if __name__ == "__main__":
    asyncio.run(main())
