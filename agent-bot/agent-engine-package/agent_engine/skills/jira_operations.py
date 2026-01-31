from typing import Any

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class JiraOperationsSkill(BaseSkill):
    skill_type = SkillType.JIRA_OPERATIONS

    def __init__(self, http_client: Any, jira_api_url: str = "http://jira-api:3002"):
        super().__init__(http_client)
        self._api_url = jira_api_url

    def get_available_actions(self) -> list[str]:
        return [
            "get_issue",
            "create_issue",
            "update_issue",
            "add_comment",
            "search_issues",
            "get_transitions",
            "transition_issue",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters

        try:
            if action == "get_issue":
                result = await self._get_issue(params["issue_key"])
            elif action == "create_issue":
                result = await self._create_issue(
                    params["project_key"],
                    params["summary"],
                    params["issue_type"],
                    params.get("description"),
                )
            elif action == "update_issue":
                result = await self._update_issue(params["issue_key"], params["fields"])
            elif action == "add_comment":
                result = await self._add_comment(params["issue_key"], params["body"])
            elif action == "search_issues":
                result = await self._search_issues(params["jql"])
            elif action == "get_transitions":
                result = await self._get_transitions(params["issue_key"])
            elif action == "transition_issue":
                result = await self._transition_issue(
                    params["issue_key"], params["transition_id"]
                )
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("jira_operation_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _get_issue(self, issue_key: str) -> dict[str, Any]:
        url = f"{self._api_url}/issues/{issue_key}"
        return await self._http.get(url)

    async def _create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self._api_url}/issues"
        return await self._http.post(
            url,
            json={
                "project_key": project_key,
                "summary": summary,
                "issue_type": issue_type,
                "description": description,
            },
        )

    async def _update_issue(
        self, issue_key: str, fields: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{self._api_url}/issues/{issue_key}"
        return await self._http.put(url, json={"fields": fields})

    async def _add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        url = f"{self._api_url}/issues/{issue_key}/comments"
        return await self._http.post(url, json={"body": body})

    async def _search_issues(self, jql: str) -> dict[str, Any]:
        url = f"{self._api_url}/search"
        return await self._http.get(url, params={"jql": jql})

    async def _get_transitions(self, issue_key: str) -> dict[str, Any]:
        url = f"{self._api_url}/issues/{issue_key}/transitions"
        return await self._http.get(url)

    async def _transition_issue(
        self, issue_key: str, transition_id: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/issues/{issue_key}/transitions"
        return await self._http.post(url, json={"transition_id": transition_id})
