from agent_engine.core.config import CLIProviderType, Settings


class TestCLIProviderType:
    def test_claude_provider_value(self) -> None:
        assert CLIProviderType.CLAUDE.value == "claude"

    def test_cursor_provider_value(self) -> None:
        assert CLIProviderType.CURSOR.value == "cursor"


class TestSettings:
    def test_default_values(self) -> None:
        settings = Settings()
        assert settings.max_concurrent_tasks == 5
        assert settings.task_timeout_seconds == 3600
        assert settings.cli_provider == CLIProviderType.CLAUDE

    def test_model_selection_planning(self) -> None:
        settings = Settings()
        model = settings.get_model_for_agent("planning")
        assert "opus" in model

    def test_model_selection_executor(self) -> None:
        settings = Settings()
        model = settings.get_model_for_agent("executor")
        assert "sonnet" in model

    def test_model_selection_brain(self) -> None:
        settings = Settings()
        model = settings.get_model_for_agent("brain")
        assert "opus" in model

    def test_model_selection_default(self) -> None:
        settings = Settings()
        model = settings.get_model_for_agent("unknown")
        assert "sonnet" in model

    def test_bot_usernames_list(self) -> None:
        settings = Settings()
        usernames = settings.bot_usernames_list
        assert isinstance(usernames, list)
        assert "github-actions[bot]" in usernames

    def test_valid_commands_list(self) -> None:
        settings = Settings()
        commands = settings.valid_commands_list
        assert isinstance(commands, list)
        assert "analyze" in commands
        assert "plan" in commands

    def test_agents_dir_property(self) -> None:
        settings = Settings()
        agents_dir = settings.agents_dir
        assert str(agents_dir).endswith("agents")

    def test_skills_dir_property(self) -> None:
        settings = Settings()
        skills_dir = settings.skills_dir
        assert str(skills_dir).endswith("skills")
