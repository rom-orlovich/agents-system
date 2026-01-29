#!/bin/bash
set -e

echo "========================================="
echo "Testing Webhook Composition Pattern"
echo "========================================="
echo

echo "1. Testing webhook composition pattern..."
uv run pytest tests/unit/test_webhook_composition_pattern.py -v

echo
echo "2. Testing webhook config loader..."
uv run pytest tests/unit/test_webhook_config_loader.py -v

echo
echo "3. Testing static webhook configs..."
uv run pytest tests/test_static_webhook_configs.py -v

echo
echo "4. Testing webhook routes..."
uv run pytest tests/integration/test_webhook_route_flow.py -v

echo
echo "5. Testing webhook handlers..."
uv run pytest tests/integration/test_webhook_handlers.py -v

echo
echo "========================================="
echo "✅ All webhook tests passed!"
echo "========================================="
