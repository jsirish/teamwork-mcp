"""Teamwork API client for MCP server."""

import logging
import os
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger(__name__)


class TeamworkClient:
    """Client for Teamwork.com API v3.
    
    This client expects to receive an OAuth access token and uses it
    to make authenticated requests to the Teamwork API.
    """
    
    def __init__(self, access_token: str, installation_domain: str):
        """Initialize Teamwork client.
        
        Args:
            access_token: OAuth 2.0 access token
            installation_domain: Teamwork installation domain (e.g., "dynamic8.teamwork.com")
        """
        self.access_token = access_token
        self.base_url = f"https://{installation_domain}/projects/api/v3"
        
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Teamwork API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            
            # Teamwork sometimes returns empty responses for successful operations
            if response.status_code == 204 or not response.content:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            LOGGER.error(f"Teamwork API error {e.response.status_code}: {e.response.text}")
            raise RuntimeError(
                f"Teamwork API error {e.response.status_code}: {e.response.text}"
            )
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Teamwork request failed: {e}")
            raise RuntimeError(f"Teamwork request failed: {e}")
    
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
