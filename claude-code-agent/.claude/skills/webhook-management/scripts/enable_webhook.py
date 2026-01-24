#!/usr/bin/env python3
"""
Enable or disable a webhook.
Usage: python enable_webhook.py --webhook-id webhook-123 --enable
       python enable_webhook.py --webhook-id webhook-123 --disable
"""

import argparse
import requests
import sys
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def toggle_webhook(webhook_id: str, enable: bool):
    """Enable or disable a webhook."""

    try:
        response = requests.patch(
            f"{API_BASE_URL}/api/webhooks/{webhook_id}",
            json={"enabled": enable},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        webhook = response.json()
        status = "enabled" if enable else "disabled"
        print(f"✅ Webhook '{webhook_id}' {status} successfully!")
        print(f"   Name: {webhook.get('name')}")
        print(f"   Provider: {webhook.get('provider')}")
        print(f"   Status: {'Enabled' if webhook.get('enabled') else 'Disabled'}")

        return webhook

    except requests.exceptions.RequestException as e:
        print(f"❌ Error updating webhook: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Enable or disable a webhook")
    parser.add_argument("--webhook-id", required=True, help="Webhook ID")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--enable", action="store_true", help="Enable the webhook")
    group.add_argument("--disable", action="store_true", help="Disable the webhook")

    args = parser.parse_args()

    toggle_webhook(
        webhook_id=args.webhook_id,
        enable=args.enable
    )


if __name__ == "__main__":
    main()
