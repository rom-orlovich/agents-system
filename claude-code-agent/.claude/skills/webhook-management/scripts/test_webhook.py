#!/usr/bin/env python3
"""
Test a webhook with a sample payload.
Usage: python test_webhook.py --webhook-id webhook-123 --event-type "issues.opened" --payload-file sample.json
"""

import argparse
import json
import requests
import sys
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def test_webhook(webhook_id, event_type, payload_file=None, payload_data=None):
    """Test a webhook with a sample payload."""
    
    # Load payload from file or use provided data
    if payload_file:
        try:
            with open(payload_file, 'r') as f:
                payload = json.load(f)
        except Exception as e:
            print(f"❌ Error reading payload file: {e}", file=sys.stderr)
            sys.exit(1)
    elif payload_data:
        payload = payload_data
    else:
        # Default sample payload
        payload = {
            "action": event_type,
            "issue": {
                "number": 123,
                "title": "Test Issue",
                "body": "This is a test issue for webhook testing"
            }
        }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/webhooks/test/{webhook_id}",
            json={
                "event_type": event_type,
                "payload": payload
            },
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ Webhook test successful!")
        print(f"   Webhook ID: {webhook_id}")
        print(f"   Event Type: {event_type}")
        print(f"   Result: {json.dumps(result, indent=2)}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error testing webhook: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test a webhook")
    parser.add_argument("--webhook-id", required=True, help="Webhook ID to test")
    parser.add_argument("--event-type", required=True, help="Event type to simulate")
    parser.add_argument("--payload-file", help="Path to JSON payload file")
    
    args = parser.parse_args()
    
    test_webhook(
        webhook_id=args.webhook_id,
        event_type=args.event_type,
        payload_file=args.payload_file
    )


if __name__ == "__main__":
    main()
