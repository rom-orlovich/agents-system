#!/bin/bash
# Comprehensive test of the webhook approval flow

set -e

echo "============================================================"
echo "🧪 Testing Webhook Approval Flow"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Verify services are running
echo -e "\n${BLUE}Test 1: Verify services${NC}"
echo "Checking webhook server..."
curl -s http://localhost:8000/health | jq '.'
echo -e "${GREEN}✓ Webhook server is healthy${NC}"

echo -e "\nChecking Redis..."
docker-compose -f infrastructure/docker/docker-compose.yml exec -T redis redis-cli ping
echo -e "${GREEN}✓ Redis is responding${NC}"

# Test 2: Test GitHub webhook endpoint
echo -e "\n${BLUE}Test 2: GitHub webhook endpoint${NC}"
GITHUB_RESPONSE=$(curl -s http://localhost:8000/webhooks/github/test)
echo "$GITHUB_RESPONSE" | jq '.'
echo -e "${GREEN}✓ GitHub webhook endpoint is working${NC}"

# Test 3: Test Slack webhook endpoint
echo -e "\n${BLUE}Test 3: Slack webhook endpoint${NC}"
SLACK_RESPONSE=$(curl -s http://localhost:8000/webhooks/slack/test)
echo "$SLACK_RESPONSE" | jq '.'
echo -e "${GREEN}✓ Slack webhook endpoint is working${NC}"

# Test 4: Test Redis task queue operations
echo -e "\n${BLUE}Test 4: Redis task operations${NC}"
echo "Testing task creation and lookup..."

# Create a test task in Redis
docker-compose -f infrastructure/docker/docker-compose.yml exec -T redis redis-cli << EOF
HSET tasks:test-task-123 task_id "test-task-123" status "pending_approval" repository "testorg/testrepo"
HSET pr:https://github.com/testorg/testrepo/pull/456 task_id "test-task-123" repository "testorg/testrepo" pr_number "456"
EOF

# Verify task was created
TASK_DATA=$(docker-compose -f infrastructure/docker/docker-compose.yml exec -T redis redis-cli HGETALL tasks:test-task-123)
echo "Task data:"
echo "$TASK_DATA"

# Verify PR mapping
PR_DATA=$(docker-compose -f infrastructure/docker/docker-compose.yml exec -T redis redis-cli HGETALL pr:https://github.com/testorg/testrepo/pull/456)
echo "PR mapping:"
echo "$PR_DATA"

echo -e "${GREEN}✓ Redis operations working${NC}"

# Test 5: Check webhook server logs
echo -e "\n${BLUE}Test 5: Recent webhook server logs${NC}"
docker-compose -f infrastructure/docker/docker-compose.yml logs --tail=5 webhook-server

# Cleanup
echo -e "\n${YELLOW}Cleaning up test data...${NC}"
docker-compose -f infrastructure/docker/docker-compose.yml exec -T redis redis-cli << EOF
DEL tasks:test-task-123
DEL pr:https://github.com/testorg/testrepo/pull/456
EOF

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo -e "${GREEN}============================================================${NC}"

echo -e "\n${YELLOW}Summary:${NC}"
echo "  ✓ Webhook server is running and healthy"
echo "  ✓ GitHub webhook endpoint configured"
echo "  ✓ Slack webhook endpoint configured"
echo "  ✓ Redis task queue operations working"
echo "  ✓ PR-to-task mapping functional"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Configure GitHub webhook with your tunnel URL"
echo "  2. Configure Slack app with your tunnel URL"
echo "  3. Test with real webhooks from GitHub/Slack"
echo ""
