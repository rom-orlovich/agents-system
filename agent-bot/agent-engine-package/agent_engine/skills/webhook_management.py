from typing import Any
import uuid

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class WebhookManagementSkill(BaseSkill):
    skill_type = SkillType.WEBHOOK_MANAGEMENT

    def __init__(self, http_client: Any, dashboard_api_url: str = "http://internal-dashboard-api:5000"):
        super().__init__(http_client)
        self._api_url = dashboard_api_url

    def get_available_actions(self) -> list[str]:
        return [
            "list_webhooks",
            "create_webhook",
            "delete_webhook",
            "test_webhook",
            "get_webhook_logs",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters

        try:
            if action == "list_webhooks":
                result = await self._list_webhooks()
            elif action == "create_webhook":
                result = await self._create_webhook(
                    params["source"],
                    params["events"],
                    params.get("filters", {}),
                )
            elif action == "delete_webhook":
                result = await self._delete_webhook(params["webhook_id"])
            elif action == "test_webhook":
                result = await self._test_webhook(params["webhook_id"])
            elif action == "get_webhook_logs":
                result = await self._get_webhook_logs(params["webhook_id"])
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("webhook_management_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _list_webhooks(self) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/webhooks"
        return await self._http.get(url)

    async def _create_webhook(
        self,
        source: str,
        events: list[str],
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        webhook_id = str(uuid.uuid4())
        url = f"{self._api_url}/api/v1/webhooks"
        result = await self._http.post(
            url,
            json={
                "webhook_id": webhook_id,
                "source": source,
                "events": events,
                "filters": filters,
                "active": True,
            },
        )
        return {"webhook_id": webhook_id, **result}

    async def _delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/webhooks/{webhook_id}"
        return await self._http.delete(url)

    async def _test_webhook(self, webhook_id: str) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/webhooks/{webhook_id}/test"
        return await self._http.post(url)

    async def _get_webhook_logs(self, webhook_id: str) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/webhooks/{webhook_id}/logs"
        return await self._http.get(url)
