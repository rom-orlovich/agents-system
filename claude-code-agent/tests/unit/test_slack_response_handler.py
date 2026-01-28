"""TDD tests for Slack domain response handler (Phase 5.1)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestSlackRoutingMetadataExtended:
    """Test Slack routing metadata with thread_ts extension."""

    def test_routing_metadata_includes_thread_ts(self):
        """
        Business Rule: Slack routing must support thread_ts.
        Behavior: SlackRoutingMetadata model accepts thread_ts field.
        """
        from api.webhooks.slack.models import SlackRoutingMetadata

        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345",
            user_id="U12345",
            thread_ts="1234567890.123456"
        )

        assert routing.thread_ts == "1234567890.123456"

    def test_routing_metadata_thread_ts_optional(self):
        """
        Business Rule: thread_ts should be optional.
        Behavior: SlackRoutingMetadata works without thread_ts.
        """
        from api.webhooks.slack.models import SlackRoutingMetadata

        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        assert routing.thread_ts is None


class TestSlackResponseHandler:
    """Test Slack domain response handler behavior."""

    @pytest.mark.asyncio
    async def test_post_response_to_slack_channel(self):
        """
        Business Rule: Response handler posts message to Slack channel.
        Behavior: When routing has channel_id, post to channel.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345",
            user_id="U12345"
        )
        result = "Analysis complete: No issues found."

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"ok": true}'
            )

            success = await handler.post_response(routing, result)

            assert success is True

    @pytest.mark.asyncio
    async def test_post_response_to_thread(self):
        """
        Business Rule: Response handler posts to thread when thread_ts exists.
        Behavior: When routing has thread_ts, include it in payload.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345",
            thread_ts="1234567890.123456"
        )
        result = "Thread reply content."

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"ok": true}'
            )

            success = await handler.post_response(routing, result)

            assert success is True
            call_args = mock_run.call_args[0][0]
            body_arg = None
            for i, arg in enumerate(call_args):
                if arg == "-d":
                    body_arg = json.loads(call_args[i + 1])
                    break

            assert body_arg is not None
            assert body_arg["thread_ts"] == "1234567890.123456"

    @pytest.mark.asyncio
    async def test_returns_false_when_missing_channel_id(self):
        """
        Business Rule: Handler returns False when channel_id is missing.
        Behavior: If routing.channel_id is empty, return False without posting.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="",
            team_id="T12345"
        )

        success = await handler.post_response(routing, "test result")

        assert success is False

    @pytest.mark.asyncio
    async def test_returns_false_when_missing_token(self):
        """
        Business Rule: Handler returns False when Slack token is missing.
        Behavior: If SLACK_BOT_TOKEN not set, return False.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('os.environ.get', return_value=None):
            success = await handler.post_response(routing, "test result")

            assert success is False

    @pytest.mark.asyncio
    async def test_validates_response_format(self):
        """
        Business Rule: Validates response format before posting.
        Behavior: Calls format validation with 'slack' type.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )
        result = "Slack message content"

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format') as mock_validate:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')
            mock_validate.return_value = (True, "")

            await handler.post_response(routing, result)

            mock_validate.assert_called_once_with(result, "slack")

    @pytest.mark.asyncio
    async def test_posts_even_when_validation_fails(self):
        """
        Business Rule: Posts response even if format validation fails.
        Behavior: Validation failure logs warning but doesn't prevent posting.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )
        result = "Invalid format content"

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format') as mock_validate, \
             patch('api.webhooks.slack.handlers.logger') as mock_logger:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')
            mock_validate.return_value = (False, "Format validation failed")

            success = await handler.post_response(routing, result)

            assert success is True
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_handles_slack_api_error(self):
        """
        Business Rule: Handler handles Slack API errors.
        Behavior: Returns False when Slack API returns ok: false.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.slack.handlers.logger') as mock_logger:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"ok": false, "error": "channel_not_found"}'
            )

            success = await handler.post_response(routing, "test result")

            assert success is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_raises_error_on_exception(self):
        """
        Business Rule: Raises SlackResponseError on exceptions.
        Behavior: When posting raises exception, raise with context.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata
        from api.webhooks.slack.errors import SlackResponseError

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.side_effect = Exception("Network error")

            with pytest.raises(SlackResponseError) as exc_info:
                await handler.post_response(routing, "test result")

            assert "Network error" in str(exc_info.value)
            assert exc_info.value.context.channel_id == "C12345"

    @pytest.mark.asyncio
    async def test_logs_successful_post(self):
        """
        Business Rule: Logs successful Slack message posting.
        Behavior: After posting, logs info with channel.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")), \
             patch('api.webhooks.slack.handlers.logger') as mock_logger:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test result")

            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "slack_response_posted"
            assert call_args[1]["channel"] == "C12345"

    @pytest.mark.asyncio
    async def test_uses_correct_api_endpoint(self):
        """
        Business Rule: Uses correct Slack API endpoint.
        Behavior: Posts to chat.postMessage endpoint.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test result")

            call_args = mock_run.call_args[0][0]
            assert "https://slack.com/api/chat.postMessage" in call_args

    @pytest.mark.asyncio
    async def test_includes_authorization_header(self):
        """
        Business Rule: Includes Bearer token in Authorization header.
        Behavior: Request includes correct Authorization header.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test result")

            call_args = mock_run.call_args[0][0]
            auth_index = call_args.index("-H") + 1
            assert "Authorization: Bearer xoxb-test-token" in call_args[auth_index]


class TestSlackResponseHandlerPayload:
    """Test Slack response handler payload construction."""

    @pytest.mark.asyncio
    async def test_payload_includes_channel(self):
        """
        Business Rule: Payload includes channel field.
        Behavior: JSON payload has channel set to channel_id.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test message")

            call_args = mock_run.call_args[0][0]
            body_arg = None
            for i, arg in enumerate(call_args):
                if arg == "-d":
                    body_arg = json.loads(call_args[i + 1])
                    break

            assert body_arg["channel"] == "C12345"

    @pytest.mark.asyncio
    async def test_payload_includes_text(self):
        """
        Business Rule: Payload includes text field.
        Behavior: JSON payload has text set to result.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test message content")

            call_args = mock_run.call_args[0][0]
            body_arg = None
            for i, arg in enumerate(call_args):
                if arg == "-d":
                    body_arg = json.loads(call_args[i + 1])
                    break

            assert body_arg["text"] == "test message content"

    @pytest.mark.asyncio
    async def test_payload_excludes_thread_ts_when_none(self):
        """
        Business Rule: Payload excludes thread_ts when not provided.
        Behavior: JSON payload has no thread_ts when routing.thread_ts is None.
        """
        from api.webhooks.slack.handlers import SlackResponseHandler
        from api.webhooks.slack.models import SlackRoutingMetadata

        handler = SlackResponseHandler()
        routing = SlackRoutingMetadata(
            channel_id="C12345",
            team_id="T12345"
        )

        with patch('subprocess.run') as mock_run, \
             patch('os.environ.get', return_value="xoxb-test-token"), \
             patch('api.webhooks.slack.handlers.validate_response_format', return_value=(True, "")):
            mock_run.return_value = MagicMock(returncode=0, stdout='{"ok": true}')

            await handler.post_response(routing, "test message")

            call_args = mock_run.call_args[0][0]
            body_arg = None
            for i, arg in enumerate(call_args):
                if arg == "-d":
                    body_arg = json.loads(call_args[i + 1])
                    break

            assert "thread_ts" not in body_arg
