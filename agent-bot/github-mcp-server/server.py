import os
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

server = Server("github-mcp-server")


class PostPRCommentInput(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    pr_number: int = Field(..., description="Pull request number", gt=0)
    comment: str = Field(..., description="Comment body", min_length=1)


class AddPRReactionInput(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    pr_number: int = Field(..., description="Pull request number", gt=0)
    reaction: Literal["+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes"] = Field(
        ..., description="Emoji reaction type"
    )


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="github_post_pr_comment",
            description="Post a comment on a GitHub pull request",
            inputSchema=PostPRCommentInput.model_json_schema(),
        ),
        Tool(
            name="github_add_pr_reaction",
            description="Add an emoji reaction to a GitHub pull request",
            inputSchema=AddPRReactionInput.model_json_schema(),
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return [TextContent(type="text", text="Error: GITHUB_TOKEN not configured")]

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        if name == "github_post_pr_comment":
            validated_input = PostPRCommentInput.model_validate(arguments)

            url = f"https://api.github.com/repos/{validated_input.owner}/{validated_input.repo}/issues/{validated_input.pr_number}/comments"

            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"body": validated_input.comment},
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "github_comment_posted",
                    owner=validated_input.owner,
                    repo=validated_input.repo,
                    pr_number=validated_input.pr_number,
                    comment_id=result.get("id"),
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully posted comment on PR #{validated_input.pr_number}. Comment ID: {result.get('id')}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "github_comment_failed",
                    owner=validated_input.owner,
                    repo=validated_input.repo,
                    pr_number=validated_input.pr_number,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error posting comment: {str(e)}")]

        elif name == "github_add_pr_reaction":
            validated_input = AddPRReactionInput.model_validate(arguments)

            url = f"https://api.github.com/repos/{validated_input.owner}/{validated_input.repo}/issues/{validated_input.pr_number}/reactions"

            try:
                response = await client.post(
                    url,
                    headers={**headers, "Accept": "application/vnd.github.squirrel-girl-preview+json"},
                    json={"content": validated_input.reaction},
                    timeout=30.0,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(
                    "github_reaction_added",
                    owner=validated_input.owner,
                    repo=validated_input.repo,
                    pr_number=validated_input.pr_number,
                    reaction=validated_input.reaction,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added {validated_input.reaction} reaction to PR #{validated_input.pr_number}",
                    )
                ]
            except httpx.HTTPError as e:
                logger.error(
                    "github_reaction_failed",
                    owner=validated_input.owner,
                    repo=validated_input.repo,
                    pr_number=validated_input.pr_number,
                    error=str(e),
                )
                return [TextContent(type="text", text=f"Error adding reaction: {str(e)}")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
