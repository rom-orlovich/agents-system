#!/bin/bash
set -e

BASE_URL=${BASE_URL:-"http://localhost:8080"}

function print_header() {
    echo ""
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo ""
}

function test_health_checks() {
    print_header "Testing Health Checks"

    services=("api-gateway:8080" "github-service:8081" "jira-service:8082" "slack-service:8083" "sentry-service:8084" "dashboard-api:8090")

    for service in "${services[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        echo "Testing $name..."

        response=$(curl -s "http://localhost:${port}/health")
        status=$(echo $response | jq -r '.status')

        if [ "$status" == "healthy" ]; then
            echo "✓ $name is healthy"
        else
            echo "✗ $name is unhealthy"
            exit 1
        fi
    done
}

function test_github_webhook() {
    print_header "Testing GitHub Webhook"

    payload='{
        "action": "created",
        "issue": {
            "number": 42,
            "body": "@agent analyze this issue"
        },
        "repository": {
            "full_name": "test/repo"
        },
        "sender": {
            "login": "test-user"
        }
    }'

    response=$(curl -s -X POST "${BASE_URL}/webhooks/github" \
        -H "Content-Type: application/json" \
        -H "X-GitHub-Event: issues" \
        -d "$payload")

    success=$(echo $response | jq -r '.success')
    task_id=$(echo $response | jq -r '.task_id')

    if [ "$success" == "true" ] && [ "$task_id" != "null" ]; then
        echo "✓ GitHub webhook processed successfully"
        echo "  Task ID: $task_id"
    else
        echo "✗ GitHub webhook failed"
        echo "$response"
        exit 1
    fi
}

function test_jira_webhook() {
    print_header "Testing Jira Webhook"

    payload='{
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "description": "Test issue description"
            }
        },
        "user": {
            "accountId": "user-123"
        }
    }'

    response=$(curl -s -X POST "${BASE_URL}/webhooks/jira" \
        -H "Content-Type: application/json" \
        -d "$payload")

    success=$(echo $response | jq -r '.success')

    if [ "$success" == "true" ]; then
        echo "✓ Jira webhook processed successfully"
    else
        echo "✗ Jira webhook failed"
        exit 1
    fi
}

function test_metrics() {
    print_header "Testing Metrics Endpoint"

    response=$(curl -s "${BASE_URL}/metrics")

    if echo "$response" | grep -q "webhook_requests_total"; then
        echo "✓ Metrics endpoint responding"
    else
        echo "✗ Metrics endpoint not working"
        exit 1
    fi
}

function test_dashboard_api() {
    print_header "Testing Dashboard API"

    response=$(curl -s "http://localhost:8090/api/v1/dashboard/analytics?period_days=7")

    if echo "$response" | jq -e '.overall_metrics' > /dev/null; then
        echo "✓ Dashboard analytics endpoint working"
    else
        echo "✗ Dashboard analytics endpoint failed"
        exit 1
    fi
}

function run_all_tests() {
    test_health_checks
    test_github_webhook
    test_jira_webhook
    test_metrics
    test_dashboard_api

    print_header "✅ All Tests Passed!"
}

case "${1:-all}" in
    health) test_health_checks ;;
    github) test_github_webhook ;;
    jira) test_jira_webhook ;;
    metrics) test_metrics ;;
    dashboard) test_dashboard_api ;;
    all) run_all_tests ;;
    *)
        echo "Usage: $0 {health|github|jira|metrics|dashboard|all}"
        exit 1
        ;;
esac
