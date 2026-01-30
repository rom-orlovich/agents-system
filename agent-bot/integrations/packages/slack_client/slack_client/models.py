from pydantic import BaseModel, Field, ConfigDict


class PostMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    text: str = Field(..., description="Message text", min_length=1)
    thread_ts: str | None = Field(None, description="Thread timestamp to reply in thread")


class PostMessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    ts: str | None = Field(None, description="Message timestamp")
    channel: str | None = Field(None)
    message: str


class UpdateMessageInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    ts: str = Field(..., description="Message timestamp", min_length=1)
    text: str = Field(..., description="Updated message text", min_length=1)


class UpdateMessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    ts: str | None = Field(None)
    message: str


class AddReactionInput(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    timestamp: str = Field(..., description="Message timestamp", min_length=1)
    name: str = Field(..., description="Reaction name without colons", min_length=1)


class AddReactionResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
