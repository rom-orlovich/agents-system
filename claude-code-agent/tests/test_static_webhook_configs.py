import pytest
from api.webhooks.github.constants import COMMANDS as GITHUB_COMMANDS, AGENT_TRIGGER_PREFIX as GITHUB_PREFIX
from api.webhooks.jira.constants import COMMANDS as JIRA_COMMANDS, AGENT_TRIGGER_PREFIX as JIRA_PREFIX
from api.webhooks.slack.constants import COMMANDS as SLACK_COMMANDS, AGENT_TRIGGER_PREFIX as SLACK_PREFIX
from api.webhooks.common.utils import match_command_from_text, check_trigger_prefix


def test_github_commands_structure():
    assert len(GITHUB_COMMANDS) > 0
    for cmd in GITHUB_COMMANDS:
        assert "name" in cmd
        assert "description" in cmd
        assert "target_agent" in cmd
        assert "requires_approval" in cmd
        assert "prompt_template" in cmd


def test_jira_commands_structure():
    assert len(JIRA_COMMANDS) > 0
    for cmd in JIRA_COMMANDS:
        assert "name" in cmd
        assert "description" in cmd
        assert "target_agent" in cmd
        assert "requires_approval" in cmd
        assert "prompt_template" in cmd


def test_slack_commands_structure():
    assert len(SLACK_COMMANDS) > 0
    for cmd in SLACK_COMMANDS:
        assert "name" in cmd
        assert "description" in cmd
        assert "target_agent" in cmd
        assert "requires_approval" in cmd
        assert "prompt_template" in cmd


def test_trigger_prefixes_defined():
    assert GITHUB_PREFIX == "@agent"
    assert JIRA_PREFIX == "@agent"
    assert SLACK_PREFIX == "@agent"


def test_match_command_from_text():
    github_analyze_cmd = next(c for c in GITHUB_COMMANDS if c["name"] == "analyze")
    
    matched = match_command_from_text("@agent analyze this issue", GITHUB_COMMANDS, GITHUB_PREFIX, ["@claude", "@bot"])
    assert matched is not None
    assert matched["name"] == "analyze"
    
    matched = match_command_from_text("@agent analysis of the bug", GITHUB_COMMANDS, GITHUB_PREFIX, ["@claude"])
    assert matched is not None
    assert matched["name"] == "analyze"
    
    matched = match_command_from_text("@claude plan this", GITHUB_COMMANDS, GITHUB_PREFIX, ["@claude"])
    assert matched is not None
    assert matched["name"] == "plan"


def test_check_trigger_prefix():
    assert check_trigger_prefix("@agent analyze", "@agent", ["@claude"]) == True
    assert check_trigger_prefix("@claude fix this", "@agent", ["@claude"]) == True
    assert check_trigger_prefix("@bot help", "@agent", ["@claude", "@bot"]) == True
    assert check_trigger_prefix("hello world", "@agent", ["@claude"]) == False
