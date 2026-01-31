import uuid
from typing import Any

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class HumanApprovalSkill(BaseSkill):
    skill_type = SkillType.HUMAN_APPROVAL

    def __init__(self, http_client: Any, dashboard_api_url: str = "http://internal-dashboard-api:5000"):
        super().__init__(http_client)
        self._api_url = dashboard_api_url

    def get_available_actions(self) -> list[str]:
        return [
            "request_approval",
            "check_approval_status",
            "cancel_approval_request",
            "list_pending_approvals",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters

        try:
            if action == "request_approval":
                result = await self._request_approval(
                    params["task_id"],
                    params["description"],
                    params.get("changes", []),
                )
            elif action == "check_approval_status":
                result = await self._check_approval_status(params["approval_id"])
            elif action == "cancel_approval_request":
                result = await self._cancel_approval_request(params["approval_id"])
            elif action == "list_pending_approvals":
                result = await self._list_pending_approvals()
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("human_approval_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _request_approval(
        self,
        task_id: str,
        description: str,
        changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        approval_id = str(uuid.uuid4())
        url = f"{self._api_url}/api/v1/approvals"
        result = await self._http.post(
            url,
            json={
                "approval_id": approval_id,
                "task_id": task_id,
                "description": description,
                "changes": changes,
                "status": "pending",
            },
        )
        return {
            "approval_id": approval_id,
            "status": "pending",
            "message": "Approval request created",
            **result,
        }

    async def _check_approval_status(self, approval_id: str) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/approvals/{approval_id}"
        return await self._http.get(url)

    async def _cancel_approval_request(self, approval_id: str) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/approvals/{approval_id}"
        return await self._http.delete(url)

    async def _list_pending_approvals(self) -> dict[str, Any]:
        url = f"{self._api_url}/api/v1/approvals"
        return await self._http.get(url, params={"status": "pending"})
