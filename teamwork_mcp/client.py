"""Teamwork API client for MCP server."""

import logging
import os
from typing import Any, Dict, List, Optional

from mcp_base import BaseAPIClient

LOGGER = logging.getLogger(__name__)


class TeamworkClient(BaseAPIClient):
    """Client for Teamwork.com API v3.
    
    Extends BaseAPIClient to inherit common HTTP request handling.
    This client expects to receive an OAuth access token and uses it
    to make authenticated requests to the Teamwork API.
    """
    
    def __init__(self, access_token: str, installation_domain: str):
        """Initialize Teamwork client.
        
        Args:
            access_token: OAuth 2.0 access token
            installation_domain: Teamwork installation domain (e.g., "dynamic8.teamwork.com")
        """
        # TeamworkClient uses dynamic base_url based on installation domain
        base_url = f"https://{installation_domain}/projects/api/v3"
        super().__init__(access_token=access_token, base_url=base_url)
    
    # ===== Project Management =====
    
    def list_projects(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List all projects."""
        return self._request(
            "GET",
            "/projects.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details."""
        return self._request("GET", f"/projects/{project_id}.json")
    
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new project."""
        payload = {"project": {"name": name}}
        if description:
            payload["project"]["description"] = description
        if start_date:
            payload["project"]["startDate"] = start_date
        if end_date:
            payload["project"]["endDate"] = end_date
            
        return self._request("POST", "/projects.json", json_data=payload)
    
    # ===== Task Management =====
    
    def list_tasks(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List tasks, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
        
        return self._request("GET", "/tasks.json", params=params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        return self._request("GET", f"/tasks/{task_id}.json")
    
    def create_task(
        self,
        name: str,
        tasklist_id: str,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        assignee_ids: Optional[List[str]] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task."""
        payload = {
            "task": {
                "name": name,
                "taskListId": tasklist_id,
            }
        }
        if description:
            payload["task"]["description"] = description
        if due_date:
            payload["task"]["dueDate"] = due_date
        if assignee_ids:
            payload["task"]["assigneeIds"] = assignee_ids
        if priority:
            payload["task"]["priority"] = priority
            
        return self._request("POST", "/tasks.json", json_data=payload)
    
    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing task."""
        payload = {"task": {}}
        if name is not None:
            payload["task"]["name"] = name
        if description is not None:
            payload["task"]["description"] = description
        if completed is not None:
            payload["task"]["completed"] = completed
        if due_date is not None:
            payload["task"]["dueDate"] = due_date
        if priority is not None:
            payload["task"]["priority"] = priority
            
        return self._request("PATCH", f"/tasks/{task_id}.json", json_data=payload)
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as complete."""
        return self.update_task(task_id, completed=True)
    
    # ===== Time Tracking =====
    
    def list_time_entries(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List time entries, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
            
        return self._request("GET", "/time.json", params=params)
    
    def log_time(
        self,
        project_id: str,
        hours: float,
        description: str,
        date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log time entry."""
        payload = {
            "timeEntry": {
                "projectId": project_id,
                "hours": hours,
                "description": description,
            }
        }
        if date:
            payload["timeEntry"]["date"] = date
        if task_id:
            payload["timeEntry"]["taskId"] = task_id
            
        return self._request("POST", "/timers.json", json_data=payload)
    
    # ===== People Management =====
    
    def list_people(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List people, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
            
        return self._request("GET", "/people.json", params=params)
    
    def get_me(self) -> Dict[str, Any]:
        """Get current authenticated user information."""
        return self._request("GET", "/me.json")
