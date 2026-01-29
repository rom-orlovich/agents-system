"""TDD tests for GitHub domain response handler (Phase 5.1)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from api.webhooks.github.models import GitHubRoutingMetadata


class TestGitHubResponseHandler:
    """Test GitHub domain response handler behavior."""

    @pytest.mark.asyncio
    async def test_post_response_to_pr_comment(self):
        """
        Business Rule: Response handler posts comment to PR.
        Behavior: When routing has pr_number, post to PR.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            pr_number=123,
            sender="test-user"
        )
        result = "Analysis complete: No issues found."

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            mock_client.post_pr_comment = AsyncMock(return_value=True)

            success, response = await handler.post_response(routing, result)

            assert success is True
            mock_client.post_pr_comment.assert_called_once_with(
                "test-owner", "test-repo", 123, result
            )

    @pytest.mark.asyncio
    async def test_post_response_to_issue_comment(self):
        """
        Business Rule: Response handler posts comment to issue.
        Behavior: When routing has issue_number but no pr_number, post to issue.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456,
            sender="test-user"
        )
        result = "Issue analyzed successfully."

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            mock_client.post_issue_comment = AsyncMock(return_value=True)

            success, response = await handler.post_response(routing, result)

            assert success is True
            mock_client.post_issue_comment.assert_called_once_with(
                "test-owner", "test-repo", 456, result
            )

    @pytest.mark.asyncio
    async def test_returns_false_when_missing_owner(self):
        """
        Business Rule: Handler returns False when owner is missing.
        Behavior: If routing.owner is empty, return False without posting.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="",
            repo="test-repo",
            issue_number=123
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            mock_client.post_issue_comment = AsyncMock()

            success, response = await handler.post_response(routing, "test result")

            assert success is False
            mock_client.post_issue_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_when_missing_repo(self):
        """
        Business Rule: Handler returns False when repo is missing.
        Behavior: If routing.repo is empty, return False without posting.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="",
            issue_number=123
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            mock_client.post_issue_comment = AsyncMock()

            success, response = await handler.post_response(routing, "test result")

            assert success is False
            mock_client.post_issue_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_pr_or_issue(self):
        """
        Business Rule: Handler returns False when neither PR nor issue specified.
        Behavior: If routing has no pr_number and no issue_number, return False.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo"
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            success, response = await handler.post_response(routing, "test result")

            assert success is False

    @pytest.mark.asyncio
    async def test_pr_takes_priority_over_issue(self):
        """
        Business Rule: PR comment takes priority over issue comment.
        Behavior: When both pr_number and issue_number exist, post to PR.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            pr_number=123,
            issue_number=456,
            sender="test-user"
        )
        result = "Review complete."

        with patch('api.webhooks.github.handlers.github_client') as mock_client:
            mock_client.post_pr_comment = AsyncMock(return_value=True)
            mock_client.post_issue_comment = AsyncMock(return_value=True)

            success, response = await handler.post_response(routing, result)

            assert success is True
            mock_client.post_pr_comment.assert_called_once()
            mock_client.post_issue_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_validates_response_format_for_pr(self):
        """
        Business Rule: Validates response format before posting to PR.
        Behavior: Calls format validation with 'pr_review' type.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            pr_number=123
        )
        result = "PR Review content"

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format') as mock_validate:
            mock_client.post_pr_comment = AsyncMock(return_value=True)
            mock_validate.return_value = (True, "")

            success, response = await handler.post_response(routing, result)

            mock_validate.assert_called_once_with(result, "pr_review")

    @pytest.mark.asyncio
    async def test_validates_response_format_for_issue(self):
        """
        Business Rule: Validates response format before posting to issue.
        Behavior: Calls format validation with 'issue_analysis' type.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456
        )
        result = "Issue analysis content"

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format') as mock_validate:
            mock_client.post_issue_comment = AsyncMock(return_value=True)
            mock_validate.return_value = (True, "")

            success, response = await handler.post_response(routing, result)

            mock_validate.assert_called_once_with(result, "issue_analysis")

    @pytest.mark.asyncio
    async def test_posts_even_when_validation_fails(self):
        """
        Business Rule: Posts response even if format validation fails.
        Behavior: Validation failure logs warning but doesn't prevent posting.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456
        )
        result = "Invalid format content"

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format') as mock_validate, \
             patch('api.webhooks.github.handlers.logger') as mock_logger:
            mock_client.post_issue_comment = AsyncMock(return_value=True)
            mock_validate.return_value = (False, "Format validation failed")

            success, response = await handler.post_response(routing, result)

            assert success is True
            mock_client.post_issue_comment.assert_called_once()
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_handles_client_exception(self):
        """
        Business Rule: Handler catches and logs client exceptions.
        Behavior: When github_client raises exception, return False and log error.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler
        from api.webhooks.github.errors import GitHubResponseError

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format', return_value=(True, "")):
            mock_client.post_issue_comment = AsyncMock(side_effect=Exception("Network error"))

            with pytest.raises(GitHubResponseError) as exc_info:
                await handler.post_response(routing, "test result")

            assert "Network error" in str(exc_info.value)
            assert exc_info.value.context.repo == "test-owner/test-repo"
            assert exc_info.value.context.issue_number == 456

    @pytest.mark.asyncio
    async def test_fallback_to_curl_on_import_error(self):
        """
        Business Rule: Falls back to curl when github_client unavailable.
        Behavior: If github_client import fails, use curl-based posting.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456
        )

        with patch('api.webhooks.github.handlers.github_client', None), \
             patch('api.webhooks.github.handlers.validate_response_format', return_value=(True, "")), \
             patch.object(handler, '_post_with_curl', new_callable=AsyncMock) as mock_curl:
            mock_curl.return_value = True

            success, response = await handler.post_response(routing, "test result")

            assert success is True
            mock_curl.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_successful_pr_post(self):
        """
        Business Rule: Logs successful PR comment posting.
        Behavior: After posting to PR, logs info with type and number.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            pr_number=123
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.github.handlers.logger') as mock_logger:
            mock_client.post_pr_comment = AsyncMock(return_value=True)

            success, response = await handler.post_response(routing, "test result")

            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "github_response_posted"
            assert call_args[1]["type"] == "pr"
            assert call_args[1]["number"] == 123

    @pytest.mark.asyncio
    async def test_logs_successful_issue_post(self):
        """
        Business Rule: Logs successful issue comment posting.
        Behavior: After posting to issue, logs info with type and number.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()
        routing = GitHubRoutingMetadata(
            owner="test-owner",
            repo="test-repo",
            issue_number=456
        )

        with patch('api.webhooks.github.handlers.github_client') as mock_client, \
             patch('api.webhooks.github.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.github.handlers.logger') as mock_logger:
            mock_client.post_issue_comment = AsyncMock(return_value=True)

            success, response = await handler.post_response(routing, "test result")

            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "github_response_posted"
            assert call_args[1]["type"] == "issue"
            assert call_args[1]["number"] == 456


