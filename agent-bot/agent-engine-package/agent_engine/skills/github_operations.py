from typing import Any

from .base import BaseSkill, SkillInput, SkillOutput, SkillType


class GitHubOperationsSkill(BaseSkill):
    skill_type = SkillType.GITHUB_OPERATIONS

    def __init__(self, http_client: Any, github_api_url: str = "http://github-api:3001"):
        super().__init__(http_client)
        self._api_url = github_api_url

    def get_available_actions(self) -> list[str]:
        return [
            "get_repository",
            "get_issue",
            "create_issue",
            "create_issue_comment",
            "get_pull_request",
            "create_pr_review_comment",
            "get_file_contents",
            "search_code",
            "list_branches",
        ]

    async def execute(self, skill_input: SkillInput) -> SkillOutput:
        action = skill_input.action
        params = skill_input.parameters

        try:
            if action == "get_repository":
                result = await self._get_repository(params["owner"], params["repo"])
            elif action == "get_issue":
                result = await self._get_issue(
                    params["owner"], params["repo"], params["issue_number"]
                )
            elif action == "create_issue":
                result = await self._create_issue(
                    params["owner"], params["repo"], params["title"], params.get("body")
                )
            elif action == "create_issue_comment":
                result = await self._create_issue_comment(
                    params["owner"],
                    params["repo"],
                    params["issue_number"],
                    params["body"],
                )
            elif action == "get_pull_request":
                result = await self._get_pull_request(
                    params["owner"], params["repo"], params["pr_number"]
                )
            elif action == "create_pr_review_comment":
                result = await self._create_pr_review_comment(
                    params["owner"],
                    params["repo"],
                    params["pr_number"],
                    params["body"],
                )
            elif action == "get_file_contents":
                result = await self._get_file_contents(
                    params["owner"], params["repo"], params["path"]
                )
            elif action == "search_code":
                result = await self._search_code(params["query"])
            elif action == "list_branches":
                result = await self._list_branches(params["owner"], params["repo"])
            else:
                return SkillOutput(success=False, result=None, error=f"Unknown action: {action}")

            return SkillOutput(success=True, result=result)
        except Exception as e:
            self._logger.exception("github_operation_failed", action=action)
            return SkillOutput(success=False, result=None, error=str(e))

    async def _get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}"
        return await self._http.get(url)

    async def _get_issue(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/issues/{issue_number}"
        return await self._http.get(url)

    async def _create_issue(
        self, owner: str, repo: str, title: str, body: str | None = None
    ) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/issues"
        return await self._http.post(url, json={"title": title, "body": body})

    async def _create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        return await self._http.post(url, json={"body": body})

    async def _get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        return await self._http.get(url)

    async def _create_pr_review_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        return await self._http.post(url, json={"body": body})

    async def _get_file_contents(
        self, owner: str, repo: str, path: str
    ) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/contents/{path}"
        return await self._http.get(url)

    async def _search_code(self, query: str) -> dict[str, Any]:
        url = f"{self._api_url}/search/code"
        return await self._http.get(url, params={"q": query})

    async def _list_branches(self, owner: str, repo: str) -> dict[str, Any]:
        url = f"{self._api_url}/repos/{owner}/{repo}/branches"
        return await self._http.get(url)
