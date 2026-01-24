#!/usr/bin/env python3
"""
Delete a webhook by ID.
Usage: python delete_webhook.py --webhook-id webhook-123 [--force]
"""

import argparse
import requests
import sys
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def delete_webhook(webhook_id: str, force: bool = False):
    """Delete a webhook by ID."""

    if not force:
        confirm = input(f"⚠️  Are you sure you want to delete webhook '{webhook_id}'? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Deletion cancelled.")
            return

    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/webhooks/{webhook_id}"
        )
        response.raise_for_status()

        print(f"✅ Webhook '{webhook_id}' deleted successfully!")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error deleting webhook: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Delete a webhook")
    parser.add_argument("--webhook-id", required=True, help="Webhook ID to delete")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompt")

    args = parser.parse_args()

    delete_webhook(
        webhook_id=args.webhook_id,
        force=args.force
    )


if __name__ == "__main__":
    main()