class TestGitHubResponseHandlerCurl:
    """Test GitHub response handler curl fallback."""

    @pytest.mark.asyncio
    async def test_curl_posts_to_issues_endpoint(self):
        """
        Business Rule: Curl fallback posts to GitHub issues API.
        Behavior: Uses correct endpoint for issue/PR comments.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="test-token"):
            mock_run.return_value = MagicMock(returncode=0)

            result = await handler._post_with_curl(
                "test-owner", "test-repo", 123, "test body"
            )

            assert result is True
            call_args = mock_run.call_args[0][0]
            assert "https://api.github.com/repos/test-owner/test-repo/issues/123/comments" in call_args

    @pytest.mark.asyncio
    async def test_curl_returns_false_without_token(self):
        """
        Business Rule: Curl fails gracefully without token.
        Behavior: Returns False when GITHUB_TOKEN not set.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()

        with patch('os.environ.get', return_value=None):
            result = await handler._post_with_curl(
                "test-owner", "test-repo", 123, "test body"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_curl_handles_process_error(self):
        """
        Business Rule: Curl handles subprocess errors gracefully.
        Behavior: Returns False when subprocess fails.
        """
        from api.webhooks.github.handlers import GitHubResponseHandler

        handler = GitHubResponseHandler()

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="test-token"):
            mock_run.return_value = MagicMock(returncode=1)

            result = await handler._post_with_curl(
                "test-owner", "test-repo", 123, "test body"
            )

            assert result is False
