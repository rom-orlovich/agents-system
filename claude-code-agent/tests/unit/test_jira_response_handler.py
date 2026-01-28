"""TDD tests for Jira domain response handler (Phase 5.1)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from api.webhooks.jira.models import JiraRoutingMetadata


class TestJiraResponseHandler:
    """Test Jira domain response handler behavior."""

    @pytest.mark.asyncio
    async def test_post_response_to_jira_ticket(self):
        """
        Business Rule: Response handler posts comment to Jira ticket.
        Behavior: When routing has issue_key, post comment to ticket.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-123",
            project_key="PROJ",
            user_name="test-user"
        )
        result = "Analysis complete: No issues found."

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock) as mock_script:
            mock_script.return_value = True

            success = await handler.post_response(routing, result)

            assert success is True
            mock_script.assert_called_once_with("PROJ-123", result)

    @pytest.mark.asyncio
    async def test_returns_false_when_missing_issue_key(self):
        """
        Business Rule: Handler returns False when issue_key is missing.
        Behavior: If routing.issue_key is empty, return False without posting.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="",
            project_key="PROJ"
        )

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock) as mock_script:
            success = await handler.post_response(routing, "test result")

            assert success is False
            mock_script.assert_not_called()

    @pytest.mark.asyncio
    async def test_validates_response_format(self):
        """
        Business Rule: Validates response format before posting.
        Behavior: Calls format validation with 'jira' type.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-456",
            project_key="PROJ"
        )
        result = "Jira analysis content"

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.jira.handlers.validate_response_format') as mock_validate:
            mock_validate.return_value = (True, "")

            await handler.post_response(routing, result)

            mock_validate.assert_called_once_with(result, "jira")

    @pytest.mark.asyncio
    async def test_posts_even_when_validation_fails(self):
        """
        Business Rule: Posts response even if format validation fails.
        Behavior: Validation failure logs warning but doesn't prevent posting.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-789",
            project_key="PROJ"
        )
        result = "Invalid format content"

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.jira.handlers.validate_response_format') as mock_validate, \
             patch('api.webhooks.jira.handlers.logger') as mock_logger:
            mock_validate.return_value = (False, "Format validation failed")

            success = await handler.post_response(routing, result)

            assert success is True
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_to_api_on_script_not_found(self):
        """
        Business Rule: Falls back to API when script not found.
        Behavior: If shell script doesn't exist, use direct API.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-123",
            project_key="PROJ"
        )

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock) as mock_script, \
             patch.object(handler, '_post_via_api', new_callable=AsyncMock) as mock_api, \
             patch('api.webhooks.jira.handlers.validate_response_format', return_value=(True, "")):
            mock_script.side_effect = FileNotFoundError("Script not found")
            mock_api.return_value = True

            success = await handler.post_response(routing, "test result")

            assert success is True
            mock_api.assert_called_once_with("PROJ-123", "test result")

    @pytest.mark.asyncio
    async def test_handles_script_exception(self):
        """
        Business Rule: Handler catches and logs script exceptions.
        Behavior: When script raises exception, fall back to API.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-123",
            project_key="PROJ"
        )

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock) as mock_script, \
             patch.object(handler, '_post_via_api', new_callable=AsyncMock) as mock_api, \
             patch('api.webhooks.jira.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.jira.handlers.logger') as mock_logger:
            mock_script.side_effect = Exception("Script error")
            mock_api.return_value = True

            success = await handler.post_response(routing, "test result")

            assert success is True
            mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_error_when_both_methods_fail(self):
        """
        Business Rule: Raises JiraResponseError when all methods fail.
        Behavior: If both script and API fail, raise error with context.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler
        from api.webhooks.jira.errors import JiraResponseError

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-123",
            project_key="PROJ"
        )

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock) as mock_script, \
             patch.object(handler, '_post_via_api', new_callable=AsyncMock) as mock_api, \
             patch('api.webhooks.jira.handlers.validate_response_format', return_value=(True, "")):
            mock_script.side_effect = FileNotFoundError("Script not found")
            mock_api.side_effect = Exception("API error")

            with pytest.raises(JiraResponseError) as exc_info:
                await handler.post_response(routing, "test result")

            assert exc_info.value.context.issue_key == "PROJ-123"

    @pytest.mark.asyncio
    async def test_logs_successful_post(self):
        """
        Business Rule: Logs successful ticket comment posting.
        Behavior: After posting, logs info with ticket key.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()
        routing = JiraRoutingMetadata(
            issue_key="PROJ-123",
            project_key="PROJ"
        )

        with patch.object(handler, '_post_via_script', new_callable=AsyncMock, return_value=True), \
             patch('api.webhooks.jira.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.jira.handlers.logger') as mock_logger:
            await handler.post_response(routing, "test result")

            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "jira_response_posted"
            assert call_args[1]["ticket"] == "PROJ-123"


class TestJiraResponseHandlerScript:
    """Test Jira response handler script-based posting."""

    @pytest.mark.asyncio
    async def test_script_executes_with_correct_args(self):
        """
        Business Rule: Script is called with correct arguments.
        Behavior: Calls post_comment.sh with ticket key and result.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="/home/agent"):
            mock_run.return_value = MagicMock(returncode=0)

            result = await handler._post_via_script("PROJ-123", "test body")

            assert result is True
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "post_comment.sh" in call_args[0]
            assert "PROJ-123" in call_args
            assert "test body" in call_args

    @pytest.mark.asyncio
    async def test_script_returns_false_on_nonzero_exit(self):
        """
        Business Rule: Script failure returns False.
        Behavior: Returns False when subprocess returns non-zero.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="/home/agent"):
            mock_run.return_value = MagicMock(returncode=1, stderr="Error")

            result = await handler._post_via_script("PROJ-123", "test body")

            assert result is False


class TestJiraResponseHandlerAPI:
    """Test Jira response handler API-based posting."""

    @pytest.mark.asyncio
    async def test_api_posts_to_jira_endpoint(self):
        """
        Business Rule: API fallback posts to Jira REST API.
        Behavior: Uses correct endpoint and ADF format.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get') as mock_env:
            mock_env.side_effect = lambda key: {
                "JIRA_BASE_URL": "https://test.atlassian.net",
                "JIRA_USER_EMAIL": "test@test.com",
                "JIRA_API_TOKEN": "test-token"
            }.get(key)
            mock_run.return_value = MagicMock(returncode=0)

            result = await handler._post_via_api("PROJ-123", "test body")

            assert result is True
            call_args = mock_run.call_args[0][0]
            assert "https://test.atlassian.net/rest/api/3/issue/PROJ-123/comment" in call_args

    @pytest.mark.asyncio
    async def test_api_returns_false_without_credentials(self):
        """
        Business Rule: API fails gracefully without credentials.
        Behavior: Returns False when Jira credentials not set.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler

        handler = JiraResponseHandler()

        with patch('os.environ.get', return_value=None):
            result = await handler._post_via_api("PROJ-123", "test body")

            assert result is False

    @pytest.mark.asyncio
    async def test_api_formats_body_as_adf(self):
        """
        Business Rule: API formats comment body in ADF format.
        Behavior: Body is wrapped in Atlassian Document Format structure.
        """
        from api.webhooks.jira.handlers import JiraResponseHandler
        import json

        handler = JiraResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get') as mock_env:
            mock_env.side_effect = lambda key: {
                "JIRA_BASE_URL": "https://test.atlassian.net",
                "JIRA_USER_EMAIL": "test@test.com",
                "JIRA_API_TOKEN": "test-token"
            }.get(key)
            mock_run.return_value = MagicMock(returncode=0)

            await handler._post_via_api("PROJ-123", "test body")

            call_args = mock_run.call_args[0][0]
            body_arg = None
            for i, arg in enumerate(call_args):
                if arg == "-d":
                    body_arg = json.loads(call_args[i + 1])
                    break

            assert body_arg is not None
            assert body_arg["body"]["type"] == "doc"
            assert body_arg["body"]["version"] == 1
            assert body_arg["body"]["content"][0]["type"] == "paragraph"
