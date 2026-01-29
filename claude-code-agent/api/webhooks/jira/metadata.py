"""Jira domain routing metadata extractor."""

from api.webhooks.jira.models import JiraRoutingMetadata


def extract_jira_routing(payload: dict) -> JiraRoutingMetadata:
    issue_key = ""
    project_key = ""
    comment_id = None
    user_name = None

    issue = payload.get("issue", {})

    if issue.get("key"):
        issue_key = issue["key"]
        if "-" in issue_key:
            project_key = issue_key.split("-")[0]

    fields = issue.get("fields", {})
    project = fields.get("project", {})
    if project.get("key"):
        project_key = project["key"]

    comment = payload.get("comment", {})
    if comment.get("id"):
        comment_id = str(comment["id"])

    user = payload.get("user", {})
    if user.get("displayName"):
        user_name = user["displayName"]

    return JiraRoutingMetadata(
        issue_key=issue_key,
        project_key=project_key,
        comment_id=comment_id,
        user_name=user_name,
    )
