import httpx
import structlog
from typing import Any

from .models import (
    PostMessageInput,
    PostMessageResponse,
    UpdateMessageInput,
    UpdateMessageResponse,
    AddReactionInput,
    AddReactionResponse,
)
from .exceptions import (
    SlackAuthenticationError,
    SlackNotFoundError,
    SlackValidationError,
    SlackRateLimitError,
    SlackServerError,
    SlackClientError,
)

logger = structlog.get_logger()


class SlackClient:
    def __init__(self, bot_token: str, timeout: float = 30.0):
        self.bot_token = bot_token
        self.timeout = timeout
        self.base_url = "https://slack.com/api"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

    def _handle_slack_error(self, response_data: dict[str, Any], context: str) -> None:
        if not response_data.get("ok"):
            error = response_data.get("error", "unknown_error")

            if error in ["invalid_auth", "not_authed", "account_inactive", "token_revoked"]:
                raise SlackAuthenticationError(f"{context}: {error}")
            elif error in ["channel_not_found", "message_not_found"]:
                raise SlackNotFoundError(f"{context}: {error}")
            elif error in ["invalid_arguments", "cant_update_message"]:
                raise SlackValidationError(f"{context}: {error}")
            elif error == "rate_limited":
                raise SlackRateLimitError(f"{context}: Rate limit exceeded")
            else:
                raise SlackClientError(f"{context}: {error}")

    def _handle_http_error(self, response: httpx.Response, context: str) -> None:
        status_code = response.status_code

        if status_code == 401:
            raise SlackAuthenticationError(f"{context}: Invalid token")
        elif status_code == 404:
            raise SlackNotFoundError(f"{context}: Resource not found")
        elif status_code == 429:
            raise SlackRateLimitError(f"{context}: Rate limit exceeded")
        elif status_code >= 500:
            raise SlackServerError(f"{context}: Server error ({status_code})")
        else:
            raise SlackClientError(f"{context}: HTTP {status_code} - {response.text}")

    async def post_message(self, input_data: PostMessageInput) -> PostMessageResponse:
        url = f"{self.base_url}/chat.postMessage"
        payload = {
            "channel": input_data.channel,
            "text": input_data.text,
        }
        if input_data.thread_ts:
            payload["thread_ts"] = input_data.thread_ts

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                self._handle_slack_error(result, "post_message")

                logger.info(
                    "slack_message_posted",
                    channel=input_data.channel,
                    ts=result.get("ts"),
                )

                return PostMessageResponse(
                    success=True,
                    ts=result.get("ts"),
                    channel=result.get("channel"),
                    message=f"Successfully posted message to {input_data.channel}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e.response, "post_message")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "slack_post_message_failed",
                    channel=input_data.channel,
                    error=str(e),
                )
                return PostMessageResponse(
                    success=False,
                    ts=None,
                    channel=None,
                    message=f"Error posting message: {str(e)}",
                )

    async def update_message(
        self, input_data: UpdateMessageInput
    ) -> UpdateMessageResponse:
        url = f"{self.base_url}/chat.update"
        payload = {
            "channel": input_data.channel,
            "ts": input_data.ts,
            "text": input_data.text,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                self._handle_slack_error(result, "update_message")

                logger.info(
                    "slack_message_updated",
                    channel=input_data.channel,
                    ts=input_data.ts,
                )

                return UpdateMessageResponse(
                    success=True,
                    ts=result.get("ts"),
                    message=f"Successfully updated message in {input_data.channel}",
                )
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e.response, "update_message")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "slack_update_message_failed",
                    channel=input_data.channel,
                    error=str(e),
                )
                return UpdateMessageResponse(
                    success=False,
                    ts=None,
                    message=f"Error updating message: {str(e)}",
                )

    async def add_reaction(self, input_data: AddReactionInput) -> AddReactionResponse:
        url = f"{self.base_url}/reactions.add"
        payload = {
            "channel": input_data.channel,
            "timestamp": input_data.timestamp,
            "name": input_data.name,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                self._handle_slack_error(result, "add_reaction")

                logger.info(
                    "slack_reaction_added",
                    channel=input_data.channel,
                    name=input_data.name,
                )

                return AddReactionResponse(
                    success=True,
                    message=f"Successfully added reaction :{input_data.name}:",
                )
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e.response, "add_reaction")
                raise
            except httpx.HTTPError as e:
                logger.error(
                    "slack_add_reaction_failed",
                    channel=input_data.channel,
                    error=str(e),
                )
                return AddReactionResponse(
                    success=False, message=f"Error adding reaction: {str(e)}"
                )
