import os
from fastapi import FastAPI, HTTPException
import structlog

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

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

app = FastAPI(
    title="Slack REST API",
    description="REST API for Slack using shared client",
    version="0.1.0",
)


def get_slack_client() -> SlackClient:
    bot_token = os.getenv("SLACK_BOT_TOKEN")

    if not bot_token:
        raise HTTPException(
            status_code=500, detail="SLACK_BOT_TOKEN must be configured"
        )

    return SlackClient(bot_token=bot_token)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "slack-rest-api"}


@app.post("/api/v1/slack/message", response_model=PostMessageResponse)
async def post_message(request: PostMessageInput):
    try:
        client = get_slack_client()
        return await client.post_message(request)
    except SlackAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SlackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SlackValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SlackRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except SlackServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.put("/api/v1/slack/message", response_model=UpdateMessageResponse)
async def update_message(request: UpdateMessageInput):
    try:
        client = get_slack_client()
        return await client.update_message(request)
    except SlackAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SlackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SlackValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SlackServerError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/v1/slack/reaction", response_model=AddReactionResponse)
async def add_reaction(request: AddReactionInput):
    try:
        client = get_slack_client()
        return await client.add_reaction(request)
    except SlackAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SlackNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SlackValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SlackServerError as e:
        raise HTTPException(status_code=502, detail=str(e))
