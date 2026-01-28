"""Unit tests for command configuration models and services."""

import pytest
from pathlib import Path
from domain.models.commands import (
    CommandPrefix,
    CommandDefinition,
    CommandsConfig,
    BotPatterns,
    CommandDefaults,
    get_commands_config,
    reload_commands_config,
    load_commands_config,
    _get_default_config,
)


class TestCommandPrefix:
    def test_valid_at_prefix(self):
        prefix = CommandPrefix(prefix="@agent", description="Test")
        assert prefix.prefix == "@agent"
        assert prefix.enabled is True

    def test_valid_slash_prefix(self):
        prefix = CommandPrefix(prefix="/claude", description="Test")
        assert prefix.prefix == "/claude"

    def test_prefix_normalized_to_lowercase(self):
        prefix = CommandPrefix(prefix="@AGENT", description="Test")
        assert prefix.prefix == "@agent"

    def test_invalid_prefix_without_at_or_slash(self):
        with pytest.raises(ValueError):
            CommandPrefix(prefix="agent", description="Test")


class TestCommandDefinition:
    def test_valid_command(self):
        cmd = CommandDefinition(name="review", description="Review code", target_agent="planning")
        assert cmd.name == "review"
        assert cmd.requires_approval is False

    def test_command_with_aliases(self):
        cmd = CommandDefinition(
            name="approve",
            aliases=["lgtm", "ship-it"],
            target_agent="executor"
        )
        assert cmd.matches("approve")
        assert cmd.matches("lgtm")
        assert cmd.matches("LGTM")
        assert not cmd.matches("reject")

    def test_all_names_includes_aliases(self):
        cmd = CommandDefinition(
            name="fix",
            aliases=["implement", "execute"],
            target_agent="executor"
        )
        all_names = cmd.all_names
        assert "fix" in all_names
        assert "implement" in all_names
        assert "execute" in all_names

    def test_name_normalized_to_lowercase(self):
        cmd = CommandDefinition(name="REVIEW", target_agent="planning")
        assert cmd.name == "review"

    def test_requires_approval(self):
        cmd = CommandDefinition(name="fix", target_agent="executor", requires_approval=True)
        assert cmd.requires_approval is True


class TestBotPatterns:
    def test_usernames_normalized(self):
        patterns = BotPatterns(usernames=["GitHub-Actions[BOT]", "CLAUDE-agent"])
        assert "github-actions[bot]" in patterns.usernames
        assert "claude-agent" in patterns.usernames


class TestCommandsConfig:
    def test_enabled_prefixes(self):
        config = CommandsConfig(
            prefixes=[
                CommandPrefix(prefix="@agent", enabled=True),
                CommandPrefix(prefix="/agent", enabled=False),
                CommandPrefix(prefix="@claude", enabled=True),
            ],
            commands=[],
        )
        assert "@agent" in config.enabled_prefixes
        assert "@claude" in config.enabled_prefixes
        assert "/agent" not in config.enabled_prefixes

    def test_valid_command_names_includes_aliases(self):
        config = CommandsConfig(
            prefixes=[CommandPrefix(prefix="@agent")],
            commands=[
                CommandDefinition(name="approve", aliases=["lgtm", "ship-it"], target_agent="executor"),
            ],
        )
        valid_names = config.valid_command_names
        assert "approve" in valid_names
        assert "lgtm" in valid_names
        assert "ship-it" in valid_names

    def test_get_command_by_name(self):
        config = CommandsConfig(
            prefixes=[CommandPrefix(prefix="@agent")],
            commands=[
                CommandDefinition(name="review", aliases=["code-review"], target_agent="planning"),
            ],
        )
        cmd = config.get_command("review")
        assert cmd is not None
        assert cmd.name == "review"

        cmd = config.get_command("code-review")
        assert cmd is not None
        assert cmd.name == "review"

    def test_is_valid_command(self):
        config = CommandsConfig(
            prefixes=[CommandPrefix(prefix="@agent")],
            commands=[
                CommandDefinition(name="analyze", aliases=["analysis"], target_agent="planning"),
            ],
        )
        assert config.is_valid_command("analyze")
        assert config.is_valid_command("analysis")
        assert not config.is_valid_command("invalid")

    def test_has_prefix(self):
        config = CommandsConfig(
            prefixes=[
                CommandPrefix(prefix="@agent", enabled=True),
                CommandPrefix(prefix="/claude", enabled=True),
            ],
            commands=[],
        )
        assert config.has_prefix("@agent review this")
        assert config.has_prefix("Please /claude analyze")
        assert not config.has_prefix("no prefix here")

    def test_command_pattern_matches_all_prefixes(self):
        config = CommandsConfig(
            prefixes=[
                CommandPrefix(prefix="@agent", enabled=True),
                CommandPrefix(prefix="/claude", enabled=True),
            ],
            commands=[],
        )
        pattern = config.command_pattern

        match = pattern.search("@agent review this")
        assert match is not None
        assert match.group(1) == "@agent"
        assert match.group(2) == "review"

        match = pattern.search("/claude analyze")
        assert match is not None
        assert match.group(1) == "/claude"
        assert match.group(2) == "analyze"


class TestLoadCommandsConfig:
    def test_loads_from_yaml_file(self):
        config = load_commands_config()
        assert len(config.enabled_prefixes) > 0
        assert len(config.valid_command_names) > 0

    def test_default_config_has_required_prefixes(self):
        config = _get_default_config()
        prefixes = config.enabled_prefixes
        assert "@agent" in prefixes
        assert "/agent" in prefixes
        assert "@claude" in prefixes
        assert "/claude" in prefixes

    def test_default_config_has_core_commands(self):
        config = _get_default_config()
        core_commands = {"analyze", "plan", "fix", "review", "approve", "reject", "improve", "help"}
        for cmd in core_commands:
            assert config.is_valid_command(cmd), f"Core command '{cmd}' missing"


class TestGetCommandsConfig:
    def test_returns_cached_config(self):
        config1 = get_commands_config()
        config2 = get_commands_config()
        assert config1 is config2

    def test_reload_clears_cache(self):
        config1 = get_commands_config()
        config2 = reload_commands_config()
        config3 = get_commands_config()
        assert config2 is config3
