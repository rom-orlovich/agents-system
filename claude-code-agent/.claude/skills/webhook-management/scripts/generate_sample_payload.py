#!/usr/bin/env python3
"""
Generate sample webhook payloads for testing.
Usage: python generate_sample_payload.py --provider github --event-type issues.opened
"""

import argparse
import json
import sys
from datetime import datetime, timezone


SAMPLE_PAYLOADS = {
    "github": {
        "issues.opened": {
            "action": "opened",
            "issue": {
                "number": 123,
                "title": "Sample Issue: Fix login bug",
                "body": "Users are experiencing login failures. @agent analyze this issue.",
                "state": "open",
                "user": {
                    "login": "testuser",
                    "id": 12345
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "labels": [{"name": "bug"}, {"name": "priority:high"}]
            },
            "repository": {
                "name": "my-app",
                "full_name": "myorg/my-app",
                "private": False
            },
            "sender": {
                "login": "testuser"
            }
        },
        "issue_comment.created": {
            "action": "created",
            "issue": {
                "number": 123,
                "title": "Sample Issue: Fix login bug",
                "body": "Users are experiencing login failures.",
                "state": "open"
            },
            "comment": {
                "id": 456,
                "body": "@agent plan a fix for this",
                "user": {
                    "login": "testuser"
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            "repository": {
                "name": "my-app",
                "full_name": "myorg/my-app"
            }
        },
        "pull_request.opened": {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Fix authentication bug",
                "body": "@agent review this PR please",
                "state": "open",
                "user": {
                    "login": "developer"
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "head": {
                    "ref": "fix/auth-bug",
                    "sha": "abc123"
                },
                "base": {
                    "ref": "main",
                    "sha": "def456"
                }
            },
            "repository": {
                "name": "my-app",
                "full_name": "myorg/my-app"
            }
        }
    },
    "jira": {
        "issue.created": {
            "webhookEvent": "jira:issue_created",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Fix login authentication bug",
                    "description": "Users cannot login. @agent analyze this ticket.",
                    "issuetype": {
                        "name": "Bug"
                    },
                    "priority": {
                        "name": "High"
                    },
                    "project": {
                        "key": "PROJ",
                        "name": "My Project"
                    },
                    "assignee": {
                        "displayName": "John Doe",
                        "emailAddress": "john@example.com"
                    },
                    "status": {
                        "name": "To Do"
                    },
                    "created": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "issue.updated": {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Fix login authentication bug",
                    "description": "Users cannot login after recent deploy.",
                    "status": {
                        "name": "In Progress"
                    },
                    "assignee": {
                        "displayName": "Agent Bot"
                    },
                    "project": {
                        "key": "PROJ",
                        "name": "My Project"
                    }
                }
            },
            "changelog": {
                "items": [
                    {
                        "field": "assignee",
                        "fromString": "Unassigned",
                        "toString": "Agent Bot"
                    }
                ]
            }
        },
        "comment.created": {
            "webhookEvent": "comment_created",
            "comment": {
                "body": "@agent plan a fix for this issue",
                "author": {
                    "displayName": "Team Lead",
                    "emailAddress": "lead@example.com"
                },
                "created": datetime.now(timezone.utc).isoformat()
            },
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Fix login authentication bug",
                    "description": "Users cannot login.",
                    "project": {
                        "key": "PROJ",
                        "name": "My Project"
                    }
                }
            }
        }
    },
    "slack": {
        "app_mention": {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U123> analyze the recent deployment failures",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123456",
                "thread_ts": "1234567890.123456"
            },
            "team_id": "T123",
            "api_app_id": "A123"
        },
        "message": {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "Can someone help debug this error?",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123456"
            }
        }
    },
    "sentry": {
        "error.created": {
            "action": "created",
            "data": {
                "event": {
                    "title": "TypeError: Cannot read property 'user' of undefined",
                    "message": "TypeError: Cannot read property 'user' of undefined",
                    "level": "error",
                    "platform": "javascript",
                    "environment": "production",
                    "url": "https://sentry.io/organizations/my-org/issues/123/",
                    "exception": {
                        "values": [
                            {
                                "type": "TypeError",
                                "value": "Cannot read property 'user' of undefined",
                                "stacktrace": {
                                    "frames": [
                                        {
                                            "filename": "app.js",
                                            "function": "getUserData",
                                            "lineno": 42,
                                            "colno": 10
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    "tags": [
                        ["environment", "production"],
                        ["level", "error"]
                    ]
                }
            }
        },
        "error.assigned": {
            "action": "assigned",
            "data": {
                "issue": {
                    "id": "123456",
                    "title": "TypeError in user authentication",
                    "status": "unresolved",
                    "level": "error"
                }
            }
        }
    }
}


def generate_payload(provider: str, event_type: str, output_file: str = None):
    """Generate a sample payload for the given provider and event type."""

    if provider not in SAMPLE_PAYLOADS:
        print(f"❌ Unknown provider: {provider}", file=sys.stderr)
        print(f"   Supported providers: {', '.join(SAMPLE_PAYLOADS.keys())}", file=sys.stderr)
        sys.exit(1)

    if event_type not in SAMPLE_PAYLOADS[provider]:
        print(f"❌ Unknown event type for {provider}: {event_type}", file=sys.stderr)
        print(f"   Supported events: {', '.join(SAMPLE_PAYLOADS[provider].keys())}", file=sys.stderr)
        sys.exit(1)

    payload = SAMPLE_PAYLOADS[provider][event_type]

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"✅ Sample payload written to {output_file}")
    else:
        print(json.dumps(payload, indent=2))

    return payload


def list_available():
    """List all available providers and event types."""
    print("Available sample payloads:\n")
    for provider, events in SAMPLE_PAYLOADS.items():
        print(f"📦 {provider}:")
        for event_type in events.keys():
            print(f"   - {event_type}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample webhook payloads for testing"
    )
    parser.add_argument("--provider",
                       choices=["github", "jira", "slack", "sentry"],
                       help="Webhook provider")
    parser.add_argument("--event-type", help="Event type to generate")
    parser.add_argument("--output", help="Output file path (default: print to stdout)")
    parser.add_argument("--list", action="store_true",
                       help="List all available providers and event types")

    args = parser.parse_args()

    if args.list:
        list_available()
        return

    if not args.provider or not args.event_type:
        parser.error("--provider and --event-type are required (or use --list)")

    generate_payload(
        provider=args.provider,
        event_type=args.event_type,
        output_file=args.output
    )


if __name__ == "__main__":
    main()
