from pydantic import BaseModel, Field, ConfigDict


class PostMessageRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    text: str = Field(..., description="Message text", min_length=1, max_length=40000)
    thread_ts: str | None = Field(None, description="Thread timestamp for replies")


class PostMessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    ts: str | None = Field(None, description="Message timestamp")
    message: str
    error: str | None = Field(None)


class UpdateMessageRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    channel: str = Field(..., description="Channel ID", min_length=1)
    ts: str = Field(..., description="Message timestamp", min_length=1)
    text: str = Field(..., description="Updated message text", min_length=1)


class UpdateMessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    success: bool
    message: str
    error: str | None = Field(None)
