#!/usr/bin/env python3
"""
Create a new webhook configuration via API.
Usage: python create_webhook.py --provider github --name "My Webhook" --triggers "issues.opened"
"""

import argparse
import json
import requests
import sys
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def create_webhook(provider, name, triggers, mention_tags=None, assignee_triggers=None):
    """Create a webhook via the API."""
    
    webhook_data = {
        "provider": provider,
        "name": name,
        "enabled": True,
        "triggers": triggers.split(",") if isinstance(triggers, str) else triggers,
    }
    
    if mention_tags:
        webhook_data["mention_tags"] = mention_tags.split(",") if isinstance(mention_tags, str) else mention_tags
    
    if assignee_triggers:
        webhook_data["assignee_triggers"] = assignee_triggers.split(",") if isinstance(assignee_triggers, str) else assignee_triggers
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/webhooks",
            json=webhook_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        webhook = response.json()
        print(f"✅ Webhook created successfully!")
        print(f"   ID: {webhook.get('id')}")
        print(f"   Name: {webhook.get('name')}")
        print(f"   Provider: {webhook.get('provider')}")
        print(f"   Webhook URL: {API_BASE_URL}/api/webhooks/{webhook.get('provider')}/{webhook.get('id')}")
        
        return webhook
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating webhook: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create a new webhook")
    parser.add_argument("--provider", required=True, choices=["github", "jira", "slack", "sentry"],
                       help="Webhook provider")
    parser.add_argument("--name", required=True, help="Webhook name")
    parser.add_argument("--triggers", required=True, help="Comma-separated list of triggers")
    parser.add_argument("--mention-tags", help="Comma-separated list of mention tags (for GitHub)")
    parser.add_argument("--assignee-triggers", help="Comma-separated list of assignee names (for Jira)")
    
    args = parser.parse_args()
    
    create_webhook(
        provider=args.provider,
        name=args.name,
        triggers=args.triggers,
        mention_tags=args.mention_tags,
        assignee_triggers=args.assignee_triggers
    )


if __name__ == "__main__":
    main()
