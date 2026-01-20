#!/bin/bash
# Test the webhook approval flow

echo "============================================================"
echo "Testing GitHub Webhook Approval Flow"
echo "============================================================"

# Test 1: Health check
echo -e "\n📡 Test 1: Health check"
curl -s http://localhost:8000/health | jq '.'

# Test 2: Simulate GitHub PR comment with @agent approve
echo -e "\n💬 Test 2: Simulating GitHub PR comment '@agent approve'"

# Create a test payload (simplified GitHub webhook payload)
PAYLOAD='{
  "comment": {
    "id": 123456,
    "body": "@agent approve",
    "user": {
      "login": "testuser"
    }
  },
  "issue": {
    "number": 123,
    "html_url": "https://github.com/testorg/testrepo/pull/123"
  },
  "repository": {
    "full_name": "testorg/testrepo"
  }
}'

# Note: This will fail signature validation without GITHUB_WEBHOOK_SECRET
# But we can test the endpoint exists
echo "Payload:"
echo "$PAYLOAD" | jq '.'

echo -e "\nSending to webhook..."
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issue_comment" \
  -H "X-Hub-Signature-256: sha256=test" \
  -d "$PAYLOAD" \
  2>/dev/null | jq '.'

echo -e "\n============================================================"
echo "✅ Test complete!"
echo "============================================================"
echo ""
echo "Note: If you see 401 Unauthorized, that's expected without"
echo "a valid webhook secret. The important thing is the endpoint"
echo "exists and processes the request structure."
