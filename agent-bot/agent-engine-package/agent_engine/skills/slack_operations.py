from typing import Any

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class SlackOperationsSkill(BaseSkill):
    skill_type = SkillType.SLACK_OPERATIONS

    def __init__(self, http_client: Any, slack_api_url: str = "http://slack-api:3003"):
        super().__init__(http_client)
        self._api_url = slack_api_url

    def get_available_actions(self) -> list[str]:
        return [
            "send_message",
            "get_channel_history",
            "get_thread_replies",
            "add_reaction",
            "get_channel_info",
            "list_channels",
            "get_user_info",
            "update_message",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters

        try:
            if action == "send_message":
                result = await self._send_message(
                    params["channel"],
                    params["text"],
                    params.get("thread_ts"),
                )
            elif action == "get_channel_history":
                result = await self._get_channel_history(
                    params["channel"], params.get("limit", 100)
                )
            elif action == "get_thread_replies":
                result = await self._get_thread_replies(params["channel"], params["ts"])
            elif action == "add_reaction":
                result = await self._add_reaction(
                    params["channel"], params["ts"], params["name"]
                )
            elif action == "get_channel_info":
                result = await self._get_channel_info(params["channel"])
            elif action == "list_channels":
                result = await self._list_channels()
            elif action == "get_user_info":
                result = await self._get_user_info(params["user"])
            elif action == "update_message":
                result = await self._update_message(
                    params["channel"], params["ts"], params["text"]
                )
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("slack_operation_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _send_message(
        self, channel: str, text: str, thread_ts: str | None = None
    ) -> dict[str, Any]:
        url = f"{self._api_url}/messages"
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        return await self._http.post(url, json=payload)

    async def _get_channel_history(
        self, channel: str, limit: int = 100
    ) -> dict[str, Any]:
        url = f"{self._api_url}/channels/{channel}/history"
        return await self._http.get(url, params={"limit": limit})

    async def _get_thread_replies(self, channel: str, ts: str) -> dict[str, Any]:
        url = f"{self._api_url}/channels/{channel}/threads/{ts}"
        return await self._http.get(url)

    async def _add_reaction(
        self, channel: str, ts: str, name: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/reactions"
        return await self._http.post(
            url, json={"channel": channel, "timestamp": ts, "name": name}
        )

    async def _get_channel_info(self, channel: str) -> dict[str, Any]:
        url = f"{self._api_url}/channels/{channel}"
        return await self._http.get(url)

    async def _list_channels(self) -> dict[str, Any]:
        url = f"{self._api_url}/channels"
        return await self._http.get(url)

    async def _get_user_info(self, user: str) -> dict[str, Any]:
        url = f"{self._api_url}/users/{user}"
        return await self._http.get(url)

    async def _update_message(
        self, channel: str, ts: str, text: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/messages/{ts}"
        return await self._http.put(url, json={"channel": channel, "text": text})
