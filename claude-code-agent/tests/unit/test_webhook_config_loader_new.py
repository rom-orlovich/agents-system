import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from pydantic import ValidationError
from core.webhook_config_loader import WebhookConfigLoader
from shared.machine_models import WebhookConfig, WebhookCommand


@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / "webhooks"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def valid_github_config():
    return {
        "name": "github",
        "endpoint": "/webhooks/github",
        "source": "github",
        "command_prefix": "@agent",
        "requires_signature": True,
        "signature_header": "X-Hub-Signature-256",
        "secret_env_var": "GITHUB_WEBHOOK_SECRET",
        "default_command": "analyze",
        "commands": [
            {
                "name": "analyze",
                "aliases": ["analysis"],
                "description": "Analyze an issue",
                "target_agent": "planning",
                "prompt_template": "Analyze issue {{issue.number}}",
                "requires_approval": False,
            },
            {
                "name": "fix",
                "aliases": ["implement"],
                "description": "Fix an issue",
                "target_agent": "executor",
                "prompt_template": "Fix issue {{issue.number}}",
                "requires_approval": True,
            },
        ],
    }


@pytest.fixture
def valid_schema():
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["name", "endpoint", "source", "commands"],
        "properties": {
            "name": {"type": "string"},
            "endpoint": {"type": "string"},
            "source": {"type": "string"},
            "commands": {"type": "array", "minItems": 1},
        },
    }


class TestWebhookConfigLoader:
    def test_load_valid_webhook_config(self, temp_config_dir, valid_github_config, valid_schema):
        github_yaml = temp_config_dir / "github.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        config = loader.load_webhook_config("github")

        assert config.name == "github"
        assert config.endpoint == "/webhooks/github"
        assert config.source == "github"
        assert len(config.commands) == 2
        assert config.commands[0].name == "analyze"
        assert config.commands[1].name == "fix"

    def test_load_nonexistent_config(self, temp_config_dir):
        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load_webhook_config("nonexistent")
        assert "webhook config not found" in str(exc_info.value).lower()

    def test_load_invalid_yaml(self, temp_config_dir):
        invalid_yaml = temp_config_dir / "invalid.yaml"
        with open(invalid_yaml, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(yaml.YAMLError):
            loader.load_webhook_config("invalid")

    def test_load_config_with_validation_error(self, temp_config_dir, valid_schema):
        invalid_config = {
            "name": "test",
            "endpoint": "/webhooks/test",
            "source": "custom",
            "commands": [],
        }

        test_yaml = temp_config_dir / "test.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(test_yaml, "w") as f:
            yaml.dump(invalid_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(ValueError):
            loader.load_webhook_config("test")

    def test_load_config_without_schema(self, temp_config_dir, valid_github_config):
        github_yaml = temp_config_dir / "github.yaml"
        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        config = loader.load_webhook_config("github")
        assert config.name == "github"

    def test_load_all_webhook_configs(self, temp_config_dir, valid_github_config, valid_schema):
        github_yaml = temp_config_dir / "github.yaml"
        jira_config = valid_github_config.copy()
        jira_config["name"] = "jira"
        jira_config["endpoint"] = "/webhooks/jira"
        jira_config["source"] = "jira"
        jira_yaml = temp_config_dir / "jira.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(jira_yaml, "w") as f:
            yaml.dump(jira_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        configs = loader.load_all_webhook_configs()

        assert "github" in configs
        assert "jira" in configs
        assert configs["github"].name == "github"
        assert configs["jira"].name == "jira"

    def test_load_all_with_one_invalid_config(
        self, temp_config_dir, valid_github_config, valid_schema
    ):
        github_yaml = temp_config_dir / "github.yaml"
        invalid_yaml = temp_config_dir / "invalid.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(invalid_yaml, "w") as f:
            f.write("invalid: yaml: [unclosed")
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(Exception):
            loader.load_all_webhook_configs()

    def test_schema_validation_missing_required_field(self, temp_config_dir, valid_schema):
        config = {
            "name": "test",
            "endpoint": "/webhooks/test",
            "source": "custom",
        }

        test_yaml = temp_config_dir / "test.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(test_yaml, "w") as f:
            yaml.dump(config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(ValueError) as exc_info:
            loader.load_webhook_config("test")
        assert "commands" in str(exc_info.value).lower()

    def test_pydantic_validation_invalid_command_name(self, temp_config_dir, valid_schema):
        config = {
            "name": "test",
            "endpoint": "/webhooks/test",
            "source": "custom",
            "commands": [
                {
                    "name": "INVALID_NAME",
                    "target_agent": "planning",
                    "prompt_template": "test",
                }
            ],
        }

        test_yaml = temp_config_dir / "test.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(test_yaml, "w") as f:
            yaml.dump(config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(ValueError):
            loader.load_webhook_config("test")

    def test_duplicate_command_names(self, temp_config_dir, valid_schema):
        config = {
            "name": "test",
            "endpoint": "/webhooks/test",
            "source": "custom",
            "commands": [
                {
                    "name": "analyze",
                    "target_agent": "planning",
                    "prompt_template": "test1",
                },
                {
                    "name": "analyze",
                    "target_agent": "executor",
                    "prompt_template": "test2",
                },
            ],
        }

        test_yaml = temp_config_dir / "test.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(test_yaml, "w") as f:
            yaml.dump(config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(ValueError) as exc_info:
            loader.load_webhook_config("test")
        assert "duplicate" in str(exc_info.value).lower()

    def test_default_command_not_in_commands(self, temp_config_dir, valid_schema):
        config = {
            "name": "test",
            "endpoint": "/webhooks/test",
            "source": "custom",
            "default_command": "nonexistent",
            "commands": [
                {
                    "name": "analyze",
                    "target_agent": "planning",
                    "prompt_template": "test",
                }
            ],
        }

        test_yaml = temp_config_dir / "test.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(test_yaml, "w") as f:
            yaml.dump(config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        with pytest.raises(ValueError) as exc_info:
            loader.load_webhook_config("test")
        assert "not found in commands" in str(exc_info.value).lower()

    def test_config_with_valid_default_command(self, temp_config_dir, valid_github_config, valid_schema):
        github_yaml = temp_config_dir / "github.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        config = loader.load_webhook_config("github")

        assert config.default_command == "analyze"
        assert any(cmd.name == "analyze" for cmd in config.commands)

    def test_config_with_command_aliases(self, temp_config_dir, valid_github_config, valid_schema):
        github_yaml = temp_config_dir / "github.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        config = loader.load_webhook_config("github")

        assert config.commands[0].aliases == ["analysis"]
        assert config.commands[1].aliases == ["implement"]

    def test_config_with_requires_approval(self, temp_config_dir, valid_github_config, valid_schema):
        github_yaml = temp_config_dir / "github.yaml"
        schema_yaml = temp_config_dir / "schema.yaml"

        with open(github_yaml, "w") as f:
            yaml.dump(valid_github_config, f)
        with open(schema_yaml, "w") as f:
            yaml.dump(valid_schema, f)

        loader = WebhookConfigLoader(config_dir=temp_config_dir)
        config = loader.load_webhook_config("github")

        assert config.commands[0].requires_approval is False
        assert config.commands[1].requires_approval is True
