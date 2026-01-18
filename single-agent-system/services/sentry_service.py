"""
Sentry Service
==============
Real integration with Sentry API.
"""

import httpx
import structlog
from typing import List, Dict, Any, Optional

from config import settings

logger = structlog.get_logger(__name__)


class SentryService:
    """Service for interacting with Sentry API."""
    
    BASE_URL = "https://sentry.io/api/0"
    
    def __init__(self):
        """Initialize Sentry client."""
        self.org = settings.sentry.org
        self.auth_token = settings.sentry.auth_token
        self.thresholds = settings.sentry.thresholds
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
        logger.info("sentry_service_initialized", org=self.org)
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make a request to the Sentry API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments
            
        Returns:
            Response data or None
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            with httpx.Client(timeout=settings.execution.api_timeout) as client:
                response = client.request(method, url, headers=self.headers, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error("sentry_request_failed", method=method, endpoint=endpoint, error=str(e))
            return None
    
    def get_issues(
        self,
        project_slug: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get issues from Sentry.
        
        Args:
            project_slug: Optional project to filter by
            query: Optional search query
            limit: Maximum issues to return
            
        Returns:
            List of issue data
        """
        endpoint = f"organizations/{self.org}/issues/"
        params = {"limit": limit}
        
        if project_slug:
            params["project"] = project_slug
        if query:
            params["query"] = query
        
        data = self._request("GET", endpoint, params=params)
        
        if not data:
            return []
        
        return [
            {
                "id": issue["id"],
                "title": issue["title"],
                "culprit": issue.get("culprit", ""),
                "level": issue.get("level", "error"),
                "status": issue.get("status", "unresolved"),
                "count": int(issue.get("count", 0)),
                "first_seen": issue.get("firstSeen"),
                "last_seen": issue.get("lastSeen"),
                "project": issue.get("project", {}).get("slug"),
                "url": issue.get("permalink"),
            }
            for issue in data
        ]
    
    def get_issue_details(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an issue.
        
        Args:
            issue_id: Sentry issue ID
            
        Returns:
            Issue details or None
        """
        endpoint = f"issues/{issue_id}/"
        data = self._request("GET", endpoint)
        
        if not data:
            return None
        
        return {
            "id": data["id"],
            "title": data["title"],
            "culprit": data.get("culprit", ""),
            "level": data.get("level", "error"),
            "status": data.get("status", "unresolved"),
            "count": int(data.get("count", 0)),
            "first_seen": data.get("firstSeen"),
            "last_seen": data.get("lastSeen"),
            "project": data.get("project", {}).get("slug"),
            "metadata": data.get("metadata", {}),
            "type": data.get("type"),
            "tags": data.get("tags", []),
            "url": data.get("permalink"),
        }
    
    def get_issue_events(self, issue_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get events for an issue (stack traces, etc.).
        
        Args:
            issue_id: Sentry issue ID
            limit: Maximum events to return
            
        Returns:
            List of event data
        """
        endpoint = f"issues/{issue_id}/events/"
        data = self._request("GET", endpoint, params={"limit": limit})
        
        if not data:
            return []
        
        return [
            {
                "id": event["id"],
                "event_id": event.get("eventID"),
                "title": event.get("title"),
                "message": event.get("message"),
                "timestamp": event.get("dateCreated"),
                "platform": event.get("platform"),
                "tags": event.get("tags", []),
                "context": event.get("context", {}),
                "entries": self._extract_entries(event.get("entries", [])),
            }
            for event in data
        ]
    
    def _extract_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract useful data from event entries.
        
        Args:
            entries: List of entry data
            
        Returns:
            Extracted entry data
        """
        result = {}
        
        for entry in entries:
            entry_type = entry.get("type")
            data = entry.get("data", {})
            
            if entry_type == "exception":
                result["exception"] = {
                    "type": data.get("values", [{}])[0].get("type"),
                    "value": data.get("values", [{}])[0].get("value"),
                    "stacktrace": self._format_stacktrace(
                        data.get("values", [{}])[0].get("stacktrace", {})
                    ),
                }
            elif entry_type == "message":
                result["message"] = data.get("formatted")
            elif entry_type == "breadcrumbs":
                result["breadcrumbs"] = [
                    {
                        "category": b.get("category"),
                        "message": b.get("message"),
                        "level": b.get("level"),
                    }
                    for b in data.get("values", [])[-5:]  # Last 5 breadcrumbs
                ]
        
        return result
    
    def _format_stacktrace(self, stacktrace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format stacktrace for readability.
        
        Args:
            stacktrace: Stacktrace data
            
        Returns:
            Formatted frames
        """
        frames = stacktrace.get("frames", [])
        return [
            {
                "filename": frame.get("filename"),
                "function": frame.get("function"),
                "lineno": frame.get("lineNo"),
                "context_line": frame.get("contextLine"),
                "in_app": frame.get("inApp", False),
            }
            for frame in frames[-10:]  # Last 10 frames
            if frame.get("inApp", False)  # Only in-app frames
        ]
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects in the organization.
        
        Returns:
            List of project data
        """
        endpoint = f"organizations/{self.org}/projects/"
        data = self._request("GET", endpoint)
        
        if not data:
            return []
        
        return [
            {
                "id": project["id"],
                "slug": project["slug"],
                "name": project["name"],
                "platform": project.get("platform"),
            }
            for project in data
        ]
    
    def should_escalate(self, issue: Dict[str, Any]) -> bool:
        """Determine if an issue should be escalated based on thresholds.
        
        Args:
            issue: Issue data
            
        Returns:
            True if issue should be escalated
        """
        level = issue.get("level", "error")
        count = issue.get("count", 0)
        threshold = self.thresholds.get(level, self.thresholds["error"])
        
        return count >= threshold
    
    def resolve_issue(self, issue_id: str) -> bool:
        """Mark an issue as resolved.
        
        Args:
            issue_id: Sentry issue ID
            
        Returns:
            True if successful
        """
        if settings.execution.dry_run:
            logger.info("dry_run_resolve_issue", issue_id=issue_id)
            return True
        
        endpoint = f"issues/{issue_id}/"
        data = self._request("PUT", endpoint, json={"status": "resolved"})
        
        if data:
            logger.info("issue_resolved", issue_id=issue_id)
            return True
        return False
