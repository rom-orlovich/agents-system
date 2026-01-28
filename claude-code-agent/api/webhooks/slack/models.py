from typing import Literal, Optional
from pydantic import BaseModel


class SlackUser(BaseModel):
    id: str
    username: str
    name: str


class SlackTeam(BaseModel):
    id: str
    domain: str


class SlackChannel(BaseModel):
    id: str
    name: str


class SlackMessage(BaseModel):
    type: str
    user: str
    text: str
    ts: str


class SlackAppMentionEvent(BaseModel):
    type: Literal["app_mention"]
    user: str
    text: str
    ts: str
    channel: str

    def extract_text(self) -> str:
        return self.text


class SlackMessageEvent(BaseModel):
    type: Literal["message"]
    user: str
    text: str
    ts: str
    channel: str

    def extract_text(self) -> str:
        return self.text


class SlackEventCallback(BaseModel):
    token: str
    team_id: str
    api_app_id: str
    type: Literal["event_callback"]
    event: SlackAppMentionEvent | SlackMessageEvent

    def extract_text(self) -> str:
        return self.event.extract_text()


class SlackUrlVerification(BaseModel):
    type: Literal["url_verification"]
    challenge: str


class SlackSlashCommand(BaseModel):
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str

    def extract_text(self) -> str:
        return self.text


SlackWebhookPayload = SlackEventCallback | SlackUrlVerification | SlackSlashCommand


class SlackRoutingMetadata(BaseModel):
    channel_id: str
    team_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
