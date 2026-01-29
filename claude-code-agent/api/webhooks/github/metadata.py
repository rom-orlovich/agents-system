"""GitHub domain routing metadata extractor."""

from api.webhooks.github.models import GitHubRoutingMetadata


def extract_github_routing(payload: dict) -> GitHubRoutingMetadata:
    owner = ""
    repo = ""
    issue_number = None
    pr_number = None
    comment_id = None
    sender = None

    repository = payload.get("repository", {})
    full_name = repository.get("full_name", "")
    if "/" in full_name:
        owner, repo = full_name.split("/", 1)

    issue = payload.get("issue", {})
    if issue.get("number"):
        issue_number = issue["number"]

    pull_request = payload.get("pull_request", {})
    if pull_request.get("number"):
        pr_number = pull_request["number"]
    elif issue.get("pull_request"):
        pr_number = issue.get("number")

    comment = payload.get("comment", {})
    if comment.get("id"):
        comment_id = comment["id"]

    sender_data = payload.get("sender", {})
    if sender_data.get("login"):
        sender = sender_data["login"]

    return GitHubRoutingMetadata(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        pr_number=pr_number,
        comment_id=comment_id,
        sender=sender,
    )
