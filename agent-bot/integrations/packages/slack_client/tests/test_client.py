import pytest
import respx
import httpx
from slack_client import (
    SlackClient,
    PostMessageInput,
    PostMessageResponse,
    UpdateMessageInput,
    UpdateMessageResponse,
    AddReactionInput,
    AddReactionResponse,
    SlackAuthenticationError,
    SlackNotFoundError,
    SlackValidationError,
    SlackRateLimitError,
    SlackServerError,
)


@pytest.fixture
def slack_client():
    return SlackClient(bot_token="xoxb-test-token")


@pytest.mark.asyncio
@respx.mock
async def test_post_message_success(slack_client):
    input_data = PostMessageInput(channel="C12345", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "ts": "1234567890.123456",
                "channel": "C12345",
            },
        )
    )

    response = await slack_client.post_message(input_data)

    assert response.success is True
    assert response.ts == "1234567890.123456"
    assert response.channel == "C12345"
    assert "Successfully posted message" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_post_message_with_thread(slack_client):
    input_data = PostMessageInput(
        channel="C12345", text="Thread reply", thread_ts="1234567890.123456"
    )

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "ts": "1234567890.123457",
                "channel": "C12345",
            },
        )
    )

    response = await slack_client.post_message(input_data)

    assert response.success is True
    assert response.ts == "1234567890.123457"


@pytest.mark.asyncio
@respx.mock
async def test_post_message_channel_not_found(slack_client):
    input_data = PostMessageInput(channel="C99999", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "error": "channel_not_found",
            },
        )
    )

    with pytest.raises(SlackNotFoundError):
        await slack_client.post_message(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_post_message_invalid_auth(slack_client):
    input_data = PostMessageInput(channel="C12345", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "error": "invalid_auth",
            },
        )
    )

    with pytest.raises(SlackAuthenticationError):
        await slack_client.post_message(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_post_message_rate_limited(slack_client):
    input_data = PostMessageInput(channel="C12345", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "error": "rate_limited",
            },
        )
    )

    with pytest.raises(SlackRateLimitError):
        await slack_client.post_message(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_update_message_success(slack_client):
    input_data = UpdateMessageInput(
        channel="C12345", ts="1234567890.123456", text="Updated message"
    )

    respx.post("https://slack.com/api/chat.update").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "ts": "1234567890.123456",
                "channel": "C12345",
            },
        )
    )

    response = await slack_client.update_message(input_data)

    assert response.success is True
    assert response.ts == "1234567890.123456"
    assert "Successfully updated message" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_update_message_not_found(slack_client):
    input_data = UpdateMessageInput(
        channel="C12345", ts="9999999999.999999", text="Updated message"
    )

    respx.post("https://slack.com/api/chat.update").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "error": "message_not_found",
            },
        )
    )

    with pytest.raises(SlackNotFoundError):
        await slack_client.update_message(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_add_reaction_success(slack_client):
    input_data = AddReactionInput(
        channel="C12345", timestamp="1234567890.123456", name="thumbsup"
    )

    respx.post("https://slack.com/api/reactions.add").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
            },
        )
    )

    response = await slack_client.add_reaction(input_data)

    assert response.success is True
    assert "Successfully added reaction" in response.message


@pytest.mark.asyncio
@respx.mock
async def test_add_reaction_invalid_arguments(slack_client):
    input_data = AddReactionInput(
        channel="C12345", timestamp="1234567890.123456", name="invalid:emoji"
    )

    respx.post("https://slack.com/api/reactions.add").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": False,
                "error": "invalid_arguments",
            },
        )
    )

    with pytest.raises(SlackValidationError):
        await slack_client.add_reaction(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_http_401_error(slack_client):
    input_data = PostMessageInput(channel="C12345", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )

    with pytest.raises(SlackAuthenticationError):
        await slack_client.post_message(input_data)


@pytest.mark.asyncio
@respx.mock
async def test_http_500_error(slack_client):
    input_data = PostMessageInput(channel="C12345", text="Hello, World!")

    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(500, json={"error": "Internal server error"})
    )

    with pytest.raises(SlackServerError):
        await slack_client.post_message(input_data)


@pytest.mark.asyncio
async def test_pydantic_strict_validation():
    with pytest.raises(ValueError):
        PostMessageInput(channel="C12345", text=123)

    with pytest.raises(ValueError):
        PostMessageInput(channel=None, text="Test")

    with pytest.raises(ValueError):
        UpdateMessageInput(channel="C12345", ts=None, text="Test")
