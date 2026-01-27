#!/usr/bin/env python3
"""
List all configured webhooks.
Usage: python list_webhooks.py [--provider github|jira|slack|sentry] [--enabled-only]
"""

import argparse
import requests
import sys
import os
from typing import Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def list_webhooks(provider: Optional[str] = None, enabled_only: bool = False):
    """List all webhooks, optionally filtered by provider."""

    try:
        url = f"{API_BASE_URL}/api/webhooks"
        params = {}

        if provider:
            params["provider"] = provider
        if enabled_only:
            params["enabled"] = "true"

        response = requests.get(url, params=params)
        response.raise_for_status()

        webhooks = response.json()

        if not webhooks:
            print("No webhooks found.")
            return

        print(f"📋 Found {len(webhooks)} webhook(s):\n")

        for webhook in webhooks:
            status = "✅ Enabled" if webhook.get("enabled") else "❌ Disabled"
            print(f"{status} {webhook.get('name')}")
            print(f"   Provider: {webhook.get('provider')}")
            print(f"   Endpoint: {webhook.get('endpoint')}")
            print(f"   Commands: {len(webhook.get('commands', []))}")

            if webhook.get("triggers"):
                print(f"   Triggers: {', '.join(webhook.get('triggers'))}")

            print()

        return webhooks

    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing webhooks: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="List all webhooks")
    parser.add_argument("--provider", choices=["github", "jira", "slack", "sentry"],
                       help="Filter by provider")
    parser.add_argument("--enabled-only", action="store_true",
                       help="Only show enabled webhooks")

    args = parser.parse_args()

    list_webhooks(
        provider=args.provider,
        enabled_only=args.enabled_only
    )


if __name__ == "__main__":
    main()
