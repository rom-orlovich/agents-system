"""
Jira Service
============
Real integration with Jira API.
"""

import structlog
from jira import JIRA, JIRAError
from typing import List, Dict, Any, Optional

from config import settings

logger = structlog.get_logger(__name__)


class JiraService:
    """Service for interacting with Jira API."""
    
    def __init__(self):
        """Initialize Jira client."""
        self.client = JIRA(
            server=settings.jira.base_url,
            basic_auth=(settings.jira.email, settings.jira.api_token)
        )
        self.project_key = settings.jira.project_key
        logger.info("jira_service_initialized", base_url=settings.jira.base_url)
    
    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get a Jira issue by key.
        
        Args:
            issue_key: Issue key (e.g., PROJ-123)
            
        Returns:
            Issue data dict or None
        """
        try:
            issue = self.client.issue(issue_key)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": str(issue.fields.status),
                "priority": str(issue.fields.priority) if issue.fields.priority else "Medium",
                "labels": issue.fields.labels or [],
                "assignee": str(issue.fields.assignee) if issue.fields.assignee else None,
                "reporter": str(issue.fields.reporter) if issue.fields.reporter else None,
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "issue_type": str(issue.fields.issuetype),
                "url": f"{settings.jira.base_url}/browse/{issue.key}",
            }
        except JIRAError as e:
            logger.error("jira_issue_not_found", issue_key=issue_key, error=str(e))
            return None
    
    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search issues using JQL.
        
        Args:
            jql: JQL query string
            max_results: Maximum results to return
            
        Returns:
            List of issue data dicts
        """
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)
            return [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": str(issue.fields.status),
                    "priority": str(issue.fields.priority) if issue.fields.priority else "Medium",
                    "labels": issue.fields.labels or [],
                }
                for issue in issues
            ]
        except JIRAError as e:
            logger.error("jira_search_failed", jql=jql, error=str(e))
            return []
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add a comment to an issue.
        
        Args:
            issue_key: Issue key
            comment: Comment text
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_add_comment", issue_key=issue_key)
            return True
            
        try:
            self.client.add_comment(issue_key, comment)
            logger.info("comment_added", issue_key=issue_key)
            return True
        except JIRAError as e:
            logger.error("jira_comment_failed", issue_key=issue_key, error=str(e))
            return False
    
    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        labels: Optional[List[str]] = None,
        priority: str = "Medium"
    ) -> Optional[Dict[str, Any]]:
        """Create a new Jira issue.
        
        Args:
            summary: Issue title
            description: Issue description
            issue_type: Type of issue (Task, Bug, Story, etc.)
            labels: List of labels
            priority: Priority level
            
        Returns:
            Created issue data or None
        """
        if settings.execution.dry_run:
            logger.info("dry_run_create_issue", summary=summary)
            return {"key": f"{self.project_key}-DRY", "summary": summary}
            
        try:
            issue_dict = {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
            
            if labels:
                issue_dict["labels"] = labels
                
            issue = self.client.create_issue(fields=issue_dict)
            logger.info("issue_created", issue_key=issue.key)
            
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "url": f"{settings.jira.base_url}/browse/{issue.key}",
            }
        except JIRAError as e:
            logger.error("jira_create_failed", summary=summary, error=str(e))
            return None
    
    def update_issue(
        self,
        issue_key: str,
        fields: Dict[str, Any]
    ) -> bool:
        """Update an existing issue.
        
        Args:
            issue_key: Issue key
            fields: Fields to update
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_update_issue", issue_key=issue_key, fields=fields)
            return True
            
        try:
            issue = self.client.issue(issue_key)
            issue.update(fields=fields)
            logger.info("issue_updated", issue_key=issue_key)
            return True
        except JIRAError as e:
            logger.error("jira_update_failed", issue_key=issue_key, error=str(e))
            return False
    
    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition an issue to a new status.
        
        Args:
            issue_key: Issue key
            transition_name: Name of the transition (e.g., "In Progress", "Done")
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_transition", issue_key=issue_key, transition=transition_name)
            return True
            
        try:
            transitions = self.client.transitions(issue_key)
            transition_id = None
            
            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break
            
            if transition_id:
                self.client.transition_issue(issue_key, transition_id)
                logger.info("issue_transitioned", issue_key=issue_key, transition=transition_name)
                return True
            else:
                logger.warning("transition_not_found", issue_key=issue_key, transition=transition_name)
                return False
        except JIRAError as e:
            logger.error("jira_transition_failed", issue_key=issue_key, error=str(e))
            return False
    
    def get_project_issues(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all issues in the configured project.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of issues
        """
        jql = f"project = {self.project_key}"
        if status:
            jql += f" AND status = '{status}'"
        jql += " ORDER BY updated DESC"
        
        return self.search_issues(jql)
