#!/usr/bin/env python3
"""
Validate a webhook configuration before deployment.
Usage: python validate_webhook.py --config webhook_config.json
"""

import argparse
import json
import sys
import re
from typing import Dict, Any, List


def validate_webhook_config(config: Dict[str, Any]) -> List[str]:
    """Validate a webhook configuration and return list of errors."""
    errors = []

    # Required fields
    required_fields = ["name", "endpoint", "source", "description", "target_agent"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    if errors:  # Don't continue if basic fields are missing
        return errors

    # Validate name (alphanumeric, hyphens, underscores)
    if not re.match(r"^[a-zA-Z0-9_-]+$", config.get("name", "")):
        errors.append("name must be alphanumeric with hyphens and underscores only")

    # Validate endpoint pattern
    endpoint = config.get("endpoint", "")
    if not re.match(r"^/webhooks/[a-z0-9-]+$", endpoint):
        errors.append(f"endpoint must match pattern /webhooks/[provider-name]: {endpoint}")

    # Validate source
    valid_sources = ["github", "jira", "slack", "sentry", "custom"]
    if config.get("source") not in valid_sources:
        errors.append(f"source must be one of {valid_sources}")

    # Validate target_agent
    valid_agents = ["brain", "planning", "executor", "custom"]
    if config.get("target_agent") not in valid_agents:
        errors.append(f"target_agent must be one of {valid_agents}")

    # Validate commands
    commands = config.get("commands", [])
    if not commands:
        errors.append("At least one command is required")
    else:
        command_names = set()
        for idx, cmd in enumerate(commands):
            cmd_name = cmd.get("name", f"command_{idx}")

            # Check for duplicate command names
            if cmd_name in command_names:
                errors.append(f"Duplicate command name: {cmd_name}")
            command_names.add(cmd_name)

            # Validate command fields
            if "name" not in cmd:
                errors.append(f"Command {idx} missing required field: name")
            if "target_agent" not in cmd:
                errors.append(f"Command '{cmd_name}' missing required field: target_agent")
            if "prompt_template" not in cmd:
                errors.append(f"Command '{cmd_name}' missing required field: prompt_template")

            # Validate command name pattern
            if cmd.get("name") and not re.match(r"^[a-z0-9_-]+$", cmd["name"]):
                errors.append(f"Command name must be lowercase alphanumeric: {cmd['name']}")

            # Validate target_agent
            if cmd.get("target_agent") not in valid_agents:
                errors.append(f"Command '{cmd_name}' has invalid target_agent: {cmd.get('target_agent')}")

            # Check prompt_template for common issues
            template = cmd.get("prompt_template", "")
            if not template.strip():
                errors.append(f"Command '{cmd_name}' has empty prompt_template")

            # Warn if template has no variables (might be intentional)
            if "{{" not in template:
                print(f"⚠️  Warning: Command '{cmd_name}' prompt_template has no variables", file=sys.stderr)

    # Validate signature settings
    if config.get("requires_signature", True):
        if "signature_header" not in config:
            errors.append("requires_signature is true but signature_header is missing")
        if "secret_env_var" not in config:
            errors.append("requires_signature is true but secret_env_var is missing")

        # Validate signature_header format
        sig_header = config.get("signature_header", "")
        if sig_header and not re.match(r"^X-[A-Za-z0-9-]+$", sig_header):
            errors.append(f"signature_header should follow X-* pattern: {sig_header}")

    # Validate default_command exists
    default_cmd = config.get("default_command")
    if default_cmd:
        cmd_names = [cmd.get("name") for cmd in commands]
        if default_cmd not in cmd_names:
            errors.append(f"default_command '{default_cmd}' not found in commands list")

    return errors


def validate_from_file(filepath: str) -> bool:
    """Validate a webhook configuration file."""
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return False

    errors = validate_webhook_config(config)

    if errors:
        print(f"❌ Validation failed with {len(errors)} error(s):\n")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ Webhook configuration is valid!")
        print(f"   Name: {config.get('name')}")
        print(f"   Provider: {config.get('source')}")
        print(f"   Endpoint: {config.get('endpoint')}")
        print(f"   Commands: {len(config.get('commands', []))}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Validate a webhook configuration"
    )
    parser.add_argument("--config", required=True,
                       help="Path to webhook configuration JSON file")

    args = parser.parse_args()

    success = validate_from_file(args.config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
