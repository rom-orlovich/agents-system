#!/bin/bash
set -e

echo "========================================="
echo "Testing Agent Bot Webhook Flow"
echo "========================================="
echo

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Please install with: pip install pytest"
    exit 1
fi

cd "$(dirname "$0")/../.."

echo "1. Running unit tests..."
cd agent-engine-package
python -m pytest tests/unit/ -v

echo
echo "2. Running webhook flow integration tests..."
python -m pytest tests/integration/test_webhook_flow.py -v

echo
echo "3. Running agent engine tests..."
python -m pytest tests/integration/test_agent_engine.py -v

echo
echo "4. Running E2E workflow tests..."
python -m pytest tests/integration/test_e2e_workflow.py -v

echo
echo "========================================="
echo "All webhook flow tests passed!"
echo "========================================="
